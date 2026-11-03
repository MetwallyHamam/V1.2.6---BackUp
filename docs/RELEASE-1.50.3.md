# SupportHub 1.50.3

## Purpose

Correct dashboard failures after large historical ticket imports and establish bounded SQL Server query behavior for growing ticket volumes.

## Changes

- Filters general and executive dashboard ticket populations by the selected database date range before materializing records.
- Splits related ticket-ID reads into batches of at most 1,000, below SQL Server's 2,100-parameter ceiling.
- Applies bounded reads to SLA clocks, SLA intervals, assignment/status history, escalations, root causes, and satisfaction data.
- Adds creation, resolution, and assignment-history indexes for historical dashboard workloads.
- Adds a 2,101-ticket regression that rejects statements exceeding 2,000 bound parameters.

## Database

Required revision: `0145_ticket_scale`.

The upgrade adds indexes only and does not modify ticket data.

## Deployment

Deploy the release to a new immutable directory, preserve the protected environment configuration, run the database migration, switch IIS to 1.50.3, and restart the application pool once.
