# Security Threat Model Baseline

## Protected assets

- User credentials, refresh tokens, API keys, and integration secrets
- Client, contact, contract, ticket, SLA, knowledge, and workforce data
- Audit logs, external delivery records, and legacy-system mappings
- Availability and integrity of the support workflow

## Trust boundaries

1. Browser to frontend and API
2. API to SQL Server
3. API/worker to SMTP, SMS, Teams, monitoring, and email gateways
4. Administrator imports and application-to-application API clients
5. IIS/reverse proxy to the Uvicorn application

## Principal threats and controls

- Credential attacks: account lockout, strong password hashing, short access tokens,
  refresh-token rotation, and generic authentication errors.
- Login credentials necessarily exist inside the user's browser while a login request is
  submitted and are therefore visible to that user in browser developer tools. Production
  rejects plain HTTP so TLS protects those credentials in transit; client-side hashing or
  encoding is not used because it would only create a replayable password equivalent.
- Broken authorization: permission dependencies, client/branch scopes, portal isolation,
  and integration client scoping.
- Replay and duplicate delivery: stable external event IDs, unique delivery records, and
  per-channel terminal states.
- Secret disclosure: API keys shown once and stored only as hashes; deployment secrets
  remain configurable through environment variables.
- Injection and unsafe exports: ORM-bound queries, Pydantic validation, and CSV formula
  neutralization.
- Host-header and browser attacks: trusted hosts, explicit CORS origins, CSP,
  frame denial, MIME sniffing prevention, and restrictive referrer/permissions policy.
- Resource exhaustion: IIS and application request-size limits, pagination, bounded
  imports, bounded outbox batches, retries, and dead-letter states.
- Audit evasion: validated correlation IDs plus authentication, authorization,
  integration, import, and credential lifecycle records.

## Residual work before production

- Replace all placeholder secrets and restrict `web.config` ACLs.
- Terminate TLS with a trusted certificate and verify HSTS at the public endpoint.
- Run dependency, SAST, secret, and container scans in CI.
- Conduct tenant-specific Entra ID/LDAP validation when provider details are available.
- Run authorization abuse cases, load tests, backup restoration, and disaster recovery
  exercises in the target infrastructure.
- Confirm SMTP, SMS, and Teams provider allowlists, rotation, monitoring, and retention.
