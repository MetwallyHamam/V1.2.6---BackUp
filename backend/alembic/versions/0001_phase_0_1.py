"""Phase 0 and 1 identity foundation.

This revision deliberately defines the original user table instead of calling
``Base.metadata.create_all``.  Live ORM metadata evolves over time; using it in
the first revision caused clean installations to create future schema objects
before the revisions responsible for them ran.
"""

import sqlalchemy as sa

from alembic import op
from app.db.base import Base
from app.db.migration_helpers import create_frozen_tables
from app.modules.iam import models  # noqa: F401

revision = "0001_phase_0_1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "users",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("username", sa.String(150), nullable=False),
        sa.Column("username_normalized", sa.String(150), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("email_normalized", sa.String(320), nullable=False),
        sa.Column("employee_code", sa.String(80), nullable=True),
        sa.Column("phone_number", sa.String(50), nullable=True),
        sa.Column("department", sa.String(150), nullable=True),
        sa.Column("job_title", sa.String(150), nullable=True),
        sa.Column("user_type", sa.String(30), nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("failed_login_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("require_password_change", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username_normalized"),
        sa.UniqueConstraint("email_normalized"),
        sa.UniqueConstraint("employee_code"),
    )
    op.create_index("ix_users_active", "users", ["is_active"])

    # The remaining Phase 0/1 IAM tables have retained their original shape.
    # Create only this frozen list; later modules own their own revisions.
    create_frozen_tables(bind, (
        "profiles",
        "permissions",
        "profile_permissions",
        "user_profiles",
        "user_permission_overrides",
        "user_client_scopes",
        "user_branch_scopes",
        "refresh_tokens",
        "authentication_events",
        "audit_logs",
    ))


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(
        (
            "profiles",
            "permissions",
            "profile_permissions",
            "user_profiles",
            "user_permission_overrides",
            "user_client_scopes",
            "user_branch_scopes",
            "refresh_tokens",
            "authentication_events",
            "audit_logs",
        )
    ):
        Base.metadata.tables[table_name].drop(bind=bind, checkfirst=True)
    op.drop_table("users")
