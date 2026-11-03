from datetime import UTC, date, datetime, time

from app.modules.contracts.service import add_working_minutes

WORKING_DAYS = {
    6: (time(8), time(17)),
    0: (time(8), time(17)),
    1: (time(8), time(17)),
    2: (time(8), time(17)),
    3: (time(8), time(17)),
}


def test_sla_skips_cairo_weekend() -> None:
    start = datetime(2026, 1, 1, 14, 0, tzinfo=UTC)  # Thursday 16:00 Cairo
    due = add_working_minutes(start, 120, "Africa/Cairo", WORKING_DAYS, set())
    assert due == datetime(2026, 1, 4, 7, 0, tzinfo=UTC)  # Sunday 09:00 Cairo


def test_sla_skips_holiday() -> None:
    start = datetime(2026, 1, 1, 14, 0, tzinfo=UTC)
    due = add_working_minutes(
        start,
        120,
        "Africa/Cairo",
        WORKING_DAYS,
        {date(2026, 1, 4)},
    )
    assert due == datetime(2026, 1, 5, 7, 0, tzinfo=UTC)
