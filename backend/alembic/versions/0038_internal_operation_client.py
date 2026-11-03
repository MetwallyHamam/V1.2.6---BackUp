"""link internal operations to CRM clients

Revision ID: 0038_operation_client
Revises: 0037_internal_operations
"""

import sqlalchemy as sa

from alembic import op

revision = "0038_operation_client"
down_revision = "0037_internal_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("internal_operations", sa.Column("client_id", sa.BigInteger(), nullable=True))
    if op.get_bind().dialect.name == "sqlite":
        op.execute(sa.text("UPDATE internal_operations SET client_id=(SELECT clients.id FROM clients WHERE clients.name=internal_operations.client_name LIMIT 1) WHERE client_id IS NULL"))
    else:
        op.create_foreign_key("fk_internal_operations_client", "internal_operations", "clients", ["client_id"], ["id"])
        op.execute(sa.text("UPDATE o SET client_id=c.id FROM internal_operations o JOIN clients c ON c.name=o.client_name WHERE o.client_id IS NULL"))


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_internal_operations_client", "internal_operations", type_="foreignkey")
    op.drop_column("internal_operations", "client_id")
