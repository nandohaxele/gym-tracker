"""Assistant I/O models and the closed provider interpretation schema.

Provider output never includes Exercise / Template / Session / WE ids.
Those come from the authenticated request, Session context, or Phase 8
resolvers after the user chooses a candidate.
"""

from datetime import date as _date
from decimal import Decimal
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.workouts.models import SetType


_INPUT = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ---- HTTP input ----------------------------------------------------------


class InterpretIn(BaseModel):
    """Authenticated interpret request. IDs are trusted only after ownership checks."""

    model_config = _INPUT

    text: str = Field(min_length=1, max_length=500)
    workout_id: Optional[int] = Field(default=None, gt=0)
    focus_workout_exercise_id: Optional[int] = Field(default=None, gt=0)
    locale: Optional[str] = Field(default=None, max_length=16)

    @field_validator("locale")
    @classmethod
    def _blank_locale(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ExecuteCommandIn(BaseModel):
    """One Phase 8-compatible command from the client.

    Treated as untrusted input. Ownership and tracking stay in services.
    """

    model_config = _INPUT

    type: Literal[
        "create_session",
        "add_exercise",
        "record_set",
        "finish_session",
        "start_template",
    ]
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    date: Optional[_date] = None
    query: Optional[str] = Field(default=None, min_length=1, max_length=120)
    locale: Optional[str] = Field(default=None, max_length=16)
    scope: Optional[str] = None
    workout_id: Optional[int] = Field(default=None, gt=0)
    workout_exercise_id: Optional[int] = Field(default=None, gt=0)
    exercise_query: Optional[str] = Field(default=None, min_length=1, max_length=120)
    template_id: Optional[int] = Field(default=None, gt=0)
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

    @field_validator("locale", "scope")
    @classmethod
    def _blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ExecuteIn(BaseModel):
    """Execute already-previewed Phase 8 commands. Does not call the LLM."""

    model_config = _INPUT

    commands: list[ExecuteCommandIn] = Field(min_length=1)


# ---- Provider structured output (no resource ids) ------------------------


class ProviderIntent(BaseModel):
    """One closed intent. Semantic queries only — no database ids."""

    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "create_session",
        "add_exercise",
        "record_set",
        "finish_session",
        "start_template",
    ]
    name: Optional[str] = Field(default=None, max_length=120)
    date: Optional[_date] = None
    query: Optional[str] = Field(default=None, max_length=120)
    locale: Optional[str] = Field(default=None, max_length=16)
    scope: Optional[Literal["any", "personal", "global"]] = None
    exercise_query: Optional[str] = Field(default=None, max_length=120)
    reps: Optional[int] = Field(default=None, gt=0)
    weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    distance_meters: Optional[int] = Field(default=None, gt=0)
    use_last_reps: bool = False
    use_last_weight: bool = False
    use_last_duration: bool = False
    use_last_distance: bool = False
    weight_delta_kg: Optional[Decimal] = None


class ProviderInterpretation(BaseModel):
    """Closed Responses API payload. Validated before any command is built."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "needs_clarification", "unknown"]
    message: Optional[str] = None
    intents: list[ProviderIntent] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ready_has_intents(self) -> "ProviderInterpretation":
        if self.status == "ready" and not self.intents:
            raise ValueError("ready interpretation must include at least one intent")
        return self


# ---- HTTP output ---------------------------------------------------------


class CommandPreview(BaseModel):
    """A Phase 8 command ready for the client to confirm or execute."""

    type: str
    payload: dict[str, Any]
    confirmation_required: bool
    preview: str


class InterpretOut(BaseModel):
    """Frontend-friendly interpret result. Never includes provider internals."""

    status: Literal[
        "ready",
        "needs_clarification",
        "unknown",
        "unavailable",
        "error",
    ]
    transcript: str
    confirmation_required: bool = False
    commands: list[CommandPreview] = Field(default_factory=list)
    preview: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class ExecuteResultItem(BaseModel):
    type: str
    status: str
    reason: Optional[str] = None
    message: Optional[str] = None
    data: Any = None
    candidates: list[Any] = Field(default_factory=list)


class ExecuteOut(BaseModel):
    status: Literal["executed", "needs_clarification", "error"]
    results: list[ExecuteResultItem]
    executed: list[ExecuteResultItem]
    failed: Optional[ExecuteResultItem] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    candidates: list[Any] = Field(default_factory=list)


HIGH_IMPACT_TYPES = frozenset(
    {"create_session", "start_template", "finish_session"}
)


def confirmation_required_for(command_type: str) -> bool:
    return command_type in HIGH_IMPACT_TYPES
