import json
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_timezone
from app.core.exceptions import ConflictError
from app.modules.contracts.models import (
    Contract,
    ContractCoverage,
    ContractCoverageRevision,
    ContractRenewalOpportunity,
)
from app.modules.iam.models import AuditLog, User
from app.modules.tickets.models import Ticket


def reconcile_contract_dates(
    db: Session, contract: Contract, start: date, end: date, actor: User
) -> None:
    """Move term-aligned coverage with the contract while retaining independent/history dates."""
    if end <= start:
        raise ConflictError("INVALID_CONTRACT_DATES", "Contract end date must be after start date.")
    if start == contract.start_date and end == contract.end_date:
        return
    for renewal in db.scalars(
        select(ContractRenewalOpportunity).where(
            ContractRenewalOpportunity.source_contract_id == contract.id,
            ContractRenewalOpportunity.stage == "CLOSED",
            ContractRenewalOpportunity.outcome.in_(["RENEWED", "PARTIAL"]),
        )
    ):
        successor = (
            db.get(Contract, renewal.successor_contract_id)
            if renewal.successor_contract_id
            else None
        )
        if successor and end >= successor.start_date:
            raise ConflictError(
                "CONTRACT_DATES_CONFLICT_WITH_RENEWAL",
                f"The new end date overlaps successor contract {successor.contract_number}, starting {successor.start_date}.",
            )
    if end < contract.end_date:
        cutoff = datetime.combine(end + timedelta(days=1), time.min, tzinfo=server_timezone())
        ticket = db.scalar(
            select(Ticket)
            .where(Ticket.contract_id == contract.id, Ticket.created_at >= cutoff)
            .limit(1)
        )
        if ticket:
            raise ConflictError(
                "CONTRACT_DATES_CONFLICT_WITH_TICKETS",
                f"Ticket {ticket.ticket_number or ticket.id} was created after {end}. The new end date would exclude its contract history.",
            )
    rows = list(
        db.scalars(select(ContractCoverage).where(ContractCoverage.contract_id == contract.id))
    )
    revisions = (
        list(
            db.scalars(
                select(ContractCoverageRevision).where(
                    ContractCoverageRevision.coverage_id.in_([row.id for row in rows])
                )
            )
        )
        if rows
        else []
    )
    rows_by_id = {row.id: row for row in rows}
    changes: list[dict[str, object]] = []
    for revision in revisions:
        row = rows_by_id[revision.coverage_id]
        proposed_end = (
            end
            if revision.effective_until == contract.end_date and row.retired_at is None
            else revision.effective_until
        )
        if (
            revision.effective_from < start
            or revision.effective_from > end
            or (proposed_end is not None and proposed_end > end)
        ):
            raise ConflictError(
                "CONTRACT_DATES_CONFLICT_WITH_COVERAGE",
                f"Coverage #{row.id}, revision {revision.revision}, runs from {revision.effective_from} to {revision.effective_until or 'open-ended'}. Review its dates before changing the contract period.",
            )
        if proposed_end != revision.effective_until:
            changes.append(
                {
                    "coverage_id": row.id,
                    "revision": revision.revision,
                    "old_end": str(revision.effective_until),
                    "new_end": str(proposed_end),
                }
            )
            revision.effective_until = proposed_end
    for row in rows:
        proposed_end = (
            end
            if row.effective_until == contract.end_date and row.retired_at is None
            else row.effective_until
        )
        if (
            row.effective_from is not None
            and (row.effective_from < start or row.effective_from > end)
        ) or (proposed_end is not None and proposed_end > end):
            raise ConflictError(
                "CONTRACT_DATES_CONFLICT_WITH_COVERAGE",
                f"Coverage #{row.id} has independently configured dates outside the proposed contract period. Review that coverage first.",
            )
        if proposed_end != row.effective_until:
            changes.append(
                {
                    "coverage_id": row.id,
                    "old_end": str(row.effective_until),
                    "new_end": str(proposed_end),
                }
            )
            row.effective_until = proposed_end
    if changes:
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Contract",
                entity_id=str(contract.id),
                action="contract.coverage.term_dates_aligned",
                new_values_json=json.dumps(changes),
            )
        )
