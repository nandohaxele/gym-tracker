"""Exercises HTTP routes.

Endpoint (see api_contract.md):
    GET /exercises  (auth required)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.exercises import service
from app.exercises.schemas import ExerciseOut


router = APIRouter()


@router.get("")
def list_all(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Return the full catalog of exercises (auth required)."""
    items = service.list_exercises(db)
    return ok([ExerciseOut.model_validate(item) for item in items])
