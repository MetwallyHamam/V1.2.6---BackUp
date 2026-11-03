# Wave 6 — Bulk Coverage, Imports, and Visit Completion Execution Plan

Status: DONE — release checkpoint verified 2026-08-20

## Objective

Safely operate coverage at scale and complete visits with engineer, outcome, document, and entitlement evidence.

## Prerequisites

- Wave 5 is complete.
- Import schemas, completion states, required documents, sign-off, correction, and entitlement-consumption rules are approved.

## Workstreams

1. Add bulk coverage selection with explicit inclusions/exclusions and effective dates.
2. Add import templates, validation, preview, apply, error export, and resumable/idempotent execution.
3. Build visit start/complete/cancel/reopen workflows with assigned and participating engineers.
4. Capture structured outcomes, actual times, notes, customer acknowledgement, and required documents.
5. Post entitlement consumption exactly once and use compensating entries for authorized reversals.
6. Add document security, retention metadata, malware/content validation, and audit trails.

## Data and API

- Persist import batches, row results, source hashes, and idempotency keys.
- Never partially apply a row; define transaction boundaries for each batch operation.
- Version completion evidence and preserve prior documents/decisions on correction.
- Validate file type, size, access scope, and storage failure behavior.

## Verification

- Test duplicate imports, partial failures, retries, invalid references, date conflicts, and large batches.
- Test completion/reopen races and exact-once entitlement posting.
- Test document authorization, upload failures, replacement, retention, and download audit.
- Reconcile visit states, engineer participation, and ledger entries.

## Exit criteria

- Bulk operations always provide preview, attributable results, and safe retry.
- Completed visits have sufficient structured and documentary evidence.
- Entitlement cannot be consumed twice.
- Security, reconciliation, performance, recovery, and automated tests pass.

## Next wave

Wave 7 — Client, Department, Shift, and Visit Reports.

## Required completion checkpoint

When accepted, record the standard `CODEX STOP POINT` and stop before Wave 7 until explicitly continued.

## Implementation and verification record

- Extended the governed coverage import template with effective dates, explicit exact-client inclusions/exclusions, preview validation, attributable row errors, CSV error export, and idempotent commit behavior.
- Added visit start, complete, cancel, and reopen transitions with optimistic completion versions, actual times, structured outcomes, customer acknowledgement, and immutable completion snapshots.
- Required validated documentary evidence before completion and added secured upload/download, content signature checks, streaming hashes, retention and scan metadata, supersession, and download auditing.
- Preserved exactly-once entitlement consumption and compensating reopen entries.
- Passed Ruff, MyPy (131 source files), 209 backend tests, frontend ESLint, four Vitest tests, TypeScript, production build, a clean SQLite migration, and clean/populated SQL Server rehearsals through `0103_visit_completion`.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 6 — Bulk Coverage, Imports, and Visit Completion/Documents
Last completed item: Passed full gates and clean/populated SQL Server revision 0103 rehearsals
Next planned item: Wave 7 — Client, Department, Shift, and Visit Reports
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0103_visit_completion
============================================================
