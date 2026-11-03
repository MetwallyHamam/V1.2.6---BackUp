"""Add independent dated shift coverage slots and required headcount.

Revision ID: 0127_shift_coverage_slots
Revises: 0126_smart_schedule_foundation
"""

import sqlalchemy as sa

from alembic import op

revision = "0127_shift_coverage_slots"
down_revision = "0126_smart_schedule_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "shift_coverage_slots",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column("shift_type_id", ident, sa.ForeignKey("shift_types.id"), nullable=False),
        sa.Column("department_id", ident, sa.ForeignKey("departments.id")),
        sa.Column("team", sa.String(150)),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Africa/Cairo"),
        sa.Column("required_headcount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("source_id", ident),
        sa.Column("notes", sa.String(1000)),
        sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("shift_type_id", "department_id", "team", "starts_at", "ends_at", name="uq_shift_coverage_slot_scope_period"),
    )
    op.create_index("ix_shift_coverage_slots_period", "shift_coverage_slots", ["starts_at", "ends_at"])


def downgrade() -> None:
    op.drop_index("ix_shift_coverage_slots_period", table_name="shift_coverage_slots")
    op.drop_table("shift_coverage_slots")
