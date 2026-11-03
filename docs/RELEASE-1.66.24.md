# SupportHub 1.66.24 — Cards Workflow Transition Fixes

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — GENERATED AND VERIFIED**

## Highlights

- Opens the complete governed resolution workflow when a Cards-view ticket is moved to Resolved.
- Keeps Resolved-to-Closed transitions in the Cards view and preserves the ticket's provided services.
- Keeps In-Progress-to-Pending Internal and Pending Client transitions in the Cards view.
- Requires the pending reason, responsible party, follow-up owner, and follow-up deadline in the inline transition dialog.
- Includes all enhancements and corrections from `1.66.23`.

## Database

- Database head remains `0198_view_layout_scope`; no migration is required.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 394 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript compilation, and the production build passed.
- The bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed.
