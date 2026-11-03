"""store user dashboard visibility separately from governed assignments

Revision ID: 0167_dashboard_user_preferences
Revises: 0166_dashboard_assignment_types
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0167_dashboard_user_preferences"
down_revision: str | None = "0166_dashboard_assignment_types"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.add_column(
        "dashboard_assignments",
        sa.Column("is_personal", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE dashboard_assignments SET is_personal = 1 WHERE dashboard_id IN "
        "(SELECT id FROM dashboards WHERE assignment_type IN ('USER', 'USER_TOP_MANAGEMENT'))"
    )
    op.create_table(
        "dashboard_user_preferences",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dashboard_type", sa.String(30), nullable=False),
        sa.Column("hidden_widget_codes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("assigned_dashboard_id", ID, sa.ForeignKey("dashboards.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_dashboard_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("user_id", "dashboard_type"),
    )


def downgrade() -> None:
    op.drop_table("dashboard_user_preferences")
    op.drop_column("dashboard_assignments", "is_personal")
