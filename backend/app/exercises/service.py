"""Exercises service layer.

Pure business logic -- never imports FastAPI primitives.

Visibility rule enforced by every read here: a caller sees global exercises
(`user_id IS NULL`) plus its own personal ones, and never another user's.

This module imports `app.workouts.models` for one read-only reason: deciding
whether an exercise already has recorded Set history, which is what freezes its
tracking configuration. The reverse dependency (workouts validating exercise
ids) goes through `selectable_exercise_ids` below.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.exercises.models import (
    DEFAULT_SYNONYM_LOCALE,
    Exercise,
    ExerciseSynonym,
    ExerciseTracking,
)
from app.exercises.normalization import clean_display_name, normalize_name
from app.exercises.schemas import ExerciseCreate, ExerciseUpdate
from app.workouts.models import Set, WorkoutExercise


# ---- Read ---------------------------------------------------------------

def _visible(db: Session, user_id: int) -> Query:
    """Base query for everything `user_id` is allowed to see."""
    return (
        db.query(Exercise)
        .options(
            selectinload(Exercise.tracking),
            selectinload(Exercise.synonyms),
        )
        .filter(or_(Exercise.user_id.is_(None), Exercise.user_id == user_id))
    )


def list_exercises(db: Session, user_id: int) -> list[Exercise]:
    """Return active global exercises plus the user's active personal ones.

    Ordering keeps the historical global grouping (muscle group, then name) and
    appends personal exercises that have no muscle group at the end rather than
    letting SQLite's NULLs-first default push them to the top.
    """
    return (
        _visible(db, user_id)
        .filter(Exercise.is_active.is_(True))
        .order_by(
            Exercise.muscle_group.is_(None).asc(),
            Exercise.muscle_group.asc(),
            Exercise.name.asc(),
        )
        .all()
    )


def selectable_exercise_ids(
    db: Session, user_id: int, exercise_ids: set[int]
) -> set[int]:
    """Subset of `exercise_ids` that `user_id` may attach to a workout.

    Valid means active *and* either global or owned by the caller. Archived
    exercises and other users' exercises are simply absent from the result, so
    callers report them identically and never leak that they exist.
    """
    if not exercise_ids:
        return set()

    rows = (
        db.query(Exercise.id)
        .filter(
            Exercise.id.in_(exercise_ids),
            Exercise.is_active.is_(True),
            or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
        )
        .all()
    )
    return {row[0] for row in rows}


def has_recorded_sets(db: Session, exercise_id: int) -> bool:
    """True once at least one Set exists via Exercise -> WorkoutExercise -> Set.

    Membership in an empty workout does not count, which is what "first use"
    means for the tracking-freeze rule. Templates do not exist yet; when they
    arrive (Phase 4) they must not count either.
    """
    return (
        db.query(Set.id)
        .join(WorkoutExercise, WorkoutExercise.id == Set.workout_exercise_id)
        .filter(WorkoutExercise.exercise_id == exercise_id)
        .first()
        is not None
    )


# ---- Name / synonym resolution -------------------------------------------

class ResolutionLevel(str, Enum):
    """Where a resolver match was found, in descending priority."""

    personal_name = "personal_name"
    personal_synonym = "personal_synonym"
    global_name = "global_name"
    global_synonym = "global_synonym"


@dataclass(frozen=True)
class ExerciseResolution:
    """Outcome of resolving a free-text name for a given user.

    Exactly one of three states: resolved (`exercise` set), ambiguous
    (`level` set with several `candidates`), or unmatched (both unset).
    """

    query: str
    normalized: str
    level: Optional[ResolutionLevel] = None
    exercise: Optional[Exercise] = None
    candidates: list[Exercise] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.exercise is not None

    @property
    def ambiguous(self) -> bool:
        return self.level is not None and self.exercise is None


def resolve_exercise(db: Session, user_id: int, text: str) -> ExerciseResolution:
    """Resolve free text to a single exercise, personal scope winning over global.

    Priority is strict: personal name, personal synonym, global name, global
    synonym. The first level with any match decides the outcome -- if that level
    holds several candidates the result is reported as ambiguous rather than
    picking one arbitrarily, and lower levels are not consulted.

    Only active exercises participate: an archived personal exercise must not
    shadow the global one whose name it may reuse.
    """
    normalized = normalize_name(text)
    if not normalized:
        raise ValidationError("Search text must contain at least one character")

    active = _visible(db, user_id).filter(Exercise.is_active.is_(True))

    def by_name(personal: bool) -> list[Exercise]:
        scope = (
            Exercise.user_id == user_id if personal else Exercise.user_id.is_(None)
        )
        return active.filter(scope, Exercise.name_normalized == normalized).all()

    def by_synonym(personal: bool) -> list[Exercise]:
        scope = (
            Exercise.user_id == user_id if personal else Exercise.user_id.is_(None)
        )
        return (
            active.join(ExerciseSynonym, ExerciseSynonym.exercise_id == Exercise.id)
            .filter(scope, ExerciseSynonym.synonym_normalized == normalized)
            .distinct()
            .all()
        )

    levels = (
        (ResolutionLevel.personal_name, lambda: by_name(personal=True)),
        (ResolutionLevel.personal_synonym, lambda: by_synonym(personal=True)),
        (ResolutionLevel.global_name, lambda: by_name(personal=False)),
        (ResolutionLevel.global_synonym, lambda: by_synonym(personal=False)),
    )

    for level, find in levels:
        matches = find()
        if not matches:
            continue
        return ExerciseResolution(
            query=text,
            normalized=normalized,
            level=level,
            exercise=matches[0] if len(matches) == 1 else None,
            candidates=matches,
        )

    return ExerciseResolution(query=text, normalized=normalized)


# ---- Write helpers -------------------------------------------------------

def _load_own_personal(db: Session, user_id: int, exercise_id: int) -> Exercise:
    """Load a personal exercise owned by `user_id`, archived ones included.

    Another user's exercise raises NotFoundError rather than a 403 so the API
    never confirms that the id exists. Global exercises are visible to everyone,
    so refusing to edit them is reported plainly instead.
    """
    exercise = (
        db.query(Exercise)
        .options(
            selectinload(Exercise.tracking),
            selectinload(Exercise.synonyms),
        )
        .filter(Exercise.id == exercise_id)
        .first()
    )
    if exercise is None or (
        exercise.user_id is not None and exercise.user_id != user_id
    ):
        raise NotFoundError("Exercise not found")
    if exercise.user_id is None:
        raise ValidationError("Global exercises cannot be modified")
    return exercise


def _assert_name_available(
    db: Session,
    user_id: Optional[int],
    name_normalized: str,
    exclude_id: Optional[int] = None,
) -> None:
    """Guard the owner-scoped normalized-name uniqueness before hitting the index.

    Archived exercises still hold their name: the partial unique index does not
    exclude them, and silently reusing the name would break a later restore.
    """
    query = db.query(Exercise.id).filter(Exercise.name_normalized == name_normalized)
    query = query.filter(
        Exercise.user_id.is_(None) if user_id is None else Exercise.user_id == user_id
    )
    if exclude_id is not None:
        query = query.filter(Exercise.id != exclude_id)

    if query.first() is not None:
        scope = "the global catalog" if user_id is None else "your exercises"
        raise ConflictError(f"An exercise named '{name_normalized}' already exists in {scope}")


def _normalized_synonyms(texts: list[str]) -> list[tuple[str, str]]:
    """Clean a synonym payload into (display, normalized) pairs.

    Blank entries are rejected and duplicates within the payload collapse, so
    the per-exercise unique index can never be the thing that reports them.
    """
    pairs: dict[str, str] = {}
    for raw in texts:
        display = clean_display_name(raw)
        normalized = normalize_name(display)
        if not normalized:
            raise ValidationError("Synonyms must contain at least one character")
        if len(display) > 120:
            raise ValidationError("Synonyms must be at most 120 characters")
        pairs.setdefault(normalized, display)
    return [(display, normalized) for normalized, display in pairs.items()]


def _assert_synonyms_available(
    db: Session,
    user_id: Optional[int],
    normalized: set[str],
    exclude_id: Optional[int] = None,
) -> None:
    """Keep synonyms unique *within an ownership scope*.

    Two globals may not share a synonym (it would make global resolution
    ambiguous) and neither may two exercises of the same user, but a personal
    synonym is free to reuse the text of a global one -- the resolver's strict
    priority order decides between them.
    """
    if not normalized:
        return

    query = (
        db.query(ExerciseSynonym.synonym_normalized)
        .join(Exercise, Exercise.id == ExerciseSynonym.exercise_id)
        .filter(ExerciseSynonym.synonym_normalized.in_(normalized))
        .filter(
            Exercise.user_id.is_(None)
            if user_id is None
            else Exercise.user_id == user_id
        )
    )
    if exclude_id is not None:
        query = query.filter(Exercise.id != exclude_id)

    taken = sorted({row[0] for row in query.all()})
    if taken:
        raise ConflictError(f"Synonym(s) already in use: {taken}")


def _tracking_rows(
    primary: str, secondary: list[str]
) -> list[ExerciseTracking]:
    """Build the tracking rows for an exercise, primary first."""
    rows = [ExerciseTracking(tracking_type=primary, is_primary=True)]
    rows.extend(
        ExerciseTracking(tracking_type=value, is_primary=False)
        for value in secondary
    )
    return rows


def _replace_children(db: Session, exercise: Exercise, attr: str, rows: list) -> None:
    """Swap a child collection, flushing the deletes before the inserts.

    Both child tables carry unique indexes that the new rows would collide with
    if SQLAlchemy emitted the INSERTs first, which its default save-before-delete
    ordering does.
    """
    getattr(exercise, attr).clear()
    db.flush()
    setattr(exercise, attr, rows)
    db.flush()


def _synonym_models(pairs: list[tuple[str, str]]) -> list[ExerciseSynonym]:
    return [
        ExerciseSynonym(
            synonym=display,
            synonym_normalized=normalized,
            locale=DEFAULT_SYNONYM_LOCALE,
        )
        for display, normalized in pairs
    ]


# ---- Write ---------------------------------------------------------------

def create_personal_exercise(
    db: Session, user_id: int, payload: ExerciseCreate
) -> Exercise:
    """Create an exercise owned by `user_id`.

    Personal exercises never get a slug -- `Exercise.id` is their stable
    identifier -- and `muscle_group` stays optional.
    """
    display = clean_display_name(payload.name)
    normalized = normalize_name(display)
    if not normalized:
        raise ValidationError("Name must contain at least one character")

    _assert_name_available(db, user_id, normalized)

    synonyms = _normalized_synonyms(payload.synonyms)
    _assert_synonyms_available(db, user_id, {n for _, n in synonyms})

    exercise = Exercise(
        user_id=user_id,
        name=display,
        name_normalized=normalized,
        slug=None,
        muscle_group=payload.muscle_group,
        is_active=True,
    )
    exercise.tracking = _tracking_rows(
        payload.primary_tracking_type.value,
        [t.value for t in payload.secondary_tracking_types],
    )
    exercise.synonyms = _synonym_models(synonyms)

    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


def update_personal_exercise(
    db: Session,
    user_id: int,
    exercise_id: int,
    payload: ExerciseUpdate,
) -> Exercise:
    """Apply a partial update to one of the user's personal exercises.

    Name and metadata are always editable. Tracking is editable only until the
    exercise has recorded Set history; after that a *changed* tracking
    configuration is rejected while an unchanged one passes through.
    """
    exercise = _load_own_personal(db, user_id, exercise_id)
    provided = payload.model_fields_set

    if "name" in provided:
        if payload.name is None:
            raise ValidationError("name cannot be null")
        display = clean_display_name(payload.name)
        normalized = normalize_name(display)
        if not normalized:
            raise ValidationError("Name must contain at least one character")
        _assert_name_available(db, user_id, normalized, exclude_id=exercise.id)
        exercise.name = display
        exercise.name_normalized = normalized

    if "muscle_group" in provided:
        exercise.muscle_group = payload.muscle_group

    if {"primary_tracking_type", "secondary_tracking_types"} & provided:
        _apply_tracking_update(db, exercise, payload, provided)

    if "synonyms" in provided:
        if payload.synonyms is None:
            raise ValidationError("synonyms cannot be null; send [] to clear them")
        synonyms = _normalized_synonyms(payload.synonyms)
        _assert_synonyms_available(
            db, user_id, {n for _, n in synonyms}, exclude_id=exercise.id
        )
        _replace_children(db, exercise, "synonyms", _synonym_models(synonyms))

    db.commit()
    db.refresh(exercise)
    return exercise


def _apply_tracking_update(
    db: Session,
    exercise: Exercise,
    payload: ExerciseUpdate,
    provided: set[str],
) -> None:
    """Resolve the requested tracking change and enforce the post-use freeze.

    A new primary that appears in the existing secondary list is simply promoted
    rather than reported as a conflict, so clients can change the primary metric
    without restating the secondaries.
    """
    if "primary_tracking_type" in provided and payload.primary_tracking_type is None:
        raise ValidationError("primary_tracking_type cannot be null")
    if (
        "secondary_tracking_types" in provided
        and payload.secondary_tracking_types is None
    ):
        raise ValidationError(
            "secondary_tracking_types cannot be null; send [] to clear them"
        )

    current_primary = exercise.primary_tracking_type
    current_secondary = set(exercise.secondary_tracking_types)

    desired_primary = (
        payload.primary_tracking_type.value
        if payload.primary_tracking_type is not None
        else current_primary
    )
    base_secondary = (
        {t.value for t in payload.secondary_tracking_types}
        if "secondary_tracking_types" in provided
        else current_secondary
    )
    desired_secondary = {t for t in base_secondary if t != desired_primary}

    if desired_primary == current_primary and desired_secondary == current_secondary:
        return

    if has_recorded_sets(db, exercise.id):
        raise ValidationError(
            "Tracking cannot be changed once the exercise has recorded sets"
        )

    _replace_children(
        db,
        exercise,
        "tracking",
        _tracking_rows(desired_primary, sorted(desired_secondary)),
    )


def archive_personal_exercise(
    db: Session, user_id: int, exercise_id: int
) -> Exercise:
    """Soft-archive a personal exercise. Idempotent.

    The row stays in the database and historical WorkoutExercise references keep
    resolving; it only disappears from listings and can no longer be added to a
    workout. There is no physical delete.

    Deferred (Phase 4 - Templates): archiving must also drop the exercise from
    the owner's future templates. Template entities do not exist yet.
    """
    exercise = _load_own_personal(db, user_id, exercise_id)
    if exercise.is_active:
        exercise.is_active = False
        db.commit()
        db.refresh(exercise)
    return exercise
