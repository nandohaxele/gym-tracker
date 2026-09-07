"""Fresh Alembic path and defensive downgrade on scratch DBs only."""

import os
import pathlib
import subprocess
import tempfile

import pytest
from sqlalchemy import create_engine, text

BACKEND = pathlib.Path(__file__).resolve().parents[1]
HEAD = "0153e917bf85"
EXPECTED_TABLES = {
    "alembic_version",
    "users",
    "exercises",
    "exercise_tracking",
    "exercise_synonyms",
    "workouts",
    "workout_exercises",
    "sets",
    "templates",
    "template_exercises",
}


def _alembic(db_url: str, *args: str) -> subprocess.CompletedProcess:
    python = BACKEND / ".venv" / "Scripts" / "python.exe"
    exe = str(python) if python.exists() else "python"
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    return subprocess.run(
        [exe, "-m", "alembic", "-x", f"db_url={db_url}", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_fresh_upgrade_head_has_expected_tables_and_sole_head():
    fd, path = tempfile.mkstemp(prefix="gym-tracker-migrate-", suffix=".db")
    os.close(fd)
    url = f"sqlite:///{pathlib.Path(path).as_posix()}"
    try:
        upgraded = _alembic(url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        current = _alembic(url, "current")
        assert HEAD in current.stdout
        heads = _alembic(url, "heads")
        assert heads.stdout.count(HEAD) == 1
        check = _alembic(url, "check")
        assert check.returncode == 0, check.stderr + check.stdout

        engine = create_engine(url)
        with engine.connect() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            assert EXPECTED_TABLES <= tables
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert version == HEAD
        engine.dispose()

        downgraded = _alembic(url, "downgrade", "f3f47238398b")
        assert downgraded.returncode == 0, downgraded.stderr
        reup = _alembic(url, "upgrade", "head")
        assert reup.returncode == 0, reup.stderr
    finally:
        os.unlink(path)


def test_head_downgrade_refuses_non_sentinel_clocks():
    fd, path = tempfile.mkstemp(prefix="gym-tracker-migrate-dirty-", suffix=".db")
    os.close(fd)
    url = f"sqlite:///{pathlib.Path(path).as_posix()}"
    try:
        assert _alembic(url, "upgrade", "head").returncode == 0
        engine = create_engine(url)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (email, hashed_password, created_at) "
                    "VALUES ('x@test.local', 'x', '2026-09-07 00:00:00')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO workouts "
                    "(user_id, name, date, created_at, started_at, ended_at) "
                    "VALUES (1, 'Live', '2026-09-07', '2026-09-07 00:00:00', "
                    "'2026-09-07 10:00:00', NULL)"
                )
            )
        engine.dispose()
        refused = _alembic(url, "downgrade", "68505223da63")
        assert refused.returncode != 0
        assert "Refusing to downgrade" in (refused.stderr + refused.stdout)
    finally:
        os.unlink(path)
