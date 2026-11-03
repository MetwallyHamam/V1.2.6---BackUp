# Roadmap Phases A–C completion evidence

This document maps the delivered roadmap scope to its authoritative implementation and
verification evidence. API paths below are relative to `/api/v1`.

## Phase A — CRM master data and ticket creation context

| Requirement | Implementation evidence | Verification evidence |
|---|---|---|
| Client, branch, contact, product/module, environment, service, category/subcategory, installation, vendor, skill, and support-team master data | `app/modules/clients/models.py`, `schemas.py`, and `routes.py`; administration UI in `frontend/src/pages/CrmCatalogsPage.tsx` and client editing in `EditClientPage.tsx` | `test_crm.py` covers catalog seeds, authorization, create/update lifecycles, reference validation, duplicate handling, installation components, and audit records |
| Multiple products/modules per installation | `InstallationComponent`, migration `0022_installation_components.py`, validated component replacement in installation create/update, and repeatable product/module controls in the CRM catalog UI | `test_client_installation_can_be_created_and_updated` |
| Controlled ticket context | Ticket foreign keys for branch, requester, product/module, environment, service, category/subcategory, plus follower records in migration `0027_ticket_crm_context.py`; dependent selectors in `CreateTicketPage.tsx` | Ticket creation service validates client ownership, active references, module/product and subcategory/category relationships; covered by `test_tickets.py` and `test_crm.py` |
| Inactive-client confirmation | Ticket creation returns a controlled conflict until an authorized employee confirms; the UI displays an explicit proceed/cancel dialog | `test_inactive_client_requires_explicit_internal_confirmation` |
| Assignment and followers | Ticket creation supports team, engineer, and followers with object/assignee validation and notifications | `test_engineer_assignment_creates_visible_ticket_and_notification` plus ticket follower route tests |
| Authorization and audit | Permission dependencies protect reads and mutations; CRM changes and inactive-client confirmation are audited with actor and changed values | `test_crm_requires_permission`, catalog audit assertions, and audit tests |

## Phase B — scalable ticket operations

| Requirement | Implementation evidence | Verification evidence |
|---|---|---|
| Server pagination, filtering, and sorting | `GET /tickets` uses bounded `limit`/`offset`, controlled sort fields, structured filters, visibility predicates, and `X-Total-Count` | `test_ticket_queue_advanced_filters` and dashboard/list tests |
| Nested advanced filters | `POST /tickets/advanced-search` accepts a validated AND/OR AST and compiles only registered fields/operators to SQLAlchemy expressions | `test_advanced_filter_ast_supports_nested_and_or` |
| Column chooser | Ticket queue stores and renders selected columns while enforcing at least one visible column | Frontend type checking, linting, and production build |
| Saved views | Private, team, and administrator-only global views persist filter/column/sort state; ownership controls default/delete; team visibility derives from active membership/leadership | Migration `0031_saved_view_team_scope.py`; `test_dashboard_and_saved_view` and `test_team_saved_view_is_visible_to_team_members` |
| Tasks and checklists | Migration `0028_ticket_tasks_checklists.py`; create/list/update routes enforce ticket visibility and assignee validity, retain completion user/time, and update ticket activity/version | `test_ticket_tasks_and_checklist_lifecycle_are_audited` |
| Bulk assignment | `POST /tickets/bulk-assignment` validates all tickets and the target team/engineer, caps requests at 100, creates notifications, and adds correlated audits | Ticket route/service tests and full backend regression suite |
| Authorization and audit | Every list/search operation starts from the caller visibility query; task, checklist, assignment, and saved-view mutations use permission/object checks and audit events | `test_tickets.py`, `test_dashboards.py`, and `test_client_portal.py` |

## Phase C — contracts, coverage, and entitlements

| Requirement | Implementation evidence | Verification evidence |
|---|---|---|
| Full contract details | Contract number/client, lifecycle status, dates, renewal notice, timezone/calendar, support summary, exclusions, request limit, escalation contact, and active state; editable administration UI | Migrations `0029_contract_entitlements.py`; contract schemas/routes; `ContractsPage.tsx`; contract update validation tests |
| Coverage dimensions | Rules support product, module, branch, environment, service, ticket type, inclusion/exclusion, and notes | Migration `0030_contract_coverage_context.py`, coverage validation, and coverage UI |
| Reference and duplicate validation | Branch must belong to client, module must belong to product, all referenced records must exist and be active where required, and exact duplicate contexts are rejected | `test_contract_coverage_rejects_invalid_context_and_duplicates` |
| Deterministic evaluation | Active contracts have stable ordering; the most specific matching rule wins and exclusions win equal-specificity conflicts | `test_coverage_uses_specificity_and_equal_specificity_exclusion_precedence` |
| Included-request limit | Existing contract ticket count is evaluated and an exhausted allowance requires an employee override; portal users cannot override | `test_included_request_limit_requires_an_audited_override` |
| Ticket entitlement snapshot | Ticket creation stores contract ID, entitlement status, and override reason; exclusions/uncovered/limit states require an explicit audited management reason | `test_contract_coverage_requires_audited_override` |
| Contract documents and renewal reminders | Protected upload/download/delete, file validation, upcoming-renewal query, idempotent notifications, and administration UI | Contract entitlement tests and full regression suite |
| Authorization and object isolation | Contract permissions protect routes; portal-aware contract, entitlement, document, and SLA lookups enforce client/ticket scope | `test_client_portal.py` |
| Audit | Contract create/update, coverage create/delete, document upload/delete, renewal notifications, and entitlement overrides record actor/context values | Audit assertions in contract and ticket tests |

## Deployment and quality gates

- Database migration head: `0057_sla_clock_lifecycle`.
- Backend gates: Ruff, mypy, and the complete pytest suite.
- Frontend gates: TypeScript build, ESLint, Vitest, and Vite production build.
- Local application route: `http://127.0.0.1:5173/SupportHub/login` (no spaces).
- Backend runtime health: `http://127.0.0.1:8000/api/v1/health`.

Operational details are expanded in `CRM_MASTER_DATA.md`,
`TICKET_QUEUE_AND_VIEWS.md`, and `CONTRACTS_AND_SLA.md`.
