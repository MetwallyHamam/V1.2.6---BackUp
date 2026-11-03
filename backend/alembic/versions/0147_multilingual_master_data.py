"""add Arabic master-data labels and complete ticket Unicode storage

Revision ID: 0147_multilingual_master_data
Revises: 0146_language_foundation
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from alembic import op

revision: str = "0147_multilingual_master_data"
down_revision: str | None = "0146_language_foundation"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

MASTER_FIELDS: dict[str, tuple[tuple[str, int], ...]] = {
    "client_statuses": (("name", 100),),
    "countries": (("name", 150),),
    "cities": (("name", 150),),
    "products": (("name", 200), ("description", 1000)),
    "product_modules": (("name", 200),),
    "environments": (("name", 100),),
    "service_catalog_items": (("name", 200), ("description", 1000)),
    "ticket_categories": (("name", 150), ("description", 1000)),
    "ticket_subcategories": (("name", 150),),
    "ticket_types": (("name", 100),),
    "ticket_statuses": (("name", 100),),
    "root_causes": (("name", 150), ("description", 1000)),
    "resolution_outcomes": (("name", 150), ("description", 1000)),
    "departments": (("name", 150), ("description", 1000)),
    "shift_types": (("name", 100), ("description", 1000)),
    "internal_operation_types": (("name", 100), ("description", 1000)),
}

TICKET_UNICODE_FIELDS: tuple[tuple[str, str, int | None], ...] = (
    ("tickets", "subcategory", 150),
    ("tickets", "pending_reason", 500),
    ("tickets", "shift_handover_reason", 1000),
    ("tickets", "permanent_fix_summary", None),
    ("tickets", "help_request_result", None),
)


def _columns(bind: Connection, table: str) -> dict[str, dict[str, object]]:
    return {str(column["name"]): column for column in sa.inspect(bind).get_columns(table)}


def _unicode(length: int | None) -> sa.Unicode | sa.UnicodeText:
    return sa.Unicode(length) if length is not None else sa.UnicodeText()


def _quote(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def _mssql_dependent_index_ddl(
    bind: Connection, table: str, columns: set[str]
) -> list[tuple[str, str]]:
    """Capture non-constraint indexes that must be rebuilt around ALTER COLUMN."""
    rows = bind.execute(
        sa.text(
            """
            SELECT i.name, i.is_unique, i.type_desc, i.filter_definition,
                   ic.key_ordinal, ic.is_included_column, ic.is_descending_key,
                   ic.index_column_id, c.name AS column_name
            FROM sys.indexes AS i
            JOIN sys.index_columns AS ic
              ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            JOIN sys.columns AS c
              ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE i.object_id = OBJECT_ID(:table)
              AND i.name IS NOT NULL
              AND i.is_primary_key = 0
              AND i.is_unique_constraint = 0
            ORDER BY i.name, ic.is_included_column, ic.key_ordinal, ic.index_column_id
            """
        ),
        {"table": table},
    ).mappings()
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
        clustered = "CLUSTERED " if str(first["type_desc"]) == "CLUSTERED" else "NONCLUSTERED "
        ddl = f"CREATE {unique}{clustered}INDEX {_quote(name)} ON {_quote(table)} ({', '.join(keys)})"
        if included:
            ddl += f" INCLUDE ({', '.join(included)})"
        if first["filter_definition"]:
            ddl += f" WHERE {first['filter_definition']}"
        captured.append((name, ddl))
    return captured


def upgrade() -> None:
    bind = op.get_bind()
    for table, fields in MASTER_FIELDS.items():
        columns = _columns(bind, table)
        for field, length in fields:
            arabic_field = f"{field}_ar"
            if arabic_field not in columns:
                op.add_column(table, sa.Column(arabic_field, sa.Unicode(length), nullable=True))
                bind.execute(sa.text(
                    f"UPDATE {table} SET {arabic_field} = {field} "
                    f"WHERE {arabic_field} IS NULL"
                ))

    if bind.dialect.name == "mssql":
        affected_by_table: dict[str, set[str]] = {}
        for table, field, _length in TICKET_UNICODE_FIELDS:
            affected_by_table.setdefault(table, set()).add(field)
        dependent_indexes = {
            table: _mssql_dependent_index_ddl(bind, table, fields)
            for table, fields in affected_by_table.items()
        }
        for table, indexes in dependent_indexes.items():
            for name, _ddl in indexes:
                op.drop_index(name, table_name=table)
        for table, field, length in TICKET_UNICODE_FIELDS:
            column = _columns(bind, table)[field]
            op.alter_column(
                table,
                field,
                existing_type=column["type"],
                type_=_unicode(length),
                existing_nullable=bool(column["nullable"]),
            )
        for indexes in dependent_indexes.values():
            for _name, ddl in indexes:
                bind.execute(sa.text(ddl))


def downgrade() -> None:
    for table, fields in reversed(tuple(MASTER_FIELDS.items())):
        columns = _columns(op.get_bind(), table)
        for field, _length in reversed(fields):
            arabic_field = f"{field}_ar"
            if arabic_field in columns:
                op.drop_column(table, arabic_field)
