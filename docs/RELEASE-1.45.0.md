# SupportHub 1.45.0

Release date: 2026-08-26

Status: **superseded — do not deploy**. SQL Server rejected an unquoted reserved `site_settings.key` identifier in migration `0136`. Use corrected release `1.45.1`.

## Highlights

- Adds the dedicated complaint-management workflow with scoped ownership, lifecycle rules, audit history, secure client tracking, feedback, closure confirmation, and explicit linked-ticket reopening.
- Reduces public tracking traffic for closed tickets while retaining automatic reopen detection and immediate focus/reconnect refresh.
- Adds a permission-controlled Customer Success workspace for satisfaction and complaint outcomes, privacy-safe evidence, matching CSV exports, and explainable versioned client-risk inputs.
- Includes SLA-warning recipient configuration, notification-rule lifecycle administration, and accessible ticket fast-action menus completed after `1.44.0`.

## Database

Required revision: `0138_customer_success`.

Migrations `0135` through `0138` add notification-rule archival, complaint management, closed-ticket polling policy, and Customer Success permissions. Back up the production database and rehearse the upgrade before changing the IIS application directory.

## Deployment

Stop the IIS application pool, preserve protected production environment values in `backend\web.config`, extract the immutable release, then run:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm database revision `0138_customer_success`, review new complaint and Customer Success permissions, validate notification settings, switch IIS to the `1.45.0` directory, restart the pool, and complete `SMOKE-TEST.md`.

## Artifact

- Package: `releases/SupportHub-1.45.0.zip`
- Size: 42,368,448 bytes
- Entries: 1,692
- SHA-256: `90F854E864D89359E6207366B42F0A977EE98D06EA88CDA2D4C5B53470CCA52B`
- Verification: Ruff, strict MyPy across 148 source files, all 292 backend tests, ESLint, all 14 frontend tests, TypeScript, production build, clean migration through `0138_customer_success`, standalone runtime help, manifest/database head, permission catalog, ZIP integrity, migration inclusion, and forbidden-file inspection passed.
