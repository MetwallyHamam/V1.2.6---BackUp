# SupportHub 1.66.34 — Service Checklists and Performance

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Replaces withdrawn candidate `1.66.33` and corrects clean-install compatibility for ticket-requirement migration `0197`.
- Adds the governed Service Checklists workspace with reusable templates, scheduled occurrences, card lanes, task progression, ticket creation, and auditable completion evidence.
- Supports Client-responsible checklist tasks with mandatory email, screenshot, or document evidence and exclusion from scheduling completion requirements.
- Improves the Top Management world map with smoother hover behavior, lower rendering cost, and clearer light/dark presentation.
- Optimizes the Tickets list endpoint by batch-loading SLA, user, client, assignment, and department evidence instead of issuing queries per ticket.
- Includes all deployable enhancements and corrections from `1.66.32`.

## Database

- Database head advances to `0203_checklist_schedules`; migration is required.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, recycle the application pool, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 401 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and the production build passed.
- Source and packaged-runtime clean migrations completed through `0203_checklist_schedules`.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, database head, deployment mode, required contents, ZIP readability, and forbidden-file inspection passed (1,830 entries).
- Artifact before final documentation refresh: `releases/SupportHub-1.66.34.zip` (43,344,981 bytes).
- Initial SHA-256: `4A2E128210FBCE7E6F083945DE16686D1FBCBC7C991F7CB542B98C6D2B8156FD`.
- Final artifact: `releases/SupportHub-1.66.34.zip` (43,345,346 bytes; 1,830 entries).
- Final SHA-256: `9BF03B07E92F8C7FC0A03BE057D5E632302E5F93B045D3B13A04C95598689119`.
