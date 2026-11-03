# Millensys Support Hub 1.66.118

## Stability and client portal release

- Hardens the escalation scheduler against sustained CPU and memory growth by separating heavy daily stages, recording per-stage working-set metrics, and releasing scheduler database connections after each cycle.
- Prevents generic transient `401` responses from incorrectly logging users out; authoritative refresh-token failures still end the session normally.
- Restores reopened-ticket progression to Resolved and Closed and restores resolution attachment access for eligible users.
- Adds ticket, service, and engineer satisfaction rating in the client portal while keeping an already-submitted public rating link read-only.
- Adds a client-scoped profile page to the portal under the independent `portal.client_profile.view` permission. Internal notes, credentials, audit information, and operational data are not exposed.
- Allows portal users to create Change Request tickets using the existing `CHANGE_REQUEST` catalog type and `CHG` numbering while retaining client-scope and contract-entitlement validation.
- Advances database compatibility to `0248_portal_client_profile`; database migration is required before application startup.

## Deployment

Back up the production database, stop or quiesce the IIS application, run the packaged backend `migrate` command, deploy the packaged frontend and backend together, and recycle the application pool once. Verify login persistence, scheduler working-set logs, portal profile authorization, satisfaction submission, and Change Request creation during smoke testing.
