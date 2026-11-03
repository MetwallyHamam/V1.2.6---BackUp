"""Add operational service checklist occurrences and delivery records."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0201_checklist_operations"
down_revision: str | None = "0200_service_checklists"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    identifier = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "service_checklist_occurrences",
        sa.Column("id", identifier, primary_key=True, autoincrement=True),
        sa.Column("occurrence_number", sa.String(30), nullable=False, unique=True),
        sa.Column("template_id", identifier, sa.ForeignKey("service_checklist_templates.id"), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("template_name", sa.Unicode(200), nullable=False),
        sa.Column("client_id", identifier, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("assigned_user_id", identifier, sa.ForeignKey("users.id")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recurrence_days", sa.Integer()),
        sa.Column("status", sa.String(30), nullable=False, server_default="SCHEDULED"),
        sa.Column("blocked_party", sa.String(20)),
        sa.Column("blocked_reason", sa.UnicodeText()),
        sa.Column("follow_up_at", sa.DateTime(timezone=True)),
        sa.Column("completion_summary", sa.UnicodeText()),
        sa.Column("service_provided", sa.UnicodeText()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_by_user_id", identifier, sa.ForeignKey("users.id")),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", identifier, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('SCHEDULED','IN_PROGRESS','BLOCKED','COMPLETED','CANCELLED')", name="ck_service_checklist_occurrence_status"),
        sa.UniqueConstraint("template_id", "client_id", "scheduled_at", name="uq_service_checklist_occurrence_slot"),
    )
    op.create_index("ix_service_checklist_occurrence_board", "service_checklist_occurrences", ["status", "due_at", "assigned_user_id"])
    op.create_index("ix_service_checklist_occurrence_client", "service_checklist_occurrences", ["client_id", "status"])
    op.create_table(
        "service_checklist_occurrence_items",
        sa.Column("id", identifier, primary_key=True, autoincrement=True),
        sa.Column("occurrence_id", identifier, sa.ForeignKey("service_checklist_occurrences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_code", sa.String(80), nullable=False),
        sa.Column("title", sa.Unicode(200), nullable=False),
        sa.Column("instructions", sa.UnicodeText()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("original_responsibility", sa.String(20), nullable=False),
        sa.Column("responsibility", sa.String(20), nullable=False),
        sa.Column("evidence_type", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("evidence_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("state", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("result_note", sa.UnicodeText()),
        sa.Column("evidence_reference", sa.Unicode(1000)),
        sa.Column("client_contact", sa.Unicode(200)),
        sa.Column("client_expected_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_by_user_id", identifier, sa.ForeignKey("users.id")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("occurrence_id", "item_code", name="uq_service_checklist_occurrence_item"),
    )
    op.create_index("ix_service_checklist_occurrence_items_order", "service_checklist_occurrence_items", ["occurrence_id", "display_order"])
    op.create_table(
        "service_delivery_records",
        sa.Column("id", identifier, primary_key=True, autoincrement=True),
        sa.Column("occurrence_id", identifier, sa.ForeignKey("service_checklist_occurrences.id"), nullable=False, unique=True),
        sa.Column("client_id", identifier, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("occurrence_number", sa.String(30), nullable=False),
        sa.Column("service_provided", sa.UnicodeText(), nullable=False),
        sa.Column("completion_summary", sa.UnicodeText(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_by_user_id", identifier, sa.ForeignKey("users.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("service_delivery_records")
    op.drop_index("ix_service_checklist_occurrence_items_order", table_name="service_checklist_occurrence_items")
    op.drop_table("service_checklist_occurrence_items")
    op.drop_index("ix_service_checklist_occurrence_client", table_name="service_checklist_occurrences")
    op.drop_index("ix_service_checklist_occurrence_board", table_name="service_checklist_occurrences")
    op.drop_table("service_checklist_occurrences")
