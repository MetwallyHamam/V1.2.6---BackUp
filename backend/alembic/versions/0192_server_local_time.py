"""store database timestamps using server-local offsets.

Revision ID: 0192_server_local_time
Revises: 0191_inbound_vendor_profiles
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mssql

from alembic import op

revision: str = "0192_server_local_time"
down_revision: str | None = "0191_inbound_vendor_profiles"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _store_setting(key: str, value: str) -> None:
    bind = op.get_bind()
    current_time = "SYSDATETIMEOFFSET()" if bind.dialect.name == "mssql" else "CURRENT_TIMESTAMP"
    exists = bind.scalar(sa.text("SELECT COUNT(*) FROM site_settings WHERE [key] = :key"), {"key": key})
    parameters = {"key": key, "value": value}
    statement = (
        f"UPDATE site_settings SET value = :value, updated_at = {current_time} WHERE [key] = :key"
        if exists
        else f"INSERT INTO site_settings ([key], value, updated_at) VALUES (:key, :value, {current_time})"
    )
    bind.execute(sa.text(statement), parameters)


def _datetimeoffset_columns() -> list[tuple[str, str]]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return [
        (table, str(column["name"]))
        for table in inspector.get_table_names()
        for column in inspector.get_columns(table)
        if isinstance(column["type"], mssql.DATETIMEOFFSET)
    ]


def upgrade() -> None:
    _store_setting("server_timezone", "Africa/Cairo")
    _store_setting("daylight_saving_enabled", "true")
    bind = op.get_bind()
    if bind.dialect.name != "mssql":
        return
    quote = bind.dialect.identifier_preparer.quote
    for table, column in _datetimeoffset_columns():
        bind.execute(sa.text(
            f"UPDATE {quote(table)} SET {quote(column)} = "
            f"{quote(column)} AT TIME ZONE 'Egypt Standard Time' "
            f"WHERE {quote(column)} IS NOT NULL"
        ))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mssql":
        quote = bind.dialect.identifier_preparer.quote
        for table, column in _datetimeoffset_columns():
            bind.execute(sa.text(
                f"UPDATE {quote(table)} SET {quote(column)} = "
                f"SWITCHOFFSET({quote(column)}, '+00:00') "
                f"WHERE {quote(column)} IS NOT NULL"
            ))
    bind.execute(sa.text(
        "DELETE FROM site_settings WHERE [key] IN ('server_timezone', 'daylight_saving_enabled')"
    ))
