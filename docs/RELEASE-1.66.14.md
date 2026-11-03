# SupportHub 1.66.14 — Assistant Status Filter Experience

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Replaces manual comma-separated status-code entry in Support Assistant settings with a lookup-backed multi-select.
- Shows localized status names, status colors, checkboxes, and removable selection chips.
- Applies the same status lookup experience to built-in and custom personal tabs.
- Improves the Built-in Tabs settings layout with responsive field grouping and visible active-filter indicators.
- Adds matching English and Arabic interface text.

## Database

- No schema change is required.
- Database head remains `0193_assistant_user_state`.

## Deployment

Back up the production database before deployment. Deploy to a new versioned directory, run `backend\runtime\SupportHubBackend.exe migrate`, switch IIS paths, and verify Assistant status filtering with a test engineer account.

## Verification

- Backend Ruff and strict MyPy passed.
- All 392 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Standalone runtime command and clean packaged migration through `0193_assistant_user_state` passed.
