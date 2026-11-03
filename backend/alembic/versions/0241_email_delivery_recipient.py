"""Deduplicate external email delivery by address and quarantine stuck contract sends.

Revision ID: 0241_email_recipient_key
Revises: 0240_contract_notify_null
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0241_email_recipient_key"
down_revision: str | None = "0240_contract_notify_null"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A PROCESSING contract event reached SMTP but failed while persisting its
    # second nullable recipient row. Treat it as sent to prevent another email.
    op.execute(
        """
        UPDATE event_outbox
        SET status = 'SENT', next_attempt_at = NULL
        WHERE event_type = 'CONTRACT_EXPIRATION_EMAIL' AND status = 'PROCESSING'
        """
    )
    op.execute(
        """
        UPDATE contract_expiration_notification_deliveries
        SET status = 'SENT', sent_at = COALESCE(sent_at, updated_at),
            failed_at = NULL, last_error = NULL
        WHERE outbox_id IN (
            SELECT id FROM event_outbox
            WHERE event_type = 'CONTRACT_EXPIRATION_EMAIL' AND status = 'SENT'
        ) AND status = 'QUEUED'
        """
    )
    op.drop_index("ix_email_delivery_outbox_recipient", table_name="email_deliveries")
    op.create_index(
        "ix_email_delivery_outbox_recipient",
        "email_deliveries",
        ["outbox_id", "recipient_email"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_email_delivery_outbox_recipient", table_name="email_deliveries")
    op.create_index(
        "ix_email_delivery_outbox_recipient",
        "email_deliveries",
        ["outbox_id", "recipient_user_id"],
        unique=True,
    )
