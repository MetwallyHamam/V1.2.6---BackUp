"""normalized country and client location masters

Revision ID: 0087_geography_masters
Revises: 0086_ticket_satisfaction
"""

import sqlalchemy as sa

from alembic import op

revision = "0087_geography_masters"
down_revision = "0086_ticket_satisfaction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "countries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("iso_alpha2", sa.String(2), nullable=False),
        sa.Column("iso_alpha3", sa.String(3), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("default_timezone", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso_alpha2"),
        sa.UniqueConstraint("iso_alpha3"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "client_locations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.BigInteger(), nullable=False),
        sa.Column("country_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("zone", sa.String(150), nullable=True),
        sa.Column("address", sa.String(1000), nullable=True),
        sa.Column("timezone", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "code"),
    )
    op.create_index("ix_client_locations_client_active", "client_locations", ["client_id", "is_active"])
    client_columns = {item["name"] for item in sa.inspect(bind).get_columns("clients")}
    if "country_id" not in client_columns:
        op.add_column("clients", sa.Column("country_id", sa.BigInteger(), nullable=True))
    if "primary_location_id" not in client_columns:
        op.add_column("clients", sa.Column("primary_location_id", sa.BigInteger(), nullable=True))
    branch_columns = {item["name"] for item in sa.inspect(bind).get_columns("branches")}
    if "location_id" not in branch_columns:
        op.add_column("branches", sa.Column("location_id", sa.BigInteger(), nullable=True))
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_clients_country", "clients", "countries", ["country_id"], ["id"])
        op.create_foreign_key("fk_branches_location", "branches", "client_locations", ["location_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_branches_location", "branches", type_="foreignkey")
    op.drop_column("branches", "location_id")
    op.drop_constraint("fk_clients_country", "clients", type_="foreignkey")
    op.drop_column("clients", "primary_location_id")
    op.drop_column("clients", "country_id")
    op.drop_index("ix_client_locations_client_active", table_name="client_locations")
    op.drop_table("client_locations")
    op.drop_table("countries")
