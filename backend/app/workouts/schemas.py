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
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
)

from app.workouts.models import SetType


# ---- Set schemas ---------------------------------------------------------

class SetIn(BaseModel):
    """Nested input for a single set, used by both create and update.

    `weight` is accepted as a compatibility alias for `weight_kg` so the
    current frontend can keep sending the pre-Phase-3 field name.
    """

    model_config = ConfigDict(populate_by_name=True)

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
        validation_alias=AliasChoices("weight_kg", "weight"),
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
    """Set representation in API responses.

    Emits both `weight_kg` and `weight` so the current frontend, which still
    reads `set.weight`, keeps working until Phase 6.
    """

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

    @computed_field
    @property
    def weight(self) -> Optional[Decimal]:
        return self.weight_kg

    @field_serializer("weight_kg", "weight", "rpe")
    def _decimal_as_number(self, value: Optional[Decimal]) -> Optional[float]:
        return None if value is None else float(value)


# ---- Embedded exercise reference ----------------------------------------

class ExerciseRefOut(BaseModel):
    """Slim exercise reference embedded inside a WorkoutExerciseOut.

    Kept intentionally minimal: enough for the UI to render the workout
    without hitting `/exercises` again.

    `muscle_group` is optional because personal exercises may omit it, and
    because history can reference an exercise that has since been archived.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    muscle_group: Optional[str] = None


# ---- WorkoutExercise schemas --------------------------------------------

class WorkoutExerciseIn(BaseModel):
    """Nested input when (re)building a workout's exercise list."""

    exercise_id: int = Field(gt=0, description="Catalog exercise id (must exist).")
    sets: list[SetIn] = Field(default_factory=list)
    order_index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Position within the parent workout; defaults to array index.",
    )


class WorkoutExerciseOut(BaseModel):
    """Nested response with hydrated exercise reference and sets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise: ExerciseRefOut
    sets: list[SetOut] = Field(default_factory=list)
    order_index: int


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

    The nested `exercises` tree fully replaces whatever the workout currently
    has -- old WorkoutExercise/Set rows are removed via SQLAlchemy's
    delete-orphan cascade.
    """

    name: str = Field(min_length=1, max_length=120)
    date: Optional[_date] = None
    exercises: list[WorkoutExerciseIn] = Field(default_factory=list)


class WorkoutSummary(BaseModel):
    """Compact representation returned by the list endpoint (no nested tree)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: _date
    created_at: datetime


class WorkoutDetail(BaseModel):
    """Full workout response with nested exercises and sets.

    Shape matches the contract defined in the Phase 4 spec:
        { id, name, date, exercises: [{ id, exercise, sets, order_index }] }
    `user_id` and `created_at` are included as helpful metadata for clients
    but are not strictly part of the documented contract.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    date: _date
    created_at: datetime
    exercises: list[WorkoutExerciseOut] = Field(default_factory=list)


# TODO (future): WorkoutTemplate schemas -- a separate flow where saved
# templates can be cloned into a new dated Workout for the current day.
