# SupportHub 1.66.41 — Ticket Creation and Context Actions

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Enhancements and corrections

- Corrects the global Quick Actions `+` ticket form so **Create ticket** closes the dialog after successful creation.
- Adds **Create and new**, which creates the current ticket and resets the form with a fresh idempotency key for immediate entry of another ticket.
- Aligns ticket context menus across web card/list views and Support Assistant right-click/three-dot entry points.
- Places Pin/Unpin first, groups the six frequent commands under Common actions, and moves secondary commands into a Windows-style hover submenu.
- Shares persisted ticket pins between the web ticket workspace and Support Assistant.
- Corrects View status history to focus on status changes and display each previous-to-new status transition with its reason, actor, and timestamp.
- Corrects removal of an SLA target from a contract linked to a shared central policy; the contract now receives an independent policy copy while the central policy and other contracts remain unchanged.
- Adds multi-client Visit Entitlement creation from the contract workspace, with duplicate removal and atomic validation/creation across every selected client.
- Includes all functionality from `1.66.40`.

## Database

- Database head remains `0206_ticket_flags`; no additional migration is introduced.

## Verification

- Backend Ruff and strict MyPy passed; all 404 backend tests passed.
- Frontend ESLint, Vitest, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version/database revision and ZIP integrity checks passed.
