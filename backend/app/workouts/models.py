"""SQLAlchemy ORM models for workouts.

Three related tables (see architecture.md):
    Workout          - top-level workout owned by a user
    WorkoutExercise  - join row attaching a catalog Exercise to a Workout
    Set              - individual performed set under a WorkoutExercise

Cascade strategy:
    - Workout.exercises    -> delete-orphan (replacing the list on PUT removes old rows)
    - WorkoutExercise.sets -> delete-orphan (same for sets)
    - User -> Workout      -> CASCADE on delete (DB + ORM)
    - WorkoutExercise -> Exercise: RESTRICT, never delete catalog rows.
"""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Workout(Base):
    """Top-level workout owned by a user."""

    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    date = Column(Date, nullable=False, default=lambda: datetime.utcnow().date())
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="workouts")
    exercises = relationship(
        "WorkoutExercise",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )

    def __repr__(self) -> str:
        return f"<Workout id={self.id} name={self.name!r} user_id={self.user_id}>"


class WorkoutExercise(Base):
    """Join row attaching a catalog Exercise to a Workout, with ordering."""

    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(
        Integer,
        ForeignKey("workouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = Column(
        Integer,
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_index = Column(Integer, nullable=False, default=0)

    workout = relationship("Workout", back_populates="exercises")
    exercise = relationship("Exercise")
    sets = relationship(
        "Set",
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="Set.order_index",
    )

    def __repr__(self) -> str:
        return (
            f"<WorkoutExercise id={self.id} "
            f"workout_id={self.workout_id} exercise_id={self.exercise_id}>"
        )


class Set(Base):
    """A single performed set (reps + weight), ordered within its WorkoutExercise."""

    __tablename__ = "sets"

    id = Column(Integer, primary_key=True, index=True)
    workout_exercise_id = Column(
        Integer,
        ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reps = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)

    workout_exercise = relationship("WorkoutExercise", back_populates="sets")

    def __repr__(self) -> str:
        return (
            f"<Set id={self.id} we_id={self.workout_exercise_id} "
            f"reps={self.reps} weight={self.weight}>"
        )
