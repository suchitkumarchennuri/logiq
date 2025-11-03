"""Database session and initialization utilities."""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine, expire_on_commit=False, class_=Session)


def init_db() -> None:
    """Ensure pgvector extension exists and create tables."""

    from app.db import models  # noqa: F401

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    models.Base.metadata.create_all(bind=engine)


@contextmanager
def db_session_scope() -> Iterator[Session]:
    """Provide a transactional scope for non-FastAPI callers (e.g., Celery)."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Iterator[Session]:
    """FastAPI dependency that yields a SQLAlchemy session."""

    with db_session_scope() as session:
        yield session
