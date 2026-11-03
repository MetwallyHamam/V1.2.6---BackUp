# SupportHub 1.52.4

## Purpose

Correct SQL Server storage of Arabic client names and other human-readable client text while retaining the historical-dashboard timeout correction from 1.52.3.

## Correction

- Changes the client ORM model to Unicode for `clients.name`, `clients.address`, and `clients.notes`.
- Adds revision `0149_client_unicode_text`, which explicitly converts those SQL Server columns to `NVARCHAR(200)`, `NVARCHAR(1000)`, and `NVARCHAR(MAX)` while safely rebuilding dependent non-constraint indexes.
- Adds API create/update/read regression coverage for Arabic client name, address, and notes.
- Adds a rollback-only real SQL Server Unicode verifier.

## Existing corrupted values

Values already stored as question marks cannot be reconstructed automatically because the original Arabic characters were lost during the earlier `VARCHAR` write. After deployment, re-enter the intended Arabic value. For the reported client 420, rename it to `عميل جديد`.

## Database and deployment

Required revision: `0149_client_unicode_text`. Back up SQL Server, deploy to a new immutable directory, run the packaged migration command, verify the manifest revision, edit any already-corrupted client values once, and smoke-test Arabic client create/edit/list behavior plus both historical dashboards before switching IIS.
