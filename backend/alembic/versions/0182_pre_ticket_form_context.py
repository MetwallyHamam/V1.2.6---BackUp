"""add configurable pre-ticket form context.

Revision ID: 0182_pre_ticket_form_context
Revises: 0181_pre_ticket_queue_views
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0182_pre_ticket_form_context"
down_revision: str | None = "0181_pre_ticket_queue_views"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("engineer_pre_tickets") as batch:
        batch.alter_column("client_id", existing_type=sa.BigInteger(), nullable=True)
        batch.alter_column("requester_contact_id", existing_type=sa.BigInteger(), nullable=True)
        batch.alter_column("product_id", existing_type=sa.BigInteger(), nullable=True)
        batch.add_column(sa.Column("product_module_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("service_id", sa.BigInteger(), nullable=True))
        batch.create_foreign_key("fk_pre_ticket_product_module", "product_modules", ["product_module_id"], ["id"])
        batch.create_foreign_key("fk_pre_ticket_service", "service_catalog_items", ["service_id"], ["id"])
    table = sa.table("ticket_form_field_settings", sa.column("field_key", sa.String), sa.column("is_visible", sa.Boolean), sa.column("is_required", sa.Boolean), sa.column("default_value", sa.String))
    op.bulk_insert(table, [{"field_key": f"pre_ticket.{key}", "is_visible": True, "is_required": True, "default_value": None} for key in ("client_id", "requester_contact_id", "product_id", "product_module_id", "service_id")])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM ticket_form_field_settings WHERE field_key LIKE 'pre_ticket.%'"))
    with op.batch_alter_table("engineer_pre_tickets") as batch:
        batch.drop_constraint("fk_pre_ticket_service", type_="foreignkey")
        batch.drop_constraint("fk_pre_ticket_product_module", type_="foreignkey")
        batch.drop_column("service_id")
        batch.drop_column("product_module_id")
        batch.alter_column("product_id", existing_type=sa.BigInteger(), nullable=False)
        batch.alter_column("requester_contact_id", existing_type=sa.BigInteger(), nullable=False)
        batch.alter_column("client_id", existing_type=sa.BigInteger(), nullable=False)
