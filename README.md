# Millensys Support Hub

Current implementation of the Millensys Support Department’s modular-monolith web platform. It provides identity, CRM, ticketing, client portal, contracts/SLA, escalations, notifications, workforce scheduling, knowledge, imports, live dashboards, saved views, and controlled exports.

## Prerequisites

- Python 3.12+
- Node.js 22 LTS and npm
- SQL Server 2022+
- Microsoft ODBC Driver 18 for SQL Server

## SQL Server configuration

Copy `.env.example` to `backend/.env`, generate a random `SECRET_KEY`, and replace `DATABASE_URL`. ODBC Driver 18 encryption is enabled in the example. Use a dedicated least-privileged application login and do not commit `.env`.

For IIS deployment, [backend/web.config](backend/web.config) is the source template
for the backend configuration, including the SQL Server connection. Release builds
package it as `backend/web_<version>.config` so extracting a release cannot overwrite
the working `backend/web.config`. Copy and merge the versioned template deliberately,
replace every `REPLACE_*` placeholder, confirm the runtime path, and restrict the
active file ACL to IIS administrators and the application-pool identity. The server
requires IIS HttpPlatformHandler and Microsoft ODBC Driver 18.

Example:

```text
mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m app.modules.iam.seed
python -m uvicorn app.main:app --reload
```

The seed command is idempotent. It creates the permission catalog, nine system profiles, required master data, and a development administrator only when all three `DEV_ADMIN_*` environment variables are present. Credentials are never hardcoded. Always migrate before running seed.

API documentation is at `http://localhost:8000/docs`. Health endpoints are:

- `GET /api/v1/health`
- `GET /api/v1/health/database`

Backend verification:

```powershell
python -m pytest
python -m ruff check app
python -m mypy app
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
npm test
npm run build
```

If the Windows workspace path contains `&` and npm’s generated shims fail, invoke the tools directly:

```powershell
node .\node_modules\vitest\vitest.mjs run
node .\node_modules\typescript\bin\tsc -b
node .\node_modules\vite\bin\vite.js build
```

## Authentication and authorization

Access tokens are short-lived JWTs. Refresh tokens are random, stored only as SHA-256 hashes, rotated on every use, and reuse revokes the whole token family. Passwords use Argon2id. Login tracks failures, lockout, inactive status, and authentication events.

Authenticated browser sessions use a 15-minute access token and a configurable 30-day sliding inactivity window (`REFRESH_TOKEN_DAYS`). Every successful login or refresh renews that 30-day window; therefore, a user who regularly uses the system remains signed in. The UI warns five minutes before inactivity expiry. Temporary network/server failures retain credentials and retry; only authoritative expiry, revocation, inactive-account, invalid-session, explicit logout, or browser-storage loss ends the session. Refresh coordination uses a browser lock and shared refresh-token storage so concurrent requests and tabs cannot rotate the same token family independently.

Authorization checks permission codes—never profile names. Active, unexpired profile grants are collected, active allow overrides are added, and active deny overrides are applied last. Client and branch scopes are calculated separately. Default is deny.

## Migrations

Create revisions with `python -m alembic revision --autogenerate -m "description"` and apply them with `python -m alembic upgrade head`. Production deployments must back up first and review generated SQL with `python -m alembic upgrade head --sql`.

Backup and guarded restore commands are documented in [docs/BACKUP_AND_RESTORE.md](docs/BACKUP_AND_RESTORE.md). Production startup now rejects the development secret, SQLite, and development administrator settings.

Secure ticket upload/download behavior and production storage requirements are documented in [docs/TICKET_ATTACHMENTS.md](docs/TICKET_ATTACHMENTS.md).

## Scope and known limitations

- SQL Server is the production database. The fast regression suite uses SQLite, while CI also provisions SQL Server 2022 with ODBC Driver 18 and MARS disabled to apply all migrations and exercise database-sensitive exports. Full migration-chain validation runs on SQL Server because several revisions add constraints with `ALTER TABLE` operations that SQLite cannot reproduce.
- Microsoft Entra ID, Redis, workers, attachment malware-scanner integration, SLA pause/recalculation history, escalation jobs, knowledge search, announcements, and later business modules remain deferred. Notification WebSockets work on a single application instance; Redis fan-out is still required before scaling to multiple instances.
- Frontend access tokens are currently memory-only. A production cookie/CSRF strategy must be finalized with the deployment topology.
- Frontend routes are lazy-loaded so each major screen is delivered as a separate chunk.
- Monitoring systems can create idempotent incidents through the authenticated webhook documented in `docs/INTEGRATIONS.md`.
- The Phase 14 security baseline and residual production risks are documented in `docs/THREAT_MODEL.md`.
- Dependency audit currently reports transitive development-tool findings; review and upgrade them before production release.

See [release and recovery log](RELEASE_STEPS.md), [assumptions](docs/ASSUMPTIONS.md), [checklist](docs/IMPLEMENTATION_CHECKLIST.md), and the original planning pack in `Start/`.
