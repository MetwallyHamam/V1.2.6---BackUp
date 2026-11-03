"""Add department master data and link users.

Revision ID: 0091_department_master
Revises: 0090_country_city_masters
"""

import re

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0091_department_master"
down_revision = "0090_country_city_masters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not table_exists(bind, "departments"):
        op.create_table(
            "departments",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("name", sa.String(150), nullable=False, unique=True),
            sa.Column("description", sa.String(1000)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        )
    if not column_exists(bind, "users", "department_id"):
        op.add_column("users", sa.Column("department_id", id_type, nullable=True))

    names = [row[0] for row in bind.execute(sa.text("SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND department <> '' ORDER BY department"))]
    used: set[str] = set()
    for index, name in enumerate(names, 1):
        base = re.sub(r"[^A-Z0-9]+", "_", str(name).upper()).strip("_")[:40] or f"DEPARTMENT_{index}"
        code = base
        suffix = 2
        while code in used:
            code = f"{base[:45]}_{suffix}"
            suffix += 1
        used.add(code)
        bind.execute(sa.text("INSERT INTO departments (code, name, is_active) VALUES (:code, :name, :active)"), {"code": code, "name": name, "active": True})
        bind.execute(sa.text("UPDATE users SET department_id = (SELECT id FROM departments WHERE name = :name) WHERE department = :name"), {"name": name})

    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_users_department", "users", "departments", ["department_id"], ["id"])
    op.create_index("ix_users_department_id", "users", ["department_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if column_exists(bind, "users", "department_id"):
        op.drop_index("ix_users_department_id", table_name="users")
        if bind.dialect.name != "sqlite":
            op.drop_constraint("fk_users_department", "users", type_="foreignkey")
        op.drop_column("users", "department_id")
    if table_exists(bind, "departments"):
        op.drop_table("departments")
