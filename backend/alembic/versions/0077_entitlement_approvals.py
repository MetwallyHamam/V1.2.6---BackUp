"""unified entitlement approval persistence

Revision ID: 0077_entitlement_approvals
Revises: 0076_sla_match_reason
"""

import sqlalchemy as sa

from alembic import op

revision = "0077_entitlement_approvals"
down_revision = "0076_sla_match_reason"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("approval_groups",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("approval_group_members",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("group_id", id_type, sa.ForeignKey("approval_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_approval_group_member"),
    )
    op.create_table("entitlement_approvals",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("source_channel", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("reason_code", sa.String(60), nullable=False),
        sa.Column("requested_action", sa.String(30), nullable=False),
        sa.Column("justification", sa.String(1000), nullable=False),
        sa.Column("request_payload_json", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("feature_mode", sa.String(20), nullable=False),
        sa.Column("policy_id", id_type, sa.ForeignKey("feature_policies.id")),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("policy_scope", sa.String(200), nullable=False),
        sa.Column("client_id", id_type, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("contract_id", id_type, sa.ForeignKey("contracts.id")),
        sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id")),
        sa.Column("approval_group_id", id_type, sa.ForeignKey("approval_groups.id")),
        sa.Column("requested_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decided_by_user_id", id_type, sa.ForeignKey("users.id")),
        sa.Column("decision_comment", sa.String(1000)),
        sa.Column("approval_deadline", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_entitlement_approval_idempotency"),
        sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','EXPIRED','CANCELLED','COMPLETED')", name="ck_entitlement_approval_status"),
    )
    op.create_index("ix_entitlement_approval_queue", "entitlement_approvals", ["status", "approval_deadline", "created_at"])
    op.create_index("ix_entitlement_approval_requester", "entitlement_approvals", ["requested_by_user_id", "created_at"])
    op.create_table("entitlement_approval_history",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("approval_id", id_type, sa.ForeignKey("entitlement_approvals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(30)),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("comment", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_entitlement_approval_history_request", "entitlement_approval_history", ["approval_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_entitlement_approval_history_request", table_name="entitlement_approval_history")
    op.drop_table("entitlement_approval_history")
    op.drop_index("ix_entitlement_approval_requester", table_name="entitlement_approvals")
    op.drop_index("ix_entitlement_approval_queue", table_name="entitlement_approvals")
    op.drop_table("entitlement_approvals")
    op.drop_table("approval_group_members")
    op.drop_table("approval_groups")
