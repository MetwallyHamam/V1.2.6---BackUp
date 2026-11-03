"""allow multiple unconverted pre-tickets on SQL Server.

Revision ID: 0183_pre_ticket_result_unique
Revises: 0182_pre_ticket_form_context
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0183_pre_ticket_result_unique"
down_revision: str | None = "0182_pre_ticket_form_context"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mssql":
        # SQLAlchemy's pymssql dialect does not implement unique-constraint
        # reflection. Query SQL Server's catalog directly so this also works
        # with auto-generated constraint names in existing installations.
        schema_name = bind.dialect.default_schema_name or "dbo"
        matching = list(
            bind.execute(
                sa.text(
                    """
                    SELECT kc.name
                    FROM sys.key_constraints AS kc
                    JOIN sys.tables AS t ON t.object_id = kc.parent_object_id
                    JOIN sys.schemas AS s ON s.schema_id = t.schema_id
                    JOIN sys.index_columns AS ic
                      ON ic.object_id = kc.parent_object_id
                     AND ic.index_id = kc.unique_index_id
                    JOIN sys.columns AS c
                      ON c.object_id = ic.object_id
                     AND c.column_id = ic.column_id
                    WHERE kc.type = 'UQ'
                      AND s.name = :schema_name
                      AND t.name = 'engineer_pre_tickets'
                    GROUP BY kc.name
                    HAVING COUNT(*) = 1
                       AND MAX(CASE WHEN c.name = 'resulting_ticket_id' THEN 1 ELSE 0 END) = 1
                    """
                ),
                {"schema_name": schema_name},
            ).scalars()
        )
        if len(matching) != 1:
            raise RuntimeError(
                "Expected one SQL Server unique constraint on engineer_pre_tickets.resulting_ticket_id."
            )
        op.drop_constraint(matching[0], "engineer_pre_tickets", type_="unique")
    op.create_index(
        "uq_engineer_pre_ticket_result",
        "engineer_pre_tickets",
        ["resulting_ticket_id"],
        unique=True,
        mssql_where=sa.text("resulting_ticket_id IS NOT NULL"),
        sqlite_where=sa.text("resulting_ticket_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_engineer_pre_ticket_result", table_name="engineer_pre_tickets")
    if op.get_bind().dialect.name == "mssql":
        op.create_unique_constraint(
            "uq_engineer_pre_ticket_resulting_ticket",
            "engineer_pre_tickets",
            ["resulting_ticket_id"],
        )
