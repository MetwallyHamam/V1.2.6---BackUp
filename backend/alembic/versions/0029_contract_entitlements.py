"""extend contract coverage and ticket entitlement snapshots

Revision ID: 0029_contract_entitlements
Revises: 0028_ticket_tasks_checklists
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0029_contract_entitlements"
down_revision = "0028_ticket_tasks_checklists"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.add_column("contracts", sa.Column("exclusions", sa.Text()))
    op.add_column("contracts", sa.Column("included_request_limit", sa.Integer()))
    op.add_column("contracts", sa.Column("escalation_contact_id", id_type))
    supports_alter = op.get_bind().dialect.name != "sqlite"
    if supports_alter:
        op.create_foreign_key("fk_contracts_escalation_contact", "contracts", "contacts", ["escalation_contact_id"], ["id"])
    # Early installations created product/branch/environment from mutable ORM
    # metadata, while clean installations correctly exclude future columns.
    # Add the complete entitlement context here so both upgrade paths converge.
    for name, target in (
        ("product_id", "products"),
        ("product_module_id", "product_modules"),
        ("branch_id", "branches"),
        ("environment_id", "environments"),
        ("service_id", "service_catalog_items"),
        ("ticket_type_id", "ticket_types"),
    ):
        if column_exists(op.get_bind(), "contract_coverages", name):
            continue
        op.add_column("contract_coverages", sa.Column(name, id_type))
        if supports_alter:
            op.create_foreign_key(f"fk_contract_coverages_{name}", "contract_coverages", target, [name], ["id"])
    op.add_column("tickets", sa.Column("contract_id", id_type))
    op.add_column("tickets", sa.Column("entitlement_status", sa.String(30)))
    op.add_column("tickets", sa.Column("entitlement_override_reason", sa.String(500)))
    if supports_alter:
        op.create_foreign_key("fk_tickets_contract", "tickets", "contracts", ["contract_id"], ["id"])
    op.create_table(
        "contract_documents",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("contract_id", id_type, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(100), nullable=False, unique=True),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by_user_id", id_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("contract_documents")
    supports_alter = op.get_bind().dialect.name != "sqlite"
    if supports_alter:
        op.drop_constraint("fk_tickets_contract", "tickets", type_="foreignkey")
    op.drop_column("tickets", "entitlement_override_reason")
    op.drop_column("tickets", "entitlement_status")
    op.drop_column("tickets", "contract_id")
    for name in ("ticket_type_id", "service_id", "product_module_id"):
        if supports_alter:
            op.drop_constraint(f"fk_contract_coverages_{name}", "contract_coverages", type_="foreignkey")
        op.drop_column("contract_coverages", name)
    if supports_alter:
        op.drop_constraint("fk_contracts_escalation_contact", "contracts", type_="foreignkey")
    op.drop_column("contracts", "escalation_contact_id")
    op.drop_column("contracts", "included_request_limit")
    op.drop_column("contracts", "exclusions")
