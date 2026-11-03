# Financial Workspace and Governance

Status: implemented in source; professional financial analytics are awaiting UAT/release approval.

## Unified workspace

The navigation now exposes one **Financial** page at `/financial` with permission-controlled tabs:

- Financial analysis
- Invoices & payments
- Ticket finance

The old `/manager-finance` and `/payments` URLs remain compatible and open the consolidated page.

## Permissions

- `finance.view`: view invoices, payments, statements, and ticket finance.
- `finance.dashboard.view`: view the executive financial dashboard and financial widgets on the normal dashboard.
- `finance.invoice.create`: create draft invoices.
- `finance.invoice.edit`: edit draft/issued/disputed invoices before collection.
- `finance.invoice.confirm`: confirm a draft invoice and issue it.
- `finance.invoice.cancel`: cancel an uncollected invoice with a mandatory reason.
- `finance.payment.collect`: confirm payments, discounts, and additional values.
- `finance.manage`: maintain finance administration data such as adjustment reasons and contract financial profiles.

These permissions can be granted to any specific profile from **Profiles & Privileges**. Existing profiles that already have `finance.manage` receive all new finance permissions through migration `0112_financial_governance`. Migration `0118_top_mgmt_finance` grants Top Management only `finance.dashboard.view`; it does not grant invoice, collection, or finance-management rights.

## Invoice lifecycle

1. Create a draft invoice.
2. Edit it while it has no collection.
3. Confirm it to change status from `DRAFT` to `ISSUED`.
4. Collect payments from the invoice row.
5. Cancellation is allowed only before any payment or discount collection.

Every edit, confirmation, and cancellation requires a reason and creates an audit record.

## Professional financial analytics

Status: **Done in source**.

The Financial page and Top Management dashboard now provide:

- selected-period invoiced revenue and confirmed cash collection;
- same-period prior-year comparison and growth percentages;
- monthly invoice, collection, and prior-year collection trend;
- client cash-contribution analysis;
- accounts-receivable aging buckets;
- invoice-status value distribution;
- primary owner-department and client filters;
- separate analysis for each currency; and
- per-dashboard show/hide chart preferences stored in the browser.

The existing profile widget codes remain compatible, but now render an income/collection trend and client cash-contribution chart instead of count cards. Monetary chart labels omit database-only trailing zeros.

“Cash contribution” is not labelled profit: profit requires cost and revenue-recognition data that this module does not currently store. Shared client departments do not duplicate finance; department attribution uses the client's primary owner department.

## Ticket payment evidence

Status: **Done in source**.

Confirmed ticket-finance collection entries require both a payment reference and a payment method. Supported methods are bank transfer, cash, cheque, card, mobile wallet, and other. Existing ledger records remain valid with a null payment method; new confirmed collections are validated by the API.
