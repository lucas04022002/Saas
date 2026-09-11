from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def engine_kwargs(database_url: str) -> dict:
    """Build engine kwargs adapted to the database driver.

    - PostgreSQL: prepare_threshold=None
    - SQLite: check_same_thread=False
    - Others: empty connect_args
    """
    if database_url.startswith("postgresql"):
        connect_args = {"prepare_threshold": None}
    elif database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}

    return {
        "future": True,
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }


engine = create_engine(settings.database_url, **engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
