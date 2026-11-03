"""Add a dedicated permission for sending ticket live-update links.

Revision ID: 0133_live_update_permission
Revises: 0132_service_module_links
"""

import sqlalchemy as sa

from alembic import op

revision = "0133_live_update_permission"
down_revision = "0132_service_module_links"
branch_labels = None
depends_on = None

PERMISSION_CODE = "ticket.live_update.send"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO permissions (code, module, description, is_high_risk, is_active) "
            "SELECT :code, 'ticket', :description, 0, 1 "
            "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = :code)"
        ),
        {
            "code": PERMISSION_CODE,
            "description": "Send and copy public ticket live-update links",
        },
    )
    bind.execute(
        sa.text(
            "INSERT INTO profile_permissions (profile_id, permission_id, scope_type) "
            "SELECT existing.profile_id, live_update.id, 'NONE' "
            "FROM profile_permissions existing "
            "JOIN permissions public_comment ON public_comment.id = existing.permission_id "
            "CROSS JOIN permissions live_update "
            "WHERE public_comment.code = 'ticket.comment.public' "
            "AND live_update.code = :code "
            "AND NOT EXISTS ("
            "SELECT 1 FROM profile_permissions assigned "
            "WHERE assigned.profile_id = existing.profile_id "
            "AND assigned.permission_id = live_update.id"
            ")"
        ),
        {"code": PERMISSION_CODE},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM profile_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = :code)"
        ),
        {"code": PERMISSION_CODE},
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE code = :code"),
        {"code": PERMISSION_CODE},
    )
