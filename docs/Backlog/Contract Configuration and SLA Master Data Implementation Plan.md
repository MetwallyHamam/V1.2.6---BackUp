# Contract Configuration and SLA Master Data Implementation Plan

Status: Deferred for later implementation  
Prepared: 2026-08-18  
Risk: High-impact contract entitlement and SLA governance change

## 1. Objective

Reduce the time and error rate involved in configuring contracts, linked clients, coverage, products, modules, services, and SLA targets.

The finished workflow must provide:

- Searchable, paginated multi-selection without a 50-client dead end.
- Selected values removed from the available-value list.
- Select-visible, select-all-matching, remove-visible, and clear-all operations.
- Bulk contract coverage creation and maintenance.
- Editable, reusable, importable SLA templates managed as master data.
- Default priority targets that apply regardless of service.
- Optional service-, product-, and module-specific priority overrides.
- Deterministic fallback behavior and auditable SLA matching.
- Versioned changes that never rewrite historical ticket SLA evidence.

## 2. Non-negotiable rules

1. A search result limit must never make valid clients or catalog values unreachable.
2. Selecting a value removes it from the available list while keeping it visible in a selected-items panel.
3. Selection must survive search, paging, sorting, and reopening the selector before save.
4. “Select all matching” means every record matching the server-side filter, not only the loaded page.
5. Large bulk actions require a count preview and confirmation.
6. An SLA policy must contain one default target per required priority before it can be published.
7. A specific override wins over a default target only when every configured scope dimension matches.
8. A missing service-specific target must fall back to the priority default; it must not result in no SLA.
9. Ticket status controls clock lifecycle. Contract, scope, and priority select the target duration.
10. Published SLA versions are immutable. Editing produces a draft/new version.
11. Existing SLA clocks retain their target, calendar, policy version, and match reason snapshots.
12. Imports are validated and transactional; invalid files must not leave partial configuration.
13. Existing contracts and SLA policies continue to work after migration without manual repair.
14. Every bulk change, publication, import, and default-template change is audited.

## 3. Current code findings

### 3.1 Client selection

`frontend/src/pages/ContractsPage.tsx` requests `/clients` with `limit: 50`. The selector uses an MUI multi-select `Autocomplete`, disables local filtering, and provides “Select visible results,” but users cannot browse beyond the returned 50 records without changing the search.

The selected options are merged back into the same option collection. This keeps selected clients in the available dropdown and makes large selections difficult to review.

The clients endpoint supports server-side search and a limit up to 200, but it does not currently expose a complete paginated selection contract suitable for “select all matching.” Raising the limit alone is not an acceptable solution.

### 3.2 Coverage configuration

Coverage rules are added one at a time. Product, module, service, site, environment, and ticket type use click-only select controls. The UI has no bulk selection, searchable catalogs, matrix preview, bulk edit, or reusable coverage bundle.

### 3.3 SLA configuration

Contracts link to reusable central SLA policies, and targets already support:

- `product_id`
- `product_module_id`
- `service_id`
- `priority`
- `context_key`
- `is_fallback`
- effective dates and a version

The current contract SLA UI creates or updates one target at a time and exposes only service and priority, despite the backend schema supporting product and module scope.

The current resolver in `backend/app/modules/sla/service.py` contains a fallback defect. For a priority, if any service-scoped target exists, an unrelated service receives no target instead of falling back to the priority-only target.

### 3.4 Existing historical protections

Ticket SLA clocks already store target and policy evidence. The implementation must continue using clock snapshots for historical reporting and must never recalculate closed or existing clocks merely because master data changes.

## 4. Target user experience

### 4.1 Contract workflow

Use a guided workspace with four sections and a persistent summary:

1. Contract details
2. Clients
3. Coverage
4. SLA and review

Users may save a draft at any section. Activation is a separate action that runs validation and shows a review summary containing:

- Contract dates and calendar
- Number and mode of linked clients
- Included and excluded coverage rules
- SLA template and version
- Missing or conflicting configuration
- Estimated impact of activation

### 4.2 Client selection panel

Replace the single dropdown with a two-panel selector.

```text
Available clients                         Selected clients (248)
┌─────────────────────────────┐          ┌─────────────────────────────┐
│ Search code or name         │          │ Search selected clients     │
│ [ ] Client A                │   Add →  │ [x] Client C        Remove  │
│ [ ] Client B                │  ← Remove│ [x] Client D        Remove  │
│ Load more / page controls   │          │ Selected paging             │
└─────────────────────────────┘          └─────────────────────────────┘
 Select visible | Select all matching     Remove visible | Clear all
```

Required behavior:

- Search by normalized client name and code.
- Server-side sorting and cursor or page-based pagination.
- Exclude selected IDs from available results.
- Preserve selection across searches and pages.
- Show total matching, loaded, and selected counts.
- Support active/inactive filtering.
- Support `Specific clients` and explicit `All clients` modes.
- Do not materialize all client IDs when `All clients` is selected.
- Warn before removing clients whose active tickets or coverage depend on the contract.

“Select all matching” should use a selection expression:

```text
mode: EXPLICIT | ALL_MATCHING
explicit_ids: []
filter_snapshot: { search, active_only, ... }
excluded_ids: []
```

The backend resolves that expression transactionally when saving. This avoids loading thousands of IDs into the browser. The API must return the affected count before confirmation.

### 4.3 Searchable catalog controls

Replace large `TextField select` controls with a shared searchable autocomplete component supporting:

- Single and multiple modes
- Debounced server-side search
- Pagination/infinite scrolling
- Keyboard navigation
- Selected chips or selected-items panel
- Selected-value exclusion
- Select visible/all matching
- Loading, empty, and error states
- Accessible labels and focus handling

Use the component for clients, products, modules, services, branches, environments, ticket types, calendars, contacts, and SLA templates where appropriate.

Module results must be filtered by selected product. A module cannot be selected without its owning product.

### 4.4 Bulk coverage builder

Allow users to select multiple values and generate coverage rules in one operation:

- Products
- Modules per product, including “all modules”
- Services
- Clients or all linked contract clients
- Sites
- Environments
- Ticket types
- Include or exclude decision
- Shared notes

Before saving, show a normalized preview rather than silently creating an uncontrolled Cartesian product. Collapse broad selections into wildcard rules when semantically equivalent.

Provide table selection, bulk edit, bulk remove, duplicate detection, conflict warnings, and a dry-run count endpoint.

## 5. SLA templates as master data

### 5.1 Master record

Promote central SLA policies into a dedicated master-data area named `SLA Templates`.

Each logical template has:

```text
code
name
description
is_system
is_default
is_active
calendar_id
include_escalation_time
current_published_version_id
created_by / created_at
updated_by / updated_at
```

Only one active template may be the system default. `No SLA` remains an explicit contract behavior and must not be confused with an incomplete template.

Suggested initial seed templates:

- `STANDARD_SUPPORT`
- `BUSINESS_HOURS_SUPPORT`
- `CRITICAL_24X7`
- `NO_SLA` only if represented as an explicit protected behavior rather than empty targets

Seeded durations require business-owner approval; migrations must not invent operational commitments.

### 5.2 Version model

Each template version has a lifecycle:

```text
DRAFT -> PUBLISHED -> RETIRED
```

Rules:

- Published versions are immutable.
- Editing a published template clones it into a new draft.
- Only one draft may be open per template unless a later requirement allows branches.
- Publishing validates all defaults and overrides atomically.
- Contracts may follow the latest published version or pin a specific version.
- Default behavior for existing contracts should preserve their current policy/version semantics.
- Publication displays affected contract count.
- Rollback means republishing a prior version as a new version, not mutating history.

### 5.3 Target matrix

Present targets as an editable matrix:

| Scope | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| Default — all services | Required | Required | Required | Required |
| PACS | Override/inherit | Override/inherit | Override/inherit | Override/inherit |
| RIS | Override/inherit | Override/inherit | Override/inherit | Override/inherit |

Each cell contains:

- First-response minutes
- Resolution minutes
- Warning percentage
- Inherit/override state
- Optional effective-from/effective-until

Actions:

- Copy one priority to selected priorities
- Copy one service row to selected services
- Reset selected cells to inherited default
- Apply a percentage or duration adjustment in bulk
- Preview resolved targets

Inherited cells are visually distinct and show their source target.

## 6. Deterministic SLA resolution

### 6.1 Required precedence

For the ticket priority and effective timestamp, choose the first exact match in this order:

1. Product + module + service + priority
2. Product + module + any service + priority
3. Product + service + priority
4. Product + any service + priority
5. Service + priority
6. Default priority target, regardless of service
7. No target

A more specific rule must never prevent evaluation of a less-specific fallback when it does not match.

If the business chooses a smaller supported scope for the first release, implement service + priority followed by default priority, while retaining a single resolver design that can add product/module tiers without another rewrite.

### 6.2 Example

```text
Default P1: respond 30 minutes, resolve 240 minutes
Default P2: respond 60 minutes, resolve 480 minutes
PACS P1 override: respond 15 minutes, resolve 120 minutes
PACS P2 override: respond 30 minutes, resolve 360 minutes
```

Expected results:

- PACS + P1 -> PACS P1 override
- PACS + P2 -> PACS P2 override
- RIS + P1 -> default P1
- Any unconfigured service + P2 -> default P2
- A service-specific P1 rule has no effect on P2, P3, or P4

### 6.3 Status versus priority

Priority selects the SLA duration. Ticket status controls the clock lifecycle:

- Configured active statuses: clock runs
- Customer-pending statuses: clock pauses according to policy
- Millensys-pending/escalated statuses: included or excluded according to policy
- Resolved/closed status: clock completes
- Reopened status: applies the approved reopen policy

Do not overload service or status to infer priority. Any automatic priority calculation remains a separate impact/urgency concern.

### 6.4 Resolver output

Return structured evidence:

```text
policy_id
policy_version
target_id
match_tier
match_reason
matched dimensions
inherited dimensions
calendar_id
first_response_minutes
resolution_minutes
warning_percent
```

Store the relevant evidence on the ticket clocks and expose it in ticket details, reports, and support diagnostics.

## 7. Import and export

### 7.1 Supported format

Provide an XLSX workbook as the primary format and CSV as a supported flat format.

Minimum target sheet columns:

| Column | Required | Notes |
|---|---|---|
| Template Code | Yes | Stable unique business code |
| Template Name | Yes for create | Display name |
| Calendar Code | Yes | Resolve by stable code, not database ID |
| Scope Type | Yes | `DEFAULT`, `SERVICE`, `PRODUCT`, `PRODUCT_SERVICE`, or `PRODUCT_MODULE_SERVICE` |
| Product Code | Conditional | Required by product scopes |
| Module Code | Conditional | Requires product code |
| Service Code | Conditional | Required by service scopes |
| Priority | Yes | `P1` through `P4` |
| Response Minutes | Yes | Positive integer |
| Resolution Minutes | Yes | Must be at least response minutes |
| Warning Percent | Yes | 1–99 |
| Effective From | No | ISO date/time |
| Effective Until | No | After effective-from |
| Default Template | No | Boolean; restricted operation |

### 7.2 Import workflow

1. Download the versioned import template.
2. Upload XLSX or CSV.
3. Select create, update draft, or create new version.
4. Parse into a staging model without writing master tables.
5. Map and validate columns.
6. Resolve catalog codes.
7. Display valid rows, warnings, errors, duplicates, and projected changes.
8. Download an annotated error workbook if needed.
9. Confirm the operation.
10. Apply all rows in one transaction.
11. Record an import job, counts, actor, source checksum, and audit event.

Unknown catalogs must fail validation by default. A separate privileged option may create missing master data only if explicitly approved later.

### 7.3 Import validation

- File type and size limits
- Formula/macro rejection
- Required columns and supported template version
- Unique template/context/priority combinations
- Valid product-module ownership
- Active catalog references or an explicit warning policy
- Complete P1–P4 defaults before publication
- No overlapping active effective windows for identical context
- Response not greater than resolution
- Exactly one default template after the operation
- No partial commit

Export must use business codes and contain enough information for a valid round-trip import.

## 8. Backend and API work

### 8.1 Search APIs

Standardize a paginated catalog response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 1247,
  "has_more": true
}
```

Add stable search, sort, active-state filters, and `exclude_ids` for small selections. For large selections, use the selection-expression contract rather than an unbounded exclusion query string.

### 8.2 Bulk client linking

Add preview and apply endpoints, for example:

```text
POST /contracts/{id}/clients/selection/preview
PUT  /contracts/{id}/clients/selection
```

Both endpoints accept the same selection expression. Apply must verify the preview token or configuration version to avoid saving against stale search results.

### 8.3 Bulk coverage

Add:

```text
POST   /contracts/{id}/coverage/bulk/preview
POST   /contracts/{id}/coverage/bulk
PATCH  /contracts/{id}/coverage/bulk
DELETE /contracts/{id}/coverage/bulk
```

Enforce contract-client eligibility, module ownership, duplicate normalization, authorization, and audit logging in the service layer.

### 8.4 SLA master data

Add endpoints for:

- Template list/search/detail
- Create and clone
- Draft creation and update
- Target matrix bulk update
- Validate and publish
- Retire and set default
- Usage/affected-contract preview
- Import template download
- Import validation, preview, apply, and error download
- Export
- Resolver simulation

Use optimistic concurrency/version fields for all master-data writes.

## 9. Data model and migration

Choose names after reviewing current `sla_policies` usage. Prefer evolving existing records over creating a competing policy system.

Likely additions:

```text
sla_templates or evolved sla_policies
  logical template identity and default flag

sla_policy_versions
  template_id, version_number, lifecycle_status, calendar and behavior snapshot

sla_targets
  version_id or equivalent immutable policy-version reference

contracts
  sla_template_id plus follow-latest/pinned-version behavior

sla_import_jobs
  file metadata, checksum, status, counts, actor, timestamps
```

Migration requirements:

1. Create version records for every existing policy.
2. Move or associate existing targets with their generated version.
3. Preserve existing contract associations.
4. Preserve all target and policy IDs required by historical clocks, or migrate references without losing evidence.
5. Backfill priority-only targets as explicit defaults.
6. Detect policies missing one or more default priorities and report them; do not invent durations.
7. Add filtered uniqueness enforcing one active system default on SQL Server.
8. Add context/effective-window indexes needed by the resolver.
9. Keep migration idempotence and SQL Server compatibility.
10. Update database compatibility checks.

## 10. Permissions and audit

Define or confirm permissions:

```text
sla_template.view
sla_template.manage
sla_template.publish
sla_template.import
sla_template.set_default
contract.clients.manage
contract.coverage.bulk_manage
```

Audit:

- Before/after template metadata
- Draft creation and publication
- Default-template change
- Contract policy reassignment
- Bulk client and coverage selection expression plus resolved count
- Import filename, checksum, mode, result, and actor
- Resolver simulation is read-only and need not be audited unless required by governance

## 11. Frontend work

Create shared components rather than implementing contract-only controls:

```text
PaginatedAutocomplete
BulkSelectionPanel
SelectionSummary
CoverageRuleBuilder
SlaTargetMatrix
SlaMatchSimulator
ImportPreviewDialog
ChangeImpactDialog
```

Contract workspace improvements:

- Persistent unsaved-change warning
- Draft/save/publish distinction
- Per-tab validation badges
- Searchable linked-client selector
- Coverage table filters and row selection
- Bulk operations with progress/error feedback
- SLA template selection with version and inheritance indicators
- Final activation review

SLA master-data page:

- Search/filter templates
- Default, active, draft, and published badges
- Usage counts
- Matrix editor
- Version history and comparison
- Import/export actions
- Publish-impact confirmation
- Resolver simulator accepting contract, product, module, service, and priority

## 12. Delivery phases

### Phase 0 — Decisions and safeguards

Status: `READY`  
Priority: Critical

- Approve SLA precedence and required P1–P4 defaults.
- Decide follow-latest versus pinned contract behavior.
- Approve initial template durations or leave templates unseeded pending business input.
- Define status-to-clock lifecycle rules.
- Capture regression fixtures for current contracts and clocks.

Exit criteria: business rules are signed off and represented as executable test cases.

### Phase 1 — Resolver correction

Status: `READY`  
Priority: Critical

- Fix service-specific-to-default fallback.
- Centralize deterministic matching.
- Return structured match evidence.
- Add unit, integration, and regression tests.

Exit criteria: unrelated services reliably use the priority default while exact service overrides win.

### Phase 2 — Search and client-selection foundation

Status: `READY`  
Priority: High

- Standard paginated catalog APIs.
- Shared searchable selector.
- Two-panel linked-client UI.
- Select all matching with preview/apply semantics.
- Remove the functional 50-client limit.

Exit criteria: every matching client is reachable and bulk selection remains correct across pages.

### Phase 3 — SLA master data and versioning

Status: `PLANNED`  
Priority: High

- Migrations and backfill.
- Master-data APIs and permissions.
- Default template enforcement.
- Draft/publish/version workflow.
- Matrix editor and simulator.

Exit criteria: an administrator can safely publish an editable template and link contracts without changing historical evidence.

### Phase 4 — SLA import/export

Status: `PLANNED`  
Priority: High

- Versioned XLSX/CSV format.
- Parse, validate, preview, apply, audit, and error-report workflow.
- Round-trip export tests.

Exit criteria: a valid export can be imported into a clean compatible environment with equivalent resolved targets.

### Phase 5 — Bulk coverage and guided contract workflow

Status: `PLANNED`  
Priority: Medium

- Searchable dependent catalogs.
- Coverage builder and preview.
- Bulk edit/remove.
- Guided draft and activation review.
- Reusable coverage bundles if approved.

Exit criteria: a large multi-client contract can be configured without repetitive one-rule-at-a-time entry.

### Phase 6 — Rollout and cleanup

Status: `PLANNED`  
Priority: Medium

- Shadow-compare old and new resolution on production-like data.
- Pilot with contract administrators.
- Measure task completion time and error rate.
- Publish operational documentation.
- Remove superseded UI only after adoption and rollback window.

## 13. Testing strategy

### 13.1 Resolver tests

- Default P1–P4 targets work for every service.
- Exact service + priority overrides default.
- A service P1 override does not affect P2–P4.
- An override for service A does not block fallback for service B.
- Product/module/service specificity follows documented precedence.
- Effective dates and inactive versions are respected.
- Ambiguous equal-specificity targets are prevented at write time.
- Existing clock snapshots do not change after publication.

### 13.2 Selection tests

- Search finds a client beyond the first 50.
- Paging never duplicates or drops selections.
- Selected clients disappear from available results.
- Search-selected-clear sequences retain correct state.
- Select all matching honors server filters.
- Exclusions from all-matching are respected.
- Concurrent client changes trigger stale-preview protection.
- Keyboard and screen-reader flows are usable.

### 13.3 Coverage tests

- Multi-product/module/service preview is deterministic.
- Broad rules are normalized without changing meaning.
- Duplicate and conflicting include/exclude rules are reported.
- Invalid product/module relationships fail atomically.
- Bulk deletion removes only selected rules.

### 13.4 Import tests

- Valid XLSX and CSV create equivalent drafts.
- Unknown codes, duplicates, invalid ranges, and missing defaults are reported by row.
- No partial data persists after any failure.
- Formula and macro content is rejected or safely ignored according to the parser policy.
- Export/import round trip preserves semantic configuration.
- Replayed import is idempotent or rejected predictably according to mode.

### 13.5 Performance tests

- Search response remains acceptable at expected production catalog size.
- Selecting all matching does not transfer all IDs to the browser.
- Resolver queries use bounded indexed lookups.
- Publishing/importing large matrices completes within the agreed operational timeout.

## 14. Acceptance criteria

The program is complete when:

1. Users can search and select any client regardless of total client count.
2. Selected clients no longer appear in available results.
3. Users can select visible results or all server-side matches and can remove selections in bulk.
4. Product, module, service, and related large catalogs are searchable.
5. Contract coverage can be created and maintained in bulk with a preview.
6. Administrators can create, edit through drafts, clone, publish, retire, and default SLA templates.
7. Every published SLA template has complete default P1–P4 targets.
8. Service-specific priority targets override defaults only for matching tickets.
9. Unconfigured services fall back to the correct default priority target.
10. Ticket status controls clock lifecycle independently of target selection.
11. SLA templates can be imported and exported with transactional validation and actionable errors.
12. Existing contracts and historical SLA clocks retain correct behavior and evidence.
13. Permissions and audits cover all master-data and bulk operations.
14. Automated tests cover precedence, fallback, versioning, imports, selection persistence, and rollback-sensitive behavior.

## 15. Rollout and rollback

1. Deploy schema and read-compatible backend changes first.
2. Backfill existing policies into versioned records.
3. Run a compatibility report for missing defaults and ambiguous contexts.
4. Enable resolver shadow comparison and investigate every mismatch.
5. Release searchable selectors and bulk APIs behind a feature flag.
6. Pilot SLA master data with administrators.
7. Enable governed resolution only after comparison acceptance.
8. Retain the old read path during the rollback window.

Rollback must disable the new feature paths without deleting newly captured master data. Never downgrade by removing version or audit records while contracts or clocks reference them.

## 16. Documentation deliverables

- SLA matching and precedence guide
- SLA template administrator guide
- Import workbook instructions and data dictionary
- Contract bulk-selection guide
- Coverage-builder guide
- Publication and rollback runbook
- Troubleshooting guide for match reasons and import failures
- Release notes and migration verification checklist

