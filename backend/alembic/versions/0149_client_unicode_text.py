"""enforce Unicode storage for client human-readable text

Revision ID: 0149_client_unicode_text
Revises: 0148_sla_outcome_snapshots
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from alembic import op

revision: str = "0149_client_unicode_text"
down_revision: str | None = "0148_sla_outcome_snapshots"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

CLIENT_UNICODE_FIELDS: tuple[tuple[str, int | None], ...] = (
    ("name", 200),
    ("address", 1000),
    ("notes", None),
)


def _quote(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def _dependent_index_ddl(
    bind: Connection, columns: set[str]
) -> list[tuple[str, str]]:
    rows = bind.execute(sa.text("""
        SELECT i.name, i.is_unique, i.type_desc, i.filter_definition,
               ic.is_included_column, ic.is_descending_key,
               ic.key_ordinal, ic.index_column_id, c.name AS column_name
        FROM sys.indexes AS i
        JOIN sys.index_columns AS ic
          ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns AS c
          ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID('clients')
          AND i.name IS NOT NULL
          AND i.is_primary_key=0
          AND i.is_unique_constraint=0
        ORDER BY i.name, ic.is_included_column, ic.key_ordinal,
                 ic.index_column_id
    """)).mappings()
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["name"]), []).append(dict(row))
    captured: list[tuple[str, str]] = []
    for name, index_rows in grouped.items():
        if not columns.intersection(str(row["column_name"]) for row in index_rows):
            continue
        keys = [
            _quote(str(row["column_name"]))
            + (" DESC" if bool(row["is_descending_key"]) else " ASC")
            for row in index_rows
            if not bool(row["is_included_column"])
        ]
        included = [
            _quote(str(row["column_name"]))
            for row in index_rows
            if bool(row["is_included_column"])
        ]
        first = index_rows[0]
        unique = "UNIQUE " if bool(first["is_unique"]) else ""
        clustered = (
            "CLUSTERED " if str(first["type_desc"]) == "CLUSTERED"
            else "NONCLUSTERED "
        )
        ddl = (
            f"CREATE {unique}{clustered}INDEX {_quote(name)} ON [clients] "
            f"({', '.join(keys)})"
        )
        if included:
            ddl += f" INCLUDE ({', '.join(included)})"
        if first["filter_definition"]:
            ddl += f" WHERE {first['filter_definition']}"
        captured.append((name, ddl))
    return captured


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mssql":
        return
    indexes = _dependent_index_ddl(
        bind, {field for field, _length in CLIENT_UNICODE_FIELDS}
    )
    for name, _ddl in indexes:
        op.drop_index(name, table_name="clients")
    columns = {
        str(column["name"]): column
        for column in sa.inspect(bind).get_columns("clients")
    }
    for field, length in CLIENT_UNICODE_FIELDS:
        column = columns[field]
        target = sa.Unicode(length) if length is not None else sa.UnicodeText()
        op.alter_column(
            "clients",
            field,
            existing_type=column["type"],
            type_=target,
            existing_nullable=bool(column["nullable"]),
        )
    for _name, ddl in indexes:
        bind.execute(sa.text(ddl))


def downgrade() -> None:
    # Never narrow Unicode client data back to lossy VARCHAR storage.
    pass
