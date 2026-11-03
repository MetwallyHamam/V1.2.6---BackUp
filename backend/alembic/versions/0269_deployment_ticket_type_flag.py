"""Control which ticket types are available to deployment issues.

Revision ID: 0269_deployment_ticket_types
Revises: 0268_deployment_links
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0269_deployment_ticket_types"
down_revision: str | None = "0268_deployment_links"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _columns() -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns("ticket_types")}


def upgrade() -> None:
    if "available_for_deployment_issue" not in _columns():
        op.add_column(
            "ticket_types",
            sa.Column(
                "available_for_deployment_issue",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    op.execute(
        sa.text(
            "UPDATE ticket_types SET available_for_deployment_issue = 1 "
            "WHERE code IN ('INCIDENT', 'SERVICE_REQUEST')"
        )
    )


def downgrade() -> None:
    if "available_for_deployment_issue" not in _columns():
        return
    if op.get_bind().dialect.name == "mssql":
        op.execute(
            """
            DECLARE @constraint_name sysname;
            SELECT @constraint_name = dc.name
            FROM sys.default_constraints dc
            JOIN sys.columns c
              ON c.default_object_id = dc.object_id
            WHERE dc.parent_object_id = OBJECT_ID('ticket_types')
              AND c.name = 'available_for_deployment_issue';
            IF @constraint_name IS NOT NULL
                EXEC('ALTER TABLE ticket_types DROP CONSTRAINT [' + @constraint_name + ']');
            """
        )
    op.drop_column("ticket_types", "available_for_deployment_issue")
