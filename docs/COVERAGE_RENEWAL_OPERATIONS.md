# Coverage and Renewal Operations

## Coverage changes

Create coverage with an effective start and end within the contract dates. Use the amendment action for scope or eligibility changes; do not replace database rows manually. An amendment closes the prior revision on the day before the new revision begins and records the actor and reason.

Retire coverage when it must no longer apply. Retirement retains the stable coverage record and its revision history. Correct contract dates before adding coverage; later contract-date edits are rejected if they would exclude an existing revision.

For an entitlement investigation, run the entitlement check for the affected client, service/context, and historical date. Preserve the returned status, contract, and revision explanation with the incident evidence.

## Renewal workflow

Create a renewal opportunity with a unique idempotency key, active employee owner, target close date, reason, and all source coverage lines being considered. The system creates an owner task and assignment notification.

Move the opportunity through its governed stage and record each line as renewed, lost, or pending. Closing requires a full, partial, or lost outcome and a reason. A partial outcome requires at least one renewed line. If a successor is linked, it must serve the same primary client and start after the source contract ends; successor coverage references must belong to it. When the successor has no SLA policy, the source SLA/calendar configuration is carried forward.

## Daily control

- Review open opportunities by target close date and owner.
- Escalate overdue renewal tasks through the owning team.
- Confirm every closed partial renewal has explicit line outcomes and reasons for lost scope.
- Confirm successor coverage dates and SLA selection before activating the successor contract.
- Investigate duplicate submissions using the opportunity idempotency key; never delete renewal evidence.

## Release and recovery checks

Before release, migrate a clean database and a populated prior-revision database to `0099_coverage_renewals`, run the full backend/frontend gates, and verify the application compatibility endpoint. Database rollback is restoration from the pre-upgrade backup; renewal and coverage evidence should not be manually truncated.
