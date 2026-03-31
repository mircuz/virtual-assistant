"""Unit tests for _add_working_days helper in availability route."""
from __future__ import annotations

from datetime import date

from booking_engine.api.routes.availability import _add_working_days


class TestAddWorkingDays:
    def test_add_one_day_midweek(self):
        # Wednesday 2026-04-01 + 1 working day = Thursday 2026-04-02
        result = _add_working_days(date(2026, 4, 1), 1)
        assert result == date(2026, 4, 2)

    def test_add_three_days_midweek(self):
        # Monday 2026-03-30 + 3 = Thursday 2026-04-02
        result = _add_working_days(date(2026, 3, 30), 3)
        assert result == date(2026, 4, 2)

    def test_skips_sunday(self):
        # Saturday 2026-04-04 + 1 working day = Monday 2026-04-06
        result = _add_working_days(date(2026, 4, 4), 1)
        assert result == date(2026, 4, 6)

    def test_friday_plus_one_skips_sunday(self):
        # Friday 2026-04-03 + 1 = Saturday 2026-04-04 (weekday < 6 = True)
        result = _add_working_days(date(2026, 4, 3), 1)
        assert result == date(2026, 4, 4)

    def test_zero_days_returns_start(self):
        result = _add_working_days(date(2026, 4, 1), 0)
        assert result == date(2026, 4, 1)
