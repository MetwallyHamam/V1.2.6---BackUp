# Remaining Waves Execution Index

Date prepared: 2026-08-20

Wave 0 through Wave 2A are complete. The files below decompose every remaining roadmap item into independently executable scopes. Execute exactly one file at a time, update its status and `RELEASE_STEPS.md`, write the master-plan stop point, and stop before the next file.

| Order | Wave | Execution file | Exit outcome |
|---:|---|---|---|
| 1 | 2B | `WAVE_2B_SITE_SETTINGS_EXECUTION_PLAN.md` | Categorized, permission-safe Site Settings |
| 2 | 2C | `WAVE_2C_TICKET_NUMBER_SEARCH_EXECUTION_PLAN.md` | Authorized full-dataset ticket-number lookup |
| 3 | 2D | `WAVE_2D_ORGANIZATION_HIERARCHY_EXECUTION_PLAN.md` | Effective-dated department and reporting hierarchy |
| 4 | 3 | `WAVE_3_SERVICE_GOVERNANCE_EXECUTION_PLAN.md` | SLA templates, worklogs, feedback, outcomes |
| 5 | 3A | `WAVE_3A_EXCEPTION_APPROVALS_FINANCE_EXECUTION_PLAN.md` | Governed exceptions, pricing, payment ledger |
| 6 | 3B | `WAVE_3B_COVERAGE_RENEWAL_EXECUTION_PLAN.md` | Effective-dated coverage and renewals |
| 7 | 3C | `WAVE_3C_OPTIONAL_CONTRACT_FINANCE_EXECUTION_PLAN.md` | Optional contract finance and reconciliation |
| 8 | 4 | `WAVE_4_VISIT_ENTITLEMENT_EXECUTION_PLAN.md` | Exact-client visit entitlement ledger |
| 9 | 5 | `WAVE_5_SHIFT_VISIT_PLANNER_EXECUTION_PLAN.md` | Weekly shift and visit planning |
| 10 | 6 | `WAVE_6_BULK_COVERAGE_VISIT_COMPLETION_EXECUTION_PLAN.md` | Bulk coverage/imports and visit completion |
| 11 | 7 | `WAVE_7_OPERATIONAL_REPORTS_EXECUTION_PLAN.md` | Reconciled operational/contract reports |
| 12 | 7A | `WAVE_7A_DASHBOARD_CONSOLIDATION_EXECUTION_PLAN.md` | Canonical KPI ownership and no duplicates |
| 13 | 7B | `WAVE_7B_DASHBOARD_EVIDENCE_STRUCTURE_EXECUTION_PLAN.md` | Exact evidence links and department structure |
| 14 | 7C | `WAVE_7C_DEPARTMENT_ACHIEVEMENTS_EXECUTION_PLAN.md` | Verified department outcomes |
| 15 | 8 | `WAVE_8_SCORECARDS_RENEWAL_INTELLIGENCE_EXECUTION_PLAN.md` | Fair scorecards and renewal intelligence |
| 16 | 9 | `WAVE_9_SNAPSHOTS_SCHEDULED_REPORTING_FORECASTING_EXECUTION_PLAN.md` | Historical snapshots, scheduling, forecasting |

Global rules for every file:

- Preserve exact-client authorization and immutable historical evidence.
- Prefer additive, backward-compatible migrations with SQLite and SQL Server rehearsals.
- Keep configurable features disabled by default until their acceptance gates pass.
- Run Ruff, Mypy, backend Pytest, frontend ESLint, Vitest, TypeScript, and production build.
- Rehearse clean and populated upgrades, verify runtime compatibility, and remove disposable databases.
- Do not begin the next wave without an explicit `continue` instruction.
