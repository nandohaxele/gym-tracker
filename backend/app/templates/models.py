"""SQLAlchemy ORM models for the Template domain.

Two tables:
    Template         - global (user_id IS NULL) or personal (user_id = owner)
    TemplateExercise - planned intent for one catalog Exercise inside a Template

Templates store intent/targets only. Actual performance lives on Session
`Set` rows. Starting a Template copies targets onto `WorkoutExercise.planned_*`
so the Session snapshot is independent of later Template edits or deletion.

Uniqueness uses SQLite partial unique indexes: a personal name may reuse a
global name, and SQLite NULL-distinct UNIQUE would not enforce global uniqueness.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utc import utc_now_naive


def _target_pair_sql(min_col: str, max_col: str) -> str:
    """Both-null or both present, positive, and min <= max."""
    return (
        f"({min_col} IS NULL AND {max_col} IS NULL) OR ("
        f"{min_col} IS NOT NULL AND {max_col} IS NOT NULL "
        f"AND {min_col} > 0 AND {max_col} > 0 "
        f"AND {min_col} <= {max_col})"
    )


class Template(Base):
    """A global catalog template or a user-owned personal template."""

    __tablename__ = "templates"

    __table_args__ = (
        Index(
            "uq_templates_global_name_normalized",
            "name_normalized",
            unique=True,
            sqlite_where=text("user_id IS NULL"),
        ),
        Index(
            "uq_templates_personal_name_normalized",
            "user_id",
            "name_normalized",
            unique=True,
            sqlite_where=text("user_id IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name = Column(String(120), nullable=False)
    name_normalized = Column(String(120), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)

    user = relationship("User", back_populates="templates")
    exercises = relationship(
        "TemplateExercise",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateExercise.order_index",
    )

    @property
    def is_global(self) -> bool:
        return self.user_id is None

    def __repr__(self) -> str:
        scope = "global" if self.user_id is None else f"user={self.user_id}"
        return f"<Template id={self.id} name={self.name!r} {scope}>"


class TemplateExercise(Base):
    """Planned exercise inside a Template: catalog id, order, and targets."""

    __tablename__ = "template_exercises"

    __table_args__ = (
        CheckConstraint(
            "target_sets > 0",
            name="ck_template_exercises_target_sets_positive",
        ),
        CheckConstraint(
            _target_pair_sql("target_reps_min", "target_reps_max"),
            name="ck_template_exercises_reps_pair",
        ),
        CheckConstraint(
            _target_pair_sql(
                "target_duration_seconds_min", "target_duration_seconds_max"
            ),
            name="ck_template_exercises_duration_pair",
        ),
        CheckConstraint(
            _target_pair_sql(
                "target_distance_meters_min", "target_distance_meters_max"
            ),
            name="ck_template_exercises_distance_pair",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="CASCADE"),
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
    target_sets = Column(Integer, nullable=False)
    target_reps_min = Column(Integer, nullable=True)
    target_reps_max = Column(Integer, nullable=True)
    target_duration_seconds_min = Column(Integer, nullable=True)
    target_duration_seconds_max = Column(Integer, nullable=True)
    target_distance_meters_min = Column(Integer, nullable=True)
    target_distance_meters_max = Column(Integer, nullable=True)

    template = relationship("Template", back_populates="exercises")
    exercise = relationship("Exercise")

    def __repr__(self) -> str:
        return (
            f"<TemplateExercise id={self.id} "
            f"template_id={self.template_id} exercise_id={self.exercise_id}>"
        )
