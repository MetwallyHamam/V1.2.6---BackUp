from datetime import UTC, datetime

from app.core.clock import server_timezone
from app.db.session import normalize_database_datetime, normalize_mssql_parameters


def test_sql_server_datetime_is_stored_as_naive_server_wall_time() -> None:
    value = datetime(2026, 10, 7, 16, 30, tzinfo=UTC)

    normalized = normalize_database_datetime(value, "mssql")

    assert normalized.tzinfo is None
    assert normalized == value.astimezone(server_timezone(value)).replace(tzinfo=None)


def test_non_sql_server_datetime_retains_server_offset() -> None:
    value = datetime(2026, 10, 7, 16, 30, tzinfo=UTC)

    normalized = normalize_database_datetime(value, "sqlite")

    assert normalized.tzinfo is not None
    assert normalized == value.astimezone(server_timezone(value))


def test_sql_server_parameter_normalization_covers_generated_defaults_and_batches() -> None:
    value = datetime(2026, 10, 7, 16, 30, tzinfo=UTC)

    normalized = normalize_mssql_parameters(
        [{"created_at": value, "name": "one"}, {"created_at": value, "name": "two"}]
    )

    assert isinstance(normalized, list)
    assert normalized[0]["created_at"].tzinfo is None
    assert normalized[1]["created_at"].tzinfo is None
    assert normalized[0]["name"] == "one"
