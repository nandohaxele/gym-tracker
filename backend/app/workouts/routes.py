"""Workouts HTTP routes.

All endpoints require JWT authentication via `get_current_user` and are
scoped to the authenticated user's own workouts.

Endpoints (mounted under /api by main.py):
    GET    /workouts
    POST   /workouts
    GET    /workouts/{workout_id}
    PUT    /workouts/{workout_id}
    DELETE /workouts/{workout_id}
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.workouts import service
from app.workouts.schemas import (
    WorkoutCreate,
    WorkoutDetail,
    WorkoutSummary,
    WorkoutUpdate,
)


router = APIRouter()


# TODO (future): support workout templates -- a separate POST /workouts/templates
# endpoint that persists a Workout-like record flagged as a template, plus
# POST /workouts/from-template/{template_id} to clone it into a dated workout
# for the current day.


@router.get("/workouts")
def list_workouts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List the authenticated user's workouts, newest first.

    TODO (future): accept `?limit=&offset=` query params once histories grow.
    """
    items = service.list_workouts(db, current_user.id)
    return ok([WorkoutSummary.model_validate(w) for w in items])


@router.post("/workouts", status_code=status.HTTP_201_CREATED)
def create_workout(
    payload: WorkoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new workout, optionally with nested exercises and sets."""
    workout = service.create_workout(db, current_user.id, payload)
    return ok(WorkoutDetail.model_validate(workout))


@router.get("/workouts/{workout_id}")
def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Fetch a single workout owned by the current user, with full nested data."""
    workout = service.get_workout(db, current_user.id, workout_id)
    return ok(WorkoutDetail.model_validate(workout))


@router.put("/workouts/{workout_id}")
def update_workout(
    workout_id: int,
    payload: WorkoutUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Fully replace a workout's fields and nested exercises/sets."""
    workout = service.update_workout(db, current_user.id, workout_id, payload)
    return ok(WorkoutDetail.model_validate(workout))


@router.delete("/workouts/{workout_id}")
def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a workout (and its nested entities, via cascade).

    Returns 200 with the standard envelope -- intentionally avoids 204 so the
    `{ success, data, error }` shape stays consistent across the whole API.
    """
    service.delete_workout(db, current_user.id, workout_id)
    return ok(None)
