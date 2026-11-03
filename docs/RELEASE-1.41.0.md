# SupportHub 1.41.0

Release date: 2026-08-25

This release makes calendar coverage gaps directly assignable from Coverage Details.

Status: self-contained Windows x64 package generated and verified.

## Highlights

- Adds **Assign Engineers** to unassigned and understaffed coverage-slot cards.
- Displays the exact number of open positions.
- Opens Quick Shift with the coverage date, Shift Type, and team prefilled.
- Retains Date From / Date To, Manual, Suggested, and Auto Balance assignment modes.
- Retains authoritative participation, eligibility, workload, and conflict validation.
- Hides the action when coverage is complete or the user cannot create Shifts.

## Database

Required revision: `0130_shift_type_defaults`. No migration is required from 1.40.0.

## Deployment

Back up the production database and stop the IIS application pool. From the extracted release root run:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm revision `0130_shift_type_defaults`, switch IIS to the immutable `1.41.0` directory, restart the pool, and complete the packaged smoke test.

## Artifact

- ZIP: `releases/SupportHub-1.41.0.zip`
- Size: 42,244,945 bytes
- Entries: 1,665
- SHA-256: `C9D02E4DFEA8F8FA0E8BA3BB4FFE266B2056C9C1425628DD5DD89BC62AA11F54`
