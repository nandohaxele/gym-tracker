"""exercise domain foundation

Phase 2. Turns the flat seeded catalog into an owned domain:

- `exercises` gains `user_id` (NULL = global), `name_normalized`, `slug`,
  `is_active`, and `muscle_group` becomes nullable
- the globally UNIQUE raw-name index is replaced by scope-aware *partial* unique
  indexes, so a personal name may reuse a global one
- new `exercise_tracking` (one primary metric + optional secondaries) and
  `exercise_synonyms` tables

Data preservation: the 23 pre-existing rows keep their ids and become global.
Their normalized names and slugs are derived from the stored name with the same
rules as `app.exercises.normalization` -- inlined below on purpose, because a
migration must keep producing the values it produced the day it was written even
if the application helpers later change.

Primary tracking is backfilled from an explicit slug -> metric table rather than
inferred. An unmapped slug aborts the migration instead of defaulting to `reps`.

SQLite notes:
- `exercises` is rebuilt twice by batch mode (once to add nullable columns and
  relax `muscle_group`, once to tighten the backfilled columns to NOT NULL and
  add the slug-scope CHECK, which can only hold after the backfill). Rebuilds
  copy `id` explicitly, so ids and `workout_exercises.exercise_id` survive.
- The partial indexes are created after the last rebuild only because the second
  rebuild's own INSERT..SELECT has to satisfy them; batch mode does reflect and
  re-emit both partial-index predicates and CHECK constraints, so a later
  migration inherits them for free.
- foreign_keys enforcement is left off; enabling it is separate technical debt.

`downgrade()` refuses to run while personal exercises exist -- it would have to
either delete them or promote them to global, and neither is a decision a
migration should make silently.

Revision ID: da9c526717c0
Revises: f3f47238398b
Create Date: 2026-09-01 09:07:23.409618

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da9c526717c0'
down_revision: Union[str, None] = 'f3f47238398b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Frozen copies of app.exercises.normalization at the time of this migration.
_WHITESPACE_RUN = re.compile(r"\s+")
_NON_SLUG_RUN = re.compile(r"[^a-z0-9]+")


def _normalize(value: str) -> str:
    return _WHITESPACE_RUN.sub(" ", value).strip().lower()


def _slugify(value: str) -> str:
    return _NON_SLUG_RUN.sub("-", _normalize(value)).strip("-")


# Explicit primary metric for every seeded global exercise. Every entry is a
# dynamic resistance movement counted in repetitions except the isometric plank,
# which is held for time. None is distance-based.
_PRIMARY_TRACKING_BY_SLUG: dict[str, str] = {
    "bench-press": "reps",
    "incline-dumbbell-press": "reps",
    "push-up": "reps",
    "deadlift": "reps",
    "pull-up": "reps",
    "barbell-row": "reps",
    "lat-pulldown": "reps",
    "back-squat": "reps",
    "front-squat": "reps",
    "leg-press": "reps",
    "romanian-deadlift": "reps",
    "leg-curl": "reps",
    "calf-raise": "reps",
    "overhead-press": "reps",
    "lateral-raise": "reps",
    "face-pull": "reps",
    "barbell-curl": "reps",
    "dumbbell-curl": "reps",
    "triceps-pushdown": "reps",
    "skullcrusher": "reps",
    "plank": "duration",
    "hanging-leg-raise": "reps",
    "cable-crunch": "reps",
}


def upgrade() -> None:
    bind = op.get_bind()

    # ---- 1. widen `exercises` (nullable first, so the copy cannot fail) ----
    with op.batch_alter_table("exercises", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("name_normalized", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(sa.Column("slug", sa.String(length=140), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=True))
        batch_op.alter_column(
            "muscle_group",
            existing_type=sa.String(length=60),
            nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_exercises_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # The raw name is no longer globally unique: two users may each have a
    # personal "My Press", and a personal name may reuse a global one.
    op.drop_index("ix_exercises_name", table_name="exercises")
    op.create_index("ix_exercises_name", "exercises", ["name"], unique=False)
    op.create_index("ix_exercises_user_id", "exercises", ["user_id"], unique=False)
    op.create_index(
        "ix_exercises_name_normalized", "exercises", ["name_normalized"], unique=False
    )

    # ---- 2. backfill the existing catalog as global exercises -------------
    # Nothing could have created a personal exercise before this revision, so
    # every existing row is global by definition.
    rows = bind.execute(sa.text("SELECT id, name FROM exercises")).fetchall()

    normalized_by_id = {row_id: _normalize(name) for row_id, name in rows}
    slug_by_id = {row_id: _slugify(name) for row_id, name in rows}

    _assert_unique("normalized name", normalized_by_id)
    _assert_unique("slug", slug_by_id)

    for row_id, _name in rows:
        bind.execute(
            sa.text(
                "UPDATE exercises "
                "SET user_id = NULL, is_active = 1, "
                "    name_normalized = :normalized, slug = :slug "
                "WHERE id = :id"
            ),
            {
                "normalized": normalized_by_id[row_id],
                "slug": slug_by_id[row_id],
                "id": row_id,
            },
        )

    # ---- 3. tighten the backfilled columns -------------------------------
    with op.batch_alter_table("exercises", schema=None) as batch_op:
        batch_op.alter_column(
            "name_normalized",
            existing_type=sa.String(length=120),
            nullable=False,
        )
        batch_op.alter_column(
            "is_active",
            existing_type=sa.Boolean(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_exercises_slug_scope",
            "(user_id IS NULL AND slug IS NOT NULL) "
            "OR (user_id IS NOT NULL AND slug IS NULL)",
        )

    # ---- 4. scope-aware uniqueness ---------------------------------------
    # Partial indexes are required, not stylistic: SQLite treats NULLs as
    # distinct, so a plain UNIQUE(user_id, name_normalized) would let every
    # global row collide freely.
    op.create_index(
        "uq_exercises_global_name_normalized",
        "exercises",
        ["name_normalized"],
        unique=True,
        sqlite_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_exercises_global_slug",
        "exercises",
        ["slug"],
        unique=True,
        sqlite_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_exercises_personal_name_normalized",
        "exercises",
        ["user_id", "name_normalized"],
        unique=True,
        sqlite_where=sa.text("user_id IS NOT NULL"),
    )

    # ---- 5. exercise_tracking --------------------------------------------
    op.create_table(
        "exercise_tracking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("tracking_type", sa.String(length=16), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "tracking_type IN ('reps', 'duration', 'distance')",
            name="ck_exercise_tracking_type",
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exercise_id", "tracking_type", name="uq_exercise_tracking_type"
        ),
    )
    op.create_index("ix_exercise_tracking_id", "exercise_tracking", ["id"], unique=False)
    op.create_index(
        "ix_exercise_tracking_exercise_id",
        "exercise_tracking",
        ["exercise_id"],
        unique=False,
    )
    # "At most one primary metric per exercise". "At least one" has no
    # declarative form in SQLite and is owned by the service layer.
    op.create_index(
        "uq_exercise_tracking_primary",
        "exercise_tracking",
        ["exercise_id"],
        unique=True,
        sqlite_where=sa.text("is_primary = 1"),
    )

    # ---- 6. backfill primary tracking for every global -------------------
    for row_id, _name in rows:
        slug = slug_by_id[row_id]
        metric = _PRIMARY_TRACKING_BY_SLUG.get(slug)
        if metric is None:
            raise RuntimeError(
                f"Global exercise id={row_id} (slug {slug!r}) has no explicit "
                "primary tracking metric. Add it to _PRIMARY_TRACKING_BY_SLUG "
                "rather than letting it default."
            )
        bind.execute(
            sa.text(
                "INSERT INTO exercise_tracking "
                "(exercise_id, tracking_type, is_primary) "
                "VALUES (:exercise_id, :metric, 1)"
            ),
            {"exercise_id": row_id, "metric": metric},
        )

    # ---- 7. exercise_synonyms --------------------------------------------
    # Uniqueness is per (exercise, locale, text) only. A global UNIQUE on
    # (locale, synonym_normalized) is deliberately absent: it would stop a
    # personal synonym from reusing a global one. Owner-scoped uniqueness lives
    # in the service layer, since ownership is on exercises.user_id and a SQLite
    # index cannot span a join.
    op.create_table(
        "exercise_synonyms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("synonym", sa.String(length=120), nullable=False),
        sa.Column("synonym_normalized", sa.String(length=120), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exercise_id",
            "locale",
            "synonym_normalized",
            name="uq_exercise_synonyms_scope",
        ),
    )
    op.create_index("ix_exercise_synonyms_id", "exercise_synonyms", ["id"], unique=False)
    op.create_index(
        "ix_exercise_synonyms_exercise_id",
        "exercise_synonyms",
        ["exercise_id"],
        unique=False,
    )
    op.create_index(
        "ix_exercise_synonyms_synonym_normalized",
        "exercise_synonyms",
        ["synonym_normalized"],
        unique=False,
    )


def _assert_unique(label: str, value_by_id: dict[int, str]) -> None:
    """Abort before any index is created if the derived values would collide."""
    seen: dict[str, int] = {}
    collisions: list[str] = []
    for row_id, value in value_by_id.items():
        if value in seen:
            collisions.append(f"{value!r} (ids {seen[value]} and {row_id})")
        else:
            seen[value] = row_id
    if collisions:
        raise RuntimeError(
            f"Cannot backfill: duplicate global {label}s -> {'; '.join(collisions)}"
        )


def downgrade() -> None:
    bind = op.get_bind()

    personal = bind.execute(
        sa.text("SELECT COUNT(*) FROM exercises WHERE user_id IS NOT NULL")
    ).scalar_one()
    if personal:
        raise RuntimeError(
            f"Refusing to downgrade: {personal} personal exercise(s) exist and "
            "this revision owns the column that makes them addressable. Decide "
            "explicitly whether to delete or promote them first."
        )

    op.drop_index("ix_exercise_synonyms_synonym_normalized", table_name="exercise_synonyms")
    op.drop_index("ix_exercise_synonyms_exercise_id", table_name="exercise_synonyms")
    op.drop_index("ix_exercise_synonyms_id", table_name="exercise_synonyms")
    op.drop_table("exercise_synonyms")

    op.drop_index("uq_exercise_tracking_primary", table_name="exercise_tracking")
    op.drop_index("ix_exercise_tracking_exercise_id", table_name="exercise_tracking")
    op.drop_index("ix_exercise_tracking_id", table_name="exercise_tracking")
    op.drop_table("exercise_tracking")

    op.drop_index("uq_exercises_personal_name_normalized", table_name="exercises")
    op.drop_index("uq_exercises_global_slug", table_name="exercises")
    op.drop_index("uq_exercises_global_name_normalized", table_name="exercises")
    # Dropped before the rebuild: they index columns that are about to vanish.
    op.drop_index("ix_exercises_name_normalized", table_name="exercises")
    op.drop_index("ix_exercises_user_id", table_name="exercises")

    # The CHECK must be dropped explicitly: batch mode reflects it and would
    # otherwise re-emit a constraint referencing the columns being removed.
    with op.batch_alter_table("exercises", schema=None) as batch_op:
        batch_op.drop_constraint("ck_exercises_slug_scope", type_="check")
        batch_op.drop_constraint("fk_exercises_user_id_users", type_="foreignkey")
        batch_op.drop_column("is_active")
        batch_op.drop_column("slug")
        batch_op.drop_column("name_normalized")
        batch_op.drop_column("user_id")
        batch_op.alter_column(
            "muscle_group",
            existing_type=sa.String(length=60),
            nullable=False,
        )

    op.drop_index("ix_exercises_name", table_name="exercises")
    op.create_index("ix_exercises_name", "exercises", ["name"], unique=True)
