"""SQLAlchemy ORM model for the User entity.

Schema (see architecture.md):
    User: id, email, hashed_password, created_at
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utc import utc_now_naive


class User(Base):
    """Application user (owner of workouts)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)

    workouts = relationship(
        "Workout",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    templates = relationship(
        "Template",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
