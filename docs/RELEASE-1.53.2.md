# SupportHub 1.53.2 — Management Dashboard SQL Server Hotfix

## Purpose

Correct the Top Management analytics HTTP 500 observed on production SQL Server through the pyodbc driver.

## Correction

- Corrects the product-demand aggregation to group by `products.name` while applying the `Unspecified` fallback only to the selected label.
- Avoids SQL Server error 8120 caused when pyodbc assigns different parameters to the selected and grouped `COALESCE` expressions.
- Retains all dashboard, personalization, scalability, finance, and migration corrections from 1.53.1.

## Database and deployment

Database revision remains `0155_financial_widgets`; no new migration is required. Deploy to a new immutable directory, switch IIS to the new package, and retry Top Management with the full `2024-01-01` through `2026-09-01` range.

