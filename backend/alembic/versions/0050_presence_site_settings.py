"""presence and public site settings

Revision ID: 0050_presence_site_settings
Revises: 0049_dynamic_contract_sla
"""
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0050_presence_site_settings"
down_revision = "0049_dynamic_contract_sla"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "users", "last_seen_at"):
        op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    if not column_exists(bind, "users", "profile_picture_url"):
        op.add_column("users", sa.Column("profile_picture_url", sa.String(1000)))
    if not table_exists(bind, "site_settings"):
        op.create_table("site_settings", sa.Column("key", sa.String(100), primary_key=True), sa.Column("value", sa.String(500), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    now = datetime.now(UTC)
    settings = {"default_theme": "SYSTEM", "default_sound": "true", "default_assignee_user_id": "", "assign_available_only": "false", "assign_online_only": "false"}
    table = sa.table("site_settings", sa.column("key", sa.String), sa.column("value", sa.String), sa.column("updated_at", sa.DateTime(timezone=True)))
    for key, value in settings.items():
        exists = bind.scalar(sa.select(sa.literal(1)).select_from(table).where(table.c.key == key))
        if not exists:
            op.bulk_insert(table, [{"key": key, "value": value, "updated_at": now}])

def downgrade() -> None:
    op.drop_table("site_settings")
    op.drop_column("users", "last_seen_at")
    op.drop_column("users", "profile_picture_url")
