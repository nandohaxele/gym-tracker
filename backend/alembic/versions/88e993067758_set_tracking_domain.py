"""set tracking domain

Phase 3. Turns the reps+weight-only Set into the locked tracking model:

- `reps` becomes nullable
- `weight` FLOAT NOT NULL becomes `weight_kg` DECIMAL(6,2) nullable
- new nullable `duration_seconds`, `distance_meters`, `rpe`, `rir`
- new `set_type` (warmup | working | dropset), default `working`

Data preservation: every existing Set keeps its id (including the PUT-churn
gaps). `reps` and the quantized `weight` values are copied as-is. New metric
columns stay NULL. `set_type` is backfilled to `working`.

The FLOAT -> DECIMAL step is an explicit `ROUND(weight, 2)` copy, not an
in-place alter: autogenerate cannot write that conversion. Historical weights
were already exact 2-decimal values inside DECIMAL(6,2).

Primary-metric-required is *not* a schema CHECK. It needs a join to
`exercise_tracking` and would reject the one historical plank row that stored
duration in `reps`. The service layer owns that rule on write only.

`downgrade()` refuses if any Set would lose data (null reps/weight_kg, any
Phase-3-only value, or a non-working set_type). Against a freshly migrated
copy of the current gym.db it is reversible.

Revision ID: 88e993067758
Revises: da9c526717c0
Create Date: 2026-09-06 22:53:30.711167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "88e993067758"
down_revision: Union[str, None] = "da9c526717c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    before_ids = [
        row[0]
        for row in bind.execute(sa.text("SELECT id FROM sets ORDER BY id")).fetchall()
    ]

    # Nullable add-columns are in-place on SQLite. The quantized copy must
    # happen *before* `weight` is dropped so the conversion is explicit.
    op.add_column("sets", sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("sets", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    op.add_column("sets", sa.Column("distance_meters", sa.Integer(), nullable=True))
    op.add_column("sets", sa.Column("rpe", sa.Numeric(3, 1), nullable=True))
    op.add_column("sets", sa.Column("rir", sa.Integer(), nullable=True))
    op.add_column(
        "sets",
        sa.Column(
            "set_type",
            sa.String(length=16),
            nullable=False,
            server_default="working",
        ),
    )

    bind.execute(sa.text("UPDATE sets SET weight_kg = ROUND(weight, 2)"))

    unconverted = bind.execute(
        sa.text("SELECT COUNT(*) FROM sets WHERE weight_kg IS NULL")
    ).scalar_one()
    if unconverted:
        raise RuntimeError(
            f"Cannot drop weight: {unconverted} set(s) have no weight_kg after "
            "the ROUND() copy. Aborting rather than losing load values."
        )

    # Rebuild to drop `weight`, relax `reps`, and attach the CHECKs. batch
    # mode copies `id` with the rest of the row, so the gapped PK sequence
    # survives.
    with op.batch_alter_table("sets", schema=None) as batch_op:
        batch_op.drop_column("weight")
        batch_op.alter_column(
            "reps",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.create_check_constraint(
            "ck_sets_set_type",
            "set_type IN ('warmup', 'working', 'dropset')",
        )
        batch_op.create_check_constraint(
            "ck_sets_reps_positive",
            "reps IS NULL OR reps > 0",
        )
        batch_op.create_check_constraint(
            "ck_sets_weight_kg_nonneg",
            "weight_kg IS NULL OR weight_kg >= 0",
        )
        batch_op.create_check_constraint(
            "ck_sets_duration_positive",
            "duration_seconds IS NULL OR duration_seconds > 0",
        )
        batch_op.create_check_constraint(
            "ck_sets_distance_positive",
            "distance_meters IS NULL OR distance_meters > 0",
        )
        batch_op.create_check_constraint(
            "ck_sets_rpe_range",
            "rpe IS NULL OR (rpe >= 0 AND rpe <= 10)",
        )
        batch_op.create_check_constraint(
            "ck_sets_rir_range",
            "rir IS NULL OR (rir >= 0 AND rir <= 5)",
        )

    after_ids = [
        row[0]
        for row in bind.execute(sa.text("SELECT id FROM sets ORDER BY id")).fetchall()
    ]
    if after_ids != before_ids:
        raise RuntimeError(
            "Set primary keys changed during the rebuild. "
            f"before={before_ids} after={after_ids}"
        )


def downgrade() -> None:
    bind = op.get_bind()

    lossy = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM sets "
            "WHERE reps IS NULL "
            "   OR weight_kg IS NULL "
            "   OR duration_seconds IS NOT NULL "
            "   OR distance_meters IS NOT NULL "
            "   OR rpe IS NOT NULL "
            "   OR rir IS NOT NULL "
            "   OR set_type != 'working'"
        )
    ).scalar_one()
    if lossy:
        raise RuntimeError(
            f"Refusing to downgrade: {lossy} set(s) have Phase 3 data that "
            "the baseline reps+weight schema cannot store. Restore from a "
            "backup rather than dropping those values."
        )

    op.add_column("sets", sa.Column("weight", sa.Float(), nullable=True))
    bind.execute(sa.text("UPDATE sets SET weight = weight_kg"))

    # CHECKs must be dropped before the rebuild: batch mode would otherwise
    # re-emit constraints that reference columns being removed.
    with op.batch_alter_table("sets", schema=None) as batch_op:
        batch_op.drop_constraint("ck_sets_set_type", type_="check")
        batch_op.drop_constraint("ck_sets_reps_positive", type_="check")
        batch_op.drop_constraint("ck_sets_weight_kg_nonneg", type_="check")
        batch_op.drop_constraint("ck_sets_duration_positive", type_="check")
        batch_op.drop_constraint("ck_sets_distance_positive", type_="check")
        batch_op.drop_constraint("ck_sets_rpe_range", type_="check")
        batch_op.drop_constraint("ck_sets_rir_range", type_="check")
        batch_op.alter_column(
            "reps",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "weight",
            existing_type=sa.Float(),
            nullable=False,
        )
        batch_op.drop_column("set_type")
        batch_op.drop_column("rir")
        batch_op.drop_column("rpe")
        batch_op.drop_column("distance_meters")
        batch_op.drop_column("duration_seconds")
        batch_op.drop_column("weight_kg")
