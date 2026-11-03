"""Remove SQL Server-hostile nullable unique constraints from notification ledger.

Revision ID: 0240_contract_notify_null
Revises: 0239_contract_notify_log
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0240_contract_notify_null"
down_revision: str | None = "0239_contract_notify_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "mssql":
        return
    # Migration 0239 used unnamed UNIQUE constraints. SQL Server permits only
    # one NULL in each, so the second SYSTEM recipient fails on NULL outbox_id.
    # Discover their generated names instead of assuming a server-specific name.
    op.execute(
        """
        DECLARE @drop_sql nvarchar(max) = N'';
        SELECT @drop_sql = @drop_sql
            + N'ALTER TABLE [contract_expiration_notification_deliveries] DROP CONSTRAINT '
            + QUOTENAME(kc.[name]) + N';'
        FROM sys.key_constraints AS kc
        INNER JOIN sys.tables AS t ON t.[object_id] = kc.[parent_object_id]
        INNER JOIN sys.index_columns AS ic
            ON ic.[object_id] = kc.[parent_object_id]
           AND ic.[index_id] = kc.[unique_index_id]
        INNER JOIN sys.columns AS c
            ON c.[object_id] = ic.[object_id]
           AND c.[column_id] = ic.[column_id]
        WHERE kc.[type] = 'UQ'
          AND t.[name] = 'contract_expiration_notification_deliveries'
          AND c.[name] IN ('notification_id', 'outbox_id');
        IF LEN(@drop_sql) > 0 EXEC sp_executesql @drop_sql;
        """
    )


def downgrade() -> None:
    # Reintroducing these constraints would recreate the production defect.
    pass
