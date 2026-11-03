# IIS production and release process

## Production topology

- IIS application `/SupportHub`: React static files from `releases/<version>/frontend`.
- IIS child application `/SupportHub/backend`: FastAPI from `releases/<version>/backend` using HttpPlatformHandler.
- Shared attachment and backup folders live outside `releases`; never package or delete them during upgrades.
- SQL Server uses a dedicated least-privileged application login.
- HTTPS is mandatory. HTTP redirects to HTTPS.

Required IIS components are URL Rewrite and HttpPlatformHandler. The application pool uses **No Managed Code**, a dedicated service identity, `AlwaysRunning`, and `StartMode=AlwaysRunning`.

## First publication

1. Install a valid TLS certificate for the production hostname.
2. Build a versioned package:

   ```powershell
   .\scripts\Build-SupportHubRelease.ps1 -Version 1.0.0
   ```

3. Copy the release to `D:\Sites\MillensysSupportHub\releases\1.0.0`.
4. Create `D:\Sites\MillensysSupportHub\shared\attachments` and `shared\backups` and grant Modify only to the application-pool identity.
5. In the release backend, create `.venv` and install the locked project dependencies. Copy the packaged `web_<version>.config` template to `web.config`, then configure it with production secrets, the public origin/host, absolute shared storage paths, and `APP_VERSION`. Never rename or copy the template over an existing working `web.config` without first preserving and merging its protected values.
6. Back up and verify SQL Server, then run `backend\runtime\SupportHubBackend.exe migrate` followed by `backend\runtime\SupportHubBackend.exe seed` from the release root. Source deployments use Alembic followed by seed. Never run seed before migration.
7. Point `/SupportHub` and `/SupportHub/backend` to the release directories, bind the valid certificate, redirect HTTP to HTTPS, and start the pool.
8. Verify `/SupportHub/backend/api/v1/health`, `/SupportHub/backend/api/v1/health/database`, login, ticket creation, upload/download, WebSockets, export, and portal access.

Never place production secrets in the release ZIP or source repository. Restrict the deployed `web.config` ACL to administrators and the pool identity.

## Every new release

1. Assign a semantic version and record changes and database compatibility.
2. Run lint, tests, TypeScript compilation, and the production build.
3. Build an immutable release package. Never edit or reuse an old version folder.
4. Copy it beside the current release and create its virtual environment. The package contains `backend/web_<version>.config`, not an active backend `web.config`, so extraction cannot overwrite the working configuration. For a new versioned directory, copy the template to `backend/web.config`, then transfer only the protected production environment values from the current configuration; do not replace the template wholesale because it may contain required process, capacity, or security settings. Confirm `APP_VERSION` matches the release.
5. Announce a maintenance window when a migration is not backward-compatible.
6. Create and verify a database backup.
7. Stop the IIS application pool, run `backend\runtime\SupportHubBackend.exe migrate`, verify the revision declared by `release-manifest.json`, run `backend\runtime\SupportHubBackend.exe seed`, switch both IIS physical paths, then start the pool.
8. Run health checks and a short functional smoke test. Record release version, migration revision, operator, backup, start/end time, and result.
9. Retain the previous application release and verified backup according to the retention policy.

## Rollback

- If no incompatible database migration ran, stop the pool, switch both IIS paths back to the previous release, and restart.
- If an incompatible migration ran, stop the application and follow the approved database restore procedure. Do not blindly run Alembic downgrade in production.
- Attachment storage is shared and must not be rolled back or overwritten with application files.

## Versioning policy

- Patch (`1.0.1`): compatible bug fixes.
- Minor (`1.1.0`): backward-compatible features and additive migrations.
- Major (`2.0.0`): breaking workflows, APIs, or migrations.

Prefer expand-and-contract database changes: add compatible structures first, deploy code that supports both forms, migrate data, and remove old structures in a later release. This keeps rollback practical.

Alembic is authoritative. SQL scripts included in the release database folder are repair aids for previously incomplete manual upgrades and must only be used according to `database\README.md` under DBA supervision.
