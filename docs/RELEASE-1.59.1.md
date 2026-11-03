# SupportHub 1.59.1 — SQL Server Dashboard Migration Correction

## Purpose

Correct the SQL Server migration failure in release 1.59.0 while retaining its dashboard-engine and Contract workspace enhancements.

## Correction

- Migration `0170_dashboard_engine` now supplies the required non-null `scope_type` when copying `dashboard.executive` profile grants to the new `topmanagementdashboard.view` permission.
- The copied permission uses the normal unscoped value, `NONE`, matching the IAM model and established migration pattern.
- Adds a release regression test that prevents migration 0170 from omitting the required scope column.

## Deployment

- Do not deploy release 1.59.0.
- Use this release when the database remains stamped at `0169_dashboard_destinations` after the failed 1.59.0 attempt.
- Back up the database before retrying the migration.
- Confirm the current Alembic revision before retrying.
- This release retains database head `0170_dashboard_engine`.

## Included functionality

- Governed dashboard profile access, tabs, reusable widget definitions, and tab placement.
- Dedicated Top Management dashboard navigation permission.
- Editable prospective contract SLA targets.
- Audited reconfiguration of future invoice schedules and synchronized draft invoices.
