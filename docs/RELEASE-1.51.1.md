# SupportHub 1.51.1

## Purpose

Correct dashboard drill-through behavior so clickable cards and chart segments open the population represented by the displayed metric.

## Dashboard corrections

- Retains the selected date range and creation, resolution, or assignment date basis.
- Retains My Dashboard scope and the selected client, product, country, zone, location, department, team, and engineer filters.
- Opens status, priority, product, workload, and country chart segments with their category-specific filter.
- Makes Top Management use ticket-queue date parameters instead of ignored dashboard-only parameters.
- Adds database-level ticket filtering for dashboard geography, team, engineer, and assignment-period drilldowns while preserving accurate paging totals.
- Opens country-support data as a country-filtered client list rather than an unrelated ticket list.
- Bounds Created Today and Closed Today using both From and To dates.

## Database

Required revision: `0147_multilingual_master_data`. This corrective release adds no migration.

## Deployment

Deploy to a new immutable directory, preserve protected environment configuration, back up SQL Server, run the packaged migration command, verify revision `0147_multilingual_master_data`, smoke-test dashboard cards and chart segments, and then switch IIS to 1.51.1.
