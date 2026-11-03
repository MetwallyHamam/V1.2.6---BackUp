"""Reconcile the UAT implementation tracker after final verification."""

from collections.abc import Sequence

from alembic import op

revision: str = "0221_uat_completion"
down_revision: str | None = "0220_uat_checklist_structure"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE uat_implementation_progress SET overall_status='COMPLETED'")


def downgrade() -> None:
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE overall_status='COMPLETED'")
