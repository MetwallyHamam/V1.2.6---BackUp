# SupportHub Phase 2 Work Reference

This is the short, authoritative Phase 2 tracker. It contains only requested user-facing work and the evidence needed to resume safely.

## Resume

- Keyword: `SUPPORTHUB-PHASE2-RESUME`
- Continue from `ACTIVE_CHECKPOINT`.
- Mark a step `DONE` only after its relevant tests pass.
- Update this file before stopping.

## Current checkpoint

```text
ACTIVE_CHECKPOINT: PHASE2.COMPLETE
ACTIVE_STATUS: DONE
NEXT_ACTION: Phase 2 is complete. Use this reference for release packaging/deployment or start a separately scoped Phase 3.
LAST_COMPLETED_STEP: P2.5.GATE — complete portal, notification, settings, migration, backend, and frontend verification passed
DATABASE_HEAD: 0057_sla_clock_lifecycle
LAST_REVIEWED_RELEASE: 1.2.5
LAST_UPDATED: 2026-08-05 Africa/Cairo
```

## Progress summary

| Area | Status | Result |
|---|---|---|
| Stabilization | `DONE_WITH_ACCEPTED_RISK` | Local backend/frontend gates pass. User deferred isolated SQL Server rehearsal because production is working. |
| Ticket workflow | `DONE` | Assignment, assign-to-me, searchable lists, pending, resolve/close/reopen, escalation children, portal confirmation, audit, and concurrency completed. |
| Contracts and SLA | `DONE` | Contract workspace, selection, coverage, dynamic SLA lifecycle, allowance, overrides, and verification completed. |
| HR and workforce | `DONE` | Employee profiles, HR department scope, calendar reliability, availability, KPI export, and full verification completed. |
| Management dashboard | `DONE` | Role-specific views, repeated issues, SLA/backlog/capacity/customer reporting, and reliable exports verified. |
| Portal, notifications, and settings | `DONE` | Portal isolation, realtime notifications/sound, public site settings, and full verification completed. |

## Remaining roadmap

### P2.2 — Contracts and dynamic SLA

| ID | Step | Status | Acceptance |
|---|---|---|---|
| P2.2.1 | Discoverable contract workspace | `DONE` | Customers, products/modules/services, SLA, and documents have visible labeled tabs and actions; no gear is required. |
| P2.2.2 | Customer-specific and shared-default precedence | `DONE` | One tested algorithm handles linked customers, dates, statuses, specificity, exclusions, and fallback. |
| P2.2.3 | Complete dynamic SLA and ticket deadlines | `DONE` | Service/priority targets create response and resolution clocks; public response/work starts, resolution, cancellation, parent closure, and reopen update them; warning notifications are deduplicated; ticket details show targets, thresholds, deadlines, completion, breach, and overdue state. |
| P2.2.4 | Complete request allowance and overrides | `DONE` | Only primary covered customer requests consume allowance; escalation children and approved overrides do not; used/remaining/override totals are visible and overrides require manager/admin permission with audit. |
| P2.2.GATE | Contract/SLA verification | `DONE` | Contract selection, coverage, SLA, and allowance tests pass. |

### P2.3 — HR, employees, and shifts

| ID | Step | Status | Acceptance |
|---|---|---|---|
| P2.3.1 | Department, job title, hierarchy, and employee profile | `DONE` | User creation supports requested job titles, hire date, manager/hierarchy, email username, and profile photo including self-service photo change. |
| P2.3.2 | HR role/group and department access | `DONE` | HR users see only permitted department dashboards, reports, shifts, and after-shift operations. |
| P2.3.3 | Shift calendar and saved-shift reliability | `DONE` | Day, week, and employee views show saved shifts in the correct timezone. |
| P2.3.4 | Active and online engineer status | `DONE` | Home/dashboard distinguishes Available, Working on ticket, and unavailable using today’s shift, presence, tickets, and internal tasks. |
| P2.3.5 | HR KPI report and Excel export | `DONE` | Approved KPI totals match the working export for the same period and department. |
| P2.3.GATE | HR/workforce verification | `DONE` | HR permissions, profiles, shifts, availability, KPI, and export tests pass. |

### P2.4 — Management dashboard and reports

| ID | Step | Status | Acceptance |
|---|---|---|---|
| P2.4.1 | Role-based management dashboard | `DONE` | Management, HR, team leader, and engineer views show useful role-specific cards and actions. |
| P2.4.2 | Repeated issues and operational reports | `DONE` | Repeated issue/root-cause, SLA, backlog, capacity, and customer reports support useful filters. |
| P2.4.3 | Reliable report export | `DONE` | Dashboard/API/export totals match and current HR export errors are eliminated. |
| P2.4.GATE | Dashboard/report verification | `DONE` | Role access, report totals, and exports pass tests. |

### P2.5 — Portal, notifications, and public settings

| ID | Step | Status | Acceptance |
|---|---|---|---|
| P2.5.1 | Portal permission and customer isolation review | `DONE` | Portal users cannot see another customer’s tickets, contracts, files, comments, or catalogs. |
| P2.5.2 | Ticket notifications and sound | `DONE` | New tickets notify intended users, assignment/escalation notifies the selected engineer, and configured sound works without duplicates. |
| P2.5.3 | Site settings and login defaults | `DONE` | UI controls default theme, sound, automatic assignee, available/online assignment filters, and each user’s default post-login page including ticket creation. |
| P2.5.GATE | Portal/settings verification | `DONE` | Isolation, notification, sound, default-page, and site-setting tests pass. |

## Completed milestones

| Date | Milestone | Evidence |
|---|---|---|
| 2026-08-05 | Stabilized current release and added migration compatibility checks. | Backend/frontend quality gates passed; SQL Server rehearsal explicitly deferred by user. |
| 2026-08-05 | Completed ticket workflow phase. | 100 backend tests plus frontend lint, tests, TypeScript, and build passed; database head reached 0056. |
| 2026-08-05 | Replaced hidden contract controls with a labeled workspace. | Frontend gates and 100 backend tests passed. |
| 2026-08-05 | Centralized deterministic contract precedence and portal catalog filtering. | Ruff/mypy passed; 103 backend tests passed. |
| 2026-08-05 | Trimmed Phase 2 to requested user-facing work. | Removed version-history architecture, distributed workers, SSO program, security-program tasks, surveys, scheduled-report architecture, and other enterprise-only roadmap items. |
| 2026-08-05 | Completed practical dynamic SLA lifecycle and display. | Migration 0057; Ruff/mypy and 106 backend tests passed; frontend lint, tests, TypeScript, and production build passed. |
| 2026-08-05 | Completed contracts and SLA phase. | Ruff/mypy and 106 backend tests passed; frontend lint, tests, TypeScript, and production build passed; migration head 0057. |
| 2026-08-05 | Completed HR and workforce phase. | Department isolation, saved-shift timezone, KPI/export consistency, 107 backend tests, and all frontend gates passed. |
| 2026-08-05 | Completed management dashboard and reports phase. | Role-gated cards, repeated issues, operational breakdowns, CSV/Excel totals, 107 backend tests, and all frontend gates passed. |
| 2026-08-05 | Completed Phase 2. | Portal/file/contract isolation, notification broadcast/assignment, validated site defaults, 108 backend tests, frontend production build, and migration head 0057 passed. |

## Applied KPI policy

- HR access is department-scoped. KPI definitions are documented inside the generated Excel workbook and dashboard/export totals use the same calculation path.

## Standard verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app alembic scripts
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m alembic heads

cd ..\frontend
node .\node_modules\eslint\bin\eslint.js .
node .\node_modules\vitest\vitest.mjs run
node .\node_modules\typescript\bin\tsc -b
node .\node_modules\vite\bin\vite.js build
```
