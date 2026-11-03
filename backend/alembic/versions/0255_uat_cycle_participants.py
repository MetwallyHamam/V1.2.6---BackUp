"""Add multiple UAT engineers and coordinators.

Revision ID: 0255_uat_cycle_participants
Revises: 0254_shift_presence_permission
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0255_uat_cycle_participants"
down_revision: str | None = "0254_shift_presence_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "uat_cycle_participants",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("cycle_id", id_type, sa.ForeignKey("uat_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cycle_id", "user_id", "role"),
        sa.CheckConstraint("role IN ('ENGINEER','COORDINATOR')", name="ck_uat_cycle_participant_role"),
    )
    op.create_index("ix_uat_cycle_participants_cycle_role", "uat_cycle_participants", ["cycle_id", "role"])
    op.execute(
        "INSERT INTO uat_cycle_participants (cycle_id,user_id,role,created_at) "
        "SELECT id,coordinator_user_id,'COORDINATOR',created_at FROM uat_cycles"
    )


def downgrade() -> None:
    op.drop_index("ix_uat_cycle_participants_cycle_role", table_name="uat_cycle_participants")
    op.drop_table("uat_cycle_participants")
