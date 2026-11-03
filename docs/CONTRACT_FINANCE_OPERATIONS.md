# Contract Finance Operations

Contract finance is optional and uses one financial profile per contract. EGP is the UI default, and the selected contract currency governs all scheduled invoices and collections. The profile records contract value, optional per-invoice value, monthly/quarterly/annual frequency, and billing day. Saving the simplified profile generates the dated invoice schedule automatically.

Managers collect an invoice through four financial values: invoice value, actual payment, discount, and additional value. The remaining balance is `invoice + additional - actual payment - discount`. Discounts and additional values require an active governed reason and may include additional free text. Default reasons cover SLA deduction, business required deduction, and exception.

Client statements show invoiced, collected, discounted, additional, and remaining totals per currency. They are visible to `finance.view` users in Invoices & Payments and Client Profile; Excel export requires `report.export`, and activating an inactive client requires `client.manage`.

Create schedules for planned installments, then post invoices with unique idempotency keys. Corrections use credit documents referencing the original invoice; posted rows are never edited or deleted. Record bank receipts as pending until independently confirmed. Imported balances stay marked unverified until reconciliation.

Allocate only confirmed, reconciled receipts to invoices. The system rejects allocations beyond either the receipt balance or invoice balance and rejects cross-currency allocation. Collected income means confirmed receipt value; allocated and outstanding values remain separate.

Daily controls:

- Review issued invoices by due date and disputed items separately.
- Reconcile receipt references against the authoritative bank/accounting source before confirmation.
- Review unallocated confirmed receipts and overdue invoice balances.
- Correct mistakes with credits or reversals, preserving the original evidence and reason.
- Restrict finance access to users with `finance.view` or `finance.manage`.

Release recovery uses a pre-upgrade database backup. Validate clean and populated migration to `0100_contract_finance`, full tests, compatibility status, and finance reconciliation before deployment.
