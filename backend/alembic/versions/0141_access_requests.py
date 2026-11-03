"""governed in-context access requests

Revision ID: 0141_access_requests
Revises: 0140_unified_send_actions
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0141_access_requests"
down_revision: str | None = "0140_unified_send_actions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

def upgrade() -> None:
    op.create_table("access_requests", sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True), sa.Column("requester_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False), sa.Column("permission_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("permissions.id"), nullable=False), sa.Column("resource", sa.String(300), nullable=False), sa.Column("return_path", sa.String(500)), sa.Column("justification", sa.String(1000), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("decided_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("status IN ('PENDING','APPROVED','DENIED','CANCELLED','EXPIRED')"))
    op.create_index("ix_access_requests_requester_status", "access_requests", ["requester_user_id", "status"])
    op.create_index("ix_access_requests_permission_status", "access_requests", ["permission_id", "status"])
    op.create_table("access_request_decisions", sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True), sa.Column("access_request_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("access_requests.id"), nullable=False), sa.Column("actor_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False), sa.Column("action", sa.String(30), nullable=False), sa.Column("reason", sa.String(1000), nullable=False), sa.Column("grant_expires_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("permission_step_up_challenges", sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True), sa.Column("actor_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_permission_step_up_actor_expiry", "permission_step_up_challenges", ["actor_user_id", "expires_at"])
    permissions = sa.table("permissions", sa.column("code", sa.String), sa.column("module", sa.String), sa.column("description", sa.String), sa.column("is_high_risk", sa.Boolean), sa.column("is_active", sa.Boolean))
    op.bulk_insert(permissions, [{"code":"permission.grant.in_context","module":"IAM","description":"Review and grant eligible in-context access requests","is_high_risk":True,"is_active":True}])

def downgrade() -> None:
    op.drop_table("permission_step_up_challenges")
    op.drop_table("access_request_decisions")
    op.drop_table("access_requests")
    op.execute("DELETE FROM permissions WHERE code = 'permission.grant.in_context'")
