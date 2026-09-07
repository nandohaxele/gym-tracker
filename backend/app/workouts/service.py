"""Workouts service layer.

Pure business logic -- never imports FastAPI primitives. All operations are
scoped by `user_id` so users can only see/edit their own data.

Child writes keep existing WorkoutExercise / Set primary keys. Collection
reassignment is used only when the replacement list contains the same ORM
instances for matched rows, so delete-orphan removes omitted children only.
"""

from datetime import date as _date
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.core.utc import date_midnight_utc, utc_now
from app.exercises import service as exercises_service
from app.exercises.models import Exercise, ExerciseTracking
from app.workouts.models import Set, Workout, WorkoutExercise
from app.workouts.schemas import (
    ReorderIn,
    SetIn,
    SetPatch,
    WorkoutCreate,
    WorkoutExerciseCreate,
    WorkoutExerciseIn,
    WorkoutPatch,
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


def _workout_detail_options():
    return (
        selectinload(Workout.exercises)
        .selectinload(WorkoutExercise.exercise)
        .selectinload(Exercise.tracking),
        selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
    )


def _workout_exercise_options():
    return (
        selectinload(WorkoutExercise.exercise).selectinload(Exercise.tracking),
        selectinload(WorkoutExercise.sets),
    )


def get_workout(db: Session, user_id: int, workout_id: int) -> Workout:
    """Load a workout with its full nested tree, scoped to `user_id`.

    Raises NotFoundError both when the workout does not exist and when it
    belongs to another user -- we intentionally do not differentiate the two
    cases to avoid leaking existence of resources across accounts.
    """
    workout = (
        db.query(Workout)
        .execution_options(populate_existing=True)
        .options(*_workout_detail_options())
        .filter(Workout.id == workout_id, Workout.user_id == user_id)
        .first()
    )
    if workout is None:
        raise NotFoundError("Workout not found")
    return workout


def get_workout_exercise(
    db: Session, user_id: int, workout_exercise_id: int
) -> WorkoutExercise:
    """Load one WorkoutExercise owned by `user_id` via its parent Session."""
    row = (
        db.query(WorkoutExercise)
        .execution_options(populate_existing=True)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .options(*_workout_exercise_options())
        .filter(
            WorkoutExercise.id == workout_exercise_id,
            Workout.user_id == user_id,
        )
        .first()
    )
    if row is None:
        raise NotFoundError("Workout exercise not found")
    return row


def get_set(db: Session, user_id: int, set_id: int) -> Set:
    """Load one Set owned by `user_id` via WorkoutExercise → Workout."""
    row = (
        db.query(Set)
        .execution_options(populate_existing=True)
        .join(WorkoutExercise, WorkoutExercise.id == Set.workout_exercise_id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .options(selectinload(Set.workout_exercise))
        .filter(Set.id == set_id, Workout.user_id == user_id)
        .first()
    )
    if row is None:
        raise NotFoundError("Set not found")
    return row


# ---- Helpers ------------------------------------------------------------

def _validate_exercise_ids(
    db: Session, user_id: int, exercise_ids: set[int]
) -> None:
    """Ensure every referenced exercise_id is one the user may actually select.

    Valid means active and either global or personally owned. Unknown ids,
    archived personal exercises and other users' exercises are all reported the
    same way, so the error never reveals that someone else's exercise exists.

    Only new attaches go through here: history that already references a
    since-archived exercise stays readable and its Sets stay editable.
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
    """Require each recorded Set to carry the parent Exercise's primary metric."""
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


def _primary_field_for(db: Session, exercise_id: int) -> str:
    primary_by_id = _primary_tracking_by_exercise_id(db, {exercise_id})
    if exercise_id not in primary_by_id:
        raise ValidationError(
            f"Exercise(s) missing primary tracking: [{exercise_id}]"
        )
    return _PRIMARY_SET_FIELD[primary_by_id[exercise_id]]


def _assert_set_primary(
    db: Session,
    exercise_id: int,
    reps,
    duration_seconds,
    distance_meters,
    *,
    grandfather: bool = False,
) -> None:
    """Require the parent Exercise primary metric on one Set write."""
    field = _primary_field_for(db, exercise_id)
    values = {
        "reps": reps,
        "duration_seconds": duration_seconds,
        "distance_meters": distance_meters,
    }
    if values[field] is None:
        if grandfather:
            return
        raise ValidationError(
            "Set is missing the exercise primary tracking metric: "
            f"exercise_id {exercise_id} requires {field}"
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


def _compact(rows) -> None:
    """Normalize order_index to compact 0..N, preserving current relative order."""
    ordered = sorted(rows, key=lambda row: (row.order_index, row.id or 0))
    for index, row in enumerate(ordered):
        row.order_index = index


def _insert_and_compact(rows: list, new_row, index: Optional[int]) -> None:
    ordered = sorted(rows, key=lambda row: (row.order_index, row.id or 0))
    if new_row in ordered:
        ordered.remove(new_row)
    target = len(ordered) if index is None else max(0, min(index, len(ordered)))
    ordered.insert(target, new_row)
    for i, row in enumerate(ordered):
        row.order_index = i


def _apply_reorder(rows: list, ids: list[int], label: str) -> None:
    existing = [row.id for row in rows]
    if sorted(ids) != sorted(existing):
        raise ValidationError(
            f"{label} ids must be a permutation of the existing items"
        )
    by_id = {row.id: row for row in rows}
    for index, row_id in enumerate(ids):
        by_id[row_id].order_index = index


def _new_set(s_in: SetIn, index: int) -> Set:
    return Set(
        reps=s_in.reps,
        weight_kg=s_in.weight_kg,
        duration_seconds=s_in.duration_seconds,
        distance_meters=s_in.distance_meters,
        rpe=s_in.rpe,
        rir=s_in.rir,
        set_type=s_in.set_type.value,
        order_index=s_in.order_index if s_in.order_index is not None else index,
    )


def _apply_set_in(row: Set, s_in: SetIn, index: int) -> None:
    """Merge explicitly provided SetIn fields onto an existing row."""
    provided = s_in.model_fields_set
    if "reps" in provided:
        row.reps = s_in.reps
    if "weight_kg" in provided:
        row.weight_kg = s_in.weight_kg
    if "duration_seconds" in provided:
        row.duration_seconds = s_in.duration_seconds
    if "distance_meters" in provided:
        row.distance_meters = s_in.distance_meters
    if "rpe" in provided:
        row.rpe = s_in.rpe
    if "rir" in provided:
        row.rir = s_in.rir
    if "set_type" in provided:
        row.set_type = s_in.set_type.value
    row.order_index = s_in.order_index if s_in.order_index is not None else index


def _build_exercise_tree(items: list[WorkoutExerciseIn]) -> list[WorkoutExercise]:
    """Translate a create payload into new ORM instances."""
    rows: list[WorkoutExercise] = []
    for ex_idx, ex_in in enumerate(items):
        planned = (
            _planned_from_input(ex_in)
            if ex_in.planned_explicitly_set()
            else dict(_EMPTY_PLANNED)
        )
        we = WorkoutExercise(
            exercise_id=ex_in.exercise_id,
            order_index=ex_in.order_index if ex_in.order_index is not None else ex_idx,
            **planned,
        )
        for s_idx, s_in in enumerate(ex_in.sets):
            we.sets.append(_new_set(s_in, s_idx))
        rows.append(we)
    return rows


def _duplicate_values(values: list[int]) -> bool:
    return len(values) != len(set(values))


def _legacy_we_fallback_ok(
    items: list[WorkoutExerciseIn], existing: list[WorkoutExercise]
) -> bool:
    """ID-less WE matching is safe only when every exercise_id is unique."""
    incoming = [ex.exercise_id for ex in items]
    current = [row.exercise_id for row in existing]
    return not _duplicate_values(incoming) and not _duplicate_values(current)


def _match_workout_exercises(
    items: list[WorkoutExerciseIn], existing: list[WorkoutExercise]
) -> list[Optional[WorkoutExercise]]:
    """Resolve each incoming WE to an existing row or None (insert).

    IDs are authoritative. A supplied id that is not a child of this Session
    is NotFoundError so foreign ids never leak via 403. When every incoming
    row omits id, a temporary sequential same-exercise fallback is used only
    if both sides have unique exercise_ids. Any other ID-less structure is
    rejected rather than guessing.
    """
    existing_by_id = {row.id: row for row in existing}
    supplied = [ex.id is not None for ex in items]
    if any(supplied) and not all(supplied):
        # Mixed: omitted ids are new rows; supplied ids must belong here.
        matches: list[Optional[WorkoutExercise]] = []
        used: set[int] = set()
        for ex_in in items:
            if ex_in.id is None:
                matches.append(None)
                continue
            candidate = existing_by_id.get(ex_in.id)
            if candidate is None:
                raise NotFoundError("Workout exercise not found")
            if candidate.id in used:
                raise ValidationError("Duplicate WorkoutExercise id in payload")
            used.add(candidate.id)
            matches.append(candidate)
        return matches

    if all(supplied):
        matches = []
        used: set[int] = set()
        for ex_in in items:
            candidate = existing_by_id.get(ex_in.id)
            if candidate is None:
                raise NotFoundError("Workout exercise not found")
            if candidate.id in used:
                raise ValidationError("Duplicate WorkoutExercise id in payload")
            used.add(candidate.id)
            matches.append(candidate)
        return matches

    # All ids omitted: legacy compatibility fallback (Phase 7 debt).
    # The live editor sends child ids. Ambiguous ID-less trees reject.
    if not _legacy_we_fallback_ok(items, existing):
        raise ValidationError(
            "Cannot reconcile workout exercises without ids when the same "
            "exercise appears more than once. Send WorkoutExercise ids."
        )
    by_exercise = {row.exercise_id: row for row in existing}
    return [by_exercise.get(ex_in.exercise_id) for ex_in in items]


def _match_sets(
    incoming: list[SetIn], existing: list[Set]
) -> list[Optional[Set]]:
    existing_by_id = {row.id: row for row in existing}
    supplied = [s.id is not None for s in incoming]
    if any(supplied) and not all(supplied):
        matches: list[Optional[Set]] = []
        used: set[int] = set()
        for s_in in incoming:
            if s_in.id is None:
                matches.append(None)
                continue
            candidate = existing_by_id.get(s_in.id)
            if candidate is None:
                raise NotFoundError("Set not found")
            if candidate.id in used:
                raise ValidationError("Duplicate Set id in payload")
            used.add(candidate.id)
            matches.append(candidate)
        return matches

    if all(supplied):
        matches = []
        used: set[int] = set()
        for s_in in incoming:
            candidate = existing_by_id.get(s_in.id)
            if candidate is None:
                raise NotFoundError("Set not found")
            if candidate.id in used:
                raise ValidationError("Duplicate Set id in payload")
            used.add(candidate.id)
            matches.append(candidate)
        return matches

    if len(incoming) != len(existing):
        raise ValidationError(
            "Cannot reconcile sets without ids when the set count changes. "
            "Send Set ids."
        )
    ordered = sorted(existing, key=lambda row: (row.order_index, row.id))
    return ordered


def _new_attach_exercise_ids(
    items: list[WorkoutExerciseIn], matches: list[Optional[WorkoutExercise]]
) -> set[int]:
    return {
        ex_in.exercise_id
        for ex_in, matched in zip(items, matches)
        if matched is None
    }


def _reconcile_sets(
    db: Session, we: WorkoutExercise, incoming: list[SetIn]
) -> None:
    matches = _match_sets(incoming, list(we.sets))
    result: list[Set] = []
    for index, (s_in, matched) in enumerate(zip(incoming, matches)):
        if matched is not None:
            primary_field = _primary_field_for(db, we.exercise_id)
            before_primary = getattr(matched, primary_field)
            _apply_set_in(matched, s_in, index)
            _assert_set_primary(
                db,
                we.exercise_id,
                matched.reps,
                matched.duration_seconds,
                matched.distance_meters,
                grandfather=(
                    before_primary is None
                    and primary_field not in s_in.model_fields_set
                ),
            )
            result.append(matched)
        else:
            row = _new_set(s_in, index)
            _assert_set_primary(
                db,
                we.exercise_id,
                row.reps,
                row.duration_seconds,
                row.distance_meters,
            )
            result.append(row)
    we.sets = result
    _compact(we.sets)


def _reconcile_exercises(
    db: Session, workout: Workout, items: list[WorkoutExerciseIn]
) -> list[WorkoutExercise]:
    matches = _match_workout_exercises(items, list(workout.exercises))
    result: list[WorkoutExercise] = []
    for index, (ex_in, matched) in enumerate(zip(items, matches)):
        if matched is not None:
            matched.order_index = (
                ex_in.order_index if ex_in.order_index is not None else index
            )
            if ex_in.planned_explicitly_set():
                for key, value in _planned_from_input(ex_in).items():
                    setattr(matched, key, value)
            _reconcile_sets(db, matched, ex_in.sets)
            result.append(matched)
        else:
            planned = (
                _planned_from_input(ex_in)
                if ex_in.planned_explicitly_set()
                else dict(_EMPTY_PLANNED)
            )
            we = WorkoutExercise(
                exercise_id=ex_in.exercise_id,
                order_index=(
                    ex_in.order_index if ex_in.order_index is not None else index
                ),
                **planned,
            )
            for s_idx, s_in in enumerate(ex_in.sets):
                row = _new_set(s_in, s_idx)
                _assert_set_primary(
                    db,
                    we.exercise_id,
                    row.reps,
                    row.duration_seconds,
                    row.distance_meters,
                )
                we.sets.append(row)
            result.append(we)
    _compact(result)
    return result


# ---- Write --------------------------------------------------------------

def create_workout(db: Session, user_id: int, payload: WorkoutCreate) -> Workout:
    """Create a workout with optional nested exercises and sets.

    Nested Sets are treated as a retrospective log: clocks use the
    date-midnight UTC sentinel (`ended_at = started_at`). No-set creates
    are active (`started_at = utc_now()`, `ended_at` NULL). `date` stays
    the client/local calendar day and is never derived from UTC.
    """
    if payload.exercises:
        _validate_exercise_ids(
            db, user_id, {ex.exercise_id for ex in payload.exercises}
        )
        _validate_set_primary_metrics(db, payload.exercises)

    day = payload.date or _date.today()
    has_sets = any(ex.sets for ex in payload.exercises)
    if has_sets:
        stamp = date_midnight_utc(day)
        started_at, ended_at = stamp, stamp
    else:
        started_at, ended_at = utc_now(), None
    workout = Workout(
        user_id=user_id,
        name=payload.name,
        date=day,
        started_at=started_at,
        ended_at=ended_at,
    )
    workout.exercises = _build_exercise_tree(payload.exercises)

    db.add(workout)
    db.commit()
    return get_workout(db, user_id, workout.id)


def update_workout(
    db: Session,
    user_id: int,
    workout_id: int,
    payload: WorkoutUpdate,
) -> Workout:
    """Reconcile scalars and the nested tree without recreating matched children.

    Child ids are authoritative. Omitted ids are new rows unless the whole
    payload is ID-less and the legacy fallback is unambiguous. `planned_*`
    is preserved unless explicitly sent. Clocks and provenance are never
    rewritten.
    """
    workout = get_workout(db, user_id, workout_id)
    matches = _match_workout_exercises(payload.exercises, list(workout.exercises))
    new_ids = _new_attach_exercise_ids(payload.exercises, matches)
    _validate_exercise_ids(db, user_id, new_ids)

    workout.name = payload.name
    if payload.date is not None:
        workout.date = payload.date

    workout.exercises = _reconcile_exercises(db, workout, payload.exercises)

    db.commit()
    return get_workout(db, user_id, workout_id)


def patch_workout(
    db: Session,
    user_id: int,
    workout_id: int,
    payload: WorkoutPatch,
) -> Workout:
    """Update Session name/date only. Clocks and children are untouched."""
    workout = get_workout(db, user_id, workout_id)
    provided = payload.model_fields_set
    if "name" in provided:
        if payload.name is None:
            raise ValidationError("name cannot be null")
        workout.name = payload.name
    if "date" in provided:
        if payload.date is None:
            raise ValidationError("date cannot be null")
        workout.date = payload.date
    db.commit()
    return get_workout(db, user_id, workout_id)


def complete_workout(db: Session, user_id: int, workout_id: int) -> Workout:
    """Mark an active Session completed. Idempotent once ended_at is set."""
    workout = get_workout(db, user_id, workout_id)
    if workout.ended_at is None:
        workout.ended_at = utc_now()
        db.commit()
    return get_workout(db, user_id, workout_id)


def delete_workout(db: Session, user_id: int, workout_id: int) -> None:
    """Delete a workout and (via cascade) its nested exercises and sets."""
    workout = get_workout(db, user_id, workout_id)
    db.delete(workout)
    db.commit()


def add_workout_exercise(
    db: Session,
    user_id: int,
    workout_id: int,
    payload: WorkoutExerciseCreate,
) -> WorkoutExercise:
    """Attach one catalog exercise. Creates zero Sets. Does not rewrite siblings."""
    workout = get_workout(db, user_id, workout_id)
    _validate_exercise_ids(db, user_id, {payload.exercise_id})
    siblings = list(workout.exercises)
    we = WorkoutExercise(
        exercise_id=payload.exercise_id,
        order_index=0,
        **dict(_EMPTY_PLANNED),
    )
    workout.exercises.append(we)
    _insert_and_compact(siblings + [we], we, payload.order_index)
    db.commit()
    return get_workout_exercise(db, user_id, we.id)


def delete_workout_exercise(
    db: Session, user_id: int, workout_exercise_id: int
) -> None:
    """Delete one WorkoutExercise and its Sets. Compact remaining siblings."""
    we = get_workout_exercise(db, user_id, workout_exercise_id)
    workout = get_workout(db, user_id, we.workout_id)
    workout.exercises.remove(we)
    _compact(list(workout.exercises))
    db.commit()


def reorder_workout_exercises(
    db: Session, user_id: int, workout_id: int, payload: ReorderIn
) -> Workout:
    """Rewrite WorkoutExercise order_index only. IDs stay the same."""
    workout = get_workout(db, user_id, workout_id)
    _apply_reorder(list(workout.exercises), payload.ids, "Workout exercise")
    db.commit()
    return get_workout(db, user_id, workout_id)


def add_set(
    db: Session,
    user_id: int,
    workout_exercise_id: int,
    payload: SetIn,
) -> Set:
    """Create one Set on a WorkoutExercise. Compact sibling order_index."""
    we = get_workout_exercise(db, user_id, workout_exercise_id)
    _assert_set_primary(
        db,
        we.exercise_id,
        payload.reps,
        payload.duration_seconds,
        payload.distance_meters,
    )
    siblings = list(we.sets)
    row = _new_set(payload, len(siblings))
    we.sets.append(row)
    _insert_and_compact(siblings + [row], row, payload.order_index)
    db.commit()
    return get_set(db, user_id, row.id)


def patch_set(db: Session, user_id: int, set_id: int, payload: SetPatch) -> Set:
    """Partial-update one Set. Re-validates the primary metric on the result."""
    row = get_set(db, user_id, set_id)
    we = row.workout_exercise
    provided = payload.model_fields_set
    primary_field = _primary_field_for(db, we.exercise_id)
    before_primary = getattr(row, primary_field)

    if "reps" in provided:
        row.reps = payload.reps
    if "weight_kg" in provided:
        row.weight_kg = payload.weight_kg
    if "duration_seconds" in provided:
        row.duration_seconds = payload.duration_seconds
    if "distance_meters" in provided:
        row.distance_meters = payload.distance_meters
    if "rpe" in provided:
        row.rpe = payload.rpe
    if "rir" in provided:
        row.rir = payload.rir
    if "set_type" in provided:
        if payload.set_type is None:
            raise ValidationError("set_type cannot be null")
        row.set_type = payload.set_type.value

    _assert_set_primary(
        db,
        we.exercise_id,
        row.reps,
        row.duration_seconds,
        row.distance_meters,
        grandfather=(
            before_primary is None and primary_field not in provided
        ),
    )

    if "order_index" in provided and payload.order_index is not None:
        _insert_and_compact(list(we.sets), row, payload.order_index)

    db.commit()
    return get_set(db, user_id, set_id)


def delete_set(db: Session, user_id: int, set_id: int) -> None:
    """Delete one Set. Compact remaining siblings. Do not recreate them."""
    row = get_set(db, user_id, set_id)
    we = get_workout_exercise(db, user_id, row.workout_exercise_id)
    we.sets.remove(row)
    _compact(list(we.sets))
    db.commit()


def reorder_sets(
    db: Session, user_id: int, workout_exercise_id: int, payload: ReorderIn
) -> WorkoutExercise:
    """Rewrite Set order_index only. IDs stay the same."""
    we = get_workout_exercise(db, user_id, workout_exercise_id)
    _apply_reorder(list(we.sets), payload.ids, "Set")
    db.commit()
    return get_workout_exercise(db, user_id, workout_exercise_id)
