"""Unit: focus.calculate_focus_time (BR-04). Does not use the database."""
from datetime import datetime, timedelta, timezone

import pytest

from focus import calculate_focus_time

T0 = datetime(2026, 11, 23, 14, 0, tzinfo=timezone.utc)


def m(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


pytestmark = pytest.mark.req("BR-04")


def test_no_pauses_effective_equals_total():
    t = calculate_focus_time(T0, m(25), [])
    assert (t.total_seconds, t.paused_seconds, t.effective_seconds) == (1500, 0, 1500)


def test_one_pause_is_subtracted():
    t = calculate_focus_time(T0, m(30), [(m(10), m(15))])
    assert (t.total_seconds, t.paused_seconds, t.effective_seconds) == (1800, 300, 1500)


def test_multiple_pauses_are_added_up():
    t = calculate_focus_time(T0, m(60), [(m(10), m(15)), (m(30), m(40))])
    assert t.paused_seconds == 900 and t.effective_seconds == 2700


def test_overlapping_pauses_are_not_subtracted_twice():
    t = calculate_focus_time(T0, m(60), [(m(10), m(20)), (m(15), m(25)), (m(25), m(30))])
    assert t.paused_seconds == 20 * 60


def test_open_pause_counts_until_end():
    t = calculate_focus_time(T0, m(30), [(m(20), None)])
    assert t.paused_seconds == 600 and t.effective_seconds == 1200


def test_pause_outside_interval_is_clipped():
    t = calculate_focus_time(T0, m(30), [(m(-5), m(5)), (m(25), m(40))])
    assert t.paused_seconds == 10 * 60


def test_pause_covering_everything_gives_zero_and_never_negative():
    t = calculate_focus_time(T0, m(30), [(m(-10), m(50))])
    assert t.effective_seconds == 0 and t.paused_seconds == t.total_seconds


def test_zero_length_pause_is_ignored():
    assert calculate_focus_time(T0, m(10), [(m(5), m(5))]).paused_seconds == 0


def test_pause_order_does_not_matter():
    a = calculate_focus_time(T0, m(60), [(m(30), m(40)), (m(10), m(15))])
    b = calculate_focus_time(T0, m(60), [(m(10), m(15)), (m(30), m(40))])
    assert a == b


def test_zero_length_session():
    assert calculate_focus_time(T0, T0, []).effective_seconds == 0


def test_end_before_start_is_an_error():
    with pytest.raises(ValueError):
        calculate_focus_time(m(10), T0, [])
