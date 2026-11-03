"""dedicated-assignment SLA calculation

Revision ID: 0070_dedicated_sla
Revises: 0069_no_sla_pm
"""

from datetime import UTC

import sqlalchemy as sa
from sqlalchemy.orm import Session

from alembic import op
from app.modules.contracts.service import calculate_due_at

revision = "0070_dedicated_sla"
down_revision = "0069_no_sla_pm"
branch_labels = None
depends_on = None


def _aware(value):  # type: ignore[no-untyped-def]
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def upgrade() -> None:
    bind = op.get_bind()
    db = Session(bind=bind)
    metadata = sa.MetaData()
    histories = sa.Table("ticket_assignment_history", metadata, autoload_with=bind)
    users = sa.Table("users", metadata, autoload_with=bind)
    settings = sa.Table("site_settings", metadata, autoload_with=bind)
    tickets = sa.Table("tickets", metadata, autoload_with=bind)
    clocks = sa.Table("ticket_sla_clocks", metadata, autoload_with=bind)
    policies = sa.Table("sla_policies", metadata, autoload_with=bind)
    configured = db.execute(
        sa.select(settings.c.value).where(settings.c.key == "default_assignee_user_id")
    ).scalar_one_or_none()
    configured_id = int(configured) if configured and str(configured).isdigit() else None
    statement = (
        sa.select(histories.c.ticket_id, sa.func.min(histories.c.created_at))
        .join(users, users.c.id == histories.c.assigned_user_id)
        .where(users.c.username_normalized != "support")
        .group_by(histories.c.ticket_id)
    )
    if configured_id is not None:
        statement = statement.where(histories.c.assigned_user_id != configured_id)
    first_assignments = dict(db.execute(statement).all())
    ticket_closures = dict(db.execute(sa.select(tickets.c.id, tickets.c.closed_at)).all())
    for clock in db.execute(sa.select(clocks)).mappings():
        values = {}
        assigned_at = first_assignments.get(clock["ticket_id"])
        if assigned_at is None:
            if clock["clock_type"] == "RESOLUTION" and clock["completed_at"] is None:
                db.execute(sa.update(clocks).where(clocks.c.id == clock["id"]).values(state="PAUSED"))
            continue
        assigned_at = _aware(assigned_at)
        if clock["clock_type"] == "FIRST_RESPONSE":
            state = "BREACHED" if assigned_at >= _aware(clock["due_at"]) else "COMPLETED"
            values.update(completed_at=assigned_at, state=state, breached_at=assigned_at if state == "BREACHED" else None)
        elif clock["clock_type"] == "RESOLUTION":
            calendar_id = db.execute(sa.select(policies.c.calendar_id).where(policies.c.id == clock["policy_id"])).scalar_one_or_none()
            if not calendar_id:
                continue
            due_at = calculate_due_at(db, calendar_id, assigned_at, clock["target_minutes"])
            values.update(started_at=assigned_at, due_at=due_at)
            closed_at = ticket_closures.get(clock["ticket_id"])
            if closed_at:
                closed_at = _aware(closed_at)
                state = "BREACHED" if closed_at >= _aware(due_at) else "COMPLETED"
                values.update(completed_at=closed_at, state=state, breached_at=closed_at if state == "BREACHED" else None)
            else:
                values.update(completed_at=None, state="RUNNING", breached_at=None)
        values["calculation_version"] = "3.0"
        db.execute(sa.update(clocks).where(clocks.c.id == clock["id"]).values(**values))
    db.commit()


def downgrade() -> None:
    # Historical timestamps cannot be reconstructed safely under the old rules.
    pass
