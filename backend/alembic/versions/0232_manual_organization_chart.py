"""Add independent manual organization chart.

Revision ID: 0232_manual_org_chart
Revises: 0231_sla_client_dependency_flags
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0232_manual_org_chart"
down_revision: str | None = "0231_sla_client_dependency_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_chart_nodes",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("parent_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("organization_chart_nodes.id")),
        sa.Column("name", sa.Unicode(200), nullable=False),
        sa.Column("node_type", sa.String(30), nullable=False),
        sa.Column("title", sa.Unicode(150)),
        sa.Column("image_url", sa.String(1000)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone_number", sa.String(50)),
        sa.Column("notes", sa.Unicode(1000)),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_organization_chart_not_self"),
    )
    op.create_index("ix_organization_chart_parent", "organization_chart_nodes", ["parent_id", "sort_order"])


def downgrade() -> None:
    op.drop_index("ix_organization_chart_parent", table_name="organization_chart_nodes")
    op.drop_table("organization_chart_nodes")
