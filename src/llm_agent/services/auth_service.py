from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy.orm import Session

from llm_agent.config import settings
from llm_agent.models.user import User


class AuthError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise AuthError(40102, "Token expired")
    except jwt.InvalidTokenError:
        raise AuthError(40101, "Invalid token")


def register(db: Session, email: str, password: str, display_name: str | None = None) -> tuple[User, str]:
    if len(password) < 6:
        raise AuthError(40002, "密码长度不能少于6位")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise AuthError(40901, "Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name or email.split("@")[0],
        role="member",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_token(user.id, user.role)
    return user, token


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not check_password(password, user.password_hash):
        raise AuthError(40101, "Invalid credentials")
    if not user.is_active:
        raise AuthError(40101, "Account disabled")

    token = _create_token(user.id, user.role)
    return user, token


def get_current_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthError(40101, "User not found")
    if not user.is_active:
        raise AuthError(40101, "Account disabled")
    return user


def change_password(db: Session, user_id: str, old_password: str, new_password: str) -> User:
    if len(new_password) < 6:
        raise AuthError(40002, "密码长度不能少于6位")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthError(40101, "User not found")
    if not check_password(old_password, user.password_hash):
        raise AuthError(40101, "Invalid old password")

    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user
