# User Profiles, Roles, and Privileges

## 1. Objective

When an administrator creates a user, the system must allow selection of one or more default profiles. A profile is a managed bundle of permissions, default dashboard/view settings, assignment scope, escalation authority, and data-access scope.

Default profiles:

1. L1 Support Agent
2. L2 Support Engineer
3. L3 Specialist
4. Call Center Agent
5. Client Portal User
6. Support Manager
7. System Administrator

The authorization source of truth remains the permission catalog. Application code must never rely only on role names such as `L1` or `Manager`.

## 2. Authorization Model

Use RBAC with scoped permissions:

- **Permission:** smallest allowed action, such as `ticket.comment.internal`.
- **Profile/Role:** reusable bundle of permissions.
- **User profile assignment:** connects a user to one or more profiles.
- **Scope:** limits where the permission applies: own tickets, assigned team, selected clients, all clients, or portal client/branches.
- **Per-user override:** exceptional allow or deny, requiring reason, expiry, and audit.

Effective permission resolution:

1. User must be active.
2. Explicit active user deny overrides profile allow.
3. Explicit active user allow may add a permission only when policy permits overrides.
4. Otherwise, permission is allowed when any active assigned profile grants it.
5. The permission scope must match the target object.
6. Default result is deny.

Avoid unrestricted custom roles in the first release. Allow administrators to clone a system profile into a custom profile, edit it, and keep a complete audit history.

## 3. Default Profile Matrix

Legend: `Own` = created/requested by user; `Assigned` = assigned to user; `Team` = assigned team; `Client` = authorized portal client/branches; `All` = all internal data allowed by policy.

| Capability | Call Center | L1 | L2 | L3 | Manager | Administrator | Client Portal |
|---|---|---|---|---|---|---|---|
| Create internal ticket | Yes | Yes | Yes | Yes | Yes | Yes | No |
| Create portal ticket | No | No | No | No | Optional | Yes | Yes |
| View tickets | Team intake | Assigned/Team | Team | Team/All technical | All | All | Client |
| Edit classification | Basic | Basic | Yes | Yes | Yes | Yes | Limited on create |
| Add public comment | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Add internal note | No by default | Yes | Yes | Yes | Yes | Yes | No |
| Assign ticket | Queue only | Self/queue | Team | Team | All teams | All | No |
| Reassign across teams | No | No | Limited | Limited | Yes | Yes | No |
| Change priority | No | Up to P3 | Up to P2 | Up to P1 with reason | Yes | Yes | No |
| Resolve ticket | No | Standard L1 cases | Yes | Yes | Yes | Yes | Confirm/reopen only |
| Close ticket | No | No | Optional | Optional | Yes | Yes | No |
| View contracts/SLA | Summary | Summary | Yes | Yes | Yes | Yes | Own entitlement summary |
| Modify contracts | No | No | No | No | Optional | Yes | No |
| View client CRM | Search/basic | Basic | Yes | Yes | Yes | Yes | Own client only |
| Modify client CRM | No | No | No | No | Optional | Yes | Own contacts, optional |
| Publish knowledge | No | Draft suggestion | Draft | Draft/review | Approve/publish | Yes | No |
| View internal knowledge | Limited | Yes | Yes | Yes | Yes | Yes | No |
| Manage shifts | No | Own view | Own view | Own view | Team/all | Yes | No |
| View dashboards | Intake | Agent | Engineer | Specialist | Management | All | Portal summary |
| Export data | No | Limited | Limited | Limited | Yes | Yes | Own tickets only |
| Manage users/profiles | No | No | No | No | View/limited | Yes | No |
| View audit log | No | No | No | No | Operational subset | Full | No |

## 4. Recommended Permissions

### Identity and administration

- `user.read`
- `user.create`
- `user.update`
- `user.disable`
- `user.reset_authentication`
- `profile.read`
- `profile.create`
- `profile.update`
- `profile.assign`
- `profile.delete_custom`
- `permission.read`
- `permission.override`
- `audit.read`
- `system.settings.manage`

### Tickets

- `ticket.create.internal`
- `ticket.create.portal`
- `ticket.read.own`
- `ticket.read.assigned`
- `ticket.read.team`
- `ticket.read.all`
- `ticket.update.basic`
- `ticket.update.classification`
- `ticket.priority.change`
- `ticket.priority.set_p1`
- `ticket.assign.self`
- `ticket.assign.team`
- `ticket.assign.cross_team`
- `ticket.comment.public`
- `ticket.comment.internal`
- `ticket.resolve`
- `ticket.close`
- `ticket.reopen`
- `ticket.cancel`
- `ticket.merge`
- `ticket.bulk_action`
- `ticket.export`
- `ticket.attachment.upload`
- `ticket.attachment.download.internal`

### CRM, contracts, and SLA

- `client.read`
- `client.manage`
- `contact.manage`
- `installation.read`
- `installation.manage`
- `contract.read`
- `contract.manage`
- `sla.read`
- `sla.manage`
- `sla.override`

### Knowledge base

- `knowledge.read.internal`
- `knowledge.create_draft`
- `knowledge.review`
- `knowledge.publish`
- `knowledge.retire`
- `knowledge.manage_categories`

### Workforce, reports, and notifications

- `shift.read.own`
- `shift.read.team`
- `shift.manage.team`
- `shift.manage.all`
- `dashboard.agent`
- `dashboard.manager`
- `report.read`
- `report.export`
- `notification.manage_own`
- `notification.broadcast`

### Client portal

- `portal.ticket.create`
- `portal.ticket.read_client`
- `portal.ticket.comment`
- `portal.ticket.confirm_resolution`
- `portal.ticket.reopen`
- `portal.knowledge.read`
- `portal.contact.manage_own`

## 5. Default Profile Details

### Call Center Agent

Purpose: receive calls, identify the client/contact, register complete information, and route the ticket.

Defaults:

- Access to call-center intake dashboard.
- Create tickets and public comments.
- Search clients, branches, contacts, contracts, and service entitlement summaries.
- Assign only to an intake queue or approved support queue.
- Cannot add internal technical notes, resolve, close, change SLA, or view sensitive technical credentials.

### L1 Support Agent

Purpose: first response, triage, known fixes, evidence collection, and escalation.

Defaults:

- Read own, assigned, and team queue tickets.
- Add public and internal comments.
- Run L1 checklists and use approved knowledge.
- Resolve only configured L1 categories.
- Cannot set P1 without approval or reassign across departments.

### L2 Support Engineer

Purpose: technical diagnosis and resolution across RIS/PACS/IIS/Windows/SQL within assigned competencies.

Defaults:

- All L1 permissions.
- Advanced classification, technical tasks, problem links, changes, and team assignment.
- Resolve most incidents and requests.
- View contract/SLA details and technical installation records.
- No user/profile administration or unrestricted contract modification.

### L3 Specialist

Purpose: deep product, database, integration, DICOM, HL7, architecture, and root-cause work.

Defaults:

- All applicable L2 permissions.
- Handle P1 and patient-safety cases with mandatory reason/audit.
- Create problem records, known errors, root-cause analyses, and change plans.
- Review knowledge and technical resolution standards.
- Access is still limited by client/team assignment unless explicitly granted.

### Support Manager

Purpose: operational control, SLA ownership, escalation, workload, reporting, and approvals.

Defaults:

- View all internal tickets, queues, dashboards, SLA risks, and staff schedules.
- Reassign across teams, override priority/SLA with reason, approve closure/change, and broadcast notifications.
- Manage team membership, saved views, schedules, categories, and selected CRM/contract operations.
- Cannot change platform security configuration or grant Administrator without a separate privileged process.

### System Administrator

Purpose: platform configuration and security administration.

Defaults:

- Full configuration access, user/profile management, integrations, catalogs, feature flags, audit, and maintenance.
- Administration does not automatically mean operational ownership of tickets.
- Use a separate named account for each administrator; no shared `admin` account.
- Require MFA and stronger session policies.

### Client Portal User

Purpose: submit and follow requests for an authorized client and branches.

Defaults:

- Create tickets, read authorized client tickets, add public comments, download public attachments, confirm resolution, reopen, and search published portal knowledge.
- Never see internal notes, internal attachments, employee-only fields, audit events, other clients, internal SLA commentary, or unrestricted contact information.
- Portal access is additionally restricted by `ClientId` and authorized branch mappings.

## 6. User Creation UI

The user form should contain:

1. Identity: display name, username, email, authentication provider.
2. User type: Employee or Client Portal.
3. Default profile selector with profile description and risk badge.
4. Additional profiles, allowed only for privileged administrators.
5. Team/department and manager.
6. Client and branch scope for portal users.
7. Skill/product scope for support staff.
8. Default dashboard and saved view inherited from profile.
9. Account status, activation date, expiry date, timezone, and language.
10. Notification defaults.
11. Review panel showing the calculated effective permissions before save.

Rules:

- Client Portal profile requires a client and at least one branch or explicit all-branches authorization.
- Employee profiles cannot be assigned to a portal-only account.
- Administrator assignment requires step-up authentication, reason, and audit.
- Manager and Administrator assignments should optionally require four-eyes approval.
- A user may have multiple profiles, but conflicting privilege combinations must produce warnings.
- Removing the last login-capable profile must require confirmation.

## 7. Profile Management UI

Provide an administration page with:

- Profile list: name, type, user count, system/custom, status, last modified.
- Profile details: description, permissions grouped by module, default scopes, default dashboard, default views, notification defaults.
- Compare profiles side by side.
- Clone profile.
- Preview users affected before changing a profile.
- Version history and rollback through a controlled new version.
- System profiles cannot be deleted; they may be disabled only when no active users depend on them.

## 8. Database Model

Recommended tables:

- `iam.Profile`
- `iam.Permission`
- `iam.ProfilePermission`
- `iam.UserProfile`
- `iam.UserPermissionOverride`
- `iam.UserClientScope`
- `iam.UserBranchScope`
- `iam.ProfileDefaultView`
- `iam.ProfileVersion`

Important fields:

- Profile: code, name, description, profile type, system/custom, risk level, active flag, default dashboard, rowversion.
- Permission: code, module, action, description, high-risk flag.
- ProfilePermission: profile, permission, effect, default scope type.
- UserProfile: user, profile, valid from/to, assigned by, reason.
- Override: allow/deny, scope, valid from/to, reason, approved by.

Never copy all permissions directly into the user row. Resolve them through assignments and cache the calculated result with invalidation when a profile changes.

## 9. API Requirements

- `GET /api/v1/profiles`
- `GET /api/v1/profiles/{id}`
- `POST /api/v1/profiles`
- `POST /api/v1/profiles/{id}/clone`
- `PATCH /api/v1/profiles/{id}`
- `PUT /api/v1/profiles/{id}/permissions`
- `GET /api/v1/permissions`
- `PUT /api/v1/users/{id}/profiles`
- `GET /api/v1/users/{id}/effective-permissions`
- `POST /api/v1/users/{id}/permission-overrides`
- `DELETE /api/v1/users/{id}/permission-overrides/{overrideId}`

All writes require rowversion/concurrency checks and audit events. Permission updates must be transactional.

## 10. Testing Requirements

- Every default profile has an explicit allow/deny test matrix.
- L1 cannot use L2/L3-only endpoints.
- Call Center cannot read internal notes.
- Client Portal cannot access another client by guessed ID, search, export, WebSocket, or attachment URL.
- Manager cannot grant Administrator unless explicitly permitted by security policy.
- Expired profile assignments and overrides stop working immediately.
- Explicit deny beats allow.
- Profile changes invalidate authorization caches.
- Disabled users lose active sessions according to policy.
- All profile assignment and privilege changes appear in the audit log.
