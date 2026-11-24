# SupportHub 1.66.163

Release date: 2026-11-04

## Work assignment conversion

- Assigned engineers can convert an active work assignment into a ticket from the assignment card.
- The standard ticket form is prefilled with the assignment title, instructions, first related client, task type, and type-specific details.
- Ticket creation, assignment linking, and KPI-source transfer are committed atomically.
- After conversion, the assignment exposes a direct link to the created ticket and no longer offers duplicate conversion.
- Assignment KPI credit is disabled after conversion so the resulting ticket remains the authoritative KPI source.

## Database

- Database revision remains `0278_work_assignment_context`.
- No additional migration is required when upgrading from `1.66.162`.

## Deployment

Deploy the complete `1.66.163` package and recycle the IIS application pool. Smoke-test assignment claim/accept, ticket-form prefilling, successful conversion, the converted-ticket link, and KPI attribution.
