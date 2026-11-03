"""Add persistent ordering to UAT cycle tests.

Revision ID: 0256_uat_test_display_order
Revises: 0255_uat_cycle_participants
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0256_uat_test_display_order"
down_revision: str | None = "0255_uat_cycle_participants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("uat_cycle_tests", sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
    op.execute(
        "UPDATE uat_cycle_tests SET display_order = ("
        "SELECT COUNT(*) FROM uat_cycle_tests AS earlier "
        "WHERE earlier.cycle_id = uat_cycle_tests.cycle_id AND earlier.id <= uat_cycle_tests.id)"
    )
    op.create_index("ix_uat_cycle_tests_cycle_order", "uat_cycle_tests", ["cycle_id", "display_order"])


def downgrade() -> None:
    op.drop_index("ix_uat_cycle_tests_cycle_order", table_name="uat_cycle_tests")
    op.drop_column("uat_cycle_tests", "display_order")
