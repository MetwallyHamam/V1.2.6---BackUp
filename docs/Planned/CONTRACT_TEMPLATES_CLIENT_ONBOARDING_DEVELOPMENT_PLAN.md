# Contract Templates and Client Onboarding Development Plan

Status: IN PROGRESS

## Implementation status

| Phase | Status | Verified result |
|---|---|---|
| Phase A — Foundation | DONE | Migration `0114`, models, permissions, ownership, acceptance date, provenance, generated identifiers, snapshot service, Ruff and backend regression tests pass. |
| Phase B — Template administration | DONE | Template list/create/edit/clone/default UI and APIs, preview APIs, save-as-template API, validation, versioning, and audit are implemented. |
| Phase C — Client onboarding | DONE | Atomic onboarding, mandatory owner department, optional contact, optional template contract, default selection, editable dates/duration, and existing-client additional-contract action are implemented. |
| Phase D — Existing contract editing | IN PROGRESS | Preview/apply APIs, selectable sections, audit reason, and finance/history guards are implemented; the contract-workspace apply-template dialog and expanded regression matrix remain planned. |
| Phase E — Delivery Projects integration | DONE | Delivery uses the atomic onboarding workflow with generated identifiers, owner/shared departments, optional contacts/access, optional template contract, acceptance date, and editable duration. Migration rehearsal, focused tests, static analysis, and production frontend build pass. |
| Phase F — Release packaging | PLANNED | Create release notes and immutable artifacts only when a release is explicitly requested. |

## 1. Goal

Add a simple reusable contract-template workflow without introducing multi-client contract accounting or historical financial migration.

The change must support:

1. Creating and managing several reusable contract templates.
2. Selecting one active template as the default.
3. Optionally creating a real contract while creating a client.
4. Creating a contract from a template later for an existing client.
5. Applying selected template sections to an existing contract through the normal contract-edit workflow.
6. Reusing the same onboarding workflow when a client is created from Delivery Projects.

## 2. Agreed business rules

- A contract template is not linked to a client, contact, ticket, invoice, payment, visit, or project.
- Primary contact creation remains optional.
- Client code is generated automatically by the server.
- Contact code is generated only when an optional contact is created.
- Contract number is generated automatically by the server.
- Every client must have one primary owner department selected from the active Department master and may be shared with multiple additional departments.
- Acceptance date is mandatory when creating a real contract.
- The real contract start date defaults to the acceptance date.
- Contract duration defaults to 12 months and remains editable before confirmation or later through authorized contract editing.
- The default contract name is `{Client Name} — {Template Name}` and remains editable before confirmation.
- A contract created from a template is a normal contract, not a template.
- Real contracts retain the source template ID and version for audit evidence.
- Template changes never modify contracts already created from that template.
- Existing invoices, payments, completed schedules, ticket history, SLA history, visits, consumed entitlements, and audit records are never copied or migrated when a template is applied.

## 3. Explicitly excluded scope

- One contract shared by several separately billed clients.
- Moving invoices or confirmed payments between contracts.
- Automatic financial balance transfers.
- Migrating closed tickets or historical SLA evidence.
- Deleting or replacing existing contracts as part of template application.
- Recalculating consumed entitlements or completed visits.
- Automatically modifying existing contracts when their source template changes.

These items require separate governance and are not necessary for the agreed simple workflow.

## 4. User scenarios

### 4.1 New client with a new contract

```text
Create client
→ Enter client details
→ Select owner department
→ Optionally enter a primary contact
→ Enable “Create a contract for this client”
→ Select a template (default template preselected)
→ Review and edit the copied contract configuration
→ Enter mandatory acceptance date
→ Confirm
```

The server creates the client, optional contact, contract, coverage, SLA, entitlements, and eligible future billing schedule in one transaction.

### 4.2 New client without a contract

The user leaves “Create a contract for this client” disabled. The system creates only the client and optional contact. The Client Profile clearly shows `No active contract` and provides `Create contract from template` later.

### 4.3 Existing client creates an additional contract

From Client Profile or Contract Setup:

```text
Create contract from template
→ Select template
→ Review/edit copied values
→ Enter acceptance/start dates
→ Confirm
```

Existing contracts and their history remain unchanged. Multiple contracts per client continue to be supported by the existing contract model.

### 4.4 Existing contract applies a template

From the normal contract-edit page:

```text
Apply template
→ Select template
→ Select sections to apply
→ Review differences
→ Enter mandatory change reason
→ Confirm
```

Eligible sections:

- Products and modules.
- Services.
- SLA policy.
- Request, work-hour, and visit entitlement defaults.
- Future billing configuration.
- Default duration only when explicitly selected.

Protected data that must not be replaced:

- Client and contract number.
- Acceptance and historical effective dates unless separately edited.
- Issued invoices and confirmed payments.
- Completed or collected billing schedules.
- Historical tickets, SLA results, visits, and audit records.

If financial activity exists, billing-template changes apply only to future unissued/unpaid schedule items. The API must reject changes that would rewrite confirmed financial evidence.

### 4.5 Client creation from Delivery Projects

Delivery Projects opens the same shared client-onboarding component and APIs. Project context may prefill client data and is linked after successful creation. No separate template or contract-creation implementation is permitted.

## 5. Data design

### 5.1 Contract template

Prefer a dedicated `contract_templates` master table rather than storing incomplete templates in the operational `contracts` table. This prevents templates from leaking into ticket selection, SLA matching, renewals, reporting, and finance totals.

Suggested fields:

```text
id
code
name
description nullable
template_type
is_default
is_active
version
default_duration_months (default 12)
default_sla_policy_id nullable
default_billing_frequency nullable
default_payment_terms_days nullable
created_by_user_id
updated_by_user_id
created_at
updated_at
```

Reuse normalized association tables for template products, modules, services, and entitlement defaults. Do not store delimited IDs.

Only one active default template may exist. Enforce this in the service transaction and with a database-safe strategy appropriate for both SQL Server and SQLite.

### 5.2 Real contract provenance

Add to real contracts:

```text
source_template_id nullable
source_template_version nullable
acceptance_date
```

The copied configuration is a snapshot. Runtime contract behavior must use the real contract records, never live template values.

### 5.3 Client ownership

Use the canonical Department master:

```text
clients.owner_department_id
```

Requirements:

- Mandatory for newly created clients.
- Only active departments are selectable.
- Existing clients receive a reviewed backfill/default before the column becomes non-null where deployment safety requires staged enforcement.
- Ownership does not itself grant blanket client or ticket visibility; existing permission and scope services remain authoritative.

### 5.4 Generated codes

Generate client, contact, and contract codes on the backend with concurrency-safe uniqueness.

Suggested defaults:

```text
Client: CLI-000001
Contact: CON-000001
Contract: CTR-2026-000001
```

Prefixes and digit width may reuse Site Settings. Manual overrides, if retained, require explicit permission and uniqueness validation.

## 6. API plan

### Template administration

- `GET /contract-templates`
- `GET /contract-templates/{id}`
- `POST /contract-templates`
- `PATCH /contract-templates/{id}`
- `POST /contract-templates/{id}/clone`
- `POST /contract-templates/{id}/make-default`
- `POST /contract-templates/{id}/activate`
- `POST /contract-templates/{id}/deactivate`
- `POST /contracts/{contract_id}/save-as-template`

### Preview and application

- `POST /contract-templates/{id}/preview`
  - Accepts client/date/value overrides.
  - Returns the exact proposed contract, coverage, SLA, entitlements, and schedule without writing.
- `POST /contracts/{contract_id}/template-preview`
  - Returns field/section differences and protected-data warnings.
- `POST /contracts/{contract_id}/apply-template`
  - Requires selected sections, expected contract version, and change reason.
  - Rechecks financial and operational protections on the server.

### Client onboarding

- Extend the existing client-create API or add one bounded orchestration endpoint such as `POST /clients/onboard`.
- Payload contains client data, optional contact, and optional contract draft produced from a template preview.
- Require an idempotency key.
- Create all requested records atomically.

### Existing client

- `POST /clients/{client_id}/contracts/from-template`
- Requires template ID/version, acceptance date, editable overrides, and idempotency key.

## 7. Permissions

Suggested permissions:

- `contract.template.view`
- `contract.template.manage`
- Reuse `contract.create` for creating a real contract.
- Reuse existing contract-edit permission for ordinary safe edits.
- `contract.template.apply` for applying a template to an existing contract.
- `client.create` and existing Delivery Project permissions remain required at their entry points.

High-risk template application must never bypass existing finance, SLA, entitlement, client-scope, or contract-edit authorization.

## 8. UI plan

### Contract Templates page

- List active/inactive templates.
- Clearly mark the default template.
- Create, edit, clone, preview, activate/deactivate, and make default.
- Show template type, duration, SLA, products/services, billing frequency, and version.

### Client creation

- Add a mandatory Primary Owner Department and an optional Shared Departments multi-select.
- Generate and display the client code.
- Keep Primary Contact in an optional collapsible section.
- Add `Create a contract for this client` switch.
- When enabled, preselect the default template and allow another template.
- Show an editable contract draft and final review summary.

### Client Profile

- Show owner department.
- Show `No active contract` when applicable.
- Add `Create contract from template` for authorized users.

### Contract edit

- Add `Apply template`.
- Allow section selection rather than all-or-nothing replacement.
- Show before/after differences.
- Show financial/history protection warnings.
- Require a meaningful reason and optimistic-lock version.

### Delivery Projects

- Launch the shared client-onboarding UI with project context.
- Return and link created client/contact/contract identifiers to the project.

## 9. Validation and safety rules

- Template code/name must be unique.
- Exactly one active default template at most.
- Template duration must be positive; default is 12 months.
- Acceptance date is mandatory for real contracts, not templates.
- End date defaults to `start date + duration − 1 day` using calendar-month arithmetic.
- Selected products/modules/services and SLA must be active when previewed and rechecked when committed.
- A module must belong to a selected product.
- A template cannot be deactivated while a draft operation is being committed without receiving a conflict response.
- Applying a template must not alter protected historical/financial records.
- Duplicate submissions return the previously created result through idempotency.
- Client, optional contact, contract, and linked configuration are committed or rolled back together.

## 10. Audit and evidence

Record:

- Template creation, editing, cloning, default changes, activation, and deactivation.
- Template ID and version used to create each contract.
- Client onboarding source (`CLIENT_SETUP` or `DELIVERY_PROJECT`).
- Generated identifiers.
- Contract-template application preview hash/version.
- Selected applied sections.
- Before/after values and mandatory reason.
- Rejected attempts to modify protected financial or historical evidence.

## 11. Migration strategy

1. Add template, template-association, provenance, acceptance-date, and client-owner-department schema.
2. Backfill acceptance date for existing contracts from the best approved source, otherwise mark records for review; do not invent legally significant dates silently.
3. Backfill client owner department using an explicitly approved rule and produce an exception report.
4. Create the initial templates from reviewed existing contract configurations.
5. Select one default template only after business review.
6. Keep existing client and contract creation APIs backward compatible during staged rollout.
7. Enable stricter mandatory-field enforcement only after populated upgrade rehearsal and backfill approval.

## 12. Test plan

### Backend

- Template CRUD, cloning, versioning, default uniqueness, and activation rules.
- Generated-code concurrency and uniqueness.
- Client-only onboarding.
- Client plus optional contact.
- Client plus contract from default/non-default template.
- Existing client creates an additional contract.
- Template snapshot independence after later template edits.
- Apply selected template sections with before/after audit evidence.
- Reject attempts to rewrite invoices, payments, completed schedules, consumed entitlements, or historical evidence.
- Future unpaid schedule changes only.
- Permission and client/department scope matrix.
- Idempotent retries and atomic rollback.
- Delivery Project uses the same orchestration path.
- Clean and populated SQLite/SQL Server migration rehearsals.

### Frontend

- Optional contact behavior.
- Contract switch disabled/enabled behavior.
- Default template selection and alternative selection.
- Editable template snapshot before confirmation.
- Mandatory owner department and acceptance-date validation.
- Preview and final confirmation.
- Existing-client contract creation.
- Apply-template section selection and differences.
- Financial/history warnings.
- Responsive layout, keyboard operation, accessible labels, loading, errors, and retry behavior.

## 13. Delivery phases

### Phase A — Foundation

Status: DONE

- Schema and migration.
- Template service and permissions.
- Generated-code service.
- Preview/snapshot logic.
- Backend tests and upgrade rehearsals.

### Phase B — Template administration

Status: DONE

- Template list/create/edit/clone/default UI.
- Save existing configuration as template.
- Template validation and audit.

### Phase C — Client onboarding

Status: DONE

- Mandatory owner department.
- Optional contact.
- Optional contract switch and editable template draft.
- Atomic client/contract creation.
- Client Profile later-action support.

### Phase D — Existing contract editing

Status: IN PROGRESS

- Apply-template preview and section selection.
- Protected financial/history rules.
- Future billing-change handling.
- Audit and regression coverage.

### Phase E — Delivery Projects integration

Status: DONE

- Shared atomic onboarding integration with Delivery project link-back.
- Owner and shared-department selection.
- Optional template contract, acceptance date, and editable duration.
- Automatic project, client, contact, employee, branch, location, contract, template, template-type, department, profile, contract-type, SLA-policy, finance-reason, approval-group, and CRM catalog codes.
- Contract Template Types create/edit/delete master-data tab.
- Static analysis, backend regression tests, production frontend build, and clean migration rehearsal.

### Phase F — Release packaging

Status: PLANNED

- Release notes and immutable packaging will be completed only after an explicit release request.

## 14. Acceptance criteria

- Administrators can maintain several simple templates and designate one default.
- A new client can be created with no contract or with one editable real contract copied from a selected template.
- Primary contact remains optional.
- Client, optional contact, and contract identifiers are generated safely by the backend.
- Owner department and real-contract acceptance date are enforced.
- Existing clients can create additional contracts from templates.
- Existing contracts can apply selected template sections without rewriting protected history or finance.
- Delivery Projects reuse the same workflow.
- Templates never appear as operational contracts or affect SLA, finance, renewal, ticket, entitlement, or visit calculations.
- Clean and populated deployment rehearsals and the complete test/build gates pass.

============================================================
CODEX STOP POINT
Status: IN PROGRESS
Completed scope: Phases A–C and E; Phase D backend protections; template administration, client onboarding, and Delivery project onboarding production UI; contract-template-type master data; automatic system identifiers; tests and production frontend build
Last completed item: Replaced Delivery quick-create with shared atomic client/contract onboarding and verified migration `0117_contract_template_types`
Next planned item: Finish Phase D contract-workspace apply-template UI; package Phase F only after an explicit release request
Safe to continue from here: YES
Blocking decision(s): Approve the existing-client owner-department backfill rule and the source used to backfill legally meaningful acceptance dates
============================================================
