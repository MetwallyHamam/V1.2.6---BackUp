"""add type-specific work assignment context

Revision ID: 0278_work_assignment_context
Revises: 0277_work_assignments
"""

import sqlalchemy as sa

from alembic import op

revision = "0278_work_assignment_context"
down_revision = "0277_work_assignments"
branch_labels = None
depends_on = None


def _drop_sql_server_default_constraint(column_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mssql":
        return
    op.execute(
        sa.text(
            """
            DECLARE @constraint_name sysname;
            DECLARE @drop_sql nvarchar(max);
            SELECT @constraint_name = dc.name
            FROM sys.default_constraints AS dc
            JOIN sys.columns AS c
              ON c.object_id = dc.parent_object_id
             AND c.column_id = dc.parent_column_id
            WHERE dc.parent_object_id = OBJECT_ID(N'work_assignments')
              AND c.name = :column_name;

            IF @constraint_name IS NOT NULL
            BEGIN
                SET @drop_sql = N'ALTER TABLE work_assignments DROP CONSTRAINT '
                    + QUOTENAME(@constraint_name);
                EXEC sys.sp_executesql @drop_sql;
            END;
            """
        ).bindparams(column_name=column_name)
    )


def _set_activity_classification_default(value: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("work_assignments") as batch:
            batch.alter_column(
                "activity_classification",
                existing_type=sa.String(20),
                server_default=value,
                existing_nullable=False,
            )
        return

    _drop_sql_server_default_constraint("activity_classification")
    op.alter_column(
        "work_assignments",
        "activity_classification",
        existing_type=sa.String(20),
        server_default=value,
        existing_nullable=False,
    )


def upgrade() -> None:
    op.add_column(
        "work_assignments",
        sa.Column("context_json", sa.Text(), nullable=False, server_default="{}"),
    )
    _set_activity_classification_default("EXTERNAL")


def downgrade() -> None:
    _set_activity_classification_default("INTERNAL")
    op.drop_column("work_assignments", "context_json")
