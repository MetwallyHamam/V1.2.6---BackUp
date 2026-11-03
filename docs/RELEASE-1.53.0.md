# SupportHub 1.53.0 — Test/UAT Release

## Purpose

Deliver the governed dashboard-template, assignment, personalization, scalability, and financial-dashboard enhancements for controlled test and user-acceptance validation.

## Dashboard enhancements

- Adds versioned dashboard templates with system, profile, department, profile-plus-department, and exceptional-user assignment precedence.
- Adds permission-protected dashboard administration, effective-user preview, affected-user counts, safe widget configuration, and reset-to-assigned behavior.
- Keeps personal layouts pinned to their assigned template version and displays a notification when a newer assigned template is available.
- Adds centralized ticket-scope filtering, typed drilldowns, scope rejection, query/response budgets, SLA outcome snapshots, and large-data benchmark tooling.
- Adds the least-privilege Financial Management profile and governed currency-safe financial analytics.
- Adds dedicated contract-value, contract-expiry, discount, and additional-adjustment widgets plus direct contract filtering.

## Database and deployment

Required revision: `0155_financial_widgets`.

Back up SQL Server before deployment, deploy to a new immutable directory, run the packaged migration command, and complete the supplied smoke test. This package is intended for test/UAT. Production approval still requires specialist-role, Arabic/RTL, business-formula, scope-policy, and rollback UAT recorded in the remaining backlog.

