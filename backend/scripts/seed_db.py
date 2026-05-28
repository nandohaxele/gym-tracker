"""CLI entrypoint to seed the database with predefined exercises.

Usage (from the `backend/` directory):
    python -m scripts.seed_db
"""

# Importing the model modules registers them on Base.metadata before create_all.
from app.auth import models as _auth_models  # noqa: F401
from app.core.database import Base, SessionLocal, engine
from app.exercises import models as _exercises_models  # noqa: F401
from app.seed.seeder import run_seed


def main() -> None:
    """Open a session, ensure tables exist, run the seeder, log results."""
    # TODO (future): replace create_all with Alembic migrations once added.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        inserted = run_seed(db)
        print(f"Seed complete. Inserted {inserted} new exercise(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
