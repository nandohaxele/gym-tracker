"""Workouts HTTP routes.

All endpoints require JWT authentication via `get_current_user` and are
scoped to the authenticated user's own workouts. Child resources are
resolved through the parent Session so another user can never mutate
someone else's WorkoutExercise or Set.

Endpoints (mounted under /api by main.py):
    GET    /workouts
    GET    /workouts/active
    POST   /workouts
    GET    /workouts/{workout_id}
    PUT    /workouts/{workout_id}
    PATCH  /workouts/{workout_id}
    DELETE /workouts/{workout_id}
    POST   /workouts/{workout_id}/complete
    POST   /workouts/{workout_id}/exercises
    POST   /workouts/{workout_id}/exercises/reorder
    DELETE /workout-exercises/{workout_exercise_id}
    POST   /workout-exercises/{workout_exercise_id}/sets
    POST   /workout-exercises/{workout_exercise_id}/sets/reorder
    PATCH  /sets/{set_id}
    DELETE /sets/{set_id}
"""

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.workouts import service
from app.templates import service as templates_service
from app.templates.schemas import TemplateDetail, TemplateNameIn
from app.workouts.schemas import (
    ReorderIn,
    SetIn,
    SetOut,
    SetPatch,
    WorkoutCreate,
    WorkoutDetail,
    WorkoutExerciseCreate,
    WorkoutExerciseOut,
    WorkoutPatch,
    WorkoutSummary,
    WorkoutUpdate,
)


router = APIRouter()


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


@router.get("/workouts/active")
def list_active_workouts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List the caller's active Sessions. Always a list; never auto-selects."""
    items = service.list_active_workouts(db, current_user.id)
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
    """Reconcile a workout's scalars and nested tree without recreating matched ids."""
    workout = service.update_workout(db, current_user.id, workout_id, payload)
    return ok(WorkoutDetail.model_validate(workout))


@router.patch("/workouts/{workout_id}")
def patch_workout(
    workout_id: int,
    payload: WorkoutPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update Session name/date only."""
    workout = service.patch_workout(db, current_user.id, workout_id, payload)
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


@router.post("/workouts/{workout_id}/complete")
def complete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Set ended_at once. Later edits and repeat calls leave it unchanged."""
    workout = service.complete_workout(db, current_user.id, workout_id)
    return ok(WorkoutDetail.model_validate(workout))


@router.post(
    "/workouts/{workout_id}/exercises",
    status_code=status.HTTP_201_CREATED,
)
def add_workout_exercise(
    workout_id: int,
    payload: WorkoutExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Attach one catalog exercise to a Session. Creates zero Sets."""
    row = service.add_workout_exercise(
        db, current_user.id, workout_id, payload
    )
    return ok(WorkoutExerciseOut.model_validate(row))


@router.post("/workouts/{workout_id}/exercises/reorder")
def reorder_workout_exercises(
    workout_id: int,
    payload: ReorderIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Reorder Session exercises. IDs and Sets are unchanged."""
    workout = service.reorder_workout_exercises(
        db, current_user.id, workout_id, payload
    )
    return ok(WorkoutDetail.model_validate(workout))


@router.delete("/workout-exercises/{workout_exercise_id}")
def delete_workout_exercise(
    workout_exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Remove one Session exercise and its Sets. Compact remaining order."""
    service.delete_workout_exercise(db, current_user.id, workout_exercise_id)
    return ok(None)


@router.post(
    "/workout-exercises/{workout_exercise_id}/sets",
    status_code=status.HTTP_201_CREATED,
)
def add_set(
    workout_exercise_id: int,
    payload: SetIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create one Set on a WorkoutExercise."""
    row = service.add_set(db, current_user.id, workout_exercise_id, payload)
    return ok(SetOut.model_validate(row))


@router.post("/workout-exercises/{workout_exercise_id}/sets/reorder")
def reorder_sets(
    workout_exercise_id: int,
    payload: ReorderIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Reorder Sets under one WorkoutExercise. IDs are unchanged."""
    row = service.reorder_sets(
        db, current_user.id, workout_exercise_id, payload
    )
    return ok(WorkoutExerciseOut.model_validate(row))


@router.patch("/sets/{set_id}")
def patch_set(
    set_id: int,
    payload: SetPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Partial-update one Set. Does not recreate siblings."""
    row = service.patch_set(db, current_user.id, set_id, payload)
    return ok(SetOut.model_validate(row))


@router.delete("/sets/{set_id}")
def delete_set(
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete one Set. Compact remaining sibling order_index values."""
    service.delete_set(db, current_user.id, set_id)
    return ok(None)


@router.post(
    "/workouts/{workout_id}/save-as-template",
    status_code=status.HTTP_201_CREATED,
)
def save_workout_as_template(
    workout_id: int,
    payload: TemplateNameIn | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Derive a personal template from actually recorded Sets."""
    name = payload.name if payload is not None else None
    template = templates_service.create_template_from_workout(
        db, current_user.id, workout_id, name=name
    )
    return ok(TemplateDetail.model_validate(template))
