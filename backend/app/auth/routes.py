"""Auth HTTP routes.

Endpoints (see api_contract.md):
    POST /auth/register
    POST /auth/login
    GET  /auth/me
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.models import User
from app.auth.schemas import Token, UserCreate, UserLogin, UserOut
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok


router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> dict:
    """Register a new account."""
    user = service.register_user(db, payload)
    return ok(UserOut.model_validate(user))


@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db)) -> dict:
    """Authenticate and return a JWT bearer token."""
    user = service.authenticate_user(db, payload.email, payload.password)
    token = service.issue_token(user)
    return ok(Token(access_token=token))


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    """Return the authenticated user's profile."""
    return ok(UserOut.model_validate(current_user))
