"""Add contract and template ticket requirements."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0197_ticket_requirements"
down_revision: str | None = "0196_ticket_start_progress"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("contracts", "contract_templates"):
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name, default in (
            ("require_product_on_ticket", sa.true()),
            ("require_module_on_ticket", sa.false()),
            ("require_service_on_ticket", sa.false()),
        ):
            if name not in existing:
                op.add_column(
                    table,
                    sa.Column(name, sa.Boolean(), nullable=False, server_default=default),
                )

def downgrade() -> None:
    for table in ("contract_templates", "contracts"):
        op.drop_column(table, "require_service_on_ticket")
        op.drop_column(table, "require_module_on_ticket")
        op.drop_column(table, "require_product_on_ticket")
