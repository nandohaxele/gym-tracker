"""Exercises service layer."""

from sqlalchemy.orm import Session

from app.exercises.models import Exercise


def list_exercises(db: Session) -> list[Exercise]:
    """Return all seeded exercises ordered by muscle_group then name."""
    return (
        db.query(Exercise)
        .order_by(Exercise.muscle_group.asc(), Exercise.name.asc())
        .all()
    )
