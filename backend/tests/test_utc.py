"""UTC helpers and SQLite UtcDateTime round-trip."""

from datetime import date, datetime, timezone

from app.workouts.models import Workout
from app.core.utc import as_utc, date_midnight_utc, serialize_utc, utc_now


def test_helpers_never_treat_naive_as_local():
    naive = datetime(2026, 7, 2, 0, 0, 0)
    aware = as_utc(naive)
    assert aware.tzinfo == timezone.utc
    assert aware.hour == 0
    assert serialize_utc(naive) == "2026-07-02T00:00:00Z"
    assert serialize_utc(date_midnight_utc(date(2026, 7, 2))) == "2026-07-02T00:00:00Z"
    now = utc_now()
    assert now.tzinfo == timezone.utc
    assert serialize_utc(now).endswith("Z")


def test_utc_datetime_reattaches_utc_on_sqlite_read(db, user_a):
    row = Workout(
        user_id=user_a["user_id"],
        name="Clock probe",
        date=date(2026, 7, 2),
        started_at=date_midnight_utc(date(2026, 7, 2)),
        ended_at=date_midnight_utc(date(2026, 7, 2)),
    )
    db.add(row)
    db.commit()
    workout_id = row.id
    db.expire_all()
    loaded = db.get(Workout, workout_id)
    assert loaded.started_at.tzinfo == timezone.utc
    assert serialize_utc(loaded.started_at) == "2026-07-02T00:00:00Z"
