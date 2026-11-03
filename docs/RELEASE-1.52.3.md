# SupportHub 1.52.3

## Purpose

Correct historical Executive and Top Management dashboard requests that the browser cancelled after 15 seconds before the backend could return 2024–present data.

## Correction

- Gives only `/dashboards/summary` and `/management-dashboards/analytics` a two-minute analytical request window.
- Keeps the normal API and authentication timeout at 15 seconds.
- Preserves dashboard formulas, filters, drilldowns, SQL aggregation, and B-47 language behavior.
- Adds a regression test that protects both the ordinary and analytical timeout policies.

## Evidence

Against the attached SQL Server copy with 20,648 tickets from 2024-09-09 through 2026-08-30, a cold full-range run took 12.259 seconds Top Management and 8.530 seconds Executive. A warm run took 3.429 and 3.689 seconds. The former leaves insufficient margin beneath a 15-second browser cutoff for the larger 30K production database.

## Database and deployment

Database revision remains `0148_sla_outcome_snapshots`; no new migration is added after 1.52.2. Deploy to a new immutable directory, preserve protected configuration, verify the manifest/database revision, and smoke-test both dashboards over the full 2024–present range before switching IIS.
