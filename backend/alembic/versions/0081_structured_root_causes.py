"""Structured root causes

Revision ID: 0081_structured_root_causes
Revises: 0080_contract_catalog_visibility
"""
import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0081_structured_root_causes"
down_revision = "0080_contract_catalog_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not table_exists(bind, "root_causes"):
        op.create_table("root_causes", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("code", sa.String(50), nullable=False, unique=True), sa.Column("name", sa.String(150), nullable=False, unique=True), sa.Column("description", sa.String(1000)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if not table_exists(bind, "ticket_root_causes"):
        op.create_table("ticket_root_causes", sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True), sa.Column("root_cause_id", id_type, sa.ForeignKey("root_causes.id", ondelete="NO ACTION"), primary_key=True), sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
        op.create_index("ix_ticket_root_causes_cause_ticket", "ticket_root_causes", ["root_cause_id", "ticket_id"])


def downgrade() -> None:
    if table_exists(op.get_bind(), "ticket_root_causes"):
        op.drop_table("ticket_root_causes")
    if table_exists(op.get_bind(), "root_causes"):
        op.drop_table("root_causes")
