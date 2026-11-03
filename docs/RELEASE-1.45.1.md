# SupportHub 1.45.1

Release date: 2026-08-27

Status: corrected self-contained Windows x64 release.

## Critical migration correction

- Corrects migrations `0136_complaint_management` and `0137_closed_ticket_polling` by quoting the SQL Server reserved columns `[key]` and `[value]` in `site_settings` statements.
- Release `1.45.0` must not be deployed. Its SQL Server upgrade stops while entering revision `0136`.
- The failed migration did not record revision `0136`. After backing up the database and replacing the release files, rerun `SupportHubBackend.exe migrate`; Alembic resumes from the recorded `0135_notification_rule_archive` revision.
- A regression test now prevents these migrations from reintroducing unquoted reserved identifiers.

## Completed backlog included

This release contains the verified implementation for:

| Point | Completed capability |
|---|---|
| **B-21** | Dedicated complaint management: reasons, numbering, scoped ownership, lifecycle controls, immutable activity, client tracking, satisfaction/closure, and explicit linked-ticket reopening. |
| **B-22** | Status-aware public ticket polling: 30 seconds while active, five-minute checks while closed, automatic reopen detection, and focus/reconnect refresh. |
| **B-23** | Customer Success analytics: governed complaint/satisfaction results, privacy-safe evidence, exports, and versioned explainable risk inputs. |
| **B-25** | Consistent outlined Engineer Queues action styling. |
| **B-26** | Configurable SLA warning thresholds plus direct emails and Support Team recipient groups. |
| **B-27** | Edit, enable/disable, and recoverable archive lifecycle for internal ticket-notification rules. |
| **B-28** | Permission-aware ticket context menu with visible keyboard/touch fast-action access. |

The package also retains all points B-01 through B-20 delivered by release `1.44.0`.

## Remaining backlog — prioritized

| Order | Priority | Point | Next outcome |
|---:|---|---|---|
| 1 | **P0** | **B-32** | Diagnose and prevent unexpected logout with safe reason reporting and return navigation. |
| 2 | **P1** | **B-24** | Unified permission-aware Send Actions for rating, live tracking, and complaint tracking. |
| 3 | **P1** | **B-31** | Close mobile dropdowns after selection without navigation or form-state loss. |
| 4 | **P1** | **B-36** | One redacted, structured, concurrency-safe application log per day. |
| 5 | **P1** | **B-38** | Guided Product → Module → Service Mosaic flow for portal ticket creation. |
| 6 | **P2** | **B-29** | Inactive Clients KPI across operational pages. |
| 7 | **P2** | **B-30** | Simplified Clients-page profile navigation. |
| 8 | **P2** | **B-34** | Compact collapsible Contract Types workspace. |
| 9 | **P2** | **B-35** | Contract Templates moved into Contract Workspace. |
| 10 | **P2** | **B-37** | Governed Training Material visibility in Client Portal. |

## Backlog source files

- Full original requirements, decisions, acceptance checks, and implementation history: source `docs\Backlog\Notes.md`; packaged copy `BACKLOG-NOTES.md`.
- Canonical filtered remaining-work queue and sequencing: source `docs\Backlog\Remaining.md`; packaged copy `REMAINING-BACKLOG.md`.
- The two backlog files are development-source documents and are referenced here explicitly; use `Remaining.md` to choose the next point and `Notes.md` for its complete specification.

## Database

Required revision: `0138_customer_success`.

Migrations `0135`–`0138` add notification-rule archival, complaint management, closed-ticket polling policy, and Customer Success permissions. Back up the production database before retrying the upgrade.

## Deployment

1. Do not continue with release `1.45.0`.
2. Back up the production database.
3. Extract release `1.45.1` to a new immutable directory and preserve protected production environment values.
4. Run `.\backend\runtime\SupportHubBackend.exe migrate` and confirm `0138_customer_success`.
5. Run `.\backend\runtime\SupportHubBackend.exe seed`.
6. Review complaint and Customer Success permissions, switch IIS to `1.45.1`, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

Final artifact size, entry count, SHA-256, and gate results are recorded after packaging in `RELEASE_STEPS.md`.
