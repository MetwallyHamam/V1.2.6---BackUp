# SupportHub 1.66.33 — Service Checklists and Performance

Status: **WITHDRAWN BEFORE DEPLOYMENT — DO NOT DEPLOY**

This candidate exposed a clean-install compatibility defect in migration `0197_ticket_requirements` during packaged-runtime rehearsal. It is superseded by `1.66.34`.

## Highlights

- Adds the governed Service Checklists workspace with reusable templates, scheduled occurrences, card lanes, task progression, ticket creation, and auditable completion evidence.
- Supports Client-responsible checklist tasks with mandatory email, screenshot, or document evidence and exclusion from scheduling completion requirements.
- Improves the Top Management world map with smoother hover behavior, lower rendering cost, and clearer light/dark presentation.
- Optimizes the Tickets list endpoint by batch-loading SLA, user, client, assignment, and department evidence instead of issuing queries per ticket.
- Includes all enhancements and corrections from `1.66.32`.

## Database

- Database head advances to `0203_checklist_schedules`; migration is required.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, recycle the application pool, and complete the supplied smoke test.

## Verification

- The release builder runs backend Ruff, strict MyPy, the complete backend test suite, frontend ESLint, the complete frontend test suite, TypeScript compilation, and the production frontend build before packaging.
- The self-contained runtime, manifest, database revision, archive integrity, required contents, and forbidden-file checks must pass before deployment.
