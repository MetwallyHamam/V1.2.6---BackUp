# SupportHub 1.66.26 — Inline Cards Resolution Workflow

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — GENERATED AND VERIFIED**

## Highlights

- Keeps ticket resolution entirely inside the Cards board without opening Ticket Details.
- Loads the client's contract-valid provided services and preselects the configured default resolution service.
- Requires a resolution summary and root cause selection.
- Displays required resolution outcome and permanent-fix evidence according to the selected root causes.
- Includes Create Knowledge Article and Close After Resolve controls.
- Includes all enhancements and corrections from `1.66.25`.

## Database

- Database head remains `0198_view_layout_scope`; no migration is required.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 395 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript compilation, and the production build passed.
- The bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed.
