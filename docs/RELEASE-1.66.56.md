# SupportHub 1.66.56 — AI provider choice and workspace UX

Release date: 2026-09-23

Status: **READY FOR CONTROLLED DEPLOYMENT**

## AI ticket intake

- Adds an optional OpenAI provider alongside the existing local Ollama provider.
- Adds Site Settings controls for provider, model and a masked OpenAI API key.
- Keeps the API key in the Local AI gateway environment rather than application database or audit values.
- Uses strict structured output for OpenAI ticket analysis and disables Ollama reasoning output for faster, cleaner JSON responses.
- Adds provider-aware readiness checks and retains the ability to switch back to local Ollama.

## Tickets workspace

- Simplifies the ticket page header, queue navigation, quick actions and filter workspace.
- Keeps ticket creation prominent and shows bulk actions only when tickets are selected.
- Makes dashboard and report widget drill-down filters authoritative, replacing stale local or saved-view filters.
- Synchronizes browser navigation with ticket filters and resets selections and pagination on drill-down.

## Master Data workspace

- Replaces the two master-data dropdowns with category tabs and one searchable section menu.
- Shows the active category, section and record count while preserving all existing tables, permissions and dialogs.
- Adds responsive English and Arabic labels for section search and counts.

## Deployment

- Database compatibility remains at the current migration head; no migration is introduced by this release.
- Deploy frontend, backend and Local AI files together.
- Preserve production environment settings and configure the desired AI provider before restarting the Local AI service.
- For OpenAI mode, store the API key only through the protected Site Settings workflow or the Local AI environment file.
- Run the normal packaged migration and seed commands, switch IIS paths, recycle the application pool and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 433 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation and the production build passed.
- The standalone runtime exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.56`, database head `0223_vendor_pre_ticket_api`, required frontend/runtime/Local AI contents and ZIP integrity passed.
- Artifact: `releases/SupportHub-1.66.56.zip` (52,683,282 bytes; 1,945 entries).
- SHA-256: `13661CCC538FCF6908B8AF17DFAB3074281342E1B85D2F61FD8E05E130050C9D`.
