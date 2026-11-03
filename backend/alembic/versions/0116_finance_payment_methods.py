"""Add payment method to ticket collections.

Revision ID: 0116_finance_payment_methods
Revises: 0115_client_department_sharing
"""

import sqlalchemy as sa

from alembic import op

revision = "0116_finance_payment_methods"
down_revision = "0115_client_department_sharing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ticket_finance_ledger_entries", sa.Column("payment_method", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("ticket_finance_ledger_entries", "payment_method")
