# Ticket Finance Payment Enhancement

Status: `COMPLETED`  
Release: `1.29.2`  
Completed: 2026-08-23

## Objective

Allow a finance manager to select a ticket and record payments for the client linked to that ticket without manually creating an invoice ledger entry first.

## Delivered workflow

1. Open **Financial → Ticket Finance** and find a ticket by number, subject, client code, or client name.
2. Select the ticket; its authoritative linked client from `ticket.client_id` is displayed and locked.
3. Select **Add payment** and enter amount, currency, payment method, receipt/reference, payment date/time, and optional notes.
4. The backend uses any existing outstanding ticket invoice balance first.
5. If no invoice exists or the balance is insufficient, a confirmed invoice ledger entry is created automatically for exactly the missing amount.
6. The confirmed collection is created atomically for the same ticket/client.
7. Multiple and partial payments are supported and appear in finance evidence/history.

## Governance and safety

- The client is derived server-side and cannot be changed by the payment request.
- Method and external reference are mandatory.
- Automatic invoice and collection either both succeed or neither is saved.
- Idempotency prevents duplicate invoices/payments on retries.
- Separate audit events include the ticket and client IDs.
- Currency totals remain separate.
- Advanced Ledger remains available for specialized invoice, billable, waiver, dispute, and adjustment evidence, but is not required for normal payments.
- Existing history is unchanged and no database migration is required.

## API and changed components

```text
POST /manager-finance/tickets/{ticket_id}/payments
```

- `backend/app/modules/finance/schemas.py`
- `backend/app/modules/finance/routes.py`
- `frontend/src/pages/ManagerFinancePage.tsx`
- `backend/app/tests/test_exception_finance.py`

## Acceptance evidence

- First and subsequent payments automatically create only the invoice amount required.
- Idempotent retries return the original payment without duplication.
- Invoiced, collected, and outstanding totals reconcile.
- Ruff passed.
- Focused finance suite passed: 7 tests.
- TypeScript compilation and production frontend build passed.

## Definition of done

- Managers record payments without using Advanced Ledger.
- Payments always belong to the selected ticket's linked client.
- Automatic invoices and payments are atomic, auditable, and reflected in financial totals.
