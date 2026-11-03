"""add escalation rule editing concurrency metadata

Revision ID: 0157_escalation_rule_editing
Revises: 0156_hr_project_dashboards
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0157_escalation_rule_editing"
down_revision: str | None = "0156_hr_project_dashboards"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("escalation_rules")}
    if "version" not in existing:
        op.add_column(
            "escalation_rules",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )
    if "created_at" not in existing:
        op.add_column(
            "escalation_rules",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        )
    if "updated_at" not in existing:
        op.add_column(
            "escalation_rules",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        )


def downgrade() -> None:
    op.drop_column("escalation_rules", "updated_at")
    op.drop_column("escalation_rules", "created_at")
    op.drop_column("escalation_rules", "version")
