"""Add ticket due dates and context-edit permissions."""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0064_ticket_edit_context"
down_revision = "0063_dynamic_dashboards"
branch_labels = None
depends_on = None

PERMISSIONS = (
    "ticket.change.client",
    "ticket.change.contract",
    "ticket.edit.due_date",
)


def upgrade() -> None:
    if not column_exists(op.get_bind(), "tickets", "due_at"):
        op.add_column("tickets", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    for code in PERMISSIONS:
        op.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','tickets','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
    for profile in ("ADMINISTRATOR", "SUPPORT_MANAGER"):
        for code in PERMISSIONS:
            op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='{profile}' AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined = "','".join(PERMISSIONS)
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
    op.drop_column("tickets", "due_at")
