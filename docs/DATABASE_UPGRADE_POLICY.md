# Database upgrade policy

Alembic is the authoritative SupportHub schema history. The expected revision for the current codebase is `0253_change_deployment_closure`.

When adding a new migration, update `EXPECTED_DATABASE_REVISION` in `app/db/compatibility.py` in the same change so production compatibility checks recognize the new head.

## Supported upgrade sequence

1. Create and verify a SQL Server backup.
2. Stop the SupportHub IIS application pool.
3. Preserve the production `backend/web.config` and shared storage.
4. From the new release root, run:

   ```powershell
   .\backend\runtime\SupportHubBackend.exe migrate
   .\backend\runtime\SupportHubBackend.exe seed
   ```

5. Confirm `alembic_version.version_num` matches the revision declared in the release manifest (`0253_change_deployment_closure` for the current release candidate).
6. Start IIS and run the release smoke checks.

For a source installation, use `python -m alembic upgrade head` followed by `python -m app.modules.iam.seed`.

## Manual SQL repair scripts

Files named `SupportHub-*-Database-Upgrade.sql` are recovery aids for installations that were previously upgraded manually. They are idempotent but are not a replacement for Alembic and do not independently establish complete migration history.

Do not run both a manual repair script and Alembic blindly. If a manual script was used, compare the real schema with the Alembic revisions and reconcile `alembic_version` under DBA supervision before a later Alembic upgrade. Never change `alembic_version` merely to silence an error.

The seed command is intentionally executed only after migration succeeds because current seed queries may require columns introduced by recent migrations.
