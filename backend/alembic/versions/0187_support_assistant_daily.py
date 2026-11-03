"""add governed daily Support Assistant tabs and follow-up marker.

Revision ID: 0187_support_assistant_daily
Revises: 0186_support_assistant_prefs
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0187_support_assistant_daily"
down_revision: str | None = "0186_support_assistant_prefs"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSIONS = (
    "support_assistant.queue.view",
    "support_assistant.mine.view",
    "support_assistant.sla_risk.view",
    "support_assistant.follow_up.view",
    "support_assistant.pre_ticket.view",
)


def upgrade() -> None:
    bind = op.get_bind()
    if "support_follow_up_flag" not in {column["name"] for column in sa.inspect(bind).get_columns("tickets")}:
        op.add_column("tickets", sa.Column("support_follow_up_flag", sa.Boolean(), nullable=False, server_default=sa.false()))
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("module"), sa.column("description"), sa.column("is_high_risk"), sa.column("is_active"))
    links = sa.table("profile_permissions", sa.column("profile_id"), sa.column("permission_id"), sa.column("scope_type"))
    descriptions = {
        "support_assistant.queue.view": "View the Support Assistant daily queue tab",
        "support_assistant.mine.view": "View the Support Assistant personal daily tab",
        "support_assistant.sla_risk.view": "View the Support Assistant SLA risk tab",
        "support_assistant.follow_up.view": "View and mark Support Assistant follow-up work",
        "support_assistant.pre_ticket.view": "View the Support Assistant pre-ticket tab",
    }
    for code in PERMISSIONS:
        permission_id = bind.scalar(sa.select(permissions.c.id).where(permissions.c.code == code))
        if permission_id is None:
            bind.execute(sa.insert(permissions).values(code=code, module="support_assistant", description=descriptions[code], is_high_risk=False, is_active=True))
            permission_id = bind.scalar(sa.select(permissions.c.id).where(permissions.c.code == code))
        if permission_id is None:
            raise RuntimeError(f"Could not create permission {code}.")
        source_codes = ("ticket.pre_ticket.queue.view", "ticket.pre_ticket.view.own") if code.endswith("pre_ticket.view") else ("ticket.view.all", "ticket.view.team", "ticket.view.department", "ticket.view.own")
        profile_ids = bind.scalars(sa.select(links.c.profile_id).join(permissions, permissions.c.id == links.c.permission_id).where(permissions.c.code.in_(source_codes)).distinct()).all()
        for profile_id in profile_ids:
            exists = bind.scalar(sa.select(links.c.profile_id).where(links.c.profile_id == profile_id, links.c.permission_id == permission_id))
            if exists is None:
                bind.execute(sa.insert(links).values(profile_id=profile_id, permission_id=permission_id, scope_type="NONE"))


def downgrade() -> None:
    bind = op.get_bind()
    permission_ids = sa.select(sa.text("id")).select_from(sa.text("permissions")).where(sa.text("code IN ('" + "','".join(PERMISSIONS) + "')"))
    bind.execute(sa.delete(sa.table("profile_permissions", sa.column("permission_id"))).where(sa.column("permission_id").in_(permission_ids)))
    bind.execute(sa.delete(sa.table("permissions", sa.column("code"))).where(sa.column("code").in_(PERMISSIONS)))
    if "support_follow_up_flag" in {column["name"] for column in sa.inspect(bind).get_columns("tickets")}:
        op.drop_column("tickets", "support_follow_up_flag")
