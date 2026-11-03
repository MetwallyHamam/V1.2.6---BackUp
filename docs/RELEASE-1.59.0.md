# SupportHub 1.59.0 — Dashboard Engine and Contract Workspace Enhancements

## Purpose

Deliver the governed dashboard engine and make contract SLA and future billing plans maintainable from the Contract workspace.

## Dashboard engine

- Introduces explicit profile-to-dashboard access with one active default dashboard per profile.
- Introduces configurable dashboard tabs, reusable widget definitions, and tab-specific widget placement.
- Adds the dedicated `topmanagementdashboard.view` permission for the Top Management navigator.
- Removes the misleading generated-profile-dashboard behavior from the governed dashboard flow.
- Keeps Executive and Top Management destinations isolated and permission-aware.
- Improves Dashboard Administration for template, tab, widget-catalog, placement, access, and preview management.

## Contract SLA workspace

- Allows authorized contract managers to add, edit, and remove product/module-scoped SLA targets.
- Supports response, resolution, warning percentage, and effective-date maintenance.
- Applies SLA configuration changes prospectively so existing ticket SLA snapshots and audit history remain unchanged.
- Reorganizes the Contract SLA experience into a clearer, less noisy management workflow.

## Contract financial plan

- Allows authorized finance users to reconfigure the contract billing profile and regenerate future draft installments.
- Allows future schedule installments to be added, edited, or removed with an audit reason.
- Synchronizes edited schedules with their draft invoices.
- Prevents changes to issued or collected invoice obligations through the schedule editor.
- Preserves financial summaries for invoiced, collected, outstanding, and overdue values.

## Database and deployment

- Advances the database revision to `0170_dashboard_engine`.
- Migration 0170 creates dashboard profile access, dashboard tabs, widget definitions, and tab-widget placements while migrating existing governed dashboard data.
- Back up production and perform an upgrade rehearsal against a recent production copy before switching IIS to this release.

## Scope note

The ticket creation and workflow gap assessment added in this workspace is planning documentation only. Its remediation items are not implemented in this release.
