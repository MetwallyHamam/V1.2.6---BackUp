# SupportHub 1.52.0

## Purpose

Complete the B-47 English/Arabic page migration and ship the validated dashboard scalability improvements accumulated after 1.51.1.

## Language enhancement

- Localizes every inventoried routed page and embedded administration/authentication surface.
- Completes multilingual master-data forms and localized selector fallback behavior.
- Adds application-wide RTL corrections, technical-value LTR isolation, language persistence coverage, and representative internal/portal Arabic tests.
- Preserves English as the normal interface; Arabic can remain administratively disabled until operational rollout.

## Dashboard and SLA performance

- Pushes Executive and Top Management filters, counts, breakdowns, trends, and agent/product totals into SQL.
- Uses SQL Server-safe 1,900-ID batches and caps inline evidence while preserving governed drilldowns.
- Persists completed resolution-SLA outcome snapshots and includes a cursor-safe historical backfill command.
- Measured full-range execution over 20,648 tickets is 2.954 seconds for Top Management and 4.703 seconds for Executive; a rollback-only one-million-row grouped-SQL benchmark completes in 0.178 seconds.

## Database

Required revision: `0148_sla_outcome_snapshots`. The migration additively stores completed resolution-SLA outcome evidence. Back up SQL Server before migration, then run `python -m scripts.backfill_sla_outcome_snapshots` once after upgrade.

## Deployment

Deploy to a new immutable directory, preserve protected environment configuration, back up SQL Server, run the packaged migration command, verify revision `0148_sla_outcome_snapshots`, run the historical SLA snapshot backfill, smoke-test English and Arabic/RTL pages plus both management dashboards, and then switch IIS to 1.52.0.
