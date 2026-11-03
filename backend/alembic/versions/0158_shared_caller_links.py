"""add governed shared caller links

Revision ID: 0158_shared_caller_links
Revises: 0157_escalation_rule_editing
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0158_shared_caller_links"
down_revision: str | None = "0157_escalation_rule_editing"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "contact_client_links",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("contact_id", id_type, sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", id_type, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linked_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contact_id", "client_id"),
    )
    op.create_index("ix_contact_client_links_client", "contact_client_links", ["client_id", "contact_id"])
    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_high_risk", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(permissions, [{
        "code": "contact.link_existing",
        "module": "CRM",
        "description": "Search all callers and link an existing caller to another client",
        "is_high_risk": False,
        "is_active": True,
    }])
    op.execute(
        "INSERT INTO profile_permissions (profile_id, permission_id, scope_type) "
        "SELECT p.id, q.id, 'NONE' FROM profiles p CROSS JOIN permissions q "
        "WHERE p.code IN ('CALL_CENTER','L1_SUPPORT','L2_SUPPORT','L3_SUPPORT','SUPPORT_MANAGER','ADMINISTRATOR') "
        "AND q.code = 'contact.link_existing' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp "
        "WHERE pp.profile_id = p.id AND pp.permission_id = q.id)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'contact.link_existing')")
    op.execute("DELETE FROM permissions WHERE code = 'contact.link_existing'")
    op.drop_index("ix_contact_client_links_client", table_name="contact_client_links")
    op.drop_table("contact_client_links")
