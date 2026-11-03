"""add employee hire date

Revision ID: 0051_user_hire_date
Revises: 0050_presence_site_settings
"""
import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0051_user_hire_date"
down_revision = "0050_presence_site_settings"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not column_exists(op.get_bind(), "users", "hire_date"):
        op.add_column("users", sa.Column("hire_date", sa.Date()))

def downgrade() -> None:
    op.drop_column("users", "hire_date")
