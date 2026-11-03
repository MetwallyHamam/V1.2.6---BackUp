# SupportHub 1.63.2 - SQL Server Top Support Agents Fix

Status: CORRECTIVE RELEASE CANDIDATE

## Correction

- Fixes the Top Support Agents dashboard query for SQL Server.
- Replaces the unsupported `SUM(CASE ... IN (SELECT ...))` expression with a left join to a distinct set of breached resolution-SLA ticket IDs.
- Preserves ranking by resolved-ticket count, then breached-ticket count, then agent name.
- Ensures a ticket is counted as breached once even if duplicate matching SLA-clock rows exist.
- Adds endpoint coverage for a breached resolved ticket and SQL Server-dialect query compilation validation.

## Database

- No database migration is required.
- Required Alembic head remains `0186_support_assistant_prefs`.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package as a new versioned release; do not modify an existing release directory.
3. Switch both IIS `/SupportHub` application paths to the new frontend and backend directories, then restart the application pool.
4. Verify `GET /SupportHub/backend/api/v1/dashboards/top-support-agents` returns HTTP 200 for a dashboard-authorized user.