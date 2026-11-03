"""Share clients with multiple departments.

Revision ID: 0115_client_department_sharing
Revises: 0114_contract_templates
"""

import sqlalchemy as sa

from alembic import op

revision = "0115_client_department_sharing"
down_revision = "0114_contract_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "client_department_links",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("client_id", id_type, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", id_type, sa.ForeignKey("departments.id"), nullable=False),
        sa.UniqueConstraint("client_id", "department_id", name="uq_client_department_link"),
    )
    op.create_index(
        "ix_client_department_links_department",
        "client_department_links",
        ["department_id", "client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_client_department_links_department", table_name="client_department_links")
    op.drop_table("client_department_links")
