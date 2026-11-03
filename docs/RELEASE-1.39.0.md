# SupportHub 1.39.0

Release date: 2026-08-25

This release completes the Smart Scheduler V2 usability and correctness audit.

Status: self-contained Windows x64 package generated and verified.

## Highlights

- Adds Quick Shift creation using Date → Shift Type → Engineers → Create.
- Adds searchable multi-engineer Manual assignment, confirmed Suggested assignment, and server-controlled Auto Balance.
- Adds canonical Shift Type start time, end time, and required headcount defaults.
- Shows inherited shift time, candidate availability, workload hints, and live coverage feedback before creation.
- Enforces active Shift participation even when Shift Type eligibility enforcement is disabled.
- Correctly handles cross-midnight defaults while preserving all historical Shift timestamps.
- Simplifies the Shift Workload view and places generator, Copy Week, Bulk Delete, and Paint Mode under advanced planner tools.
- Uses Agenda by default and a full-screen Quick Shift dialog on small screens.

## Database

Required database revision: `0130_shift_type_defaults`.

The additive migration from 1.38.0 adds default start time, default end time, and default required headcount to Shift Types. It does not update the actual timestamps of existing Shifts.

## Validation

- Backend Ruff and strict MyPy passed over 141 source files.
- Full backend suite: 280 tests passed.
- Frontend ESLint, TypeScript, and 12 Vitest tests passed.
- Frontend production build passed with the existing non-blocking large-chunk advisory.
- Clean SQLite migration through `0130_shift_type_defaults` passed.

## Deployment

Back up the production database and stop the IIS application pool. From the extracted release root run:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm the database revision is `0130_shift_type_defaults`, switch IIS to the immutable `1.39.0` directory, start the pool, and run the packaged smoke-test checklist.

## Artifact

- ZIP: `releases/SupportHub-1.39.0.zip`
- Size: 42,240,846 bytes
- Entries: 1,665
- SHA-256: `8F8E3BFB4F1CE82F5314B3DE8B860E428CDF3D74A423D8A5094D429A19092D90`
