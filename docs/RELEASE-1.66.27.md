# SupportHub 1.66.27 — Default Resolution Service Selection

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Returns the CRM default-resolution-service flag in the contract-scoped ticket catalog.
- Automatically selects the configured default Service Provided in Cards resolution.
- Automatically selects the same default in the Ticket Details resolution workflow.
- Keeps the service selection editable so engineers can add or remove provided services.
- Includes all enhancements and corrections from `1.66.26`.

## Database

- Database head remains `0198_view_layout_scope`; no migration is required.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 395 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript compilation, and the production build passed.
- The packaged backend runtime command passed.
- ZIP integrity, required entries, and forbidden generated-file inspection passed (1,810 entries).
