"""Auth business logic: register / authenticate users and issue tokens.

Routes call into these functions; this module never touches FastAPI primitives.
"""

from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.schemas import UserCreate
from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password


def register_user(db: Session, payload: UserCreate) -> User:
    """Create a new user, hashing the password.

    Raises:
        ConflictError: if the email is already registered.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise ConflictError("Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Validate credentials and return the User on success.

    Uses a constant-ish comparison flow to avoid leaking which side failed.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password")
    return user


def issue_token(user: User) -> str:
    """Return a signed JWT for the given user."""
    return create_access_token(subject=user.id)
