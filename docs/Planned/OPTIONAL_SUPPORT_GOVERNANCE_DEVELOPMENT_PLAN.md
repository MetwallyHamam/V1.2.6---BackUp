# Optional Support Governance Development Plan

Last updated: 2026-08-12  
Plan owner: Millensys Support Hub  
Overall status: In progress  
Current phase: P4 — Unified entitlement and approval workflow

## Implementation tracking legend

Use these flags for every implementation item:

| Flag | Meaning |
|---|---|
| `[x]` | Implemented and verified |
| `[~]` | Currently in progress; only one item should normally have this flag |
| `[ ]` | Not started |
| `[!]` | Blocked; the reason must be recorded in the Stop/Resume Log |
| `[-]` | Intentionally deferred or removed from scope |

`NEXT` identifies the exact task where implementation should resume. Move the marker whenever a task is completed, blocked, or deliberately deferred.

## Resume from here

> **NEXT: P8.16 — Run the restricted live Microsoft 365 mailbox pilot in `SHADOW`, then record tenant security sign-off before switching any Outlook feature to `ENFORCED`.**

Current implementation state:

- Planning and architecture are complete.
- P1 is complete and packaged as standalone release 1.9.0.
- Latest released application before this plan: Support Hub 1.8.3.
- Current database head before this plan: `0071_knowledge_resources`.
- P1 migration is `0072_feature_policy_control`.
- P2 is complete and packaged as standalone release 1.10.0.
- P3 is complete and packaged as standalone release 1.11.0.

## Executable implementation checklist

### P1 — Feature & Policy Control foundation

- [x] **P1.1 Data-model design:** confirmed feature definitions, policy overrides, versions, scopes, effective dates, modes, validation, uniqueness rules, and audit fields.
- [x] **P1.2 Migration:** added `0072_feature_policy_control` with tables, indexes, constraints, defaults, and compatibility validation.
- [x] **P1.3 Domain service:** implemented product/service → contract → client → system → catalog fallback resolution.
- [x] **P1.4 Operating modes:** implemented typed `OFF`, `SHADOW`, and `ENFORCED` results.
- [x] **P1.5 Policy snapshots:** effective results contain source scope/key, policy ID/version, configuration, mode, and evaluation time for later ticket/event snapshots.
- [-] **P1.6 Cache:** deferred until the first high-volume consumer; indexed authoritative reads avoid stale administrative policy during the foundation phase.
- [x] **P1.7 Permissions:** added separate `feature_policy.view` and `feature_policy.manage` permissions.
- [x] **P1.8 Admin APIs:** added catalog, policies, effective preview, create/update, validation, version conflict, and removal endpoints.
- [x] **P1.9 Site Settings UI:** added Feature & Policy Control, scope editor, mode/expiry, inheritance display, removal, and effective preview.
- [x] **P1.10 Audit:** records create/update/delete values, operator, reason, version, and effective dates.
- [x] **P1.11 Seed:** seeds ten stable feature keys without overwriting configured modes.
- [x] **P1.12 Automated tests:** resolver/API tests pass; full suite passes 133 tests.
- [x] **P1.13 Upgrade verification:** clean migration and `0071` → `0072` upgrade plus seed both succeeded.
- [x] **P1.14 Documentation:** added `FEATURE_POLICY_CONTROL.md` with modes, resolution, security, deployment, and recovery.
- [x] **P1.15 Release gate:** standalone v1.9.0 verified with runtime, revision manifest, and SHA-256.

### P2 — Contract types and governance

- [x] **P2.1 Data-model design:** contract-type catalog, defaults, precedence, lifecycle rules, and historical behavior.
- [x] **P2.2 Migration:** added `0073_contract_types`, seeded system types, and safely assigned existing contracts to `LEGACY`.
- [x] **P2.3 Contract service:** effective-date candidates, coverage specificity, configured type precedence, safe exclusion priority, and equal-rank ambiguity detection are implemented by feature mode.
- [x] **P2.4 APIs:** type management, defaults preview, and governed applicability validation are implemented.
- [x] **P2.5 Contract UI:** type management, create/edit selection, effective-mode display, and inherited-default/applicability explanations are implemented.
- [x] **P2.6 Compatibility:** current generic contract behavior is preserved when the feature is `OFF` or `SHADOW`.
- [x] **P2.7 Tests:** catalog permissions/audit, feature modes, precedence, ambiguity, defaults preview, and warranty-to-support transition are covered; full suite passes 139 tests.
- [x] **P2.8 Release gate:** migration rehearsals, documentation, standalone runtime/manifest verification, and SHA-256 validation passed for v1.10.0.

### P3 — Product-scoped SLA and multiple-contract resolution

- [x] **P3.1 Target design:** canonical target contexts, six-level specificity, explicit fallback, half-open effective dates, versions, and uniqueness rules are finalized.
- [x] **P3.2 Migration:** `0074_product_scoped_sla` adds product/module targets, effective dates, versions, canonical uniqueness, and clock snapshots while backfilling existing meaning.
- [x] **P3.3 Resolver:** the approved six-level matching order returns traceable match evidence and prevents cross-product leakage in `ENFORCED`; `OFF`/`SHADOW` retain current clocks.
- [x] **P3.4 Contract candidates:** candidate API filters by client, product/service coverage, dates, status, and applicability, with portal scope enforcement.
- [x] **P3.5 Ambiguity:** internal and portal forms auto-select one valid contract and require explicit choice for multiple valid contracts; server validates the chosen contract.
- [x] **P3.6 SLA snapshot:** new clocks persist agreed response/resolution minutes, contract, target, calendar, policy version, warning threshold, and calculation version.
- [x] **P3.7 Shadow evaluation:** `SHADOW` persists legacy/governed targets, minutes, match reason, and outcome without changing operational clocks; per-ticket and review-list APIs are available.
- [x] **P3.8 Contract UI:** governed editor configures product/module/service/priority targets, effective windows, explicit fallbacks, versions, canonical keys, five match tiers, and validation errors; legacy service editor remains available during adoption.
- [x] **P3.9 Ticket UI:** internal and portal details show product, service, governing contract, targets, results, immutable agreement identifiers, and persisted match/no-match evidence.
- [x] **P3.10 Reporting consistency:** shared ticket evidence uses immutable clock target/calendar snapshots; grid and CSV expose target, actual, balance, state, match reason, target ID, policy version, and calendar ID.
- [x] **P3.11 Tests:** leakage prevention, specificity, fallback, ambiguity, snapshots, historical stability, and performance.
- [x] **P3.12 Release gate:** shadow report review, migration rehearsal, documentation, and standalone release candidate.

### P4 — Unified entitlement and approval workflow

- [x] **P4.1 Decision model:** defined stable reason/action codes, immutable evidence output, policy identity/version, safe defaults, feature-mode behavior, and deterministic precedence.
- [x] **P4.2 Approval model/migration:** migration `0077` adds idempotent requests, decisions, approver groups, deadlines, immutable status history, comments, and audit.
- [ ] **P4.3 Entitlement engine:** evaluate inactive/expired/uncovered/no-SLA/limit/ambiguity conditions consistently.
- [ ] **P4.4 Policy configuration:** configure Allow, Warn, Require approval, or Block by scope and condition.
- [ ] **P4.5 Internal submission:** confirmation, justification, pending approval, retry protection, and authorized override.
- [ ] **P4.6 Portal submission:** create transparent pending requests without client-side bypass.
- [ ] **P4.7 Approval workspace:** queues, detail, approve/reject, bulk-safe filters, deadlines, and escalation.
- [ ] **P4.8 Notifications:** request, reminder, decision, expiry, and escalation events.
- [ ] **P4.9 Audit/security:** immutable decision history and scoped approver authorization.
- [ ] **P4.10 Tests:** every condition/action, concurrency, duplicate submission, authorization, portal parity, and `OFF` fallback.
- [ ] **P4.11 Release gate:** operational procedure, migration rehearsal, and standalone release candidate.

### P5 — Dynamic support tiers and sequential escalation

- [ ] **P5.1 Tier design:** ordered tier catalog, rank, next tier, terminal destination, and active state.
- [ ] **P5.2 Assignment design/migration:** user-tier assignments with optional team/product/service scope and effective dates.
- [ ] **P5.3 Eligibility service:** determine a user's effective tiers and valid next-tier recipients.
- [ ] **P5.4 Sequential escalation:** enforce the configured path only in `ENFORCED` mode.
- [ ] **P5.5 Shadow escalation:** record which candidates/path would differ without restricting the current workflow.
- [ ] **P5.6 Emergency override:** separate permission, mandatory reason, audit, and notification.
- [ ] **P5.7 User administration UI:** assign tiers and expertise scopes.
- [ ] **P5.8 Escalation UI:** show current tier, next tier, eligible recipients, terminal action, and override explanation.
- [ ] **P5.9 History:** store origin/destination tiers, users, reason, policy version, and time.
- [ ] **P5.10 Tests:** sequential paths, scope, inactive tiers/users, terminal levels, override, `OFF`, and concurrent escalation.
- [ ] **P5.11 Release gate:** role-mapping review, documentation, and standalone release candidate.

### P6 — Tier-based routing and ticket visibility

- [ ] **P6.1 Ownership model/migration:** add ticket owning tier and historical/default handling.
- [ ] **P6.2 Routing engine:** product/service expertise first, followed by configured fallbacks.
- [ ] **P6.3 Visibility policy:** exact, same-and-lower, scoped expertise, management, audit, and collaborator rules.
- [ ] **P6.4 Query enforcement:** apply visibility to API lists/details, search, relations, bulk actions, and attachments.
- [ ] **P6.5 Reporting enforcement:** apply identical rules to exports, dashboards, counts, drill-down, and saved views.
- [ ] **P6.6 UI:** show ownership tier, routing reason, and allowed tier changes.
- [ ] **P6.7 Shadow access report:** show users who would gain or lose access before enforcement.
- [ ] **P6.8 Security tests:** prevent direct-ID, export, dashboard, websocket, notification, and attachment bypasses.
- [ ] **P6.9 Performance tests:** validate scoped ticket queries and dashboards under production-like volume.
- [ ] **P6.10 Release gate:** access-impact approval, documentation, and standalone release candidate.

### P7 — Notification policy engine

- [ ] **P7.1 Rule model/migration:** event, conditions, recipients, channels, severity, mandatory state, mode, and scope.
- [ ] **P7.2 Recipient resolver:** user, role, tier, team, manager, approver, product owner, requester, and client contact.
- [ ] **P7.3 Event integration:** publish stable events without duplicating existing notifications.
- [ ] **P7.4 Template engine:** safe variables, previews, validation, localization readiness, and HTML/text output.
- [ ] **P7.5 Delivery controls:** deduplication, retries, failure status, mandatory rules, and user preferences.
- [ ] **P7.6 Shadow simulation:** record intended recipients/channels without sending.
- [ ] **P7.7 Configuration UI:** rule builder, scope, preview, test, enable/disable, and history.
- [ ] **P7.8 Monitoring UI:** queued, sent, failed, retried, and suppressed deliveries.
- [ ] **P7.9 Tests:** recipient correctness, privacy, mandatory behavior, deduplication, retry, shadow, and scale.
- [ ] **P7.10 Release gate:** template review, operational documentation, and standalone release candidate.

### P8 — Microsoft Outlook integration

- [x] **P8.1 Azure prerequisites:** documented tenant app registration, least-privilege Graph permissions, mailbox access restriction, consent, webhook security, secrets, and operational controls.
- [x] **P8.2 Secure settings model:** protected deployment secrets, credential-state reporting, durable mailbox/allow/block/unknown-sender/attachment policy, versioned templates, and independent feature modes.
- [x] **P8.3 Email Integration UI:** Configuration, Templates, and Health tabs provide connection status/test, allowlists, attachment defaults, templates, subscription lifecycle controls, health, and manual synchronization.
- [x] **P8.4 Graph client:** application-token acquisition/cache, bounded timeouts, throttling/transient retries, per-request correlation, and sanitized errors.
- [x] **P8.5 Subscription management:** create, validate, renew, automatic scheduled renewal, reauthorize/recreate status, lifecycle callbacks, and expiry/health.
- [x] **P8.6 Webhook:** validates Graph challenges and client state with constant-time comparison, honors `OFF`, and enqueues notifications quickly and idempotently.
- [x] **P8.7 Delta recovery:** bounded manual delta reconciliation persists the cursor and queues missed messages without duplicates.
- [x] **P8.8 Sender resolution:** deterministic allow/block rules, exact active contact/client mapping, ambiguity quarantine, and configurable unknown-sender behavior.
- [x] **P8.9 Ticket creation:** normalized content, governed ticket service, validated attachments, idempotent P4 approval handoff, retry/dead-letter behavior, and exactly-once boundary.
- [x] **P8.10 Threading:** conversation identity maps replies to one existing ticket and appends one public email comment.
- [x] **P8.11 Loop protection:** ignores the Support mailbox, automatic replies, delivery reports, header-marked generated messages, and repeated Graph events.
- [x] **P8.12 Acknowledgement:** configurable versioned template and feature policy enqueue acknowledgement only after successful ticket commit.
- [x] **P8.13 Status email:** configurable in-progress, pending, resolved, closed, and reopened templates use durable Graph delivery and threading.
- [x] **P8.14 Operations:** inbound/outbound queues, retries, dead-letter state, replay, synchronization/health, last success/error, audit, and administrative APIs.
- [x] **P8.15 Tests:** Graph validation, deduplication, sender rules, loop protection, approvals, entitlements, migrations, and full regression passed; live Graph behavior is isolated behind the staging gate.
- [ ] **P8.16 Live staging test:** restricted mailbox pilot with `SHADOW`, then controlled `ENFORCED` validation.
- [~] **P8.17 Release gate:** connection/recovery/security documentation and standalone release candidate are complete; tenant security sign-off follows P8.16.

### P9 — Integrated verification and controlled rollout

- [ ] **P9.1 Full regression:** authentication, clients, contracts, tickets, portal, SLA, dashboard, deletion, handover, knowledge, notifications, and reports.
- [ ] **P9.2 Upgrade rehearsal:** verified production-like backup from current head through all new migrations.
- [ ] **P9.3 Clean install:** migrate empty supported database to head and seed successfully.
- [ ] **P9.4 Rollback rehearsal:** restore database backup and previous application release; validate login and critical workflows.
- [ ] **P9.5 Security review:** secrets, permissions, tenant access, webhooks, approvals, attachments, exports, and audit.
- [ ] **P9.6 Performance review:** dashboards, ticket lists, policy resolution, notification bursts, and email bursts.
- [ ] **P9.7 Shadow review:** approve contract, SLA, approval, tier, visibility, notification, and email comparison reports.
- [ ] **P9.8 Documentation:** administrator guide, operator runbook, user guide, deployment, migration, monitoring, and recovery.
- [ ] **P9.9 Production package:** standalone runtime, manifest, migration head, notes, smoke tests, and SHA-256.
- [ ] **P9.10 Controlled deployment:** backup, migrate, seed, preserve production configuration, switch IIS, smoke-test, monitor, and record evidence.

## Stop/Resume Log

Add an entry whenever work stops, including partial implementation and verification state.

| Date/time | Stopped after | Status | Files/migration | Verification completed | Next exact action | Blocker/notes |
|---|---|---|---|---|---|---|
| 2026-08-12 | Architecture and implementation-plan preparation | Ready to start P1.1 | Plan file only; database remains at `0071_knowledge_resources` | Architecture reviewed; no implementation tests required | Confirm P1 data model, then implement migration | None |
| 2026-08-12 | P1.14 documentation | P1 implementation verified; packaging active | `0072_feature_policy_control`; feature models, resolver, APIs, seed, permissions, UI, tests, docs | Ruff passed; MyPy passed; frontend production build passed; 133 tests passed; upgrade and clean migration rehearsals passed | Build standalone P1 release and record evidence | Policy cache deferred until first high-volume consumer |
| 2026-08-12 | P1.15 standalone release gate | P1 completed; ready for P2.1 | v1.9.0; `0072_feature_policy_control`; standalone runtime present | Manifest and package verified; SHA-256 recorded | Finalize P2 contract-type model | None |
| 2026-08-12 | P2.2 contract-type foundation | Catalog and migration completed; P2 service active | `0073_contract_types`; model, seed, APIs, create UI, management UI, compatibility checks | Ruff and MyPy passed; frontend production build passed; 136 tests passed; `0072` upgrade and clean migration plus seed passed | Implement P2.3 applicability and ambiguity service | None |
| 2026-08-12 | P2.4 governed applicability | Resolver and preview API completed; P2 UI explanation active | Contract resolver, entitlement validation, defaults preview, precedence/ambiguity tests | Ruff and MyPy passed; frontend production build passed; 138 tests passed | Complete P2.5 UI explanations and edit-time type selection | None |
| 2026-08-12 | P2.8 standalone release gate | P2 completed; ready for P3.1 | v1.10.0; `0073_contract_types`; governance UI and standalone runtime | Ruff, MyPy, frontend build, 139 tests, clean/upgrade rehearsals, runtime and manifest passed | Finalize P3 product-scoped SLA target design | None |
| 2026-08-12 | P3.3 resolver foundation | Target schema, migration, resolver, and clock snapshots completed | `0074_product_scoped_sla`; canonical contexts, effective dates, versions, explicit fallback | Ruff/MyPy and focused SLA tests passed; `0073` upgrade and clean migration plus seed passed | Implement explicit contract candidate selection for ambiguity | None |
| 2026-08-12 | P3.6 explicit selection and snapshots | Candidate selection and immutable agreement evidence completed | Candidate API; ticket contract input; internal and portal selectors; clock snapshot columns | Ruff, MyPy, frontend build, and 141 tests passed | Persist P3.7 shadow comparisons | None |
| 2026-08-12 | P3.7 shadow evidence | Durable comparison and review APIs completed; P3 contract editor active | `0075_sla_shadow_evidence`; comparison model/APIs; portal agreement evidence | Ruff, MyPy, frontend build, 142 tests, clean/upgrade migration rehearsals passed | Extend product-scoped SLA contract editor | None |
| 2026-08-12 | P3.8 product-scoped editor | Governed target editor completed; ticket evidence alignment active | `ProductScopedSlaEditor`; internal/portal product and governing-contract evidence | Frontend production build and focused 12-test SLA regression passed | Persist/display resolver match reason and align grids/exports | None |
| 2026-08-12 | P3.10 evidence consistency | Match evidence and snapshot-based reporting completed; final gate active | `0076_sla_match_reason`; common SLA evidence, grid/export columns, portal/internal match display | Ruff, MyPy, frontend build, 142 tests, `0075`→`0076` migration passed | Run clean 0076 rehearsal and package P3 release | None |
| 2026-08-12 | P3.12 standalone release gate | P3 completed; ready for P4.1 | v1.11.0; migrations through `0076_sla_match_reason`; product-scoped SLA runtime and UI | Ruff, MyPy, frontend build, 142 tests, clean/upgrade rehearsals, runtime and manifest passed | Define P4 unified entitlement decision model | None |
| 2026-08-12 | P4.1 decision model and P8.1 prerequisites | Deterministic entitlement engine completed; Outlook security prerequisites documented | `entitlements/decision_service.py`; entitlement tests; P4 and P8 architecture docs | Ruff and MyPy passed; 23 focused entitlement/policy/contract tests passed | Implement P4.2 approval persistence and idempotency | P8 runtime will consume P4 decisions; minimum P7 event delivery will be introduced where P4/P8 require it |
| 2026-08-12 | P4.2 persistence and P8.4 Graph client | Approval persistence/API and clean migration completed; Outlook secure configuration API and Graph client completed | `0077_entitlement_approvals`; entitlement routes/models; Outlook configuration/routes/client | Ruff and MyPy passed; focused tests passed; clean migration and seed reached `0077` | Complete P8 settings UI and subscription/webhook foundation | Live connection testing requires Millensys Entra credentials and mailbox policy |
| 2026-08-12 | P8.2 secure settings and P8.3 UI foundation | Durable templates/queues/subscription health and Email Integration tabs completed | `0078_outlook_email_foundation`; Outlook models/APIs; `OutlookEmailSettings` | Ruff and MyPy passed; frontend production build passed; `0077` upgrade and clean migration/seed reached `0078` | Implement P8.5 subscription lifecycle and manual synchronization controls | Live Graph operations require Millensys Entra credentials and a public HTTPS notification URL |
| 2026-08-12 | P8.5–P8.7 Graph delivery foundation | Subscription controls, secured idempotent webhook, lifecycle events, and delta recovery completed; scheduled renewal remains | Outlook Graph routes/client; Email Integration Health controls; webhook queue tests | Ruff and MyPy passed; 9 focused tests passed; frontend production build passed | Implement sender resolution and governed message processing | Live Graph validation remains a staging gate requiring Millensys Entra credentials |
| 2026-08-12 | P8.8–P8.11 ingestion core | Sender mapping, quarantine, durable idempotency claim, governed ticket creation, conversation comments, and loop protection implemented | Outlook processor; queue/message operations APIs; integration defaults | Ruff and MyPy passed; 20 focused Outlook/approval/contract tests passed | Add attachments and P4 approval request handoff | Attachment scanning and outbound messaging remain before enforcement |
| 2026-08-12 | P8 implementation and v1.12.0 release gate | Attachments, approval handoff, acknowledgements/status mail, scheduled processing/renewal, outbound retries/replay, and standalone package completed | `0077`–`0079`; Outlook inbound/outbound services; v1.12.0 | Ruff, MyPy (114 files), frontend build, 153 tests, clean/upgrade migrations, executable/manifest/archive passed | Run P8.16 restricted live mailbox pilot in `SHADOW` | External tenant credentials, consent, mailbox restriction, and security sign-off required before `ENFORCED` |

## Implementation evidence register

Complete this table as releases are produced.

| Phase | Migration revision | Tests/evidence | Release candidate | SHA-256 | Result |
|---|---|---|---|---|---|
| P1 | `0072_feature_policy_control` | Ruff, MyPy, frontend build, 133 tests, clean/upgrade rehearsals passed | v1.9.0 standalone | `F193B4E1BE707C288582AB5948F4ED2E0B6F3320291291CEC7EF9A146851DD2A` | Completed |
| P2 | `0073_contract_types` | Ruff, MyPy, frontend build, 139 tests, clean/upgrade rehearsals and runtime verification passed | v1.10.0 standalone | `3EC5C85F3867BE3F0209DC51C2A373737E3C87F528614BF36AED364A204B0E6E` | Completed |
| P3 | `0074_product_scoped_sla`, `0075_sla_shadow_evidence`, `0076_sla_match_reason` | Ruff, MyPy, frontend build, 142 tests, clean/upgrade migrations and runtime verification passed | v1.11.0 standalone | `145A00B96909BF017A88D7CDF8E4AC1414DA66B6F68E5A807A228CEF295B6C41` | Completed |
| P4 | `0077_entitlement_approvals` | Decision and persistence regression included in 153 passing tests | Included in v1.12.0 | See P8 package checksum | Required P8 approval foundation completed |
| P5 | Not created | Not run | Not built | — | Pending |
| P6 | Not created | Not run | Not built | — | Pending |
| P7 | Not created | Not run | Not built | — | Pending |
| P8 | `0078_outlook_email_foundation`, `0079_outlook_outbound` | Ruff, MyPy, frontend build, 155 tests including SQL Server migration and release-revision regressions, clean/upgrade rehearsals and runtime verification passed | v1.12.0 standalone (corrected SQL Server migration and database compatibility gate) | `4DEF35FEEB873FE5892352B7096B3637DE180B4431A13EA70BBF9D47378745F6` | Code/release completed; restricted live tenant pilot pending |
| P9 | Depends on completed phases | Not run | Not built | — | Pending |

## Objective

Deliver configurable email integration, contract governance, product-scoped SLA, entitlement approvals, dynamic support tiers, sequential escalation, tier-based access, and role/tier notifications without forcing any capability into use before the organization is ready.

All new operational capabilities must be independently controllable and must preserve existing behavior when disabled.

## Feature operating modes

High-impact features use three modes:

| Mode | Behavior |
|---|---|
| `OFF` | Preserve the current Support Hub behavior. Stored configuration remains intact but is not enforced. |
| `SHADOW` | Evaluate the new policy and record/report the proposed result without blocking, rerouting, hiding, emailing, or changing SLA. |
| `ENFORCED` | Apply the configured policy to eligible new operations. |

Effective configuration is resolved in this order:

1. Product/service override
2. Contract override
3. Client override
4. System default

Every evaluated ticket must record the effective feature mode and policy version used. Existing ticket history must not be silently recalculated after configuration changes.

## Master status

| ID | Phase | Status | Depends on |
|---|---|---|---|
| P0 | Architecture and existing-system assessment | Completed | — |
| P1 | Feature & Policy Control foundation | Completed | P0 |
| P2 | Contract types and governance | Completed | P1 |
| P3 | Product-scoped SLA and multiple-contract resolution | Completed | P1, P2 |
| P4 | Unified entitlement and approval workflow | In progress | P1, P2, P3 |
| P5 | Dynamic support tiers and sequential escalation | Pending | P1 |
| P6 | Tier-based routing and ticket visibility | Pending | P1, P5 |
| P7 | Notification policy engine | Pending | P1, P4, P5 |
| P8 | Microsoft Outlook integration | In progress | P1, P3, P4, minimum required P7 delivery |
| P9 | Integrated verification and controlled rollout | Pending | P1–P8 |

Status values: `Pending`, `In progress`, `Blocked`, `Completed`.

## P0 — Architecture and existing-system assessment

Status: Completed

Completed decisions:

- Extend the current contract, coverage, SLA, entitlement, escalation, notification, and permission foundations.
- Keep ticket priority, ticket type, and support tier as separate concepts.
- Use configurable support tiers instead of hardcoded L1/L2/L3 logic.
- Use one entitlement approval engine for all coverage exceptions.
- Use Microsoft Graph webhooks plus reconciliation for Outlook integration.
- Apply new policies to new operations without rewriting historical evidence.

## P1 — Feature & Policy Control foundation

Status: In progress

### Scope

- Central feature catalog with stable feature keys.
- `OFF`, `SHADOW`, and `ENFORCED` operating modes.
- System, client, contract, and product/service policy scopes.
- Deterministic effective-policy resolver.
- Policy versioning and effective dates.
- Audit history containing old value, new value, operator, reason, and timestamp.
- Site Settings workspace with feature descriptions and impact warnings.
- Backend enforcement; UI switches must never be the only control.
- Cache and cache invalidation for frequently evaluated policy settings.
- Safe behavior for scheduled jobs when their feature is disabled.
- Permission-controlled configuration management.

### Initial feature keys

- `contract_types`
- `product_scoped_sla`
- `entitlement_approvals`
- `support_tiers`
- `sequential_escalation`
- `tier_ticket_visibility`
- `notification_policies`
- `outlook_inbound_email`
- `email_creation_acknowledgement`
- `email_status_notifications`

### Acceptance gate

- Effective settings resolve correctly at every scope.
- `OFF` reproduces current behavior.
- `SHADOW` records decisions without operational side effects.
- Configuration changes are audited.
- Unauthorized users cannot read secrets or change policy.
- Automated resolver, API, permission, and regression tests pass.

## P2 — Contract types and governance

Status: Pending

### Scope

- Configurable contract-type catalog, initially supporting Warranty, Support, Service, Managed Service, Trial, Project Support, and Custom.
- Type defaults for SLA applicability, calendar, approval behavior, renewal behavior, and commercial treatment.
- Allow a client to hold multiple active and historical contracts.
- Allow overlapping contracts when coverage differs.
- Configure contract precedence instead of silently selecting by end date.
- Detect equally applicable contracts and require an explicit selection.
- Preserve warranty history when a later support contract begins.

### Acceptance gate

- Multiple contracts can coexist without overwriting one another.
- Contract ambiguity is detected and explained.
- Disabled contract-type behavior retains the current generic contract workflow.
- Existing contracts remain valid after migration.

## P3 — Product-scoped SLA and multiple-contract resolution

Status: Pending

### Scope

- Extend SLA targeting to contract, product, optional module, service, and priority.
- Use the following match order:
  1. Product + module + service + priority
  2. Product + service + priority
  3. Product + priority
  4. Contract default service + priority
  5. Contract default priority
  6. No matching SLA
- Make broad fallback targets explicitly configurable.
- Filter contract choices by client, product, dates, status, and coverage.
- Auto-select only when exactly one valid contract applies.
- Require selection when multiple valid contracts apply.
- Snapshot governing contract, target, calendar, and policy version on the ticket.
- Provide a shadow comparison report before enforcement.

### Acceptance gate

- An SLA for one product cannot leak to an unrelated product.
- Service-specific targets exclude unrelated services.
- Historical tickets retain their original agreed targets.
- SLA dashboard, grid, portal, exports, and drill-down use the same resolver.
- Shadow reporting identifies changed outcomes before enforcement.

## P4 — Unified entitlement and approval workflow

Status: In progress — P4.1 complete; P4.2 is next

### Conditions

- Inactive client
- Inactive contract
- Expired contract
- Product not covered
- Service not covered
- No matching SLA
- Included request limit exceeded
- Multiple matching contracts

### Configurable actions

- Allow
- Warn and require confirmation
- Require approval
- Block

### Scope

- Reusable entitlement decision record.
- Pending-approval ticket/request state that preserves submitted data.
- Configurable approver roles, groups, product owners, contract managers, and client-specific approvers.
- Justification, decision comment, approval deadline, reminders, escalation, and full audit history.
- Client portal creates a pending request rather than bypassing contractual controls.
- Internal users with an explicit override permission can proceed with an audited reason where policy allows.
- Duplicate submission protection throughout approval creation.

### Acceptance gate

- Every exception produces one deterministic reason and action.
- No approval request is duplicated by repeated submission.
- Approval, rejection, expiry, and cancellation are audited.
- `OFF` preserves the existing confirmation workflow.
- Portal and internal behavior follow the same entitlement engine.

## P5 — Dynamic support tiers and sequential escalation

Status: Pending

### Scope

- Configurable ordered support tiers with name, code, rank, next tier, active status, and escalation eligibility.
- User-to-tier assignments, with optional product, service, team, and department scope.
- Sequential escalation mode.
- L1 selects eligible L2 recipients, L2 selects eligible L3 recipients, and so forth based on configuration rather than fixed names.
- Configurable terminal destinations such as Engineering, Vendor, Management, or no further escalation.
- Emergency sequence override permission with mandatory reason.
- Escalation history records origin tier, destination tier, users, reason, time, and policy version.
- Preserve the current unrestricted escalation workflow when disabled.

### Acceptance gate

- Next-tier candidates are correctly scoped.
- Users cannot bypass enforced sequence without override permission.
- Disabling the feature restores current escalation selection.
- Current owner, collaborator, child-ticket, and SLA-time rules remain explicit and tested.

## P6 — Tier-based routing and ticket visibility

Status: Pending

### Scope

- Add configurable owning support tier to tickets.
- Route by product/service expertise first, then configurable fallback rules.
- Keep priority and ticket type independent from tier.
- Configurable access models: exact tier, current tier and higher, product/service scope, team management, audit, and explicit collaboration.
- Apply access consistently to details, lists, advanced search, exports, dashboards, reports, saved views, APIs, notifications, and bulk actions.
- Shadow report shows which users would gain or lose visibility.

### Recommended default

- L1 sees scoped L1 tickets.
- L2 sees scoped L1 and L2 tickets.
- L3 sees scoped L1, L2, and L3 tickets.
- Managers see their managed teams.
- Authorized administrators and auditors retain broad access.

### Acceptance gate

- No API or export bypasses tier visibility.
- Higher-tier access behavior is configurable.
- Explicit ticket collaborators retain intended access.
- Shadow impact is reviewed before enforcement.

## P7 — Notification policy engine

Status: Pending

### Scope

- Rule structure: event + conditions + recipient selector + channel + severity.
- Recipients by user, role, support tier, team, product owner, contract approver, manager, requester, or client contact.
- In-system and email channels initially; Teams and SMS remain optional extensions.
- Mandatory versus user-adjustable notifications.
- Template management with safe variables and previews.
- Deduplication, retries, delivery status, and failure visibility.
- Shadow simulation showing intended recipients without sending.

### Initial events

- Ticket created
- Ticket assigned
- Status changed
- Tier escalation
- Approval requested/approved/rejected/expired
- SLA warning/breach
- Contract renewal/expiry
- Email integration failure

### Acceptance gate

- Each event generates no more than the intended notifications.
- Mandatory notifications cannot be disabled by personal preferences.
- Shadow mode sends nothing.
- Delivery failures are retryable and visible to administrators.

## P8 — Microsoft Outlook integration

Status: In progress — P8.1 complete; implementation proceeds after the P4 approval foundation

### Scope

- Microsoft Graph application authentication for `Support@millensys.com`.
- Dedicated Email Integration tab in Site Settings.
- Secure tenant/application credential configuration and connection test.
- Inbox change-notification webhook.
- Automatic subscription renewal and lifecycle-event handling.
- Delta synchronization/reconciliation for missed notifications.
- Allowed domains, allowed addresses, blocked senders, and unknown-sender action.
- Sender-to-client/contact mapping with quarantine for ambiguous or unknown mappings.
- New message creates one ticket; a reply to a known thread adds one public comment.
- Deduplicate using Graph message identity and Internet Message-ID.
- Ignore Support Hub messages, automatic replies, delivery reports, and loops.
- Subject normalization and conversation threading.
- Validated attachments with size, type, storage, and scan status.
- Configurable creation acknowledgement and status-triggered client emails.
- Templates for created, in progress, pending, resolved, closed, and reopened events.
- Processing queue, retry policy, dead-letter handling, health status, and audit trail.

### Acceptance gate

- Repeated webhook delivery never creates duplicate tickets or comments.
- Subscription expiry, removal, reauthorization, and missed events recover automatically.
- Unauthorized senders follow configured policy.
- An incoming email cannot select an unrelated client contract or SLA.
- Outbound messages thread correctly and cannot create an email loop.
- Disabling the integration stops processing safely without deleting configuration.

## P9 — Integrated verification and controlled rollout

Status: Pending

### Scope

- Schema migration and rollback rehearsal using a production-like backup.
- Clean-install and upgrade-path verification.
- Unit, integration, API, UI, permission, concurrency, duplicate-submission, and scheduler tests.
- SLA consistency tests across ticket, portal, dashboard, grid, exports, and drill-down.
- Security review for Microsoft credentials, webhook validation, attachments, approvals, and data access.
- Performance tests for dashboards, ticket grids, policy evaluation, notifications, and email bursts.
- Operator documentation, configuration guide, monitoring guide, and incident recovery steps.
- Staging pilot with `SHADOW` reports reviewed before enforcement.
- Standalone Windows/IIS release, checksum, database revision, deployment guide, and rollback plan.

### Recommended rollout

| Capability | Initial production mode |
|---|---|
| Contract types | `ENFORCED` after migration validation |
| Product-scoped SLA | `SHADOW` |
| Entitlement warnings | `ENFORCED` |
| Entitlement approvals | `OFF` |
| Support tiers | `SHADOW` |
| Sequential escalation | `OFF` |
| Tier visibility | `OFF` |
| Notification policies | `SHADOW` |
| Outlook integration | `OFF` until connection and recovery tests pass |

### Final acceptance gate

- All phase acceptance gates pass.
- Shadow reports are reviewed and signed off.
- Production configuration is documented.
- Backup and rollback are verified.
- Operational owners understand how to disable each feature safely.

## Cross-cutting requirements

- No feature may rely only on frontend enforcement.
- All sensitive changes require permissions and audit entries.
- Secrets must not appear in API responses, logs, releases, or browser storage.
- Database migrations must be forward-safe and preserve existing data.
- Existing tickets retain their historical contract and SLA evidence.
- All automated processing must be idempotent.
- All scheduled jobs need health, last-success, last-error, and manual-retry visibility.
- Portal explanations must be honest and understandable without exposing internal-only information.
- Dashboard totals and drill-down results must use the same underlying query rules.

## Plan update procedure

At the end of each development increment:

1. Update the phase and overall status.
2. Record completed acceptance criteria.
3. Record migrations and compatibility impact.
4. Record test results and unresolved risks.
5. Identify the next active phase.
6. Add a dated entry to the change log.

## Change log

| Date | Change |
|---|---|
| 2026-08-12 | Created the master plan. Marked architecture assessment complete and Feature & Policy Control foundation in progress. |
