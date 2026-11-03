from datetime import UTC, datetime

from app.core.clock import (
    as_server_time,
    configure_server_clock,
    server_clock_settings,
    server_now,
    server_timezone,
)


def test_server_clock_uses_cairo_daylight_offset() -> None:
    previous = server_clock_settings()
    try:
        configure_server_clock("Africa/Cairo", True)
        summer = as_server_time(datetime(2026, 9, 8, 21, 20, 59, tzinfo=UTC))
        winter = as_server_time(datetime(2026, 12, 8, 21, 20, 59, tzinfo=UTC))
        assert summer.isoformat() == "2026-09-09T00:20:59+03:00"
        assert winter.isoformat() == "2026-12-08T23:20:59+02:00"
    finally:
        configure_server_clock(*previous)


def test_disabling_daylight_uses_standard_server_offset() -> None:
    previous = server_clock_settings()
    try:
        configure_server_clock("Africa/Cairo", False)
        value = datetime(2026, 9, 8, 21, 20, 59, tzinfo=UTC).astimezone(
            server_timezone(datetime(2026, 9, 8, tzinfo=UTC))
        )
        assert value.isoformat() == "2026-09-08T23:20:59+02:00"
        assert server_now().utcoffset() is not None
    finally:
        configure_server_clock(*previous)


def test_naive_database_value_is_not_shifted_again() -> None:
    previous = server_clock_settings()
    try:
        configure_server_clock("Africa/Cairo", True)
        value = datetime(2026, 9, 9, 0, 20, 59)
        assert as_server_time(value).replace(tzinfo=None) == value
    finally:
        configure_server_clock(*previous)
