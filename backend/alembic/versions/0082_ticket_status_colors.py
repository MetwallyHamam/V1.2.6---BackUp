"""Configurable ticket status colors

Revision ID: 0082_ticket_status_colors
Revises: 0081_structured_root_causes
"""
import sqlalchemy as sa

from alembic import op

revision = "0082_ticket_status_colors"
down_revision = "0081_structured_root_causes"
branch_labels = None
depends_on = None

DEFAULTS = {"NEW":"#607D8B","TRIAGED":"#5C6BC0","ASSIGNED":"#7E57C2","IN_PROGRESS":"#0288D1","PENDING_CLIENT":"#F9A825","PENDING_INTERNAL":"#FB8C00","PENDING_VENDOR":"#EF6C00","RESOLVED":"#2E7D32","CLIENT_CONFIRMATION":"#00897B","CLOSED":"#455A64","CANCELLED":"#C62828","REOPENED":"#D81B60"}

def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("ticket_statuses")}
    if "color" not in columns:
        op.add_column("ticket_statuses", sa.Column("color", sa.String(7), nullable=True))
    for code, color in DEFAULTS.items():
        bind.execute(sa.text("UPDATE ticket_statuses SET color=:color WHERE code=:code AND color IS NULL"), {"code":code,"color":color})
    bind.execute(sa.text("UPDATE ticket_statuses SET color='#607D8B' WHERE color IS NULL"))
    with op.batch_alter_table("ticket_statuses") as batch:
        batch.alter_column("color", existing_type=sa.String(7), nullable=False, server_default="#607D8B")

def downgrade() -> None:
    if "color" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("ticket_statuses")}:
        op.drop_column("ticket_statuses", "color")
