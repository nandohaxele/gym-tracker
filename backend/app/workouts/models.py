"""SQLAlchemy ORM models for workouts.

Three related tables (see architecture.md):
    Workout          - top-level workout owned by a user
    WorkoutExercise  - join row attaching a catalog Exercise to a Workout
    Set              - individual performed set under a WorkoutExercise

Cascade strategy:
    - Workout.exercises    -> delete-orphan on true parent delete / removed children
    - WorkoutExercise.sets -> delete-orphan on true parent delete / removed children
    - Normal updates keep existing child rows and their primary keys
    - User -> Workout      -> CASCADE on delete (DB + ORM)
    - WorkoutExercise -> Exercise: RESTRICT, never delete catalog rows.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utc import UtcDateTime, utc_now


def _planned_pair_sql(min_col: str, max_col: str) -> str:
    """Both-null or both present, positive, and min <= max."""
    return (
        f"({min_col} IS NULL AND {max_col} IS NULL) OR ("
        f"{min_col} IS NOT NULL AND {max_col} IS NOT NULL "
        f"AND {min_col} > 0 AND {max_col} > 0 "
        f"AND {min_col} <= {max_col})"
    )


class SetType(str, Enum):
    """How a recorded set was intended, independent of the tracking metrics."""

    warmup = "warmup"
    working = "working"
    dropset = "dropset"


SET_TYPE_VALUES: tuple[str, ...] = tuple(t.value for t in SetType)


class Workout(Base):
    """Top-level workout owned by a user. This is the performed Session."""

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
    started_at = Column(UtcDateTime, nullable=False, default=utc_now)
    ended_at = Column(UtcDateTime, nullable=True)
    source_template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user = relationship("User", back_populates="workouts")
    source_template = relationship("Template")
    exercises = relationship(
        "WorkoutExercise",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )

    def __repr__(self) -> str:
        return f"<Workout id={self.id} name={self.name!r} user_id={self.user_id}>"


class WorkoutExercise(Base):
    """Join row attaching a catalog Exercise to a Workout, with ordering.

    `planned_*` is a frozen Session snapshot of Template targets at Start.
    It is not live-linked to TemplateExercise and is independent of later
    Template edits or deletion. Ad-hoc Sessions leave these columns NULL.
    """

    __tablename__ = "workout_exercises"

    __table_args__ = (
        CheckConstraint(
            "planned_sets IS NULL OR planned_sets > 0",
            name="ck_workout_exercises_planned_sets_positive",
        ),
        CheckConstraint(
            _planned_pair_sql("planned_reps_min", "planned_reps_max"),
            name="ck_workout_exercises_planned_reps_pair",
        ),
        CheckConstraint(
            _planned_pair_sql(
                "planned_duration_seconds_min", "planned_duration_seconds_max"
            ),
            name="ck_workout_exercises_planned_duration_pair",
        ),
        CheckConstraint(
            _planned_pair_sql(
                "planned_distance_meters_min", "planned_distance_meters_max"
            ),
            name="ck_workout_exercises_planned_distance_pair",
        ),
    )

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
    planned_sets = Column(Integer, nullable=True)
    planned_reps_min = Column(Integer, nullable=True)
    planned_reps_max = Column(Integer, nullable=True)
    planned_duration_seconds_min = Column(Integer, nullable=True)
    planned_duration_seconds_max = Column(Integer, nullable=True)
    planned_distance_meters_min = Column(Integer, nullable=True)
    planned_distance_meters_max = Column(Integer, nullable=True)

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
    """A single performed set, ordered within its WorkoutExercise.

    Tracking fields (`reps`, `duration_seconds`, `distance_meters`) are all
    nullable. The service layer requires the parent Exercise's *primary*
    metric on write; historical rows that predate that rule are left intact.
    `weight_kg` is an optional load attribute, not a tracking type: 0 and
    NULL are distinct (unloaded vs. unknown).
    """

    __tablename__ = "sets"

    __table_args__ = (
        CheckConstraint(
            "set_type IN (" + ", ".join(repr(v) for v in SET_TYPE_VALUES) + ")",
            name="ck_sets_set_type",
        ),
        CheckConstraint(
            "reps IS NULL OR reps > 0",
            name="ck_sets_reps_positive",
        ),
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg >= 0",
            name="ck_sets_weight_kg_nonneg",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_sets_duration_positive",
        ),
        CheckConstraint(
            "distance_meters IS NULL OR distance_meters > 0",
            name="ck_sets_distance_positive",
        ),
        CheckConstraint(
            "rpe IS NULL OR (rpe >= 0 AND rpe <= 10)",
            name="ck_sets_rpe_range",
        ),
        CheckConstraint(
            "rir IS NULL OR (rir >= 0 AND rir <= 5)",
            name="ck_sets_rir_range",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workout_exercise_id = Column(
        Integer,
        ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reps = Column(Integer, nullable=True)
    weight_kg = Column(Numeric(6, 2), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    distance_meters = Column(Integer, nullable=True)
    rpe = Column(Numeric(3, 1), nullable=True)
    rir = Column(Integer, nullable=True)
    set_type = Column(
        String(16),
        nullable=False,
        default=SetType.working.value,
        server_default="working",
    )
    order_index = Column(Integer, nullable=False, default=0)

    workout_exercise = relationship("WorkoutExercise", back_populates="sets")

    def __repr__(self) -> str:
        return (
            f"<Set id={self.id} we_id={self.workout_exercise_id} "
            f"reps={self.reps} weight_kg={self.weight_kg} "
            f"set_type={self.set_type!r}>"
        )
