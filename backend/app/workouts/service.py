"""Workouts service layer.

Pure business logic -- never imports FastAPI primitives. All operations are
scoped by `user_id` so users can only see/edit their own data.

N+1 strategy:
    - `list_workouts` returns flat rows (no exercise/set loading).
    - `get_workout` uses `selectinload` to load the full tree in 3 queries
      (workout, exercises, sets) + 1 for the exercise catalog refs.
"""

from collections import defaultdict, deque
from datetime import date as _date
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.exercises import service as exercises_service
from app.exercises.models import ExerciseTracking
from app.workouts.models import Set, Workout, WorkoutExercise
from app.workouts.schemas import (
    WorkoutCreate,
    WorkoutExerciseIn,
    WorkoutUpdate,
)

_EMPTY_PLANNED: dict[str, None] = {
    "planned_sets": None,
    "planned_reps_min": None,
    "planned_reps_max": None,
    "planned_duration_seconds_min": None,
    "planned_duration_seconds_max": None,
    "planned_distance_meters_min": None,
    "planned_distance_meters_max": None,
}

# Exercise tracking type -> Set column that must be present on write.
# Weight is not a tracking type and is never required by this map.
_PRIMARY_SET_FIELD = {
    "reps": "reps",
    "duration": "duration_seconds",
    "distance": "distance_meters",
}


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

def _validate_exercise_ids(
    db: Session, user_id: int, exercise_ids: set[int]
) -> None:
    """Ensure every referenced exercise_id is one the user may actually select.

    Valid means active and either global or personally owned. Unknown ids,
    archived personal exercises and other users' exercises are all reported the
    same way, so the error never reveals that someone else's exercise exists.

    Only writes go through here: `get_workout` deliberately does not filter, so
    history that references a since-archived exercise stays readable and is never
    rewritten.

    Single batched query -- avoids N round-trips when validating large trees.
    """
    if not exercise_ids:
        return

    found = exercises_service.selectable_exercise_ids(db, user_id, exercise_ids)
    missing = exercise_ids - found
    if missing:
        raise ValidationError(f"Unknown exercise_id(s): {sorted(missing)}")


def _primary_tracking_by_exercise_id(
    db: Session, exercise_ids: set[int]
) -> dict[int, str]:
    """Return the primary tracking type for each requested exercise_id."""
    if not exercise_ids:
        return {}
    rows = (
        db.query(ExerciseTracking.exercise_id, ExerciseTracking.tracking_type)
        .filter(
            ExerciseTracking.exercise_id.in_(exercise_ids),
            ExerciseTracking.is_primary.is_(True),
        )
        .all()
    )
    return {exercise_id: tracking_type for exercise_id, tracking_type in rows}


def _validate_set_primary_metrics(
    db: Session, items: list[WorkoutExerciseIn]
) -> None:
    """Require each recorded Set to carry the parent Exercise's primary metric.

    Secondary metrics stay optional. `weight_kg` is never required here — it
    is not a tracking type. Historical rows that lack a primary metric are
    not run through this function; only create/update writes are.

    `get_workout` deliberately does not call this, so pre-Phase-3 history
    (e.g. the plank set that stored duration in `reps`) stays readable.
    """
    recorded = [ex for ex in items if ex.sets]
    if not recorded:
        return

    exercise_ids = {ex.exercise_id for ex in recorded}
    primary_by_id = _primary_tracking_by_exercise_id(db, exercise_ids)

    missing_tracking = sorted(exercise_ids - primary_by_id.keys())
    if missing_tracking:
        raise ValidationError(
            f"Exercise(s) missing primary tracking: {missing_tracking}"
        )

    failures: list[str] = []
    for ex_in in recorded:
        field = _PRIMARY_SET_FIELD[primary_by_id[ex_in.exercise_id]]
        for index, s_in in enumerate(ex_in.sets):
            if getattr(s_in, field) is None:
                failures.append(
                    f"exercise_id {ex_in.exercise_id} set[{index}] requires {field}"
                )
    if failures:
        raise ValidationError(
            "Set is missing the exercise primary tracking metric: "
            + "; ".join(failures)
        )


def _planned_from_input(ex_in: WorkoutExerciseIn) -> dict:
    return {
        "planned_sets": ex_in.planned_sets,
        "planned_reps_min": ex_in.planned_reps_min,
        "planned_reps_max": ex_in.planned_reps_max,
        "planned_duration_seconds_min": ex_in.planned_duration_seconds_min,
        "planned_duration_seconds_max": ex_in.planned_duration_seconds_max,
        "planned_distance_meters_min": ex_in.planned_distance_meters_min,
        "planned_distance_meters_max": ex_in.planned_distance_meters_max,
    }


def _planned_from_row(row: WorkoutExercise) -> dict:
    return {
        "planned_sets": row.planned_sets,
        "planned_reps_min": row.planned_reps_min,
        "planned_reps_max": row.planned_reps_max,
        "planned_duration_seconds_min": row.planned_duration_seconds_min,
        "planned_duration_seconds_max": row.planned_duration_seconds_max,
        "planned_distance_meters_min": row.planned_distance_meters_min,
        "planned_distance_meters_max": row.planned_distance_meters_max,
    }


def _planned_buckets(workout: Workout) -> dict[int, deque[dict]]:
    """Group existing planned snapshots by exercise_id, in current order.

    Sequential same-id matching is deterministic even when a Session repeats
    an exercise: the first incoming row with that id takes the first stored
    snapshot, the next takes the next, extras become NULL.
    """
    buckets: dict[int, deque[dict]] = defaultdict(deque)
    for row in workout.exercises:
        buckets[row.exercise_id].append(_planned_from_row(row))
    return buckets


def _resolve_planned(
    ex_in: WorkoutExerciseIn,
    buckets: Optional[dict[int, deque[dict]]] = None,
) -> dict:
    """Use an explicit payload snapshot, else consume a preserved one."""
    if ex_in.planned_explicitly_set():
        return _planned_from_input(ex_in)
    if buckets is not None and buckets[ex_in.exercise_id]:
        return buckets[ex_in.exercise_id].popleft()
    return dict(_EMPTY_PLANNED)


def _build_exercise_tree(
    items: list[WorkoutExerciseIn],
    planned_buckets: Optional[dict[int, deque[dict]]] = None,
) -> list[WorkoutExercise]:
    """Translate the nested input payload into ORM instances.

    `order_index` defaults to the array position when not provided, so the
    client can rely on insertion order without computing indexes itself.

    On PUT, `planned_buckets` supplies Session snapshot values the current
    frontend does not send, so the destructive child rebuild does not erase
    planned_* copied at Template Start.
    """
    rows: list[WorkoutExercise] = []
    for ex_idx, ex_in in enumerate(items):
        planned = _resolve_planned(ex_in, planned_buckets)
        we = WorkoutExercise(
            exercise_id=ex_in.exercise_id,
            order_index=ex_in.order_index if ex_in.order_index is not None else ex_idx,
            **planned,
        )
        for s_idx, s_in in enumerate(ex_in.sets):
            we.sets.append(
                Set(
                    reps=s_in.reps,
                    weight_kg=s_in.weight_kg,
                    duration_seconds=s_in.duration_seconds,
                    distance_meters=s_in.distance_meters,
                    rpe=s_in.rpe,
                    rir=s_in.rir,
                    set_type=s_in.set_type.value,
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
            db, user_id, {ex.exercise_id for ex in payload.exercises}
        )
        _validate_set_primary_metrics(db, payload.exercises)

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
            db, user_id, {ex.exercise_id for ex in payload.exercises}
        )
        _validate_set_primary_metrics(db, payload.exercises)

    workout.name = payload.name
    if payload.date is not None:
        workout.date = payload.date

    # Reassigning the collection orphans the old children -> delete-orphan
    # cascade removes them on flush, taking their Sets along via the
    # WorkoutExercise.sets cascade. planned_* is copied off the old rows
    # first so a frontend that does not send those fields cannot erase the
    # Template Start snapshot. source_template_id is a scalar on Workout
    # and is not part of this payload, so provenance is left intact.
    planned_buckets = _planned_buckets(workout)
    workout.exercises = _build_exercise_tree(payload.exercises, planned_buckets)

    db.commit()
    return get_workout(db, user_id, workout_id)


def delete_workout(db: Session, user_id: int, workout_id: int) -> None:
    """Delete a workout and (via cascade) its nested exercises and sets."""
    workout = get_workout(db, user_id, workout_id)
    db.delete(workout)
    db.commit()
