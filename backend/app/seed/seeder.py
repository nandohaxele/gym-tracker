"""Idempotent seeder for predefined exercises.

Inserts any exercise from PREDEFINED_EXERCISES that doesn't already exist
(matched by `name`). Safe to re-run any time.
"""

from sqlalchemy.orm import Session

from app.exercises.models import Exercise
from app.seed.exercises_seed import PREDEFINED_EXERCISES


def run_seed(db: Session) -> int:
    """Upsert predefined exercises. Returns the number of new rows inserted."""
    existing_names = {name for (name,) in db.query(Exercise.name).all()}

    inserted = 0
    for item in PREDEFINED_EXERCISES:
        if item["name"] in existing_names:
            continue
        db.add(Exercise(name=item["name"], muscle_group=item["muscle_group"]))
        inserted += 1

    if inserted:
        db.commit()
    return inserted
