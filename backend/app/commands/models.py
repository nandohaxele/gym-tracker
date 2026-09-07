"""Structured domain commands and the internal execution result.

Pydantic rejects malformed arguments before the executor runs. `user_id`
is never a command field — the trusted caller supplies it.
"""

from dataclasses import dataclass, field
from datetime import date as _date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.workouts.models import SetType


_INPUT_CONFIG = ConfigDict(str_strip_whitespace=True)


class CommandStatus(str, Enum):
    executed = "executed"
    needs_clarification = "needs_clarification"
    error = "error"


class CommandReason(str, Enum):
    exercise = "exercise"
    template = "template"
    session = "session"
    workout_exercise = "workout_exercise"
    validation = "validation"
    not_found = "not_found"
    conflict = "conflict"


@dataclass
class CommandResult:
    """Internal orchestration result. Not the global HTTP envelope."""

    status: CommandStatus
    reason: Optional[CommandReason] = None
    message: Optional[str] = None
    data: Any = None
    candidates: list[Any] = field(default_factory=list)


class CreateSessionCommand(BaseModel):
    """Create an active ad-hoc Session (no Sets, ended_at NULL)."""

    model_config = _INPUT_CONFIG

    name: str = Field(min_length=1, max_length=120)
    date: Optional[_date] = None


class AddExerciseCommand(BaseModel):
    """Resolve an Exercise query and attach it to a Session."""

    model_config = _INPUT_CONFIG

    query: str = Field(min_length=1, max_length=120)
    locale: Optional[str] = Field(default=None, max_length=10)
    workout_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("locale")
    @classmethod
    def _blank_locale(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class RecordSetCommand(BaseModel):
    """Record one Set on a uniquely determined WorkoutExercise."""

    model_config = _INPUT_CONFIG

    workout_exercise_id: Optional[int] = Field(default=None, gt=0)
    workout_id: Optional[int] = Field(default=None, gt=0)
    exercise_query: Optional[str] = Field(default=None, min_length=1, max_length=120)
    locale: Optional[str] = Field(default=None, max_length=10)
    reps: Optional[int] = Field(default=None, gt=0)
    weight_kg: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=6, decimal_places=2
    )
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    distance_meters: Optional[int] = Field(default=None, gt=0)
    rpe: Optional[Decimal] = Field(
        default=None, ge=0, le=10, max_digits=3, decimal_places=1
    )
    rir: Optional[int] = Field(default=None, ge=0, le=5)
    set_type: SetType = SetType.working

    @field_validator("locale")
    @classmethod
    def _blank_locale(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("rpe")
    @classmethod
    def _rpe_half_steps(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return None
        if value % Decimal("0.5") != 0:
            raise ValueError("rpe must be in increments of 0.5")
        return value


class FinishSessionCommand(BaseModel):
    """Complete an owned Session. Omitted id uses the unique active Session."""

    workout_id: Optional[int] = Field(default=None, gt=0)


class StartTemplateCommand(BaseModel):
    """Start a visible Template by id or exact name query."""

    model_config = _INPUT_CONFIG

    template_id: Optional[int] = Field(default=None, gt=0)
    query: Optional[str] = Field(default=None, min_length=1, max_length=120)
    scope: Optional[str] = Field(default=None)

    @field_validator("scope")
    @classmethod
    def _scope(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned not in {"any", "personal", "global"}:
            raise ValueError("scope must be any, personal, or global")
        return cleaned

    @model_validator(mode="after")
    def _id_or_query(self) -> "StartTemplateCommand":
        if self.template_id is None and not self.query:
            raise ValueError("template_id or query is required")
        return self


Command = Union[
    CreateSessionCommand,
    AddExerciseCommand,
    RecordSetCommand,
    FinishSessionCommand,
    StartTemplateCommand,
]
