# SupportHub 1.66.39 — Calendar and Quick Actions

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Enhancements

- Replaces the Support Now planner list with a day, week, month, and custom-range calendar containing colored shift and internal-operation blocks.
- Keeps calendar double-click creation in modal dialogs for internal operations and painted shifts without navigating away from the calendar.
- Changes global Quick Actions from hover-only icons to a click-open labeled menu.
- Sorts Quick Actions by label length, longest first, and gives action types differentiated colored icons.
- Opens ticket, Pre-Ticket, field-visit, and typed internal-operation workflows in dialogs over the current screen.
- Aligns ticket card/row and Support Assistant context actions, retains Add Ticket Flag, and removes the duplicate Customer Contact action while retaining Open WhatsApp.
- Includes all functionality from `1.66.38`.

## Database

- Database head remains `0206_ticket_flags`; no additional migration is introduced.

## Verification

- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 31 test files and 79 tests, TypeScript compilation, and the production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.39`, database head `0206_ticket_flags`, self-contained deployment mode, ZIP readability, and required runtime contents passed.
