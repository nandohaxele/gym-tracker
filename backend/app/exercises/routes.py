"""Exercises HTTP routes.

Endpoints (mounted under /api/exercises by main.py, all auth required):
    GET    /exercises                        global + own active exercises
    GET    /exercises/last-weights           latest load per exercise id
    POST   /exercises                        create a personal exercise
    PATCH  /exercises/{exercise_id}          update a personal exercise
    POST   /exercises/{exercise_id}/archive  soft-archive a personal exercise

There is no DELETE: archiving is a soft state change, because historical
WorkoutExercise rows must keep resolving. Archiving is idempotent, and there is
deliberately no restore endpoint in this phase.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationError
from app.core.response import ok
from app.exercises import service
from app.exercises.schemas import (
    ExerciseCreate,
    ExerciseOut,
    ExerciseUpdate,
    LastWeightOut,
)


router = APIRouter()


@router.get("")
def list_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List the global catalog plus the caller's own active personal exercises."""
    items = service.list_exercises(db, current_user.id)
    return ok([ExerciseOut.model_validate(item) for item in items])


@router.get("/last-weights")
def last_weights(
    ids: str = Query(default="", description="Comma-separated exercise ids."),
    exclude_workout_id: Optional[int] = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Latest recorded weight_kg per requested exercise, from the caller's history."""
    exercise_ids: list[int] = []
    for part in ids.split(","):
        token = part.strip()
        if not token:
            continue
        if not token.isdigit() or int(token) <= 0:
            raise ValidationError(
                "ids must be a comma-separated list of positive integers"
            )
        exercise_ids.append(int(token))
    rows = service.last_weights(
        db, current_user.id, exercise_ids, exclude_workout_id=exclude_workout_id
    )
    return ok(
        [
            LastWeightOut(exercise_id=exercise_id, weight_kg=weight_kg)
            for exercise_id, weight_kg in rows
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_exercise(
    payload: ExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a personal exercise owned by the caller."""
    exercise = service.create_personal_exercise(db, current_user.id, payload)
    return ok(ExerciseOut.model_validate(exercise))


@router.patch("/{exercise_id}")
def update_exercise(
    exercise_id: int,
    payload: ExerciseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update one of the caller's personal exercises."""
    exercise = service.update_personal_exercise(
        db, current_user.id, exercise_id, payload
    )
    return ok(ExerciseOut.model_validate(exercise))


@router.post("/{exercise_id}/archive")
def archive_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Soft-archive one of the caller's personal exercises."""
    exercise = service.archive_personal_exercise(db, current_user.id, exercise_id)
    return ok(ExerciseOut.model_validate(exercise))
