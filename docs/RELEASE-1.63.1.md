# SupportHub 1.63.1 — SQL Server Permission-Migration Fix

Status: **CORRECTIVE RELEASE CANDIDATE**

## Correction

- Fixes migrations `0184_pre_ticket_convert_perm` and `0185_ticket_delete_approval` for SQL Server schemas where `profile_permissions.scope_type` is non-nullable and has no database default.
- Both migrations now explicitly insert `scope_type='NONE'` for new profile-permission assignments.
- Adds a release regression guard requiring the scope value in both migrations.
- Retains all Support Assistant functionality delivered in `1.63.0`.

## Database

- Required Alembic head remains `0186_support_assistant_prefs`.
- A failed transactional SQL Server upgrade at `0184` should remain stamped at `0183_pre_ticket_result_unique`; deploy this corrective package and rerun `migrate`.
- The migrations are retry-safe: existing permission and profile-permission rows are checked before insertion.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy `1.63.1` over the failed `1.63.0` application files while preserving production configuration values.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Confirm Alembic reaches `0186_support_assistant_prefs`.
5. Run the Pre-Ticket and Support Assistant smoke tests.

Final artifact size and checksum are recorded after the self-contained build completes.
