# SupportHub 1.38.0

Release date: 2026-08-25

This release introduces Smart Scheduling, Coverage, and Operations planning as a unified, permission-aware workspace.

Status: ready; self-contained Windows x64 package generated and verified.

## Highlights

- Adds Overview, Planner, Workload, and Setup areas for scheduling operations.
- Adds independent Shift and Operation participation controls while preserving historical assignments.
- Adds Shift Type employee eligibility with backend enforcement across manual and generated workflows.
- Adds dated coverage slots, required headcount, coverage summaries, and a real Coverage Gap Queue.
- Adds real-date recurring Shift generation with Preview/Apply, stale-preview protection, workload-aware Auto Balance, Fixed assignment, Keep Existing, and cyclic Rotations.
- Adds reusable multi-row Schedule Recipes, Paint Mode, and multi-target Copy Week.
- Adds recurring Internal Operation generation with preview/apply and durable batch evidence.
- Adds exact-client Outdoor Visit entitlement preview and remaining allowance in the Visit planner and Overview.
- Adds responsive scheduling navigation and mobile quick actions.

## Database

Required database revision: `0129_operation_generation`.

The additive migration chain from 1.37.2 is:

1. `0126_smart_schedule_foundation`
2. `0127_shift_coverage_slots`
3. `0128_schedule_recipes_rotations`
4. `0129_operation_generation`

The migrations add participation and eligibility fields, coverage requirements, rotations, recipes, generation batches, and generated Shift/Operation batch links. Existing scheduling records are preserved. Participation defaults to enabled and Shift Type eligibility enforcement defaults to disabled for backward compatibility.

## Validation

- Backend Ruff and MyPy passed.
- Full backend suite: 277 tests passed.
- Frontend ESLint, TypeScript, and 11 Vitest tests passed.
- Frontend production build passed with the existing non-blocking vendor-chunk advisory.
- Clean SQLite migration from base through `0129_operation_generation` passed.

See `docs/SHIFT_AND_OPERATION_SCHEDULING_BEHAVIOR.md` in the source repository for the complete behavior, API, migration, limitation, and manual-test reference.

## Deployment

Back up the production database and stop the IIS application pool. From the extracted release root run:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm the database revision is `0129_operation_generation`, switch the IIS frontend and backend paths to the immutable `1.38.0` directory, start the pool, and run the packaged smoke-test checklist.

## Artifact

- ZIP: `releases/SupportHub-1.38.0.zip`
- Size: 42,228,210 bytes
- SHA-256: `57A88608CAF4C43395D6D1FACDE444D6B138D007F730318C227BC63599EBDF05`
