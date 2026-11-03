"""scope API credentials to inbound vendors and add WhatsApp ticket type.

Revision ID: 0191_inbound_vendor_profiles
Revises: 0190_inbound_pre_ticket
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0191_inbound_vendor_profiles"
down_revision: str | None = "0190_inbound_pre_ticket"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("integration_api_clients")}
    if "provider_key" not in columns:
        op.add_column("integration_api_clients", sa.Column("provider_key", sa.String(40)))
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("integration_api_clients")}
    if "ix_integration_api_clients_provider" not in indexes:
        op.create_index("ix_integration_api_clients_provider", "integration_api_clients", ["provider_key", "is_active"])
    ticket_types = sa.table(
        "ticket_types",
        sa.column("code"), sa.column("name"), sa.column("name_ar"),
        sa.column("color"), sa.column("number_prefix"), sa.column("is_active"),
    )
    if op.get_bind().scalar(sa.select(ticket_types.c.code).where(ticket_types.c.code == "WHATSAPP")) is None:
        op.get_bind().execute(sa.insert(ticket_types).values(code="WHATSAPP", name="WhatsApp", name_ar="واتساب", color="#25D366", number_prefix="WAP", is_active=True))


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM ticket_types WHERE code='WHATSAPP'"))
    bind = op.get_bind()
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("integration_api_clients")}
    if "ix_integration_api_clients_provider" in indexes:
        op.drop_index("ix_integration_api_clients_provider", table_name="integration_api_clients")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("integration_api_clients")}
    if "provider_key" in columns:
        op.drop_column("integration_api_clients", "provider_key")
