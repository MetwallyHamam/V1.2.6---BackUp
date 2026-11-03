# Contract expiration notification review — 2026-10-01

## Critical finding: scheduler transaction ownership (fixed in source)

The SQL Server application-lock query starts a transaction on the connection
shared by scheduler stages. Stage sessions join that transaction; their commits
do not commit the outer transaction. Closing the lock session rolls back queue
claims and delivery evidence even though SMTP has already sent the message.
This permits repeated sends and PENDING/0 records after an actual send.

A regression test models the lock query's transaction using a real SQLAlchemy
connection and a mocked SMTP sender. It failed before the change (SENT reverted
to PENDING). The scheduler now commits the lock acquisition transaction before
starting stages. The session-owned SQL Server lock remains held until release.
The regression verifies persisted SENT and exactly one send across two cycles.
This reproduces the transaction mechanism locally; live SQL Server and mailbox
delivery have not been verified in this review.

## High priority: uncertain SMTP acknowledgement (fixed in source)

Contract attempts and PROCESSING ledger state are committed before SMTP. Final
results are committed immediately after each contract message. Network failures
with uncertain acceptance become UNKNOWN and are not automatically resent.
Explicit SMTP rejection retains bounded retries. A regression verifies a timeout
cannot produce a second automatic send. A process crash can still leave
PROCESSING and requires review; automatically resetting it risks duplicate mail.
SMTP cannot guarantee exactly-once delivery across process/database failure.

## Activity display (fixed in source)

Failed activity queries no longer also display the empty-history message.
The UI explains SMTP acceptance versus inbox delivery and uncertain outcomes.

## Remaining gaps requiring operational verification or further work

- P0: Confirm the corrected scheduler against the deployed SQL Server and inspect
  current outbox/ledger records before resetting any historical events. Old
  PENDING rows may already have been emailed; do not bulk resend them.
- P1: SMTP partial recipient refusal needs recipient-level acceptance reporting;
  successful send_message can still report refused recipients.
- P1: A governed reconciliation/retry action is needed for UNKNOWN and stale
  PROCESSING outcomes, with a duplicate-risk warning and an audit record.
- P1: Scheduler diagnostics remain per-process and are not durable across IIS
  restarts. Store worker/stage execution evidence in the database.
- P1: Migrations 0241/0242 historically mark uncertain/suppressed records SENT.
  That is suppression evidence, not proof of SMTP acceptance. Do not use those
  rows alone to infer inbox delivery.
- P2: Revalidate queued contract eligibility and recipients at send time; queued
  payloads may become stale after a contract or recipient configuration change.

No production data was deleted, no production messages were sent, and no new
release was built as part of this review. Existing 1.66.99 archives do not contain
these source changes. No new schema migration is required for these changes.
