"""add internal operations module

Revision ID: 0037_internal_operations
Revises: 0036_auto_close_pref
"""

import sqlalchemy as sa

from alembic import op

revision = "0037_internal_operations"
down_revision = "0036_auto_close_pref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "internal_operations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("operation_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="SCHEDULED"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(300), nullable=True),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_internal_operations_schedule", "internal_operations", ["operation_type", "starts_at", "status"])
    op.create_table(
        "internal_operation_assignees",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operation_id", sa.BigInteger(), sa.ForeignKey("internal_operations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("operation_id", "user_id"),
    )
    op.create_table(
        "internal_operation_comments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operation_id", sa.BigInteger(), sa.ForeignKey("internal_operations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("comment_type", sa.String(30), nullable=False, server_default="COMMENT"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "internal_operation_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("operation_id", sa.BigInteger(), sa.ForeignKey("internal_operations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(100), nullable=False, unique=True),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("module", sa.String),
        sa.column("description", sa.String),
        sa.column("is_high_risk", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(permissions, [
        {"code": "internal_operation.view", "module": "internal_operations", "description": "View and contribute to assigned internal operations", "is_high_risk": False, "is_active": True},
        {"code": "internal_operation.manage", "module": "internal_operations", "description": "Create, edit, and bulk-assign internal operations", "is_high_risk": False, "is_active": True},
    ])
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, x.id, 'NONE' FROM profiles p CROSS JOIN permissions x WHERE x.code = 'internal_operation.view' AND p.profile_type IN ('EMPLOYEE', 'ADMINISTRATOR') AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=x.id)"))
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, x.id, 'NONE' FROM profiles p CROSS JOIN permissions x WHERE x.code = 'internal_operation.manage' AND (p.code IN ('SUPPORT_MANAGER', 'ADMINISTRATOR') OR p.profile_type = 'ADMINISTRATOR') AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=x.id)"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('internal_operation.view','internal_operation.manage'))"))
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('internal_operation.view','internal_operation.manage')"))
    op.drop_table("internal_operation_documents")
    op.drop_table("internal_operation_comments")
    op.drop_table("internal_operation_assignees")
    op.drop_index("ix_internal_operations_schedule", table_name="internal_operations")
    op.drop_table("internal_operations")
