# SupportHub 1.40.0

Release date: 2026-08-25

This release adds inclusive date-range creation to the Smart Scheduler Quick Shift workflow.

Status: self-contained Windows x64 package generated and verified.

## Highlights

- Replaces the single Quick Shift date with Date From and Date To.
- Supports inclusive ranges from 1 through 31 days.
- Shows the selected day count and daily coverage before creation.
- Manual and Suggested assignment only allow engineers available on every selected date.
- Auto Balance selects the best available engineers independently for each day.
- Creates one coverage slot per day and applies all Draft Shift creation in one transaction.
- Preserves the existing Shift Type defaults, cross-midnight handling, eligibility, conflict checks, and historical Shift timestamps.
- Continues accepting the legacy single-date Quick Shift API payload.

## Database

Required revision: `0130_shift_type_defaults`. No new database migration is required from 1.39.0.

## Deployment

Back up the production database and stop the IIS application pool. From the extracted release root run:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm revision `0130_shift_type_defaults`, switch IIS to the immutable `1.40.0` directory, restart the pool, and complete the packaged smoke test.

## Artifact

- ZIP: `releases/SupportHub-1.40.0.zip`
- Size: 42,244,712 bytes
- Entries: 1,665
- SHA-256: `AC060D390760E9D1A80DFCCF33502B6D77F220E0C3F1FB9AC7CCBD7198FFDBFC`
