"""public ticket satisfaction

Revision ID: 0086_ticket_satisfaction
Revises: 0085_mgmt_geo
"""
import sqlalchemy as sa

from alembic import op

revision = "0086_ticket_satisfaction"
down_revision = "0085_mgmt_geo"
branch_labels = None
depends_on = None

def upgrade():
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    with op.batch_alter_table("email_deliveries") as batch:
        batch.alter_column("recipient_user_id", existing_type=id_type, nullable=True)
    op.create_table("ticket_satisfaction", sa.Column("id", id_type, primary_key=True), sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("engineer_user_id", id_type, sa.ForeignKey("users.id")), sa.Column("recipient_email", sa.String(320), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("service_rating", sa.Integer()), sa.Column("engineer_rating", sa.Integer()), sa.Column("comments", sa.String(2000)), sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("invitation_sent_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
    op.create_index("ix_ticket_satisfaction_token", "ticket_satisfaction", ["token_hash"], unique=True)

def downgrade():
    op.drop_table("ticket_satisfaction")
    with op.batch_alter_table("email_deliveries") as batch:
        batch.alter_column("recipient_user_id", existing_type=sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False)
