"""Pydantic schemas for the workouts module.

Defines the request/response shapes for the workout system, including the
nested tree shared between create/update and the hydrated detail response.

Set field rules (Phase 3):
    - reps, duration_seconds, distance_meters : optional, > 0 when present
    - weight_kg : optional DECIMAL(6,2), >= 0; 0 is distinct from null
    - rpe : optional, 0.0–10.0 in 0.5 increments (backend-only for now)
    - rir : optional integer 0–5, where 5 means "5+"
    - set_type : warmup | working | dropset, default working
    - order_index : optional; service layer falls back to array index

The Exercise primary tracking metric is required on write; that rule lives in
the service layer because it depends on `exercise_tracking`.
"""

from datetime import date as _date
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.core.utc import serialize_utc
from app.exercises.models import TrackingType
from app.workouts.models import SetType


def _require_planned_pair(
    min_value: Optional[int], max_value: Optional[int], label: str
) -> None:
    if min_value is None and max_value is None:
        return
    if min_value is None or max_value is None:
        raise ValueError(f"{label} min and max must both be set")
    if min_value > max_value:
        raise ValueError(f"{label} min must be <= max")


_PLANNED_FIELD_NAMES = frozenset(
    {
        "planned_sets",
        "planned_reps_min",
        "planned_reps_max",
        "planned_duration_seconds_min",
        "planned_duration_seconds_max",
        "planned_distance_meters_min",
        "planned_distance_meters_max",
    }
)


# ---- Set schemas ---------------------------------------------------------

class SetIn(BaseModel):
    """Nested input for a single set, used by both create and update.

    Optional `id` lets PUT match an existing Set without recreating it.
    """

    id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Existing Set id.",
    )
    reps: Optional[int] = Field(
        default=None,
        gt=0,
        description="Repetitions performed. Optional; must be > 0 when present.",
    )
    weight_kg: Optional[Decimal] = Field(
        default=None,
        ge=0,
        max_digits=6,
        decimal_places=2,
        description=(
            "Load in kilograms. Optional; 0 is valid and distinct from null."
        ),
    )
    duration_seconds: Optional[int] = Field(
        default=None,
        gt=0,
        description="Duration in seconds. Optional; must be > 0 when present.",
    )
    distance_meters: Optional[int] = Field(
        default=None,
        gt=0,
        description="Distance in meters. Optional; must be > 0 when present.",
    )
    rpe: Optional[Decimal] = Field(
        default=None,
        ge=0,
        le=10,
        max_digits=3,
        decimal_places=1,
        description="RPE 0.0–10.0 in 0.5 increments. Independent of RIR.",
    )
    rir: Optional[int] = Field(
        default=None,
        ge=0,
        le=5,
        description='RIR 0–5, where 5 means "5+". Independent of RPE.',
    )
    set_type: SetType = Field(
        default=SetType.working,
        description="warmup | working | dropset. Defaults to working.",
    )
    order_index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Position within the parent exercise; defaults to array index.",
    )

    @field_validator("rpe")
    @classmethod
    def _rpe_half_steps(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return None
        if value % Decimal("0.5") != 0:
            raise ValueError("rpe must be in increments of 0.5")
        return value


class SetOut(BaseModel):
    """Set representation in API responses. Canonical load field is `weight_kg`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reps: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    duration_seconds: Optional[int] = None
    distance_meters: Optional[int] = None
    rpe: Optional[Decimal] = None
    rir: Optional[int] = None
    set_type: SetType
    order_index: int

    @field_serializer("weight_kg", "rpe")
    def _decimal_as_number(self, value: Optional[Decimal]) -> Optional[float]:
        return None if value is None else float(value)


class SetPatch(BaseModel):
    """Partial update for one Set. Only provided fields are applied."""

    reps: Optional[int] = Field(default=None, gt=0)
    weight_kg: Optional[Decimal] = Field(
        default=None,
        ge=0,
        max_digits=6,
        decimal_places=2,
    )
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    distance_meters: Optional[int] = Field(default=None, gt=0)
    rpe: Optional[Decimal] = Field(
        default=None, ge=0, le=10, max_digits=3, decimal_places=1
    )
    rir: Optional[int] = Field(default=None, ge=0, le=5)
    set_type: Optional[SetType] = None
    order_index: Optional[int] = Field(default=None, ge=0)

    @field_validator("rpe")
    @classmethod
    def _rpe_half_steps(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return None
        if value % Decimal("0.5") != 0:
            raise ValueError("rpe must be in increments of 0.5")
        return value


class ReorderIn(BaseModel):
    """Ordered permutation of existing child ids."""

    ids: list[int] = Field(default_factory=list)


# ---- Embedded exercise reference ----------------------------------------

class ExerciseRefOut(BaseModel):
    """Exercise reference embedded inside Session / Template exercise rows.

    Includes tracking so historical Sessions stay input-aware even after the
    exercise is archived and disappears from `GET /exercises`.
    `muscle_group` is optional because personal exercises may omit it.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    muscle_group: Optional[str] = None
    is_active: bool = True
    primary_tracking_type: TrackingType
    secondary_tracking_types: list[TrackingType] = Field(default_factory=list)


# ---- WorkoutExercise schemas --------------------------------------------

class WorkoutExerciseIn(BaseModel):
    """Nested input when (re)building a workout's exercise list.

    `planned_*` is optional. The current frontend does not send it. On PUT,
    omitted planned fields are preserved from the existing Session snapshot
    (see workouts.service). Ad-hoc POST leaves them NULL.
    Optional `id` lets PUT match an existing WorkoutExercise without
    recreating it or its Sets.
    """

    id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Existing WorkoutExercise id. Omitted by the current frontend.",
    )
    exercise_id: int = Field(gt=0, description="Catalog exercise id (must exist).")
    sets: list[SetIn] = Field(default_factory=list)
    order_index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Position within the parent workout; defaults to array index.",
    )
    planned_sets: Optional[int] = Field(default=None, gt=0)
    planned_reps_min: Optional[int] = Field(default=None, gt=0)
    planned_reps_max: Optional[int] = Field(default=None, gt=0)
    planned_duration_seconds_min: Optional[int] = Field(default=None, gt=0)
    planned_duration_seconds_max: Optional[int] = Field(default=None, gt=0)
    planned_distance_meters_min: Optional[int] = Field(default=None, gt=0)
    planned_distance_meters_max: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _planned_pairs(self) -> "WorkoutExerciseIn":
        _require_planned_pair(self.planned_reps_min, self.planned_reps_max, "planned_reps")
        _require_planned_pair(
            self.planned_duration_seconds_min,
            self.planned_duration_seconds_max,
            "planned_duration_seconds",
        )
        _require_planned_pair(
            self.planned_distance_meters_min,
            self.planned_distance_meters_max,
            "planned_distance_meters",
        )
        return self

    def planned_explicitly_set(self) -> bool:
        """True when the client sent at least one planned_* field."""
        return bool(self.model_fields_set & _PLANNED_FIELD_NAMES)


class WorkoutExerciseOut(BaseModel):
    """Nested response with hydrated exercise reference and sets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise: ExerciseRefOut
    sets: list[SetOut] = Field(default_factory=list)
    order_index: int
    planned_sets: Optional[int] = None
    planned_reps_min: Optional[int] = None
    planned_reps_max: Optional[int] = None
    planned_duration_seconds_min: Optional[int] = None
    planned_duration_seconds_max: Optional[int] = None
    planned_distance_meters_min: Optional[int] = None
    planned_distance_meters_max: Optional[int] = None


class WorkoutExerciseCreate(BaseModel):
    """Attach one catalog exercise to an existing Session. Creates zero Sets."""

    exercise_id: int = Field(gt=0)
    order_index: Optional[int] = Field(default=None, ge=0)


# ---- Workout schemas -----------------------------------------------------

class WorkoutCreate(BaseModel):
    """Payload to create a workout (optionally with nested exercises and sets)."""

    name: str = Field(min_length=1, max_length=120)
    date: Optional[_date] = Field(
        default=None,
        description="Workout date (YYYY-MM-DD). Defaults to today server-side.",
    )
    exercises: list[WorkoutExerciseIn] = Field(default_factory=list)


class WorkoutUpdate(BaseModel):
    """Full-update payload for a workout (PUT semantics).

    The nested `exercises` tree is reconciled in place: matched
    WorkoutExercise / Set rows keep their primary keys. `started_at`,
    `ended_at`, `created_at`, and `source_template_id` are not in this
    payload and are never rewritten by PUT.
    """

    name: str = Field(min_length=1, max_length=120)
    date: Optional[_date] = None
    exercises: list[WorkoutExerciseIn] = Field(default_factory=list)


class WorkoutPatch(BaseModel):
    """Scalar-only Session update. Does not touch children or clocks."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    date: Optional[_date] = None


class WorkoutSummary(BaseModel):
    """Compact representation returned by the list endpoint (no nested tree)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: _date
    created_at: datetime
    started_at: datetime
    ended_at: Optional[datetime] = None

    @field_serializer("created_at", "started_at", "ended_at")
    def _timestamps(self, value: Optional[datetime]) -> Optional[str]:
        return serialize_utc(value)


class WorkoutDetail(BaseModel):
    """Full workout response with nested exercises and sets.

    Additive Phase 5 fields: `started_at`, `ended_at`. `date` remains the
    training calendar day. `ended_at` NULL means the Session is active.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    date: _date
    created_at: datetime
    started_at: datetime
    ended_at: Optional[datetime] = None
    source_template_id: Optional[int] = None
    exercises: list[WorkoutExerciseOut] = Field(default_factory=list)

    @field_serializer("created_at", "started_at", "ended_at")
    def _timestamps(self, value: Optional[datetime]) -> Optional[str]:
        return serialize_utc(value)


# TODO (future): WorkoutTemplate schemas -- a separate flow where saved
# templates can be cloned into a new dated Workout for the current day.
