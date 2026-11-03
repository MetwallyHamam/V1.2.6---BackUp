"""Outlook email integration foundation

Revision ID: 0078_outlook_email_foundation
Revises: 0077_entitlement_approvals
"""

import sqlalchemy as sa

from alembic import op

revision = "0078_outlook_email_foundation"
down_revision = "0077_entitlement_approvals"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("site_settings") as batch:
        batch.alter_column("value", existing_type=sa.String(500), type_=sa.Text(), existing_nullable=False)
    op.create_table("outlook_email_templates",
        sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("event_key", sa.String(40), nullable=False, unique=True),
        sa.Column("subject_template", sa.String(300), nullable=False), sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("outlook_subscriptions",
        sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("graph_subscription_id", sa.String(200), nullable=False, unique=True),
        sa.Column("mailbox_address", sa.String(320), nullable=False), sa.Column("resource", sa.String(500), nullable=False), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("delta_link", sa.Text()), sa.Column("last_notification_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.String(1000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outlook_subscription_status_expiry", "outlook_subscriptions", ["status", "expires_at"])
    op.create_table("outlook_notifications",
        sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("deduplication_key", sa.String(64), nullable=False), sa.Column("subscription_id", sa.String(200), nullable=False),
        sa.Column("resource", sa.String(1000), nullable=False), sa.Column("change_type", sa.String(30), nullable=False), sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(1000)), sa.Column("received_at", sa.DateTime(timezone=True), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("deduplication_key", name="uq_outlook_notification_dedup"),
    )
    op.create_index("ix_outlook_notification_queue", "outlook_notifications", ["status", "next_attempt_at", "received_at"])
    op.create_table("outlook_messages",
        sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("graph_message_id", sa.String(500), nullable=False), sa.Column("internet_message_id", sa.String(500)),
        sa.Column("conversation_id", sa.String(500)), sa.Column("sender_address", sa.String(320), nullable=False), sa.Column("normalized_subject", sa.String(300), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("client_id", id_type, sa.ForeignKey("clients.id")), sa.Column("contact_id", id_type, sa.ForeignKey("contacts.id")),
        sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id")), sa.Column("comment_id", id_type, sa.ForeignKey("ticket_comments.id")), sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("last_error", sa.String(1000)), sa.Column("received_at", sa.DateTime(timezone=True), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("graph_message_id", name="uq_outlook_graph_message"),
    )
    op.create_index("ix_outlook_internet_message", "outlook_messages", ["internet_message_id"])
    op.create_index("ix_outlook_conversation", "outlook_messages", ["conversation_id"])
    op.create_index("ix_outlook_message_status_received", "outlook_messages", ["status", "received_at"])


def downgrade() -> None:
    op.drop_table("outlook_messages"); op.drop_table("outlook_notifications"); op.drop_table("outlook_subscriptions"); op.drop_table("outlook_email_templates")
    with op.batch_alter_table("site_settings") as batch:
        batch.alter_column("value", existing_type=sa.Text(), type_=sa.String(500), existing_nullable=False)
