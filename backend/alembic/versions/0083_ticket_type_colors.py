"""Ticket type colors

Revision ID: 0083_ticket_type_colors
Revises: 0082_ticket_status_colors
"""
import sqlalchemy as sa

from alembic import op

revision = "0083_ticket_type_colors"
down_revision = "0082_ticket_status_colors"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if "color" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("ticket_types")}:
        op.add_column("ticket_types", sa.Column("color", sa.String(7), nullable=True))
    op.execute("UPDATE ticket_types SET color='#607D8B' WHERE color IS NULL")
    with op.batch_alter_table("ticket_types") as batch:
        batch.alter_column("color", existing_type=sa.String(7), nullable=False, server_default="#607D8B")

def downgrade() -> None:
    if "color" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("ticket_types")}:
        op.drop_column("ticket_types", "color")
