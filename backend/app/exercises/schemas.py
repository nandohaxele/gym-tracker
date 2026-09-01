"""Pydantic schemas for the exercises module.

`muscle_group` is optional everywhere: a personal exercise needs only a name and
a tracking configuration.

The normalized columns (`name_normalized`, `synonym_normalized`) are deliberately
not exposed -- they are an internal uniqueness/resolution mechanism, and clients
can reproduce them from `name` if they ever need to.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.exercises.models import TrackingType


# ---- Output --------------------------------------------------------------

class ExerciseSynonymOut(BaseModel):
    """An alternative name attached to an exercise."""

    model_config = ConfigDict(from_attributes=True)

    synonym: str
    locale: str


class ExerciseOut(BaseModel):
    """Public exercise representation.

    `is_global` is derived from `user_id`, which is never sent to clients: a
    caller only ever receives global exercises plus its own, so the owner id
    would carry no information it does not already have.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    muscle_group: Optional[str] = None
    slug: Optional[str] = None
    is_global: bool
    is_active: bool
    created_at: datetime
    primary_tracking_type: TrackingType
    secondary_tracking_types: list[TrackingType] = Field(default_factory=list)
    synonyms: list[ExerciseSynonymOut] = Field(default_factory=list)


# ---- Input ---------------------------------------------------------------

# Trimming inputs here keeps `name` presentable; the separate `name_normalized`
# column is what uniqueness and resolution actually compare.
_INPUT_CONFIG = ConfigDict(str_strip_whitespace=True)


def _reject_bad_tracking_shape(
    primary: Optional[TrackingType],
    secondary: Optional[list[TrackingType]],
) -> None:
    """Validate the primary/secondary split without touching the database."""
    if secondary is None:
        return
    if len(set(secondary)) != len(secondary):
        raise ValueError("secondary_tracking_types contains duplicates")
    if primary is not None and primary in secondary:
        raise ValueError("secondary_tracking_types must not contain the primary metric")


class ExerciseCreate(BaseModel):
    """Payload to create a personal exercise.

    Only `name` and `primary_tracking_type` are required; the exercise is owned
    by the authenticated user and never gets a slug.
    """

    model_config = _INPUT_CONFIG

    name: str = Field(min_length=1, max_length=120)
    primary_tracking_type: TrackingType
    secondary_tracking_types: list[TrackingType] = Field(default_factory=list)
    muscle_group: Optional[str] = Field(default=None, max_length=60)
    synonyms: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "ExerciseCreate":
        _reject_bad_tracking_shape(
            self.primary_tracking_type, self.secondary_tracking_types
        )
        if self.muscle_group == "":
            self.muscle_group = None
        return self


class ExerciseUpdate(BaseModel):
    """Partial-update payload for a personal exercise (PATCH semantics).

    Only the fields present in the request body are applied, so the service
    inspects `model_fields_set`. Sending `muscle_group: null` clears it; sending
    `synonyms: []` removes them all.

    Tracking fields are rejected once the exercise has recorded Set history --
    but only when they would actually change the configuration, so a client that
    PATCHes back an unchanged object still succeeds.
    """

    model_config = _INPUT_CONFIG

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    primary_tracking_type: Optional[TrackingType] = None
    secondary_tracking_types: Optional[list[TrackingType]] = None
    muscle_group: Optional[str] = Field(default=None, max_length=60)
    synonyms: Optional[list[str]] = None

    @model_validator(mode="after")
    def _check(self) -> "ExerciseUpdate":
        _reject_bad_tracking_shape(
            self.primary_tracking_type, self.secondary_tracking_types
        )
        if self.muscle_group == "":
            self.muscle_group = None
        return self
