"""CLI entrypoint to seed the database with predefined exercises.

Usage (from the `backend/` directory):
    alembic upgrade head
    python -m scripts.seed_db
"""

from sqlalchemy import inspect

# Importing the model modules registers every mapper. All three are required:
# User.workouts references "Workout" by name, so omitting the workouts module
# makes mapper configuration fail on the first query.
from app.auth import models as _auth_models  # noqa: F401
from app.core.database import SessionLocal, engine
from app.exercises import models as _exercises_models  # noqa: F401
from app.workouts import models as _workouts_models  # noqa: F401
from app.seed.seeder import run_seed


def main() -> None:
    """Open a session, run the seeder, log results."""
    # Tables are created by Alembic, so a missing one means migrations have not
    # been applied. Fail with that instruction rather than a raw OperationalError.
    if not inspect(engine).has_table("exercises"):
        raise SystemExit(
            "Table 'exercises' is missing. Run `alembic upgrade head` from "
            "backend/ before seeding."
        )

    db = SessionLocal()
    try:
        inserted = run_seed(db)
        print(f"Seed complete. Inserted {inserted} new exercise(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
