"""Repair tickets that were started but still store the ASSIGNED status."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app import main as app_main  # noqa: F401  # Load the complete ORM registry.
from app.core.clock import server_now
from app.db.session import SessionLocal
from app.modules.tickets.models import Ticket, TicketStatus, TicketStatusHistory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit the repair")
    parser.add_argument("--backup-dir", type=Path, default=Path("storage/data-repairs"))
    args = parser.parse_args()

    with SessionLocal() as db:
        assigned = db.scalar(select(TicketStatus).where(TicketStatus.code == "ASSIGNED"))
        in_progress = db.scalar(
            select(TicketStatus).where(TicketStatus.code == "IN_PROGRESS")
        )
        if assigned is None or in_progress is None:
            raise RuntimeError("ASSIGNED or IN_PROGRESS ticket status is missing")

        tickets = list(
            db.scalars(
                select(Ticket)
                .where(
                    Ticket.status_id == assigned.id,
                    Ticket.progress_started_at.is_not(None),
                )
                .order_by(Ticket.id)
            )
        )
        print(f"AFFECTED_COUNT={len(tickets)}")
        if not args.apply or not tickets:
            return 0

        args.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = args.backup_dir / f"started-assigned-{stamp}.json"
        backup_path.write_text(
            json.dumps(
                [
                    {
                        "id": ticket.id,
                        "ticket_number": ticket.ticket_number,
                        "status_id": ticket.status_id,
                        "version": ticket.version,
                        "last_activity_at": ticket.last_activity_at.isoformat(),
                        "progress_started_at": ticket.progress_started_at.isoformat(),
                    }
                    for ticket in tickets
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

        changed_at = server_now()
        reason = "Data repair: progress had started while stored status remained ASSIGNED"
        for ticket in tickets:
            actor_id = ticket.assigned_user_id or ticket.created_by_user_id
            ticket.status_id = in_progress.id
            ticket.version += 1
            ticket.last_activity_at = changed_at
            db.add(
                TicketStatusHistory(
                    ticket_id=ticket.id,
                    from_status_id=assigned.id,
                    to_status_id=in_progress.id,
                    changed_by_user_id=actor_id,
                    reason=reason,
                    source="DATA_REPAIR",
                    created_at=changed_at,
                )
            )
        db.commit()
        print(f"UPDATED_COUNT={len(tickets)}")
        print(f"BACKUP={backup_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
