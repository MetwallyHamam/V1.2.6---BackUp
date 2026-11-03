"""Central SupportHub server/business clock.

Database timestamps intentionally retain the configured server-local offset.
The configuration is process-wide and refreshed from Site Settings whenever a
database session is opened or the settings are changed.
"""

from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_SERVER_TIMEZONE = "Africa/Cairo"

_lock = RLock()
_timezone_name = DEFAULT_SERVER_TIMEZONE
_daylight_saving_enabled = True


def configure_server_clock(timezone_name: str, daylight_saving_enabled: bool) -> None:
    """Apply validated process-wide server clock settings."""
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown server timezone: {timezone_name}") from exc
    global _timezone_name, _daylight_saving_enabled
    with _lock:
        _timezone_name = timezone_name
        _daylight_saving_enabled = daylight_saving_enabled


def server_clock_settings() -> tuple[str, bool]:
    with _lock:
        return _timezone_name, _daylight_saving_enabled


def _standard_timezone(zone: ZoneInfo, year: int) -> tzinfo:
    offsets = [
        datetime(year, month, 1, 12, tzinfo=zone).utcoffset()
        for month in range(1, 13)
    ]
    standard = min((offset for offset in offsets if offset is not None), default=timedelta())
    return timezone(standard, name=f"{zone.key}-standard")


def server_timezone(at: datetime | None = None) -> tzinfo:
    name, daylight_enabled = server_clock_settings()
    zone = ZoneInfo(name)
    if daylight_enabled:
        return zone
    reference = at or datetime.now(UTC)
    return _standard_timezone(zone, reference.year)


def server_now() -> datetime:
    """Return the current aware datetime with the configured server offset."""
    current_utc = datetime.now(UTC)
    return current_utc.astimezone(server_timezone(current_utc))


def server_today() -> date:
    """Return the current calendar date according to the central server clock."""
    return server_now().date()


def as_server_time(value: datetime) -> datetime:
    """Convert an aware instant to the configured server timezone."""
    if value.tzinfo is None:
        # SQLite returns the already-local value without tzinfo. Treat naive
        # application values as server-local so repeated flushes never shift it.
        value = value.replace(tzinfo=server_timezone(value))
    return value.astimezone(server_timezone(value))
