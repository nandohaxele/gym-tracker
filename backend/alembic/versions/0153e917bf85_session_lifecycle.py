"""session lifecycle

Phase 5. Adds Session clock fields on `workouts` and leaves child tables
untouched so WorkoutExercise / Set ids stay stable:

- `started_at` timezone-aware DATETIME, NOT NULL after backfill
- `ended_at` timezone-aware DATETIME, nullable (NULL = active)

Historical Sessions (the existing 8) do not have a real gym clock-in.
`created_at` is first-persist time and disagrees with `date` on workout 9
(date=2026-07-02, created_at=2026-07-03). Backfill therefore uses UTC
midnight of the stored `date` as an unknown-time sentinel for both
`started_at` and `ended_at` (completed, duration unknown). No duration
and no `created_at` clock is invented.

`date`, `created_at`, `source_template_id`, planned_*, Sets, and Templates
are not rewritten. Child primary keys must survive the workouts rebuild.

`downgrade()` refuses if any Session is active (`ended_at IS NULL`) or any
`started_at` is not the date-midnight sentinel, so live-session clocks are
not silently dropped.

Revision ID: 0153e917bf85
Revises: 68505223da63
Create Date: 2026-09-06 23:28:29.630541

"""
from datetime import date as date_cls
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0153e917bf85"
down_revision: Union[str, None] = "68505223da63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SENTINEL_TIME = "00:00:00"


def _ids(bind, table: str) -> list[int]:
    return [
        row[0]
        for row in bind.execute(
            sa.text(f"SELECT id FROM {table} ORDER BY id")
        ).fetchall()
    ]


def _parse_date(value) -> date_cls:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_cls):
        return value
    return date_cls.fromisoformat(str(value)[:10])


def _is_date_midnight_utc(date_value, started_at) -> bool:
    """True when started_at is the unknown-time sentinel for `date`."""
    if started_at is None:
        return False
    day = _parse_date(date_value)
    if isinstance(started_at, datetime):
        stamp = started_at
        if stamp.tzinfo is not None:
            stamp = stamp.astimezone(timezone.utc).replace(tzinfo=None)
        return (
            stamp.date() == day
            and stamp.hour == 0
            and stamp.minute == 0
            and stamp.second == 0
            and stamp.microsecond == 0
        )
    text = str(started_at)
    return text.startswith(f"{day.isoformat()} {_SENTINEL_TIME}") or text.startswith(
        f"{day.isoformat()}T{_SENTINEL_TIME}"
    )


def upgrade() -> None:
    bind = op.get_bind()

    before_workouts = _ids(bind, "workouts")
    before_wes = _ids(bind, "workout_exercises")
    before_sets = _ids(bind, "sets")

    op.add_column(
        "workouts",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workouts",
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    rows = bind.execute(sa.text("SELECT id, date FROM workouts")).fetchall()
    for workout_id, date_value in rows:
        day = _parse_date(date_value)
        stamp = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        bind.execute(
            sa.text(
                "UPDATE workouts SET started_at = :stamp, ended_at = :stamp "
                "WHERE id = :id"
            ),
            {"stamp": stamp, "id": workout_id},
        )

    missing = bind.execute(
        sa.text("SELECT COUNT(*) FROM workouts WHERE started_at IS NULL")
    ).scalar_one()
    if missing:
        raise RuntimeError(
            f"{missing} workout(s) have no started_at after the date-midnight "
            "backfill. Aborting rather than inventing clocks."
        )

    with op.batch_alter_table("workouts", schema=None) as batch_op:
        batch_op.alter_column(
            "started_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
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


def downgrade() -> None:
    bind = op.get_bind()

    active = bind.execute(
        sa.text("SELECT COUNT(*) FROM workouts WHERE ended_at IS NULL")
    ).scalar_one()
    if active:
        raise RuntimeError(
            "Refusing to downgrade: "
            f"{active} active Session(s) have ended_at IS NULL. "
            "Restore from a backup rather than dropping live clocks."
        )

    rows = bind.execute(
        sa.text("SELECT id, date, started_at, ended_at FROM workouts")
    ).fetchall()
    non_sentinel = [
        row[0]
        for row in rows
        if not _is_date_midnight_utc(row[1], row[2])
        or not _is_date_midnight_utc(row[1], row[3])
        or str(row[2]) != str(row[3])
    ]
    if non_sentinel:
        raise RuntimeError(
            "Refusing to downgrade: started_at/ended_at is not the "
            f"date-midnight sentinel on workout id(s) {non_sentinel}. "
            "Restore from a backup rather than dropping live clocks."
        )

    with op.batch_alter_table("workouts", schema=None) as batch_op:
        batch_op.drop_column("ended_at")
        batch_op.drop_column("started_at")
