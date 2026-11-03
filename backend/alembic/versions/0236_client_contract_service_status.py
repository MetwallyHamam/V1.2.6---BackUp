"""Add derived client contract service status.

Revision ID: 0236_client_contract_status
Revises: 0235_service_checklist_shares
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0236_client_contract_status"
down_revision: str | None = "0235_service_checklist_shares"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column(
            "contract_service_status",
            sa.String(30),
            nullable=False,
            server_default="NO_ACTIVE_CONTRACT",
        ),
    )
    op.create_index(
        "ix_clients_contract_service_status", "clients", ["contract_service_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_clients_contract_service_status", table_name="clients")
    op.drop_column("clients", "contract_service_status")
