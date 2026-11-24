"""add governed maintenance scheduling

Revision ID: 0280_maintenance_scheduling
Revises: 0279_work_assignment_evidence
"""

import sqlalchemy as sa

from alembic import op

revision = "0280_maintenance_scheduling"
down_revision = "0279_work_assignment_evidence"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("maintenance_schedules", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("job_type", sa.String(40), nullable=False), sa.Column("frequency", sa.String(20), nullable=False), sa.Column("run_time", sa.Time(), nullable=False), sa.Column("weekday", sa.Integer()), sa.Column("day_of_month", sa.Integer()), sa.Column("retention_days", sa.Integer(), nullable=False), sa.Column("keep_last", sa.Integer(), nullable=False), sa.Column("is_enabled", sa.Boolean(), nullable=False), sa.Column("next_run_at", sa.DateTime(timezone=True)), sa.Column("last_run_at", sa.DateTime(timezone=True)), sa.Column("last_status", sa.String(20)), sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_maintenance_schedules_due", "maintenance_schedules", ["is_enabled", "next_run_at"])
    op.create_table("maintenance_runs", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("schedule_id", ID, sa.ForeignKey("maintenance_schedules.id", ondelete="SET NULL")), sa.Column("job_type", sa.String(40), nullable=False), sa.Column("trigger_type", sa.String(20), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("duration_ms", sa.Integer()), sa.Column("artifact_path", sa.String(1000)), sa.Column("artifact_size_bytes", sa.BigInteger()), sa.Column("deleted_items", sa.Integer(), nullable=False), sa.Column("summary", sa.Text()), sa.Column("error_message", sa.Text()), sa.Column("initiated_by_user_id", ID, sa.ForeignKey("users.id")))
    op.create_index("ix_maintenance_runs_schedule_started", "maintenance_runs", ["schedule_id", "started_at"])


def downgrade() -> None:
    op.drop_table("maintenance_runs")
    op.drop_table("maintenance_schedules")
