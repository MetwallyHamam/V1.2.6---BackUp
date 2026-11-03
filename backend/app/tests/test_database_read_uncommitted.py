from app.db.session import database_engine_options


def test_sql_server_uses_read_uncommitted_by_default() -> None:
    options = database_engine_options(
        "mssql+pyodbc://user:password@server/database",
        True,
    )

    assert options["isolation_level"] == "READ UNCOMMITTED"


def test_sql_server_read_uncommitted_can_be_disabled() -> None:
    options = database_engine_options(
        "mssql+pymssql://user:password@server/database",
        False,
    )

    assert "isolation_level" not in options


def test_non_sql_server_database_is_unchanged() -> None:
    options = database_engine_options("sqlite+pysqlite:///:memory:", True)

    assert "isolation_level" not in options
