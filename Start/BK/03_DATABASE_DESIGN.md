# SQL Server Database Design

## 1. Conventions

- Schema names by domain: `iam`, `crm`, `svc`, `tkt`, `kb`, `wf`, `ops`, `audit`, `integration`.
- Primary keys: `BIGINT IDENTITY` for high-volume entities; `INT IDENTITY` for small catalogs.
- Public IDs: UUID/uniqueidentifier for externally exposed objects when useful.
- Time: `DATETIME2(3)` in UTC.
- Boolean: `BIT`.
- Money: `DECIMAL(19,4)`; never `FLOAT` or `REAL`.
- Concurrency: `ROWVERSION`.
- Names: singular table names are acceptable if consistently applied.
- Every table has explicit primary key, foreign keys, and appropriate constraints.

## 2. Core Entity Groups

### Identity

- User
- Role
- Permission
- UserRole
- RolePermission
- Team
- TeamMember
- Skill
- UserSkill
- LoginSession/RefreshToken

### CRM

- Client
- ClientStatus
- Branch
- Contact
- ContactBranchAccess
- Product
- ProductModule
- ClientInstallation
- Environment
- Vendor

### Contracts and SLA

- Contract
- ContractCoverage
- Entitlement
- ServiceCatalogItem
- SlaPolicy
- SlaTarget
- BusinessCalendar
- BusinessCalendarDay
- Holiday
- ContractContact
- ContractDocument

### Ticketing

- Ticket
- TicketType
- TicketStatus
- TicketPriority
- Impact
- Urgency
- Category
- Subcategory
- TicketComment
- TicketAttachment
- TicketAssignmentHistory
- TicketStatusHistory
- TicketLink
- TicketWatcher
- TicketTask
- TicketTag
- TicketCustomFieldValue
- TicketSlaClock
- TicketSlaEvent
- Approval

### Notifications

- Notification
- NotificationDelivery
- NotificationPreference
- EventOutbox
- EmailTemplate

### Workforce

- ShiftType
- Shift
- OnCallRotation
- LeaveRequest
- ShiftSwapRequest
- Handover

### Knowledge

- Article
- ArticleVersion
- ArticleCategory
- ArticleTag
- ArticleFeedback
- ArticleTicketLink

### Imports

- ImportJob
- ImportFile
- ImportRow
- ImportError
- ImportCommitBatch

### Audit

- AuditEvent
- SecurityEvent

## 3. Client Isolation

Every client-owned table should contain `ClientId`, directly or through a guaranteed join path. APIs must enforce object-level authorization.

Defense in depth options:

1. Application policy filters on every query.
2. SQL Server Row-Level Security for selected client-facing tables.
3. Separate database is not initially recommended unless contractual isolation requires it.

Do not rely on hiding UI buttons for access control.

## 4. Ticket Table Key Fields

- TicketId
- PublicId
- TicketNumber
- TicketTypeId
- ClientId
- BranchId
- RequesterContactId
- CreatedByUserId
- SourceChannelId
- ServiceCatalogItemId
- ProductId
- ProductModuleId
- EnvironmentId
- CategoryId
- SubcategoryId
- ImpactId
- UrgencyId
- PriorityId
- StatusId
- AssignedTeamId
- AssignedUserId
- ContractId
- Subject
- Description
- FirstOccurredAtUtc
- PatientSafetyFlag
- SecurityIncidentFlag
- FirstResponseDueAtUtc
- ResolutionDueAtUtc
- FirstRespondedAtUtc
- ResolvedAtUtc
- ClosedAtUtc
- LastActivityAtUtc
- ReopenCount
- CreatedAtUtc
- UpdatedAtUtc
- RowVersion

Use computed/reporting columns carefully. Business calculations such as SLA deadline should be persisted with calculation history, not recalculated differently by every report.

## 5. Auditing

Business audit must answer:

- Who performed the action?
- When?
- From which IP/device/session?
- Through which source: UI, portal, API, import, automation?
- Which record?
- What action?
- Old and new values for approved fields?
- Why, when a reason is required?
- Correlation ID?

Do not write passwords, tokens, secrets, or full sensitive clinical data into audit payloads.

## 6. Index Strategy

High-value indexes include:

- TicketNumber unique
- ClientId + StatusId + UpdatedAtUtc
- AssignedTeamId + StatusId + PriorityId + ResolutionDueAtUtc
- AssignedUserId + StatusId + UpdatedAtUtc
- StatusId + ResolutionDueAtUtc
- ClientId + BranchId + CreatedAtUtc
- Contract end/status/renewal dates
- Notification recipient + read state + created date
- Outbox status + next attempt date
- Shift employee/team + start/end

Use included columns based on actual query plans. Do not create every possible composite index.

## 7. Search

Use SQL Server Full-Text Search for:

- Knowledge article title, summary, and body
- Optionally ticket subject and description

Keep exact identifiers such as ticket number, accession, and server names supported by normal indexed search fields.

## 8. Data Retention

Define retention by data type:

- Closed tickets
- Attachments
- Notifications
- Audit events
- Security events
- Import staging rows
- Generated reports
- WebSocket connection logs

Retention jobs must be reviewed and reversible where legal or contractual holds apply.

## 9. Migration Rules

- Alembic migration for every schema change.
- No automatic destructive migration in production.
- Backward-compatible expand/migrate/contract approach for major changes.
- Migration scripts are tested against a production-like database copy.
- Include rollback or documented forward-fix procedure.
- Seed only stable catalogs; do not hard-code client-specific production data.
