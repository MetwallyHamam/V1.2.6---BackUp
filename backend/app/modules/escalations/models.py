from datetime import datetime
from typing import cast

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    event,
    select,
    update,
)
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class EscalationRule(Base):
    __tablename__ = "escalation_rules"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    clock_type: Mapped[str] = mapped_column(String(30))
    threshold_percent: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str | None] = mapped_column(String(5))
    severity: Mapped[str] = mapped_column(String(20))
    notify_assignee: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_managers: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EscalationEvent(Base):
    __tablename__ = "escalation_events"
    __table_args__ = (
        UniqueConstraint("ticket_sla_clock_id", "rule_id"),
        Index("ix_escalation_ticket_created", "ticket_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id"))
    ticket_sla_clock_id: Mapped[int] = mapped_column(IdType, ForeignKey("ticket_sla_clocks.id"))
    rule_id: Mapped[int] = mapped_column(IdType, ForeignKey("escalation_rules.id"))
    threshold_percent: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EscalationWorkItem(Base):
    """The next SLA evaluation required for one live clock.

    This table is deliberately small and indexed by due time.  The scheduler
    consumes it instead of rediscovering work by scanning every running clock.
    """

    __tablename__ = "escalation_work_items"
    __table_args__ = (
        UniqueConstraint("ticket_sla_clock_id"),
        Index("ix_escalation_work_due", "status", "next_evaluation_at", "id"),
        Index("ix_escalation_work_ticket", "ticket_id", "status"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id"), nullable=False)
    ticket_sla_clock_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("ticket_sla_clocks.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    next_evaluation_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


def _sync_clock_work_item(_mapper: object, connection: Connection, target: object) -> None:
    """Synchronize queue state inside the same transaction as an SLA-clock change."""
    from app.modules.contracts.models import TicketSlaClock

    if not isinstance(target, TicketSlaClock) or target.id is None:
        return
    now = utc_now()
    active = target.state == "RUNNING" and target.completed_at is None
    immediate_at = target.started_at if active else now
    values = {
        "ticket_id": target.ticket_id,
        "status": "PENDING" if active else "COMPLETED",
        "next_evaluation_at": immediate_at if active else target.due_at,
        "last_error": None,
        "updated_at": now,
    }
    table = cast(Table, EscalationWorkItem.__table__)
    existing = connection.execute(
        select(table.c.id).where(table.c.ticket_sla_clock_id == target.id)
    ).scalar_one_or_none()
    if existing is None:
        connection.execute(
            table.insert().values(
                ticket_sla_clock_id=target.id,
                attempt_count=0,
                processed_count=0,
                created_at=now,
                **values,
            )
        )
    else:
        connection.execute(update(table).where(table.c.id == existing).values(**values))


def _register_clock_queue_events() -> None:
    from app.modules.contracts.models import TicketSlaClock

    event.listen(TicketSlaClock, "after_insert", _sync_clock_work_item)
    event.listen(TicketSlaClock, "after_update", _sync_clock_work_item)


def _reschedule_queue_for_rule_change(
    _mapper: object, connection: Connection, _target: object
) -> None:
    now = utc_now()
    table = cast(Table, EscalationWorkItem.__table__)
    connection.execute(
        update(table).values(
            status="PENDING",
            next_evaluation_at=now,
            last_error=None,
            updated_at=now,
        )
    )


def reschedule_escalation_work(db: Session) -> None:
    """Make queue entries due after warning configuration changes."""
    db.execute(
        update(EscalationWorkItem).values(
            status="PENDING",
            next_evaluation_at=utc_now(),
            last_error=None,
            updated_at=utc_now(),
        )
    )


_register_clock_queue_events()
event.listen(EscalationRule, "after_insert", _reschedule_queue_for_rule_change)
event.listen(EscalationRule, "after_update", _reschedule_queue_for_rule_change)
