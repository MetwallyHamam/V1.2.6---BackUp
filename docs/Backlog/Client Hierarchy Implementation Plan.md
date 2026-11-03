# Client Hierarchy Implementation Plan

Status: Deferred for later implementation  
Prepared: 2026-08-16  
Risk: Critical cross-system change

## 1. Objective

Add an unlimited-depth organizational hierarchy for CRM clients while preserving exact operational ownership.

Example:

```text
UHIA
└── UHIA - Luxor
    ├── Karnak
    └── Tiba
```

Every node remains a complete client account with its own tickets, branches, contacts, installations, operations, contracts, portal access, dashboards, and reports. A ticket or operation always belongs to the exact affected client. Hierarchy is used only for navigation, explicitly authorized visibility, explicitly configured contract inheritance, and aggregate reporting.

Standalone clients with no parent or children must retain current behavior without additional configuration.

## 2. Non-negotiable rules

1. Organizational hierarchy does not automatically grant portal access.
2. Organizational hierarchy does not automatically extend contract coverage.
3. Parent contacts, branches, and installations are not automatically shared with children.
4. Tickets remain assigned to the exact affected client, never rewritten to the hierarchy root.
5. Historical tickets retain their selected contract and SLA evidence after hierarchy changes.
6. Existing clients migrate as root clients and continue working unchanged.
7. Circular parent relationships must be impossible.
8. Aggregate results must remain auditable by showing the owning client for every drill-down row.

## 3. Current code findings

The current system uses exact `client_id` matching throughout tickets, internal operations, dashboards, reports, installations, and portal authorization.

Contracts already support:

- An owning client through `contracts.client_id`.
- Explicit eligible clients through `contract_client_links`.
- Per-coverage client targeting through `contract_coverage_clients`.
- Global applicability through `applies_to_all_clients`.

Entitlement currently considers only the exact owning client, explicitly linked clients, and global contracts. The client portal currently creates tickets using the first ID in `client_ids`, which must be corrected before a portal user can access multiple hierarchy clients.

## 4. Data model

### 4.1 Client hierarchy

Add to `clients`:

```text
parent_client_id  BIGINT NULL FK clients.id
```

Add an index on `parent_client_id`. Configure the foreign key with restrictive deletion behavior so a parent with children cannot be deleted accidentally.

Do not store a materialized hierarchy path initially. Use centralized traversal functions and revisit a closure table only if production volume proves recursive traversal insufficient.

### 4.2 Contract hierarchy scope

Add an explicit contract field:

```text
hierarchy_scope:
  OWNER_ONLY
  DIRECT_CHILDREN
  ALL_DESCENDANTS
```

Default all existing contracts to `OWNER_ONLY`.

Explicit `contract_client_links` remain supported. They cover intentionally selected clients outside or inside the hierarchy. `applies_to_all_clients` remains the global option.

Contract eligibility and coverage-row applicability remain separate decisions:

1. Is the contract eligible for the affected client?
2. Does a matching coverage row apply to the affected client?
3. Does it match product, module, branch, environment, service, and ticket type?
4. Which contract and SLA win according to deterministic precedence?

### 4.3 Portal hierarchy scope

Add an explicit scope mode to user-client assignments rather than expanding every parent assignment silently:

```text
CLIENT_ONLY
CLIENT_AND_DIRECT_CHILDREN
CLIENT_AND_ALL_DESCENDANTS
```

Existing assignments migrate to `CLIENT_ONLY`.

Branch scopes remain exact. A user authorized for descendant clients must still be restricted to explicitly authorized branches when branch restrictions are configured.

## 5. Shared hierarchy service

Create one backend hierarchy service used by every module. Required operations:

```text
get_ancestors(client_id)
get_descendants(client_id, depth=None, include_self=False)
get_scope_ids(client_id, scope_mode, include_self=True)
get_client_path(client_id)
is_descendant(ancestor_id, candidate_id)
validate_parent_change(client_id, parent_client_id)
```

Requirements:

- Detect cycles before writes.
- Handle missing and inactive nodes deliberately.
- Apply a defensive maximum traversal depth.
- Return deterministic ordering.
- Avoid module-specific copies of recursive logic.
- Support SQLite and SQL Server consistently; application-level traversal is acceptable initially.

## 6. Client management behavior

Add an optional `Parent client` selector to create/edit client screens.

Validation:

- A client cannot parent itself.
- A descendant cannot become an ancestor's parent.
- A missing or invalid parent is rejected.
- Parent changes are audited with old and new parent IDs and paths.
- Deleting a client with children is blocked.
- Deactivating a parent does not automatically deactivate descendants.

Client profile additions:

- Breadcrumb path.
- Parent link.
- Expandable child tree.
- Direct and total descendant counts.
- Clickable navigation to every permitted node.
- Scope selector shown only when descendants exist: `This client`, `Direct children`, `Full hierarchy`.

## 7. Ticket creation behavior

### 7.1 Internal creation

Replace the flat client label with a searchable hierarchy path, for example:

```text
UHIA > UHIA - Luxor > Karnak
```

After selecting the affected client, reload only that client's:

- Branches and sites.
- Contacts and callers.
- Installations.
- Ticket form policies and defaults.
- Eligible contracts and contract-derived catalog.

The ticket stores the exact affected `client_id`.

### 7.2 Contract selection precedence

Evaluate candidates in this conceptual order while preserving existing coverage specificity, exclusions, contract-type precedence, shared-default behavior, and ambiguity protection:

1. Exact child-owned contract.
2. Contract explicitly linked to the child.
3. Nearest eligible ancestor contract.
4. More distant eligible ancestor contract.
5. Shared/global default.

Do not silently choose between equally eligible contracts. Require explicit selection when the existing governance rules consider the result ambiguous.

Show the source clearly:

```text
Contract: UHIA-LUXOR-2026
Owner: UHIA - Luxor
Affected client: Karnak
Applicability: Covers all descendants
```

### 7.3 Changing a ticket's client

Retain the existing permission requirement and additionally:

- Require an audit/change reason.
- Clear incompatible branch and requester values.
- Revalidate installations and client-specific context.
- Re-run entitlement and contract selection.
- Rebuild the applicable SLA lifecycle according to the approved change policy.
- Audit old/new client, contract, entitlement, and SLA decisions.

## 8. Client Portal behavior

### 8.1 Single-client user

When effective scope contains one client, select it automatically and hide the affected-client selector. This preserves current standalone-client behavior.

### 8.2 Hierarchy manager

When effective scope contains multiple clients, require an `Affected client` selection. Only authorized hierarchy nodes appear.

Changing the affected client must reload:

- Portal contract catalog.
- Contract candidates.
- Covered products, modules, and services.
- Branches available to the user.
- Allowed requester/contact context.

Remove all use of `client_ids[0]` as the implicit ticket client.

Backend enforcement is mandatory:

- Submitted client is in calculated effective scope.
- Branch belongs to the submitted client and is within branch scope.
- Requester belongs to the submitted client.
- Contract is eligible for the submitted client.
- Coverage applies to the submitted client's ticket context.

Portal ticket lists and reports may aggregate authorized clients, but must show the affected client and hierarchy path.

## 9. Contract product coverage example

One Luxor contract may cover its descendants while giving each child different products:

```text
Contract: UHIA-LUXOR-2026
Owner: UHIA - Luxor
Hierarchy scope: ALL_DESCENDANTS

Coverage row 1:
  Product: Product A
  Applicable clients: Karnak

Coverage row 2:
  Product: Product B
  Applicable clients: Tiba

Coverage row 3:
  Product: Common Product
  Applicable clients: all eligible clients for the contract
```

Ticket behavior:

- Karnak sees Product A and shared covered products.
- Tiba sees Product B and shared covered products.
- A product not covered for the affected client is hidden or marked as requiring approval according to `ticket_catalog_visibility`.

An empty coverage client list currently means the row applies to all clients eligible for that contract. Preserve and document this meaning.

## 10. SLA behavior

SLA continues to follow the contract selected by entitlement.

Preserve:

- Contract SLA policy and business calendar.
- Product/module/service-specific SLA target resolution.
- Coverage exclusion precedence.
- Included request limit behavior.
- Shadow/enforced feature-policy behavior.
- Entitlement approval and override workflows.

If Karnak and Tiba use different products under the same Luxor contract, product-scoped targets can provide different SLA targets. If the same product requires different targets per child, choose one of these explicitly during detailed design:

1. Add client scope to SLA targets, with careful precedence rules.
2. Use separate child contracts/SLA policies.

Prefer separate contracts when commercial terms, calendars, limits, or obligations materially differ. Do not add client-scoped SLA targets without a dedicated ambiguity and precedence review.

## 11. Products and installations

Product, module, service, and environment masters remain global catalogs.

Installations remain owned by the exact client and are not inherited automatically. A Karnak ticket uses Karnak installations even when entitlement comes from a Luxor contract.

Hierarchy profiles may aggregate descendant installations, but every result must display its owning client.

Contract-covered product availability and installed-product availability are separate facts. The UI should distinguish `contract covered` from `installed at this client` where both are relevant.

## 12. Internal operations

Internal operations retain one exact optional `client_id`.

Add:

- Hierarchical client labels.
- `include_descendants`/scope filtering for authorized aggregate views.
- Owning-client columns in lists and exports.
- Hierarchy aggregation in client profiles.

An operation recorded for Karnak remains a Karnak operation but appears in authorized Luxor/UHIA aggregate reporting.

## 13. Dashboards and reports

Replace ad hoc exact-filter expansion with centralized scope resolution.

Every hierarchy-aware endpoint should accept a deliberate scope, for example:

```text
scope=SELF
scope=DIRECT_CHILDREN
scope=FULL_HIERARCHY
```

Default to `SELF` for backward compatibility.

Apply resolved client IDs consistently to:

- Tickets and SLA calculations.
- Contracts and entitlement summaries.
- Internal operations and working hours.
- Satisfaction results.
- Installations, locations, and branches.
- Management dashboards.
- Client profile preview.
- Word and Excel exports.
- Drill-down URLs and evidence tables.

Aggregate displays must include:

- Total hierarchy metrics.
- Per-client breakdown.
- Client path on evidence rows.
- Scope and included-client disclosure in exports.

Do not sum already aggregated parent values with child values. Aggregate from source records selected by resolved client IDs to avoid double counting.

## 14. Imports, integrations, and email

Review and update all client lookups in:

- Excel import templates and validation.
- Integration/API client scopes.
- Outlook/email-to-ticket client matching.
- Project handovers.
- Feature policies resolved by client.
- Notification filters and recipient visibility.
- Saved ticket views and exported filters.

Imports should accept an optional parent client code and reject missing parents or cycles. Client codes remain globally unique and should be preferred over names for hierarchy import references.

Automated ticket sources must continue resolving the exact affected client; they must not default to the hierarchy root.

## 15. API changes

Likely additions:

```text
GET  /clients/{id}/hierarchy
GET  /clients/{id}/ancestors
GET  /clients/{id}/descendants
PATCH /clients/{id}              parent_client_id
```

Extend client read models with:

- `parent_client_id`
- `parent_client_name`
- `hierarchy_path`
- `direct_child_count`
- `descendant_count`
- `has_children`

Do not recursively embed an unlimited child tree in every `/clients` response. Provide a dedicated hierarchy endpoint and compact metadata in lists.

Update portal catalog and entitlement candidate APIs to require or explicitly resolve the selected affected client when the user has multiple authorized clients.

## 16. Database migration and compatibility

Create the next Alembic revision after the current head.

Migration steps:

1. Add nullable `clients.parent_client_id` and index.
2. Add the self-referencing foreign key using SQL Server-compatible naming.
3. Add `contracts.hierarchy_scope` with `OWNER_ONLY` default.
4. Add portal user-client hierarchy scope storage with `CLIENT_ONLY` default.
5. Backfill all existing rows to backward-compatible defaults.
6. Add constraints/checks supported consistently by SQLite and SQL Server; enforce remaining cycle rules in application code.

Test both clean installation and upgrade from an existing populated database.

Deletion and destructive client cleanup code must be updated so a client with children cannot be removed and hierarchy references cannot be orphaned.

## 17. Authorization and privacy tests

Required negative tests:

- Karnak-only user cannot view Tiba tickets.
- Luxor hierarchy manager can view only configured descendants.
- A parent assignment using `CLIENT_ONLY` does not include children.
- A user cannot submit a client ID outside effective scope.
- A user cannot submit a sibling branch or requester ID.
- Reparenting does not silently expand an existing portal assignment unless its explicit scope mode says so.
- Reparenting does not silently make an `OWNER_ONLY` contract applicable.
- Unauthorized hierarchy nodes are excluded from client trees and search results.

## 18. Functional test matrix

### Hierarchy

- Create root, child, and grandchild.
- Move a subtree between parents.
- Reject self-parent and indirect cycles.
- Block deletion of a parent with children.
- Preserve standalone-client behavior.

### Tickets

- Create an exact-child ticket.
- Filter branches and callers to the selected child.
- Resolve an exact child contract before an ancestor contract.
- Resolve the nearest applicable ancestor.
- Detect equal-precedence ambiguity.
- Revalidate context when changing client.

### Contract and products

- Luxor contract applies to Karnak and Tiba through `ALL_DESCENDANTS`.
- Product A applies only to Karnak.
- Product B applies only to Tiba.
- Shared coverage applies to both.
- Explicit exclusion overrides an equally specific inclusion.
- `OWNER_ONLY` does not leak to descendants.

### Portal

- Single-client portal flow remains unchanged.
- Multi-client manager must select the affected client.
- Catalog and candidates reload after selection.
- Tampered client, branch, contact, or contract IDs are rejected.
- Portal lists aggregate only authorized clients.

### Dashboards and reports

- `SELF` matches current exact-client totals.
- `FULL_HIERARCHY` includes all descendants once.
- Direct-child scope excludes grandchildren.
- Per-client totals reconcile to aggregate totals.
- Drill-down records reconcile to displayed metrics.
- Word and Excel exports state the selected scope.

### Migration

- Clean SQLite installation.
- Upgrade populated SQLite database.
- SQL Server migration rehearsal.
- Downgrade safety where supported.

## 19. Delivery phases

### Phase 1: Hierarchy foundation

- Migration and model changes.
- Shared hierarchy service.
- Client CRUD validation and audit.
- Tree, breadcrumb, and profile navigation.
- Standalone-client regression tests.

### Phase 2: Ticket and portal authorization

- Hierarchical internal selector.
- Explicit portal hierarchy scopes.
- Affected-client portal selector.
- Branch/contact isolation.
- Removal of first-client assumptions.

### Phase 3: Contract and SLA inheritance

- Contract hierarchy scope.
- Ancestor candidate resolution.
- Client-specific coverage behavior.
- Precedence, exclusion, ambiguity, and snapshot tests.

### Phase 4: Products, installations, and operations

- Exact-owner displays.
- Hierarchy filters and aggregate views.
- Product coverage versus installation indicators.

### Phase 5: Dashboards, reports, exports, and integrations

- Shared scope filtering.
- Aggregate and comparative visualizations.
- Evidence/drill-down reconciliation.
- Import, email, integration, and notification review.

## 20. Release controls

- Place hierarchy behavior behind a feature flag until migrations and authorization tests pass.
- Deploy schema changes before enabling hierarchy configuration.
- Keep all contracts and portal scopes on backward-compatible defaults initially.
- Enable hierarchy for a controlled UHIA pilot first.
- Configure the Luxor contract and Karnak/Tiba product coverage explicitly.
- Run entitlement previews before allowing portal ticket creation.
- Compare pre-release and post-release dashboard totals for standalone clients.
- Maintain a rollback plan that disables the feature without deleting hierarchy data.

## 21. Definition of done

The change is complete only when:

- Standalone clients behave exactly as before.
- Unlimited-depth client hierarchy is manageable without cycles.
- Every ticket retains an exact affected client.
- Portal access is explicit and enforced server-side.
- Parent contracts cover descendants only when configured.
- Karnak and Tiba can receive different products under one Luxor contract.
- SLA selection remains deterministic and auditable.
- Operations, dashboards, profiles, reports, and exports support deliberate hierarchy scopes.
- Aggregate totals reconcile with client-level evidence.
- SQLite and SQL Server migrations and regression suites pass.
- Security tests prove sibling and unauthorized descendant isolation.

## 22. Planning estimate

This is a multi-phase critical change. Implement and verify it in separate bounded sessions rather than one large unreviewed patch. Before work begins, confirm the contract hierarchy rules, portal assignment scope UX, and whether client-specific SLA targets are required for the same product.
