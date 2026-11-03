"""Add normalized Major Incident affected scopes.

Revision ID: 0250_major_incident_scopes
Revises: 0249_service_management
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0250_major_incident_scopes"
down_revision: str | None = "0249_service_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _scope_table(name: str, column: str, target: str) -> None:
    op.create_table(
        name,
        sa.Column(
            "major_incident_id",
            ID,
            sa.ForeignKey("major_incidents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            column,
            ID,
            sa.ForeignKey(target, ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def upgrade() -> None:
    _scope_table("major_incident_client_scopes", "client_id", "clients.id")
    _scope_table("major_incident_product_scopes", "product_id", "products.id")
    _scope_table(
        "major_incident_module_scopes", "product_module_id", "product_modules.id"
    )
    _scope_table(
        "major_incident_service_scopes", "service_id", "service_catalog_items.id"
    )
    _scope_table(
        "major_incident_environment_scopes", "environment_id", "environments.id"
    )


def downgrade() -> None:
    for table in (
        "major_incident_environment_scopes",
        "major_incident_service_scopes",
        "major_incident_module_scopes",
        "major_incident_product_scopes",
        "major_incident_client_scopes",
    ):
        op.drop_table(table)
