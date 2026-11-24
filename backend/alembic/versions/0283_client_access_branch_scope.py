"""add optional branch scope to client access credentials

Revision ID: 0283_client_access_branch_scope
Revises: 0282_uat_defect_links
"""

import sqlalchemy as sa

from alembic import op

revision = "0283_client_access_branch_scope"
down_revision = "0282_uat_defect_links"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("client_access_credentials") as batch:
            batch.add_column(sa.Column("branch_id", ID, nullable=True))
            batch.create_foreign_key(
                "fk_client_access_credentials_branch_id",
                "branches",
                ["branch_id"],
                ["id"],
            )
            batch.create_index(
                "ix_client_access_client_branch_active",
                ["client_id", "branch_id", "is_active"],
            )
        return
    op.add_column("client_access_credentials", sa.Column("branch_id", ID, nullable=True))
    op.create_foreign_key(
        "fk_client_access_credentials_branch_id",
        "client_access_credentials",
        "branches",
        ["branch_id"],
        ["id"],
    )
    op.create_index(
        "ix_client_access_client_branch_active",
        "client_access_credentials",
        ["client_id", "branch_id", "is_active"],
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("client_access_credentials") as batch:
            batch.drop_index("ix_client_access_client_branch_active")
            batch.drop_constraint("fk_client_access_credentials_branch_id", type_="foreignkey")
            batch.drop_column("branch_id")
        return
    op.drop_index("ix_client_access_client_branch_active", table_name="client_access_credentials")
    op.drop_constraint(
        "fk_client_access_credentials_branch_id",
        "client_access_credentials",
        type_="foreignkey",
    )
    op.drop_column("client_access_credentials", "branch_id")
