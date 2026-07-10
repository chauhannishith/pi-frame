from datetime import datetime
from zoneinfo import ZoneInfo

from daily_scheduler import parse_daily_change_time, seconds_until_next_run


class TestDailyScheduler:
    def test_parse_default_invalid(self):
        assert parse_daily_change_time(None) == (3, 0)
        assert parse_daily_change_time("bad") == (3, 0)
        assert parse_daily_change_time("2560") == (3, 0)

    def test_parse_hhmm(self):
        assert parse_daily_change_time("0300") == (3, 0)
        assert parse_daily_change_time("1530") == (15, 30)
        assert parse_daily_change_time("0000") == (0, 0)

    def test_seconds_until_next_run_same_day(self):
        tz = ZoneInfo("UTC")
        now = datetime(2026, 7, 10, 1, 0, tzinfo=tz)
        assert seconds_until_next_run(3, 0, now=now, tz=tz) == 2 * 3600

    def test_seconds_until_next_run_rolls_to_tomorrow(self):
        tz = ZoneInfo("UTC")
        now = datetime(2026, 7, 10, 4, 0, tzinfo=tz)
        assert seconds_until_next_run(3, 0, now=now, tz=tz) == 23 * 3600

    def test_seconds_until_next_run_respects_timezone(self):
        tz = ZoneInfo("Asia/Kolkata")
        now = datetime(2026, 7, 10, 1, 0, tzinfo=tz)
        assert seconds_until_next_run(3, 0, now=now, tz=tz) == 2 * 3600
