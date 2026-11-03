from collections.abc import Generator
from datetime import datetime

from sqlalchemy import DateTime, create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import as_server_time
from app.core.config import get_settings

settings = get_settings()


def database_engine_options(database_url: str, read_uncommitted: bool) -> dict[str, object]:
    """Return provider-specific engine options.

    SQL Server's READ UNCOMMITTED transaction isolation has the same read
    semantics as applying WITH (NOLOCK) to every table reference. Configuring
    it on the engine covers ORM-generated SQL, relationship loads, and textual
    SELECT statements without modifying write SQL or rewriting query text.
    """
    options: dict[str, object] = {
        "pool_pre_ping": True,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout_seconds,
        "pool_recycle": settings.database_pool_recycle_seconds,
    }
    if database_url.casefold().startswith("mssql+") and read_uncommitted:
        options["isolation_level"] = "READ UNCOMMITTED"
    return options


engine = create_engine(
    settings.database_url,
    **database_engine_options(
        settings.database_url,
        settings.database_read_uncommitted,
    ),
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def normalize_database_datetime(value: datetime, dialect_name: str) -> datetime:
    """Normalize application timestamps for the target database representation.

    SQL Server ``datetime``/``datetime2`` columns do not retain an offset.  The
    pymssql driver serializes aware values as strings that SQL Server rejects,
    so persist the configured server-local wall time without ``tzinfo``.  Read
    paths already restore naive database values to the configured server zone.
    """
    normalized = as_server_time(value)
    if dialect_name == "mssql":
        return normalized.replace(tzinfo=None)
    return normalized


def normalize_mssql_parameters(parameters: object) -> object:
    """Remove offsets from every datetime bound through the MSSQL driver."""
    if isinstance(parameters, datetime):
        return normalize_database_datetime(parameters, "mssql")
    if isinstance(parameters, dict):
        return {key: normalize_mssql_parameters(value) for key, value in parameters.items()}
    if isinstance(parameters, tuple):
        return tuple(normalize_mssql_parameters(value) for value in parameters)
    if isinstance(parameters, list):
        return [normalize_mssql_parameters(value) for value in parameters]
    return parameters


@event.listens_for(engine, "before_cursor_execute", retval=True)
def normalize_mssql_bound_parameters(
    connection: object,
    _cursor: object,
    statement: str,
    parameters: object,
    _context: object,
    _executemany: bool,
) -> tuple[str, object]:
    """Normalize generated defaults and bulk parameters after ORM processing."""
    dialect = getattr(getattr(connection, "dialect", None), "name", None)
    if dialect == "mssql":
        parameters = normalize_mssql_parameters(parameters)
    return statement, parameters


@event.listens_for(Session, "before_flush")
def normalize_datetime_offsets(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Enforce server-local offsets for every ORM datetime write."""
    dialect_name = session.get_bind().dialect.name
    for item in session.new.union(session.dirty):
        state = inspect(item)
        for column in state.mapper.columns:
            if not isinstance(column.type, DateTime):
                continue
            attribute = state.mapper.get_property_by_column(column).key
            value = getattr(item, attribute, None)
            if isinstance(value, datetime):
                setattr(item, attribute, normalize_database_datetime(value, dialect_name))


def refresh_server_clock(db: Session) -> None:
    """Refresh the process clock without coupling the DB layer to ORM models."""
    from app.core.clock import DEFAULT_SERVER_TIMEZONE, configure_server_clock

    try:
        result = db.execute(
            text(
                "SELECT [key], value FROM site_settings "
                "WHERE [key] IN ('server_timezone', 'daylight_saving_enabled')"
            )
        )
        rows: dict[str, str] = {str(row[0]): str(row[1]) for row in result}
    except Exception:
        # Migrations, first startup, and health checks may run before the table exists.
        return
    configure_server_clock(
        rows.get("server_timezone", DEFAULT_SERVER_TIMEZONE),
        rows.get("daylight_saving_enabled", "true").casefold() == "true",
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        refresh_server_clock(db)
        yield db
    finally:
        db.close()
