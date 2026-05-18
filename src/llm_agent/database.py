import os
import threading

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool

engine = None
SessionLocal = None
_database_url = None
_init_lock = threading.Lock()


class Base(DeclarativeBase):
    pass


def init_database(database_url: str):
    global engine, SessionLocal, _database_url
    _database_url = database_url
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def reinit_database():
    """在 Gunicorn post_fork 中调用，为每个 worker 重建独立的连接池。

    fork 之后父进程的 engine/连接池不能被子进程共享，
    必须 dispose 旧 engine 并重新创建。
    """
    global engine, SessionLocal
    if _database_url is None:
        return
    with _init_lock:
        # 关闭旧连接池中的所有连接
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass
        # 重建 engine — 每个 worker 获得独立的连接池
        engine = create_engine(
            _database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    print(f"[worker {os.getpid()}] 数据库连接池已重建")


def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # 出错时回滚，确保 session 不会停留在 failed 状态
        if db.is_active:
            db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    Base.metadata.create_all(bind=engine)


def seed_admin():
    import bcrypt
    from llm_agent.models.user import User
    from llm_agent.config import settings

    if SessionLocal is None:
        return

    if not settings.admin_email or not settings.admin_password:
        print("[init] 管理员账号未配置（ADMIN_EMAIL/ADMIN_PASSWORD），跳过种子创建")
        return

    db = SessionLocal()
    try:
        password_hash = bcrypt.hashpw(
            settings.admin_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        if db.query(User).count() == 0:
            admin = User(
                email=settings.admin_email,
                password_hash=password_hash,
                display_name="管理员",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"[init] 已创建默认管理员账号: {settings.admin_email}")
    finally:
        db.close()
