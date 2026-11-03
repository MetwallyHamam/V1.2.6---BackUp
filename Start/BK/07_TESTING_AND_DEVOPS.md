# Testing, DevOps, Observability, and Operations

## 1. Test Pyramid

### Unit Tests

- Priority calculation
- Workflow transition validation
- SLA working-time arithmetic
- Escalation rule matching
- Permission policies
- Import validation
- Notification deduplication

### Integration Tests

- SQL Server repositories
- API endpoints
- Authentication and authorization
- Outbox and worker processing
- Attachment authorization
- WebSocket notification recovery
- Excel staging and commit

### End-to-End Tests

- Agent ticket lifecycle
- Client portal submission and response
- Cross-client isolation
- Contract/SLA selection
- Critical escalation
- Shift-aware assignment
- Knowledge publishing

## 2. Mandatory Security Tests

- IDOR/object-level authorization
- Role escalation
- SQL injection
- XSS and rich-text sanitation
- CSRF
- File upload bypass
- Path traversal
- Rate limiting
- Token/session revocation
- WebSocket authorization
- Export data leakage

## 3. Performance Tests

Test with production-like volumes:

- Ticket list with common filters
- Global search
- Dashboard queries
- Notification burst
- Concurrent client portal users
- Large Excel import
- Attachment upload/download
- SLA scheduler processing

Set measurable SLOs before testing.

## 4. CI Pipeline

1. Validate formatting/linting.
2. Type check.
3. Run backend unit tests.
4. Run frontend tests.
5. Build backend/frontend.
6. Run migration against disposable SQL Server test database.
7. Run integration tests.
8. Run security/dependency/secret scans.
9. Publish artifacts.

## 5. Deployment Pipeline

- Build immutable artifact/image
- Deploy to test
- Run smoke tests
- Deploy to UAT
- Approval gate
- Database migration backup/check
- Deploy production using rolling or blue/green process
- Run smoke tests
- Monitor error/SLA indicators
- Roll back application if required

## 6. Observability

### Logs

Structured JSON with:

- Timestamp
- Level
- Service/module
- Environment
- Correlation ID
- User/client ID where safe
- Ticket ID where relevant
- Event/action
- Duration
- Result/error code

### Metrics

- Request count, latency, and errors
- Database query duration/pool state
- Worker queue depth and failures
- WebSocket connections
- Notification success/failure
- SLA job lag
- Import duration/errors
- Authentication failures

### Traces

Trace HTTP request through database, outbox, worker, and external notification when possible.

## 7. Backup and Restore

- SQL Server full, differential, and log backups according to RPO
- Attachment storage backup/versioning
- Encryption keys/configuration backup
- Restore drill at least quarterly
- Document actual restore duration and gaps

## 8. Operational Runbooks

Create runbooks for:

- Application unavailable
- Database unavailable
- Redis unavailable
- Worker queue stuck
- Email/SMS provider failure
- WebSocket failure
- SLA scheduler lag
- Import failure
- Attachment malware alert
- Database restore
- Release rollback
- Compromised account

## 9. Release Criteria

A release cannot proceed with:

- Failed tests
- Unreviewed critical/high vulnerabilities
- Missing migration backup/rollback plan
- Broken monitoring
- Unapproved permission changes
- Unresolved data-loss risk
