"""shared default contracts for multiple clients

Revision ID: 0052_shared_default_contracts
Revises: 0051_user_hire_date
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0052_shared_default_contracts"
down_revision = "0051_user_hire_date"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "contracts", "is_shared_default"):
        op.add_column("contracts", sa.Column("is_shared_default", sa.Boolean(), nullable=False, server_default=sa.false()))
    if not table_exists(bind, "contract_client_links"):
        op.create_table(
        "contract_client_links",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("contract_id", id_type, nullable=False),
        sa.Column("client_id", id_type, nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("contract_id", "client_id", name="uq_contract_client_link"),
        )
    op.execute("INSERT INTO contract_client_links (contract_id, client_id) SELECT c.id, c.client_id FROM contracts c WHERE NOT EXISTS (SELECT 1 FROM contract_client_links l WHERE l.contract_id=c.id AND l.client_id=c.client_id)")


def downgrade() -> None:
    op.drop_table("contract_client_links")
    op.drop_column("contracts", "is_shared_default")
