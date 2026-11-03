"""expand contract coverage uniqueness to the full entitlement context

Revision ID: 0030_contract_coverage_context
Revises: 0029_contract_entitlements
"""

import sqlalchemy as sa

from alembic import op

revision = "0030_contract_coverage_context"
down_revision = "0029_contract_entitlements"
branch_labels = None
depends_on = None

OLD_COLUMNS = ["contract_id", "product_id", "branch_id", "environment_id"]
NEW_COLUMNS = [
    "contract_id",
    "product_id",
    "product_module_id",
    "branch_id",
    "environment_id",
    "service_id",
    "ticket_type_id",
]


def _drop_unique_with_columns(columns: list[str]) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mssql":
        name = bind.execute(
            sa.text(
                "SELECT TOP 1 kc.name FROM sys.key_constraints kc "
                "WHERE kc.parent_object_id = OBJECT_ID('contract_coverages') "
                "AND kc.type = 'UQ' AND kc.name <> 'uq_contract_coverage_context'"
            )
        ).scalar()
        if name:
            op.drop_constraint(name, "contract_coverages", type_="unique")
        return
    inspector = sa.inspect(bind)
    for constraint in inspector.get_unique_constraints("contract_coverages"):
        if constraint.get("column_names") == columns and constraint.get("name"):
            op.drop_constraint(constraint["name"], "contract_coverages", type_="unique")
            return


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite cannot alter table-level constraints. Application validation still
        # enforces the expanded context on local/test databases.
        return
    _drop_unique_with_columns(OLD_COLUMNS)
    op.create_unique_constraint(
        "uq_contract_coverage_context", "contract_coverages", NEW_COLUMNS
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    op.drop_constraint(
        "uq_contract_coverage_context", "contract_coverages", type_="unique"
    )
    op.create_unique_constraint(
        "uq_contract_coverage_legacy", "contract_coverages", OLD_COLUMNS
    )
