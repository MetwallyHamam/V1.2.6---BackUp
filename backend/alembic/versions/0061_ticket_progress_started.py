"""Track ticket progress start and administrative override."""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0061_ticket_progress_started"
down_revision = "0060_notification_filters_views"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not column_exists(op.get_bind(), "tickets", "progress_started_at"):
        op.add_column("tickets", sa.Column("progress_started_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT 'ticket.start_progress_any','ticket','Start progress on any visible ticket',1,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='ticket.start_progress_any')"))
    for profile in ("ADMINISTRATOR", "SUPPORT_MANAGER"):
        op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='{profile}' AND pm.code='ticket.start_progress_any' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code='ticket.start_progress_any')"))
    op.execute(sa.text("DELETE FROM permissions WHERE code='ticket.start_progress_any'"))
    op.drop_column("tickets", "progress_started_at")
