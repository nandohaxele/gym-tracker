"""Reusable FastAPI dependencies.

Currently exposes `get_current_user` which extracts the bearer token,
decodes it, and loads the matching User row. Used by every protected route.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.database import get_db
from app.core.exceptions import AuthError
from app.core.security import decode_token


# tokenUrl is informational (used by /docs); routes still accept JSON via /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated User from the request's Bearer token."""
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Invalid token payload")

    try:
        user = db.get(User, int(user_id))
    except (TypeError, ValueError) as exc:
        raise AuthError("Invalid token subject") from exc

    if user is None:
        raise AuthError("User no longer exists")

    return user
