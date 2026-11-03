"""Record the UAT dashboard and review views as work in progress."""

from collections.abc import Sequence

from alembic import op

revision: str = "0210_uat_review_progress"
down_revision: str | None = "0209_uat_blocked_add_tests"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area IN ('UAT Dashboard', 'Board View', 'List View') AND overall_status='NOT_STARTED'")


def downgrade() -> None:
    pass
