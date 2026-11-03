# Contracts and SLA

This increment adds contract master data and deterministic SLA deadlines.

Implemented capabilities:

- Client contracts with status, start/end dates, renewal notice, timezone, and coverage summary
- Contract coverage records for product, branch, and environment combinations
- Coverage rules for product modules, services, and ticket types, including explicit exclusions
- Server-side validation that branches belong to the contract client and modules belong to the selected product
- Deterministic specificity resolution, with exclusions winning when equally specific rules conflict
- Ticket entitlement snapshots and audited management override reasons
- Included-request-limit enforcement and contract document upload/download administration
- Contract lifecycle status changes with audit records
- Secure contract document deletion with protected storage and extension/signature validation
- Upcoming-renewal queries and idempotent in-app reminders for contract administrators
- Relational business calendars and holidays
- SLA policies and P1–P4 first-response/resolution targets
- Cairo Sunday–Thursday 08:00–17:00 seed calendar
- Working-time calculations that skip weekends and configured holidays
- Automatic active-contract selection during ticket creation
- Default-policy fallback when no client-specific policy exists
- Persisted first-response and resolution clocks with calculation version
- Ticket SLA panel and contract administration screen

Entitlement behavior:

- Active contracts are evaluated for the ticket date and client.
- Coverage rules may constrain product, module, branch, environment, service, and ticket type.
- The most specific rule wins; an exclusion wins when equally specific rules conflict.
- Existing clients without an entered contract receive a `NO_CONTRACT` snapshot for remediation.
- Once an active contract exists, excluded, uncovered, or limit-exceeded requests are blocked for portal users. Authorized employees must enter an override reason, which is persisted and audited.
- Contract files use the same protected type, signature, path-containment, and size controls as ticket attachments.

Seed targets:

| Priority | First response | Resolution |
|---|---:|---:|
| P1 | 15 minutes | 4 working hours |
| P2 | 30 minutes | 8 working hours |
| P3 | 2 working hours | 24 working hours |
| P4 | 4 working hours | 48 working hours |

The values are initial defaults and should be replaced or overridden by approved
contract policies before production use.
