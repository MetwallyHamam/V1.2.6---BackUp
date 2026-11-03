"""Add checklist schedules and linked Scheduled Service tickets."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0203_checklist_schedules"
down_revision: str | None = "0202_checklist_evidence"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    identifier = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "service_checklist_schedules",
        sa.Column("id", identifier, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Unicode(200), nullable=False),
        sa.Column("template_id", identifier, sa.ForeignKey("service_checklist_templates.id"), nullable=False),
        sa.Column("client_id", identifier, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("assigned_user_id", identifier, sa.ForeignKey("users.id")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_generate_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False, server_default="Africa/Cairo"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", identifier, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("template_id", "client_id", "starts_at", name="uq_service_checklist_schedule_start"),
    )
    op.create_index("ix_service_checklist_schedule_generation", "service_checklist_schedules", ["is_active", "is_paused", "next_generate_at"])
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("service_checklist_occurrences") as batch:
            batch.add_column(sa.Column("schedule_id", identifier))
            batch.add_column(sa.Column("ticket_id", identifier))
            batch.create_foreign_key("fk_checklist_occurrence_schedule", "service_checklist_schedules", ["schedule_id"], ["id"])
            batch.create_foreign_key("fk_checklist_occurrence_ticket", "tickets", ["ticket_id"], ["id"])
            batch.create_unique_constraint("uq_checklist_occurrence_ticket", ["ticket_id"])
    else:
        op.add_column("service_checklist_occurrences", sa.Column("schedule_id", identifier))
        op.add_column("service_checklist_occurrences", sa.Column("ticket_id", identifier))
        op.create_foreign_key("fk_checklist_occurrence_schedule", "service_checklist_occurrences", "service_checklist_schedules", ["schedule_id"], ["id"])
        op.create_foreign_key("fk_checklist_occurrence_ticket", "service_checklist_occurrences", "tickets", ["ticket_id"], ["id"])
        op.create_unique_constraint("uq_checklist_occurrence_ticket", "service_checklist_occurrences", ["ticket_id"])


def downgrade() -> None:
    op.drop_constraint("uq_checklist_occurrence_ticket", "service_checklist_occurrences", type_="unique")
    op.drop_constraint("fk_checklist_occurrence_ticket", "service_checklist_occurrences", type_="foreignkey")
    op.drop_constraint("fk_checklist_occurrence_schedule", "service_checklist_occurrences", type_="foreignkey")
    op.drop_column("service_checklist_occurrences", "ticket_id")
    op.drop_column("service_checklist_occurrences", "schedule_id")
    op.drop_index("ix_service_checklist_schedule_generation", table_name="service_checklist_schedules")
    op.drop_table("service_checklist_schedules")
