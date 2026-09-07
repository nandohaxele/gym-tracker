"""Authenticated assistant HTTP boundary."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.assistant.models import ExecuteIn, InterpretIn
from app.assistant.rate_limit import check as check_rate_limit
from app.assistant.service import execute_assistant, interpret_utterance
from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok


router = APIRouter()


@router.post("/interpret")
def interpret(
    payload: InterpretIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Preview validated Phase 8 commands. Never writes."""
    check_rate_limit(current_user.id)
    result = interpret_utterance(
        db,
        current_user.id,
        payload.text,
        workout_id=payload.workout_id,
        focus_workout_exercise_id=payload.focus_workout_exercise_id,
        locale=payload.locale,
    )
    return ok(result.model_dump(mode="json"))


@router.post("/execute")
def execute(
    payload: ExecuteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run already-validated Phase 8 commands. Does not call the LLM."""
    result = execute_assistant(db, current_user.id, payload.commands)
    return ok(result.model_dump(mode="json"))
