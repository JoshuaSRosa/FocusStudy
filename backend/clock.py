"""BR-03: the SERVER clock is the source of truth for session timestamps.

The whole API calls `clock.now()` instead of using datetime directly, which
lets the tests "move time forward" deterministically (monkeypatch).
"""
from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)
