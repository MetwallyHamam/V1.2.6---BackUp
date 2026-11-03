"""Allow blocked attempts and cycle-specific ad-hoc tests."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0209_uat_blocked_add_tests"
down_revision: str | None = "0208_uat_defect_retest"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("uat_cycle_tests") as batch:
        batch.alter_column("test_case_id", existing_type=sa.BigInteger(), nullable=True)
    with op.batch_alter_table("uat_test_attempts") as batch:
        batch.add_column(sa.Column("blocking_reason", sa.UnicodeText()))
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area IN ('BLOCKED Workflow', 'Ad-hoc Test Cases', 'Test Checklist Versioning') AND overall_status='NOT_STARTED'")


def downgrade() -> None:
    with op.batch_alter_table("uat_test_attempts") as batch:
        batch.drop_column("blocking_reason")
    with op.batch_alter_table("uat_cycle_tests") as batch:
        batch.alter_column("test_case_id", existing_type=sa.BigInteger(), nullable=False)
