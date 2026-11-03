# SupportHub 1.66.22 — Contracts, Ticket Views, and Navigation UX

Status: **SELF-CONTAINED WINDOWS X64 RELEASE**

## Highlights

- Adds configurable contract coverage validation with Product validation as the default, including contract templates and add/edit contract workflows.
- Adds resolution-service scope controls for contract-only services or all available services.
- Corrects ticket Saved View and personal Grid/Cards layout behavior, empty-state headers, filter editing, and In Progress lane membership.
- Reorganizes the application sidebar into six permission-aware work areas without removing routes.
- Adds contextual work-area navigation, breadcrumbs, and a shared page header.
- Makes the Tickets filter toolbar visibly expandable and enables permitted users to double-click the New lane to create a ticket.
- Adds personal drag, reorder, resize, and explicit layout saving to Top Management dashboard widgets.

## Database

- Advances the database head to `0198_view_layout_scope`.
- Run the packaged migration command before starting the upgraded application.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

The release builder runs backend lint, strict type checks, the complete backend test suite, frontend lint, the complete frontend test suite, TypeScript compilation, and the production frontend build before packaging.

- Backend: Ruff and strict MyPy passed; all 394 tests passed.
- Frontend: ESLint, all 68 tests, TypeScript, and the production build passed.
- Standalone runtime commands and ZIP contents were verified.
- Artifact: `releases/SupportHub-1.66.22.zip` (43,220,505 bytes; 1,810 entries).
- SHA-256: `8284D400C8819097F3E666D8A03CBB06CC69CC083C65F7BF136ADD91E9C0ED1B`.
