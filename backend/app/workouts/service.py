"""Workouts service layer.

Pure business logic -- never imports FastAPI primitives. All operations are
scoped by `user_id` so users can only see/edit their own data.

N+1 strategy:
    - `list_workouts` returns flat rows (no exercise/set loading).
    - `get_workout` uses `selectinload` to load the full tree in 3 queries
      (workout, exercises, sets) + 1 for the exercise catalog refs.
"""

from datetime import date as _date

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.exercises.models import Exercise
from app.workouts.models import Set, Workout, WorkoutExercise
from app.workouts.schemas import (
    WorkoutCreate,
    WorkoutExerciseIn,
    WorkoutUpdate,
)


# ---- Read ---------------------------------------------------------------

def list_workouts(db: Session, user_id: int) -> list[Workout]:
    """Return all workouts owned by `user_id`, newest first.

    TODO (future): accept `limit` / `offset` (or cursor) for pagination once
    workout histories grow. For now we return everything.
    """
    return (
        db.query(Workout)
        .filter(Workout.user_id == user_id)
        .order_by(Workout.date.desc(), Workout.created_at.desc())
        .all()
    )


def get_workout(db: Session, user_id: int, workout_id: int) -> Workout:
    """Load a workout with its full nested tree, scoped to `user_id`.

    Raises NotFoundError both when the workout does not exist and when it
    belongs to another user -- we intentionally do not differentiate the two
    cases to avoid leaking existence of resources across accounts.
    """
    workout = (
        db.query(Workout)
        .options(
            selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
            selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
        )
        .filter(Workout.id == workout_id, Workout.user_id == user_id)
        .first()
    )
    if workout is None:
        raise NotFoundError("Workout not found")
    return workout


# ---- Helpers ------------------------------------------------------------

def _validate_exercise_ids(db: Session, exercise_ids: set[int]) -> None:
    """Ensure every referenced exercise_id exists in the catalog.

    Single batched query -- avoids N round-trips when validating large trees.
    """
    if not exercise_ids:
        return

    found_rows = (
        db.query(Exercise.id).filter(Exercise.id.in_(exercise_ids)).all()
    )
    found = {row[0] for row in found_rows}
    missing = exercise_ids - found
    if missing:
        raise ValidationError(f"Unknown exercise_id(s): {sorted(missing)}")


def _build_exercise_tree(items: list[WorkoutExerciseIn]) -> list[WorkoutExercise]:
    """Translate the nested input payload into ORM instances.

    `order_index` defaults to the array position when not provided, so the
    client can rely on insertion order without computing indexes itself.
    """
    rows: list[WorkoutExercise] = []
    for ex_idx, ex_in in enumerate(items):
        we = WorkoutExercise(
            exercise_id=ex_in.exercise_id,
            order_index=ex_in.order_index if ex_in.order_index is not None else ex_idx,
        )
        for s_idx, s_in in enumerate(ex_in.sets):
            we.sets.append(
                Set(
                    reps=s_in.reps,
                    weight=s_in.weight,
                    order_index=s_in.order_index
                    if s_in.order_index is not None
                    else s_idx,
                )
            )
        rows.append(we)
    return rows


# ---- Write --------------------------------------------------------------

def create_workout(db: Session, user_id: int, payload: WorkoutCreate) -> Workout:
    """Create a workout with optional nested exercises and sets."""
    if payload.exercises:
        _validate_exercise_ids(
            db, {ex.exercise_id for ex in payload.exercises}
        )

    workout = Workout(
        user_id=user_id,
        name=payload.name,
        date=payload.date or _date.today(),
    )
    workout.exercises = _build_exercise_tree(payload.exercises)

    db.add(workout)
    db.commit()

    # Re-fetch via get_workout to return a fully hydrated tree (matches PUT/GET).
    return get_workout(db, user_id, workout.id)


def update_workout(
    db: Session,
    user_id: int,
    workout_id: int,
    payload: WorkoutUpdate,
) -> Workout:
    """Replace a workout's scalar fields and its entire nested exercises/sets.

    Relies on `cascade="all, delete-orphan"` to drop the previous nested rows
    when we reassign `workout.exercises`. Safer than manual delete loops --
    SQLAlchemy emits the right DELETE order on flush.
    """
    workout = get_workout(db, user_id, workout_id)

    if payload.exercises:
        _validate_exercise_ids(
            db, {ex.exercise_id for ex in payload.exercises}
        )

    workout.name = payload.name
    if payload.date is not None:
        workout.date = payload.date

    # Reassigning the collection orphans the old children -> delete-orphan
    # cascade removes them on flush, taking their Sets along via the
    # WorkoutExercise.sets cascade.
    workout.exercises = _build_exercise_tree(payload.exercises)

    db.commit()
    return get_workout(db, user_id, workout_id)


def delete_workout(db: Session, user_id: int, workout_id: int) -> None:
    """Delete a workout and (via cascade) its nested exercises and sets."""
    workout = get_workout(db, user_id, workout_id)
    db.delete(workout)
    db.commit()
