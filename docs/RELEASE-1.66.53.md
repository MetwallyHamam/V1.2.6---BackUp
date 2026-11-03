# SupportHub 1.66.53 — Client UAT interaction and Support Now correction

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Client Portal UAT

- Prevents the UAT workspace from failing when browser storage is unavailable or restricted.
- Opens test cards in an immediate right-side details drawer.
- Adds explicit Start testing and Move to ready actions to card and right-click menus.
- Corrects right-click menu rendering and preserves controlled drag-and-drop for assigned testers.
- Keeps tester assignment, portal permissions, sign-off and result restrictions enforced.

## Support Now

- Adds separate Waiting for approval and Pending tickets cards with filtered drill-through links.
- Excludes approval-pending and workflow-pending tickets from Open tickets.
- Defines Need attention as actionable open tickets with an SLA deadline later today.
- Excludes pending and approval-pending tickets from Need attention.

## Deployment

- Database compatibility revision remains `0222_uat_template_clients`; no new migration is introduced.
- Self-contained Windows x64 deployment under `/SupportHub/`.
