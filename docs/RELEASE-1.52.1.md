# SupportHub 1.52.1

## Purpose

Provide the deployable self-contained Windows x64 package for the completed B-47 language migration and dashboard/SLA performance improvements delivered in source release 1.52.0.

## Included changes

- Includes every localized routed and embedded page, multilingual master-data form, RTL correction, technical-value isolation rule, and language persistence/regression test from B-47.
- Includes Executive and Top Management SQL aggregation/filter pushdown, evidence caps, SQL Server-safe batching, and persisted completed resolution-SLA outcomes.
- Bundles the Windows backend runtime; the deployment server does not require a separate Python installation.

## Database

Required revision: `0148_sla_outcome_snapshots`. Back up SQL Server, run the packaged migration command, verify the manifest revision, then run `python -m scripts.backfill_sla_outcome_snapshots` once from an approved administrative source backend environment.

## Deployment

Deploy to a new immutable directory, preserve protected environment configuration, back up SQL Server, migrate and seed, verify revision `0148_sla_outcome_snapshots`, backfill historical SLA snapshots, smoke-test English and Arabic/RTL pages and both management dashboards, and switch IIS only after the checks pass.
