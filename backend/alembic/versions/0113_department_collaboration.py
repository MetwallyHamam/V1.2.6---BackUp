"""Controlled cross-department ticket collaboration.

Revision ID: 0113_department_collaboration
Revises: 0112_financial_governance
"""

import sqlalchemy as sa

from alembic import op

revision = "0113_department_collaboration"
down_revision = "0112_financial_governance"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("ticket.view.department", "View help requests routed to the user's department", False),
    ("ticket.help.request", "Route a controlled help request to another department", True),
    ("ticket.help.return", "Return a department help-request result to Support", False),
)


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column("support_teams", sa.Column("department_id", sa.BigInteger(), nullable=True))
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_support_teams_department", "support_teams", "departments", ["department_id"], ["id"])
    op.add_column("tickets", sa.Column("routed_department_id", sa.BigInteger(), nullable=True))
    op.add_column("tickets", sa.Column("routed_team_id", sa.BigInteger(), nullable=True))
    op.add_column("tickets", sa.Column("routing_status", sa.String(30), nullable=True))
    op.add_column("tickets", sa.Column("help_request_result", sa.Text(), nullable=True))
    op.add_column("tickets", sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("returned_by_user_id", sa.BigInteger(), nullable=True))
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_tickets_routed_department", "tickets", "departments", ["routed_department_id"], ["id"])
        op.create_foreign_key("fk_tickets_routed_team", "tickets", "support_teams", ["routed_team_id"], ["id"])
        op.create_foreign_key("fk_tickets_returned_by", "tickets", "users", ["returned_by_user_id"], ["id"])
    op.create_index("ix_tickets_routing_department_status", "tickets", ["routed_department_id", "routing_status", "status_id"])
    op.create_index("ix_tickets_routing_team_status", "tickets", ["routed_team_id", "routing_status", "status_id"])
    op.add_column("saved_views", sa.Column("department_id", sa.BigInteger(), nullable=True))
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_saved_views_department", "saved_views", "departments", ["department_id"], ["id"])
    for code, description, high_risk in PERMISSIONS:
        bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT :code,'tickets',:description,:high_risk,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"), {"code": code, "description": description, "high_risk": high_risk})
    for profile_code, permission_codes in {
        "CALL_CENTER": ("ticket.view.department", "ticket.view.own", "ticket.assign.self", "ticket.help.return"),
        "L3_SUPPORT": ("ticket.help.request",),
        "SUPPORT_MANAGER": ("ticket.help.request",),
    }.items():
        for code in permission_codes:
            bind.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT pr.id,p.id,'NONE' FROM profiles pr CROSS JOIN permissions p WHERE pr.code=:profile AND p.code=:code AND NOT EXISTS (SELECT 1 FROM profile_permissions x WHERE x.profile_id=pr.id AND x.permission_id=p.id)"), {"profile": profile_code, "code": code})


def downgrade() -> None:
    op.drop_constraint("fk_saved_views_department", "saved_views", type_="foreignkey")
    op.drop_column("saved_views", "department_id")
    op.drop_index("ix_tickets_routing_team_status", table_name="tickets")
    op.drop_index("ix_tickets_routing_department_status", table_name="tickets")
    for name in ("fk_tickets_returned_by", "fk_tickets_routed_team", "fk_tickets_routed_department"):
        op.drop_constraint(name, "tickets", type_="foreignkey")
    for column in ("returned_by_user_id", "returned_at", "help_request_result", "routing_status", "routed_team_id", "routed_department_id"):
        op.drop_column("tickets", column)
    op.drop_constraint("fk_support_teams_department", "support_teams", type_="foreignkey")
    op.drop_column("support_teams", "department_id")
