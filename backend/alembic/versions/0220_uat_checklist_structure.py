"""Add checklist categories and versioned section placement."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0220_uat_checklist_structure"
down_revision: str | None = "0219_uat_client_coordinator"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("uat_checklist_categories",
                    sa.Column("id", id_type, primary_key=True, autoincrement=True),
                    sa.Column("code", sa.String(80), nullable=False, unique=True),
                    sa.Column("name", sa.Unicode(150), nullable=False),
                    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("uat_checklist_templates") as batch:
        batch.add_column(sa.Column("category_id", id_type,
                                   sa.ForeignKey("uat_checklist_categories.id", name="fk_uat_checklist_templates_category_id"), nullable=True))
    with op.batch_alter_table("uat_checklist_version_items") as batch:
        batch.add_column(sa.Column("section_name", sa.Unicode(150), nullable=True))
    bind = op.get_bind()
    for code, name in (("FULL_UAT", "Full UAT"), ("REGRESSION", "Regression"), ("SMOKE", "Smoke Test"),
                       ("UPGRADE", "Upgrade Validation"), ("HOTFIX", "Hotfix Validation"),
                       ("INTEGRATION", "Integration Testing"), ("NEW_INSTALL", "New Installation"),
                       ("CLIENT_ACCEPTANCE", "Client Acceptance"), ("SECURITY", "Security Testing"),
                       ("PERMISSION", "Permission Testing"), ("PERFORMANCE", "Performance Testing")):
        bind.execute(sa.text("INSERT INTO uat_checklist_categories (code, name, is_active) VALUES (:code, :name, :active)"),
                     {"code": code, "name": name, "active": True})
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area='Checklist Builder' AND overall_status='NOT_STARTED'")


def downgrade() -> None:
    with op.batch_alter_table("uat_checklist_version_items") as batch:
        batch.drop_column("section_name")
    with op.batch_alter_table("uat_checklist_templates") as batch:
        batch.drop_column("category_id")
    op.drop_table("uat_checklist_categories")
