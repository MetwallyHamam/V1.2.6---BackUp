# SupportHub 1.35.0

Ticket workspace and role-based onboarding program release.

## Ticket workspace

- Consolidates My Queue, engineer queues, team tickets, department requests, and CSV export in the Fast Actions bar.
- Moves Columns and Save View into the filter bar and makes the entire filter heading keyboard-accessible and clickable.
- Adds ticket filters for content, operational attributes, safety/security flags, and additional lifecycle dates.
- Adds visual Group By for status, priority, engineer, team, department, client, source, and entitlement, persisted in saved views.

## Employee onboarding

- Adds stable template codes, categories, durations, ordering, task types, completion rules, availability offsets, due offsets, and approval requirements.
- Adds reusable role-based programs that combine ordered checklist templates into one immutable employee snapshot.
- Adds employee submission, manager/authorized override review, required-task enforcement, and automatic plan completion.
- Seeds onboarding catalogs, materials, focused templates, and PACS, RIS, and general-support programs without inserting external resource URLs.
- Retains compatibility with existing single-template onboarding assignments.

## Database and verification

- Database revision: `0123_onboarding_programs`.
- Clean migration rehearsal passed through the new head.
- Backend Ruff, strict MyPy, and all 260 tests passed.
- Frontend ESLint, all 9 tests, TypeScript, and the production Vite build passed.
