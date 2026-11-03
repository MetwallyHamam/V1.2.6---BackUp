# SupportHub 1.56.1 — KPI Draft Management and Top Management Widgets

## Purpose

Correct the Top Management dashboard assignment integration and add safe management of KPI Drafts before submission.

## Corrections and enhancements

- Adds an Assigned Profile Dashboard tab to Top Management, resolved from the same effective Dashboard Administration assignment used by the governed dashboard API.
- Renders authorized widgets from the assigned Top Management profile template and lists the same widgets in the Top Management show/hide dialog.
- Keeps Executive Overview, Customer Service Success, and Financial Analysis available as separate analytics tabs.
- Ensures standard KPI cards obey the effective widget configuration.
- Lists existing KPI Drafts in Team Workflow and allows them to be reopened in the editor for repeated rating and comment changes.
- Allows authorized deletion of never-submitted KPI Drafts after confirmation and records the deletion in the audit log.
- Protects submitted, reopened, and submission-container-linked KPI evidence from deletion.

## Database and deployment

Database revision remains `0165_kpi_submission_batches`; this corrective release adds no migration. Back up production, deploy to a new immutable directory, run the packaged migration compatibility check and seed command, and complete the smoke test before switching IIS.

