"""Persist reusable public-link token ciphertext.

Revision ID: 0140_unified_send_actions
Revises: 0139_complaint_registration
"""
import sqlalchemy as sa

from alembic import op

revision = "0140_unified_send_actions"
down_revision = "0139_complaint_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ticket_live_updates",sa.Column("token_ciphertext",sa.Text()))
    op.add_column("complaint_public_tokens",sa.Column("token_ciphertext",sa.Text()))


def downgrade() -> None:
    op.drop_column("complaint_public_tokens","token_ciphertext")
    op.drop_column("ticket_live_updates","token_ciphertext")
