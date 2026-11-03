import json
import re
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any, cast

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone, server_today
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client, ClientStatus
from app.modules.contracts.models import Contract, ContractClientLink
from app.modules.finance.models import (
    ContractBillingSchedule,
    ContractCollection,
    ContractFinanceProfile,
    ContractInvoice,
    ContractReceipt,
    ContractReceiptAllocation,
    FinanceAdjustmentReason,
    TicketCommercialDecision,
    TicketFinanceLedgerEntry,
)
from app.modules.finance.schemas import (
    BillingScheduleRead,
    BillingScheduleUpdate,
    BillingScheduleWrite,
    ClientStatementCurrencyRead,
    ClientStatementRead,
    CollectionRead,
    CollectionWrite,
    CommercialDecisionRead,
    CommercialDecisionWrite,
    ContractFinanceProfileRead,
    ContractFinanceProfileWrite,
    ContractFinanceSummary,
    ContractInvoiceEdit,
    ContractInvoiceRead,
    ContractInvoiceWrite,
    ContractReceiptRead,
    ContractReceiptWrite,
    FinanceAdjustmentReasonRead,
    FinanceAdjustmentReasonWrite,
    FinanceSummaryRead,
    FinancialBreakdownSlice,
    FinancialClientContribution,
    FinancialCurrencyAnalytics,
    FinancialDashboardContract,
    FinancialDashboardRead,
    FinancialDashboardTotal,
    FinancialPeriodRead,
    FinancialTrendPoint,
    InvoiceActionWrite,
    InvoiceCollectionRead,
    LedgerEntryRead,
    LedgerEntryWrite,
    PaymentWorkspaceRead,
    ReceiptAllocationRead,
    ReceiptAllocationWrite,
    TicketFinanceRead,
    TicketPaymentWrite,
)
from app.modules.iam.models import AuditLog, Department, User
from app.modules.tickets.models import Ticket

router = APIRouter(prefix="/manager-finance", tags=["manager finance"])


def _invoice_has_collection(db: Session, invoice_id: int) -> bool:
    return bool(
        db.scalar(select(ContractCollection.id).where(ContractCollection.invoice_id == invoice_id).limit(1))
        or db.scalar(select(ContractReceiptAllocation.id).where(ContractReceiptAllocation.invoice_id == invoice_id, ContractReceiptAllocation.is_reversal == False).limit(1))  # noqa: E712
    )


def _contract(db: Session, contract_id: int) -> Contract:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    return contract


def _profile(db: Session, contract_id: int) -> ContractFinanceProfile:
    profile = db.get(ContractFinanceProfile, contract_id)
    if not profile:
        raise ConflictError("CONTRACT_FINANCE_NOT_ENABLED", "Create the optional finance profile first.")
    return profile


def _same_currency(profile: ContractFinanceProfile, currency: str) -> None:
    if profile.currency != currency:
        raise ConflictError("CONTRACT_FINANCE_CURRENCY_MISMATCH", "All contract finance records must use the profile currency.")


def _scheduled_dates(contract: Contract, frequency: str, billing_day: int) -> list[date]:
    step = {"MONTHLY": 1, "QUARTERLY": 3, "ANNUAL": 12}[frequency]
    year, month = contract.start_date.year, contract.start_date.month
    result: list[date] = []
    while True:
        candidate = date(year, month, min(billing_day, monthrange(year, month)[1]))
        if candidate < contract.start_date:
            total = year * 12 + month - 1 + step
            year, month = divmod(total, 12); month += 1
            continue
        if candidate > contract.end_date:
            break
        result.append(candidate)
        total = year * 12 + month - 1 + step
        year, month = divmod(total, 12); month += 1
    return result


def _rebuild_generated_schedule(db: Session, contract: Contract, profile: ContractFinanceProfile, actor: User) -> None:
    generated = list(db.scalars(select(ContractInvoice).where(ContractInvoice.contract_id == contract.id, ContractInvoice.status == "DRAFT", ContractInvoice.reason == "Automatically generated from the contract financial profile.")))
    locked = list(db.scalars(select(ContractInvoice).where(ContractInvoice.contract_id == contract.id, ContractInvoice.document_type == "INVOICE", ContractInvoice.status != "DRAFT", ContractInvoice.status != "CANCELLED")))
    generated_ids = [row.id for row in generated]
    generated_schedule_ids = [row.schedule_id for row in generated if row.schedule_id is not None]
    locked_schedule_ids = [row.schedule_id for row in locked if row.schedule_id is not None]
    existing_schedule_ids = set(db.scalars(select(ContractBillingSchedule.id).where(ContractBillingSchedule.contract_id == contract.id)))
    if existing_schedule_ids - set(generated_schedule_ids) - set(locked_schedule_ids):
        raise ConflictError("MANUAL_BILLING_SCHEDULE_EXISTS", "This contract has a manual billing schedule. Remove or complete it before generating a profile schedule.")
    if generated_ids and db.scalar(select(ContractCollection.id).where(ContractCollection.invoice_id.in_(generated_ids)).limit(1)):
        return
    if generated_ids:
        db.execute(delete(ContractInvoice).where(ContractInvoice.id.in_(generated_ids)))
    if generated_schedule_ids:
        db.execute(delete(ContractBillingSchedule).where(ContractBillingSchedule.id.in_(generated_schedule_ids)))
    if profile.contract_value is None and profile.invoice_amount is None:
        return
    dates = _scheduled_dates(contract, profile.billing_frequency, profile.billing_day)
    locked_dates = {row.due_date for row in locked}
    dates = [value for value in dates if value not in locked_dates]
    if not dates:
        return
    if profile.invoice_amount is not None:
        amounts = [profile.invoice_amount for _ in dates]
    else:
        total = max(Decimal(), (profile.contract_value or Decimal()) - sum((row.total_amount for row in locked), Decimal()))
        standard = (total / len(dates)).quantize(Decimal("0.0001"))
        amounts = [standard for _ in dates]
        amounts[-1] = total - sum(amounts[:-1], Decimal())
    used_numbers = set(db.scalars(select(ContractBillingSchedule.installment_number).where(ContractBillingSchedule.contract_id == contract.id)))
    available_numbers = (number for number in range(1, len(dates) + len(used_numbers) + 2) if number not in used_numbers)
    for due_date, amount in zip(dates, amounts, strict=True):
        number = next(available_numbers)
        schedule = ContractBillingSchedule(contract_id=contract.id, installment_number=number, description=f"{profile.billing_frequency.title()} payment {number}", due_date=due_date, amount=amount, currency=profile.currency, status="INVOICED", created_by_user_id=actor.id)
        db.add(schedule); db.flush()
        invoice = ContractInvoice(contract_id=contract.id, schedule_id=schedule.id, idempotency_key=f"profile-schedule-{contract.id}-{number}-{due_date.isoformat()}", document_type="INVOICE", invoice_number=f"SCH-{contract.contract_number}-{number:03d}", issued_date=due_date, due_date=due_date, subtotal=amount, tax_amount=Decimal(), total_amount=amount, currency=profile.currency, status="DRAFT", reason="Automatically generated from the contract financial profile.", imported_unverified=False, created_by_user_id=actor.id)
        db.add(invoice)


def _invoice_collection(db: Session, invoice: ContractInvoice) -> InvoiceCollectionRead:
    collections = list(db.scalars(select(ContractCollection).where(ContractCollection.invoice_id == invoice.id).order_by(ContractCollection.collected_date, ContractCollection.id)))
    legacy = db.scalar(select(func.coalesce(func.sum(ContractReceiptAllocation.amount), 0)).where(ContractReceiptAllocation.invoice_id == invoice.id, ContractReceiptAllocation.is_reversal == False)) or Decimal()  # noqa: E712
    actual = legacy + sum((row.actual_payment for row in collections), Decimal())
    discounts = sum((row.discount_amount for row in collections), Decimal())
    additional = sum((row.additional_amount for row in collections), Decimal())
    remaining = max(Decimal(), invoice.total_amount + additional - actual - discounts)
    return InvoiceCollectionRead(invoice=ContractInvoiceRead.model_validate(invoice), scheduled_amount=invoice.total_amount, actual_payment=actual, discounts=discounts, additional=additional, remaining=remaining, collections=[CollectionRead.model_validate(row) for row in collections])


def _ticket_finance(db: Session, ticket: Ticket) -> TicketFinanceRead:
    decisions = list(db.scalars(select(TicketCommercialDecision).where(TicketCommercialDecision.ticket_id == ticket.id).order_by(TicketCommercialDecision.sequence.desc())))
    entries = list(db.scalars(select(TicketFinanceLedgerEntry).where(TicketFinanceLedgerEntry.ticket_id == ticket.id).order_by(TicketFinanceLedgerEntry.occurred_at, TicketFinanceLedgerEntry.id)))
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for entry in entries:
        if entry.status != "CONFIRMED": continue
        key = {"BILLABLE":"billable", "INVOICE":"invoiced", "COLLECTION":"collected", "WAIVER":"waived", "DISPUTE":"disputed"}.get(entry.entry_type)
        if key: totals[entry.currency][key] += entry.amount
    summaries = [FinanceSummaryRead(currency=currency, billable=values["billable"], invoiced=values["invoiced"], collected=values["collected"], waived=values["waived"], disputed=values["disputed"], outstanding=max(Decimal(), values["invoiced"] - values["collected"] - values["waived"])) for currency, values in sorted(totals.items())]
    client = db.get(Client, ticket.client_id)
    return TicketFinanceRead(ticket_id=ticket.id, ticket_number=ticket.ticket_number or str(ticket.id), client_id=ticket.client_id, client_code=client.code if client else None, client_name=client.name if client else "Unknown client", subject=ticket.subject, latest_decision=CommercialDecisionRead.model_validate(decisions[0]) if decisions else None, entries=[LedgerEntryRead.model_validate(item) for item in entries], totals=summaries)


@router.get("", response_model=list[TicketFinanceRead])
def list_finance(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[TicketFinanceRead]:
    ticket_ids = set(db.scalars(select(TicketCommercialDecision.ticket_id))) | set(db.scalars(select(TicketFinanceLedgerEntry.ticket_id)))
    tickets = list(db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids)).order_by(Ticket.updated_at.desc()).limit(limit))) if ticket_ids else []
    return [_ticket_finance(db, ticket) for ticket in tickets]


@router.get("/tickets/lookup", response_model=list[TicketFinanceRead])
def lookup_ticket_finance(search: str = Query(min_length=1, max_length=100), limit: int = Query(default=20, ge=1, le=50), db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[TicketFinanceRead]:
    term = f"%{search.strip()}%"
    tickets = list(db.scalars(select(Ticket).join(Client, Client.id == Ticket.client_id).where((Ticket.ticket_number.ilike(term)) | (Ticket.subject.ilike(term)) | (Client.name.ilike(term)) | (Client.code.ilike(term))).order_by(Ticket.updated_at.desc()).limit(limit)))
    return [_ticket_finance(db, ticket) for ticket in tickets]


@router.get("/tickets/{ticket_id}", response_model=TicketFinanceRead)
def read_finance(ticket_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> TicketFinanceRead:
    ticket = db.get(Ticket, ticket_id)
    if not ticket: raise NotFoundError()
    return _ticket_finance(db, ticket)


@router.post("/tickets/{ticket_id}/decisions", response_model=CommercialDecisionRead, status_code=201)
def create_decision(ticket_id: int, data: CommercialDecisionWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> TicketCommercialDecision:
    if not db.get(Ticket, ticket_id): raise NotFoundError()
    current = db.scalar(select(func.max(TicketCommercialDecision.sequence)).where(TicketCommercialDecision.ticket_id == ticket_id)) or 0
    if current != data.expected_sequence: raise ConflictError("STALE_COMMERCIAL_DECISION", "The commercial decision changed; refresh and retry.")
    item = TicketCommercialDecision(ticket_id=ticket_id, sequence=current + 1, created_by_user_id=actor.id, **data.model_dump(exclude={"expected_sequence"}))
    db.add(item); db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="TicketCommercialDecision", entity_id=str(item.id), action="ticket.finance.decision_recorded", reason=data.reason, new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item)
    return item


@router.post("/tickets/{ticket_id}/ledger", response_model=LedgerEntryRead, status_code=201)
def create_ledger_entry(ticket_id: int, data: LedgerEntryWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> TicketFinanceLedgerEntry:
    if not db.get(Ticket, ticket_id): raise NotFoundError()
    existing = db.scalar(select(TicketFinanceLedgerEntry).where(TicketFinanceLedgerEntry.idempotency_key == data.idempotency_key))
    if existing: return existing
    if data.reversal_of_entry_id is not None:
        original = db.get(TicketFinanceLedgerEntry, data.reversal_of_entry_id)
        if not original or original.ticket_id != ticket_id: raise ConflictError("INVALID_FINANCE_REVERSAL", "The reversed entry does not belong to this ticket.")
    now = server_now()
    item = TicketFinanceLedgerEntry(ticket_id=ticket_id, status_at=now, created_by_user_id=actor.id, **data.model_dump())
    db.add(item)
    try: db.flush()
    except IntegrityError:
        db.rollback()
        found = db.scalar(select(TicketFinanceLedgerEntry).where(TicketFinanceLedgerEntry.idempotency_key == data.idempotency_key))
        if found: return found
        raise
    db.add(AuditLog(actor_user_id=actor.id, entity_type="TicketFinanceLedgerEntry", entity_id=str(item.id), action="ticket.finance.ledger_recorded", reason=data.reason, new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item)
    return item


@router.post("/tickets/{ticket_id}/payments", response_model=LedgerEntryRead, status_code=201)
def create_ticket_payment(
    ticket_id: int,
    data: TicketPaymentWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("finance.manage")),
) -> TicketFinanceLedgerEntry:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    existing = db.scalar(
        select(TicketFinanceLedgerEntry).where(
            TicketFinanceLedgerEntry.idempotency_key == data.idempotency_key
        )
    )
    if existing:
        if existing.ticket_id != ticket_id or existing.entry_type != "COLLECTION":
            raise ConflictError("PAYMENT_IDEMPOTENCY_CONFLICT", "The payment request key is already used by another finance entry.")
        return existing

    confirmed = list(
        db.scalars(
            select(TicketFinanceLedgerEntry).where(
                TicketFinanceLedgerEntry.ticket_id == ticket_id,
                TicketFinanceLedgerEntry.currency == data.currency,
                TicketFinanceLedgerEntry.status == "CONFIRMED",
            )
        )
    )
    invoiced = sum((row.amount for row in confirmed if row.entry_type == "INVOICE"), Decimal())
    collected = sum((row.amount for row in confirmed if row.entry_type == "COLLECTION"), Decimal())
    waived = sum((row.amount for row in confirmed if row.entry_type == "WAIVER"), Decimal())
    remaining = max(Decimal(), invoiced - collected - waived)
    auto_invoice_amount = max(Decimal(), data.amount - remaining)
    auto_invoice: TicketFinanceLedgerEntry | None = None
    if auto_invoice_amount > 0:
        auto_invoice = TicketFinanceLedgerEntry(
            ticket_id=ticket.id,
            idempotency_key=f"{data.idempotency_key}:invoice"[:200],
            entry_type="INVOICE",
            status="CONFIRMED",
            amount=auto_invoice_amount,
            currency=data.currency,
            payment_method=None,
            external_reference=f"AUTO-{data.reference.strip()}"[:200],
            reason="Invoice created automatically with ticket payment",
            occurred_at=data.paid_at,
            status_at=server_now(),
            reversal_of_entry_id=None,
            created_by_user_id=actor.id,
        )
        db.add(auto_invoice)

    item = TicketFinanceLedgerEntry(
        ticket_id=ticket.id,
        idempotency_key=data.idempotency_key,
        entry_type="COLLECTION",
        status="CONFIRMED",
        amount=data.amount,
        currency=data.currency,
        payment_method=data.payment_method,
        external_reference=data.reference.strip(),
        reason=(data.notes or "Payment recorded for the client linked to the selected ticket").strip(),
        occurred_at=data.paid_at,
        status_at=server_now(),
        reversal_of_entry_id=None,
        created_by_user_id=actor.id,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        found = db.scalar(
            select(TicketFinanceLedgerEntry).where(
                TicketFinanceLedgerEntry.idempotency_key == data.idempotency_key
            )
        )
        if found and found.ticket_id == ticket_id and found.entry_type == "COLLECTION":
            return found
        raise
    if auto_invoice is not None:
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="TicketFinanceLedgerEntry",
                entity_id=str(auto_invoice.id),
                action="ticket.finance.invoice_auto_created",
                reason=auto_invoice.reason,
                new_values_json=json.dumps(
                    {
                        "ticket_id": ticket.id,
                        "client_id": ticket.client_id,
                        "amount": str(auto_invoice.amount),
                        "currency": auto_invoice.currency,
                        "payment_reference": data.reference,
                    },
                    default=str,
                ),
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketFinanceLedgerEntry",
            entity_id=str(item.id),
            action="ticket.finance.payment_recorded",
            reason=item.reason,
            new_values_json=json.dumps(
                {
                    "ticket_id": ticket.id,
                    "client_id": ticket.client_id,
                    "amount": str(item.amount),
                    "currency": item.currency,
                    "payment_method": item.payment_method,
                    "reference": item.external_reference,
                    "paid_at": item.occurred_at,
                },
                default=str,
            ),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/contracts/{contract_id}/profile", response_model=ContractFinanceProfileRead | None)
def read_contract_profile(contract_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> ContractFinanceProfile | None:
    _contract(db, contract_id)
    return db.get(ContractFinanceProfile, contract_id)


@router.put("/contracts/{contract_id}/profile", response_model=ContractFinanceProfileRead)
def save_contract_profile(contract_id: int, data: ContractFinanceProfileWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> ContractFinanceProfile:
    contract = _contract(db, contract_id)
    item = db.get(ContractFinanceProfile, contract_id)
    if item and item.currency != data.currency and db.scalar(select(ContractInvoice.id).where(ContractInvoice.contract_id == contract_id).limit(1)):
        raise ConflictError("POSTED_FINANCE_CURRENCY_LOCKED", "Currency cannot change after a financial document exists.")
    if not item:
        item = ContractFinanceProfile(contract_id=contract_id, updated_by_user_id=actor.id, **data.model_dump())
        db.add(item)
    else:
        for field, value in data.model_dump().items(): setattr(item, field, value)
        item.updated_by_user_id = actor.id
    db.flush()
    # Legacy API callers did not send scheduling fields. Preserve their manual
    # invoice workflow; the simplified UI explicitly supplies the frequency.
    if "billing_frequency" in data.model_fields_set:
        _rebuild_generated_schedule(db, contract, item, actor)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractFinanceProfile", entity_id=str(contract_id), action="contract.finance.profile_saved", new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item)
    return item


@router.get("/adjustment-reasons", response_model=list[FinanceAdjustmentReasonRead])
def list_adjustment_reasons(include_inactive: bool = False, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[FinanceAdjustmentReason]:
    query = select(FinanceAdjustmentReason).order_by(FinanceAdjustmentReason.name)
    if not include_inactive:
        query = query.where(FinanceAdjustmentReason.is_active == True)  # noqa: E712
    return list(db.scalars(query))


@router.post("/adjustment-reasons", response_model=FinanceAdjustmentReasonRead, status_code=201)
def create_adjustment_reason(data: FinanceAdjustmentReasonWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> FinanceAdjustmentReason:
    values = data.model_dump(); requested_code = values.pop("code", None)
    item = FinanceAdjustmentReason(code=requested_code or f"PENDING-FAR-{server_now().timestamp()}", created_by_user_id=actor.id, **values)
    db.add(item)
    try:
        db.flush()
        if not requested_code: item.code = f"FAR-{item.id:06d}"
    except IntegrityError as exc:
        db.rollback(); raise ConflictError("DUPLICATE_ADJUSTMENT_REASON", "Adjustment reason code already exists.") from exc
    db.add(AuditLog(actor_user_id=actor.id, entity_type="FinanceAdjustmentReason", entity_id=str(item.id), action="finance.adjustment_reason_created", new_values_json=json.dumps(data.model_dump())))
    db.commit(); db.refresh(item); return item


@router.patch("/adjustment-reasons/{reason_id}", response_model=FinanceAdjustmentReasonRead)
def update_adjustment_reason(reason_id: int, data: FinanceAdjustmentReasonWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> FinanceAdjustmentReason:
    item = db.get(FinanceAdjustmentReason, reason_id)
    if not item:
        raise NotFoundError()
    before = {"code": item.code, "name": item.name, "adjustment_type": item.adjustment_type, "is_active": item.is_active}
    values = data.model_dump(exclude={"code"})
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback(); raise ConflictError("DUPLICATE_ADJUSTMENT_REASON", "Adjustment reason code already exists.") from exc
    db.add(AuditLog(actor_user_id=actor.id, entity_type="FinanceAdjustmentReason", entity_id=str(item.id), action="finance.adjustment_reason_updated", old_values_json=json.dumps(before), new_values_json=json.dumps(values)))
    db.commit(); db.refresh(item); return item


@router.post("/contracts/{contract_id}/schedules", response_model=BillingScheduleRead, status_code=201)
def create_schedule(contract_id: int, data: BillingScheduleWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> ContractBillingSchedule:
    _contract(db, contract_id); profile = _profile(db, contract_id); _same_currency(profile, data.currency)
    item = ContractBillingSchedule(contract_id=contract_id, status="PLANNED", created_by_user_id=actor.id, **data.model_dump())
    db.add(item)
    try: db.flush()
    except IntegrityError as exc:
        db.rollback(); raise ConflictError("DUPLICATE_INSTALLMENT", "Installment number already exists.") from exc
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractBillingSchedule", entity_id=str(item.id), action="contract.finance.schedule_created", new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item); return item


@router.get("/contracts/{contract_id}/schedules", response_model=list[BillingScheduleRead])
def list_schedules(contract_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[ContractBillingSchedule]:
    _contract(db, contract_id)
    return list(db.scalars(select(ContractBillingSchedule).where(ContractBillingSchedule.contract_id == contract_id).order_by(ContractBillingSchedule.due_date, ContractBillingSchedule.installment_number)))


def _editable_schedule_invoice(db: Session, schedule: ContractBillingSchedule) -> ContractInvoice | None:
    invoice = db.scalar(select(ContractInvoice).where(ContractInvoice.schedule_id == schedule.id, ContractInvoice.document_type == "INVOICE"))
    if invoice and (invoice.status != "DRAFT" or _invoice_has_collection(db, invoice.id)):
        raise ConflictError("BILLING_SCHEDULE_LOCKED", "This installment already has an issued or collected invoice and cannot be changed. Adjust a future draft installment instead.")
    return invoice


@router.put("/contracts/{contract_id}/schedules/{schedule_id}", response_model=BillingScheduleRead)
def update_schedule(contract_id: int, schedule_id: int, data: BillingScheduleUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> ContractBillingSchedule:
    _contract(db, contract_id)
    item = db.get(ContractBillingSchedule, schedule_id)
    if not item or item.contract_id != contract_id:
        raise NotFoundError()
    invoice = _editable_schedule_invoice(db, item)
    before = {"description": item.description, "due_date": item.due_date.isoformat(), "amount": str(item.amount)}
    item.description, item.due_date, item.amount = data.description, data.due_date, data.amount
    if invoice:
        invoice.issued_date = data.due_date
        invoice.due_date = data.due_date
        invoice.subtotal = data.amount
        invoice.total_amount = data.amount + invoice.tax_amount
        invoice.reason = f"Draft invoice synchronized with revised schedule: {data.reason}"
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractBillingSchedule", entity_id=str(item.id), action="contract.finance.schedule_updated", reason=data.reason, old_values_json=json.dumps(before), new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item)
    return item


@router.delete("/contracts/{contract_id}/schedules/{schedule_id}", status_code=204)
def delete_schedule(contract_id: int, schedule_id: int, reason: str = Query(min_length=5, max_length=1000), db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> None:
    _contract(db, contract_id)
    item = db.get(ContractBillingSchedule, schedule_id)
    if not item or item.contract_id != contract_id:
        raise NotFoundError()
    invoice = _editable_schedule_invoice(db, item)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractBillingSchedule", entity_id=str(item.id), action="contract.finance.schedule_deleted", reason=reason, old_values_json=json.dumps({"installment_number": item.installment_number, "description": item.description, "due_date": item.due_date.isoformat(), "amount": str(item.amount)})))
    if invoice:
        db.delete(invoice)
    db.delete(item); db.commit()


@router.post("/contracts/{contract_id}/invoices", response_model=ContractInvoiceRead, status_code=201)
def create_contract_invoice(contract_id: int, data: ContractInvoiceWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.invoice.create"))) -> ContractInvoice:
    _contract(db, contract_id); profile = _profile(db, contract_id); _same_currency(profile, data.currency)
    existing = db.scalar(select(ContractInvoice).where(ContractInvoice.idempotency_key == data.idempotency_key))
    if existing: return existing
    if data.due_date < data.issued_date: raise ConflictError("INVALID_INVOICE_DATES", "Invoice due date cannot precede its issue date.")
    if data.schedule_id and not db.scalar(select(ContractBillingSchedule.id).where(ContractBillingSchedule.id == data.schedule_id, ContractBillingSchedule.contract_id == contract_id)):
        raise ConflictError("INVALID_BILLING_SCHEDULE", "Billing schedule does not belong to this contract.")
    if data.reversal_of_invoice_id:
        original = db.get(ContractInvoice, data.reversal_of_invoice_id)
        if not original or original.contract_id != contract_id or data.document_type != "CREDIT": raise ConflictError("INVALID_CREDIT_REVERSAL", "Credit must reverse an invoice on this contract.")
    values = data.model_dump()
    if not values["invoice_number"]:
        prefix = f"INV-{data.issued_date.year}-"
        numbers = list(db.scalars(select(ContractInvoice.invoice_number).where(ContractInvoice.invoice_number.like(f"{prefix}%"))))
        sequence = max([int(match.group(1)) for value in numbers if (match := re.fullmatch(rf"{re.escape(prefix)}(\d+)", value))] or [0]) + 1
        values["invoice_number"] = f"{prefix}{sequence:06d}"
    total = (data.subtotal + data.tax_amount).quantize(Decimal("0.0001"))
    item = ContractInvoice(contract_id=contract_id, total_amount=total, created_by_user_id=actor.id, **values)
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        duplicate = db.scalar(select(ContractInvoice).where(ContractInvoice.idempotency_key == data.idempotency_key))
        if duplicate:
            return duplicate
        raise ConflictError("DUPLICATE_INVOICE", "This invoice request was already processed.") from exc
    if data.schedule_id:
        schedule = db.get(ContractBillingSchedule, data.schedule_id)
        if schedule: schedule.status = "INVOICED"
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractInvoice", entity_id=str(item.id), action="contract.finance.document_posted", reason=data.reason, new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item); return item


@router.put("/contracts/{contract_id}/invoices/{invoice_id}", response_model=ContractInvoiceRead)
def edit_contract_invoice(contract_id: int, invoice_id: int, data: ContractInvoiceEdit, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.invoice.edit"))) -> ContractInvoice:
    invoice = db.get(ContractInvoice, invoice_id)
    if not invoice or invoice.contract_id != contract_id or invoice.document_type != "INVOICE":
        raise NotFoundError()
    if invoice.status not in {"DRAFT", "ISSUED", "DISPUTED"} or _invoice_has_collection(db, invoice_id):
        raise ConflictError("INVOICE_EDIT_LOCKED", "Only an uncollected draft, issued, or disputed invoice can be edited.")
    if data.due_date < data.issued_date:
        raise ConflictError("INVALID_INVOICE_DATES", "Invoice due date cannot precede its issue date.")
    old = {"invoice_number": invoice.invoice_number, "issued_date": invoice.issued_date, "due_date": invoice.due_date, "subtotal": invoice.subtotal, "tax_amount": invoice.tax_amount, "reason": invoice.reason}
    for field, value in data.model_dump().items():
        setattr(invoice, field, value)
    invoice.total_amount = (data.subtotal + data.tax_amount).quantize(Decimal("0.0001"))
    if invoice.schedule_id:
        schedule = db.get(ContractBillingSchedule, invoice.schedule_id)
        if schedule:
            schedule.due_date = data.due_date; schedule.amount = invoice.total_amount
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractInvoice", entity_id=str(invoice.id), action="contract.finance.invoice_edited", reason=data.reason, old_values_json=json.dumps(old, default=str), new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(invoice); return invoice


@router.post("/contracts/{contract_id}/invoices/{invoice_id}/confirm", response_model=ContractInvoiceRead)
def confirm_contract_invoice(contract_id: int, invoice_id: int, data: InvoiceActionWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.invoice.confirm"))) -> ContractInvoice:
    invoice = db.get(ContractInvoice, invoice_id)
    if not invoice or invoice.contract_id != contract_id or invoice.document_type != "INVOICE":
        raise NotFoundError()
    if invoice.status != "DRAFT":
        raise ConflictError("INVOICE_CONFIRM_LOCKED", "Only a draft invoice can be confirmed.")
    invoice.status = "ISSUED"
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractInvoice", entity_id=str(invoice.id), action="contract.finance.invoice_confirmed", reason=data.reason, old_values_json=json.dumps({"status":"DRAFT"}), new_values_json=json.dumps({"status":"ISSUED"})))
    db.commit(); db.refresh(invoice); return invoice


@router.post("/contracts/{contract_id}/invoices/{invoice_id}/cancel", response_model=ContractInvoiceRead)
def cancel_contract_invoice(contract_id: int, invoice_id: int, data: InvoiceActionWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.invoice.cancel"))) -> ContractInvoice:
    invoice = db.get(ContractInvoice, invoice_id)
    if not invoice or invoice.contract_id != contract_id or invoice.document_type != "INVOICE":
        raise NotFoundError()
    if invoice.status in {"CANCELLED", "COLLECTED", "PARTIALLY_COLLECTED"} or _invoice_has_collection(db, invoice_id):
        raise ConflictError("INVOICE_CANCEL_LOCKED", "A collected or already cancelled invoice cannot be cancelled.")
    previous = invoice.status; invoice.status = "CANCELLED"
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractInvoice", entity_id=str(invoice.id), action="contract.finance.invoice_cancelled", reason=data.reason, old_values_json=json.dumps({"status":previous}), new_values_json=json.dumps({"status":"CANCELLED"})))
    db.commit(); db.refresh(invoice); return invoice


@router.get("/contracts/{contract_id}/invoices", response_model=list[ContractInvoiceRead])
def list_contract_invoices(contract_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[ContractInvoice]:
    _contract(db, contract_id)
    return list(db.scalars(select(ContractInvoice).where(ContractInvoice.contract_id == contract_id).order_by(ContractInvoice.issued_date.desc(), ContractInvoice.id.desc())))


@router.get("/contracts/{contract_id}/collection-workspace", response_model=list[InvoiceCollectionRead])
def collection_workspace(contract_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[InvoiceCollectionRead]:
    _contract(db, contract_id)
    invoices = list(db.scalars(select(ContractInvoice).where(ContractInvoice.contract_id == contract_id, ContractInvoice.document_type == "INVOICE", ContractInvoice.status != "CANCELLED").order_by(ContractInvoice.due_date, ContractInvoice.id)))
    return [_invoice_collection(db, invoice) for invoice in invoices]


@router.post("/contracts/{contract_id}/invoices/{invoice_id}/collect", response_model=CollectionRead, status_code=201)
def collect_invoice(contract_id: int, invoice_id: int, data: CollectionWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.payment.collect"))) -> ContractCollection:
    invoice = db.get(ContractInvoice, invoice_id)
    if not invoice or invoice.contract_id != contract_id or invoice.document_type != "INVOICE" or invoice.status == "CANCELLED":
        raise NotFoundError()
    if invoice.status == "DRAFT":
        raise ConflictError("INVOICE_NOT_CONFIRMED", "Confirm the draft invoice before collecting payment.")
    existing = db.scalar(select(ContractCollection).where(ContractCollection.idempotency_key == data.idempotency_key))
    if existing:
        return existing
    reason = db.get(FinanceAdjustmentReason, data.adjustment_reason_id) if data.adjustment_reason_id else None
    if data.adjustment_reason_id and (not reason or not reason.is_active):
        raise ConflictError("INVALID_ADJUSTMENT_REASON", "Select an active finance adjustment reason.")
    if reason and data.discount_amount and reason.adjustment_type not in {"DISCOUNT", "BOTH"}:
        raise ConflictError("INVALID_DISCOUNT_REASON", "The selected reason is not valid for discounts.")
    if reason and data.additional_amount and reason.adjustment_type not in {"ADDITIONAL", "BOTH"}:
        raise ConflictError("INVALID_ADDITIONAL_REASON", "The selected reason is not valid for additional values.")
    current = _invoice_collection(db, invoice)
    settlement = data.actual_payment + data.discount_amount - data.additional_amount
    if settlement <= 0 or settlement > current.remaining:
        raise ConflictError("COLLECTION_EXCEEDS_REMAINING", "The payment plus discount, less additional value, must be positive and cannot exceed the invoice remaining value.")
    item = ContractCollection(contract_id=contract_id, invoice_id=invoice_id, invoice_amount=invoice.total_amount, currency=invoice.currency, created_by_user_id=actor.id, **data.model_dump())
    db.add(item); db.flush()
    if current.remaining - settlement == 0:
        invoice.status = "COLLECTED"
    elif data.actual_payment or data.discount_amount:
        invoice.status = "PARTIALLY_COLLECTED"
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractCollection", entity_id=str(item.id), action="contract.finance.collection_confirmed", reason=data.adjustment_notes, new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item); return item


def _previous_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def _growth(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None if current else Decimal()
    return ((current - previous) * Decimal("100") / previous).quantize(Decimal("0.1"))


def _next_month(value: date) -> date:
    return date(value.year + value.month // 12, value.month % 12 + 1, 1)


@router.get("/dashboard", response_model=FinancialDashboardRead)
def financial_dashboard(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    contract_id: int | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("finance.dashboard.view")),
) -> FinancialDashboardRead:
    today = server_today()
    report_start, report_end = date_from or date(today.year, 1, 1), date_to or today
    if report_start > report_end:
        raise ConflictError("INVALID_FINANCIAL_PERIOD", "From date cannot be after To date.")
    previous_start, previous_end = _previous_year(report_start), _previous_year(report_end)
    client_query = select(Client)
    if client_id is not None:
        client_query = client_query.where(Client.id == client_id)
    if department_id is not None:
        client_query = client_query.where(Client.owner_department_id == department_id)
    clients = {item.id: item for item in db.scalars(client_query)}
    contract_query = select(Contract).where(or_(Contract.client_id.in_(list(clients) or [-1]), Contract.client_links.any(ContractClientLink.client_id.in_(list(clients) or [-1]))))
    if contract_id is not None:
        contract_query = contract_query.where(Contract.id == contract_id)
    contracts = list(db.scalars(contract_query.order_by(Contract.contract_number)))
    departments = {item.id: item.name for item in db.scalars(select(Department))}
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    rows: list[FinancialDashboardContract] = []
    invoice_count = 0
    for contract in contracts:
        profile = db.get(ContractFinanceProfile, contract.id)
        invoices = list(db.scalars(select(ContractInvoice).where(ContractInvoice.contract_id == contract.id, ContractInvoice.document_type == "INVOICE", ContractInvoice.status != "CANCELLED").order_by(ContractInvoice.due_date)))
        collected = [_invoice_collection(db, invoice) for invoice in invoices]
        currency = profile.currency if profile else (invoices[0].currency if invoices else "EGP")
        contract_value = profile.contract_value if profile and profile.contract_value is not None else Decimal()
        invoice_value = sum((item.scheduled_amount for item in collected), Decimal())
        paid = sum((item.actual_payment for item in collected), Decimal())
        discounts = sum((item.discounts for item in collected), Decimal())
        additional = sum((item.additional for item in collected), Decimal())
        current_remaining = sum((item.remaining for item in collected), Decimal())
        all_remaining = max(Decimal(), contract_value + additional - paid - discounts)
        billing_progress = min(Decimal("100"), invoice_value * Decimal("100") / contract_value) if contract_value > 0 else Decimal()
        collection_rate = min(Decimal("100"), paid * Decimal("100") / invoice_value) if invoice_value > 0 else Decimal()
        values = totals[currency]; values["contract_value"] += contract_value; values["invoice_value"] += invoice_value; values["paid_amount"] += paid; values["discounts"] += discounts; values["additional"] += additional; values["remaining"] += current_remaining; values["current_remaining"] += current_remaining; values["all_remaining"] += all_remaining
        linked_names = list(db.scalars(select(Client.name).where(Client.id.in_(contract.customer_ids)).order_by(Client.name)))
        client = clients.get(client_id or contract.client_id)
        rows.append(FinancialDashboardContract(contract_id=contract.id, contract_number=contract.contract_number, contract_name=contract.name, client_id=client.id if client else contract.client_id, client_name=", ".join(linked_names), end_date=contract.end_date, currency=currency, contract_value=contract_value, invoice_value=invoice_value, paid_amount=paid, discounts=discounts, additional=additional, remaining=current_remaining, current_remaining=current_remaining, all_remaining=all_remaining, billing_progress=billing_progress, collection_rate=collection_rate, invoice_count=len(invoices)))
        invoice_count += len(invoices)
    total_rows = []
    for currency, values in sorted(totals.items()):
        contract_value = values["contract_value"]
        invoice_value = values["invoice_value"]
        values["billing_progress"] = min(Decimal("100"), invoice_value * Decimal("100") / contract_value) if contract_value > 0 else Decimal()
        values["collection_rate"] = min(Decimal("100"), values["paid_amount"] * Decimal("100") / invoice_value) if invoice_value > 0 else Decimal()
        total_rows.append(FinancialDashboardTotal(currency=currency, **values))

    contract_ids = [item.id for item in contracts]
    invoices = list(db.scalars(select(ContractInvoice).where(
        ContractInvoice.contract_id.in_(contract_ids or [-1]), ContractInvoice.document_type == "INVOICE",
        ContractInvoice.status != "CANCELLED", ContractInvoice.issued_date <= report_end,
    )))
    invoice_ids = [item.id for item in invoices]
    collections = list(db.scalars(select(ContractCollection).where(ContractCollection.invoice_id.in_(invoice_ids or [-1]), ContractCollection.collected_date <= report_end)))
    allocations = db.execute(select(ContractReceiptAllocation, ContractReceipt).join(ContractReceipt, ContractReceipt.id == ContractReceiptAllocation.receipt_id).where(
        ContractReceiptAllocation.invoice_id.in_(invoice_ids or [-1]), ContractReceiptAllocation.is_reversal == False,  # noqa: E712
        ContractReceipt.status == "CONFIRMED", ContractReceipt.received_date <= report_end,
    )).all()
    ticket_rows = db.execute(select(TicketFinanceLedgerEntry, Ticket).join(Ticket, Ticket.id == TicketFinanceLedgerEntry.ticket_id).where(
        Ticket.client_id.in_(list(clients) or [-1]), TicketFinanceLedgerEntry.status == "CONFIRMED",
        TicketFinanceLedgerEntry.occurred_at < datetime.combine(report_end + timedelta(days=1), datetime.min.time(), tzinfo=server_timezone()),
    )).all()
    by_currency: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "invoiced": Decimal(), "collected": Decimal(), "previous_invoiced": Decimal(), "previous_collected": Decimal(),
        "clients": defaultdict(lambda: defaultdict(Decimal)), "trend": defaultdict(lambda: defaultdict(Decimal)),
        "aging": defaultdict(lambda: [Decimal(), 0]), "statuses": defaultdict(lambda: [Decimal(), 0]),
    })
    contract_client = {item.id: item.client_id for item in contracts}
    invoice_by_id = {item.id: item for item in invoices}
    settlements: dict[int, Decimal] = defaultdict(Decimal)
    for payment in collections:
        settlements[payment.invoice_id] += payment.actual_payment + payment.discount_amount - payment.additional_amount
    for allocation, _receipt in allocations:
        settlements[allocation.invoice_id] += allocation.amount
    for invoice in invoices:
        metrics = by_currency[invoice.currency]; linked_client_id = contract_client[invoice.contract_id]
        if report_start <= invoice.issued_date <= report_end:
            metrics["invoiced"] += invoice.total_amount; metrics["clients"][linked_client_id]["invoiced"] += invoice.total_amount
            metrics["trend"][invoice.issued_date.replace(day=1)]["invoiced"] += invoice.total_amount
        elif previous_start <= invoice.issued_date <= previous_end:
            metrics["previous_invoiced"] += invoice.total_amount
            metrics["trend"][invoice.issued_date.replace(day=1, year=invoice.issued_date.year + 1)]["previous_invoiced"] += invoice.total_amount
        remaining = max(Decimal(), invoice.total_amount - settlements[invoice.id])
        metrics["clients"][linked_client_id]["outstanding"] += remaining
        metrics["statuses"][invoice.status][0] += invoice.total_amount; metrics["statuses"][invoice.status][1] += 1
        if remaining:
            days = (report_end - invoice.due_date).days
            bucket = "Current" if days <= 0 else "1–30 days" if days <= 30 else "31–60 days" if days <= 60 else "61–90 days" if days <= 90 else "90+ days"
            metrics["aging"][bucket][0] += remaining; metrics["aging"][bucket][1] += 1
    for payment in collections:
        payment_invoice = invoice_by_id.get(payment.invoice_id)
        if not payment_invoice:
            continue
        metrics = by_currency[payment.currency]; linked_client_id = contract_client[payment_invoice.contract_id]
        if report_start <= payment.collected_date <= report_end:
            metrics["collected"] += payment.actual_payment; metrics["clients"][linked_client_id]["collected"] += payment.actual_payment
            metrics["trend"][payment.collected_date.replace(day=1)]["collected"] += payment.actual_payment
        elif previous_start <= payment.collected_date <= previous_end:
            metrics["previous_collected"] += payment.actual_payment
            metrics["trend"][payment.collected_date.replace(day=1, year=payment.collected_date.year + 1)]["previous_collected"] += payment.actual_payment
    for allocation, receipt in allocations:
        allocated_invoice = invoice_by_id.get(allocation.invoice_id)
        if not allocated_invoice:
            continue
        metrics = by_currency[allocation.currency]; linked_client_id = contract_client[allocated_invoice.contract_id]
        if report_start <= receipt.received_date <= report_end:
            metrics["collected"] += allocation.amount; metrics["clients"][linked_client_id]["collected"] += allocation.amount
            metrics["trend"][receipt.received_date.replace(day=1)]["collected"] += allocation.amount
        elif previous_start <= receipt.received_date <= previous_end:
            metrics["previous_collected"] += allocation.amount
            metrics["trend"][receipt.received_date.replace(day=1, year=receipt.received_date.year + 1)]["previous_collected"] += allocation.amount
    for entry, ticket in ticket_rows:
        occurred = entry.occurred_at.date(); key = "invoiced" if entry.entry_type == "INVOICE" else "collected" if entry.entry_type == "COLLECTION" else None
        if not key:
            continue
        metrics = by_currency[entry.currency]
        if report_start <= occurred <= report_end:
            metrics[key] += entry.amount; metrics["clients"][ticket.client_id][key] += entry.amount; metrics["trend"][occurred.replace(day=1)][key] += entry.amount
        elif previous_start <= occurred <= previous_end:
            previous_key = f"previous_{key}"; metrics[previous_key] += entry.amount
            metrics["trend"][occurred.replace(day=1, year=occurred.year + 1)][previous_key] += entry.amount

    analytics: list[FinancialCurrencyAnalytics] = []
    aging_order = ["Current", "1–30 days", "31–60 days", "61–90 days", "90+ days"]
    for currency, metrics in sorted(by_currency.items()):
        cursor = report_start.replace(day=1); trend: list[FinancialTrendPoint] = []
        while cursor <= report_end:
            point = metrics["trend"][cursor]
            trend.append(FinancialTrendPoint(label=cursor.strftime("%b %Y"), previous_label=_previous_year(cursor).strftime("%b %Y"), invoiced=point["invoiced"], collected=point["collected"], previous_invoiced=point["previous_invoiced"], previous_collected=point["previous_collected"]))
            cursor = _next_month(cursor)
        total_cash = sum((item["collected"] for item in metrics["clients"].values()), Decimal())
        client_rows = []
        for linked_client_id, client_values in metrics["clients"].items():
            linked_client = clients.get(linked_client_id)
            if not linked_client:
                continue
            share = client_values["collected"] * Decimal("100") / total_cash if total_cash else Decimal()
            client_rows.append(FinancialClientContribution(client_id=linked_client.id, client_name=linked_client.name, department_id=linked_client.owner_department_id, department_name=departments.get(linked_client.owner_department_id) if linked_client.owner_department_id is not None else None, invoiced=client_values["invoiced"], collected=client_values["collected"], outstanding=client_values["outstanding"], collection_share=share.quantize(Decimal("0.1"))))
        client_rows.sort(key=lambda item: (-item.collected, item.client_name))
        outstanding = sum((item[0] for item in metrics["aging"].values()), Decimal()); overdue = sum((metrics["aging"][key][0] for key in aging_order[1:]), Decimal())
        analytics.append(FinancialCurrencyAnalytics(currency=currency, invoiced=metrics["invoiced"], collected=metrics["collected"], outstanding=outstanding, overdue=overdue,
            previous_invoiced=metrics["previous_invoiced"], previous_collected=metrics["previous_collected"], invoiced_growth_percent=_growth(metrics["invoiced"], metrics["previous_invoiced"]), collected_growth_percent=_growth(metrics["collected"], metrics["previous_collected"]), collection_rate=(metrics["collected"] * Decimal("100") / metrics["invoiced"]).quantize(Decimal("0.1")) if metrics["invoiced"] else Decimal(), trend=trend, clients=client_rows,
            aging=[FinancialBreakdownSlice(label=key, amount=metrics["aging"][key][0], count=metrics["aging"][key][1]) for key in aging_order], invoice_status=[FinancialBreakdownSlice(label=key.replace("_", " ").title(), amount=item[0], count=item[1]) for key, item in sorted(metrics["statuses"].items())]))
    return FinancialDashboardRead(totals=total_rows, contracts=rows, contract_count=len(contracts), invoice_count=invoice_count, period=FinancialPeriodRead(start=report_start, end=report_end, previous_start=previous_start, previous_end=previous_end), analytics=analytics)


@router.get("/clients/{client_id}/statement", response_model=ClientStatementRead)
def client_statement(client_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> ClientStatementRead:
    client = db.get(Client, client_id)
    if not client: raise NotFoundError()
    status = db.get(ClientStatus, client.status_id) if client.status_id else None
    contracts = list(db.scalars(select(Contract).where(or_(Contract.client_id == client_id, Contract.client_links.any(ContractClientLink.client_id == client_id))).order_by(Contract.start_date.desc())))
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    contract_rows: list[dict[str, object]] = []
    for contract in contracts:
        invoices = list(db.scalars(select(ContractInvoice).where(ContractInvoice.contract_id == contract.id, ContractInvoice.document_type == "INVOICE", ContractInvoice.status != "CANCELLED").order_by(ContractInvoice.due_date)))
        rows = [_invoice_collection(db, invoice) for invoice in invoices]
        profile = db.get(ContractFinanceProfile, contract.id)
        currency = profile.currency if profile else (rows[0].invoice.currency if rows else "EGP")
        for row in rows:
            values = totals[row.invoice.currency]; values["invoices"] += row.scheduled_amount; values["collected"] += row.actual_payment; values["discounts"] += row.discounts; values["additional"] += row.additional; values["remaining"] += row.remaining
        contract_rows.append({"contract_id": contract.id, "contract_number": contract.contract_number, "contract_name": contract.name, "currency": currency, "invoices": [row.model_dump(mode="json") for row in rows]})
    return ClientStatementRead(client_id=client.id, client_code=client.code, client_name=client.name, account_status=status.name if status else ("Active" if client.is_active else "Inactive"), totals=[ClientStatementCurrencyRead(currency=currency, **values) for currency, values in sorted(totals.items())], contracts=contract_rows)


@router.get("/clients/{client_id}/statement.xlsx")
def export_client_statement(client_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("report.export"))) -> StreamingResponse:
    statement = client_statement(client_id, db, actor)
    book = Workbook(); sheet = book.active; sheet.title = "Client Statement"
    sheet.append(["MILLENSYS Support Hub — Client Statement"]); sheet["A1"].font = Font(bold=True, size=16, color="FFFFFF"); sheet["A1"].fill = PatternFill("solid", fgColor="17365D")
    sheet.append(["Client", statement.client_name, "Code", statement.client_code or "", "Account status", statement.account_status])
    sheet.append([]); sheet.append(["Currency", "Invoices", "Collected", "Discounts", "Additional", "Remaining"])
    for cell in sheet[sheet.max_row]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="1F4E79")
    for total in statement.totals: sheet.append([total.currency, total.invoices, total.collected, total.discounts, total.additional, total.remaining])
    sheet.append([]); sheet.append(["Contract", "Invoice", "Due date", "Currency", "Invoice value", "Collected", "Discount", "Additional", "Remaining", "Status"])
    for cell in sheet[sheet.max_row]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="1F4E79")
    for contract in statement.contracts:
        for row in cast(list[dict[str, Any]], contract["invoices"]):
            invoice = row["invoice"]
            sheet.append([contract["contract_number"], invoice["invoice_number"], invoice["due_date"], invoice["currency"], invoice["total_amount"], row["actual_payment"], row["discounts"], row["additional"], row["remaining"], invoice["status"]])
    for column in sheet.columns: sheet.column_dimensions[column[0].column_letter].width = min(35, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
    output = BytesIO(); book.save(output); output.seek(0)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Client", entity_id=str(client_id), action="client.finance_statement.exported")); db.commit()
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="Client-Statement-{client_id}.xlsx"'})


@router.post("/clients/{client_id}/activate", status_code=204)
def activate_client_account(client_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("client.manage"))) -> None:
    client = db.get(Client, client_id)
    if not client: raise NotFoundError()
    active_id = db.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE", ClientStatus.is_active == True))  # noqa: E712
    if not active_id: raise ConflictError("ACTIVE_CLIENT_STATUS_MISSING", "The ACTIVE client status is not configured.")
    previous = {"status_id": client.status_id, "is_active": client.is_active}
    client.status_id = active_id; client.is_active = True
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Client", entity_id=str(client.id), action="client.activated_from_finance", old_values_json=json.dumps(previous), new_values_json=json.dumps({"status_id": active_id, "is_active": True})))
    db.commit()


@router.post("/contracts/{contract_id}/receipts", response_model=ContractReceiptRead, status_code=201)
def create_contract_receipt(contract_id: int, data: ContractReceiptWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> ContractReceipt:
    _contract(db, contract_id); profile = _profile(db, contract_id); _same_currency(profile, data.currency)
    existing = db.scalar(select(ContractReceipt).where(ContractReceipt.idempotency_key == data.idempotency_key))
    if existing: return existing
    if data.reversal_of_receipt_id:
        original = db.get(ContractReceipt, data.reversal_of_receipt_id)
        if not original or original.contract_id != contract_id or data.status != "REVERSED": raise ConflictError("INVALID_RECEIPT_REVERSAL", "Reversal must reference a receipt on this contract.")
    item = ContractReceipt(contract_id=contract_id, created_by_user_id=actor.id, **data.model_dump())
    db.add(item); db.flush(); db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractReceipt", entity_id=str(item.id), action="contract.finance.receipt_posted", reason=data.reason, new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item); return item


@router.get("/contracts/{contract_id}/receipts", response_model=list[ContractReceiptRead])
def list_contract_receipts(contract_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[ContractReceipt]:
    _contract(db, contract_id)
    return list(db.scalars(select(ContractReceipt).where(ContractReceipt.contract_id == contract_id).order_by(ContractReceipt.received_date.desc(), ContractReceipt.id.desc())))


@router.get("/payments", response_model=list[PaymentWorkspaceRead])
def payment_workspace(db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> list[PaymentWorkspaceRead]:
    rows = db.execute(select(ContractReceipt, Contract, Client).join(Contract, Contract.id == ContractReceipt.contract_id).join(Client, Client.id == Contract.client_id).order_by(ContractReceipt.received_date.desc(), ContractReceipt.id.desc())).all()
    result: list[PaymentWorkspaceRead] = []
    for receipt, contract, client in rows:
        allocated = db.scalar(select(func.coalesce(func.sum(ContractReceiptAllocation.amount), 0)).where(ContractReceiptAllocation.receipt_id == receipt.id, ContractReceiptAllocation.is_reversal == False)) or Decimal()  # noqa: E712
        result.append(PaymentWorkspaceRead(receipt_id=receipt.id, contract_id=contract.id, contract_number=contract.contract_number, client_id=client.id, client_code=client.code, client_name=client.name, receipt_reference=receipt.receipt_reference, received_date=receipt.received_date, amount=receipt.amount, currency=receipt.currency, status=receipt.status, allocated=allocated, unallocated=max(Decimal(), receipt.amount-allocated)))
    return result


@router.post("/contracts/{contract_id}/receipts/{receipt_id}/allocations", response_model=ReceiptAllocationRead, status_code=201)
def allocate_contract_receipt(contract_id: int, receipt_id: int, data: ReceiptAllocationWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("finance.manage"))) -> ContractReceiptAllocation:
    receipt = db.get(ContractReceipt, receipt_id); invoice = db.get(ContractInvoice, data.invoice_id)
    if not receipt or not invoice or receipt.contract_id != contract_id or invoice.contract_id != contract_id: raise NotFoundError()
    if receipt.status != "CONFIRMED" or receipt.imported_unverified: raise ConflictError("RECEIPT_NOT_COLLECTED", "Only a confirmed, reconciled receipt can be allocated.")
    if invoice.currency != receipt.currency: raise ConflictError("ALLOCATION_CURRENCY_MISMATCH", "Receipt and invoice currencies must match.")
    receipt_allocated = db.scalar(select(func.coalesce(func.sum(ContractReceiptAllocation.amount), 0)).where(ContractReceiptAllocation.receipt_id == receipt.id)) or Decimal()
    invoice_allocated = db.scalar(select(func.coalesce(func.sum(ContractReceiptAllocation.amount), 0)).where(ContractReceiptAllocation.invoice_id == invoice.id)) or Decimal()
    if receipt_allocated + data.amount > receipt.amount or invoice_allocated + data.amount > invoice.total_amount:
        raise ConflictError("ALLOCATION_EXCEEDS_BALANCE", "Allocation exceeds the receipt or invoice balance.")
    item = ContractReceiptAllocation(receipt_id=receipt.id, invoice_id=invoice.id, amount=data.amount, currency=receipt.currency, is_reversal=False, reason=data.reason, created_by_user_id=actor.id)
    db.add(item); db.flush(); db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractReceiptAllocation", entity_id=str(item.id), action="contract.finance.receipt_allocated", reason=data.reason, new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item); return item


@router.get("/contracts/{contract_id}/summary", response_model=ContractFinanceSummary | None)
def contract_finance_summary(contract_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("finance.view"))) -> ContractFinanceSummary | None:
    _contract(db, contract_id); profile = db.get(ContractFinanceProfile, contract_id)
    if not profile: return None
    invoices = list(db.scalars(select(ContractInvoice).where(ContractInvoice.contract_id == contract_id, ContractInvoice.status != "CANCELLED", ContractInvoice.imported_unverified == False)))  # noqa: E712
    allocations = db.scalar(select(func.coalesce(func.sum(ContractReceiptAllocation.amount), 0)).join(ContractReceipt).where(ContractReceipt.contract_id == contract_id, ContractReceipt.status == "CONFIRMED", ContractReceipt.imported_unverified == False)) or Decimal()  # noqa: E712
    collected = db.scalar(select(func.coalesce(func.sum(ContractReceipt.amount), 0)).where(ContractReceipt.contract_id == contract_id, ContractReceipt.status == "CONFIRMED", ContractReceipt.imported_unverified == False)) or Decimal()  # noqa: E712
    simple_collections = list(db.scalars(select(ContractCollection).where(ContractCollection.contract_id == contract_id)))
    simple_actual = sum((row.actual_payment for row in simple_collections), Decimal())
    simple_settlement = sum((row.actual_payment + row.discount_amount - row.additional_amount for row in simple_collections), Decimal())
    invoiced = sum((row.total_amount for row in invoices if row.document_type == "INVOICE"), Decimal())
    credited = sum((row.total_amount for row in invoices if row.document_type == "CREDIT"), Decimal())
    overdue = sum((row.total_amount for row in invoices if row.document_type == "INVOICE" and row.due_date < server_today()), Decimal())
    settled = allocations + simple_settlement
    outstanding = max(Decimal(), invoiced - credited - settled)
    return ContractFinanceSummary(currency=profile.currency, invoiced=invoiced, credited=credited, collected=collected + simple_actual, allocated=settled, outstanding=outstanding, overdue=min(overdue, outstanding))
