"""Pydantic schemas for the workouts module.

Defines the request/response shapes for the workout system, including the
nested tree shared between create/update and the hydrated detail response.

Validation rules (from PRD):
    - workout.name      : required, 1..120 chars
    - set.reps          : > 0
    - set.weight        : >= 0
    - order_index       : optional; service layer falls back to array index
"""

from datetime import date as _date
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---- Set schemas ---------------------------------------------------------

class SetIn(BaseModel):
    """Nested input for a single set, used by both create and update."""

    reps: int = Field(gt=0, description="Repetitions performed. Must be > 0.")
    weight: float = Field(ge=0, description="Weight used. Must be >= 0.")
    order_index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Position within the parent exercise; defaults to array index.",
    )


class SetOut(BaseModel):
    """Set representation in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reps: int
    weight: float
    order_index: int


# ---- Embedded exercise reference ----------------------------------------

class ExerciseRefOut(BaseModel):
    """Slim exercise reference embedded inside a WorkoutExerciseOut.

    Kept intentionally minimal: enough for the UI to render the workout
    without hitting `/exercises` again.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    muscle_group: str


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
