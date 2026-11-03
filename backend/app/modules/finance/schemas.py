from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommercialDecisionWrite(BaseModel):
    chargeability: Literal["CONTRACTED", "CHARGEABLE", "NON_CHARGEABLE", "PENDING"]
    approval_status: Literal["PENDING", "APPROVED", "REJECTED"]
    estimated_amount: Decimal | None = Field(default=None, ge=0, max_digits=19, decimal_places=4)
    quoted_amount: Decimal | None = Field(default=None, ge=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern="^[A-Z]{3}$")
    reason: str = Field(min_length=5, max_length=1000)
    expected_sequence: int = Field(ge=0)


class CommercialDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    sequence: int
    chargeability: str
    approval_status: str
    estimated_amount: Decimal | None
    quoted_amount: Decimal | None
    currency: str
    reason: str
    created_by_user_id: int
    created_at: datetime


class LedgerEntryWrite(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    entry_type: Literal["BILLABLE", "INVOICE", "COLLECTION", "WAIVER", "DISPUTE", "ADJUSTMENT"]
    status: Literal["PENDING", "CONFIRMED", "VOID"]
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern="^[A-Z]{3}$")
    payment_method: Literal["CASH", "BANK_TRANSFER", "CHEQUE", "CARD", "MOBILE_WALLET", "OTHER"] | None = None
    external_reference: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=5, max_length=1000)
    occurred_at: datetime
    reversal_of_entry_id: int | None = None

    @model_validator(mode="after")
    def confirmed_collection_requires_reference(self) -> "LedgerEntryWrite":
        if self.entry_type == "COLLECTION" and self.status == "CONFIRMED" and not self.external_reference:
            raise ValueError("A confirmed collection requires an external payment reference.")
        if self.entry_type == "COLLECTION" and self.status == "CONFIRMED" and not self.payment_method:
            raise ValueError("A confirmed collection requires a payment method.")
        return self


class LedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    idempotency_key: str
    entry_type: str
    status: str
    amount: Decimal
    currency: str
    payment_method: str | None
    external_reference: str | None
    reason: str
    occurred_at: datetime
    status_at: datetime
    reversal_of_entry_id: int | None
    created_by_user_id: int
    created_at: datetime


class TicketPaymentWrite(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern="^[A-Z]{3}$")
    payment_method: Literal["CASH", "BANK_TRANSFER", "CHEQUE", "CARD", "MOBILE_WALLET", "OTHER"]
    reference: str = Field(min_length=1, max_length=200)
    paid_at: datetime
    notes: str | None = Field(default=None, max_length=1000)


class FinanceSummaryRead(BaseModel):
    currency: str
    billable: Decimal
    invoiced: Decimal
    collected: Decimal
    waived: Decimal
    disputed: Decimal
    outstanding: Decimal


class TicketFinanceRead(BaseModel):
    ticket_id: int
    ticket_number: str
    client_id: int
    client_code: str | None = None
    client_name: str
    subject: str
    latest_decision: CommercialDecisionRead | None
    entries: list[LedgerEntryRead]
    totals: list[FinanceSummaryRead]


class ContractFinanceProfileWrite(BaseModel):
    currency: str = Field(default="EGP", pattern="^[A-Z]{3}$")
    contract_value: Decimal | None = Field(default=None, ge=0, max_digits=19, decimal_places=4)
    tax_rate: Decimal = Field(default=Decimal(), ge=0, le=1, max_digits=9, decimal_places=6)
    discount_amount: Decimal = Field(default=Decimal(), ge=0, max_digits=19, decimal_places=4)
    billing_model: Literal["FIXED", "INSTALLMENT", "USAGE", "HYBRID"]
    payment_terms_days: int = Field(default=0, ge=0, le=3650)
    billing_frequency: Literal["MONTHLY", "QUARTERLY", "ANNUAL"] = "ANNUAL"
    billing_day: int = Field(default=1, ge=1, le=31)
    invoice_amount: Decimal | None = Field(default=None, gt=0, max_digits=19, decimal_places=4)
    purchase_order_reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)


class ContractFinanceProfileRead(ContractFinanceProfileWrite):
    model_config = ConfigDict(from_attributes=True)
    contract_id: int
    updated_by_user_id: int
    updated_at: datetime


class BillingScheduleWrite(BaseModel):
    installment_number: int = Field(gt=0)
    description: str = Field(min_length=2, max_length=300)
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern="^[A-Z]{3}$")


class BillingScheduleRead(BillingScheduleWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int
    status: str
    created_by_user_id: int
    created_at: datetime


class BillingScheduleUpdate(BaseModel):
    description: str = Field(min_length=2, max_length=300)
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    reason: str = Field(min_length=5, max_length=1000)


class ContractInvoiceWrite(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    schedule_id: int | None = None
    document_type: Literal["INVOICE", "CREDIT"]
    invoice_number: str | None = Field(default=None, max_length=100)
    issued_date: date
    due_date: date
    subtotal: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    tax_amount: Decimal = Field(default=Decimal(), ge=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern="^[A-Z]{3}$")
    status: Literal["DRAFT", "ISSUED", "DISPUTED", "CANCELLED", "PARTIALLY_COLLECTED", "COLLECTED"]
    reversal_of_invoice_id: int | None = None
    reason: str = Field(min_length=5, max_length=1000)
    imported_unverified: bool = False


class ContractInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int
    idempotency_key: str
    schedule_id: int | None
    document_type: str
    invoice_number: str | None
    issued_date: date
    due_date: date
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    status: str
    reversal_of_invoice_id: int | None
    reason: str
    imported_unverified: bool
    created_by_user_id: int
    created_at: datetime


class ContractInvoiceEdit(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=100)
    issued_date: date
    due_date: date
    subtotal: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    tax_amount: Decimal = Field(default=Decimal(), ge=0, max_digits=19, decimal_places=4)
    reason: str = Field(min_length=5, max_length=1000)


class InvoiceActionWrite(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class ContractReceiptWrite(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    receipt_reference: str = Field(min_length=1, max_length=200)
    received_date: date
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern="^[A-Z]{3}$")
    status: Literal["PENDING", "CONFIRMED", "REVERSED"]
    reversal_of_receipt_id: int | None = None
    reason: str = Field(min_length=5, max_length=1000)
    imported_unverified: bool = False


class ContractReceiptRead(ContractReceiptWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int
    created_by_user_id: int
    created_at: datetime


class ReceiptAllocationWrite(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    reason: str = Field(min_length=5, max_length=1000)


class ReceiptAllocationRead(ReceiptAllocationWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    receipt_id: int
    currency: str
    is_reversal: bool
    created_by_user_id: int
    created_at: datetime


class ContractFinanceSummary(BaseModel):
    currency: str
    invoiced: Decimal
    credited: Decimal
    collected: Decimal
    allocated: Decimal
    outstanding: Decimal
    overdue: Decimal


class PaymentWorkspaceRead(BaseModel):
    receipt_id: int
    contract_id: int
    contract_number: str
    client_id: int
    client_code: str | None = None
    client_name: str
    receipt_reference: str
    received_date: date
    amount: Decimal
    currency: str
    status: str
    allocated: Decimal
    unallocated: Decimal


class FinanceAdjustmentReasonWrite(BaseModel):
    code: str | None = Field(default=None, pattern="^[A-Z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    adjustment_type: Literal["DISCOUNT", "ADDITIONAL", "BOTH"] = "DISCOUNT"
    is_active: bool = True


class FinanceAdjustmentReasonRead(FinanceAdjustmentReasonWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CollectionWrite(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    reference: str | None = Field(default=None, max_length=200)
    collected_date: date
    actual_payment: Decimal = Field(ge=0, max_digits=19, decimal_places=4)
    discount_amount: Decimal = Field(default=Decimal(), ge=0, max_digits=19, decimal_places=4)
    additional_amount: Decimal = Field(default=Decimal(), ge=0, max_digits=19, decimal_places=4)
    adjustment_reason_id: int | None = None
    adjustment_notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_adjustment(self) -> "CollectionWrite":
        if self.actual_payment == 0 and self.discount_amount == 0:
            raise ValueError("Actual payment or discount is required.")
        if (self.discount_amount or self.additional_amount) and not self.adjustment_reason_id:
            raise ValueError("An adjustment reason is required for a discount or additional value.")
        return self


class CollectionRead(CollectionWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int
    invoice_id: int
    invoice_amount: Decimal
    currency: str
    created_by_user_id: int
    created_at: datetime


class InvoiceCollectionRead(BaseModel):
    invoice: ContractInvoiceRead
    scheduled_amount: Decimal
    actual_payment: Decimal
    discounts: Decimal
    additional: Decimal
    remaining: Decimal
    collections: list[CollectionRead]


class ClientStatementCurrencyRead(BaseModel):
    currency: str
    invoices: Decimal
    collected: Decimal
    discounts: Decimal
    additional: Decimal
    remaining: Decimal


class ClientStatementRead(BaseModel):
    client_id: int
    client_code: str | None = None
    client_name: str
    account_status: str
    totals: list[ClientStatementCurrencyRead]
    contracts: list[dict[str, object]]


class FinancialDashboardTotal(BaseModel):
    currency: str
    contract_value: Decimal
    invoice_value: Decimal
    paid_amount: Decimal
    remaining: Decimal
    discounts: Decimal
    additional: Decimal
    current_remaining: Decimal
    all_remaining: Decimal
    billing_progress: Decimal
    collection_rate: Decimal


class FinancialDashboardContract(BaseModel):
    contract_id: int
    contract_number: str
    contract_name: str
    client_id: int
    client_name: str
    end_date: date
    currency: str
    contract_value: Decimal
    invoice_value: Decimal
    paid_amount: Decimal
    remaining: Decimal
    discounts: Decimal
    additional: Decimal
    current_remaining: Decimal
    all_remaining: Decimal
    billing_progress: Decimal
    collection_rate: Decimal
    invoice_count: int


class FinancialPeriodRead(BaseModel):
    start: date
    end: date
    previous_start: date
    previous_end: date


class FinancialTrendPoint(BaseModel):
    label: str
    previous_label: str
    invoiced: Decimal
    collected: Decimal
    previous_invoiced: Decimal
    previous_collected: Decimal


class FinancialClientContribution(BaseModel):
    client_id: int
    client_name: str
    department_id: int | None = None
    department_name: str | None = None
    invoiced: Decimal
    collected: Decimal
    outstanding: Decimal
    collection_share: Decimal


class FinancialBreakdownSlice(BaseModel):
    label: str
    amount: Decimal
    count: int


class FinancialCurrencyAnalytics(BaseModel):
    currency: str
    invoiced: Decimal
    collected: Decimal
    outstanding: Decimal
    overdue: Decimal
    previous_invoiced: Decimal
    previous_collected: Decimal
    invoiced_growth_percent: Decimal | None = None
    collected_growth_percent: Decimal | None = None
    collection_rate: Decimal
    trend: list[FinancialTrendPoint]
    clients: list[FinancialClientContribution]
    aging: list[FinancialBreakdownSlice]
    invoice_status: list[FinancialBreakdownSlice]


class FinancialDashboardRead(BaseModel):
    totals: list[FinancialDashboardTotal]
    contracts: list[FinancialDashboardContract]
    contract_count: int
    invoice_count: int
    period: FinancialPeriodRead
    analytics: list[FinancialCurrencyAnalytics]
