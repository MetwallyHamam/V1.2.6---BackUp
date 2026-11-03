"""Add deployment issue type master data.

Revision ID: 0272_deployment_issue_types
Revises: 0271_deployment_products
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0272_deployment_issue_types"
down_revision: str | None = "0271_deployment_products"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "deployment_issue_types" not in inspector.get_table_names():
        op.create_table(
            "deployment_issue_types",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("name", sa.String(150), nullable=False, unique=True),
            sa.Column("name_ar", sa.Unicode(150)),
            sa.Column("description", sa.String(1000)),
            sa.Column("description_ar", sa.Unicode(1000)),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        issue_types = sa.table(
            "deployment_issue_types",
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("is_default", sa.Boolean),
            sa.column("is_active", sa.Boolean),
        )
        op.bulk_insert(
            issue_types,
            [
                {"code": "ISSUE", "name": "Issue", "is_default": True, "is_active": True},
                {"code": "ERROR", "name": "Error", "is_default": False, "is_active": True},
                {"code": "BUG", "name": "BUG", "is_default": False, "is_active": True},
                {"code": "ENHANCEMENT", "name": "Enhancement", "is_default": False, "is_active": True},
            ],
        )
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("deployment_issues")}
    if "issue_type_id" not in columns:
        with op.batch_alter_table("deployment_issues") as batch:
            batch.add_column(sa.Column("issue_type_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite")))
            batch.create_foreign_key(
                "fk_deployment_issues_issue_type",
                "deployment_issue_types",
                ["issue_type_id"],
                ["id"],
                ondelete="NO ACTION",
            )
        op.execute(
            "UPDATE deployment_issues SET issue_type_id = "
            "(SELECT id FROM deployment_issue_types WHERE code = 'ISSUE') "
            "WHERE issue_type_id IS NULL"
        )
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("deployment_issues")}
    if "affects_workflow" not in columns:
        op.add_column(
            "deployment_issues",
            sa.Column("affects_workflow", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("deployment_issues")}
    if "update_needed" not in columns:
        op.add_column(
            "deployment_issues",
            sa.Column("update_needed", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("deployment_issues")}
    if "issue_type_id" in columns:
        with op.batch_alter_table("deployment_issues") as batch:
            batch.drop_constraint("fk_deployment_issues_issue_type", type_="foreignkey")
            batch.drop_column("issue_type_id")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("deployment_issues")}
    if "affects_workflow" in columns:
        op.drop_column("deployment_issues", "affects_workflow")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("deployment_issues")}
    if "update_needed" in columns:
        op.drop_column("deployment_issues", "update_needed")
    if "deployment_issue_types" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("deployment_issue_types")
