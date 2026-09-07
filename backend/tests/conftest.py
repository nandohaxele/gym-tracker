"""Isolated test database: temp SQLite + Alembic + real seeder.

This module sets DATABASE_URL before importing the application so the
process-level engine never points at backend/gym.db.
"""

from __future__ import annotations

import os
import pathlib
import tempfile
import uuid

_BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
_fd, _TEST_DB_PATH = tempfile.mkstemp(prefix="gym-tracker-test-", suffix=".db")
os.close(_fd)
_TEST_DB = pathlib.Path(_TEST_DB_PATH).resolve()
if _TEST_DB.name == "gym.db" or _TEST_DB == (_BACKEND_DIR / "gym.db").resolve():
    raise RuntimeError("Refusing to bind tests to live gym.db")

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed.seeder import run_seed  # noqa: E402


def _assert_not_live_db() -> None:
    url = get_settings().database_url
    if "gym.db" in url:
        raise RuntimeError(f"Tests resolved DATABASE_URL to live file: {url}")
    live = (_BACKEND_DIR / "gym.db").resolve()
    if _TEST_DB == live:
        raise RuntimeError("Test database path is live gym.db")


_assert_not_live_db()


@pytest.fixture(scope="session", autouse=True)
def _migrated_seeded_db():
    """Build schema from Alembic and seed the global catalog once."""
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    # Alembic 1.13 reads -x from cmd_opts, not an upgrade() kwarg.
    cfg.cmd_opts = type("opts", (), {"x": [f"db_url={os.environ['DATABASE_URL']}"]})()
    command.upgrade(cfg, "head")
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
    yield
    engine.dispose()
    try:
        os.unlink(_TEST_DB)
    except OSError:
        pass


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user_a(client):
    from tests.helpers import register_login

    return register_login(client, f"a-{uuid.uuid4().hex[:10]}@gmail.com")


@pytest.fixture
def user_b(client):
    from tests.helpers import register_login

    return register_login(client, f"b-{uuid.uuid4().hex[:10]}@gmail.com")
