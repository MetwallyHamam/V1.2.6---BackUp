"""Add governed ticket notification rules.

Revision ID: 0095_ticket_notify
Revises: 0094_scope_shift
"""
import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0095_ticket_notify"
down_revision = "0094_scope_shift"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind(); id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not column_exists(bind, "users", "support_notification_email"):
        op.add_column("users", sa.Column("support_notification_email", sa.String(320), nullable=True))
    if not table_exists(bind, "ticket_notification_rules"):
        op.create_table("ticket_notification_rules", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("creator_profile_ids_json", sa.Text(), nullable=False, server_default="[]"), sa.Column("assigned_engineer_ids_json", sa.Text(), nullable=False, server_default="[]"), sa.Column("match_mode", sa.String(10), nullable=False, server_default="ANY"), sa.Column("to_json", sa.Text(), nullable=False, server_default="[]"), sa.Column("cc_json", sa.Text(), nullable=False, server_default="[]"), sa.Column("include_matched_engineer_email", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("evaluate_initial_assignment", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("evaluate_later_reassignment", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("match_mode IN ('ANY','ALL')", name="ck_ticket_notification_rule_match_mode"))
        op.create_index("ix_ticket_notification_rules_enabled", "ticket_notification_rules", ["is_enabled"])

def downgrade() -> None:
    bind = op.get_bind()
    if table_exists(bind, "ticket_notification_rules"):
        op.drop_index("ix_ticket_notification_rules_enabled", table_name="ticket_notification_rules"); op.drop_table("ticket_notification_rules")
    if column_exists(bind, "users", "support_notification_email"): op.drop_column("users", "support_notification_email")
