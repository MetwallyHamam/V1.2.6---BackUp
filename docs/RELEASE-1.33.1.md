# SupportHub 1.33.1

Corrective release for the SQL Server migration in 1.33.0.

## Correction

- Replaces the SQL Server-reserved `current` table alias in migration `0122_operations_permissions` with the safe alias `assigned_permission`.
- Keeps the same additive, idempotent permission migration and database head.
- Adds regression coverage preventing the reserved alias from returning.
- Includes all Operations Workspace and Contract Financials enhancements from 1.33.0.

## Upgrade recovery

- If the 1.33.0 migration failed with `Incorrect syntax near the keyword 'current'`, deploy 1.33.1 and run `SupportHubBackend.exe migrate` again.
- The migration safely checks for existing permission rows, so retrying does not require manual cleanup.
- After migration succeeds, run `SupportHubBackend.exe seed` and restart the IIS application.

Database revision: `0122_operations_permissions`.
