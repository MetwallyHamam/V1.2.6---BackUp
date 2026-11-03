# SupportHub Development Session History

Last updated: 2026-08-24

## Purpose

Use this file to resume work after reopening VS Code. It records what was requested, what was implemented, the releases produced, the production issue discovered, and the exact current stopping point.

## Current stopping point

Release **1.37.2** has been built and fully verified locally. It has **not yet been confirmed as deployed successfully** to production.

The next action is to deploy `releases/SupportHub-1.37.2.zip`, preserve the production database configuration in `backend/web.config`, migrate the production database from `0124_template_effective_dates` to `0125_shift_pattern_dates`, seed, restart IIS, and verify database health.

Do not deploy releases 1.37.0 or 1.37.1. They are superseded by 1.37.2.

## Latest production diagnosis

Production URL:

`https://millensysonline.net/SupportHub/login`

Production was running application version `1.37.1`. Migration `0124_template_effective_dates` completed, but login remained blocked with:

> The SupportHub database is not compatible with this application release. Run the database migration before using the system.

The database health endpoint reported:

```json
{
  "status": "unavailable",
  "database": "reachable",
  "schema": "SCHEMA_INCOMPLETE",
  "revision": "0124_template_effective_dates"
}
```

SQL Server confirmed that `0124` correctly added these columns:

- `internal_operation_templates.effective_from`
- `internal_operation_templates.effective_to`
- `shift_roster_templates.effective_from`
- `shift_roster_templates.effective_to`

The actual missing columns were:

- `shift_patterns.effective_from`
- `shift_patterns.effective_to`

The SQLAlchemy model and compatibility requirements expected these columns, but migration `0124` did not create them. This mismatch caused `SCHEMA_INCOMPLETE`.

## Corrective release 1.37.2

Migration `0125_shift_pattern_dates` was added. It safely adds the two nullable columns to `shift_patterns`, preserving all existing rows.

Important files:

- `backend/alembic/versions/0125_shift_pattern_effective_dates.py`
- `backend/app/db/compatibility.py`
- `backend/app/tests/test_database_compatibility.py`
- `backend/app/tests/test_release_database_revision.py`
- `docs/RELEASE-1.37.2.md`
- `RELEASE_STEPS.md`

The revision identifier was intentionally shortened to `0125_shift_pattern_dates` because Alembic's default SQL Server version column accepts at most 32 characters.

### Release artifact

Path:

`releases/SupportHub-1.37.2.zip`

Size: `42,071,800` bytes

SHA-256:

`0FF88CD16F4809E1F1954C11FADDBA1F3ACD6DA7F8AA363B55A57ECBBD95A1C3`

Manifest database head: `0125_shift_pattern_dates (head)`

### Verification completed

- Clean database migration through `0125_shift_pattern_dates`: passed.
- Ruff: passed.
- Strict MyPy: passed for 136 source files.
- Backend tests: 263 passed.
- Frontend tests: 9 passed.
- ESLint: passed.
- TypeScript build: passed.
- Vite production build: passed.
- Standalone executable `--help` smoke test: passed.
- ZIP integrity: passed with 1,650 entries.
- Package hygiene: zero `.env`, `.venv`, `node_modules`, `__pycache__`, `.pyc`, or `.pyo` entries.

## Production deployment steps still required

1. Back up the SupportHub SQL Server database.
2. Stop the SupportHub IIS application pool.
3. Deploy release 1.37.2, preserving the production `backend/web.config` database connection and shared-storage settings.
4. From the deployed `D:\Support\Metwally\SupportHub\backend` directory, run:

```powershell
.\runtime\SupportHubBackend.exe migrate
.\runtime\SupportHubBackend.exe seed
```

5. Restart IIS:

```powershell
iisreset
```

6. Verify the live application:

```powershell
$base = 'https://' + 'millensysonline.net/SupportHub/backend/api/v1'
curl.exe -s "$base/health"
curl.exe -s "$base/health/database"
```

Expected database response:

```json
{
  "status": "ok",
  "database": "reachable",
  "schema": "compatible",
  "revision": "0125_shift_pattern_dates"
}
```

7. Log in and confirm the compatibility warning has disappeared.

## Other enhancements completed in this workstream

### Operations and scheduling

- Added persisted Date From/Date To fields to reusable shift-roster templates and internal-operation templates.
- Connected date ranges with week-number and weekday scheduling behavior.
- Added/retained Outdoor / Field Visit operation-type support.
- Enhanced the unified Operations Workspace and separated its permissions from the removed legacy Shift Planner navigation.

### Onboarding

- Added edit/delete capability for training materials, material templates, material categories, and checklist templates.
- Restored training-material Type, Content Name, and URL fields.
- Expanded checklist-template item editing layout.
- Added audited onboarding-user unassignment.
- Added horizontal and vertical professional department hierarchy layouts.
- Added profile-image display in hierarchy views.
- Added profile-image file selection/upload during user creation instead of URL-only input.

### Tickets

- Ticket list responses now include the authoritative `client_name`, preventing labels such as `Client #1` when the client is outside the first client-catalog page.
- Ticket fast actions now clear mutually exclusive quick-action state before applying the selected action.
- Moving away from **My queue** clears its `assigned_user_id` and `open_only` filters.
- The blue **Open tickets** indicator should no longer remain after selecting Today's tickets or another fast action.
- These ticket fixes were included in 1.37.1 and therefore are also included in 1.37.2.

### Release packaging

- Updated `scripts/Build-SupportHubRelease.ps1` to remove generated Python cache directories and bytecode from release packages.
- Corrected the stale database-compatibility test assertion when the migration head advanced.

## Earlier migration fixes retained

- Migration `0122_operations_permissions` was corrected for SQL Server because `current` was used as an alias and is a reserved keyword.
- Migration `0123_onboarding_programs` uses filtered unique indexes on SQL Server so multiple legacy `NULL` category/material/template codes do not fail the migration.

## Recommended first message next session

Use this prompt after reopening VS Code:

> Read `docs/SESSION-HISTORY.md` completely and continue from the current stopping point. First confirm whether release 1.37.2 was deployed and whether the live `/health/database` endpoint reports revision `0125_shift_pattern_dates` with schema `compatible`.

## Repository note

At the time this file was created, the workspace root was not detected as a Git repository. Do not assume Git history or rollback is available; preserve existing files and database backups carefully.
