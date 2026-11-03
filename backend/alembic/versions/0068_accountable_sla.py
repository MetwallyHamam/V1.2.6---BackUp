"""accountable SLA intervals

Revision ID: 0068_accountable_sla
Revises: 0067_scoped_contract_assignments
"""

import sqlalchemy as sa

from alembic import op

revision = "0068_accountable_sla"
down_revision = "0067_scoped_contract_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    policy_columns = {item["name"] for item in inspector.get_columns("sla_policies")}
    if "include_escalation_time" not in policy_columns:
        op.add_column("sla_policies", sa.Column("include_escalation_time", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "ticket_sla_intervals" not in inspector.get_table_names():
        op.create_table(
            "ticket_sla_intervals",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("ticket_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("interval_type", sa.String(30), nullable=False),
            sa.Column("responsible_party", sa.String(20)),
            sa.Column("comment", sa.String(1000)),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True)),
            sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        )
        op.create_index("ix_ticket_sla_intervals_ticket_started", "ticket_sla_intervals", ["ticket_id", "started_at"])


def downgrade() -> None:
    op.drop_table("ticket_sla_intervals")
    op.drop_column("sla_policies", "include_escalation_time")
