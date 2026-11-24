"""Add effective-dated customer department policies.

Revision ID: 0286_department_policies
Revises: 0285_customer_structure
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0286_department_policies"
down_revision: str | None = "0285_customer_structure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _assignment_table(name: str, parent_table: str, parent_column: str) -> None:
    op.create_table(
        name,
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column(parent_column, ID, nullable=False),
        sa.Column("department_id", ID, nullable=False),
        sa.Column("relationship", sa.String(30), nullable=False),
        sa.Column("access_profile", sa.String(40), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Unicode(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", ID, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint([parent_column], [f"{parent_table}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    prefix = {"organization_id": "org", "client_id": "client", "branch_id": "branch"}[
        parent_column
    ]
    op.create_index(
        f"ix_{prefix}_department_assignments_effective",
        name,
        [parent_column, "department_id", "is_active", "effective_from", "effective_until"],
    )


def _add_mode(table_name: str, default: str) -> None:
    column = sa.Column(
        "department_policy_mode", sa.String(20), nullable=False, server_default=default
    )
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(column)
    else:
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_mode("organizations", "EXTEND")
    _add_mode("clients", "EXTEND")
    _add_mode("branches", "INHERIT")
    _assignment_table(
        "organization_department_assignments", "organizations", "organization_id"
    )
    _assignment_table("client_department_assignments", "clients", "client_id")
    _assignment_table("branch_department_assignments", "branches", "branch_id")

    bind = op.get_bind()
    for code, description in (
        ("customer_structure.policy.view", "View effective customer department policies."),
        ("customer_structure.policy.manage", "Manage effective customer department policies."),
    ):
        bind.execute(
            sa.text(
                "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
                "SELECT :code,'customer_structure',:description,0,1 WHERE NOT EXISTS "
                "(SELECT 1 FROM permissions WHERE code=:code)"
            ),
            {"code": code, "description": description},
        )
    bind.execute(
        sa.text(
            "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
            "SELECT profile.id,permission.id,'NONE' FROM profiles profile "
            "CROSS JOIN permissions permission "
            "WHERE profile.code IN ('SUPPORT_MANAGER','TOP_MANAGEMENT','PROJECT_HANDOVER','ADMINISTRATOR') "
            "AND permission.code='customer_structure.policy.view' "
            "AND NOT EXISTS (SELECT 1 FROM profile_permissions existing "
            "WHERE existing.profile_id=profile.id AND existing.permission_id=permission.id)"
        )
    )
    bind.execute(
        sa.text(
            "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
            "SELECT profile.id,permission.id,'NONE' FROM profiles profile "
            "CROSS JOIN permissions permission "
            "WHERE profile.code='ADMINISTRATOR' "
            "AND permission.code='customer_structure.policy.manage' "
            "AND NOT EXISTS (SELECT 1 FROM profile_permissions existing "
            "WHERE existing.profile_id=profile.id AND existing.permission_id=permission.id)"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM profile_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN "
            "('customer_structure.policy.view','customer_structure.policy.manage'))"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN "
            "('customer_structure.policy.view','customer_structure.policy.manage')"
        )
    )
    for table_name, prefix in (
        ("branch_department_assignments", "branch"),
        ("client_department_assignments", "client"),
        ("organization_department_assignments", "org"),
    ):
        op.drop_index(f"ix_{prefix}_department_assignments_effective", table_name=table_name)
        op.drop_table(table_name)
    for table_name in ("branches", "clients", "organizations"):
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table(table_name) as batch:
                batch.drop_column("department_policy_mode")
        else:
            op.drop_column(table_name, "department_policy_mode")
