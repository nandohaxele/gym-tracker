"""Pydantic schemas for the Template domain.

Targets are intent only. There is no weight / RPE / RIR / set_type target.
Min/max pairs are all-or-nothing: both null, or both present with min <= max.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.workouts.schemas import ExerciseRefOut


def require_target_pair(
    min_value: Optional[int], max_value: Optional[int], label: str
) -> None:
    """Reject a half-set or inverted min/max pair."""
    if min_value is None and max_value is None:
        return
    if min_value is None or max_value is None:
        raise ValueError(f"{label} min and max must both be set")
    if min_value > max_value:
        raise ValueError(f"{label} min must be <= max")


# ---- Nested exercise targets --------------------------------------------

class TemplateExerciseIn(BaseModel):
    """Nested input when (re)building a template's exercise list."""

    exercise_id: int = Field(gt=0)
    target_sets: int = Field(gt=0)
    target_reps_min: Optional[int] = Field(default=None, gt=0)
    target_reps_max: Optional[int] = Field(default=None, gt=0)
    target_duration_seconds_min: Optional[int] = Field(default=None, gt=0)
    target_duration_seconds_max: Optional[int] = Field(default=None, gt=0)
    target_distance_meters_min: Optional[int] = Field(default=None, gt=0)
    target_distance_meters_max: Optional[int] = Field(default=None, gt=0)
    order_index: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _pairs(self) -> "TemplateExerciseIn":
        require_target_pair(self.target_reps_min, self.target_reps_max, "reps")
        require_target_pair(
            self.target_duration_seconds_min,
            self.target_duration_seconds_max,
            "duration_seconds",
        )
        require_target_pair(
            self.target_distance_meters_min,
            self.target_distance_meters_max,
            "distance_meters",
        )
        return self


class TemplateExerciseOut(BaseModel):
    """Nested response with hydrated exercise reference and targets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise: ExerciseRefOut
    order_index: int
    target_sets: int
    target_reps_min: Optional[int] = None
    target_reps_max: Optional[int] = None
    target_duration_seconds_min: Optional[int] = None
    target_duration_seconds_max: Optional[int] = None
    target_distance_meters_min: Optional[int] = None
    target_distance_meters_max: Optional[int] = None


# ---- Template -----------------------------------------------------------

_INPUT_CONFIG = ConfigDict(str_strip_whitespace=True)


class TemplateCreate(BaseModel):
    """Create a personal template. `name` is required; exercises are optional."""

    model_config = _INPUT_CONFIG

    name: str = Field(min_length=1, max_length=120)
    exercises: list[TemplateExerciseIn] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    """Partial update for a personal template (PATCH semantics).

    Only fields present in the body are applied. Sending `exercises` replaces
    the whole target tree; omitting it leaves the current tree intact.
    """

    model_config = _INPUT_CONFIG

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    exercises: Optional[list[TemplateExerciseIn]] = None


class TemplateNameIn(BaseModel):
    """Optional name override for personalize / save-as-template."""

    model_config = _INPUT_CONFIG

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)


class TemplateSummary(BaseModel):
    """Compact list representation (no nested exercises)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_global: bool
    created_at: datetime


class TemplateDetail(BaseModel):
    """Full template with nested target tree."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_global: bool
    created_at: datetime
    exercises: list[TemplateExerciseOut] = Field(default_factory=list)


class TemplateResolveIn(BaseModel):
    """Exact normalized template-name resolution."""

    model_config = _INPUT_CONFIG

    query: str = Field(min_length=1, max_length=120)
    scope: Optional[Literal["any", "personal", "global"]] = None

    @field_validator("scope")
    @classmethod
    def _blank_scope(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class TemplateResolveOut(BaseModel):
    """Machine-readable template resolver outcome. HTTP 200 for all statuses."""

    status: Literal["resolved", "ambiguous", "not_found"]
    query: str
    normalized: str
    scope: Literal["any", "personal", "global"]
    level: Optional[Literal["personal", "global"]] = None
    template: Optional[TemplateSummary] = None
    candidates: list[TemplateSummary] = Field(default_factory=list)
