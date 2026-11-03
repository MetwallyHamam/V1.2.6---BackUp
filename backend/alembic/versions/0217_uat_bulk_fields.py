"""Add per-test due dates and priority overrides for bulk planning."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0217_uat_bulk_fields"
down_revision: str | None = "0216_uat_client_defect_ticket"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("uat_cycle_tests") as batch:
        batch.add_column(sa.Column("due_date", sa.Date()))
        batch.add_column(sa.Column("priority_override", sa.String(20)))
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area='Bulk Actions' AND overall_status='NOT_STARTED'")


def downgrade() -> None:
    with op.batch_alter_table("uat_cycle_tests") as batch:
        batch.drop_column("priority_override")
        batch.drop_column("due_date")
