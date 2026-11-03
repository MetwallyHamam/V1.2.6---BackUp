# Dashboards, Saved Views, and Reporting

The dashboard now uses live permission-scoped data and shows open, assigned,
unassigned, P1, breached, due-soon, resolved, and closed ticket counts, plus
priority/status breakdowns and contracts expiring within 30 days.

Saved views persist owner, private/global scope, validated JSON filters, columns,
sorting, and default state. Global views require configuration authority.

Ticket CSV export is capped at 10,000 authorized rows and prefixes untrusted
values beginning with `=`, `+`, `-`, or `@` to prevent spreadsheet formula
execution.

Future work includes the nested filter-builder UI, scheduled exports, chart
drill-down, and query-plan tuning with production-scale SQL Server data.

