You are working on the **MILLENSYS Support Hub System**.

I need you to inspect and enhance the existing **Roles / Profiles / Permissions / Authorization architecture**.
as i attached a database from the current production on my local sql server user sa , PW P@$4m!DB database name MillensysSupportHub this acataly the working production database  you can use it to inspect too 

Do **not** start by replacing the current permission model with a predefined architecture.

The existing system is already working and contains many workflows, shared components, permission checks, page guards, APIs, roles, and dependencies.

The goal is:

> Understand the current implementation first, identify where the permission model is causing workflow conflicts or excessive access, then enhance/refactor it using the safest design that fits the existing codebase.

---

# Main Business Problem

Currently, permissions sometimes appear to be strongly coupled to pages/modules.

However, a user role may participate in a workflow that needs functions from several different modules.

For example, the **Project Handover** profile may need to:

* Create a client.
* Select an engineer.
* Select a contract template.
* Select products/services.
* Select branches/reference data.
* Create a contract.
* Upload documents.
* Complete project delivery.

Some of those functions may currently depend on permissions such as:

```text
Master Data Access
User Management
Client Management
Contract Management
```

This can create a problem:

A role needs only one function from another module, but granting that permission may expose the entire page/module or other administrative functions.

Example:

```text
Project Handover
    ↓
Needs to select Contract Template
    ↓
Current code may require Master Data permission
    ↓
User may accidentally receive access to Master Data administration
```

This is the behavior that needs investigation and improvement.

---

# Existing Profiles

Preserve the current profile structure unless there is a strong technical reason to change it.

Current profiles include:

| Name                      | Code             | Type          | Risk     | Managed |
| ------------------------- | ---------------- | ------------- | -------- | ------- |
| Call Center               | CALL_CENTER      | EMPLOYEE      | STANDARD | System  |
| Client Portal             | CLIENT_PORTAL    | CLIENT_PORTAL | STANDARD | System  |
| General Technical Support | PRF-000020       | EMPLOYEE      | STANDARD | Custom  |
| Human Resources           | HR               | EMPLOYEE      | STANDARD | System  |
| L1 Support                | L1_SUPPORT       | EMPLOYEE      | STANDARD | System  |
| L2 Support                | L2_SUPPORT       | EMPLOYEE      | STANDARD | System  |
| L3 Support                | L3_SUPPORT       | EMPLOYEE      | STANDARD | System  |
| Project Handover          | PROJECT_HANDOVER | EMPLOYEE      | STANDARD | System  |
| Support Manager           | SUPPORT_MANAGER  | EMPLOYEE      | STANDARD | System  |
| System Administrator      | ADMINISTRATOR    | ADMINISTRATOR | CRITICAL | System  |
| Team Leaders              | PRF-000019       | EMPLOYEE      | STANDARD | Custom  |
| Top Management            | TOP_MANAGEMENT   | EMPLOYEE      | STANDARD | System  |

Do not redesign these roles before understanding how they are currently used.

---

# PHASE 1 — INSPECT ONLY

Before changing any code, inspect the complete authorization implementation.

Do not modify anything during this phase.

## Inspect Backend

Find and understand:

* Authentication implementation.
* User model.
* Profile/role model.
* Permission model.
* Role/profile permission mappings.
* User-level permission overrides if present.
* Permission database tables.
* Permission seed data.
* Permission constants/enums.
* Authorization middleware.
* Authorization decorators.
* Route/API permission checks.
* Service-layer authorization.
* Repository/data-access authorization if any.
* Record/data scope handling.
* Admin permission checks.
* Master Data permission checks.
* Client permission checks.
* User/Engineer permission checks.
* Contract permission checks.
* Project Handover permission checks.
* Ticket permission checks.
* Shift permission checks.
* Operation permission checks.
* Onboarding permission checks.
* Client Care permission checks.
* Report/KPI permission checks.

---

# Inspect Frontend

Find and understand:

* Authentication context/store.
* Current-user object.
* Loaded permission structure.
* Profile structure.
* Permission helper functions.
* Route guards.
* Protected routes.
* Sidebar/menu filtering.
* Page visibility.
* Tab visibility.
* Button visibility.
* Disabled actions.
* Modals.
* Shared dropdowns.
* Shared selectors.
* Reusable forms.
* Shared tables.
* Action menus.
* Permission-aware hooks/components.

Search for patterns such as:

```text
hasPermission(...)
can(...)
permissions.includes(...)
ProtectedRoute
PermissionGuard
RequirePermission
CanAccess
```

and similar project-specific implementations.

---

# Inspect Database

Determine:

* Tables responsible for profiles.
* Tables responsible for permissions.
* Mapping tables.
* Whether permissions contain module/category/action metadata.
* Whether permission hierarchy exists.
* Whether parent-child permissions exist.
* Whether permissions have dependencies.
* Whether permissions are seeded.
* Whether permissions are system-managed or custom.
* Whether role/profile changes are audited.
* Whether data scope is stored separately.

Do not create new tables unless the existing schema genuinely cannot support the required improvement.

---

# PHASE 2 — MAP CURRENT BEHAVIOR

After understanding the architecture, create an inventory of the actual permission system.

Produce:

## Existing Permission Catalog

For every permission, identify:

```text
Permission
Purpose
Backend usage
Frontend usage
Pages affected
Functions affected
Profiles currently using it
```

Especially identify permissions that are reused in many unrelated places.

---

# Identify Broad/Coupled Permissions

Search for permissions that control too many unrelated behaviors.

For example:

```text
MASTER_DATA
MASTER_DATA_VIEW
MASTER_DATA_MANAGE
USER_MANAGEMENT
CLIENT_MANAGEMENT
ADMIN
```

These are only examples.

Use the real permission names from the code.

For each broad permission, determine:

```text
Where is it checked?
Why is it checked there?
What functionality actually needs it?
Does it expose more functionality than required?
```

---

# PHASE 3 — MAP WORKFLOWS

The important part of this task is understanding permissions from the perspective of actual workflows.

For each major profile, identify the workflows it participates in.

Examples include:

```text
Ticket Handling
Ticket Assignment
Ticket Escalation
Project Handover
Client Creation
Contract Creation
Shift Planning
Internal Operations
Client Care
Onboarding
Approvals
Knowledge Base
Reports
KPI
Notifications
```

Use the workflows that actually exist in the system.

---

# Identify Engaged Functions

For every workflow, identify the functions it consumes.

Example:

```text
Project Handover
```

may call functions such as:

```text
Open Project Handover
Create Project
Create Client
Search Client
Select Engineer
Assign Engineer
Select Contract Template
Select Product
Select Service
Select Branch
Create Contract
Upload Document
Complete Handover
```

The same shared function may be used in several workflows.

Example:

```text
Select Engineer
```

may be used by:

```text
Project Handover
Ticket Assignment
Shift Planning
Operations
Onboarding
```

Identify this reuse from the actual code.

---

# Create a Workflow Dependency Matrix

Produce a matrix similar to:

| Workflow         | Function                 | Current Permission | Actual Resource   | Shared With     | Problem   |
| ---------------- | ------------------------ | ------------------ | ----------------- | --------------- | --------- |
| Project Handover | Select Engineer          | USER_MANAGEMENT    | Engineer          | Shift, Ticket   | Too broad |
| Project Handover | Select Contract Template | MASTER_DATA_VIEW   | Contract Template | Contract        | Too broad |
| Shift Planning   | Select Engineer          | USER_MANAGEMENT    | Engineer          | Project, Ticket | Too broad |

Use the real findings from the code.

This matrix must be produced before designing the refactor.

---

# PHASE 4 — IDENTIFY THE ACTUAL DESIGN PROBLEM

Determine whether the current architecture problem is mainly caused by:

* Page-based permissions.
* Module-based permissions.
* Resource-level permissions that are too broad.
* Shared API permission dependencies.
* Shared component permission checks.
* Route guards.
* Menu visibility logic.
* Backend authorization.
* Dropdown endpoints.
* Parent/child permission inheritance.
* Incorrect role assignments.
* Missing function-level permissions.
* Missing read/use/manage separation.
* Permission duplication.
* Permission naming inconsistencies.
* Legacy permissions.

Do not assume the answer in advance.

Document the real cause.

---

# PHASE 5 — PROPOSE THE SAFEST ENHANCEMENT

Only after completing the inspection should you design the enhancement.

The preferred direction is:

> A role should receive only the capabilities necessary to perform its workflow.

However, adapt the implementation to the existing architecture.

Do not force a completely new permission system if the existing system can be improved safely.

Potential improvements may include:

```text
Separating page access from action access
Separating lookup/read permissions from management permissions
Adding granular function permissions
Splitting overly broad permissions
Adding safe shared lookup endpoints
Improving permission helpers
Changing route/menu permission logic
Adding permission dependencies
Improving profile permission UX
```

Use only the improvements justified by the code inspection.

---

# Important Design Principle

A workflow can use data/functionality from another module without necessarily receiving administrative access to that module.

For example:

```text
Project Handover
    ↓
Select Engineer
```

should not necessarily mean:

```text
Access User Administration
Edit Engineer
Deactivate Engineer
Manage Profile
```

Likewise:

```text
Project Handover
    ↓
Select Contract Template
```

should not necessarily mean:

```text
Open Master Data
Create Template
Edit Template
Delete Template
```

But do not implement new permissions blindly.

First determine whether the current system already has a mechanism that can provide this separation.

---

# Prefer Enhancement Over Replacement

If the existing permission structure already has granular permissions such as:

```text
CLIENT_CREATE
CLIENT_VIEW
CLIENT_EDIT
CONTRACT_TEMPLATE_VIEW
PROJECT_CREATE
```

reuse and improve them.

Do not introduce an entirely new naming structure just for consistency.

If the existing system uses:

```text
PERMISSION_CLIENT_CREATE
```

do not automatically change everything to:

```text
client.create
```

unless there is a strong benefit and the migration is safe.

Consistency with the existing codebase is more important than forcing a theoretical naming convention.

---

# Shared Function Permissions

If a shared function currently depends on an administrative permission, evaluate whether it can safely have a smaller permission.

For example:

```text
Engineer selector
```

could potentially depend on:

```text
VIEW_ENGINEER_LOOKUP
```

instead of:

```text
MANAGE_USERS
```

But choose the final permission design based on the current architecture.

Do not create unnecessary permissions if an existing safe read permission already solves the problem.

---

# Lookup APIs

Inspect all shared selectors/dropdowns.

Examples:

```text
Engineer selector
Client selector
Product selector
Service selector
Branch selector
Contract template selector
Shift type selector
Department selector
```

Determine whether they use administrative endpoints.

Example problem:

```text
GET /api/admin/users
```

used simply to populate:

```text
Select Engineer
```

If this causes broad authorization requirements, improve it.

Possible solution:

```text
GET /api/lookup/engineers
```

but only introduce dedicated lookup endpoints if they improve security and reuse.

Reuse existing APIs where safe.

---

# Backend Is the Security Authority

Ensure that frontend permission visibility is not the only security check.

Sensitive backend actions must remain protected.

Example:

A Project Handover user may be allowed to retrieve/select a contract template.

But attempting to call:

```text
Update Contract Template
Delete Contract Template
```

directly through the API must still be rejected.

Use the appropriate HTTP authorization response, normally:

```text
403 Forbidden
```

depending on the existing API conventions.

---

# Navigation Must Be Independent Where Necessary

Investigate whether the sidebar/menu is built directly from permission ownership.

Example:

If a user receives a small permission required for Project Handover, it should not accidentally cause this menu to appear:

```text
Administration
  → Master Data
```

Improve navigation rules if this coupling exists.

Menu visibility, page accessibility, and action capability may need separate checks.

Use the current application's design rather than introducing unnecessary abstractions.

---

# Profile Permission Management UX

Inspect the current profile permission management screen.

Determine whether the administrator can understand what each permission actually enables.

Potential problem:

```text
MASTER_DATA_VIEW
```

does not tell the administrator whether it means:

```text
Can select products
Can select branches
Can open Master Data page
Can view contract templates
Can manage templates
```

If the UI is confusing, enhance it.

Possible improvements:

* Group permissions by business area.
* Improve permission display names.
* Add descriptions.
* Distinguish workflow/function permissions from administration permissions.
* Show permission risk.
* Show permission dependencies.
* Show what workflows use the permission.

Do not redesign the entire UI unnecessarily.

---

# Existing Profiles Must Be Evaluated

Analyze the current permission behavior of:

```text
CALL_CENTER
CLIENT_PORTAL
PRF-000020
HR
L1_SUPPORT
L2_SUPPORT
L3_SUPPORT
PROJECT_HANDOVER
SUPPORT_MANAGER
ADMINISTRATOR
PRF-000019
TOP_MANAGEMENT
```

For every profile, document:

```text
Current workflows
Current permissions
Permissions actually required
Broad permissions currently used
Potential over-permissioning
Potential missing permissions
```

Do not automatically change every profile.

Only migrate permissions that need correction.

---

# Project Handover Must Be a Primary Test Case

Use `PROJECT_HANDOVER` as one of the primary validation scenarios.

The desired business behavior is:

```text
Project Handover user
    ↓
Open Project Handover
    ↓
Create / manage permitted project
    ↓
Select or create client where allowed
    ↓
Select engineer
    ↓
Select contract template
    ↓
Select product/service/branch
    ↓
Create contract/project records
    ↓
Upload documents
    ↓
Continue handover workflow
```

This should work without unnecessarily providing access to:

```text
User Administration
Master Data Administration
Contract Template Administration
Product Administration
Service Administration
Branch Administration
Permission Administration
```

However, determine the final permission combination based on the actual code.

---

# Do Not Break Working Workflows

This refactor must be backward-compatible.

Before changing permissions, determine which screens/functions currently rely on them.

Pay special attention to shared permissions because modifying one permission could affect many modules.

Regression-test:

```text
Tickets
Clients
Contracts
Project Handover
Shifts
Operations
Onboarding
Client Care
Knowledge Base
Approvals
Reports
KPI
Notifications
Master Data
User Management
```

Use the modules actually present in the current source code.

---

# Migration Strategy

If new permissions are required:

1. Create them safely.
2. Map existing profiles to them.
3. Preserve existing user/profile assignments.
4. Avoid removing old permissions immediately.
5. Identify legacy permissions as deprecated where possible.
6. Keep temporary compatibility logic if required.
7. Remove legacy permission checks only after verifying all references.

If database migrations are necessary, make them:

* SQL Server compatible.
* Idempotent where practical.
* Transactional where practical.
* Safe for existing data.
* Easy to roll back or understand.

---

# Avoid Permission Explosion

Do not create a permission for every field, button, or minor UI element.

Create granular permissions only for meaningful business/security boundaries.

For example:

Good candidate:

```text
Create Client
Assign Engineer
Approve Operation
Edit Contract Template
Delete Client
Manage Users
```

Probably unnecessary:

```text
View Client Name Field
View Contract Date Label
Open Engineer Dropdown Arrow
```

Maintain a practical authorization model.

---

# Avoid Duplicate Concepts

Before adding a permission, search for an existing permission with the same meaning.

Do not create:

```text
ENGINEER_SELECT
SELECT_ENGINEER
ENGINEER_LOOKUP
VIEW_ENGINEERS_FOR_DROPDOWN
```

unless they actually represent different security behaviors.

Reuse existing concepts whenever possible.

---

# Authorization Consistency

After refactoring, the following layers should agree:

```text
Database permission
Backend authorization
Frontend permission helper
Route/page access
Menu visibility
Action/button visibility
Shared component behavior
```

Avoid situations where:

```text
Frontend allows but backend denies
```

or:

```text
Backend allows but frontend hides
```

unless that behavior is intentional.

---

# Tests

Add or update tests where the project already has testing infrastructure.

At minimum validate:

### Project Handover

Allowed workflow functions work.

Administrative functions remain blocked.

### Shared Engineer Selection

Engineer can be selected where needed without granting full user administration.

### Contract Template Selection

Template can be selected/used without granting template administration.

### Call Center

Required ticket/client lookup functions continue working.

### L1 / L2 / L3

Ticket workflow is not broken.

### Team Leaders

Team-level management remains functional.

### Support Manager

Manager workflow remains functional.

### Top Management

Read/reporting access remains functional.

### Administrator

Administrator retains all expected administrative capability.

### Client Portal

Client data isolation remains enforced.

---

# Required Output Before Implementation

Before making significant changes, produce a concise technical analysis containing:

## 1. Current Architecture

Explain how roles and permissions currently work.

## 2. Main Problems Found

List actual coupling/conflicts found in the code.

## 3. Affected Workflows

List workflows affected by those problems.

## 4. Shared Functions

List shared functions currently requiring broad permissions.

## 5. Proposed Enhancement

Explain the smallest safe architectural improvement.

## 6. Migration Impact

Explain what existing roles/permissions will be affected.

Then proceed with implementation.

Do not wait for additional confirmation unless the codebase contains a genuinely blocking ambiguity.

---

# Required Final Deliverables

After implementation provide:

## Current State vs Enhanced State

Example:

```text
BEFORE

Project Handover
→ MASTER_DATA_VIEW
→ Contract selector works
→ Master Data page also becomes accessible

AFTER

Project Handover
→ minimum required permission
→ Contract selector works
→ Master Data administration remains protected
```

Use the real permission names from the project.

---

## Permission Changes

Provide:

| Existing Permission | Problem | Enhancement | Profiles Affected |
| ------------------- | ------- | ----------- | ----------------- |

---

## Workflow / Function Matrix

Provide:

| Role | Workflow | Function | Required Permission |
| ---- | -------- | -------- | ------------------- |

---

## Changed Files

Separate:

```text
Backend
Frontend
Database
Tests
```

and explain each important change.

---

## Database Changes

Provide all required migration/seed scripts and explain them.

---

## Legacy Permissions

Classify existing permissions as:

```text
UNCHANGED
REFACTORED
COMPATIBILITY
DEPRECATED
SAFE TO REMOVE LATER
```

---

## Regression Results

Report which workflows were tested and their result.

---

# Critical Rules

1. **Inspect first.**
2. **Do not force a new architecture before understanding the current one.**
3. **Do not replace working permission infrastructure unnecessarily.**
4. **Prefer targeted enhancement over rewrite.**
5. **Preserve existing roles.**
6. **Preserve existing users and assignments.**
7. **Do not grant broad administration rights just to enable one workflow function.**
8. **Do not create duplicate permissions.**
9. **Do not create excessive micro-permissions.**
10. **Backend authorization remains mandatory.**
11. **Do not change unrelated workflows.**
12. **Follow existing coding patterns and project conventions.**
13. **Keep migration backward-compatible.**
14. **Reuse shared permission helpers where possible.**
15. **Document every broad permission that remains and why.**

---

# Core Goal

The final authorization system should match how the Support Hub actually works:

```text
ROLE
   ↓
Participates in workflows
   ↓
Workflow uses functions
   ↓
User receives only the access required for those functions
```

without unnecessarily turning a workflow user into an administrator of the modules supplying those functions.

The implementation must be based on the **existing source code and actual workflow dependencies**, not assumptions.

---

# Stop Point

When the permission analysis, enhancement, migration, and regression testing are complete:

STOP.

Do not continue into unrelated authentication, role, workflow, or UI redesign.

Finish with:

```text
=========================================
STOP POINT — PERMISSION ENHANCEMENT DONE
=========================================

Architecture inspected:
- ...

Problems identified:
- ...

Enhancements implemented:
- ...

Profiles affected:
- ...

Legacy permissions:
- ...

Regression tests:
- ...

Remaining recommendations:
- ...
```
