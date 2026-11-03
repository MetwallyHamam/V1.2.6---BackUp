# SupportHub 1.31.5

Production capacity and 502-resilience patch for IIS deployments serving concurrent users.

## Changes

- Runs four independent backend processes behind IIS HttpPlatformHandler instead of one.
- Caps each process at five persistent and five overflow SQL connections, with a 15-second acquisition timeout and 30-minute connection recycling.
- Converts database-pool exhaustion into a structured retryable HTTP 503 response instead of an unhandled backend failure.
- Bounds each process to two simultaneous Argon2 password checks, preventing a login burst from exhausting server memory while queued logins wait briefly.
- Uses a SQL Server application lock to guarantee only one escalation/email/Outlook scheduler cycle runs across all backend processes.
- Adds IIS child-process startup retries and configuration regression coverage.
- Adds an operator-controlled concurrent-login test script that reads its password from an environment variable.

No database migration is required. Database compatibility remains `0120_internal_ops_lifecycle`.

## Deployment requirements

- Confirm SQL Server can accept the configured maximum of 40 application connections before deployment.
- Preserve the production secrets while adopting the new `web.config` process and pool settings.
- Do not overwrite the packaged `web.config` with the previous release's complete file. Transfer the protected environment values into the new template so the four-process and pool settings remain active.
- Set the IIS application pool to No Managed Code, `AlwaysRunning`, idle timeout `0`, and enable preload for the backend application.
- After switching releases, verify `/api/v1/health`, `/api/v1/health/database`, normal login, scheduler status, and the IIS/Uvicorn logs.
- Use the packaged login-load script only with an approved dedicated test account and maintenance/test window.
