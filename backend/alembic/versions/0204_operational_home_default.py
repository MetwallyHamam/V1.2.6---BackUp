"""Make the lightweight operational home the default landing page."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0204_operational_home"
down_revision: str | None = "0203_checklist_schedules"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE users SET default_page = 'home'"))


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE users SET default_page = CASE "
            "WHEN user_type = 'CLIENT_PORTAL' THEN 'portal' ELSE 'dashboard' END"
        )
    )
