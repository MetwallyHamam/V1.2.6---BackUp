# Support Hub 1.66.100

Fixes scheduler transaction ownership that could roll back email delivery
evidence after SMTP accepted a message, allowing repeated expiration emails.
Contract attempts are persisted before SMTP and results committed per message.
Uncertain network outcomes become UNKNOWN and are not automatically retried.
Activity distinguishes failed loading from empty history and explains delivery states.

Database head remains `0242_contract_email_key`; no new migration is required
when upgrading from 1.66.99.

Deploy with SMTP disabled and all old IIS workers stopped. Preserve production
configuration, set APP_VERSION to 1.66.100, then restart the pool. Review existing
PENDING and PROCESSING contract events before enabling SMTP: previous workers
may already have sent them without retaining evidence. Do not bulk reset them.
SENT means SMTP acceptance, not guaranteed inbox delivery. UNKNOWN requires
administrator review before any resend.

Local regression tests reproduce the outer-transaction failure and verify one
send across repeated scheduler cycles. Live SQL Server and mailbox delivery
remain deployment verification steps.
