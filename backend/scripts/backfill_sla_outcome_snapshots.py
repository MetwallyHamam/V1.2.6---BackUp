"""Backfill persisted outcomes for completed resolution SLA clocks."""

import argparse
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.contracts.models import TicketSlaClock
from app.modules.sla.service import resolution_sla_results
from app.modules.tickets.models import Ticket


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 1900:
        raise ValueError("--batch-size must be between 1 and 1900")
    attempted = 0
    calculated = 0
    skipped = 0
    last_ticket_id = 0
    with SessionLocal() as database:
        while args.limit is None or attempted < args.limit:
            batch_size = min(
                args.batch_size,
                (args.limit - attempted) if args.limit else args.batch_size,
            )
            ticket_ids = list(database.scalars(
                select(TicketSlaClock.ticket_id)
                .where(
                    TicketSlaClock.clock_type == "RESOLUTION",
                    TicketSlaClock.completed_at.is_not(None),
                    TicketSlaClock.accountable_minutes.is_(None),
                    TicketSlaClock.ticket_id > last_ticket_id,
                )
                .order_by(TicketSlaClock.ticket_id)
                .limit(batch_size)
            ))
            if not ticket_ids:
                break
            last_ticket_id = ticket_ids[-1]
            tickets = list(database.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids))))
            outcomes = resolution_sla_results(database, tickets)
            clocks = {
                clock.ticket_id: clock
                for clock in database.scalars(select(TicketSlaClock).where(
                    TicketSlaClock.ticket_id.in_(ticket_ids),
                    TicketSlaClock.clock_type == "RESOLUTION",
                ))
            }
            calculated_at = datetime.now(UTC)
            for ticket_id, outcome in outcomes.items():
                clock = clocks[ticket_id]
                clock.accountable_minutes = outcome.accountable_minutes
                clock.customer_pending_minutes = outcome.customer_pending_minutes
                clock.millensys_pending_minutes = outcome.millensys_pending_minutes
                clock.escalation_minutes = outcome.escalation_minutes
                clock.saved_minutes = outcome.saved_minutes
                clock.overrun_minutes = outcome.overrun_minutes
                clock.outcome_calculated_at = calculated_at
            database.commit()
            attempted += len(ticket_ids)
            calculated += len(outcomes)
            skipped += len(ticket_ids) - len(outcomes)
            print(
                f"Attempted {attempted}; backfilled {calculated}; skipped {skipped} "
                f"completed resolution clocks."
            )
    print(f"PASS attempted={attempted} backfilled={calculated} skipped={skipped}")


if __name__ == "__main__":
    main()
