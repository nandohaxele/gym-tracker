"""SQLAlchemy ORM model for the Exercise entity.

Schema (see architecture.md):
    Exercise: id, name, muscle_group, created_at
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class Exercise(Base):
    """Predefined exercise from the seeded catalog."""

    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    muscle_group = Column(String(60), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Exercise id={self.id} name={self.name!r} group={self.muscle_group!r}>"
