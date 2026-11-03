"""add configurable ticket creation fields

Revision ID: 0032_ticket_form_settings
Revises: 0031_saved_view_team_scope
"""

import sqlalchemy as sa

from alembic import op

revision = "0032_ticket_form_settings"
down_revision = "0031_saved_view_team_scope"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


FIELD_KEYS = (
    "ticket_type_id", "client_id", "subject", "description", "product_id",
    "product_module_id", "category_id", "subcategory_id", "service_id",
    "environment_id", "impact", "urgency", "priority", "affected_users",
    "first_occurred_at", "patient_safety_flag", "security_incident_flag",
    "requester_contact_id", "branch_id", "assigned_team", "assigned_user_id",
    "follower_user_ids",
)


def upgrade() -> None:
    table = op.create_table(
        "ticket_form_field_settings",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("field_key", sa.String(length=80), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("field_key", name="uq_ticket_form_field_settings_key"),
    )
    op.create_index("ix_ticket_form_field_settings_field_key", "ticket_form_field_settings", ["field_key"], unique=True)
    op.bulk_insert(table, [{"field_key": key, "is_visible": True, "is_required": False} for key in FIELD_KEYS])


def downgrade() -> None:
    op.drop_index("ix_ticket_form_field_settings_field_key", table_name="ticket_form_field_settings")
    op.drop_table("ticket_form_field_settings")

