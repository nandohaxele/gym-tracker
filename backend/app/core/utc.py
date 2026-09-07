"""UTC datetime boundary.

SQLite + SQLAlchemy `DateTime(timezone=True)` stores a naive UTC string and
returns naive datetimes. Treating those as local time would shift Session
clocks. This module is the only place that converts across that boundary:

- writes are always timezone-aware UTC
- reads attach UTC when the driver dropped tzinfo
- API serialization emits `...Z`
"""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.engine import Dialect
from sqlalchemy.types import DateTime, TypeDecorator


def utc_now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def utc_now_naive() -> datetime:
    """Naive UTC for `created_at` columns that are not UtcDateTime.

    SQLite stores those as DATETIME without tzinfo. Callers must treat the
    stored value as UTC, never as server-local time.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Return timezone-aware UTC. Naive values are treated as UTC, never local."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def date_midnight_utc(day: date) -> datetime:
    """Unknown-time sentinel: calendar day at 00:00:00 UTC.

    Used for historical Sessions and retrospective nested creates. Zero elapsed
    time (`ended_at == started_at`) means the real clock is unknown, not a
    measured zero-minute workout.
    """
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def serialize_utc(value: Optional[datetime]) -> Optional[str]:
    """ISO-8601 UTC with a Z suffix."""
    aware = as_utc(value)
    if aware is None:
        return None
    return aware.isoformat().replace("+00:00", "Z")


class UtcDateTime(TypeDecorator):
    """DateTime that always yields timezone-aware UTC on the ORM."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect: Dialect):
        if value is None:
            return None
        return as_utc(value)

    def process_result_value(self, value, dialect: Dialect):
        if value is None:
            return None
        if isinstance(value, str):
            text = value.replace("Z", "+00:00")
            value = datetime.fromisoformat(text)
        return as_utc(value)
