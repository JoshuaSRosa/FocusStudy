"""BR-04: effective focus time calculation (total time minus pauses).

Pure function (no database, no Flask) so it can be tested in isolation.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

Interval = tuple[datetime, datetime | None]


@dataclass(frozen=True)
class FocusTime:
    total_seconds: int
    paused_seconds: int
    effective_seconds: int


def calculate_focus_time(start: datetime, end: datetime, pauses: Iterable[Interval]) -> FocusTime:
    """Calculates the focus time of a session.

    - `end` is the end of the session (or "now", for a session still open);
    - a pause without an end (still open) counts until `end`;
    - pauses are clipped to [start, end];
    - overlapping pauses are merged (time is not subtracted twice);
    - the result is never negative.
    """
    if end < start:
        raise ValueError("session end is before its start")

    clipped: list[tuple[datetime, datetime]] = []
    for p_start, p_end in pauses:
        p_end = end if p_end is None else p_end
        a, b = max(p_start, start), min(p_end, end)
        if b > a:
            clipped.append((a, b))

    clipped.sort()
    paused = 0.0
    current_start: datetime | None = None
    current_end: datetime | None = None
    for a, b in clipped:
        if current_end is None or a > current_end:
            if current_end is not None:
                paused += (current_end - current_start).total_seconds()
            current_start, current_end = a, b
        else:
            current_end = max(current_end, b)
    if current_end is not None:
        paused += (current_end - current_start).total_seconds()

    total = int((end - start).total_seconds())
    paused_s = min(int(paused), total)
    return FocusTime(total, paused_s, total - paused_s)
