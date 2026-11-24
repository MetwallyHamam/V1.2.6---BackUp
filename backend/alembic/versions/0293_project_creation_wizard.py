"""Add governed project creation wizard scope and scheduling.

Revision ID: 0293_project_creation_wizard
Revises: 0292_unified_ops_hardening
"""

import sqlalchemy as sa

from alembic import op

revision = "0293_project_creation_wizard"
down_revision = "0292_unified_ops_hardening"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("company_projects") as batch:
        batch.add_column(sa.Column("intake_owner_user_id", ID, nullable=True))
        batch.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("published_by_user_id", ID, nullable=True))
        batch.create_foreign_key(
            "fk_project_intake_owner", "users", ["intake_owner_user_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_project_publisher", "users", ["published_by_user_id"], ["id"]
        )
    op.add_column(
        "company_project_phases",
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "company_project_phases",
        sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True),
    )
    with op.batch_alter_table("project_tasks") as batch:
        batch.add_column(sa.Column("product_id", ID, nullable=True))
        batch.add_column(sa.Column("product_module_id", ID, nullable=True))
        batch.add_column(sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_project_task_product", "products", ["product_id"], ["id"])
        batch.create_foreign_key(
            "fk_project_task_module", "product_modules", ["product_module_id"], ["id"]
        )
    for table, parent, parent_column, target, target_column in (
        (
            "company_project_product_scopes",
            "company_projects",
            "project_id",
            "products",
            "product_id",
        ),
        (
            "company_project_module_scopes",
            "company_projects",
            "project_id",
            "product_modules",
            "product_module_id",
        ),
        (
            "project_phase_product_scopes",
            "company_project_phases",
            "phase_id",
            "products",
            "product_id",
        ),
        (
            "project_phase_module_scopes",
            "company_project_phases",
            "phase_id",
            "product_modules",
            "product_module_id",
        ),
    ):
        op.create_table(
            table,
            sa.Column("id", ID, primary_key=True, autoincrement=True),
            sa.Column(
                parent_column, ID, sa.ForeignKey(f"{parent}.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(target_column, ID, sa.ForeignKey(f"{target}.id"), nullable=False),
            sa.UniqueConstraint(parent_column, target_column),
        )


def downgrade() -> None:
    for table in (
        "project_phase_module_scopes",
        "project_phase_product_scopes",
        "company_project_module_scopes",
        "company_project_product_scopes",
    ):
        op.drop_table(table)
    with op.batch_alter_table("project_tasks") as batch:
        batch.drop_constraint("fk_project_task_module", type_="foreignkey")
        batch.drop_constraint("fk_project_task_product", type_="foreignkey")
        for column in ("planned_end_at", "planned_start_at", "product_module_id", "product_id"):
            batch.drop_column(column)
    op.drop_column("company_project_phases", "planned_end_at")
    op.drop_column("company_project_phases", "planned_start_at")
    with op.batch_alter_table("company_projects") as batch:
        batch.drop_constraint("fk_project_publisher", type_="foreignkey")
        batch.drop_constraint("fk_project_intake_owner", type_="foreignkey")
        batch.drop_column("published_by_user_id")
        batch.drop_column("published_at")
        batch.drop_column("intake_owner_user_id")
