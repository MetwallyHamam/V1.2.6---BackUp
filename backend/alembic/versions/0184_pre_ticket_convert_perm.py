"""add independent pre-ticket conversion permission.

Revision ID: 0184_pre_ticket_convert_perm
Revises: 0183_pre_ticket_result_unique
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0184_pre_ticket_convert_perm"
down_revision: str | None = "0183_pre_ticket_result_unique"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSION_CODE = "ticket.pre_ticket.convert_assign"


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    permissions = sa.Table("permissions", metadata, autoload_with=bind)
    profiles = sa.Table("profiles", metadata, autoload_with=bind)
    profile_permissions = sa.Table("profile_permissions", metadata, autoload_with=bind)

    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar()
    if permission_id is None:
        result = bind.execute(
            sa.insert(permissions).values(
                code=PERMISSION_CODE,
                module="ticket",
                description="Convert a Pre-Ticket and assign the official ticket to its creator",
                is_high_risk=False,
                is_active=True,
            )
        )
        permission_id = result.inserted_primary_key[0]

    call_center_profile_id = bind.execute(
        sa.select(profiles.c.id).where(profiles.c.code == "CALL_CENTER")
    ).scalar()
    if call_center_profile_id is not None and not bind.execute(
        sa.select(profile_permissions.c.permission_id).where(
            profile_permissions.c.profile_id == call_center_profile_id,
            profile_permissions.c.permission_id == permission_id,
        )
    ).scalar():
        bind.execute(
            sa.insert(profile_permissions).values(
                profile_id=call_center_profile_id,
                permission_id=permission_id,
                scope_type="NONE",
            )
        )


def downgrade() -> None:
    # Preserve permission and assignment history on downgrade.
    pass
