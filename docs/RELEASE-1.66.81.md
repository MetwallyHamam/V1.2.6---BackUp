# SupportHub 1.66.81 - Board self-assignment

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Ticket board

- Dropping an unassigned or shared-queue ticket into the Assigned lane now assigns it directly to the logged-in user.
- The action requires `ticket.assign.self`; users without that permission cannot perform the drop.
- The backend limits self-assignment permission to the acting user and rejects attempts to assign another engineer or team.
- New, Triaged and Reopened tickets enter Assigned in the same atomic assignment request, preventing cards from jumping back to New.
- Existing dedicated assignments continue to use the normal workflow status transition.

## Session isolation

- Explicit logout clears saved return navigation and marks the login as a fresh account session.
- A different user now lands on their own configured default page instead of inheriting the previous user's page.
- Automatic session-expiry reauthentication continues to support safe return navigation.

## Checklist assignment

- Replaces the privileged `/users` dependency with a restricted checklist-assignee lookup.
- The lookup requires `service_checklist.reassign` or `service_checklist.schedule.manage`, not `user.manage`.
- Only active employee accounts are exposed and accepted as checklist assignees.
- New recurring checklist schedules default to the logged-in creator when no engineer is explicitly selected.

## Deployment

- Database revision remains `0233_ticket_reports`; no schema migration is required from `1.66.80`.
- Deploy the packaged frontend and backend together because both layers participate in the board and checklist actions.
- Preserve the active `SECRET_KEY`, database settings, integration secrets and chosen `processesPerApplication` value when activating `backend/web_1.66.81.config`.

## Verification

- Full automated release validation and packaged-runtime checks are executed by the self-contained release builder before packaging.
