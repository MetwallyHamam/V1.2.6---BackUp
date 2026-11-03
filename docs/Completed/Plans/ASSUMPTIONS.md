# Phase 0–1 Assumptions

1. The planning pack in `Start/` is the approved product charter for this increment.
2. Phase 0–1 means the foundation plus local authentication, users, profiles, permissions, scopes, refresh-token rotation, and audit. Later business domains remain placeholders.
3. Python 3.12+ is supported. SQL Server 2022 with Microsoft ODBC Driver 18 is the production database.
4. Local authentication uses bearer access and refresh tokens. The frontend keeps access tokens in memory; production cookie/CSRF hardening remains an explicit deployment decision.
5. `ADMINISTRATOR` is the stable profile code and “System Administrator” is its display name.
6. The database health endpoint returns a safe unavailable response when SQL Server is not configured or reachable.
7. Client and branch IDs are scoped foundations only; CRM records are intentionally not implemented in this phase.
8. Redis and background workers are deferred until their business consumers are implemented.
9. Development administrator credentials are supplied only by environment variables.

