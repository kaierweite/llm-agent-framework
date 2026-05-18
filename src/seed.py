import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_agent.config import settings
from llm_agent import database
import llm_agent.models  # noqa: F401
from llm_agent.models.user import User
from llm_agent.services.auth_service import hash_password


def seed():
    database.init_database(settings.database_url)
    database.create_tables()
    db = database.SessionLocal()

    email = "kaierweite@gmail.com"
    password = "123456"

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"用户 {email} 已存在，跳过创建。")
        db.close()
        return

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name="kaierweite",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.close()
    print(f"预置用户创建成功: {email}")


if __name__ == "__main__":
    seed()
