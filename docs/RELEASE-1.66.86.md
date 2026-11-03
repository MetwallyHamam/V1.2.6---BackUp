# SupportHub 1.66.86 - Checklist row save fix

Release date: 2026-09-28

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Checklist execution

- Fixes `405 Method Not Allowed` when an engineer saves an individual checklist row.
- Sends checklist row updates with the backend's supported `PUT` method.
- Keeps checklist workflow commands such as start, block, complete, and client handoff on `POST`.
- Includes the complete paginated client lookup and inactive-client name fix from 1.66.85.

## Deployment

- Database revision remains `0234_simple_checklist_rows`; no migration is required.
- Deploy the packaged frontend and backend together.

## Verification

- Frontend lint and TypeScript compilation pass.
- Full release validation and packaged-runtime inspection are executed by the self-contained release builder.
