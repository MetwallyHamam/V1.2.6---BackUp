"""Allow several deployment issues to share one incident.

Revision ID: 0268_deployment_links
Revises: 0267_deployment_defaults
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0268_deployment_links"
down_revision: str | None = "0267_deployment_defaults"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _indexes() -> dict[str, dict[str, object]]:
    return {
        str(index["name"]): index
        for index in sa.inspect(op.get_bind()).get_indexes("deployment_issues")
    }


def upgrade() -> None:
    indexes = _indexes()
    if "uq_deployment_issues_linked_ticket" in indexes:
        op.drop_index("uq_deployment_issues_linked_ticket", table_name="deployment_issues")
    if "ix_deployment_issues_linked_ticket" not in indexes:
        op.create_index(
            "ix_deployment_issues_linked_ticket",
            "deployment_issues",
            ["linked_ticket_id"],
            unique=False,
        )


def downgrade() -> None:
    indexes = _indexes()
    if "ix_deployment_issues_linked_ticket" in indexes:
        op.drop_index("ix_deployment_issues_linked_ticket", table_name="deployment_issues")
    if "uq_deployment_issues_linked_ticket" not in indexes:
        op.create_index(
            "uq_deployment_issues_linked_ticket",
            "deployment_issues",
            ["linked_ticket_id"],
            unique=True,
            mssql_where=sa.text("linked_ticket_id IS NOT NULL"),
            sqlite_where=sa.text("linked_ticket_id IS NOT NULL"),
        )
