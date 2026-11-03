# SupportHub 1.52.2

## Purpose

Provide the corrected deployable self-contained Windows x64 package for the completed B-47 language migration and dashboard/SLA performance improvements.

## Correction from 1.52.1

- Makes revision `0148_sla_outcome_snapshots` safe on both populated SQL Server upgrades and clean SQLite/package migration rehearsals.
- Keeps the frozen historical `ticket_sla_clocks` schema from prematurely inheriting revision 0148 columns.
- Retains column/index existence guards so interrupted or historically generated schemas can migrate safely.

## Included changes

- Includes every localized routed and embedded page, multilingual master-data form, RTL correction, technical-value isolation rule, and language persistence/regression test from B-47.
- Includes Executive and Top Management SQL aggregation/filter pushdown, evidence caps, SQL Server-safe batching, and persisted completed resolution-SLA outcomes.
- Bundles the Windows backend runtime; the deployment server does not require a separate Python installation.

## Database and deployment

Required revision: `0148_sla_outcome_snapshots`. Deploy to a new immutable directory, preserve protected environment configuration, back up SQL Server, migrate and seed, verify the manifest revision, run `python -m scripts.backfill_sla_outcome_snapshots` once from an approved administrative source backend environment, smoke-test English and Arabic/RTL pages and both management dashboards, and switch IIS only after all checks pass.
