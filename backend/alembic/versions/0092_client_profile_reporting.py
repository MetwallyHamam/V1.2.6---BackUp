"""Add client support commencement date.

Revision ID: 0092_client_profile
Revises: 0091_department_master
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0092_client_profile"
down_revision = "0091_department_master"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "clients", "support_started_at"):
        op.add_column("clients", sa.Column("support_started_at", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if column_exists(bind, "clients", "support_started_at"):
        op.drop_column("clients", "support_started_at")
