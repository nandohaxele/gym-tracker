"""Single-process per-user throttle for interpret only.

Not a distributed limit. Ordinary workout APIs are not throttled.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.core.config import get_settings
from app.core.exceptions import RateLimitError

_lock = threading.Lock()
_hits: dict[int, deque[float]] = defaultdict(deque)


def reset() -> None:
    """Test helper."""
    with _lock:
        _hits.clear()


def check(user_id: int) -> None:
    settings = get_settings()
    limit = max(1, int(settings.assistant_rate_limit_per_minute))
    now = time.monotonic()
    window = 60.0
    with _lock:
        bucket = _hits[user_id]
        while bucket and now - bucket[0] >= window:
            bucket.popleft()
        if len(bucket) >= limit:
            raise RateLimitError(
                "Too many assistant requests. Try again in a minute."
            )
        bucket.append(now)
