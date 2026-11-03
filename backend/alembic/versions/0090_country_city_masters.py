"""Add reusable city masters and link clients to cities.

Revision ID: 0090_country_city_masters
Revises: 0089_kpi_review_lock
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0090_country_city_masters"
down_revision = "0089_kpi_review_lock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_exists(bind, "cities"):
        op.create_table(
            "cities",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("country_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("country_id", "code"),
            sa.UniqueConstraint("country_id", "name"),
        )
    if not column_exists(bind, "clients", "city_id"):
        op.add_column("clients", sa.Column("city_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
        if bind.dialect.name != "sqlite":
            op.create_foreign_key("fk_clients_city", "clients", "cities", ["city_id"], ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    if column_exists(bind, "clients", "city_id"):
        if bind.dialect.name != "sqlite":
            op.drop_constraint("fk_clients_city", "clients", type_="foreignkey")
        op.drop_column("clients", "city_id")
    if table_exists(bind, "cities"):
        op.drop_table("cities")
