"""Allow multiple users without employee codes.

Revision ID: 0021_nullable_employee_code
Revises: 0020_notification_preferences
"""

import sqlalchemy as sa

from alembic import op

revision = "0021_nullable_employee_code"
down_revision = "0020_notification_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "mssql":
        op.execute(
            """
            DECLARE @constraint_name sysname;
            SELECT TOP (1) @constraint_name = kc.name
            FROM sys.key_constraints AS kc
            JOIN sys.index_columns AS ic
              ON ic.object_id = kc.parent_object_id
             AND ic.index_id = kc.unique_index_id
            JOIN sys.columns AS c
              ON c.object_id = ic.object_id
             AND c.column_id = ic.column_id
            WHERE kc.parent_object_id = OBJECT_ID(N'dbo.users')
              AND kc.[type] = 'UQ'
              AND c.name = N'employee_code';
            IF @constraint_name IS NOT NULL
            BEGIN
                DECLARE @drop_sql nvarchar(500);
                SET @drop_sql = N'ALTER TABLE dbo.users DROP CONSTRAINT '
                    + QUOTENAME(@constraint_name);
                EXEC sys.sp_executesql @drop_sql;
            END;
            IF NOT EXISTS (
                SELECT 1 FROM sys.indexes
                WHERE object_id = OBJECT_ID(N'dbo.users')
                  AND name = N'ux_users_employee_code_not_null'
            )
                CREATE UNIQUE INDEX ux_users_employee_code_not_null
                    ON dbo.users(employee_code)
                    WHERE employee_code IS NOT NULL;
            """
        )
    else:
        op.create_index(
            "ux_users_employee_code_not_null",
            "users",
            ["employee_code"],
            unique=True,
            sqlite_where=sa.text("employee_code IS NOT NULL"),
        )


def downgrade() -> None:
    op.drop_index("ux_users_employee_code_not_null", table_name="users")
    if op.get_bind().dialect.name == "mssql":
        op.create_unique_constraint(
            "uq_users_employee_code", "users", ["employee_code"]
        )
