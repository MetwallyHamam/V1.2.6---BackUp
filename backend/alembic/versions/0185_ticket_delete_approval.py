"""add approval-based ticket deletion and trash permissions.

Revision ID: 0185_ticket_delete_approval
Revises: 0184_pre_ticket_convert_perm
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0185_ticket_delete_approval"
down_revision: str | None = "0184_pre_ticket_convert_perm"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSIONS = {
    "ticket.delete.request": "Request ticket deletion",
    "ticket.delete.approve": "Approve or reject ticket deletion",
    "ticket.trash.view": "View archived tickets",
    "ticket.trash.restore": "Restore archived tickets",
}
PROFILE_PERMISSIONS = {
    "L3_SUPPORT": {"ticket.delete.request"},
    "SUPPORT_MANAGER": set(PERMISSIONS),
    "ADMINISTRATOR": set(PERMISSIONS),
}


def upgrade() -> None:
    op.create_table(
        "ticket_deletion_requests",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "ticket_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.Unicode(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "decided_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("users.id"),
        ),
        sa.Column("decision_comment", sa.Unicode(1000)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','CANCELLED')"),
    )
    op.create_index(
        "ix_ticket_deletion_requests_queue", "ticket_deletion_requests", ["status", "created_at"]
    )
    op.create_index(
        "ix_ticket_deletion_requests_ticket",
        "ticket_deletion_requests",
        ["ticket_id", "created_at"],
    )
    op.create_index(
        "uq_ticket_deletion_request_pending",
        "ticket_deletion_requests",
        ["ticket_id"],
        unique=True,
        mssql_where=sa.text("status = 'PENDING'"),
        sqlite_where=sa.text("status = 'PENDING'"),
    )

    bind = op.get_bind()
    meta = sa.MetaData()
    permissions = sa.Table("permissions", meta, autoload_with=bind)
    profiles = sa.Table("profiles", meta, autoload_with=bind)
    links = sa.Table("profile_permissions", meta, autoload_with=bind)
    for code, description in PERMISSIONS.items():
        permission_id = bind.execute(
            sa.select(permissions.c.id).where(permissions.c.code == code)
        ).scalar()
        if permission_id is None:
            permission_id = bind.execute(
                sa.insert(permissions).values(
                    code=code,
                    module="ticket",
                    description=description,
                    is_high_risk=code == "ticket.delete.approve",
                    is_active=True,
                )
            ).inserted_primary_key[0]
        for profile_code, codes in PROFILE_PERMISSIONS.items():
            if code not in codes:
                continue
            profile_id = bind.execute(
                sa.select(profiles.c.id).where(profiles.c.code == profile_code)
            ).scalar()
            if (
                profile_id is not None
                and not bind.execute(
                    sa.select(links.c.permission_id).where(
                        links.c.profile_id == profile_id, links.c.permission_id == permission_id
                    )
                ).scalar()
            ):
                bind.execute(
                    sa.insert(links).values(
                        profile_id=profile_id,
                        permission_id=permission_id,
                        scope_type="NONE",
                    )
                )


def downgrade() -> None:
    op.drop_index("uq_ticket_deletion_request_pending", table_name="ticket_deletion_requests")
    op.drop_index("ix_ticket_deletion_requests_ticket", table_name="ticket_deletion_requests")
    op.drop_index("ix_ticket_deletion_requests_queue", table_name="ticket_deletion_requests")
    op.drop_table("ticket_deletion_requests")
