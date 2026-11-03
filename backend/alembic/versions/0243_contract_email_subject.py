"""Include contract name in the default expiration email subject.

Revision ID: 0243_contract_email_subject
Revises: 0242_contract_email_key
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0243_contract_email_subject"
down_revision: str | None = "0242_contract_email_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_SUBJECT = "Contract {contract_number} expires in {days_remaining} day(s)"
NEW_SUBJECT = "Contract {contract_number} — {contract_name} expires in {days_remaining} day(s)"


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE site_settings
            SET value = :new_subject
            WHERE [key] = 'contract_expiration_notification_subject'
              AND value = :old_subject
            """
        ),
        {"old_subject": OLD_SUBJECT, "new_subject": NEW_SUBJECT},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE site_settings
            SET value = :old_subject
            WHERE [key] = 'contract_expiration_notification_subject'
              AND value = :new_subject
            """
        ),
        {"old_subject": OLD_SUBJECT, "new_subject": NEW_SUBJECT},
    )
