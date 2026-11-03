"""Add versioned service checklist template foundation."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0200_service_checklists"
down_revision: str | None = "0199_ticket_templates"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    identifier = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "service_checklist_templates",
        sa.Column("id", identifier, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.Unicode(200), nullable=False),
        sa.Column("description", sa.UnicodeText()),
        sa.Column("schedule_mode", sa.String(30), nullable=False, server_default="SCHEDULED"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("publication_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", identifier, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("schedule_mode IN ('SCHEDULED','CLIENT_MANAGED_UNSCHEDULED')", name="ck_service_checklist_template_mode"),
        sa.CheckConstraint("publication_status IN ('DRAFT','PUBLISHED','RETIRED')", name="ck_service_checklist_template_state"),
    )
    op.create_index("ix_service_checklist_templates_active_mode", "service_checklist_templates", ["is_active", "schedule_mode"])
    op.create_table(
        "service_checklist_template_items",
        sa.Column("id", identifier, primary_key=True, autoincrement=True),
        sa.Column("template_id", identifier, sa.ForeignKey("service_checklist_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_code", sa.String(80), nullable=False),
        sa.Column("title", sa.Unicode(200), nullable=False),
        sa.Column("instructions", sa.UnicodeText()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("responsibility", sa.String(20), nullable=False, server_default="MILLENSYS"),
        sa.Column("evidence_type", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("evidence_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expected_duration_minutes", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("responsibility IN ('MILLENSYS','CLIENT','SHARED')", name="ck_service_checklist_item_responsibility"),
        sa.CheckConstraint("evidence_type IN ('NONE','COMMENT','FILE','VALUE','CONFIRMATION','LINK')", name="ck_service_checklist_item_evidence"),
        sa.UniqueConstraint("template_id", "item_code", name="uq_service_checklist_item_code"),
    )
    op.create_index("ix_service_checklist_items_template_order", "service_checklist_template_items", ["template_id", "display_order"])


def downgrade() -> None:
    op.drop_index("ix_service_checklist_items_template_order", table_name="service_checklist_template_items")
    op.drop_table("service_checklist_template_items")
    op.drop_index("ix_service_checklist_templates_active_mode", table_name="service_checklist_templates")
    op.drop_table("service_checklist_templates")
