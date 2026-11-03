# Support Hub 1.37.2

Release date: 2026-08-24

This database compatibility hotfix corrects the omitted shift-pattern effective-date migration discovered after deploying 1.37.1.

## Fix

- Adds nullable `effective_from` and `effective_to` columns to `shift_patterns` through migration `0125_shift_pattern_dates`.
- Aligns the physical SQL Server schema, SQLAlchemy model, and production compatibility requirements.
- Preserves all existing shift patterns and scheduling data.

## Upgrade

After deploying the release, stop the IIS application pool and run:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Restart IIS afterward. The expected database revision is `0125_shift_pattern_dates`.
