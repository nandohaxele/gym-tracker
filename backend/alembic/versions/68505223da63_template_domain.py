"""template domain

Phase 4. Adds reusable Template intent as a separate entity from Workout
Sessions, plus a frozen planned snapshot on WorkoutExercise so Start does
not need Set prefills:

- new `templates` (user_id NULL = global, else personal)
- new `template_exercises` (targets only; no weight / RPE / RIR / set_type)
- `workouts.source_template_id` nullable provenance (ON DELETE SET NULL)
- `workout_exercises.planned_*` nullable snapshot columns

Data preservation: existing workouts (8) and workout_exercises (17) keep
their ids. Provenance and planned_* are left NULL -- no historical plan is
inferred. New template tables start empty. Sets are not touched.

Partial unique indexes express per-scope name uniqueness because SQLite
treats NULLs as distinct. Runtime PRAGMA foreign_keys stays off; service
code clears provenance and archive-cleans personal template exercises.

`downgrade()` refuses if any template exists or any Session has provenance
or a planned snapshot, so user-created Phase 4 data is not silently dropped.

Revision ID: 68505223da63
Revises: 88e993067758
Create Date: 2026-09-06 23:09:52.133394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "68505223da63"
down_revision: Union[str, None] = "88e993067758"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pair_sql(min_col: str, max_col: str) -> str:
    return (
        f"({min_col} IS NULL AND {max_col} IS NULL) OR ("
        f"{min_col} IS NOT NULL AND {max_col} IS NOT NULL "
        f"AND {min_col} > 0 AND {max_col} > 0 "
        f"AND {min_col} <= {max_col})"
    )


def _ids(bind, table: str) -> list[int]:
    return [
        row[0]
        for row in bind.execute(
            sa.text(f"SELECT id FROM {table} ORDER BY id")
        ).fetchall()
    ]


def upgrade() -> None:
    bind = op.get_bind()

    before_workouts = _ids(bind, "workouts")
    before_wes = _ids(bind, "workout_exercises")
    before_sets = _ids(bind, "sets")

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_normalized", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_templates_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_templates_id", "templates", ["id"], unique=False)
    op.create_index("ix_templates_user_id", "templates", ["user_id"], unique=False)
    op.create_index(
        "ix_templates_name_normalized",
        "templates",
        ["name_normalized"],
        unique=False,
    )
    op.create_index(
        "uq_templates_global_name_normalized",
        "templates",
        ["name_normalized"],
        unique=True,
        sqlite_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_templates_personal_name_normalized",
        "templates",
        ["user_id", "name_normalized"],
        unique=True,
        sqlite_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "template_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("target_sets", sa.Integer(), nullable=False),
        sa.Column("target_reps_min", sa.Integer(), nullable=True),
        sa.Column("target_reps_max", sa.Integer(), nullable=True),
        sa.Column("target_duration_seconds_min", sa.Integer(), nullable=True),
        sa.Column("target_duration_seconds_max", sa.Integer(), nullable=True),
        sa.Column("target_distance_meters_min", sa.Integer(), nullable=True),
        sa.Column("target_distance_meters_max", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "target_sets > 0",
            name="ck_template_exercises_target_sets_positive",
        ),
        sa.CheckConstraint(
            _pair_sql("target_reps_min", "target_reps_max"),
            name="ck_template_exercises_reps_pair",
        ),
        sa.CheckConstraint(
            _pair_sql(
                "target_duration_seconds_min", "target_duration_seconds_max"
            ),
            name="ck_template_exercises_duration_pair",
        ),
        sa.CheckConstraint(
            _pair_sql(
                "target_distance_meters_min", "target_distance_meters_max"
            ),
            name="ck_template_exercises_distance_pair",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name="fk_template_exercises_template_id_templates",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name="fk_template_exercises_exercise_id_exercises",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_template_exercises_id", "template_exercises", ["id"], unique=False
    )
    op.create_index(
        "ix_template_exercises_template_id",
        "template_exercises",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        "ix_template_exercises_exercise_id",
        "template_exercises",
        ["exercise_id"],
        unique=False,
    )

    op.add_column(
        "workouts",
        sa.Column("source_template_id", sa.Integer(), nullable=True),
    )
    with op.batch_alter_table("workouts", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_workouts_source_template_id_templates",
            "templates",
            ["source_template_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_workouts_source_template_id",
            ["source_template_id"],
            unique=False,
        )

    planned_columns = (
        "planned_sets",
        "planned_reps_min",
        "planned_reps_max",
        "planned_duration_seconds_min",
        "planned_duration_seconds_max",
        "planned_distance_meters_min",
        "planned_distance_meters_max",
    )
    for name in planned_columns:
        op.add_column(
            "workout_exercises",
            sa.Column(name, sa.Integer(), nullable=True),
        )

    with op.batch_alter_table("workout_exercises", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_workout_exercises_planned_sets_positive",
            "planned_sets IS NULL OR planned_sets > 0",
        )
        batch_op.create_check_constraint(
            "ck_workout_exercises_planned_reps_pair",
            _pair_sql("planned_reps_min", "planned_reps_max"),
        )
        batch_op.create_check_constraint(
            "ck_workout_exercises_planned_duration_pair",
            _pair_sql(
                "planned_duration_seconds_min",
                "planned_duration_seconds_max",
            ),
        )
        batch_op.create_check_constraint(
            "ck_workout_exercises_planned_distance_pair",
            _pair_sql(
                "planned_distance_meters_min",
                "planned_distance_meters_max",
            ),
        )

    after_workouts = _ids(bind, "workouts")
    after_wes = _ids(bind, "workout_exercises")
    after_sets = _ids(bind, "sets")
    if after_workouts != before_workouts:
        raise RuntimeError(
            "Workout primary keys changed during the rebuild. "
            f"before={before_workouts} after={after_workouts}"
        )
    if after_wes != before_wes:
        raise RuntimeError(
            "WorkoutExercise primary keys changed during the rebuild. "
            f"before={before_wes} after={after_wes}"
        )
    if after_sets != before_sets:
        raise RuntimeError(
            "Set primary keys changed during the rebuild. "
            f"before={before_sets} after={after_sets}"
        )

    leftover_prov = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM workouts WHERE source_template_id IS NOT NULL"
        )
    ).scalar_one()
    leftover_planned = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM workout_exercises WHERE "
            "planned_sets IS NOT NULL "
            "OR planned_reps_min IS NOT NULL "
            "OR planned_reps_max IS NOT NULL "
            "OR planned_duration_seconds_min IS NOT NULL "
            "OR planned_duration_seconds_max IS NOT NULL "
            "OR planned_distance_meters_min IS NOT NULL "
            "OR planned_distance_meters_max IS NOT NULL"
        )
    ).scalar_one()
    if leftover_prov or leftover_planned:
        raise RuntimeError(
            "Migration inferred historical template state. "
            f"source_template_id set on {leftover_prov} workout(s); "
            f"planned_* set on {leftover_planned} workout_exercise(s)."
        )


def downgrade() -> None:
    bind = op.get_bind()

    template_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM templates")
    ).scalar_one()
    provenance = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM workouts WHERE source_template_id IS NOT NULL"
        )
    ).scalar_one()
    planned = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM workout_exercises WHERE "
            "planned_sets IS NOT NULL "
            "OR planned_reps_min IS NOT NULL "
            "OR planned_reps_max IS NOT NULL "
            "OR planned_duration_seconds_min IS NOT NULL "
            "OR planned_duration_seconds_max IS NOT NULL "
            "OR planned_distance_meters_min IS NOT NULL "
            "OR planned_distance_meters_max IS NOT NULL"
        )
    ).scalar_one()
    if template_count or provenance or planned:
        raise RuntimeError(
            "Refusing to downgrade: Phase 4 template or snapshot data exists "
            f"(templates={template_count}, provenance={provenance}, "
            f"planned={planned}). Restore from a backup rather than dropping it."
        )

    with op.batch_alter_table("workout_exercises", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_workout_exercises_planned_sets_positive", type_="check"
        )
        batch_op.drop_constraint(
            "ck_workout_exercises_planned_reps_pair", type_="check"
        )
        batch_op.drop_constraint(
            "ck_workout_exercises_planned_duration_pair", type_="check"
        )
        batch_op.drop_constraint(
            "ck_workout_exercises_planned_distance_pair", type_="check"
        )
        batch_op.drop_column("planned_distance_meters_max")
        batch_op.drop_column("planned_distance_meters_min")
        batch_op.drop_column("planned_duration_seconds_max")
        batch_op.drop_column("planned_duration_seconds_min")
        batch_op.drop_column("planned_reps_max")
        batch_op.drop_column("planned_reps_min")
        batch_op.drop_column("planned_sets")

    with op.batch_alter_table("workouts", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_workouts_source_template_id_templates", type_="foreignkey"
        )
        batch_op.drop_index("ix_workouts_source_template_id")
        batch_op.drop_column("source_template_id")

    op.drop_index(
        "ix_template_exercises_exercise_id", table_name="template_exercises"
    )
    op.drop_index(
        "ix_template_exercises_template_id", table_name="template_exercises"
    )
    op.drop_index("ix_template_exercises_id", table_name="template_exercises")
    op.drop_table("template_exercises")

    op.drop_index(
        "uq_templates_personal_name_normalized", table_name="templates"
    )
    op.drop_index("uq_templates_global_name_normalized", table_name="templates")
    op.drop_index("ix_templates_name_normalized", table_name="templates")
    op.drop_index("ix_templates_user_id", table_name="templates")
    op.drop_index("ix_templates_id", table_name="templates")
    op.drop_table("templates")
