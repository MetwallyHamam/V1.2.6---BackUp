"""flag existing client portal tickets"""

import sqlalchemy as sa

from alembic import op

revision = "0045_flag_portal_tickets"
down_revision = "0044_knowledge_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE tickets SET source_channel='CLIENT_PORTAL' WHERE created_by_user_id IN (SELECT id FROM users WHERE user_type='CLIENT_PORTAL')"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE tickets SET source_channel='WEB' WHERE source_channel='CLIENT_PORTAL'"))
