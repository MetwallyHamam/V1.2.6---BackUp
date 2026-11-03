# Security and Privacy Best Practices

## 1. Security Baseline

Use OWASP ASVS as the verification baseline. Select an agreed assurance target and track requirements in the backlog.

## 2. Authentication

- Prefer Microsoft Entra ID OIDC for employees.
- Use Authorization Code flow with PKCE where applicable.
- Local client passwords use Argon2id or an approved modern password hasher.
- MFA for privileged accounts.
- Rate-limit authentication endpoints.
- Lock or throttle repeated failures.
- Password reset tokens are random, single-use, short-lived, and stored hashed.
- Revoke sessions after password/security changes.

## 3. Authorization

- Deny by default.
- Check authorization at API/service/query levels.
- Enforce object-level client and branch access.
- Use permission names such as `ticket.read.team`, `ticket.assign`, `contract.edit`.
- Log privileged and denied actions where useful.
- Test horizontal and vertical privilege escalation.

## 4. Session and Token Security

- Secure, HttpOnly, SameSite cookies where the architecture supports them.
- CSRF protection for cookie-authenticated writes.
- Short-lived access token and protected refresh-token rotation when token-based auth is used.
- Do not store long-lived secrets in browser local storage.
- WebSocket connections require authenticated authorization and revalidation.

## 5. Input and Output Security

- Validate every request with strict schemas.
- Parameterize database queries.
- Sanitize rich text.
- Encode untrusted output.
- Validate URLs and block server-side request forgery targets.
- Restrict file types and sizes.
- Prevent CSV/Excel formula injection on exports.
- Never trust imported Excel cells.

## 6. Sensitive Healthcare Data

- Minimize patient-identifiable data.
- Prefer reference identifiers over clinical content.
- Mask sensitive values by permission.
- Exclude sensitive values from logs, notifications, URLs, analytics, and email subjects.
- Define retention and deletion rules.
- Record access to sensitive fields where required.

## 7. Secrets

- No secrets in source control.
- Separate secrets by environment.
- Use a secret manager or protected environment injection.
- Rotate database, email, SMS, and integration credentials.
- Never expose backend secrets to frontend builds.

## 8. Transport and Storage

- HTTPS only.
- Modern TLS configuration.
- Encrypt database connections.
- Encrypt backups and attachment storage.
- Protect encryption keys separately.
- Use least-privileged SQL login.

## 9. Audit and Logging

Log:

- Authentication/security events
- Permission/role changes
- Client access changes
- Contract and SLA changes
- Ticket priority/status/assignment changes
- Public/internal comment creation
- Attachment upload/download/delete
- Imports and exports
- Administrative configuration changes
- Automation actions

Do not log credentials, tokens, or unrestricted request bodies.

## 10. Abuse Controls

- API rate limits
- Portal submission limits
- Attachment quotas
- Export limits and watermark/audit where appropriate
- Search query limits
- Notification flood protection
- Account anomaly detection

## 11. Secure Development Lifecycle

- Threat modeling for each major capability
- Peer review
- SAST
- Dependency scanning
- Secret scanning
- DAST in staging
- Security unit/integration tests
- Patch policy
- Security incident response process

## 12. Production Hardening Checklist

- Debug disabled
- API docs restricted or intentionally published
- Default accounts removed
- CORS allowlist
- Trusted hosts
- Security headers
- CSP
- Error pages do not reveal internals
- Backups tested
- Admin access protected
- Logs centralized and protected
- Dependency versions pinned and maintained
