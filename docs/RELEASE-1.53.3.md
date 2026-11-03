# SupportHub 1.53.3 — Customer Success SQL Scale Hotfix

## Purpose

Correct the Customer Success analytics HTTP 500 exposed after deploying the management-dashboard correction in 1.53.2.

## Correction

- Replaces the survey query's expanded ticket-ID `IN (...)` predicate with a joined, date-scoped ticket query.
- Replaces complaint-reopen ID expansion with a joined complaint-scope query and an in-memory intersection over the already authorized result set.
- Prevents SQL Server's 2,100-parameter limit from failing large Customer Success periods; the production log contained 8,534 expanded ticket parameters.
- Adds a 2,101-ticket regression that rejects any non-batch statement exceeding the governed parameter ceiling.
- Retains the management-dashboard product aggregation correction from 1.53.2.

## Database and deployment

Database revision remains `0155_financial_widgets`; no new migration is required. Deploy to a new immutable directory, switch IIS to the new package, restart the application pool, and retry both Top Management and Customer Success over the full historical range.

