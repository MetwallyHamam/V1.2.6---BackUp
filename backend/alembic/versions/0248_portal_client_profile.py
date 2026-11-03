"""Add the independent client portal profile permission.

Revision ID: 0248_portal_client_profile
Revises: 0247_portal_ticket_satisfaction
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0248_portal_client_profile"
down_revision: str | None = "0247_portal_ticket_satisfaction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    permission_id = bind.execute(
        sa.text("SELECT id FROM permissions WHERE code = :code"),
        {"code": "portal.client_profile.view"},
    ).scalar()
    if permission_id is None:
        bind.execute(
            sa.text("INSERT INTO permissions (code, module, description, is_high_risk, is_active) VALUES (:code, :module, :description, :risk, :active)"),
            {"code": "portal.client_profile.view", "module": "client_portal", "description": "View the scoped client profile in the client portal", "risk": False, "active": True},
        )
        permission_id = bind.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"),
            {"code": "portal.client_profile.view"},
        ).scalar_one()
    profile_id = bind.execute(
        sa.text("SELECT id FROM profiles WHERE code = :code"), {"code": "CLIENT_PORTAL"}
    ).scalar()
    if profile_id is not None:
        exists = bind.execute(
            sa.text("SELECT permission_id FROM profile_permissions WHERE profile_id = :profile_id AND permission_id = :permission_id"),
            {"profile_id": profile_id, "permission_id": permission_id},
        ).first()
        if exists is None:
            bind.execute(
                sa.text("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) VALUES (:profile_id, :permission_id, :scope_type)"),
                {"profile_id": profile_id, "permission_id": permission_id, "scope_type": "CLIENT"},
            )


def downgrade() -> None:
    bind = op.get_bind()
    permission_id = bind.execute(
        sa.text("SELECT id FROM permissions WHERE code = :code"),
        {"code": "portal.client_profile.view"},
    ).scalar()
    if permission_id is not None:
        bind.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id = :permission_id"), {"permission_id": permission_id})
        bind.execute(sa.text("DELETE FROM permissions WHERE id = :permission_id"), {"permission_id": permission_id})
