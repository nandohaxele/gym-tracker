"""Database engine, session factory, and declarative Base.

Designed to be Postgres-ready: the only SQLite-specific tweak is
`connect_args={"check_same_thread": False}` which is applied conditionally.

Application SQLite connections enable `PRAGMA foreign_keys=ON` via
`make_engine`. Alembic `env.py` creates its own engine and must NOT call
this helper — batch rebuilds assume foreign keys are off.
"""

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings


def apply_sqlite_runtime_pragmas(dbapi_connection, _connection_record) -> None:
    """Per-connection SQLite settings for the application runtime."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(url: str, *, enable_sqlite_foreign_keys: bool = True) -> Engine:
    """Create an engine. SQLite app connections get runtime FK enforcement."""
    is_sqlite = url.startswith("sqlite")
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        future=True,
        pool_pre_ping=True,
    )
    if is_sqlite and enable_sqlite_foreign_keys:
        event.listen(engine, "connect", apply_sqlite_runtime_pragmas)
    return engine


_settings = get_settings()

# Runtime SQLite FK enforcement. Alembic env.py must not use make_engine.
engine = make_engine(_settings.database_url)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
