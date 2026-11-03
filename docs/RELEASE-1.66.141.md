# Support Hub 1.66.141

Release date: 2026-10-15

## Highlights

- Adds the active **Deployment / Follow UP** service to the service catalog.
- Defaults deployment-issue resolution to root cause **Other** and service provided **Deployment / Follow UP** while keeping both fields editable.
- Includes the deployment owner in the **Resolved by** list even when the owner is not assigned an engineering role.
- Allows deployment follow-up items to be classified or changed between **Issue** and **Change Request**; new Change Request items create `CHG-` tickets.
- Keeps the Support Hub server clock authoritative for reported, resolved, and delivered timestamps; manual browser entries are sent with an explicit offset and date-order errors are shown before submission.
- Adds a collapsible deployment-plan sidebar, a visible **Add Issue** shortcut, and double-click issue creation in the Open lane.
- Consolidates all deployment issues into one multi-column table in PDF and Word reports.
- Uses landscape report pages and fitted column widths so issue details remain readable.

## Database

- Advances the database head to `0267_deployment_defaults`.
- The migration is idempotent: it creates or reactivates the service and root cause without duplicating existing catalog entries.
- Existing ticket-wide default service behavior is unchanged; the new default applies specifically to deployment-issue resolution.

## Deployment notes

1. Back up the production database and application files.
2. Deploy the complete `1.66.141` release while retaining production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate` from the release root.
4. Start or recycle the Support Hub application pool.
5. Open a deployment issue resolution dialog and confirm **Other** and **Deployment / Follow UP** are preselected.
6. Confirm the deployment owner appears under **Resolved by** and that an item can be changed to **Change Request**.
7. Export a deployment report to PDF and Word and confirm its items appear in one landscape table.
