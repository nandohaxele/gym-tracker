"""SQLAlchemy ORM models for the Exercise domain.

Three tables:
    Exercise         - global (user_id IS NULL) or personal (user_id = owner) exercise
    ExerciseTracking - which metrics an exercise is tracked by, one flagged primary
    ExerciseSynonym  - alternative names used by the name/synonym resolver

Ownership model:
    global   -> user_id IS NULL, slug NOT NULL, visible to every authenticated user
    personal -> user_id = owner,  slug IS NULL, visible only to its owner

Uniqueness is expressed with SQLite *partial* unique indexes rather than plain
UNIQUE constraints, because `UNIQUE(user_id, name_normalized)` alone cannot
enforce global uniqueness: SQLite treats NULLs as distinct, so 23 global rows
with `user_id IS NULL` would never collide. The two scopes therefore get one
partial index each, which also gives us the desired behaviour that a personal
name may freely reuse a global name.

Verified on SQLAlchemy 2.0 / SQLite 3.45: a `batch_alter_table("exercises", ...)`
rebuild does reflect and re-emit both `ck_exercises_slug_scope` and the partial
indexes' WHERE clauses, so later migrations do not have to re-create them by
hand. The flip side is that a batch operation which drops `user_id` or `slug`
must drop that CHECK constraint explicitly first.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class TrackingType(str, Enum):
    """The metrics an exercise can be tracked by.

    Weight is deliberately *not* a tracking type: it is an independent load
    attribute of a Set, not the metric that defines the exercise.
    """

    reps = "reps"
    duration = "duration"
    distance = "distance"


TRACKING_TYPE_VALUES: tuple[str, ...] = tuple(t.value for t in TrackingType)

DEFAULT_SYNONYM_LOCALE = "en"


class Exercise(Base):
    """A global catalog exercise or a user-owned personal exercise."""

    __tablename__ = "exercises"

    __table_args__ = (
        # A global exercise must carry a slug; a personal one must not.
        CheckConstraint(
            "(user_id IS NULL AND slug IS NOT NULL) "
            "OR (user_id IS NOT NULL AND slug IS NULL)",
            name="ck_exercises_slug_scope",
        ),
        Index(
            "uq_exercises_global_name_normalized",
            "name_normalized",
            unique=True,
            sqlite_where=text("user_id IS NULL"),
        ),
        Index(
            "uq_exercises_global_slug",
            "slug",
            unique=True,
            sqlite_where=text("user_id IS NULL"),
        ),
        Index(
            "uq_exercises_personal_name_normalized",
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
    name = Column(String(120), nullable=False, index=True)
    name_normalized = Column(String(120), nullable=False, index=True)
    slug = Column(String(140), nullable=True)
    muscle_group = Column(String(60), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tracking = relationship(
        "ExerciseTracking",
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="ExerciseTracking.id",
    )
    synonyms = relationship(
        "ExerciseSynonym",
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="ExerciseSynonym.id",
    )

    @property
    def is_global(self) -> bool:
        return self.user_id is None

    @property
    def primary_tracking_type(self) -> str | None:
        """The single primary metric, or None if tracking has not been loaded/set."""
        for row in self.tracking:
            if row.is_primary:
                return row.tracking_type
        return None

    @property
    def secondary_tracking_types(self) -> list[str]:
        return [row.tracking_type for row in self.tracking if not row.is_primary]

    def __repr__(self) -> str:
        scope = "global" if self.user_id is None else f"user={self.user_id}"
        return f"<Exercise id={self.id} name={self.name!r} {scope}>"


class ExerciseTracking(Base):
    """One tracked metric of an exercise; exactly one row per exercise is primary.

    "At most one primary" is enforced by a partial unique index; "at least one"
    is enforced by the service layer and the Phase 2 backfill, since SQLite has
    no deferred constraints to express it declaratively.
    """

    __tablename__ = "exercise_tracking"

    __table_args__ = (
        UniqueConstraint(
            "exercise_id", "tracking_type", name="uq_exercise_tracking_type"
        ),
        CheckConstraint(
            "tracking_type IN ("
            + ", ".join(repr(v) for v in TRACKING_TYPE_VALUES)
            + ")",
            name="ck_exercise_tracking_type",
        ),
        Index(
            "uq_exercise_tracking_primary",
            "exercise_id",
            unique=True,
            sqlite_where=text("is_primary = 1"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(
        Integer,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tracking_type = Column(String(16), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)

    exercise = relationship("Exercise", back_populates="tracking")

    def __repr__(self) -> str:
        flag = "primary" if self.is_primary else "secondary"
        return (
            f"<ExerciseTracking exercise_id={self.exercise_id} "
            f"{self.tracking_type} {flag}>"
        )


class ExerciseSynonym(Base):
    """An alternative name for an exercise, used by the resolver.

    Uniqueness is per (exercise, locale, normalized text). Owner-scoped
    uniqueness -- "no two globals share a synonym" -- is enforced in the service
    layer instead of the schema, because ownership lives on `exercises.user_id`
    and SQLite indexes cannot span a join. A deliberately *absent*
    UNIQUE(locale, synonym_normalized) is what lets a personal synonym reuse the
    text of a global one; the resolver reports ambiguity if duplicates ever slip
    into the same scope.
    """

    __tablename__ = "exercise_synonyms"

    __table_args__ = (
        UniqueConstraint(
            "exercise_id",
            "locale",
            "synonym_normalized",
            name="uq_exercise_synonyms_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(
        Integer,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    synonym = Column(String(120), nullable=False)
    synonym_normalized = Column(String(120), nullable=False, index=True)
    locale = Column(String(10), nullable=False, default=DEFAULT_SYNONYM_LOCALE)

    exercise = relationship("Exercise", back_populates="synonyms")

    def __repr__(self) -> str:
        return (
            f"<ExerciseSynonym exercise_id={self.exercise_id} "
            f"{self.synonym!r} locale={self.locale!r}>"
        )
