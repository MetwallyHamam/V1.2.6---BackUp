"""Add effective-dated organization hierarchy.

Revision ID: 0096_org_hierarchy
Revises: 0095_ticket_notify
"""

from datetime import date

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, index_exists, table_exists

revision = "0096_org_hierarchy"
down_revision = "0095_ticket_notify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    for name, column_type in (
        ("parent_department_id", id_type),
        ("head_user_id", id_type),
        ("effective_from", sa.Date()),
        ("effective_until", sa.Date()),
    ):
        if not column_exists(bind, "departments", name):
            op.add_column("departments", sa.Column(name, column_type, nullable=True))
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("departments") as batch:
            batch.create_foreign_key("fk_departments_parent", "departments", ["parent_department_id"], ["id"], ondelete="RESTRICT")
            batch.create_foreign_key("fk_departments_head_user", "users", ["head_user_id"], ["id"], ondelete="RESTRICT")
    else:
        op.create_foreign_key("fk_departments_parent", "departments", "departments", ["parent_department_id"], ["id"], ondelete="NO ACTION")
        op.create_foreign_key("fk_departments_head_user", "departments", "users", ["head_user_id"], ["id"], ondelete="NO ACTION")
    if not index_exists(bind, "departments", "ix_departments_parent_department_id"):
        op.create_index("ix_departments_parent_department_id", "departments", ["parent_department_id"])
    if not index_exists(bind, "departments", "ix_departments_head_user_id"):
        op.create_index("ix_departments_head_user_id", "departments", ["head_user_id"])

    if not table_exists(bind, "department_memberships"):
        op.create_table(
            "department_memberships",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("department_id", id_type, sa.ForeignKey("departments.id"), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_until", sa.Date()),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.CheckConstraint("effective_until IS NULL OR effective_until >= effective_from", name="ck_department_membership_dates"),
        )
        op.create_index("ix_department_membership_user_dates", "department_memberships", ["user_id", "effective_from", "effective_until"])
        op.create_index("ix_department_membership_department_dates", "department_memberships", ["department_id", "effective_from", "effective_until"])
    if not table_exists(bind, "department_hierarchy_assignments"):
        op.create_table(
            "department_hierarchy_assignments",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("department_id", id_type, sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parent_department_id", id_type, sa.ForeignKey("departments.id")),
            sa.Column("head_user_id", id_type, sa.ForeignKey("users.id")),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_until", sa.Date()),
            sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.CheckConstraint("department_id <> parent_department_id", name="ck_department_hierarchy_not_self"),
            sa.CheckConstraint("effective_until IS NULL OR effective_until >= effective_from", name="ck_department_hierarchy_dates"),
        )
        op.create_index("ix_department_hierarchy_dates", "department_hierarchy_assignments", ["department_id", "effective_from", "effective_until"])
        op.create_index("ix_department_hierarchy_parent_dates", "department_hierarchy_assignments", ["parent_department_id", "effective_from", "effective_until"])
    if not table_exists(bind, "user_reporting_lines"):
        op.create_table(
            "user_reporting_lines",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("manager_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_until", sa.Date()),
            sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.CheckConstraint("user_id <> manager_user_id", name="ck_user_reporting_line_not_self"),
            sa.CheckConstraint("effective_until IS NULL OR effective_until >= effective_from", name="ck_user_reporting_line_dates"),
        )
        op.create_index("ix_user_reporting_line_user_dates", "user_reporting_lines", ["user_id", "effective_from", "effective_until"])
        op.create_index("ix_user_reporting_line_manager_dates", "user_reporting_lines", ["manager_user_id", "effective_from", "effective_until"])

    today = date.today()
    bind.execute(sa.text("UPDATE departments SET effective_from = :today WHERE effective_from IS NULL"), {"today": today})
    bind.execute(sa.text("INSERT INTO department_hierarchy_assignments (department_id, parent_department_id, head_user_id, effective_from, created_at) SELECT id, parent_department_id, head_user_id, :today, CURRENT_TIMESTAMP FROM departments"), {"today": today})
    bind.execute(sa.text("INSERT INTO department_memberships (user_id, department_id, effective_from, is_primary, created_at) SELECT id, department_id, :today, :primary, CURRENT_TIMESTAMP FROM users WHERE department_id IS NOT NULL"), {"today": today, "primary": True})
    bind.execute(sa.text("INSERT INTO user_reporting_lines (user_id, manager_user_id, effective_from, created_at) SELECT id, reports_to_user_id, :today, CURRENT_TIMESTAMP FROM users WHERE reports_to_user_id IS NOT NULL"), {"today": today})


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in ("user_reporting_lines", "department_hierarchy_assignments", "department_memberships"):
        if table_exists(bind, table_name):
            op.drop_table(table_name)
    for index_name in ("ix_departments_head_user_id", "ix_departments_parent_department_id"):
        if index_exists(bind, "departments", index_name):
            op.drop_index(index_name, table_name="departments")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("departments") as batch:
            batch.drop_constraint("fk_departments_head_user", type_="foreignkey")
            batch.drop_constraint("fk_departments_parent", type_="foreignkey")
            for name in ("effective_until", "effective_from", "head_user_id", "parent_department_id"):
                batch.drop_column(name)
    else:
        op.drop_constraint("fk_departments_head_user", "departments", type_="foreignkey")
        op.drop_constraint("fk_departments_parent", "departments", type_="foreignkey")
        for name in ("effective_until", "effective_from", "head_user_id", "parent_department_id"):
            op.drop_column("departments", name)
