"""SQLAlchemy engine / session factory and database initialisation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger("nexa.db")

connect_args: Dict[str, Any] = {}
if settings.is_sqlite:
    # FastAPI serves requests from a thread pool, so the default SQLite
    # same-thread guard has to be relaxed.
    connect_args["check_same_thread"] = False

engine: Engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.SQL_ECHO,
    future=True,
    pool_pre_ping=True,
)


if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):  # noqa: ANN001
        """Enable foreign keys and a faster, safer journal mode."""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
    future=True,
)


def init_db() -> None:
    """Import every model module then create all tables."""
    # Importing the package registers all mappers on ``Base.metadata``.
    import app.models  # noqa: F401  pylint: disable=unused-import

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised at %s", settings.DATABASE_URL)


def get_session() -> Generator[Session, None, None]:
    """Yield a session and always close it (used outside FastAPI DI too)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
