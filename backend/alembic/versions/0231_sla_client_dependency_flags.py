"""Seed governed client-dependency SLA pause reasons."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0231_sla_client_dependency_flags"
down_revision: str | None = "0230_dynamic_reports_center"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = (
        ("CLIENT_INFRASTRUCTURE_WAIT", "Waiting for Client Infrastructure", "Customer infrastructure must be restored or corrected before support work can continue.", "#EF6C00", 10),
        ("CLIENT_ACCESS_WAIT", "Waiting for Client Access", "Customer access, credentials, VPN, or an approved maintenance window is required.", "#F57C00", 20),
        ("CLIENT_INFORMATION_WAIT", "Waiting for Customer Information", "Requested diagnostic information or confirmation is outstanding from the customer.", "#FB8C00", 30),
        ("THIRD_PARTY_DEPENDENCY", "Third-party Dependency", "An authorized external supplier dependency prevents resolution work from continuing.", "#8D6E63", 40),
    )
    for code, name, description, color, order in rows:
        exists = bind.execute(
            sa.text("SELECT id FROM ticket_flags WHERE code=:code"), {"code": code}
        ).first()
        if not exists:
            bind.execute(
                sa.text(
                    "INSERT INTO ticket_flags "
                    "(code,name,name_ar,description,color,pauses_sla,is_active,sort_order,created_at,updated_at) "
                    "VALUES (:code,:name,NULL,:description,:color,:pauses_sla,:is_active,:sort_order,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                ),
                {"code": code, "name": name, "description": description, "color": color, "pauses_sla": True, "is_active": True, "sort_order": order},
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM ticket_flags WHERE code IN "
            "('CLIENT_INFRASTRUCTURE_WAIT','CLIENT_ACCESS_WAIT','CLIENT_INFORMATION_WAIT','THIRD_PARTY_DEPENDENCY') "
            "AND NOT EXISTS (SELECT 1 FROM ticket_flag_assignments WHERE ticket_flag_assignments.flag_id=ticket_flags.id)"
        )
    )
