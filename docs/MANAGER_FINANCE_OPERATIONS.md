# Manager Finance Operations

Manager Finance is an evidence ledger, not an accounting replacement. Access requires `finance.view`; changes require `finance.manage`.

1. Open **Manager Finance**, enter the ticket ID, and append a commercial decision. Decisions are never edited; a correction is a higher sequence with its reason.
2. Record billable, invoice, collection, waiver, dispute, or adjustment evidence as a new ledger entry. Reusing the same idempotency key returns the original entry.
3. Use `PENDING` until source evidence is verified. Only `CONFIRMED` entries affect totals, and a confirmed collection requires its external payment reference.
4. Never describe estimates, quotes, pending collections, or invoices as collected income. Outstanding is confirmed invoices less confirmed collections and waivers, per currency.
5. Use reversal links and reasoned adjustment entries to correct evidence; do not delete ledger history.

Exception approvals are bound to `operation_scope`, enforce optimistic versions, and can be consumed only once. Approval-group membership and requester/approver separation are enforced unless an administrator performs an audited recovery. Managers should run the overdue-expiry action as part of queue review and use reminders for aging pending requests.
