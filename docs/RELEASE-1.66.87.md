# Millensys Support Hub 1.66.87

## Highlights

- Redesigns Service Checklists around persistent engineer/client assignment cards, reusable checklist events, history, engineer transfers, reminders, exports, secure sharing, and manager monitoring.
- Adds consistent checklist status colors across grid, lane, and history views.
- Creates system-controlled Scheduled Service tickets from checklist events without requiring ticket-create permission or applying SLA.
- Adds Client Safeguard checklist metrics to Customer Success, Client Profile, and Support Now.
- Changes the Support Assistant Ops tab into an in-place personal operations view scoped to the logged-in user.
- Fixes ticket-board assignment transitions and approval handling, complaint caller validation, and Operational Board checklist lanes.

## Database

- Database revision: `0235_service_checklist_shares`.
- Apply migrations before starting the upgraded application.

## Deployment

- Self-contained Windows x64 backend runtime; no server-side Python installation is required.
- Review and merge `backend/web_1.66.87.config` without overwriting the active server configuration.
