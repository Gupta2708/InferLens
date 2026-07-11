from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def db_connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    if database_url.startswith("postgresql+psycopg"):
        # Supabase transaction/session poolers can reuse server connections across
        # clients. Named prepared statements from psycopg may then collide.
        return {"prepare_threshold": None}
    return {}


settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=db_connect_args(settings.database_url),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()