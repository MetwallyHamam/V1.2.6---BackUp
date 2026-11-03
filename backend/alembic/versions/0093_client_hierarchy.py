"""Add the client hierarchy foundation.

Revision ID: 0093_client_hierarchy
Revises: 0092_client_profile
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, index_exists

revision = "0093_client_hierarchy"
down_revision = "0092_client_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not column_exists(bind, "clients", "parent_client_id"):
        op.add_column("clients", sa.Column("parent_client_id", id_type, nullable=True))
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("clients") as batch:
                batch.create_foreign_key(
                    "fk_clients_parent_client", "clients", ["parent_client_id"], ["id"], ondelete="RESTRICT"
                )
        else:
            op.create_foreign_key(
                "fk_clients_parent_client", "clients", "clients", ["parent_client_id"], ["id"], ondelete="NO ACTION"
            )
    if not index_exists(bind, "clients", "ix_clients_parent_client_id"):
        op.create_index("ix_clients_parent_client_id", "clients", ["parent_client_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if index_exists(bind, "clients", "ix_clients_parent_client_id"):
        op.drop_index("ix_clients_parent_client_id", table_name="clients")
    if column_exists(bind, "clients", "parent_client_id"):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("clients") as batch:
                batch.drop_constraint("fk_clients_parent_client", type_="foreignkey")
                batch.drop_column("parent_client_id")
        else:
            op.drop_constraint("fk_clients_parent_client", "clients", type_="foreignkey")
            op.drop_column("clients", "parent_client_id")
