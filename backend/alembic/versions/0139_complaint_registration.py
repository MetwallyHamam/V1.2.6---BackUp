"""Enhance complaint registration.

Revision ID: 0139_complaint_registration
Revises: 0138_customer_success
"""
import sqlalchemy as sa

from alembic import op

revision = "0139_complaint_registration"
down_revision = "0138_customer_success"
branch_labels = None
depends_on = None


def upgrade() -> None:
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "complaint_subject_engineers",
        sa.Column("complaint_id", id_type, sa.ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("engineer_user_id", id_type, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("added_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )


def downgrade() -> None:
    op.drop_table("complaint_subject_engineers")
