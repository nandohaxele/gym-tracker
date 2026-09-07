"""Templates service layer.

Pure business logic -- never imports FastAPI primitives.

Visibility: a caller sees global templates (`user_id IS NULL`) plus its own
personal ones, and never another user's. Cross-user access is NotFoundError.
"""

from dataclasses import dataclass, field
from datetime import date as _date
from enum import Enum
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.exercises import service as exercises_service
from app.exercises.models import Exercise
from app.exercises.normalization import clean_display_name, normalize_name
from app.templates.models import Template, TemplateExercise
from app.templates.schemas import (
    TemplateCreate,
    TemplateExerciseIn,
    TemplateUpdate,
)
from app.core.utc import utc_now
from app.workouts.models import Set, Workout, WorkoutExercise


def _is_recorded_set(row: Set) -> bool:
    """True when a Set carries at least one actual tracking metric."""
    return (
        row.reps is not None
        or row.duration_seconds is not None
        or row.distance_meters is not None
    )


# ---- Read ---------------------------------------------------------------

def _visible(db: Session, user_id: int) -> Query:
    return db.query(Template).filter(
        or_(Template.user_id.is_(None), Template.user_id == user_id)
    )


def _detail_options():
    return (
        selectinload(Template.exercises)
        .selectinload(TemplateExercise.exercise)
        .selectinload(Exercise.tracking),
    )


def list_templates(db: Session, user_id: int) -> list[Template]:
    """Global templates plus the caller's personal ones, by normalized name."""
    return (
        _visible(db, user_id)
        .order_by(Template.name_normalized.asc(), Template.id.asc())
        .all()
    )


class TemplateResolutionLevel(str, Enum):
    """Where a template name match was found."""

    personal = "personal"
    global_ = "global"


class TemplateResolveScope(str, Enum):
    """Optional scope restriction for template resolution."""

    any = "any"
    personal = "personal"
    global_ = "global"


@dataclass(frozen=True)
class TemplateResolution:
    """Exact-name template resolution outcome."""

    query: str
    normalized: str
    scope: str
    level: Optional[TemplateResolutionLevel] = None
    template: Optional[Template] = None
    candidates: list[Template] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.template is not None

    @property
    def ambiguous(self) -> bool:
        return self.level is not None and self.template is None

    @property
    def status(self) -> str:
        if self.resolved:
            return "resolved"
        if self.ambiguous:
            return "ambiguous"
        return "not_found"


def _unique_templates(rows: list[Template]) -> list[Template]:
    unique: dict[int, Template] = {}
    for row in rows:
        unique.setdefault(row.id, row)
    return list(unique.values())


def resolve_template(
    db: Session,
    user_id: int,
    text: str,
    scope: Optional[str] = None,
) -> TemplateResolution:
    """Resolve an exact normalized template name.

    `scope` is `any` (default), `personal`, or `global`. For `any`, personal
    exact name wins over global exact name. No synonyms, no fuzzy match.
    """
    normalized = normalize_name(text)
    if not normalized:
        raise ValidationError("Search text must contain at least one character")

    raw_scope = scope.strip() if scope and scope.strip() else "any"
    try:
        resolved_scope = TemplateResolveScope(raw_scope)
    except ValueError:
        raise ValidationError("scope must be any, personal, or global") from None

    def by_personal() -> list[Template]:
        return _unique_templates(
            _visible(db, user_id)
            .filter(
                Template.user_id == user_id,
                Template.name_normalized == normalized,
            )
            .all()
        )

    def by_global() -> list[Template]:
        return _unique_templates(
            _visible(db, user_id)
            .filter(
                Template.user_id.is_(None),
                Template.name_normalized == normalized,
            )
            .all()
        )

    if resolved_scope is TemplateResolveScope.personal:
        levels = ((TemplateResolutionLevel.personal, by_personal),)
    elif resolved_scope is TemplateResolveScope.global_:
        levels = ((TemplateResolutionLevel.global_, by_global),)
    else:
        levels = (
            (TemplateResolutionLevel.personal, by_personal),
            (TemplateResolutionLevel.global_, by_global),
        )

    for level, find in levels:
        matches = find()
        if not matches:
            continue
        return TemplateResolution(
            query=text,
            normalized=normalized,
            scope=resolved_scope.value,
            level=level,
            template=matches[0] if len(matches) == 1 else None,
            candidates=matches,
        )

    return TemplateResolution(
        query=text, normalized=normalized, scope=resolved_scope.value
    )


def get_template(db: Session, user_id: int, template_id: int) -> Template:
    """Load a visible template with its target tree.

    Missing ids and another user's personal templates both raise NotFoundError.
    """
    template = (
        db.query(Template)
        .options(*_detail_options())
        .filter(
            Template.id == template_id,
            or_(Template.user_id.is_(None), Template.user_id == user_id),
        )
        .first()
    )
    if template is None:
        raise NotFoundError("Template not found")
    return template


def _load_own_personal(db: Session, user_id: int, template_id: int) -> Template:
    """Load a personal template owned by `user_id`.

    Another user's template is NotFoundError. A global is a ValidationError
    so the API can say plainly that globals cannot be modified.
    """
    template = (
        db.query(Template)
        .options(*_detail_options())
        .filter(Template.id == template_id)
        .first()
    )
    if template is None or (
        template.user_id is not None and template.user_id != user_id
    ):
        raise NotFoundError("Template not found")
    if template.user_id is None:
        raise ValidationError("Global templates cannot be modified")
    return template


# ---- Name uniqueness ----------------------------------------------------

def _assert_name_available(
    db: Session,
    user_id: Optional[int],
    name_normalized: str,
    exclude_id: Optional[int] = None,
) -> None:
    query = db.query(Template.id).filter(
        Template.name_normalized == name_normalized
    )
    query = query.filter(
        Template.user_id.is_(None) if user_id is None else Template.user_id == user_id
    )
    if exclude_id is not None:
        query = query.filter(Template.id != exclude_id)
    if query.first() is not None:
        scope = "the global catalog" if user_id is None else "your templates"
        raise ConflictError(
            f"A template named '{name_normalized}' already exists in {scope}"
        )


def _prepare_name(raw: str) -> tuple[str, str]:
    display = clean_display_name(raw)
    normalized = normalize_name(display)
    if not normalized:
        raise ValidationError("Name must contain at least one character")
    return display, normalized


# ---- Exercise tree ------------------------------------------------------

def _validate_exercise_ids(
    db: Session, user_id: int, exercise_ids: set[int]
) -> None:
    if not exercise_ids:
        return
    found = exercises_service.selectable_exercise_ids(db, user_id, exercise_ids)
    missing = exercise_ids - found
    if missing:
        raise ValidationError(f"Unknown exercise_id(s): {sorted(missing)}")


def _build_exercise_tree(items: list[TemplateExerciseIn]) -> list[TemplateExercise]:
    rows: list[TemplateExercise] = []
    for idx, item in enumerate(items):
        rows.append(
            TemplateExercise(
                exercise_id=item.exercise_id,
                order_index=item.order_index if item.order_index is not None else idx,
                target_sets=item.target_sets,
                target_reps_min=item.target_reps_min,
                target_reps_max=item.target_reps_max,
                target_duration_seconds_min=item.target_duration_seconds_min,
                target_duration_seconds_max=item.target_duration_seconds_max,
                target_distance_meters_min=item.target_distance_meters_min,
                target_distance_meters_max=item.target_distance_meters_max,
            )
        )
    return rows


def _copy_exercise_tree(source: list[TemplateExercise]) -> list[TemplateExercise]:
    """Deep-copy target rows so personalize does not share ORM instances."""
    return [
        TemplateExercise(
            exercise_id=row.exercise_id,
            order_index=row.order_index,
            target_sets=row.target_sets,
            target_reps_min=row.target_reps_min,
            target_reps_max=row.target_reps_max,
            target_duration_seconds_min=row.target_duration_seconds_min,
            target_duration_seconds_max=row.target_duration_seconds_max,
            target_distance_meters_min=row.target_distance_meters_min,
            target_distance_meters_max=row.target_distance_meters_max,
        )
        for row in source
    ]


# ---- Write --------------------------------------------------------------

def create_personal_template(
    db: Session, user_id: int, payload: TemplateCreate
) -> Template:
    """Create a template owned by `user_id`."""
    display, normalized = _prepare_name(payload.name)
    _assert_name_available(db, user_id, normalized)
    if payload.exercises:
        _validate_exercise_ids(
            db, user_id, {item.exercise_id for item in payload.exercises}
        )

    template = Template(
        user_id=user_id,
        name=display,
        name_normalized=normalized,
    )
    template.exercises = _build_exercise_tree(payload.exercises)
    db.add(template)
    db.commit()
    return get_template(db, user_id, template.id)


def update_personal_template(
    db: Session,
    user_id: int,
    template_id: int,
    payload: TemplateUpdate,
) -> Template:
    """Apply a partial update to one of the user's personal templates."""
    template = _load_own_personal(db, user_id, template_id)
    provided = payload.model_fields_set

    if "name" in provided:
        if payload.name is None:
            raise ValidationError("name cannot be null")
        display, normalized = _prepare_name(payload.name)
        _assert_name_available(db, user_id, normalized, exclude_id=template.id)
        template.name = display
        template.name_normalized = normalized

    if "exercises" in provided:
        if payload.exercises is None:
            raise ValidationError("exercises cannot be null; send [] to clear them")
        _validate_exercise_ids(
            db, user_id, {item.exercise_id for item in payload.exercises}
        )
        template.exercises = _build_exercise_tree(payload.exercises)

    db.commit()
    return get_template(db, user_id, template.id)


def delete_personal_template(
    db: Session, user_id: int, template_id: int
) -> None:
    """Delete a personal template.

    Sessions started from it keep their planned_* snapshot. Provenance is
    cleared in the service layer; runtime FK SET NULL is the DB backstop.
    """
    template = _load_own_personal(db, user_id, template_id)
    db.query(Workout).filter(Workout.source_template_id == template.id).update(
        {Workout.source_template_id: None},
        synchronize_session="fetch",
    )
    db.delete(template)
    db.commit()


def personalize_template(
    db: Session,
    user_id: int,
    template_id: int,
    name: Optional[str] = None,
) -> Template:
    """Deep-copy a global template into a new personal template.

    Does not start a Session and does not mutate the source.
    """
    source = get_template(db, user_id, template_id)
    if source.user_id is not None:
        raise ValidationError("Only global templates can be personalized")

    raw_name = name if name is not None else source.name
    display, normalized = _prepare_name(raw_name)
    _assert_name_available(db, user_id, normalized)
    _validate_exercise_ids(db, user_id, {row.exercise_id for row in source.exercises})

    copy = Template(
        user_id=user_id,
        name=display,
        name_normalized=normalized,
    )
    copy.exercises = _copy_exercise_tree(source.exercises)
    db.add(copy)
    db.commit()
    return get_template(db, user_id, copy.id)


def start_template(db: Session, user_id: int, template_id: int) -> Workout:
    """Create an independent Session snapshot from a visible template.

    Copies name, provenance, exercise ids/order, and target_* → planned_*.
    Creates zero Set rows. Does not create a personal template.
    """
    from app.workouts.service import get_workout

    template = get_template(db, user_id, template_id)
    if template.exercises:
        _validate_exercise_ids(
            db, user_id, {row.exercise_id for row in template.exercises}
        )

    workout = Workout(
        user_id=user_id,
        name=template.name,
        date=_date.today(),
        source_template_id=template.id,
        started_at=utc_now(),
        ended_at=None,
    )
    for row in template.exercises:
        workout.exercises.append(
            WorkoutExercise(
                exercise_id=row.exercise_id,
                order_index=row.order_index,
                planned_sets=row.target_sets,
                planned_reps_min=row.target_reps_min,
                planned_reps_max=row.target_reps_max,
                planned_duration_seconds_min=row.target_duration_seconds_min,
                planned_duration_seconds_max=row.target_duration_seconds_max,
                planned_distance_meters_min=row.target_distance_meters_min,
                planned_distance_meters_max=row.target_distance_meters_max,
            )
        )

    db.add(workout)
    db.commit()
    return get_workout(db, user_id, workout.id)


def create_template_from_workout(
    db: Session,
    user_id: int,
    workout_id: int,
    name: Optional[str] = None,
) -> Template:
    """Derive a personal template from actually recorded Session Sets.

    planned_* on WorkoutExercise is ignored. Archived personal exercises are
    omitted. A Session with no eligible exercises is rejected.
    """
    from app.workouts.service import get_workout

    workout = get_workout(db, user_id, workout_id)
    raw_name = name if name is not None else workout.name
    display, normalized = _prepare_name(raw_name)
    _assert_name_available(db, user_id, normalized)

    items: list[TemplateExercise] = []
    order = 0
    for we in workout.exercises:
        recorded = [row for row in we.sets if _is_recorded_set(row)]
        if not recorded:
            continue
        exercise = we.exercise
        if (
            exercise is not None
            and exercise.user_id is not None
            and not exercise.is_active
        ):
            continue

        reps = [row.reps for row in recorded if row.reps is not None]
        durations = [
            row.duration_seconds
            for row in recorded
            if row.duration_seconds is not None
        ]
        distances = [
            row.distance_meters
            for row in recorded
            if row.distance_meters is not None
        ]
        items.append(
            TemplateExercise(
                exercise_id=we.exercise_id,
                order_index=order,
                target_sets=len(recorded),
                target_reps_min=min(reps) if reps else None,
                target_reps_max=max(reps) if reps else None,
                target_duration_seconds_min=min(durations) if durations else None,
                target_duration_seconds_max=max(durations) if durations else None,
                target_distance_meters_min=min(distances) if distances else None,
                target_distance_meters_max=max(distances) if distances else None,
            )
        )
        order += 1

    if not items:
        raise ValidationError(
            "No eligible exercises to save as a template"
        )

    template = Template(
        user_id=user_id,
        name=display,
        name_normalized=normalized,
    )
    template.exercises = items
    db.add(template)
    db.commit()
    return get_template(db, user_id, template.id)


def remove_exercise_from_owner_personal_templates(
    db: Session, user_id: int, exercise_id: int
) -> None:
    """Drop a personal exercise from the owner's personal templates only.

    Does not touch Sessions, Sets, or global templates. Caller owns the
    surrounding transaction.
    """
    rows = (
        db.query(TemplateExercise)
        .join(Template, Template.id == TemplateExercise.template_id)
        .filter(
            Template.user_id == user_id,
            TemplateExercise.exercise_id == exercise_id,
        )
        .all()
    )
    template_ids = {row.template_id for row in rows}
    for row in rows:
        db.delete(row)
    for template_id in template_ids:
        cached = db.get(Template, template_id)
        if cached is not None:
            db.expire(cached, ["exercises"])
