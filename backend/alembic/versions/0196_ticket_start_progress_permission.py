"""Add a dedicated permission for starting ticket progress.

Revision ID: 0196_ticket_start_progress
Revises: 0195_ticket_default_view
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0196_ticket_start_progress"
down_revision: str | None = "0195_ticket_default_view"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSION = "ticket.start.progress"


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
    profiles = sa.table("profiles", sa.column("id"), sa.column("code"))
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
                module="ticket",
                description="Start or resume ticket progress",
                is_high_risk=False,
                is_active=True,
            )
        )
        permission_id = bind.scalar(
            sa.select(permissions.c.id).where(permissions.c.code == PERMISSION)
        )
    if permission_id is None:
        raise RuntimeError(f"Could not create permission {PERMISSION}.")

    change_status_id = bind.scalar(
        sa.select(permissions.c.id).where(permissions.c.code == "ticket.change.status")
    )
    if change_status_id is not None:
        profile_ids = bind.scalars(
            sa.select(links.c.profile_id)
            .join(profiles, profiles.c.id == links.c.profile_id)
            .where(
                links.c.permission_id == change_status_id,
                profiles.c.code != "CALL_CENTER",
            )
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

    assign_self_id = bind.scalar(
        sa.select(permissions.c.id).where(permissions.c.code == "ticket.assign.self")
    )
    call_center_id = bind.scalar(
        sa.select(profiles.c.id).where(profiles.c.code == "CALL_CENTER")
    )
    if assign_self_id is not None and call_center_id is not None:
        bind.execute(
            sa.delete(links).where(
                links.c.profile_id == call_center_id,
                links.c.permission_id == assign_self_id,
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
            sa.delete(sa.table("profile_permissions", sa.column("permission_id"))).where(
                sa.column("permission_id") == permission_id
            )
        )
        bind.execute(
            sa.delete(sa.table("permissions", sa.column("code"))).where(
                sa.column("code") == PERMISSION
            )
        )
