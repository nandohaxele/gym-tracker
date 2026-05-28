"""Pydantic schemas for the exercises module."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExerciseOut(BaseModel):
    """Public exercise representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    muscle_group: str
    created_at: datetime
