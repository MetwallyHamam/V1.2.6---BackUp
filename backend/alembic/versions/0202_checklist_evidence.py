"""Add protected checklist evidence and item linkage."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0202_checklist_evidence"
down_revision: str | None = "0201_checklist_operations"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    identifier = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "service_checklist_evidence",
        sa.Column("id", identifier, primary_key=True, autoincrement=True),
        sa.Column("occurrence_id", identifier, sa.ForeignKey("service_checklist_occurrences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.Unicode(255), nullable=False),
        sa.Column("stored_filename", sa.String(100), nullable=False, unique=True),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", identifier, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_service_checklist_evidence_occurrence", "service_checklist_evidence", ["occurrence_id", "created_at"])
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("service_checklist_occurrence_items") as batch:
            batch.add_column(sa.Column("evidence_id", identifier))
            batch.create_foreign_key(
                "fk_checklist_item_evidence",
                "service_checklist_evidence",
                ["evidence_id"],
                ["id"],
            )
    else:
        op.add_column("service_checklist_occurrence_items", sa.Column("evidence_id", identifier))
        op.create_foreign_key("fk_checklist_item_evidence", "service_checklist_occurrence_items", "service_checklist_evidence", ["evidence_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_checklist_item_evidence", "service_checklist_occurrence_items", type_="foreignkey")
    op.drop_column("service_checklist_occurrence_items", "evidence_id")
    op.drop_index("ix_service_checklist_evidence_occurrence", table_name="service_checklist_evidence")
    op.drop_table("service_checklist_evidence")
