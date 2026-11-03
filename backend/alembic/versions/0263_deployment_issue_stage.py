"""Classify deployment issues by when they occurred.

Revision ID: 0263_deployment_issue_stage
Revises: 0262_deployment_schema_reconcile
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0263_deployment_issue_stage"
down_revision: str | None = "0262_deployment_schema_reconcile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("deployment_issues")}
    if "occurrence_stage" not in columns:
        op.add_column(
            "deployment_issues",
            sa.Column(
                "occurrence_stage",
                sa.String(30),
                nullable=False,
                server_default="DURING_DEPLOYMENT",
            ),
        )


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("deployment_issues")}
    if "occurrence_stage" in columns:
        op.drop_column("deployment_issues", "occurrence_stage")
