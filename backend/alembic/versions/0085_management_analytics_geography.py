"""management analytics geography

Revision ID: 0085_mgmt_geo
Revises: 0084_unified_email_queue
"""
import sqlalchemy as sa

from alembic import op

revision = "0085_mgmt_geo"
down_revision = "0084_unified_email_queue"
branch_labels = None
depends_on = None

def upgrade():
    for table in ("clients", "branches"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}
        if "country" not in columns:
            op.add_column(table, sa.Column("country", sa.String(100), nullable=True))
        if "zone" not in columns:
            op.add_column(table, sa.Column("zone", sa.String(100), nullable=True))

def downgrade():
    for table in ("branches", "clients"):
        op.drop_column(table, "zone")
        op.drop_column(table, "country")
