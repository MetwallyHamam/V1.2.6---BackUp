"""add Support Assistant backlog permission.

Revision ID: 0189_support_assistant_backlog
Revises: 0188_default_resolution_service
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0189_support_assistant_backlog"
down_revision: str | None = "0188_default_resolution_service"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSION = "support_assistant.backlog.view"


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id"),
        sa.column("code"),
        sa.column("module"),
        sa.column("description"),
        sa.column("is_high_risk"),
        sa.column("is_active"),
    )
    links = sa.table(
        "profile_permissions",
        sa.column("profile_id"),
        sa.column("permission_id"),
        sa.column("scope_type"),
    )
    permission_id = bind.scalar(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
    )
    if permission_id is None:
        bind.execute(
            sa.insert(permissions).values(
                code=PERMISSION,
                module="support_assistant",
                description="View assigned unresolved tickets in the Support Assistant backlog",
                is_high_risk=False,
                is_active=True,
            )
        )
        permission_id = bind.scalar(
            sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
        )
    if permission_id is None:
        raise RuntimeError(f"Could not create permission {PERMISSION}.")
    profile_ids = bind.scalars(
        sa.select(links.c.profile_id)
        .join(permissions, permissions.c.id == links.c.permission_id)
        .where(permissions.c.code == "support_assistant.mine.view")
        .distinct()
    ).all()
    for profile_id in profile_ids:
        exists = bind.scalar(
            sa.select(links.c.profile_id).where(
                links.c.profile_id == profile_id,
                links.c.permission_id == permission_id,
            )
        )
        if exists is None:
            bind.execute(
                sa.insert(links).values(
                    profile_id=profile_id,
                    permission_id=permission_id,
                    scope_type="NONE",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    permission_id = bind.scalar(
        sa.select(sa.text("id"))
        .select_from(sa.text("permissions"))
        .where(sa.text("code = :code"))
        .params(code=PERMISSION)
    )
    if permission_id is not None:
        bind.execute(
            sa.delete(
                sa.table("profile_permissions", sa.column("permission_id"))
            ).where(sa.column("permission_id") == permission_id)
        )
        bind.execute(
            sa.delete(sa.table("permissions", sa.column("code"))).where(
                sa.column("code") == PERMISSION
            )
        )
