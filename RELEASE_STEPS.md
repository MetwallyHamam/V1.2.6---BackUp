# Release Steps and Development Recovery Log

## 1.66.159 — 2026-10-26

Status: self-contained Windows x64 Knowledge Base organization and downloads release built and verified.

- Adds managed Tools & Downloads content with uploaded files, external links, category administration, and portal visibility.
- Groups Knowledge articles and Downloads into expandable categories and groups ticket-generated knowledge by Product.
- Adds the Tickets Knowledge Base category and automatically classifies new and existing ticket-generated articles.
- Corrects Knowledge Base filter and category selectors.
- Advances database compatibility to `0274_ticket_knowledge_category`.
- Backend Ruff and strict MyPy passed across 203 source files; all 557 backend tests passed.
- Frontend ESLint, all 133 frontend tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, `diagnose-db`, and `recover-admin`.
- Manifest version `1.66.159`, IIS `APP_VERSION`, database head `0274_ticket_knowledge_category`, required migrations, ZIP readability, 2,090 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.159.zip`.

## 1.66.158 — 2026-10-25

Status: self-contained Windows x64 streamlined sidebar and opened-page navigation release built and verified.

- Adds collapsible sidebar areas with automatic expansion of the active area.
- Reduces sidebar visual noise with neutral inactive icons, compact spacing, and a stronger selected-page treatment.
- Adds session-based opened-page tabs while excluding category headings such as Support from breadcrumbs and tabs.
- Retains database compatibility at `0272_deployment_issue_types`; no migration is required from `1.66.157`.
- Backend Ruff and strict MyPy passed across 203 source files; all 556 backend tests passed.
- Frontend ESLint, all 133 frontend tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, `diagnose-db`, and `recover-admin`.
- Manifest version `1.66.158`, IIS `APP_VERSION`, database head `0272_deployment_issue_types`, required contents, ZIP CRC/readability, 2,086 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.158.zip` (54,003,998 bytes).
- SHA-256: `42AF2FD2D8EFAF814638D98E59D2852385625A2ED4E8DF5CC0FC3AA919E62DC1`.

## 1.66.157 — 2026-10-24

Status: self-contained Windows x64 Service Checklist card-layout release built and verified.

- Gives client and checklist names the full card width across all status and engineer lanes.
- Moves checklist selection and status controls to a dedicated responsive row and prevents character-by-character title wrapping.
- Retains database compatibility at `0272_deployment_issue_types`; no migration is required from `1.66.156`.
- Backend Ruff and strict MyPy passed across 203 source files; all 556 backend tests passed.
- Frontend ESLint, all 133 frontend tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, `diagnose-db`, and `recover-admin`.
- Manifest version `1.66.157`, IIS `APP_VERSION`, database head `0272_deployment_issue_types`, required contents, ZIP CRC/readability, 2,086 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.157.zip` (54,002,627 bytes).
- SHA-256: `2913F6CF402C5AFFFF10DAF753C601E0CAD127F31315CAF9F30FBC590B2F73E6`.

## 1.66.156 — 2026-10-24

Status: self-contained Windows x64 Tickets, Problem Management, and native ITOP migration release built and verified.

- Keeps repeated Tickets navigation clicks on Today's tickets and preserves pending statuses in their correct board lanes.
- Adds multi-ticket Problem linking, linked-ticket removal with reason, and close-dialog completion of required root-cause and permanent-fix summaries.
- Adds native ITOP workbook staging, missing-master-data preview and confirmation, ticket/caller/engineer migration, assignment tracking, logs, resolutions, and historical timestamps.
- Retains database compatibility at `0272_deployment_issue_types`; no migration is required from `1.66.154`.
- Backend Ruff and strict MyPy passed across 203 source files; all 556 backend tests passed.
- Frontend ESLint, all 133 frontend tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, `diagnose-db`, and `recover-admin`.
- Manifest version `1.66.156`, IIS `APP_VERSION`, database head `0272_deployment_issue_types`, required ITOP import sources, ZIP CRC/readability, 2,086 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.156.zip` (54,001,981 bytes).
- SHA-256: `5D7C337E7AC3409519FE14F3C8969C185C4416C8A0299ABD72024BFEAF6176E0`.

## 1.66.155 — 2026-10-23

Status: corrected Tickets navigation and pending-lane release build requested.

- Alternates repeated Tickets navigation clicks between Today and All Time.
- Keeps client-pending and other pending tickets in their actual pending lanes even when they have a previous progress start timestamp.
- Retains database compatibility at `0272_deployment_issue_types`; no migration is required from `1.66.154`.
- Full release verification and final artifact metadata will be recorded after the build completes.

## 1.66.154 — 2026-10-23

Status: corrected self-contained Windows x64 workflow-list isolation release built and verified.

- Corrects the workflow tabs so they no longer inherit saved Tickets columns, widths, density, or grouping.
- Adds fixed operational columns for Escalations, Shift Handover, Approvals, and Trash.
- Adds Archived and Archive Reason to the Trash list and preserves workflow filters, sorting, selection, and actions.
- Retains database compatibility at `0272_deployment_issue_types`; no new migration is required from `1.66.153`.
- Backend Ruff and strict MyPy passed across 203 source files; all 553 backend tests passed.
- Frontend ESLint, all 129 frontend tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, `diagnose-db`, and `recover-admin`.
- Manifest version `1.66.154`, database head `0272_deployment_issue_types`, required contents, ZIP readability, CRC, 2,086 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.154.zip` (53,978,205 bytes).
- SHA-256: `FC02B5224FF8CFEF3339783E94E498292DB719D5C95FB3A78BA10284F689A1CF`.

## 1.66.153 — 2026-10-23

Status: self-contained Windows x64 concurrency and workflow-layout release built and verified.

- Enables SQL Server `READ UNCOMMITTED` centrally for all application reads, with a configuration opt-out and no behavior change for SQLite or other providers.
- Makes Escalations, Shift Handover, Approvals, and Trash use dedicated list layouts independent of the normal Tickets default layout.
- Preserves workflow-specific filters/actions and the user's regular Tickets layout preference.
- Adds the multi-organization Project Delivery and Product Development implementation plan.
- Retains database compatibility at `0272_deployment_issue_types`; no new migration is required from `1.66.152`.
- Backend Ruff and strict MyPy passed across 203 source files; all 553 backend tests passed.
- Frontend ESLint, all 127 frontend tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, `diagnose-db`, and `recover-admin`.
- Manifest version `1.66.153`, database head `0272_deployment_issue_types`, standalone metadata, required contents, ZIP readability, 2,086 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.153.zip` (53,980,176 bytes).
- SHA-256: `6C7C942450B04EEB1232458C299C98E3C1C0C3ECE730694EB3DD124011F68A25`.

## 1.66.152 — 2026-10-17

Status: full self-contained Windows x64 client lifecycle release built and verified.

- Adds UAT, Deployment, Incident, Change Request, and Problem lifecycle summaries to the internal Client Profile and Client Portal.
- Adds recent-record drill-down navigation and active/open counts.
- Preserves portal visibility and client-scope controls and avoids exposing internal Problem content.
- Adds the lifecycle summary to the Client Profile Word report.
- Retains database compatibility at `0272_deployment_issue_types`; no new migration is required from `1.66.151`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 550 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Manifest version, database head, packaged runtime, ZIP readability, and 2,083 archive entries were verified.
- Final artifact: `releases/SupportHub-1.66.152.zip` (53,965,415 bytes; 2,083 entries).
- SHA-256: `27A736945EF65DDF2B139D1DFCF72F72772932F367251B69CBCD6294F912E743`.

## 1.66.150 — 2026-10-16

Status: full self-contained Windows x64 release built and verified.

- Corrects Q3/Q4 KPI history and finalized-report filtering and naming.
- Rechecks ticket entitlement against extended contracts and cancels obsolete pending exception approvals when coverage is restored.
- Adds managed Deployment Issue Types with Issue, Error, BUG, and Enhancement defaults.
- Adds complete deployment issue content editing without requiring a workflow transition.
- Adds Affects workflow and Update needed issue indicators across creation, editing, cards, linked-ticket context, public live tracking, and PDF/Word reports.
- Advances database compatibility to `0272_deployment_issue_types`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 550 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime commands, manifest version, database head, migration inclusion, ZIP readability, 2,082 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.150.zip` (53,954,852 bytes; 2,082 entries).
- SHA-256: `5636EBE4E4A4B01E5DC5763FA6243A5497A5D79DD6C9E74D9EAD66967225B2A1`.

## 1.66.149 — 2026-10-16

Status: full self-contained Windows x64 release built and verified.

- Adds multiple versioned Products to deployment plans with exactly one Main Product.
- Shows Product/version context on the plan and deployment PDF/Word reports.
- Restricts issue ticket creation to plan Products and preselects the Main Product.
- Preserves legacy deployment plans so Product configuration can be added during editing.
- Advances database compatibility to `0271_deployment_products`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 549 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Clean migration, downgrade, and repeat upgrade through revision 0271 passed before packaging.
- Packaged runtime commands, manifest version, database head, frontend and migration inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.149.zip` (`53,941,884` bytes; 2,081 entries).
- SHA-256: `00EE28B756A9D99D9D24ABAC8219DD12FB684AD93E5584540C21AE3EE6534E2F`.

## 1.66.148 — 2026-10-16

Status: full self-contained Windows x64 release built and verified.

- Integrates deployment issue resolutions with governed Knowledge Base draft creation.
- Prefills deployment, issue, investigation, root-cause, resolution, validation, service, and follow-up context.
- Applies the deployment Client and linked Incident Product/Module to the draft.
- Links each draft to its deployment issue and related Incident while preventing duplicate drafts.
- Advances database compatibility to `0270_deployment_knowledge`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 549 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Clean migration, downgrade, and repeat upgrade through revision 0270 passed before packaging.
- Packaged runtime commands, manifest version, database head, frontend and migration inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.148.zip` (`53,933,245` bytes; 2,080 entries).
- SHA-256: `AF5C151C8492DE69C615ADE3FEC21F2309F5A49711BCD0FFB9B926AB0AA5FE4C`.

## 1.66.147 — 2026-10-16

Status: full self-contained Windows x64 release built and verified.

- Adds a governed Ticket Type flag controlling availability for deployment issue ticket creation.
- Enables Incident and Service Request by default while hiding other Ticket Types.
- Enforces the configured selection on the server and exposes the flag in Ticket Type master data.
- Fixes the Ticket Flags panel layout inside narrow deployment workflow cards.
- Advances database compatibility to `0269_deployment_ticket_types`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 549 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Clean migration, downgrade, and repeat upgrade through revision 0269 passed before packaging.
- Packaged runtime commands, manifest version, database head, frontend and migration inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.147.zip` (`53,928,694` bytes; 2,079 entries).
- SHA-256: `E40658A360E1DF0A7057C702B2BA1E44A4E4F7681FE1B43B70E6B3D917638CEB`.

## 1.66.146 — 2026-10-15

Status: full self-contained Windows x64 release built and verified.

- Adds Quarter filtering to KPI History and Comparison and includes submitted/finalized reviews in bulk downloads.
- Names finalized KPI workbooks with the engineer and quarter.
- Adds inline Ticket Type, Product, Module, Reporter / Caller, and Description fields to deployment issue creation.
- Copies those governed values into the linked ticket and uses the client Contact as the issue reporter and ticket caller.
- Retains database compatibility at `0268_deployment_links`; no new migration is introduced.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 549 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime commands, manifest version, database head, frontend and migration inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.146.zip` (`53,925,998` bytes; 2,078 entries).
- SHA-256: `569C7075FA9F5FA7188CC0B28B9A3B669935E4D5807055944976D43D5FA18366`.

## 1.66.145 — 2026-10-15

Status: full self-contained Windows x64 release built and verified.

- Adds explicit issue-only and issue-plus-ticket creation actions.
- Supports many deployment issues per Incident and many Incidents per Problem.
- Adds Incident and Problem selection, governed permissions, aggregate synchronization, and report lineage.
- Adds date- and agent-filtered bulk ZIP download for finalized KPI Excel reports.
- Advances database compatibility to `0268_deployment_links`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 549 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime help, manifest version, database head, frontend asset inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.145.zip` (`53,922,342` bytes; 2,078 entries).
- SHA-256: `B441503C144DD6F9B55088D8FC218CA172A8BCBCC28D498D207D3B2691E167C2`.

## 1.66.144 — 2026-10-15

Status: full self-contained Windows x64 release built and verified.

- Enforces readable natural height directly on every deployment-item card.
- Adds governed drag-and-drop workflow transitions with target highlighting and invalid-jump protection.
- Retains database compatibility at `0267_deployment_defaults`; no new migration is introduced.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 548 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime help, manifest version, database head, frontend asset inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.144.zip` (`53,910,705` bytes; 2,077 entries).
- SHA-256: `72770D4BFAED34963F6EEEC98C9D94B12898FC9B26EF3B37A309140705241B23`.

## 1.66.143 — 2026-10-15

Status: superseded before deployment by `1.66.144`, which applies the card-size rule directly and adds drag-and-drop.

- Adds independent vertical scrolling to every deployment workflow lane.
- Prevents cards in high-volume lanes from shrinking into unreadable rows.
- Retains database compatibility at `0267_deployment_defaults`; no new migration is introduced.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 548 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime help, manifest version, database head, frontend asset inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.143.zip` (`53,910,498` bytes; 2,077 entries).
- SHA-256: `9C9B504F13B5E4AF4BD6526512E334D7A4C8C55F1CCAD5AF16765E5F9B6E0566`.

## 1.66.142 — 2026-10-15

Status: superseded before deployment by `1.66.143` because high-volume lane cards could shrink.

- Adds a capped card viewport and independent vertical scrollbar to every deployment workflow lane.
- Keeps lane headings visible and preserves horizontal scrolling across the full board.
- Retains database compatibility at `0267_deployment_defaults`; no new migration is introduced.

## 1.66.141 — 2026-10-15

Status: full self-contained Windows x64 release built and verified.

- Adds the active `Deployment / Follow UP` service and makes it the deployment-resolution default.
- Makes `Other` the default root cause for deployment-issue resolution; both selections remain editable.
- Includes the deployment owner in Resolved by and supports Issue/Change Request classification with matching ticket creation.
- Uses server time by default for deployment-item timestamps and validates reported/resolved/delivered ordering with precise messages.
- Adds a collapsible deployment-plan sidebar, a direct Add Issue action, and Open-lane double-click issue creation.
- Replaces separate issue blocks in deployment PDF and Word exports with one fitted, multi-column landscape table.
- Advances database compatibility to `0267_deployment_defaults` with an idempotent catalog migration.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 548 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime help, manifest version, database head, migration inclusion, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.141.zip` (`53,910,066` bytes; 2,077 entries).
- SHA-256: `5097AF122582E8CC8D2BD68DB02A8E8C1020BC0684610588FD66C1D706938770`.

## 1.66.140 — 2026-10-15

Status: full self-contained Windows x64 corrective release built and verified.

- Fixes SQL Server error 1781 when migration `0264_deployment_issue_workflow` encounters defaults already bound by an approved schema repair.
- Detects and preserves existing defaults for `responsible_party` and `delivered`, while clean upgrades still create the required defaults.
- Retains database compatibility at `0266_deployment_ticket_sync`; no new schema revision is introduced.
- Supersedes `1.66.138` and `1.66.139` for deployment.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 548 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime help, manifest version, database head, SQL Server type/default retry protections, ZIP readability, 2,076 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.140.zip` (`53,903,984` bytes).
- SHA-256: `91F72577C67158F8A5F2C1D084AA00A85ED894E07844F6364561F8FAEBC09CE9`.

## 1.66.139 — 2026-10-15

Status: full self-contained Windows x64 corrective release built and verified.

- Fixes migration `0264_deployment_issue_workflow` for Microsoft SQL Server by supplying `existing_type` on all `ALTER COLUMN ... NOT NULL` operations.
- Allows the deployment-issue workflow migration to resume safely after the SQL Server/Alembic compatibility failure reported in `1.66.138`.
- Retains database compatibility at `0266_deployment_ticket_sync`; no new schema revision is introduced.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 548 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime help, manifest version, database head, corrected migration inclusion, ZIP readability, 2,076 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.139.zip` (`53,902,470` bytes).
- SHA-256: `0E96E62AD1B0299364D4AA69556207828C281F2E36C751D646F7DC2E36CDFB01`.

## 1.66.138 — 2026-10-15

Status: full self-contained Windows x64 release built and verified.

- Integrates deployment issues and incident tickets with bidirectional status, resolution, root-cause, service-provided, delivery, closure, and reopen synchronization.
- Adds an explicit Reopened deployment-issue workflow state with a required reason and retained historical delivery data.
- Makes existing ticket flags available from linked deployment issues, including governed SLA pause and resume behavior.
- Adds a visible, default-enabled option to create and link an incident ticket automatically when creating a deployment issue.
- Extends professional deployment PDF and Word reports with multiple root causes, services provided, delivery details, and reopen context.
- Advances database compatibility to `0266_deployment_ticket_sync`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 548 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Packaged runtime help and clean migration through `0266_deployment_ticket_sync` passed; the ZIP contains 2,077 entries.
- Final artifact: `releases/SupportHub-1.66.138.zip` (`54,015,213` bytes).
- SHA-256: `5513F98218D0982AFA1EC483692D5DF8D235BC18C0405AC778AC3301A8464CC4`.

## 1.66.137 — 2026-10-13

Status: full self-contained Windows x64 release built and verified.

- Prevents content and status-control overflow in every Deployment Issues and Follow-up workflow lane.
- Preserves the Tickets-list period and complete filter URL when opening a ticket and returning from ticket details.
- Retains database compatibility at `0263_deployment_issue_stage`; no migration is required.
- Full release gates passed: Ruff, strict MyPy across 202 backend source files, 546 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Manifest version `1.66.137`, database head `0263_deployment_issue_stage`, standalone metadata, runtime commands, ZIP readability, 2,070 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.137.zip` (`53,848,513` bytes; expanded release `103,173,937` bytes; 2,070 entries).
- SHA-256: `043C34DBD0C4DF69C461A175B00D02529A06DE485E1B3EF97D105F7FF333D617`.

## 1.66.136 — 2026-10-11

Status: full self-contained Windows x64 release built and verified.

- Fixes the Issues and Follow-up board lanes collapsing into unreadable one-character-wide columns.
- Gives every workflow lane a stable readable width with horizontal Kanban scrolling when space is limited.
- Stacks Issue Stage and Issue Status controls inside each card for responsive desktop, tablet, and mobile use.
- Adds professional status colors to both workflow lanes and issue cards: orange Open, blue In Progress, amber Pending Implementation, green Resolved, and slate Closed.
- Replaces native browser prompts with branded in-system dialogs for issue resolution/closure and deployment finalization.
- Widens workflow lanes and guarantees a clear full-width Issue Status selector without cramped vertical text.
- Includes the complete deployment issue workflow, stage classification, post-deployment follow-up, and deployment timeline from `1.66.135`.
- Database compatibility remains `0263_deployment_issue_stage`; no additional schema change is required.
- Full release gates passed: Ruff, strict MyPy across 202 backend source files, 546 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Final artifact: `releases/SupportHub-1.66.136.zip` (`53,849,221` bytes; expanded release `103,173,038` bytes; 2,070 entries).
- SHA-256: `2D63A95122D5F91D50429ECA7DC4C3121224D4C7AC8F418C0EF6478295BF0614`.

## 1.66.135 — 2026-10-11

Status: full self-contained Windows x64 release built and verified.

- Adds the complete deployment issue workflow: Open, In Progress, Pending Implementation, Resolved, and Closed.
- Keeps issue follow-up editable after deployment finalization and supports reopening issues.
- Classifies issues as Before Deployment, During Deployment, or After Deployment, with board filtering and client-portal submission.
- Adds issue-stage details to automatic tickets and branded PDF/Word deployment reports.
- Adds a modern responsive deployment-step timeline with numbered status markers, progress connectors, planned/actual duration, and planned/actual time windows.
- Advances database compatibility to `0263_deployment_issue_stage` with an idempotent SQL Server-compatible migration.
- Full release gates passed: Ruff, strict MyPy across 202 backend source files, 546 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Final artifact: `releases/SupportHub-1.66.135.zip` (`53,847,958` bytes; expanded release `103,168,778` bytes; 2,070 entries).
- SHA-256: `D6663A1DE36CFA7FFD18BC3070EA4EAC8F5D45039FCC3850E19012B704449691`.

## 1.66.134 — 2026-10-11

Status: full self-contained Windows x64 release built and verified.

- Removes a false compatibility requirement for `change_request_details.approved_software_version`.
- Confirms the approved-version field belongs to `deployment_plans`, where revision 0262 already reconciles it.
- Keeps database head `0262_deployment_schema_reconcile`; no schema mutation is required.
- Supersedes `1.66.133` before deployment.
- Adds separate UAT template Edit and New Version actions while preserving archive and duplication.
- Adds direct numeric test ordering and automatic module-grouped ordering in the template editor.
- Full release gates passed: Ruff, strict MyPy across 202 backend source files, 546 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Artifact: `releases/SupportHub-1.66.134.zip` (`53,842,344` bytes; expanded release `103,159,339` bytes).
- SHA-256: `19F19C4C1BA672CE93001909F0A19F1CD8531B572AD246346A3799D1B524CEE8`.

## 1.66.133 — 2026-10-11

Status: diagnostic-only release superseded before deployment by `1.66.134`.

- Keeps database head `0262_deployment_schema_reconcile`.
- Exposes the exact missing table and columns when compatibility reports `SCHEMA_INCOMPLETE`.
- Adds `SupportHubBackend.exe diagnose-db` for an authoritative server-side compatibility check.

## 1.66.132 — 2026-10-11

Status: full corrective self-contained Windows x64 release built and verified.

- Reconciles the complete deployment schema for databases at 0261 that still report `SCHEMA_INCOMPLETE`.
- Repairs missing and partially created deployment plan, share-link, evidence, and document structures without resetting data.
- Advances database compatibility to `0262_deployment_schema_reconcile`.
- Supersedes `1.66.131` for deployment.
- Full release gates passed: Ruff, strict MyPy across 202 backend source files, 545 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Artifact: `releases/SupportHub-1.66.132.zip` (`53,840,785` bytes; expanded release `103,125,574` bytes).
- SHA-256: `A7DE32A083AB4371748446B162859D347EDC8865158E9A461DEBF36140C296C8`.

## 1.66.131 — 2026-10-11

Status: superseded by `1.66.132`; its repair did not cover every legacy form of the 0260 deployment schema.

- Repairs upgrades from databases already stamped at `0260_deployment_share_links`.
- Adds idempotent forward migration `0261_deployment_evidence_repair` without resetting application data.
- Verifies the exact reported path by removing the newer deployment schema from a database stamped at 0260 and successfully upgrading it to 0261.
- Supersedes `1.66.130` for deployment.
- Full release gates passed: Ruff, strict MyPy across 202 backend source files, 545 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Artifact: `releases/SupportHub-1.66.131.zip` (`53,839,876` bytes; expanded release `103,116,769` bytes).
- SHA-256: `5AAEBCBFD3D9C708DAD790CE5754267A781AE148F0DE8DEECCE367BF68CFB8D3`.

## 1.66.130 — 2026-10-10

Status: superseded by `1.66.131`; do not deploy against a database previously stamped at the earlier form of revision 0260.

- Adds approved software version tracking to deployment plans and branded reports.
- Adds authenticated deployment documentation uploads per plan.
- Adds file evidence and shared-file/recorded-video URLs per issue.
- Supports the same evidence workflow in the scoped client portal.
- Includes the Start-response fix, public live tracking, finalized-plan editing, rollback plans, and client issue reporting from the superseded candidate.
- Database compatibility remains `0260_deployment_share_links`, expanded before release packaging.
- Full release gates passed: Ruff, strict MyPy across 202 backend source files, 545 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Artifact: `releases/SupportHub-1.66.130.zip` (`53,836,285` bytes; expanded release `103,111,671` bytes).
- SHA-256: `0125291C3579DBF20D73FB0D610EDD29477BDF19B967DC134F61B2F46610FF29`.

## 1.66.129 — 2026-10-10

Status: superseded before packaging by `1.66.130`; do not deploy.

- Fixes the SQL Server timestamp mismatch that caused Start to display an error after successfully updating a deployment step.
- Adds expiring/revocable public stakeholder live-tracking URLs with 15-second refresh.
- Adds finalized-plan editing and a structured rollback plan included in PDF and Word reports.
- Allows scoped client-portal contacts to submit deployment issues without exposing internal controls.
- Database compatibility advances to `0260_deployment_share_links`.

## 1.66.128 — 2026-10-10

Status: superseded before deployment by `1.66.129`, which corrects deployment Start responses and completes live stakeholder sharing and client issue reporting.

- Supersedes `1.66.127` for deployment.
- Corrects the SQL Server migration failure when multiple existing integration API clients have a null Basic-auth username.
- Uses a filtered unique index for non-null `api_username` values, preserving username uniqueness without modifying legacy API-key vendor rows.
- Adds regression coverage for the SQL Server predicate.
- Includes all UAT, integration, deployment tracking, follow-up, ticket automation, and branded report changes from `1.66.127`.
- Database compatibility remains `0259_deployment_follow_up`.
- Full verification: Ruff and strict MyPy passed across 202 backend source files; 544 backend tests and 121 frontend tests passed; TypeScript and production frontend builds passed.
- Bundled runtime help and clean/repeat migration through `0259_deployment_follow_up` passed.
- Artifact: `releases/SupportHub-1.66.128.zip`.

## 1.66.127 — 2026-10-10

Status: superseded before deployment; do not deploy because migration `0257` used a non-filtered SQL Server unique index for nullable usernames. Replaced by `1.66.128`.

- Adds UAT Product/Module filters, persistent test ordering, client-portal workspace visibility, and active-cycle editing.
- Expands third-party integrations for multiple vendors and sources with API Key or HTTP Basic authentication, direct/pre-ticket intake, and ticket-status synchronization.
- Adds simplified deployment planning, ordered live activities, comments, owners, planned versus actual time, and client-portal tracking.
- Adds deployment follow-up issues with status, priority, phase, owner, next action, resolution, and optional automatic incident-ticket creation.
- Adds deployment closure summaries, pending-phase insights, and branded PDF/Word reports named with the client and planned deployment date.
- Database compatibility advances to `0259_deployment_follow_up`.
- Full verification: Ruff and strict MyPy passed across 202 backend source files; 543 backend tests and 121 frontend tests passed; TypeScript and production frontend builds passed.
- Bundled Windows x64 runtime help and clean/repeat migration through `0259_deployment_follow_up` passed.
- Artifact: `releases/SupportHub-1.66.127.zip`.

## 1.66.126 — 2026-10-08

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Adds distinct Support Now shift time states: Upcoming, In progress, and Ended.
- Uses blue for upcoming, green for active, and a light neutral card with dark text for ended shifts.
- Refreshes the time state every 30 seconds without exposing permission-controlled engineer presence.
- Adds direct regression coverage for all three time states.
- Database compatibility remains `0255_uat_cycle_participants`.
- Full verification: 541 backend tests and 119 frontend tests passed; production frontend build passed.
- Packaged runtime help and clean SQLite migration to `0255_uat_cycle_participants` passed, including a second idempotent migration run.
- Artifact: `releases/SupportHub-1.66.126.zip` (53,740,043 bytes).
- SHA-256: `9AF1004317DF0D1A61589E827F96CB6300B0471F8E36906F898DCBE19C59F38D`.

## 1.66.125 — 2026-10-08

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Replaces the failure-prone WebGL management map with synchronously rendered bundled SVG country geometry.
- Removes external tiles, WebGL availability, load-event timing, and runtime layer registration from the widget.
- Preserves density coloring, hover counts, keyboard access, and client drill-down.
- Adds direct regression coverage for geometry rendering, country matching, density color, and click behavior.
- Reduces the UAT workspace to four focused areas, one cycle selector, and collapsed advanced tools.
- Replaces the three-step UAT wizard with one creation form and automatic code/name generation.
- Adds multiple UAT engineers, round-robin test ownership, and multiple Support-department coordinators.
- Includes the simplified UAT launch/import workflow delivered in `1.66.124`.
- Adds a preview-first transactional SQL Server script for resetting UAT-domain data and rebuilding clean masters.
- Database compatibility advances to `0255_uat_cycle_participants`.
- Full verification: 541 backend tests and 118 frontend tests passed; production frontend build passed.
- Packaged runtime help and clean SQLite migration to `0255_uat_cycle_participants` passed, including a second idempotent migration run.
- Artifact: `releases/SupportHub-1.66.125.zip` (53,741,526 bytes).
- SHA-256: `99D62EBF5B3799282D4B5896F8873FEEEE6BAC2D41A599E38CB0923052B44DB5`.

## 1.66.124 — 2026-10-08

Status: superseded before deployment; do not deploy. The release retained the MapLibre/WebGL initialization path responsible for repeated blank-map reports. Replaced by `1.66.125`.

- Simplifies UAT setup into Client, Templates, and Launch steps with immediate activation.
- Adds client coordinator and sign-off approver selection during launch and enables the main portal collaboration defaults.
- Adds a downloadable four-column UAT Excel starter and validated master-template import.
- Retains multiple-template assignment, lane workflows, failed-test ticket integration, client sign-off, and public stakeholder tracking.
- Reworks the self-contained management map with neutral land/sea styling, selective data colors, lighter visual effects, and stable resizing.
- Database compatibility remains `0254_shift_presence_permission`; no new migration is required.
- Backend Ruff and strict MyPy passed across 201 source files; all 540 backend tests passed.
- Frontend ESLint, all 117 Vitest tests, TypeScript compilation, and the production build passed.
- Packaged runtime help and clean migration through `0254_shift_presence_permission` passed.
- Manifest version/head, required contents, ZIP readability, 2,055 entries, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.124.zip`.

## 1.66.114 — 2026-10-03

Status: ready for controlled deployment; self-contained Windows x64 release built and verified.

- Adds the contextual Knowledge Base resolution library and ticket-resolution application workflow.
- Fixes leaked SQL Server `NOCOUNT` state that could produce false concurrency conflicts and disrupt scheduled escalation/email work.
- Adds defensive row-count normalization before scheduler stages.
- Database compatibility advances to `0245_knowledge_resolution`.
- Deployment requires migration followed by recycling every IIS application-pool worker.
- Backend Ruff and strict MyPy passed across 196 source files; all 506 backend tests passed.
- Frontend ESLint, all 100 Vitest tests, TypeScript compilation, and the production build passed.
- Packaged runtime help, clean and repeatable migration through `0245_knowledge_resolution`, manifest metadata, ZIP readability, required contents, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.114.zip` (53,173,111 bytes; 2,017 entries), SHA-256 `510C418E99E0157C731DC38B17CB0087D179C5CD07B3A08AD9744D3278CA6973`.

## 1.66.113 — 2026-10-03

Status: ready for controlled deployment; self-contained Windows x64 release built and verified.

- Adds an administrator-controlled option to require complete resolution details when closing tickets.
- Adds a permission-scoped Missing resolution queue to the Support Assistant.
- Aligns ticket-card resolution navigation with the configured close-time workflow.
- Includes the latest service-checklist board and checklist-workspace presentation updates.
- Retains database compatibility at `0244_checklist_default_template`; no new migration is required.
- Backend Ruff and strict MyPy passed across 196 source files; all 501 backend tests passed.
- Frontend ESLint, all 100 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest version `1.66.113`, database head `0244_checklist_default_template`, ZIP readability, standalone metadata, runtime presence, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.113.zip` (53,149,364 bytes; 2,016 entries), SHA-256 `C22505450B88E94D05654F2A17F2041A756BB0F9C9931627AB98BDA480CF7828`.

## 1.66.96 — 2026-09-30

Status: ready for controlled deployment; self-contained Windows x64 anti-spam hotfix release.

- Sends one contract-expiration SMTP message with real To and CC headers.
- Changes email-delivery deduplication to `(outbox_id, recipient_email)` for external recipients.
- Quarantines already-transmitted contract events stuck in processing so migration cannot trigger more copies.
- Adds 15-second delivery-activity refresh in the Contract workspace.
- Database compatibility advances to `0241_email_recipient_key`.
- Backend Ruff and strict MyPy passed across 196 source files; all 493 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.96`, database head `0241_email_recipient_key`, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.96.zip` (53,114,377 bytes; 2,011 entries).
- Final SHA-256: `E6EC04C7FF0B71270C62F36A2AA579F9E2F86ABB331E789FCBC4F73C938EA2DC`.

## 1.66.95 — 2026-09-30

Status: ready for controlled deployment; self-contained Windows x64 hotfix release.

- Fixes SQL Server rejecting multiple contract-notification ledger rows because nullable notification/outbox references were globally unique.
- Fixes the 500 response when saving a rule with separate To and CC users.
- Makes rule persistence and immediate evaluation atomic.
- Retains global milestone catch-up and branded contract-expiration HTML email delivery.
- Database compatibility advances to `0240_contract_notify_null`.
- Backend Ruff and strict MyPy passed across 196 source files; all 493 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.95`, database head `0240_contract_notify_null`, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.95.zip` (53,109,330 bytes; 2,010 entries).
- Final SHA-256: `70CDAB477DBD3E52DB8E0AAC9167F90CE3B593D4E4B162B2A6CE49F331F13BEB`.

## 1.66.94 — 2026-09-30

Status: ready for controlled deployment; self-contained Windows x64 release.

- Fixes future contract renewal-notice dates suppressing configured expiration reminders.
- Applies the nearest missed global milestone once, including the seven-day milestone for a contract with two days remaining.
- Formats contract-expiration messages using the standard responsive Millensys Support Hub branded HTML email.
- Adds a Contract Expiration badge and contract-workspace action link while retaining a plain-text alternative.
- Database compatibility remains `0239_contract_notify_log`; no new migration is required from `1.66.93`.
- Backend Ruff and strict MyPy passed across 196 source files; all 493 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.94`, database head `0239_contract_notify_log`, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.94.zip` (53,108,156 bytes; 2,009 entries).
- Final SHA-256: `8CDDF2D15BB0A953DEDB9016C59330A06EAB616D545FDE260648EB7C5C443A08`.

## 1.66.92 — 2026-09-30

Status: ready for controlled deployment; self-contained Windows x64 release generated and verified.

- Adds governed Contract workspace configuration for expiration reminder days, To/CC recipients, and email templates.
- Queues durable, deduplicated expiration emails while retaining in-app renewal reminders.
- Adds the assignable `contract.notification_rules.manage` permission with Administrator access by default.
- Database compatibility revision advances to `0238_contract_notify_perm`.
- Backend Ruff and strict MyPy passed across 196 source files; all 493 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.92`, database head `0238_contract_notify_perm`, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.92.zip` (53,093,116 bytes; 2,008 entries).
- Final SHA-256: `09E42DEC0197501D03B02369552EF7C035613DFEC76B59073AE5CCE4ED96D227`.

## 1.66.91 — 2026-09-30

Status: ready for controlled deployment; self-contained Windows x64 release generated and verified.

- Enables approved-template and similar-ticket discovery from three characters, including technical keywords such as `HL7`.
- Applies the same discovery threshold to Ticket and Pre-Ticket creation while retaining the final ticket-subject validation rule.
- Fixes the Support Assistant invalid-data error caused by requesting an Operations count through the ticket queue API.
- Database compatibility revision remains `0237_escalation_work_queue`; no migration is introduced.
- Backend Ruff and strict MyPy passed across 196 source files; all 491 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.91`, database head `0237_escalation_work_queue`, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.91.zip` (53,079,813 bytes; 2,007 entries).
- Final SHA-256: `BE880AC027C42421752CEA09923334FF4BF3DE02FDFAA661CA749011DE76CB96`.

## 1.66.90 — 2026-09-30

Status: ready for controlled deployment; self-contained Windows x64 release.

- Adds peer multi-client contract editing, linked-client contacts and branches, approval-group selection, date-aligned coverage, and renewal hardening.
- Corrects service-checklist monitoring so current overdue and blocked work is not hidden by future generated occurrences.
- Enforces checklist evidence, handoff, terminal-state, ticket synchronization, pause, retirement, import, and public-sharing safeguards.
- Database compatibility remains at `0237_escalation_work_queue`; no migration is introduced.
- Backend Ruff and strict MyPy passed across 196 source files; all 491 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.90`, database head `0237_escalation_work_queue`, ZIP readability, forbidden-file inspection, and standalone packaging passed.
- Final artifact: `releases/SupportHub-1.66.90.zip` (53,079,314 bytes; 2,007 entries).
- Final SHA-256: `564F2A67E6AF0DBCF397148EDC06045A4DB9791042443699E9C6CE21E3193D7F`.

## 1.66.86 — 2026-09-28

Status: Checklist row-save HTTP-method patch self-contained Windows x64 release prepared for controlled deployment.

- Fixes the checklist execution UI sending `POST` to the row-update endpoint.
- Uses the backend's supported `PUT` contract for individual checklist row saves.
- Retains `POST` for workflow commands and client handoff actions.
- Database compatibility remains at `0234_simple_checklist_rows`; no migration is introduced.

## 1.66.85 — 2026-09-28

Status: Checklist client-lookup patch self-contained Windows x64 release prepared for controlled deployment.

- Fixes the checklist assignment page's invalid 500-row client request.
- Retrieves every client through supported 200-row paginated requests.
- Includes inactive clients so existing plans retain their client names in management views.
- Database compatibility remains at `0234_simple_checklist_rows`; no migration is introduced.

## 1.66.84 — 2026-09-28

Status: Bulk checklist-plan management self-contained Windows x64 release prepared for controlled deployment.

- Adds bulk client assignment to one engineer and published template.
- Adds audited individual and bulk plan transfer while preserving completed history.
- Moves unfinished checklist work to the new engineer.
- Removes timezone from checklist assignment forms and Excel import/export, using the central server clock.
- Keeps the client-engineer-template master-data relationship and highlighted example row.
- Database compatibility remains at `0234_simple_checklist_rows`; no migration is introduced.

## 1.66.83 — 2026-09-28

Status: Service-checklist assignment and scheduler-hardening self-contained Windows x64 release prepared for controlled deployment.

- Adds role-scoped Client Assignments and Engineer Board tabs.
- Supports manager reassignment of recurring client work and unfinished occurrences.
- Adds Excel assignment-template export and validated master-data import.
- Shows team completion, open work, client responsibility, progress, due dates, and evidence gaps.
- Bounds scheduler SLA and Outlook workloads and releases stage resources between cycles.
- Database compatibility remains at `0234_simple_checklist_rows`; no migration is introduced.

## 1.66.82 — 2026-09-27

Status: Simplified service-checklist self-contained Windows x64 release prepared for controlled deployment.

- Adds the Excel-style checklist row workflow and four requested statuses.
- Adds unfinished checklist monitoring by engineer and client.
- Carries client-specific row configuration forward to future occurrences.
- Sends deduplicated due/overdue email reminders.
- Creates a linked Closed ticket only when a checklist is completed.
- Database revision: `0234_simple_checklist_rows`.

## 1.66.81 — 2026-09-27

Status: Ticket-board self-assignment self-contained Windows x64 release prepared for controlled deployment.

- Makes a drop into Assigned claim an unassigned/shared ticket for the logged-in user.
- Enforces `ticket.assign.self` independently from team assignment authority.
- Atomically assigns and advances New, Triaged and Reopened tickets to Assigned.
- Prevents self-assignment permission from assigning another engineer or team.
- Prevents a newly logged-in account from inheriting the explicitly logged-out user's last route.
- Adds a checklist-specific active-employee lookup governed by checklist permissions instead of `user.manage`.
- Defaults new recurring checklist schedules to the logged-in creator while retaining the eligible-engineer selector.
- Database compatibility remains at `0233_ticket_reports`; no migration is introduced.

## 1.66.80 — 2026-09-27

Status: Scheduler-performance and HTTP clipboard self-contained Windows x64 release prepared for controlled deployment.

- Replaces per-clock ticket, policy, business-calendar, holiday, recipient and escalation-event reads with bulk cycle preloads.
- Adds total and per-stage scheduler timings to the administrator System Operations view.
- Adds an HTTP-compatible clipboard fallback and manual-copy recovery for rating and live-tracking messages.
- Packages a two-process baseline while preserving operator control of the deployed `web.config`.
- Database compatibility remains at `0233_ticket_reports`; no migration is introduced.

## 1.66.79 — 2026-09-27

Status: Self-contained Windows x64 release prepared for controlled deployment.

- Packages the validated `1.66.78` ticket date/time filters, access-placeholder correction and HTTP-LAN UUID startup hardening.
- Includes its own backend runtime and does not require a server Python installation.
- Database compatibility remains at `0233_ticket_reports`; no migration is introduced.
- PWA installation requires HTTPS in Chrome or Edge and is not offered by plain HTTP or embedded Assistant webviews.

## 1.66.78 — 2026-09-27

Status: Ticket date-and-time filter self-contained Windows x64 release prepared for controlled deployment.

- Upgrades Tickets custom and advanced date filters to exact date/time controls across created, updated, assigned, resolved, first-occurred and closed timestamps.
- Retains legacy whole-day behavior for presets, saved views and URLs containing date-only boundaries.
- Adds API regression coverage for exact timestamp filtering while preserving the existing date-only contract.
- Prevents the access dialog from querying or granting the placeholder `unknown` capability on unmapped routes.
- Loads the UUID compatibility layer at the SupportHub entry point to remove startup-order gaps on HTTP LAN origins.
- Database compatibility remains at `0233_ticket_reports`; no migration is introduced.
- Deploy the packaged frontend and backend together because both layers implement the feature.

## 1.66.77 — 2026-09-27

Status: Millensys brand-theme self-contained Windows x64 release prepared for controlled deployment.

- Adds the Millensys Brand light/dark theme using the corporate `#02303F`, `#13778F` and `#96BDF4` palette.
- Retains the complete `1.66.76` LAN staging compatibility, theme collection, Support Assistant scrolling and preference corrections.
- Database compatibility remains at `0233_ticket_reports`; no migration is introduced.
- Deploy the packaged frontend and backend together because theme identifiers are backend-validated.

## 1.66.76 — 2026-09-27

Status: LAN staging compatibility and modern theme self-contained Windows x64 release prepared for controlled deployment.

- Adds a cryptographically strong UUID fallback for HTTP LAN staging origins where `crypto.randomUUID` is unavailable.
- Makes Support Assistant tabs scrollable on touch devices and compact layouts.
- Clears unavailable hidden saved-view preferences instead of blocking profile updates.
- Adds six light/dark modern themes: Aurora Glow, Sakura Bloom, Neon Pulse, Modern Mocha, Arctic Glass and Obsidian Gold.
- Database compatibility remains at `0233_ticket_reports`; no migration is introduced.
- Deploy the packaged frontend and backend together because the expanded theme whitelist is enforced by the backend.

## 1.66.73 — 2026-09-26

Status: ticket reports and client action dialog self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds closed-ticket Incident Report and Ticket Report workflows with completion forms for missing manual data.
- Adds a Tickets Reports tab, versioned PDFs, mobile-responsive public share links, downloads, and configured-base-URL link generation.
- Enhances client access and contact actions with dialogs, inline access management, WhatsApp, rating, live-tracking, copy-message, and optional delivery actions.
- Adds `docs/APPROVAL_ENHANCEMENTS.md` as a planning-only specification; approval behavior is not changed in this release.
- Database revision: `0233_ticket_reports`.
- Backend Ruff and strict MyPy passed; all 451 backend tests passed.
- Frontend ESLint, all 87 Vitest tests, TypeScript compilation and the production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.73`, database head `0233_ticket_reports`, ZIP readability and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.73.zip` (52,857,386 bytes; 1,981 entries).
- SHA-256: `F9259FF5378E0844E8D2958E10AB954F7C368150F1043C24A63E390116F6591A`.

## 1.66.72 — 2026-09-25

Status: contact-ticket filtering self-contained Windows x64 release built and verified; ready for controlled deployment.

- Corrects Show contact tickets to retain and apply the selected caller ID.
- Adds frontend and backend regression coverage excluding unrelated tickets.
- Database compatibility remains at `0232_manual_org_chart`.
- Backend Ruff and strict MyPy passed; all 449 backend tests passed.
- Frontend ESLint, all 87 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.72.zip` (52,810,230 bytes; 1,971 entries).
- SHA-256: `DE045C8C5B5781EE7E8AEFA79BF25E90AEF9523652BDEDA68C50D23A431C851D`.

## 1.66.71 — 2026-09-25

Status: dedicated client action self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds a permission-controlled Edit access action from the ticket client menu.
- Routes client access, information, contacts, profile, and tickets actions to dedicated destinations.
- Database compatibility remains at `0232_manual_org_chart`.
- Backend Ruff and strict MyPy passed; all 449 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.71.zip` (52,809,650 bytes; 1,971 entries).
- SHA-256: `0214D7E00ED03B8C68D1239C71F8E92078E00309A77812BEEF9304B7BC1645C7`.

## 1.66.70 — 2026-09-25

Status: ticket caller, client, and flag action self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds Contact / Caller and Flags ticket-list columns.
- Adds direct caller and client action menus.
- Adds the inline flag dialog to the ticket row context menu.
- Database compatibility remains at `0232_manual_org_chart`.
- Backend Ruff and strict MyPy passed; all 449 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation, and the production build passed.
- Artifact: `releases/SupportHub-1.66.70.zip` (52,811,055 bytes; 1,971 entries).
- SHA-256: `1A737E5CE04B2E4F19CF39DC2C8DB02319576D80D2F98A8CF586E7B7EFECE6BD`.

## 1.66.69 — 2026-09-25

Status: manual organization hierarchy self-contained Windows x64 release built and verified; ready for controlled deployment.

- Replaces the department-based hierarchy presentation with a standalone manually configured organization chart.
- Supports executives, managers, teams, team members, and custom roles with independent names, titles, portraits, contact details, notes, parent relationships, status, and ordering.
- Adds modern portrait-over-card presentation, distinct team cards, connecting lines, search, and separate read/configuration modes.
- Adds cycle prevention, child-delete protection, permission enforcement, and audit logging.
- Adds database revision `0232_manual_org_chart`.
- Backend Ruff and strict MyPy passed; all 448 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.69`, database head `0232_manual_org_chart`, required contents, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.69.zip` (52,807,675 bytes; 1,971 entries).
- SHA-256: `31E6DD6F851BDA892D0691FA109EC022BE1C2FA7908E67D0065D74E388F1829A`.

## 1.66.68 — 2026-09-24

Status: department hierarchy self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds the dedicated department hierarchy tree and configuration workspace.
- Supports effective-dated parent and department-head assignments, historical as-of views, hierarchy paths, and vacancy presentation.
- Supports staged multi-department changes with atomic publishing.
- Enforces cycle, self-parent, missing-parent, effective-period overlap, authorization, and audit controls.
- Database compatibility remains at the current migration head; no new schema migration is introduced.
- Backend Ruff and strict MyPy passed; all 447 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.68`, database head `0231_sla_client_dependency_flags`, required contents, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.68.zip` (52,798,177 bytes; 1,970 entries).
- SHA-256: `31FDA343E3CDEFABF25D13A07C6229FCA85E1CF82B95DCB389001AF18A09731A`.

## 1.66.60 — 2026-09-23

Status: ready for controlled deployment; self-contained Windows x64 release.

- Adds reusable News post templates with a dedicated Templates workspace.
- Adds template creation, editing, deletion, reuse and **Save as template** actions.
- Corrects draft preview actions and prevents templates from being published directly.
- Database compatibility revision: `0226_news_templates`.
- Backend focused validation and frontend lint, TypeScript and all 86 tests passed before packaging.

## 1.66.59 — 2026-09-23

Status: SQL Server News migration correction prepared for self-contained Windows x64 release.

- Corrected SQL Server error 1785 in `0225_news_engagement` by removing the redundant direct post-to-vote delete cascade.
- Preserved cascade cleanup through `news_poll_options` and added a SQL Server migration regression test.
- Includes the complete interactive News announcement feature set from `1.66.58`.
- Database compatibility revision: `0225_news_engagement`.
- Backend Ruff and strict MyPy passed; all 437 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation and production build passed.
- Corrected migration text, runtime commands, manifest, ZIP readability and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.59.zip` (52,726,464 bytes; 1,956 entries).
- SHA-256: `44B5959E341F9DDE99A07EE2231917A05C69F0610A9B1CC964B702965260282F`.

## 1.66.58 — 2026-09-23

Status: Interactive News announcement self-contained Windows x64 release prepared for controlled deployment.

- Added an automatic post-login News announcement popup with image and video presentation.
- Added explicit Save draft, Publish now and Unpublish workflows and corrected unpublished draft previews.
- Added optional likes, comments, single-choice polls and user mentions.
- Added in-app notifications for users mentioned in a published News post.
- Preserved confirmation, dismissal, audience, scheduling and expiry behavior.
- Database compatibility revision: `0225_news_engagement`.
- Backend Ruff and strict MyPy passed; all 436 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest, required contents, ZIP readability and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.58.zip` (52,726,573 bytes; 1,956 entries).
- SHA-256: `9234B79FE20A7B84557159AA78E788269844146BE69E19060D3097ADCE14907C`.

## 1.66.57 — 2026-09-23

Status: News Center and compact Tickets workspace self-contained Windows x64 release prepared for controlled deployment.

- Added the bilingual employee and Client Portal News Center with reusable content templates, cover images and controlled YouTube/Vimeo media.
- Added scheduled publication, expiry, audience selection, featured news, manual publish/unpublish and publisher confirmation counts.
- Added per-user confirmation and dismissal state with audited publishing lifecycle actions.
- Added the `news.view`, `news.create`, `news.publish`, `news.manage` and `news.analytics` permission model.
- Compacted Tickets breadcrumb/header/quick-view surfaces and replaced the large empty state with an inline contextual message.
- Database compatibility revision: `0224_news_center`.

## 1.66.56 — 2026-09-23

Status: AI-provider and workspace-UX self-contained Windows x64 release prepared for controlled deployment.

- Added optional OpenAI Responses API ticket analysis alongside local Ollama, with strict structured output and provider-aware health checks.
- Added protected Site Settings controls for AI provider, model and masked API-key configuration without database or audit secret persistence.
- Simplified Tickets navigation, header, actions and filter surfaces.
- Made dashboard/report widget drill-down filters replace stale local and saved-view ticket filters.
- Reorganized Master Data with category tabs and one searchable section selector while preserving existing catalog workflows.
- Added English and Arabic labels for the new Master Data controls.
- Database compatibility remains at the current migration head; no migration is introduced.
- Backend Ruff and strict MyPy passed; all 433 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.56`, database head `0223_vendor_pre_ticket_api`, self-contained deployment mode, required contents, ZIP readability and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.56.zip` (52,683,282 bytes; 1,945 entries).
- SHA-256: `13661CCC538FCF6908B8AF17DFAB3074281342E1B85D2F61FD8E05E130050C9D`.

## 1.66.55 — 2026-09-23

- Added API-only users and profiles with short-lived integration tokens.
- Added direct WhatsApp/email/general Pre-Ticket API with optional client matching, idempotency and transaction status.
- Added single-use hosted external Pre-Ticket forms for client-bound external-system launches.
- Added vendor-specific API documentation downloads.
- Added configurable Local AI intake instructions, faithful Arabic-to-English output, Arabic catalog matching and unique phonetic client matching.
- Branch remains optional and unknown/ambiguous clients enter manual review without losing the Pre-Ticket.
- Database compatibility revision: `0223_vendor_pre_ticket_api`.

## 1.66.54 — 2026-09-22

Status: local AI client detection and CPU performance release prepared for self-contained Windows x64 packaging.

- Detects an explicitly named client from a bounded active-client shortlist and validates it against governed master data before applying it to ticket creation.
- Produces a professional subject and description with safe non-empty fallbacks and validates product/module suggestions against active catalogs.
- Adds healthcare-system guidance for HIS, RIS, PACS, DICOM, modality worklist, image routing, reporting, integrations, and ERP terminology.
- Changes the packaged local model default from `qwen2.5:7b` to CPU-friendlier `qwen2.5:3b`.
- Keeps the model resident, constrains context/output, uses structured JSON output, bounds retrieval input, and records non-sensitive Ollama timing metrics.
- Adds governed Local server and Remote server modes in Site Settings, a server-side physical-folder browser and validation for local installations, plus an immediate connection test.
- Database compatibility revision remains `0222_uat_template_clients`; no migration is introduced.

## 1.66.53 — 2026-09-22

Status: client UAT interaction and Support Now counting correction prepared for self-contained Windows x64 release.

- Makes the client UAT workspace resilient when browser storage is restricted.
- Opens UAT cards in a details drawer and restores explicit status, drag-and-drop and right-click actions.
- Adds separate Waiting for approval and Pending tickets cards to Support Now.
- Excludes pending tickets from Open tickets and limits Need attention to actionable tickets approaching today's SLA deadline.
- Database compatibility revision remains `0222_uat_template_clients`; no new migration is introduced.

## 1.66.52 — 2026-09-21

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Adds responsive List and Board views to the client UAT portal.
- Adds colored workflow lanes, modern cards/rows, search, filtering, remembered layout and client-safe quick/right-click result actions.
- Preserves portal assignment, permissions, sign-off, collaboration, evidence and linked-defect restrictions.
- Database compatibility revision remains `0222_uat_template_clients`; no new migration is introduced.
- Backend Ruff and strict MyPy passed; all 425 backend tests passed.
- Frontend ESLint, all 82 Vitest tests, TypeScript compilation and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed` and `recover-admin`; manifest and ZIP checks passed.

## 1.66.51 — 2026-09-21

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Keeps UAT master templates client-independent and selects the client only when starting a cycle.
- Adds named master-template Excel import with automatic codes and portable Product, Module and Feature data.
- Adds the Needs Investigation failure gate, client portal options and inline evidence preview.
- Modernizes the UAT board and list with colored workflow states, ticket-style cards, quick status controls and right-click actions.
- Database compatibility revision remains `0222_uat_template_clients`; no new migration is introduced.
- Makes the optional local AI service directory portable and keeps its backend service address configurable through `LOCAL_AI_BASE_URL`.
- Backend Ruff and strict MyPy passed; all 425 backend tests passed.
- Frontend ESLint, all 82 Vitest tests, TypeScript compilation and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed` and `recover-admin`; manifest, ZIP integrity and forbidden-file checks passed.

## 1.66.50 — 2026-09-21

Status: reusable UAT workflow and client portal correction prepared for self-contained Windows x64 release.

- Adds multi-client reusable UAT templates with portable Excel export and import.
- Adds the four-step cycle wizard and ticket-style list/board workspace with controlled drag and drop.
- Moves test execution into a focused action drawer.
- Removes Support Now from client portal navigation, preferences and direct route access.
- Database compatibility revision: `0222_uat_template_clients`.
- Backend Ruff and strict MyPy passed; all 424 backend tests passed.
- Frontend ESLint, all 82 Vitest tests, TypeScript compilation and production build passed.

## 1.66.48 — 2026-09-20

Status: customer work-hour widget corrections prepared for self-contained Windows x64 release.

- Enables the Executive customer consumption and work-hour queries.
- Includes Resolved and Closed ticket SLA evidence in the Client working and saved hours widget.
- Uses approved worklogs and completed SLA time as distinct fallback sources in Support work hours per customer.
- Database head remains `0206_ticket_flags`; no schema migration is introduced.

## 1.66.47 — 2026-09-20

Status: client profile and dashboard corrections prepared for self-contained Windows x64 release.

- Counts completed resolution SLA evidence for Resolved or Closed tickets in the client profile and client hours summary.
- Keeps reopened tickets excluded and adds a resolved-ticket regression check.
- Adds personal layout controls to Support Now and main Executive widgets.
- Removes the duplicate attention list and aligns the Need attention card link with its count.
- Adds Top 3 Agents, status and priority charts, and a seven-day ticket creation chart to Support Now.
- Database head remains `0206_ticket_flags`; no schema migration is introduced.

## 1.66.46 — 2026-09-20

Status: client-hours widget paging and matching client-profile dates prepared for self-contained Windows x64 release.

- Shows three client rows per page across all dashboards using the shared widget.
- Passes the widget date range to the client profile when opening a row.
- Aligns the widget and profile eligibility for closed tickets, with a reopened-ticket regression check.
- Database head remains `0206_ticket_flags`; no schema migration is introduced.

## 1.66.45 — 2026-09-20

Status: client-hours correction prepared for self-contained Windows x64 release.

- Prevents a 500 response when historical ticket hours belong to an inactive client.
- Database head remains `0206_ticket_flags`; no schema migration is introduced.
- Added an inactive-client hours API regression check.

## 1.66.44 — 2026-09-20

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Adds reusable SLA master data and contract-specific target editing in the contract workspace.
- Publishes target-bearing SLA versions on active changes and requires a current publication for contract linking and ticket clocks.
- Uses product and effective-date target selection consistently and reports missing or ambiguous SLA coverage.
- Adds master-policy usage counts and contract P1–P4 coverage preview.
- Adds client working, SLA target, and saved-hour widgets across Support Now, client profile, Executive, and Top Management dashboards, including widget catalog and customization support.
- Database head remains `0206_ticket_flags`; run seed during deployment to repair the default SLA snapshot where needed.
- Production SLA creation error still requires the exact API response and deployed database state for diagnosis.
- Backend Ruff and strict MyPy passed; all 406 backend tests passed.
- Frontend ESLint, all 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`; manifest and ZIP integrity checks passed.


## 1.66.43 — 2026-09-19

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Adds personal Quick Actions visibility and draggable, saved button position.
- Removes the duplicate Support Assistant page header and corrects the Tickets row-count menu placement.
- Shows approved customer work hours in a per-client chart with dashboard filters.
- Packages optional default SLA and legacy root-cause classification SQL scripts.
- Database head remains `0206_ticket_flags`; no additional migration is introduced.
- Backend Ruff and strict MyPy passed; all 404 backend tests passed.
- Frontend ESLint, all 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`; manifest and ZIP integrity checks passed.
- Final artifact: `releases/SupportHub-1.66.43.zip` (43,416,178 bytes; 1,846 entries), SHA-256 `7F45925490CBE4F32936B1AA1EF0574064F92809217BB7A7E15C106E2478597E`.

## 1.66.42 — 2026-09-19

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Adds management support-consumption and approved-work-hours measures and an editable Word analysis export.
- Corrects historical SLA calculations and executive response and resolution statistics.
- Includes contract and dashboard corrections since `1.66.41`.
- Database head remains `0206_ticket_flags`; no additional migration is introduced.
- Backend Ruff and strict MyPy passed; all 404 backend tests passed.
- Frontend ESLint, all 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`; manifest and ZIP integrity checks passed.
- Final artifact: `releases/SupportHub-1.66.42.zip` (43,411,619 bytes; 1,844 entries), SHA-256 `2F78C139725CA728896BBD6302B7A49E2277B4BA85102A69BFC41D03260A9233`.


## 1.66.41 — 2026-09-15

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Corrects Quick Actions ticket creation: Create closes the dialog, while Create and new resets it for another ticket.
- Unifies context actions across web card/list views and Support Assistant right-click/three-dot menus.
- Places shared Pin/Unpin first, organizes frequent actions under Common actions, and exposes secondary actions from a hover submenu.
- Makes View status history show explicit previous-to-new status transitions with reason, actor, and timestamp.
- Corrects SLA-target removal for contracts linked to shared central policies without modifying the shared policy or other contracts.
- Adds atomic multi-client Visit Entitlement creation with a checkbox multi-select in the contract workspace.
- Database head remains `0206_ticket_flags`; no additional migration is introduced.
- Backend Ruff and strict MyPy passed; all 404 backend tests passed.
- Frontend ESLint, Vitest, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`; manifest and ZIP integrity checks passed.
- Final artifact: `releases/SupportHub-1.66.41.zip` (43,396,626 bytes; 1,844 entries), SHA-256 `76C567E2587BB56DF2A1A24A310C5D6553C6B2139725E6200D287F000A352C4C`.


## 1.66.40 — 2026-09-15

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Makes Assistant preference saves resilient to deleted stale pinned-ticket IDs.
- Restores the compact circular `+` Quick Actions trigger while retaining its click-open menu.
- Database head remains `0206_ticket_flags`; no additional migration is introduced.
- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 31 test files and 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`; manifest and ZIP integrity checks passed (1,844 initial entries).
- Final artifact: `releases/SupportHub-1.66.40.zip` (43,395,250 bytes), SHA-256 `5F799BA89B797487839595D13E662DAB8063326C9F19CF64F2CD1FC190415DC0`.


## 1.66.39 — 2026-09-15

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Replaces the Support Now planner list with a real calendar and keeps double-click creation in dialogs.
- Makes Quick Actions click-open, labeled, length-sorted, colored, and dialog-based.
- Aligns web and Support Assistant ticket context actions and removes the duplicate Customer Contact entry.
- Database head remains `0206_ticket_flags`; no additional migration is introduced.
- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 31 test files and 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`; manifest and ZIP integrity checks passed (1,844 entries).
- Final artifact: `releases/SupportHub-1.66.39.zip` (43,396,506 bytes), SHA-256 `D81B48EA3DAE9961B47AD08C2400288342359E9C551258DF3BF9412DB2088374`.


## 1.66.38 — 2026-09-15

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Delivers Support Now navigation/home enhancements, planner and operation workflows, ticket and operation approvals, and Assistant Ops access.
- Adds governed ticket flags with optional SLA pause/resume and ticket/Assistant context actions.
- Corrects saved-view date-filter noise and replaces verbose UI transport errors with concise recovery hints while preserving diagnostics.
- Removes duplicate ticket-creation buttons and their redundant access request from Support Assistant.
- Database head advances to `0206_ticket_flags`; run the packaged migration and seed commands during deployment.
- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 31 test files and 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`; manifest and ZIP integrity checks passed (1,847 entries).
- Final artifact: `releases/SupportHub-1.66.38.zip` (43,395,723 bytes), SHA-256 `FB6A67EEC5F7955773841492FDED7C6218DCD0B07D94ECE5F38BF732A5EF33D6`.


## 1.66.37 — 2026-09-14

Status: corrective self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Restores the Dashboard sidebar link on desktop when `dashboard.agent` or `dashboard.manager` is granted.
- Keeps Home as the default landing page and includes all functionality from `1.66.36`.
- Database head remains `0205_self_field_visit`; no additional migration is introduced.
- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 78 tests, TypeScript compilation, and production build passed.
- Runtime commands, manifest, ZIP readability, and forbidden-file inspection passed (1,840 entries).
- Initial artifact: `releases/SupportHub-1.66.37.zip` (43,371,782 bytes), SHA-256 `CCCA6BB673DB4B520CE89852CB076D27E982268C1778109B46216FD1F29B652C`.


## 1.66.36 — 2026-09-14

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Adds the lightweight responsive Support Operations Home as the default post-login page.
- Adds permission-aware desktop/mobile Quick Actions and the self-assigned field-visit approval workflow.
- Corrects relative saved-view dates, raises the standard API timeout to 30 seconds, and improves gateway/timeout messages.
- Advances the database head to `0205_self_field_visit`; migration and profile assignment of `visit.field.create.self` are required.
- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 78 tests, TypeScript compilation, and production build passed.
- Runtime commands, manifest, required contents, ZIP readability, and forbidden-file inspection passed (1,840 entries).
- Initial artifact: `releases/SupportHub-1.66.36.zip` (43,371,836 bytes), SHA-256 `8E7559BCD917026BEB239A4852D4F21937D2E34038A85FF315B914EF30C357B7`.


## 1.66.35 — 2026-09-14

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Optimizes dashboard filter metadata and online-engineer aggregation to reduce SQL Server load and connection-pool occupancy.
- Adds bounded recovery for transient `502`, `503`, and `504` responses on read-only frontend requests.
- Extends the analytical timeout to dashboard metadata and online-engineer requests without weakening the ordinary API timeout.
- Database head remains `0203_checklist_schedules`; no new migration is introduced.
- Backend Ruff and strict MyPy passed; all 401 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and production build passed.
- Runtime commands, manifest, required contents, ZIP readability, and forbidden-file inspection passed (1,830 entries).
- Initial artifact: `releases/SupportHub-1.66.35.zip` (43,343,240 bytes).
- Initial SHA-256: `AF9792169B54F5BDBF610F86C53A5BBD0B387CF2A7170EFA44E60008E32569F6`.
- Final artifact after documentation refresh: `releases/SupportHub-1.66.35.zip` (43,343,580 bytes; 1,830 entries).
- Final SHA-256: `99F21011B4C4A38E384342678DFF877DDCF8B4090160160E360887F93F207B61`.


## 1.66.34 — 2026-09-13

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Supersedes withdrawn `1.66.33` with corrected clean-install compatibility for migration `0197_ticket_requirements`.
- Includes governed Service Checklists, Client-responsible evidence, smoother world-map rendering, and batched Tickets list enrichment.
- Advances the database head to `0203_checklist_schedules`; migration is required.
- Backend Ruff and strict MyPy passed; all 401 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and production build passed.
- Source and packaged-runtime clean migrations completed through `0203_checklist_schedules`.
- Runtime commands, manifest, required contents, ZIP readability, and forbidden-file inspection passed (1,830 entries).
- Artifact before final documentation refresh: `releases/SupportHub-1.66.34.zip` (43,344,981 bytes).
- Initial SHA-256: `4A2E128210FBCE7E6F083945DE16686D1FBCBC7C991F7CB542B98C6D2B8156FD`.
- Final artifact: `releases/SupportHub-1.66.34.zip` (43,345,346 bytes; 1,830 entries).
- Final SHA-256: `9BF03B07E92F8C7FC0A03BE057D5E632302E5F93B045D3B13A04C95598689119`.


## 1.66.33 — 2026-09-13

Status: withdrawn before deployment; do not deploy. Packaged clean-install rehearsal exposed a duplicate-column compatibility defect in migration `0197_ticket_requirements`. Superseded by `1.66.34`.

- Adds governed Service Checklists with templates, schedules, card lanes, task progression, ticket creation, and completion evidence.
- Supports Client-responsible checklist tasks with mandatory attached evidence and exclusion from scheduling completion requirements.
- Makes the Top Management world map smoother and less expensive to render while improving light/dark appearance.
- Removes per-ticket database query amplification from the Tickets list SLA and queue evidence enrichment.
- Advances the database head to `0203_checklist_schedules`; migration is required.
- Artifact target: `releases/SupportHub-1.66.33.zip`.


## 1.66.32 — 2026-09-13

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Corrects the Top Management world map for both light and dark themes with theme-aware oceans, land, borders, grid, shadows, supported-market colors, hover cards, client text, and legend chips.
- Improves hover contrast and tooltip positioning while retaining client names, keyboard focus, and country drill-down behavior.
- Leaves all Tickets and Support Assistant right-click and fast-action menus unchanged.
- Database head remains `0199_ticket_templates`; no migration is required.
- Backend Ruff and strict MyPy passed; all 397 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, database head, deployment mode, required contents, ZIP readability, and forbidden-file inspection passed (1,813 entries).
- Artifact before final documentation refresh: `releases/SupportHub-1.66.32.zip` (43,255,673 bytes).
- Initial SHA-256: `E258EDC52C8F75462BC5F914511C1E7C21123E28EBF74BEBC96A398639DB9DFD`.
- Final artifact after documentation refresh: `releases/SupportHub-1.66.32.zip` (43,255,927 bytes; 1,813 entries).
- Final SHA-256: `C35AA4534FB74C4CDC8068443F32BF216D442677327152F678A980DA4A296D78`.


## 1.66.30 — 2026-09-13

Status: withdrawn before deployment; do not deploy. The standard builder produced a source-only package without the required self-contained Windows runtime. Replaced by `1.66.31`.

- Modernizes the Top Management world map with responsive heat styling, hover highlighting, supported-client names, accessible focus behavior, and country drill-downs.
- Makes notification WebSocket tickets portable across the four production backend workers by replacing process-local ticket storage with short-lived signed tickets.
- Modernizes the shared HTML email presentation used by Support Hub notifications.
- Separates ticket-template suggestions from similar-ticket lookup: normal subjects show templates, while a trailing `*` explicitly searches similar tickets and is removed before submission in Ticket and Pre-Ticket creation.
- Adds permission-controlled ticket-template management with edit and soft-delete actions.
- Organizes long Tickets and Support Assistant context menus into grouped fast-action sections and adds Open WhatsApp when a usable client contact number is available.
- Database head remains `0199_ticket_templates`; no migration is required.


## 1.66.31 — 2026-09-13

Status: self-contained Windows x64 release generated and verified; ready for controlled deployment.

- Replaces withdrawn source-only package `1.66.30` with the required self-contained Windows x64 deployment.
- Modernizes the Top Management world map with responsive heat styling, hover highlighting, supported-client names, accessible focus behavior, and country drill-downs.
- Makes notification WebSocket tickets portable across the four production backend workers by replacing process-local ticket storage with short-lived signed tickets.
- Modernizes the shared HTML email presentation used by Support Hub notifications.
- Separates ticket-template suggestions from similar-ticket lookup and adds permission-controlled template editing and soft deletion.
- Organizes Tickets and Support Assistant fast actions and adds Open WhatsApp when a usable client contact number is available.
- Database head remains `0199_ticket_templates`; no migration is required.
- Backend Ruff and strict MyPy passed; all 397 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, database head, deployment mode, required contents, ZIP readability, and forbidden-file inspection passed (1,813 entries).
- Artifact before final documentation refresh: `releases/SupportHub-1.66.31.zip` (43,254,911 bytes).
- Initial SHA-256: `09188770583C23830BE218886A1F6FC00FD5DFA8F5B1F302BB4469E2C24E34A0`.
- Final artifact after documentation refresh: `releases/SupportHub-1.66.31.zip` (43,255,159 bytes; 1,813 entries).
- Final SHA-256: `A86FBE1E82A09D6650BCDB235AF18B1B5BCA39406F56CB67572D51382E617CD7`.


## 1.66.29 — 2026-09-13

Status: self-contained Windows x64 release generated and verified.

- Adds permission-controlled ticket mentions with access-filtered recipients across employees, Client Portal users, and other active users.
- Adds email and in-system mention notifications, optional follower addition, consolidated outstanding-mention popup, and acknowledgement actions.
- Adds mention actions to Tickets Grid/Cards and Support Assistant and supports `@` activation from ticket conversation entry.
- Corrects SLA saved/overrun interpolation and hides the final SLA balance until the ticket is Resolved or Closed.
- Compacts ticket creation, exposes Create Ticket at the top and in a sticky action bar, and replaces expanded recent caller tickets with a dropdown.
- Database head remains `0199_ticket_templates`; no migration is required. Run seed to register `ticket.mention`.
- Backend Ruff and strict MyPy passed; all 396 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript, and the production build passed.
- Bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed (1,811 entries).
- Artifact before final documentation refresh: `releases/SupportHub-1.66.29.zip` (43,242,848 bytes).
- Final artifact after documentation refresh: `releases/SupportHub-1.66.29.zip` (43,243,038 bytes; 1,811 entries).
- SHA-256: `1CFBEA0BE7EB8DF3D1862E440A36FF0A0E741B8A56564A5D5C6FE3A4A33F9F0D`.


## 1.66.28 — 2026-09-13

Status: self-contained Windows x64 release generated and verified.

- Resolves and closes active tickets atomically when they are moved to the Closed Cards lane, using the complete inline resolution requirements without a redundant close checkbox.
- Keeps already-resolved tickets on the normal direct-close workflow.
- Positions the Cards quick preview below the application header and adds detailed SLA evidence.
- Adds Task, Worklog, Checklist, related-ticket, Knowledge Base, and template actions to ticket context menus, including Support Assistant where applicable.
- Adds automatic keyword suggestions for Ticket and Pre-Ticket creation and Knowledge Base resolution suggestions.
- Adds governed ticket templates created from existing tickets, with Global, Client, Product, or Module scope and optional Client Portal visibility.
- Includes all enhancements and corrections from `1.66.27`.
- Database head advances to `0199_ticket_templates`; migration is required.
- Backend Ruff and strict MyPy passed; all 396 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript, and the production build passed.
- Bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed (1,811 entries).
- Artifact: `releases/SupportHub-1.66.28.zip` (43,231,799 bytes before final documentation refresh).
- Final artifact after documentation refresh: `releases/SupportHub-1.66.28.zip` (43,231,896 bytes; 1,811 entries).
- SHA-256: `F21C12F183DAB28BE9EA4EE2E231BD48BE766DD6B6E36D37F08FA241DBAE4C2E`.


## 1.66.27 — 2026-09-13

Status: self-contained Windows x64 release generated and verified.

- Exposes the CRM `is_default_resolution_service` flag through the contract-scoped ticket catalog.
- Enables both Cards and Ticket Details resolution dialogs to preselect the configured default provided service.
- Preserves manual addition and removal of provided services before resolution.
- Includes all enhancements and corrections from `1.66.26`.
- Database head remains `0198_view_layout_scope`; no migration is required.
- Backend Ruff and strict MyPy passed; all 395 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript, and the production build passed.
- Bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed (1,810 entries).
- Artifact: `releases/SupportHub-1.66.27.zip` (43,224,115 bytes before final documentation refresh).
- Final artifact after documentation refresh: `releases/SupportHub-1.66.27.zip` (43,224,200 bytes; 1,810 entries).
- SHA-256: `119C9388EB781226096D9973C4E929763AEFFDB63B985CF4E559BCABE19AAACB`.


## 1.66.26 — 2026-09-12

Status: self-contained Windows x64 release generated and verified.

- Keeps Resolve transitions entirely inside the Tickets Cards board instead of opening Ticket Details.
- Loads contract-valid provided services and automatically selects the configured default resolution service.
- Includes root cause, conditional outcome and permanent-fix evidence, knowledge-draft creation, and close-after-resolve controls in the inline dialog.
- Includes all enhancements and corrections from `1.66.25`.
- Database head remains `0198_view_layout_scope`; no migration is required.
- Backend Ruff and strict MyPy passed; all 395 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript, and the production build passed.
- Bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed (1,810 entries).
- Artifact: `releases/SupportHub-1.66.26.zip` (43,222,030 bytes before final documentation refresh).
- Final artifact after documentation refresh: `releases/SupportHub-1.66.26.zip` (43,222,110 bytes; 1,810 entries).
- SHA-256: `EFD292B03FE5235243BD837D578FD93C617B41ACEBEF40D4F4245B5112AA763F`.


## 1.66.25 — 2026-09-12

Status: self-contained Windows x64 release generated and verified.

- Treats both standard Client Portal and Mosaic ticket creation as Client Portal origins for configured ticket-creation email notifications.
- Adds regression coverage proving both `CLIENT_PORTAL` and `MOSAIC` tickets queue the governed portal notification.
- Includes all enhancements and corrections from `1.66.24`.
- Database head remains `0198_view_layout_scope`; no migration is required.
- Backend Ruff and strict MyPy passed; all 395 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript, and the production build passed.
- Bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed (1,810 entries).
- Artifact: `releases/SupportHub-1.66.25.zip` (43,221,773 bytes before final documentation refresh).
- Final artifact after documentation refresh: `releases/SupportHub-1.66.25.zip` (43,221,855 bytes; 1,810 entries).
- SHA-256: `06E159B9B24FB257DDFF3E10CDE7F0271322FDC3C505806A4B48DCA0D90B10C4`.


## 1.66.24 — 2026-09-12

Status: self-contained Windows x64 release generated and verified.

- Restores the complete governed resolution workflow when a Cards-view ticket is moved to Resolved.
- Keeps Resolved-to-Closed transitions inside the Cards view with provided-service selection preserved.
- Keeps In-Progress-to-Pending Internal and Pending Client transitions inside the Cards view with responsibility, follow-up owner, deadline, and reason requirements.
- Database head remains `0198_view_layout_scope`; no migration is required.
- Backend Ruff and strict MyPy passed; all 394 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript, and the production build passed.
- Bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed (1,810 entries).
- Artifact: `releases/SupportHub-1.66.24.zip` (43,221,124 bytes before final documentation refresh).
- Final artifact after documentation refresh: `releases/SupportHub-1.66.24.zip` (43,221,198 bytes; 1,810 entries).
- SHA-256: `A44E3E2AB2A77A56577042CFD35A9FB855F47179F98605ED33159CF0FFDC75F7`.


## 1.66.23 — 2026-09-12

Status: release candidate; full standalone build and verification in progress.

- Returns users to their originating workspace or ticket list after successful ticket creation.
- Keeps card resolution inside the Tickets board and opens the local resolution workflow.
- Includes the complete `1.66.22` enhancement scope.
- Database head remains `0198_saved_view_layout_scope`.
- Artifact target: `releases/SupportHub-1.66.23.zip`.


## 1.66.22 — 2026-09-12

Status: self-contained Windows x64 release generated and verified.

- Adds contract coverage validation and resolution-service scope controls across contracts and contract templates.
- Corrects Saved View and personal Grid/Cards layout behavior on Tickets.
- Adds the permission-aware six-area shell, contextual navigation, breadcrumbs, and shared page headers.
- Improves the Tickets filter toolbar and adds New-lane double-click ticket creation.
- Adds personal drag, reorder, resize, and explicit saving for Top Management dashboard layouts.
- Advances the database head to `0198_view_layout_scope`.
- Backend Ruff and strict MyPy passed; all 394 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Bundled runtime commands, ZIP integrity, required migrations, and manifest revision were verified.
- Artifact: `releases/SupportHub-1.66.22.zip` (43,220,505 bytes; 1,810 entries).
- SHA-256: `8284D400C8819097F3E666D8A03CBB06CC69CC083C65F7BF136ADD91E9C0ED1B`.


## 1.66.21 — 2026-09-10

Status: self-contained Windows x64 release generated and verified.

- Corrects Support Assistant ticket actions on mobile and desktop by navigating to the authenticated ticket action route instead of embedding it in a blocked iframe.
- Preserves the active Support Assistant tab as the return destination after the ticket action completes.
- Database head remains `0196_ticket_start_progress`; no migration is required.
- Complete release pipeline passed in the successful packaging run, including backend lint, strict MyPy, backend tests, frontend lint, frontend tests, TypeScript, production build, and standalone-runtime build.
- ZIP integrity, required frontend/runtime entries, and forbidden generated-file inspection passed (1,808 entries).
- Artifact: `releases/SupportHub-1.66.21.zip` (43,212,393 bytes), SHA-256 `FDDC5F55E027A9D5278C9C6ED64332020B52D13EA8E9EEEF85E073D41646E802`.

## 1.66.20 — 2026-09-10

Status: release preparation in progress.

- Adds personal default Grid/Cards ticket layouts without requiring Saved Views.
- Corrects Saved View name reuse, Backlog filtered counts, Ticket Detail accents, and Customer Success satisfaction navigation and engineer display.
- Advances the database through `0195_ticket_default_view` and `0196_ticket_start_progress`.
- Separates Start Progress from general status changes and removes default Call Center claim/progress access.
- Hides unauthorized Support Assistant actions and classifies shared Support ownership as New/unassigned rather than dedicated assignment.
- Artifact target: `releases/SupportHub-1.66.20.zip`.

## 1.66.19 — 2026-09-10

Status: self-contained Windows x64 release generated and verified.

- Enhances Support Assistant mobile actions, reopened-ticket priority, saved layouts, previews, and in-place fast actions.
- Adds a fixed mobile ticket-creation action bar and a slide panel for additional caller, branch, and assignment information.
- Adds permission-controlled Copy to new ticket actions in Support Assistant and the main Tickets Cards/Grid views.
- Database head remains `0194_ticket_grid_preferences`; no migration is required. Run seed to register `ticket.copy`.
- Backend Ruff, strict MyPy, and all 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Bundled runtime commands and a clean packaged migration through `0194_ticket_grid_preferences` passed.
- ZIP integrity, runtime inclusion, required frontend bundles, and forbidden-data inspection passed (1,806 entries).
- Artifact: `releases/SupportHub-1.66.19.zip` (43,207,069 bytes before final documentation refresh).

## 1.66.18 — 2026-09-10

Status: self-contained Windows x64 release generated and verified.

- Corrects and separates the mobile Grid and Cards experiences.
- Adds complete permission-aware pending-ticket actions to Cards.
- Adds touch-accessible three-dot actions and Change Status to Support Assistant cards.
- Simplifies the Support Assistant mobile header.
- Database head remains `0194_ticket_grid_preferences`; no migration is required.
- Backend Ruff, strict MyPy, and all 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Bundled runtime commands, ZIP integrity, runtime inclusion, and forbidden-data inspection passed.
- Artifact: `releases/SupportHub-1.66.18.zip` (43,203,063 bytes; 1,806 entries before final documentation refresh).
- Initial SHA-256 before final documentation refresh: `1565D06A51BFA7E4B7E1F2D049C1B4BF98EEB9044CD885538665580663BE4403`.

## 1.66.17 — 2026-09-10

Status: self-contained Windows x64 release generated and verified.

- Adds the advanced configurable ticket board, lane selection, swimlanes, limits, metrics, preview, quick filters, live refresh, and fast actions.
- Adds optimistic workflow-aware card movement, movable/collapsible lanes, and manual card ordering.
- Adds explicit durable grid-layout saving and saved Grid/Cards defaults.
- Database head remains `0194_ticket_grid_preferences`; no migration is required.
- Backend Ruff, strict MyPy, and all 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Bundled runtime commands, ZIP integrity, runtime inclusion, and forbidden-data inspection passed.
- Artifact: `releases/SupportHub-1.66.17.zip` (43,203,140 bytes; 1,806 entries before final documentation refresh).
- Initial SHA-256 before final documentation refresh: `D8E449B8AC88AC9E3666F1B3BD0738B4B6751D7555BDCE11F0C1E6EEA6F69054`.
- Final artifact after documentation refresh: `releases/SupportHub-1.66.17.zip` (43,203,393 bytes; 1,806 entries).
- Final SHA-256: `13D1E216639DCCE916A6C8A8013DCE85303AB8F1A13D058A4F217AB20316090B`.

## 1.66.16 — 2026-09-10

Status: self-contained Windows x64 release generated and verified.

- Adds directly movable and resizable ticket-grid headers with durable per-user widths and ordering.
- Adds dynamically grouped ticket card views and authorized drag-and-drop status changes.
- Saves grid/card mode, grouping, filters, sorting, and visible columns in ticket saved views.
- Database head remains `0194_ticket_grid_preferences`; no migration is required.
- Backend Ruff, strict MyPy, and all 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Bundled runtime commands, ZIP integrity, runtime inclusion, and forbidden-data inspection passed.
- Artifact: `releases/SupportHub-1.66.16.zip` (43,198,234 bytes; 1,806 entries before final documentation refresh).
- Initial SHA-256 before final documentation refresh: `40FCB9D37D16177ACF5CE26D0D366756482BA6E91EC73C5010312A06F25F281C`.
- Final artifact after documentation refresh: `releases/SupportHub-1.66.16.zip` (43,198,522 bytes; 1,806 entries).
- Final SHA-256: `6A7948017F4947EA92BF187DEDA58EC6CAE0C7D59ECAB156AECA4F30C3B6C241`.

## 1.66.15 — 2026-09-09

Status: self-contained Windows x64 release generated and verified.

- Adds a compact, responsive Tickets workspace with per-user drag-and-drop column layouts, density, page-size, sorting, grouping, and scroll-position persistence.
- Moves editable saved views into the Tickets page, removes their sidebar entry, and supports update, rename, default, and delete operations.
- Adds date-type and period presets for created, updated, assigned, resolved, and closed timestamps.
- Adds sticky sortable headers, tooltips, thin status/SLA indicators, mobile ticket cards, and native middle-click opening in a new tab.
- Advances the database head to `0194_ticket_grid_preferences`.
- Backend Ruff, strict MyPy, and all 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Standalone runtime commands and a clean packaged migration through `0194_ticket_grid_preferences` passed.
- ZIP integrity, required migration inclusion, and forbidden-data inspection passed (1,806 entries).
- Artifact: `releases/SupportHub-1.66.15.zip` (43,197,606 bytes).
- SHA-256: `B4A0911C7DA351BD3994D971DD9A686DCACA52217546800EAB2F59B7DC8ED748`.

## 1.66.14 — 2026-09-09

Status: self-contained Windows x64 release generated and verified.

- Replaces comma-separated Assistant status-code inputs with lookup-backed multi-select controls for built-in and personal tabs.
- Adds localized status names, color cues, checkbox selection, removable chips, responsive settings panels, and active-filter indicators.
- Database head remains `0193_assistant_user_state`.
- Backend Ruff, strict MyPy, and all 392 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Standalone runtime command and clean packaged migration through `0193_assistant_user_state` passed.
- Artifact: `releases/SupportHub-1.66.14.zip` (43,267,140 bytes; 1,806 entries).
- SHA-256: `6368CD44452EB01C54B03B2FABC1EB831DC136FE136EAABAAB6EC7C39AC8B8FD`.

## 1.66.13 — 2026-09-09

Status: self-contained Windows x64 release generated and verified.

- Adds durable per-user Assistant defaults, layout, density, page size, hidden card fields, tab filters, and sorting.
- Adds custom personal tabs with full management, default selection, and reordering.
- Adds ticket preview, sticky navigation and filters, active-filter chips, Cards/List modes, loading skeletons, improved empty states, mobile actions, and accessibility improvements.
- Preserves full-card flashing for overdue/unreceived and SLA-risk tickets.
- Improves notification return navigation and ticket resolution/closure return-to-source behavior.
- Advances the database head to `0193_assistant_user_state`.
- Backend Ruff, strict MyPy, and all 392 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Database head: `0193_assistant_user_state`.
- Standalone runtime command and clean packaged migration smoke tests passed.
- Artifact: `releases/SupportHub-1.66.13.zip` (43,266,711 bytes; 1,806 entries).
- SHA-256: `506F1B55EDECA73CA61F20515B97D9191A4532E85C5BDA441E8A056D8D5D6042`.

## 1.66.12 — 2026-09-09

Status: self-contained Windows x64 release generated and verified.

- Centralizes database writes, dashboards, filters, reports, Support Assistant, Client Portal, and public pages on the configured server clock.
- Adds the Server date/time and daylight-saving controls to Site Settings.
- Advances the database head to `0192_server_local_time` and converts existing SQL Server `datetimeoffset` values to the Egypt server-local representation without changing their instant.
- Backend Ruff, strict MyPy, and all 392 backend tests passed.
- Frontend ESLint, all 68 tests, and TypeScript passed.
- Production frontend build, standalone runtime command smoke test, and clean repeatable packaged migration through `0192_server_local_time` passed.
- Artifact: `releases/SupportHub-1.66.12.zip` (43,176,526 bytes; 1,792 entries).
- SHA-256: `84A566D3F81EF5937C843E09974AC5E0F03F5AA4702FD5764701088565FF9EF1`.

## 1.66.11 — 2026-09-08

Status: self-contained Windows x64 release generated and verified.

- Adds multi-vendor inbound profiles, vendor-scoped credentials, dynamic Ticket Type selection, and per-field enabled/required controls.
- Adds the active WhatsApp Ticket Type and advances the database head to `0191_inbound_vendor_profiles`.
- Renames inbound contact fields to Caller Name and Caller Number with legacy configuration migration.
- Corrects the Third-party Integration label and SQL Server Ticket-page filtering with large SLA result sets.
- Backend Ruff and strict MyPy passed; all 388 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The packaged runtime exposed all supported commands and completed a clean migration through `0191_inbound_vendor_profiles`.
- Artifact: `releases/SupportHub-1.66.11.zip` (43,160,937 bytes; 1,799 entries).
- SHA-256: `E508B36E709F93F68D047A6E2DF678A2FA66B22A1317353DFAC8AEB6C5DB0FB8`.

## 1.66.6 - 2026-09-08

Status: self-contained Windows x64 release generated and verified.

- Compacts optional resolution-dialog controls and moves long guidance into tooltips.
- Highlights and disables inactive clients in Ticket and Pre-Ticket creation.
- Adds atomic dedicated-engineer parent-to-escalation-child closure while retaining final-child-to-parent closure.
- Database head remains `0188_default_resolution_service`; no migration is required.
- Backend Ruff, strict MyPy, all 384 backend tests, frontend ESLint, all 68 frontend tests, TypeScript, and the production build passed.
- Bundled runtime commands and a clean packaged migration through `0188_default_resolution_service` passed.
- Manifest, IIS runtime configuration, required contents, and ZIP readability passed.
- Artifact: `releases/SupportHub-1.66.6.zip` (`43,113,588` bytes; 1,792 entries).
- SHA-256: `A45448984927C3F8AA378DE26F5F78A43D1E4B5C28A786B5922602442CDFEF48`.

## 1.66.5 - 2026-09-08

Status: self-contained Windows x64 release generated and verified.

- Corrects native Support Assistant popup-window resizing and compact-width behavior.
- Corrects the nine-minute orange Queue warning for shared/default support assignments that still lack a dedicated engineer.
- Fits dashboard widget accent borders to their curved card edges.
- Database head remains `0188_default_resolution_service`; no migration is required.
- Backend Ruff, strict MyPy, all 383 backend tests, frontend ESLint, all 68 frontend tests, TypeScript, and the production build passed.
- Bundled runtime commands and a clean packaged migration through `0188_default_resolution_service` passed.
- Manifest, IIS runtime configuration, required contents, and ZIP readability passed.
- Artifact: `releases/SupportHub-1.66.5.zip` (`43,109,608` bytes; 1,792 entries).
- SHA-256: `8D148DCD49EAF67DBBD0D21C704AE04377169533B61CBE5914D8C063F799D25F`.

## 1.66.4 - 2026-09-08

Status: self-contained Windows x64 release generated and verified.

- Synchronizes Support Assistant Queue arrivals, tab attention color, and notification sound; adds a nine-minute orange warning.
- Adds the counted actionable Pre-Tickets tab to Tickets and immediate count refresh after actions.
- Adds saved drag resizing, width presets, responsive compact density, RTL resizing, and safe storage fallback.
- Corrects dashboard widget accents and ticket drill-down accuracy.
- Database head remains `0188_default_resolution_service`; no migration is required.
- Full backend and frontend release gates passed.
- Bundled runtime commands, clean packaged migration, manifest, required contents, and ZIP readability passed.
- Artifact: `releases/SupportHub-1.66.4.zip` (`43,186,581` bytes; 1,792 entries).
- SHA-256: `D9BFA64BFB7762511F28972B3778E8CF3D2B9C006464A224A428C764E7845ABD`.

## 1.66.3 - 2026-09-07

Status: self-contained Windows x64 release generated and verified.

- Replaces the double SLA alert outline with a single modern red frame and soft near-breach glow.
- Keeps breached tickets visibly red without continuous animation and preserves reduced-motion support.
- Retains the shared Support Assistant card treatment on Executive and Top Management dashboard widgets.
- Database head remains `0188_default_resolution_service`; no migration is required.
- Ruff, strict MyPy, all 383 backend tests, frontend lint, all 57 frontend tests, TypeScript, and the production frontend build passed.
- Manifest version, database head, deployment mode, bundled runtime, Support Assistant frontend bundle, and ZIP readability passed.
- Artifact: `releases/SupportHub-1.66.3.zip` (`42,451,018` bytes; 1,792 entries).
- SHA-256: `4C75D5CC0F8F86F067359C0C0C3079581A6BB2E177083CF87FD079A3A6593799`.

## 1.66.2 - 2026-09-07

Status: self-contained Windows x64 release generated and verified.

- Packages the dashboard-card alignment and Support Assistant SLA alert-frame changes with the backend runtime for deployment without a server-side Python install.
- Database head remains `0188_default_resolution_service`; no migration is required.
- Ruff, strict MyPy, all 383 backend tests, frontend lint, all 57 frontend tests, TypeScript, and the production frontend build passed.
- Manifest version, database head, deployment mode, bundled runtime, required frontend contents, and ZIP readability passed.
- Artifact: `releases/SupportHub-1.66.2.zip` (`42,451,437` bytes; 1,792 entries).
- SHA-256: `EE7AB7282D85FBA73CE4E016B0AD52D321FA60F48F55E6F995827D544DB40909`.

## 1.66.1 - 2026-09-07

Status: self-contained release generated and artifact verified.

- Aligns Executive and Top Management dashboard widgets with the modern Support Assistant ticket-card surface and interaction treatment.
- Adds a red pulsing, reduced-motion-aware SLA alert frame to Support Assistant cards that are at risk of breach or already overrun.
- Database head remains `0188_default_resolution_service`; no migration is required.
- Artifact: `releases/SupportHub-1.66.1.zip` (`2,093,573` bytes; 514 entries).
- SHA-256: `A2823D1141FBED79FAA737C86C5C246A96EDF2806554121EF60493F0D05C46CA`.

## 1.66.0 - 2026-09-07

Status: self-contained Windows x64 release generated and verified.

- Corrects Support Assistant lifecycle actions after Queue self-assignment and progress start.
- Restricts Follow-up to In Progress or explicitly marked tickets.
- Adds creation-time descending Queue/Mine ordering, right-click actions, keyboard context-menu access, persistent drag ordering, and modern status-reactive card styling.
- Database head remains `0188_default_resolution_service`; no migration is required.
- Ruff, strict MyPy, 383 backend tests, frontend lint, 55 frontend tests, TypeScript, and the production frontend build passed.
- Packaged runtime commands and a clean packaged migration through `0188_default_resolution_service` passed.
- Manifest/IIS version, database head, required contents, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.0.zip` (`43,106,217` bytes; 1,792 entries).
- SHA-256: `10BD74E5684A3E7592AF2657D41A1BDCD093A6EA6DBA1BBA44BE81CBC90C08B5`.

## 1.65.0 - 2026-09-07

Status: self-contained Windows x64 release generated and verified.

- Fixes stale-version conflicts in read-only ticket SLA previews while retaining guarded writes.
- Hides invalid terminal-ticket actions in Support Assistant Mine cards.
- Adds migration `0188_default_resolution_service` for a governed default resolution service, multi-service resolution evidence, and resolution-history preservation.
- Prevents personal hidden-widget preferences from an old dashboard suppressing Top 3 Support Agents on a newly assigned dashboard.
- Ruff, strict MyPy, 383 backend tests, frontend lint, 53 frontend tests, TypeScript, and the production frontend build passed.
- Packaged runtime commands and a clean packaged migration through `0188_default_resolution_service` passed.
- Manifest/IIS version, database head, required contents, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.65.0.zip` (`43,104,629` bytes; 1,792 entries).
- SHA-256: `80826843986D6DCE52D28ECD304942A0844E64D30D0628CD85E04A8776759CB8`.

## 1.64.1 - 2026-09-07

Status: self-contained Windows x64 release generated and verified.

- Adds Queue/Mine-specific card actions, status-color accents, and Support Activity resolution defaulting.
- Adds collapsed Assistant help, full-system shortcut, and reliable return navigation through creation flows.
- Enforces direct ticket creation separately from Pre-Ticket creation/conversion in both UI and route access.
- Adds Queue arrival highlighting and configured notification sound with realtime updates and a 30-second recovery poll.
- Database head remains `0187_support_assistant_daily`; no new migration is required.
- Ruff, strict MyPy, 380 backend tests, frontend lint, 52 frontend tests, TypeScript, and the production frontend build passed.
- Packaged runtime commands, manifest/IIS version, database head, required contents, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.64.1.zip` (`43,097,649` bytes; 1,791 entries).
- SHA-256: `DE2645C68DA88E260F0C9A2346C33E6BEFC748308770F4DC051854D785239B86`.

## 1.64.0 - 2026-09-07

Status: self-contained Windows x64 release generated and verified.

- Fixes the SQL Server Top Support Agents aggregate query.
- Delivers the permission-governed daily Support Assistant queues, counts, follow-up workflow, quick creation actions, navigation recovery, WebSocket refresh, and polling fallback.
- Advances the database head to `0187_support_assistant_daily`.
- Ruff, strict MyPy, 380 backend tests, frontend lint, 50 frontend tests, TypeScript, and the production frontend build passed.
- Packaged runtime commands and the `0186` to `0187` upgrade path passed.
- Artifact: `releases/SupportHub-1.64.0.zip` (`43,098,504` bytes; 1,791 entries).
- SHA-256: `092770F1E4C5990EEB4C14312311D7B572EDFE229AE68BC0A5B81063CF49A349`.

## 1.63.2 - 2026-09-07

Status: corrective release candidate; standalone packaging pending.

- Corrects the SQL Server Top Support Agents query that attempted to aggregate an expression containing an `IN (SELECT ...)` predicate.
- Calculates breached resolved tickets using a left join to distinct breached resolution-SLA ticket IDs, preserving the existing ranking semantics and one-count-per-ticket behavior.
- Adds regression coverage for breached-agent counts and validates the aggregate with SQLAlchemy's MSSQL dialect.
- Database head remains `0186_support_assistant_prefs`; no migration is required.

## 1.63.1 — 2026-09-06

Status: corrective release candidate; standalone packaging in progress.

- Corrects SQL Server migration failure in `0184` and the equivalent latent issue in `0185` by explicitly supplying `profile_permissions.scope_type='NONE'`.
- Retains database head `0186_support_assistant_prefs` and all `1.63.0` Support Assistant functionality.
- Adds a migration regression guard for both corrected revisions.

## 1.63.0 — 2026-09-06

Status: self-contained Windows x64 release generated and verified.

- Adds the focused, installable Support Assistant with operational queues, compact SLA-aware cards, existing-workflow quick actions, live refresh/recovery, independent-window mode, and audited personal pinning.
- Adds migration `0186_support_assistant_prefs`; the change is additive and does not rewrite ticket data.
- Clean migration through `0186`, Ruff, strict MyPy, frontend ESLint, TypeScript, all 50 frontend tests, and the production frontend build passed.
- All 379 backend tests passed in the final release pipeline; all 50 frontend tests, lint, type checks, and production build also passed.
- Release notes and staging UAT steps are available in `docs/RELEASE-1.63.0.md` and `docs/RELEASE_SMOKE_TEST.md`.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`; a clean packaged migration passed through `0186_support_assistant_prefs`.
- Artifact: `releases/SupportHub-1.63.0.zip` (`43,089,971` bytes; `1,790` entries).
- SHA-256: `520697C1D6FE4DE781B569B645BFF49ACC9D22D2181895EC49F48A530CF35354`.

## 1.62.1 — 2026-09-06

Status: independent Pre-Ticket conversion permission implemented and verified in source; packaging deferred by request.

- Adds `ticket.pre_ticket.convert_assign` and removes the Convert & Assign dependency on both `ticket.create` and general queue processing.
- Keeps claim, information request, rejection, and cancellation under `ticket.pre_ticket.queue.process`.
- Migration grants the new permission to the Call Center system profile for continuity while leaving custom profile assignment explicit.
- Database head advances to `0184_pre_ticket_convert_perm`.
- Clean migration, Ruff, strict MyPy, 19 focused backend tests, frontend ESLint, and TypeScript passed before packaging.
- No 1.62.1 release artifact has been built. Full regression and packaging remain deferred.

## 1.62.0 — 2026-09-06

Status: Pre-Ticket entitlement and resolution-service self-contained Windows x64 release built and verified; ready for controlled deployment.

- Allows uncovered product selection on Pre-Tickets and requests existing entitlement approval only when conversion creates the official ticket.
- Adds governed Service Provided selection/change to Resolve and Close with relationship validation and audit evidence.
- Database head remains `0183_pre_ticket_result_unique`; no migration is added.
- Ruff, strict MyPy, all 377 backend tests, frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- The packaged runtime completed a clean migration and seed through `0183_pre_ticket_result_unique`.
- Standalone commands, manifest version, IIS application version, ZIP readability, 1,784 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.62.0.zip` (43,060,905 bytes).
- SHA-256: `E5FFE35751DC52880514BCF47798F68EB842FEEB5C6FB6890D38521A80D0F760`.

## 1.61.4 — 2026-09-06

Status: independent Pre-Ticket creation permission self-contained Windows x64 release built and verified; ready for controlled deployment.

- Makes `ticket.pre_ticket.create` sufficient for the Pre-Ticket form and its required client, contact, form-setting, and contract-catalog lookups.
- Keeps `ticket.create` independently required by official ticket creation.
- Database head remains `0183_pre_ticket_result_unique`; no migration is added.
- Ruff, strict MyPy, all 8 focused Pre-Ticket tests, all 376 backend tests, frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- The packaged runtime completed a clean migration and seed through `0183_pre_ticket_result_unique`.
- Standalone commands, manifest version, IIS application version, ZIP readability, 1,784 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.61.4.zip` (43,057,340 bytes).
- SHA-256: `5A77352D46B8DDDDAA830433C491034FCAD5DB99DDCF2764566382BA30FCF1D8`.

## 1.61.3 — 2026-09-06

Status: SQL Server migration-driver corrective self-contained Windows x64 release built and verified; ready for controlled deployment.

- Replaces migration 0183's unsupported `pymssql` unique-constraint reflection call with parameterized SQL Server system-catalog discovery.
- Retains support for auto-generated constraint names and scopes discovery to the configured default schema.
- Database head remains `0183_pre_ticket_result_unique`.
- Ruff, strict MyPy, all 10 focused migration/compatibility tests, all 375 backend tests, frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- The packaged runtime completed a clean migration and seed through `0183_pre_ticket_result_unique`.
- Standalone commands, manifest version, IIS application version, ZIP readability, 1,784 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.61.3.zip` (43,052,409 bytes).
- SHA-256: `034C84E84C7CA0F9AE2F19C8FCE70910A7420431B216E092AA1EA728991D3268`.

## 1.61.2 — 2026-09-06

Status: SQL Server Pre-Ticket submission corrective self-contained Windows x64 release built and verified; ready for controlled deployment.

- Replaces the nullable resulting-ticket ordinary unique constraint with a SQL Server filtered unique index, allowing multiple unconverted Pre-Tickets while keeping resulting ticket links unique.
- Adds complete Pre-Ticket operational timing and count/aging breakdowns for Release D.
- Database revision advances to `0183_pre_ticket_result_unique`.
- Clean migration, Ruff, strict MyPy, all 375 backend tests, frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed before packaging.
- The packaged runtime completed a clean migration and seed through `0183_pre_ticket_result_unique`.
- Standalone runtime commands, manifest version, IIS application version, database head, ZIP readability, 1,784 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.61.2.zip` (43,055,357 bytes).
- SHA-256: `0522D7223C81D74479B7F8EAA9F73C2888E0319FFB7249B0AA72D841443E02AA`.

## 1.61.1 — 2026-09-06

Status: Pre-Ticket conversion and navigation corrective self-contained Windows x64 release built and verified; ready for controlled deployment.

- Allows Call Center to complete missing optional Pre-Ticket context during controlled conversion while preserving submitted values and official ticket validation.
- Restores active covered products in the Pre-Ticket Product selector by removing a redundant filter against a property not returned by the contract catalog.
- Keeps Site Settings as the single Configuration sidebar entry for Engineer Pre-Tickets configuration, Email Integration, and Ticket Form Settings.
- Database revision remains `0182_pre_ticket_form_context`; no migration is added.
- Ruff, strict MyPy, all 374 backend tests, frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed before packaging.
- The packaged runtime completed a clean migration and seed through `0182_pre_ticket_form_context`.
- An isolated 1.61.0 → 1.61.1 packaged-runtime upgrade rehearsal passed; repeated 1.61.1 migration and seed commands were idempotent and retained head `0182_pre_ticket_form_context`.
- Standalone runtime commands, manifest version, IIS application version, database head, ZIP readability, 1,783 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.61.1.zip` (43,049,196 bytes).
- SHA-256: `DC9CDD6EBF717BC205464DB015EBB04AF82C99DB1CDB35691A889EA5DBB9C401`.

## 1.61.0 — 2026-09-06

Status: Configurable Pre-Ticket context self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds five always-visible Pre-Ticket context controls—Client, Contact, Product, Module, and Service—to Ticket Form Settings.
- All five fields are mandatory by default; administrators can change only whether each is mandatory.
- Persists Module and Service on the Pre-Ticket and forwards them into official ticket creation for precise contract-coverage matching.
- Database revision advances to `0182_pre_ticket_form_context`.
- Clean migration, Ruff, and strict MyPy passed across 154 source files; all 374 backend tests passed.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- Standalone runtime commands, manifest revision/version, and ZIP integrity passed (1,783 entries).
- Package: `releases/SupportHub-1.61.0.zip` (43,044,874 bytes).
- SHA-256: `F5D3298604CBB0DAB6E91793038D26F1B1625F19D87115420CDD1845D74C674C`.

## 1.60.3 — 2026-09-06

Status: Pre-Ticket discovery self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds the discoverable Site Settings entry for the Engineer Pre-Tickets feature policy and a Tickets-page New Pre-Ticket fast action.
- Database revision remains `0181_pre_ticket_queue_views`; no migration is required from 1.60.2.
- Ruff and strict MyPy passed across 154 source files; all 372 backend tests passed.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- Standalone runtime commands, manifest version, database head, and ZIP integrity passed (1,782 entries).
- Package: `releases/SupportHub-1.60.3.zip` (43,036,528 bytes).
- SHA-256: `10608712825A46332848F7556125A311FE90CC6DFAB2600FBFCCDC15AA5D7746`.

## 1.60.2 — 2026-09-06

Status: Pre-Ticket queue completion self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds server-side Call Center queue search, paging, lifecycle-status filtering, and complete matching CSV export.
- Adds private named Call Center queue views through additive migration `0181_pre_ticket_queue_views`.
- Ruff and strict MyPy passed across 154 source files; all 372 backend tests passed.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed. Existing Node local-storage and bundle-size notices remain non-blocking warnings.
- Standalone runtime commands, manifest version, database head, backend IIS configuration, and ZIP integrity passed (1,782 entries).
- Package: `releases/SupportHub-1.60.2.zip` (43,036,473 bytes).
- SHA-256: `CF4B7CE6744401F86A5B7410A08D7C52486E960D791C096D129E640A75D99CA8`.
- Production-copy upgrade rehearsal and controlled staging UAT remain pending before production enablement.

## 1.60.1 — 2026-09-05

Status: Pre-Ticket usability and Fast Create configuration completion self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds inline Contact creation, queue local search/paging, permission-gated CSV export, and a guided Feature Policy Fast Create profile editor.
- No database migration; database head remains `0180_pre_ticket_messages`.
- The feature stays OFF until the approved Ticket Type and P1–P4 mapping are configured and staging UAT is accepted.
- Ruff and strict MyPy passed across 154 source files; all 370 backend tests passed.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed. Existing React `act(...)`, Node local-storage, and bundle-size messages remain non-blocking warnings.
- Package: `releases/SupportHub-1.60.1.zip`.

## 1.60.0 — 2026-09-05

Status: Engineer Pre-Tickets self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds the governed Pre-Ticket lifecycle, queue processing, conversion to the creator, notification/audit evidence, and timing metrics.
- Database revision advances to `0180_pre_ticket_messages` through migrations `0178_engineer_pre_tickets`, `0179_pre_ticket_permissions`, and `0180_pre_ticket_messages`.
- Pre-Tickets remain OFF until the Fast Create profile is configured and approved.
- Ruff and strict MyPy passed across 154 source files; all 368 backend tests passed.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed. Existing React `act(...)`, Node local-storage, and bundle-size messages remain non-blocking warnings.
- Manifest version, standalone runtime, database head, and ZIP readability were verified (1,781 entries).
- Package: `releases/SupportHub-1.60.0.zip` (43,023,279 bytes).
- SHA-256: `F430A6A9A4525CB874C0CD789223346E2E8286FFACE2C0F7E352CAB5CEB95B64`.

## 1.59.7 — 2026-09-05

Status: coverage planner controls self-contained Windows x64 release built and verified; ready for controlled deployment.

- Refreshes coverage-slot data after shift edits and deletions, avoiding stale Coverage details.
- Allows Shift Managers to create intentionally empty coverage blocks and assign engineers later.
- Adds individual and selected-calendar-day bulk deletion of coverage blocks, with audit records.
- Coverage-block deletion does not delete existing shifts.
- Database revision remains `0177_ticket_archive`; no migration is required.
- Ruff and strict MyPy passed across 150 source files; all 367 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed. Existing React `act(...)`, Node local-storage, and Vite bundle-size messages remain non-blocking warnings.
- Manifest version, standalone runtime, database head, and ZIP readability were verified (1,767 entries).
- Package: `releases/SupportHub-1.59.7.zip` (42,981,708 bytes).
- SHA-256: `8F833307171ACFCCDB63B098199E3ECE9B7E9F564BF5E8F77672D41C37EBF0BC`.

## 1.59.6 — 2026-09-05

Status: Weekly Planner first-slice self-contained Windows x64 release built and verified; ready for controlled deployment.

- Adds a separate Unified Planner Weekly Planner dialog while preserving Quick Shift as the fast single-shift workflow.
- Loads multiple existing staffed Roster Templates into editable blocks; managers can modify shift details and engineers, preview the complete range, and create one batch of Draft shifts.
- Extends generator rows with fixed engineer IDs so each row can retain a different selected team.
- Database revision remains `0177_ticket_archive`; no migration is required.
- Ruff and strict MyPy passed across 150 source files; all 366 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed. Existing React `act(...)`, Node local-storage, and Vite bundle-size messages remain non-blocking warnings.
- Manifest version, standalone runtime, database head, and ZIP readability were verified (1,767 entries).
- Package: `releases/SupportHub-1.59.6.zip` (42,977,053 bytes).
- SHA-256: `211F2570B73EF08A4C051A55A9D8CB26D400363716EF3B53B94DFD019CD670AB`.

## 1.59.5 — 2026-09-05

Status: contract coverage removal corrective self-contained Windows x64 release built and verified; ready for controlled deployment.

- Deletes unused product, module, and service coverage rules from the selected contract.
- Retires rules that match ticket history for a client linked to the contract, preserving coverage revisions and audit history.
- Shows the actual API failure message in the removal dialog and reports client request timeouts clearly.
- Database revision remains `0177_ticket_archive`; no migration is required.
- Ruff and strict MyPy passed across 150 source files; all 365 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed.
- Manifest version, standalone runtime, database head, and ZIP readability were verified (1,767 entries).
- Package: `releases/SupportHub-1.59.5.zip` (42,974,999 bytes).
- SHA-256: `CB74CD987996734470B2A31E341C73C012DAF0175A3693F0BF134D0941F8EFDD`.

## 1.59.4 — 2026-09-05

Status: SQL Server breached-ticket drill-through corrective self-contained Windows x64 release prepared for guarded build and verification.

- Corrects `07002` SQL Server ODBC failures caused by more than 2,100 expanded ticket-ID parameters in breached-ticket dashboard drill-through queries.
- Uses the database-side SLA-clock predicate for counts and paging instead of materializing the breached ticket IDs in application memory.
- Database revision remains `0177_ticket_archive`; no migration is required.

## 1.59.3 — 2026-09-05

Status: historical SLA calculation corrective self-contained Windows x64 release built and verified; ready for controlled deployment.

- Corrects the 370-day calculation cap that caused valid historical ticket SLA evaluations to raise an exception.
- Restores ticket-list SLA evidence and scheduled escalation processing for tickets older than one year.
- Retains a 100-year data-sanity limit for corrupt timestamps and adds a regression test beyond the former cap.
- Database revision remains `0177_ticket_archive`; no migration is required.
- Ruff and strict MyPy passed across 150 source files; all 364 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed.
- Manifest version, standalone runtime commands, database head, ZIP readability, 1,767 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.59.3.zip` (42,973,706 bytes).
- SHA-256: `202DB0E19C96F263FE5DC002E563B66E35D29D7956969C2BC748F95D463B044F`.

## 1.59.2 — 2026-09-05

Status: ticket creation and workflow remediation self-contained Windows x64 release built and verified; ready for controlled deployment after a production-copy upgrade rehearsal.

- Adds access-safe ticket-creation email delivery and scoped workflow notifications for assignment, escalation, reassignment, and status transitions.
- Adds auditable client-confirmation evidence and required task/checklist readiness gates with an authorized override path.
- Adds initial ticket attachments, atomic ticket-context validation, and archive/restore in place of destructive ticket bulk deletion.
- Advances the database head to `0177_ticket_archive` through migrations `0176_workflow_readiness` and `0177_ticket_archive`.
- Ruff and strict MyPy passed across 150 source files; all 363 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed. Known React `act(...)`, Node local-storage, and bundle-size messages remain non-blocking warnings.
- The standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.59.2`, backend IIS `APP_VERSION`, database head, ZIP readability, 1,767 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.59.2.zip`.
- SHA-256: `B87DA9EB07E0320FDFD84004B0F96AD29CEB04B6E65481A6074DC91DD68EE34D`.

## 1.59.1 — 2026-09-04

Status: SQL Server dashboard-migration corrective self-contained Windows x64 release built and verified; ready for controlled deployment.

- Corrects the 1.59.0 upgrade failure caused by omitting required `profile_permissions.scope_type` while copying the Top Management navigator permission.
- Uses `NONE`, matching the IAM model and established permission-migration convention.
- Adds a regression test for the required scope column.
- Retains the 1.59.0 dashboard-engine and Contract workspace enhancements.
- Database revision remains `0170_dashboard_engine`; no additional migration is added because 1.59.0 failed before stamping revision 0170.
- Ruff and strict MyPy passed across 150 source files; all 344 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed; known non-blocking React and bundle-size warnings remain.
- A staged revision-0169 database upgraded successfully through the packaged runtime to `0170_dashboard_engine`; the repeated packaged migration was idempotent.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, backend IIS `APP_VERSION`, database head, ZIP readability, 1,759 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.59.1.zip` (42,917,357 bytes).
- SHA-256: `DC7A9A649A0879D23685E7D3FCC18E0266C531B2A0B3BC538A29054AC6058101`.

## 1.59.0 — 2026-09-04

Status: unaccepted immutable candidate; do not deploy. Production SQL Server migration validation exposed a required permission-scope omission in revision 0170.

- Adds explicit profile dashboard access, required default-dashboard governance, configurable dashboard tabs, reusable widget definitions, and tab-specific widget placement.
- Adds the dedicated `topmanagementdashboard.view` permission and permission-aware Top Management navigation.
- Adds prospective editing of product/module-scoped contract SLA targets while preserving existing ticket SLA snapshots.
- Adds audited reconfiguration of future billing schedules and synchronized draft invoices while locking issued or collected obligations.
- Advances the database revision to `0170_dashboard_engine`.
- Ruff and strict MyPy passed across 150 source files; all 343 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed; known non-blocking React test and bundle-size warnings remain.
- Packaged standalone runtime clean migration and idempotent second migration passed through `0170_dashboard_engine`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, backend IIS `APP_VERSION`, database head, bundled runtime, ZIP readability, 1,759 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.59.0.zip` (42,917,309 bytes).
- SHA-256: `1B7E6E3295ACA88D1AF25FB91783D2660E9BBB930509836FDF85A4E9DC05EF53`.

## 1.58.0 — 2026-09-02

Status: destination-first dashboard governance self-contained Windows x64 release prepared for verification and controlled deployment.

- Isolates Executive and Top Management templates and rejects cross-destination assignments.
- Automatically splits legacy templates shared across both destinations while preserving widgets and assignments.
- Rebuilds Dashboard Administration around one destination selector with responsive template, assignment, and preview workflows.
- Shows the full governed widget catalog to dashboard administrators, including required permissions and preview visibility diagnostics.
- Corrects the compressed vertical widget editor and duplicated destination selector.
- Replaces the misleading Top Management system-fallback assignment message with a clear unassigned state.
- Advances the database revision to `0169_dashboard_destinations`.
- Final package verification results are recorded after the release build completes.

## 1.57.2 — 2026-09-02

Status: SQL Server dashboard-migration corrective self-contained Windows x64 release built and verified; ready for controlled deployment after a production-copy upgrade rehearsal.

- Fixes the `0168_remove_profile_queries` upgrade failure under SQL Server/ODBC.
- Resolves inserted dashboard identities through their unique governed code instead of driver-dependent `inserted_primary_key` metadata.
- Safely reuses a migrated dashboard row if an interrupted migration attempt committed it before failing.
- Includes the mobile Reports navigation correction from 1.57.1.
- Database revision remains `0168_remove_profile_queries`; no additional migration is added.
- Ruff and strict MyPy passed across 150 source files; all 339 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed; known non-blocking React test and bundle-size warnings remain.
- A staged 0167 database containing legacy profile widgets upgraded successfully through the packaged runtime; the widgets and governed assignment were preserved, and a second migration was idempotent.
- Manifest version, backend IIS `APP_VERSION`, database head, bundled runtime, ZIP readability, 1,754 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.57.2.zip` (42,891,895 bytes).
- SHA-256: `778EE5E3B7D229CDED24D6D2D25969BF767A899DC8AE6501BE3DBB91E938C4D2`.

## 1.57.1 — 2026-09-02

Status: mobile Reports navigation corrective self-contained Windows x64 release built and verified; ready for controlled deployment after a production-copy upgrade rehearsal.

- Adds permission-aware report destinations to the mobile navigation drawer.
- Corrects desktop Reports visibility for Top Management-only users.
- Adds localized English and Arabic report navigation labels.
- Database revision remains `0168_remove_profile_queries`; no migration is added.
- Ruff and strict MyPy passed across 150 source files; all 337 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed; known non-blocking React test and bundle-size warnings remain.
- Packaged standalone runtime clean migration and idempotent second migration passed through `0168_remove_profile_queries`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, backend IIS `APP_VERSION`, database head, bundled runtime, ZIP readability, 1,752 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.57.1.zip` (42,889,310 bytes).
- SHA-256: `E9B60B330D952B12D33899F162C62A907031C1E821D81A8F9F10A1F25302EF7B`.

## 1.57.0 — 2026-09-02

Status: dashboard-assignment governance self-contained Windows x64 release built and verified; ready for controlled deployment after a production-copy upgrade rehearsal.

- Separates Executive and Top Management dashboard assignment resolution.
- Replaces personal dashboard copies with per-user, per-destination widget visibility preferences.
- Prevents user customization from introducing unassigned widgets or masking later administrator changes.
- Removes Profile Dashboard Queries and migrates legacy selections into governed templates and assignments.
- Advances the database revision to `0168_remove_profile_queries`.
- Ruff and strict MyPy passed across 150 source files; all 337 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed; known non-blocking React test and bundle-size warnings remain.
- Packaged standalone runtime clean migration and idempotent second migration passed through `0168_remove_profile_queries`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, backend IIS `APP_VERSION`, database head, bundled runtime, ZIP readability, 1,752 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.57.0.zip` (42,890,888 bytes).
- SHA-256: `24CDAC02B799A7BC2EE9898DE3D43639D85366D6F467E237D4134C6D2A1ECF24`.

## 1.55.0 — 2026-09-01

Status: Project Delivery and dashboard-governance self-contained Windows x64 release built and verified; ready for controlled deployment after a production-copy upgrade rehearsal.

- Adds editable pending Project Handovers, structured project scope and pending points, and multiple audited contract-template sources with deduplicated merged scope.
- Adds governed dashboard-section visibility, explicit profile dashboard precedence, and permission-aware login landing pages.
- Advances the database revision to `0161_multi_handover_templates`.
- Ruff and strict MyPy passed across 150 source files; all 332 backend tests passed.
- Frontend ESLint, all 47 tests across 24 files, TypeScript, and the production Vite build passed; known non-blocking React test and bundle-size warnings remain.
- Packaged standalone runtime clean migration and idempotent second migration passed through `0161_multi_handover_templates`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, backend IIS `APP_VERSION`, database head, ZIP readability, 1,746 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.55.0.zip` (42,845,706 bytes).
- SHA-256: `3607CC1E8B6076625FC65D51C46C54BB4C9D36F63D905DE0B1FEA1A2579464ED`.

## 1.54.0 — 2026-09-01

Status: workflow and dashboard enhancement self-contained Windows x64 release built and verified; ready for controlled deployment after a production-copy upgrade rehearsal.

- Adds HR and Project Handover dashboards and Top Management profile landing-page selection.
- Corrects disabled SLA-email behavior for both warning and escalation events.
- Adds governed escalation-rule editing and permission-controlled shared-caller search/linking.
- Advances the database revision to `0158_shared_caller_links`.
- Ruff and strict MyPy passed across 150 source files; all 331 backend tests passed.
- All 47 frontend tests across 24 files, ESLint, TypeScript, and the production Vite build passed; known non-blocking React test and bundle-size warnings remain.
- Packaged runtime clean migration and idempotent second migration passed through `0158_shared_caller_links`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, backend IIS `APP_VERSION`, database head, ZIP readability, 1,743 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.54.0.zip` (42,826,232 bytes).
- SHA-256: `23CC01E1AEA0A05E113DE21966BA2BA13E4398AFDD43B7F74755922FE74D7637`.

## 1.53.3 — 2026-09-01

Status: Customer Success SQL-scale corrective self-contained Windows x64 release built and verified; deploy this release instead of 1.53.2.

- Corrects production pyodbc error 07002 caused by expanding 8,534 ticket IDs into the Customer Success survey query.
- Uses joined, date/client-scoped SQL for surveys and complaint-reopen evidence instead of unbounded ID predicates.
- Adds a 2,101-ticket parameter-ceiling regression.
- Database revision remains `0155_financial_widgets`; no migration is added.
- Ruff and strict MyPy passed across 150 source files; all 326 backend tests passed.
- All 47 frontend tests across 24 files and the production Vite build passed; known non-blocking React test and bundle-size warnings remain.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, backend IIS `APP_VERSION`, database head, ZIP CRC/readability, 1,740 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.53.3.zip` (42,798,357 bytes).
- SHA-256: `22C0E899B78F403ED1636EAECCA650D56AAB028AF25DB541DA4FDA6982D50DED`.

## 1.53.2 — 2026-09-01

Status: management-dashboard SQL Server corrective self-contained Windows x64 release built and verified; deploy this release instead of 1.53.1.

- Corrects production SQL Server error 8120 in the product-demand aggregation by grouping on the underlying product-name column instead of a separately parameterized `COALESCE` expression.
- The production correlation log, focused six-test suite, and exact multi-year populated-database call confirm the failure and correction.
- Database revision remains `0155_financial_widgets`; no migration is added.
- Ruff and strict MyPy passed; all 325 backend tests and all 47 frontend tests passed; TypeScript and the production Vite build passed.
- The exact populated-database request for `2024-01-01` through `2026-09-01` returns all 17 Executive Overview widgets.
- Standalone runtime commands, manifest version, IIS `APP_VERSION`, database head, ZIP CRC/readability, 1,738 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.53.2.zip` (42,795,510 bytes).
- SHA-256: `636C56F7A331E1EFCFF90E2444BAF40C935BC08130E181373728D6A5614D2828`.

## 1.53.1 — 2026-09-01

Status: corrected dashboard-enhancement self-contained Windows x64 test/UAT release built and verified; use this package for controlled testing.

- Supersedes unaccepted candidate 1.53.0 after its packaged clean SQLite migration exposed an unsupported post-creation foreign-key alteration in revision 0154.
- Skips that constraint operation only on SQLite while retaining the verified non-cascading self-reference on SQL Server.
- Ruff and strict MyPy passed; all 325 backend tests and all 47 frontend tests passed; TypeScript and the production Vite build passed.
- Source and packaged-runtime clean SQLite migrations plus idempotent second upgrades passed through `0155_financial_widgets`.
- The populated SQL Server migration also passed through `0155_financial_widgets`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, IIS `APP_VERSION`, database head, bundled runtime, ZIP readability/CRC, 1,738 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.53.1.zip` (42,794,457 bytes).
- SHA-256: `E73F6BD9254829E0E88632D7D9095B1B4287B5305DF909CB7A05D07AF871BF40`.

## 1.53.0 — 2026-09-01

Status: unaccepted immutable candidate; do not deploy. Its packaged clean SQLite migration exposed the revision-0154 constraint portability defect before release acceptance.

- Adds governed dashboard templates, deterministic assignments, administration, safe personalization, and assigned-template update notification.
- Adds dashboard SQL/scalability improvements, response-SLA snapshots, evidence caps, regression budgets, and million-row benchmark coverage.
- Adds the least-privilege Financial Management profile and currency-safe contract-value, expiry, discount, and adjustment widgets with direct contract filtering.
- Database revision is `0155_financial_widgets`; populated SQL Server migration passed after verifying the non-cascading dashboard self-reference.
- Ruff, strict MyPy, all backend tests, TypeScript, and the production Vite build pass.
- Final artifact/runtime/ZIP verification will be recorded after packaging.

This file is the durable record for every development session and release. Update it whenever code, migrations, configuration, or release artifacts change. Record work before closing the editor and again after verification.

## 1.52.4 — 2026-08-31

Status: Arabic client-text corrective self-contained Windows x64 release built and verified; deploy this release.

- Corrects client name/address/notes storage with revision `0149_client_unicode_text` and Unicode ORM types.
- Local SQL Server upgraded successfully; reflected types are `NVARCHAR(200)`, `NVARCHAR(1000)`, and `NVARCHAR(MAX)`.
- Rollback-only real SQL Server Arabic round-trip verification passed.
- Focused Ruff, strict MyPy, and 21 API/migration/compatibility tests pass.
- Retains the 1.52.3 historical-dashboard timeout correction.
- Ruff and strict MyPy passed across 149 source files; all 316 backend tests passed.
- Frontend ESLint, TypeScript, all 47 tests across 24 files, and the production Vite build passed; known non-blocking warnings remain.
- Packaged runtime clean migration and idempotent second migration passed through `0149_client_unicode_text`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, IIS `APP_VERSION`, database head, ZIP readability, 1,727 entries, bundled runtime, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.52.4.zip` (42,714,620 bytes).
- SHA-256: `485A3E179C0845DC2885DCD6EE49039F0C89D8EED8EAD244048CD679893B4E97`.

## 1.52.3 — 2026-08-31

Status: dashboard-timeout corrective self-contained Windows x64 release built and verified; deploy this release.

- Corrects browser cancellation of full-range Executive and Top Management analytics by applying a 120-second timeout only to those two historical requests; the ordinary API timeout remains 15 seconds.
- Reproduced the boundary on 20,648 tickets: cold Top Management/Executive runs took 12.259/8.530 seconds, while warm runs took 3.429/3.689 seconds.
- Focused frontend ESLint, three timeout/date tests, and TypeScript pass.
- Database revision remains `0148_sla_outcome_snapshots`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 315 backend tests passed.
- Frontend ESLint, TypeScript, all 47 tests across 24 files, and the production Vite build passed; known non-blocking warnings remain.
- Packaged runtime clean migration and idempotent second migration passed through `0148_sla_outcome_snapshots`.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, IIS `APP_VERSION`, database head, compiled 120-second analytics configuration, ZIP readability, 1,725 entries, bundled runtime, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.52.3.zip` (42,713,682 bytes).
- SHA-256: `856284D2932DD70A0A6305449A59D6DE7AD89A1A69592F23F2B59A36FAA1AFD5`.

## 1.52.2 — 2026-08-31

Status: corrected self-contained Windows x64 release built and verified; deploy this release instead of 1.52.1.

- Supersedes unaccepted candidate 1.52.1 after its clean packaged migration rehearsal exposed duplicate revision-0148 columns on SQLite.
- Freezes the revision-owned SLA snapshot columns correctly and adds safe column/index existence guards.
- Source clean migration and idempotent second upgrade now pass through `0148_sla_outcome_snapshots`.
- Ruff and strict MyPy passed across 149 source files; all 315 backend tests passed.
- Frontend ESLint, TypeScript, all 46 tests across 23 files, and the production Vite build passed; known React test and large-chunk warnings remain non-blocking.
- Packaged runtime clean migration passed through `0148_sla_outcome_snapshots`, and an idempotent second migration run passed.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, IIS `APP_VERSION`, database head, ZIP readability, 1,725 entries, bundled runtime, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.52.2.zip` (42,712,891 bytes).
- SHA-256: `DDC1C2CFEB14A0E29EF9754E30918A9AF57846CA4DEB79509E24C4E2E2A266C2`.

## 1.52.1 — 2026-08-31

Status: unaccepted immutable candidate; do not deploy. Its clean packaged SQLite migration exposed duplicate revision-0148 snapshot columns before release acceptance.

- Supersedes the source-only 1.52.0 package for normal IIS deployment by bundling the standalone backend runtime.
- Retains the completed B-47 language scope, dashboard SQL improvements, and database revision `0148_sla_outcome_snapshots`.
- Final runtime, manifest, ZIP, and forbidden-file verification will be recorded after packaging.

## 1.52.0 — 2026-08-31

Status: source-deployment package built and verified; use 1.52.1 for the normal self-contained Windows deployment.

- Completes all inventoried B-47 page localization, multilingual administration, RTL, technical-text isolation, and persistence/regression coverage.
- Includes Executive and Top Management SQL aggregation/filter pushdown, evidence caps, and SQL Server-safe 1,900-ID batching.
- Adds revision `0148_sla_outcome_snapshots` and a cursor-safe historical outcome backfill; the local production copy upgraded and backfilled successfully.
- Measured uninstrumented full-range execution over 20,648 tickets is 2.954 seconds Top Management and 4.703 seconds Executive; the one-million-row grouped-SQL benchmark completes in 0.178 seconds.
- Ruff and strict MyPy passed across 149 source files; all 315 backend tests passed.
- Frontend ESLint, TypeScript, all 46 tests across 23 files, and the production Vite build passed; only known non-blocking warnings remain.
- Source package: `releases/SupportHub-1.52.0.zip` (1,912,637 bytes), SHA-256 `2907C03F137BE1A27D2476BCFC922A49323E1F50C9B45563263CBD1FD7AD31F6`.

## 1.51.1 — 2026-08-30

Status: dashboard drill-through corrective self-contained Windows x64 release built and verified.

- Aligns clickable cards and chart segments with their displayed dashboard population.
- Retains period, date basis, dashboard scope, geography, client, product, department, team, and engineer filters.
- Database revision remains `0147_multilingual_master_data`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 315 backend tests passed.
- Frontend ESLint, TypeScript, all 42 tests across 21 files, and the production Vite build passed; the existing vendor-chunk advisory remains non-blocking.
- Packaged runtime clean migration passed from an empty database through `0147_multilingual_master_data`, including an idempotent second migration run.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest, IIS `APP_VERSION`, database head, ZIP readability, 1,722 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.51.1.zip` (42,642,333 bytes).
- SHA-256: `EEF05959DDF9C64C7242C28CF76F44B0371923C9ED065C78481A33C5015EDCAB`.

## 1.51.0 — 2026-08-30

Status: Language Enhancement Phase 1 and dashboard-performance self-contained Windows x64 release built and verified.

- Defines Language Enhancement Phase 1 while retaining English as the normal interface and deferring remaining Arabic pages to Phase 2.
- Includes database revisions `0146_language_foundation` and `0147_multilingual_master_data`.
- Corrects the Top Management first-response N+1 query path; measured full-range execution improved from 39.99 seconds to 2.85 seconds on 20,648 tickets and 20,396 SLA clocks.
- Corrects revision 0147 so SQL Server covering indexes that include converted ticket text columns are safely rebuilt.
- Ruff and strict MyPy passed across 149 source files; all 315 backend tests passed.
- Frontend ESLint, TypeScript, all 42 tests across 21 files, and the production Vite build passed; the existing vendor-chunk advisory remains non-blocking.
- Packaged runtime clean migration passed from an empty database through `0147_multilingual_master_data`.
- Standalone runtime help exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest, IIS `APP_VERSION`, database head, ZIP readability, 1,722 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.51.0.zip` (42,636,279 bytes).
- SHA-256: `254B9A4B81B76ABF31745146A55FFE7CC46EECB87EC356144DFBF9880DD7E0DF`.

## Reusable User Request import preparer — 2026-08-29

Status: implemented and verified against the 8,113-row external export.

- Adds an interactive/CLI Python converter that asks for the export folder and filename and writes prepared and unresolved workbooks beside the source.
- Bundles the controlled ticket template, the supplied 415-row Support Hub client mapping, and Python dependency declaration.
- Preserves the proven organization/client, status, priority, source, agent fallback, legacy evidence, and Excel formula-safety rules.
- Reproduced 7,923 prepared rows and 190 unresolved client rows from `User Request Export (7).xlsx`.
- Python compilation, command help, workbook sheet structure, row counts, and controlled assignee output passed.

## 1.50.4 — 2026-08-29

Status: dashboard-default corrective self-contained Windows x64 release built and verified; supersedes 1.50.3.

- Defaults the General and Top Management dashboards to the current local calendar month through today.
- Reset filters restores that same month-to-date range.
- Restricts the Top 3 trophy leaderboard to Support department employees with at least one handled ticket in the selected period.
- Preserves the complete cross-department agent KPI report.
- Database compatibility revision remains `0145_ticket_scale`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 311 backend tests passed.
- Frontend ESLint, TypeScript, all 39 tests, and the production build passed.
- Standalone runtime help, manifest/version/head, ZIP readability, 1,714 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.50.4.zip` (42,549,261 bytes; 1,714 entries).
- SHA-256: `F66995E433EF63089BD1ABC5774D854CC970D8FC744367CF914D1185CD71DC5B`.

## 1.50.3 — 2026-08-29

Status: scalability corrective self-contained Windows x64 release built and verified; supersedes 1.50.2.

- Corrects SQL Server's 2,100-parameter failure in dashboard related-data queries after large ticket imports.
- Filters general and executive dashboard ticket populations by the selected period in SQL before materialization.
- Batches SLA, assignment/status history, escalation, root-cause, and satisfaction reads at 1,000 ticket IDs.
- Adds migration `0145_ticket_scale` with ticket creation/resolution and assignment-history indexes.
- Adds a 2,101-ticket SQL Server parameter-limit regression; focused general/executive dashboard tests and a clean migration to head passed.
- Ruff and strict MyPy passed across 149 source files; all 311 backend tests passed.
- Frontend ESLint, all 37 tests, TypeScript, and the production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Standalone runtime help, manifest/version/head, IIS `APP_VERSION`, ZIP readability, 1,713 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.50.3.zip` (42,548,571 bytes; 1,713 entries).
- SHA-256: `7AC559C718347FB743D9AD682EC895336F6A47E277A4D4D768DF6B44A02F1B62`.

## 1.50.2 — 2026-08-29

Status: corrective self-contained Windows x64 release built and verified; supersedes 1.50.1.

- Corrects long-running confirmation requests that exceeded the frontend's 15-second API timeout while the server continued processing.
- Confirmation now returns `IMPORTING`, runs atomically with an isolated deployment-bound database session, records `IMPORT_FAILED` on rollback, and is polled automatically by the UI.
- Replaces the misleading catch-all reference-change message with the actual API error and clear active/failed status guidance.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 310 backend tests passed.
- Frontend ESLint, all 37 tests, TypeScript, and the production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Standalone runtime help, manifest/version/head, IIS `APP_VERSION`, async import UI inclusion, ZIP readability, 1,712 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.50.2.zip` (42,545,026 bytes; 1,712 entries).
- SHA-256: `13FD0B69A41F9ADA6EACF129E07033673FEF649E642FA42BE2D0A0C62F0A77AE`.

## 1.50.1 — 2026-08-29

Status: corrective self-contained Windows x64 release built and verified; supersedes 1.50.0.

- Corrects large ticket workbook validation/confirmation that could exceed IIS's five-minute request timeout and surface as HTTP 502.
- Replaces per-row ticket reference queries with request-scoped preloaded lookup maps for validation and confirmation.
- Adds a 500-ticket regression proving bounded reference reads across both stages.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 310 backend tests passed.
- Frontend ESLint, all 37 tests, TypeScript, and the production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Standalone runtime help, manifest/version/head, IIS `APP_VERSION`, optimized import source inclusion, ZIP CRC/readability, 1,712 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.50.1.zip` (42,543,351 bytes; 1,712 entries).
- SHA-256: `F56CA893A9133093DF723A2884B22BFE1F12031C2E104457FF50AA7603D51DB9`.

## 1.50.0 — 2026-08-28

Status: self-contained Windows x64 feature release built and verified; supersedes 1.49.3.

- Adds governed compatibility for the external User Request Excel export under the Tickets migration task.
- Maps external organization names to unique Support Hub client names, legacy priorities/statuses to current codes, agents/callers by full name, and exact service matches where available.
- Preserves validation, replay protection, explicit confirmation, and atomic insertion; unknown or ambiguous core references remain validation errors.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 309 backend tests passed.
- Frontend ESLint, all 37 tests, TypeScript, and the production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Standalone runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest/version/head, IIS `APP_VERSION`, required external-import source, ZIP CRC/readability, 1,712 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.50.0.zip` (42,538,781 bytes; 1,712 entries).
- SHA-256: `C9E0CEB1E0C7D44BEB519FE87012BF46ED694F672D69D84258E0F3718B0D53C7`.

## External User Request ticket import — 2026-08-28

Status: implemented and focused verification passed; packaging in release 1.50.0.

- The attached 279-row external export schema is recognized only for the Tickets task; controlled imports remain unchanged.
- Organization Name is treated as the Support Hub client name. Legacy references, caller/service metadata, dates, assignment, status, and priority are normalized into the current ticket design.
- Ruff, strict MyPy for the import service, all seven import tests, TypeScript, and the production frontend build passed before packaging.
- Stabilized the existing dropdown placement assertion so it waits for the request-animation-frame position correction; the focused test passes and production behavior is unchanged.

## 1.49.3 — 2026-08-28

Status: corrected self-contained Windows x64 release built and verified; supersedes 1.49.2.

- Packages the verified global correction that forces searchable Select result lists below their fields and recalculates constrained placement during scroll/resize.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 308 backend tests passed.
- Frontend ESLint, all 37 tests, TypeScript, and production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Clean migration using the packaged standalone runtime reached `0144_handover_cleanup`; runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest/version/head, IIS `APP_VERSION`, required contents, ZIP readability, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.49.3.zip` (42,531,186 bytes; 1,712 entries).
- SHA-256: `CA2C2BFCD71EE9BC699BF56FE0BA9A38D6DD4D4C209D586D0EA61A08205E2D05`.

## Dropdown results forced below field — 2026-08-28

Status: implemented, verified, and packaged in release 1.49.3.

- Shared searchable MUI Select menus now force the result paper's top edge to the field's bottom edge plus a six-pixel gap instead of allowing automatic upward placement or overlap.
- Available menu height is constrained to the viewport space below the field and positioning is recalculated during scroll and resize.
- Direct field typing, normalized contains filtering, accessibility, existing values, permission scope, and dedicated autocomplete behavior remain unchanged.
- Frontend ESLint, TypeScript, 5 focused dropdown tests, all 37 frontend tests, and production build passed. No backend or migration change was made.

## 1.49.2 — 2026-08-28

Status: corrected self-contained Windows x64 release built and verified; supersedes 1.49.1.

- Packages the verified system-wide dropdown positioning, focus-conflict, and option-indexing correction.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 308 backend tests passed.
- Frontend ESLint, all 37 tests, TypeScript, and production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Clean migration using the packaged standalone runtime reached `0144_handover_cleanup`; runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest/version/head, IIS `APP_VERSION`, required contents, ZIP readability, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.49.2.zip` (42,530,596 bytes; 1,712 entries).
- SHA-256: `A9EC49EB8E105A30828B4229E811FE0117D50692BF6315B9C84D6777CE86E31A`.

## System-wide dropdown positioning and performance correction — 2026-08-28

Status: implemented, verified, and packaged in release 1.49.2.

- Shared MUI form Select controls, including Tickets filters and dialog fields, now keep one immediately focused editable field while the results overlay is anchored below it with a visible gap.
- The old selected-option autofocus/typeahead path is disabled so it no longer competes with field typing or repositions the list over the search area.
- Visible option labels are normalized and indexed once per menu opening; each keypress performs only a contained-text lookup instead of re-reading every option tree.
- The menu remains in MUI's accessible overlay layer, while the projected input visually occupies the original field. Dedicated autocomplete, server loading, permissions, values, and action/navigation menus are unchanged.
- Frontend ESLint, TypeScript, 5 focused dropdown tests, all 37 frontend tests, and the production build passed. No backend or migration change was made.

## 1.49.1 — 2026-08-28

Status: corrected self-contained Windows x64 release built and verified; supersedes 1.49.0.

- Packages the Client Portal native dropdown, popup placement, sole-client catalog/loading, Mosaic prompt, and ticket-number wrapping corrections on top of 1.49.0.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 308 backend tests passed.
- Frontend ESLint, all 37 tests, TypeScript, and production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Clean migration using the packaged standalone runtime reached `0144_handover_cleanup`; runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest/version/head, IIS `APP_VERSION`, required contents, ZIP readability, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.49.1.zip` (42,529,761 bytes; 1,712 entries).
- SHA-256: `E8B2724AEDE4349BC4F2D539FF658AF5261BA4AC4D40F26E16EEACC08374D0E0`.

## Client Portal dropdown/catalog and ticket-number UX correction — 2026-08-28

Status: implemented and verified in the working tree; not included in immutable release 1.49.0.

- Positions native autocomplete results below the editable field with a fixed visual gap, preventing the popup from covering the search area.
- The portal catalog now returns the sole authorized client as selected on the first request. Create with Mosaic applies it before paint and avoids the previous identical second catalog request; multi-client portal accounts retain explicit selection and scoped reload behavior.
- Internal Tickets keeps a Client Portal ticket number and its source chip on one row and prevents character-level wrapping of the ticket link.
- Existing catalog authorization, contracts, entitlement, Mosaic relationships, URL state, and multi-client scope remain unchanged.
- Ruff and strict MyPy passed; all 6 focused portal backend tests passed. Frontend ESLint, TypeScript, all 37 tests, and production build passed. No migration was added.

## Client Portal native searchable dropdown correction — 2026-08-28

Status: implemented and verified in the working tree; not included in immutable release 1.49.0.

- Replaces Client Portal form/filter MUI Select controls with true editable autocomplete fields rather than relying on the shared menu overlay.
- Covers My Requests status/product/module/service filters and Create Request affected-client, product, module, service, request-type, priority, and multi-contract selection.
- A single focus/click allows immediate typing in the visible field; normalized case-insensitive contains matching, clearing, keyboard navigation, and no-results behavior are native to the control.
- Existing values, URL filters, dependent clearing, entitlement logic, Mosaic cards, and portal API permission scope are unchanged.
- Frontend ESLint and TypeScript passed; 2 focused portal-dropdown tests and all 37 frontend tests passed; the production build passed with only the existing chunk-size advisory. No backend or migration change was made.

## 1.49.0 — 2026-08-28

Status: self-contained Windows x64 release built and verified.

- Packages the B-38/B-44 guided Mosaic workflow, B-46 responsive live tracking/escalation/inline satisfaction, and the B-45 direct-in-field dropdown correction.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 308 backend tests passed.
- Frontend ESLint, all 35 tests, TypeScript, and the production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Clean migration using the packaged standalone runtime reached `0144_handover_cleanup`; runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest/version/head, IIS `APP_VERSION`, required contents, ZIP readability, 1,711 entries, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.49.0.zip` (42,527,493 bytes; 1,711 entries).
- SHA-256: `0E317E55C656CEE08B2963EEFC75186CFF8D88F2700321E33D17D2B49791B888`.

## B-45 direct-in-field search correction — 2026-08-28

Status: implemented, verified, and packaged in release 1.49.0.

- Removes the separate search box previously rendered inside each dropdown list.
- Opening a shared MUI form Select now focuses an accessible text input visually occupying the original field, allowing immediate typing after the first click; the open options filter by normalized, case-insensitive contained text.
- Applies through the application theme to form dropdowns on pages and in dialogs. Existing dedicated autocomplete/server-backed lookups retain their scope, while action, navigation, and context menus remain unchanged.
- Closing restores the selected label and value without clearing the selection. An explicit no-results state remains available.
- Frontend ESLint and TypeScript passed; 3 focused regressions and all 35 frontend tests passed; the production build passed with only the existing chunk-size advisory. No backend or migration change was made.

## B-44 / B-38 checkpoint — 2026-08-28

Status: implemented, verified, and packaged in release 1.49.0.

- Restores Create with Mosaic as one explicit progressive Product → Module → linked Service card mode with responsive and accessible states, URL restoration, Back/Change controls, retained draft details, and review before submission.
- Extends the scoped portal catalog with minimum service-module relationship IDs and filters each service step accordingly.
- The backend rejects incomplete, out-of-scope, cross-product, inactive, or unlinked Mosaic paths and persists valid selections with source `MOSAIC` through the existing entitlement/approval transaction.
- Normal portal ticket creation remains distinct; attachment and duplicate-submission safeguards are preserved.
- Ruff and strict MyPy passed across 149 source files; all 308 backend tests passed. Frontend ESLint, TypeScript, all 34 tests, and the production build passed. No migration was added.

## B-46 checkpoint — 2026-08-28

Status: implemented, verified, and packaged in release 1.49.0.

- Public live tracking uses a horizontal desktop timeline and vertical narrow-screen timeline with long-content containment.
- Adds generic client-safe active/historical escalation evidence without internal reason, assignee, child-ticket, or routing details.
- Adds server-derived satisfaction states and inline rating only for an existing eligible unexpired satisfaction record on a closed ticket; no satisfaction token is exposed or decrypted through the live API.
- Standalone and inline satisfaction use one atomic audited idempotent submission function; reopened tickets preserve submitted acknowledgement and B-22 polling remains unchanged.
- Ruff and strict MyPy passed across 149 source files; all 307 backend tests passed. Frontend ESLint, TypeScript, all 32 tests, and the production build passed. No migration was added.

## 1.48.1 — 2026-08-28

Status: corrected self-contained Windows x64 release built and verified; supersedes 1.48.0.

- Integrates the B-45 search input into the actual MUI dropdown list and corrects matching to normalized, case-insensitive contained text.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 306 backend tests passed.
- Frontend ESLint, all 31 tests including real MUI Select integration coverage, TypeScript, and the production build passed.
- Clean migration using the packaged standalone runtime reached `0144_handover_cleanup`; runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest/version/head, IIS `APP_VERSION`, required contents, ZIP integrity, and forbidden-file checks passed.
- Package: `releases/SupportHub-1.48.1.zip` (42,512,256 bytes; 1,711 entries).
- SHA-256: `DEABBCB8120B1ACBFD66BB063C389280293AEC9D721E932A8C923A88B10497D0`.

## 1.48.0 — 2026-08-28

Status: self-contained Windows x64 release built and verified, but superseded by corrected release 1.48.1; do not deploy.

- Packages B-45 searchable form dropdowns across the system.
- Database compatibility revision remains `0144_handover_cleanup`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 306 backend tests passed.
- Frontend ESLint, all 31 tests, TypeScript, and the production build passed. Vite's existing large-chunk advisory remains non-blocking.
- Clean migration using the packaged standalone runtime reached `0144_handover_cleanup`; runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest/version/head, IIS `APP_VERSION`, required contents, ZIP integrity, and forbidden-file checks passed.
- Package: `releases/SupportHub-1.48.0.zip` (42,510,822 bytes; 1,711 entries).
- SHA-256: `942B57727EB75EC3C31D411538FDEFC6281C0F9E239E5A14AC2C571FC1565775`.

## B-45 checkpoint — 2026-08-28

Status: implemented and verified in the working tree; not yet packaged.

- Audited 197 form-selector locations across 62 frontend files.
- Added one shared searchable MUI Select menu with case-insensitive visible-label filtering, keyboard-safe input, sticky responsive search, and an explicit no-results state.
- Existing dedicated autocomplete/server-backed selectors retain their scoped loading behavior; action and navigation menus are unchanged.
- Frontend ESLint, TypeScript, two focused regression tests, all 31 frontend tests, and the production build passed. Vite's existing large-chunk advisory remains non-blocking.

## 1.47.1 — 2026-08-28

Status: corrected self-contained Windows x64 release built and verified; supersedes 1.47.0.

- Includes the Project Handover `0144_handover_cleanup` correction, exact workspace route guards, user permission-source visibility, B-42 responsive UX improvements, and B-43 unified Knowledge/portal training navigation.
- Database compatibility revision: `0144_handover_cleanup`.
- 1.47.0 must not be deployed because it does not include the direct-override and renamed-profile cleanup.
- Ruff and strict MyPy passed across 149 source files; all 306 backend tests passed.
- Frontend ESLint, all 29 tests, TypeScript, and the production build passed. Vite's large-chunk advisory remains non-blocking.
- Clean migration through `0144_handover_cleanup` using the packaged standalone runtime passed; runtime help exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest, IIS `APP_VERSION`, database head, release notes, permission catalog, required migration, ZIP integrity, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.47.1.zip` (42,506,548 bytes; 1,711 entries).
- SHA-256: `9B3542FFC59754A8B831EED1B0BB600327F4EE2BAB18542D73A383444195F080`.

## Project Handover workspace-isolation correction — 2026-08-28

Status: implemented and verified; release 1.47.0 is superseded and must not be deployed without this correction.

- Migration `0144_handover_cleanup` recognizes canonical and renamed Project Handover profiles, restores the complete eight-permission baseline including `project_handover.client.create`, removes broad Client/Contract/Operations profile assignments, and removes broad active `ALLOW` user overrides for assigned Project Handover users.
- Exact frontend route guards now reject Contract Workspace and Operations Workspace URLs unless the user independently holds the corresponding workspace permission. Sidebar visibility remains based on the same exact permissions.
- Permissions received from another active profile remain effective; the cleanup does not weaken separately authorized roles.
- Ruff, strict MyPy, all 305 backend tests, frontend ESLint/TypeScript, all 27 frontend tests, production build, and clean migration through `0144_handover_cleanup` passed.

## User permission-source visibility — 2026-08-28

Status: implemented and verified; not yet packaged.

- Added a `profile.manage`-protected user permission-access endpoint returning profile-derived sources, complete direct override history, active/expired state, ALLOW/DENY effect, validity, scope, reason, approver/creator identity, and the final effective permission set.
- Edit User now displays direct overrides separately from assigned profiles and explains that DENY overrides take precedence.
- Ruff, strict MyPy, focused backend coverage, frontend ESLint/TypeScript, and production build passed.

## 1.47.0 — 2026-08-27

Status: self-contained Windows x64 release built and verified; database head `0143_project_delivery`.

- Packages B-36 daily exception logging, the B-32 and B-39 post-release corrections, and B-40 compact Contract Workspace/scoped Project Delivery access.
- Adds migration `0143_project_delivery` and six dedicated Project Delivery permissions without credential reveal.
- Remaining numbered backlog: B-38 and B-41.
- Ruff and strict MyPy passed across 149 source files; all 305 backend tests passed.
- Frontend ESLint, all 25 tests, TypeScript, and production build passed.
- Clean standalone-runtime migration through `0143_project_delivery`, runtime help, manifest/version/database head, ZIP integrity, migration/release-note/permission-catalog inclusion, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.47.0.zip` (42,496,269 bytes; 1,711 entries).
- SHA-256: `3A157F6157CDA6F9EBB4C7139C0C1C9F99BABD2B7B7F14CF9D86A71C501287C9`.

## B-39 confirmed access workflow checkpoint — 2026-08-27

Status: implemented and verified; not included in immutable corrected release 1.46.1.

- Shows only a compact clickable icon for a missing capability; no permission dialog opens automatically.
- The icon dialog offers a normal permission request recorded as `REQUESTED` or an immediate credential-authorized shared-profile grant recorded as `DIRECT_GRANTED`.
- Direct grants preview the primary profile and affected-user count, require an active authorized approver who holds both in-context grant authority and the capability, apply account lockout, prohibit self/high-risk grants, update the profile atomically, refresh permissions, audit the action, and notify the requester.
- Access Requests displays requester and source/latest action evidence for both paths.
- Ruff and strict MyPy passed; four focused backend tests and all 305 backend tests passed; ESLint, focused icon coverage, all 25 frontend tests, TypeScript, and production build passed.
- Database head remains `0142_portal_training`; no migration or release artifact was created.

## B-32 notification correction checkpoint — 2026-08-27

Status: implemented and verified; not included in immutable corrected release 1.46.1.

- Keeps routine successful 15-minute access-token renewal silent.
- Emits **Connection restored** only after a refresh cycle encounters a transient connection/server failure and then succeeds.
- Preserves the access-token lifetime, authoritative session termination, shared in-flight refresh, and browser-lock coordination.
- ESLint, two focused regression tests, all 24 frontend tests, TypeScript, and the production build passed.

## B-36 implementation checkpoint — 2026-08-27

Status: implemented and verified; not included in immutable corrected release 1.46.1.

- Preserves IIS/HttpPlatformHandler `uvicorn_*` process-output logs and adds separate Cairo-day `support-hub-errors-YYYY-MM-DD.log` files for application `ERROR`/`CRITICAL` records.
- Uses a Windows inter-process lock so four IIS workers append complete JSON records without rotating or renaming a shared active file.
- Adds safe exception/token/credential redaction, correlation and deployment identity, Unicode output, inactive-day gzip compression, 30-day retention, a 512 MB total cap, duplicate-handler prevention, and stream fallback when file logging fails.
- Adds deployment settings to `web.config` and `.env.example`; the IIS application-pool identity requires Modify access to the configured error-log directory.
- Ruff and strict MyPy passed across 149 source files; four focused logging tests and all 304 backend tests passed.
- Database head remains `0142_portal_training`; no migration or release artifact was created.

## 1.46.1 — 2026-08-27

Status: corrected self-contained Windows x64 release built and verified; supersedes 1.46.0 for deployment.

- Converts ordinary permission-denied API responses into requestable access dialogs using exact backend-provided permission metadata and securely bound action resources.
- High-risk access remains restricted to Profiles & Privileges.
- Database head remains `0142_portal_training`; no migration is added.
- Ruff and strict MyPy passed across 149 source files; all 300 backend tests passed.
- Frontend ESLint, all 22 tests, TypeScript, and production build passed.
- Standalone runtime help, manifest/version/database head, ZIP integrity, migration inclusion, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.46.1.zip` (42,457,371 bytes; 1,708 entries).
- SHA-256: `BECE5D1422F57FF682801E5A0C061B4FD3421F33D0E35EC8EF03E088C8856304`.

## 1.46.0 — 2026-08-27

Status: self-contained Windows x64 release built and verified; database head `0142_portal_training`.

- Packages B-24, B-29–B-32, B-34, B-35, B-37, and B-39 on top of corrected release 1.45.1.
- Adds migrations `0139_auth_events` through `0142_portal_training`.
- Remaining backlog after this release: B-36 and B-38.
- Ruff and strict MyPy passed across 149 source files; all 299 backend tests passed.
- Frontend ESLint, all 21 tests, TypeScript, and production build passed.
- Clean SQLite migration through `0142_portal_training`, standalone runtime help, manifest/version/database head, ZIP integrity, migration and release-note inclusion, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.46.0.zip` (42,455,392 bytes; 1,708 entries).
- SHA-256: `23EDAD1C606AF55A0B963383E4F5E27F86EB245658E6DB3393E2A34A5C6D459C`.

## Packaged development handoff — 2026-08-27

Status: packaged in corrected release 1.46.1; resume with B-36 after confirmation and do not rebuild completed work. Release 1.46.0 is superseded and must not be deployed.

- Implemented and verified B-32 unexpected-logout prevention: bounded refresh retries, no credential clearing on transient failures, coordinated multi-tab refresh, client-safe reason diagnostics, safe return navigation, explicit cross-tab logout, authentication events, and a renewable 30-day inactivity window with a five-minute warning.
- Enhanced B-21 complaint registration with searchable client/caller/ticket/engineer selection, mandatory caller, separate handler and multiple complaint-subject engineers, ticket-list registration fast action, popup status transitions, and Customer Success engineer-rating/comment columns plus searchable filters.
- Implemented and verified B-24 unified Send Actions for ticket list and details using one server eligibility manifest and one shared dialog for rating, live tracking, and linked-complaint tracking.
- Repeated live-ticket and complaint tracking preparations reuse recoverable encrypted valid tokens; delivery preparation remains permission-enforced and audited.
- Added and verified B-31 shared mobile multi-select dismissal with explicit Done/Cancel behavior and no history pollution.
- Added and verified B-39 governed access requests, password step-up approval, expiring user overrides, immutable evidence, notifications, and calm access-required UI.
- Added and verified B-29 one scoped server-side Inactive Clients metric and shared drilldown card across Clients, Tickets, Support Dashboard, and Top Management Dashboard.
- Added and verified B-37 default-private Training Material publication, portal-safe resource enforcement, dedicated portal permission, audited controls, and portal training view.
- Added and verified B-35 consolidated Contract Workspace navigation with embedded permission-aware Contract Templates, legacy URL redirection, responsive layout, and unsaved-edit protection; removed the duplicate sidebar entry.
- Added and verified B-34 compact Contract Types accordions with status/default/SLA/client-count summaries, URL deep links, unmounted collapsed details, and an on-demand searchable paginated linked-client dialog.
- Added and verified B-30 semantic Client Information name links, a permission-controlled row-level interactive-profile action, distinct Edit behavior, responsive row actions, and URL-backed list-state restoration.
- Added migrations `0141_access_requests` and `0142_portal_training`; current working-tree database compatibility head is `0142_portal_training`.
- Verification at stop: Ruff and strict MyPy passed; all 300 backend tests passed; frontend ESLint, TypeScript, all 22 tests, and production build passed; clean SQLite migration through `0142_portal_training` passed.
- Corrected release artifact `releases/SupportHub-1.46.1.zip` was built from this working tree at revision `0142_portal_training`.
- Next queue: B-36, B-38. Continue the established rule of stopping after each completed point for confirmation.

## 1.45.1 — 2026-08-27

Status: corrected self-contained Windows x64 release built and verified; database head remains `0138_customer_success`.

- Supersedes `1.45.0`, whose SQL Server upgrade rejected the unquoted reserved `site_settings.key` identifier in migration `0136`.
- Quotes `[key]` and `[value]` in migrations `0136` and `0137` while preserving SQLite and SQL Server compatibility.
- Adds regression coverage for reserved identifiers and expands the release note with completed points, prioritized remaining points, and their canonical source files.
- Ruff and strict MyPy passed across 148 source files; all 293 backend tests passed.
- Frontend ESLint, all 14 tests, TypeScript, and production build passed.
- Clean migration through `0138_customer_success`, standalone runtime help, manifest/database head, ZIP integrity, migration inclusion, packaged backlog sources, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.45.1.zip` (42,389,946 bytes; 1,694 entries).
- SHA-256: `B0EDB5677A881A9A587E5BE5F8DE6BDF34C2F06FFC7C766EE024CE50DE147741`.

## 1.45.0 — 2026-08-26

Status: self-contained Windows x64 release built and verified; database head `0138_customer_success`.

- Packages B-21 complaint management, B-22 status-aware public polling, and B-23 Customer Success analytics.
- Also includes working-tree implementations B-25 through B-28.
- Adds migrations `0135_notification_rule_archive` through `0138_customer_success`.
- Remaining backlog is reduced to ten prioritized items: B-24, B-29–B-32, and B-34–B-38.
- Ruff and strict MyPy passed across 148 source files; all 292 backend tests passed.
- Frontend ESLint, all 14 tests, TypeScript, and the production build passed.
- Clean migration through `0138_customer_success`, standalone runtime help, manifest/database head, refreshed 159-right permission catalog, ZIP integrity, migration inclusion, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.45.0.zip` (42,368,448 bytes; 1,692 entries).
- SHA-256: `90F854E864D89359E6207366B42F0A977EE98D06EA88CDA2D4C5B53470CCA52B`.

## 1.44.0 — 2026-08-26

Status: self-contained Windows x64 release built and verified; database head `0134_satisfaction_delivery`.

- Adds permission-controlled manual satisfaction delivery by WhatsApp or queued email, reusable encrypted rating links, configurable templates/channels/expiry, and audit records.
- Modernizes secure public ticket tracking with client and ticket details, resolution timing, and timestamped status flow while retaining public-comment-only visibility.
- Remaining backlog item after this release: B-21 complaint-management workflow.
- Ruff and strict MyPy passed; all 290 backend tests passed.
- Frontend ESLint, all 12 tests, TypeScript, and production build passed.
- Standalone runtime help, manifest/database head, ZIP integrity, migration inclusion, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.44.0.zip` (42,294,851 bytes; 1,675 entries).
- SHA-256: `F551CE818CECC27D7D6E9D836B5E38EC6F5174D85B4B9D67444F549FBD470415`.

## 1.43.1 — 2026-08-26

Status: self-contained Windows x64 release built and verified.

- Adds dedicated `ticket.live_update.send` authorization for the Copy/Send live-update buttons and API.
- Removes the Ticket Details page dependency on configuration-management access for reading the non-sensitive enabled flag.
- Adds migration `0133_live_update_permission`; existing profiles with `ticket.comment.public` inherit the new permission for backward compatibility.
- Required database revision is `0133_live_update_permission`.
- Ruff passed; MyPy passed across 142 source files; all 288 backend tests passed.
- Frontend ESLint, all 12 Vitest tests, TypeScript, and the production build passed.
- Standalone runtime `--help`, manifest version/database head, ZIP integrity, permission catalog, migration inclusion, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.43.1.zip` (42,277,061 bytes; 1,672 entries).
- SHA-256: `E804F37BED47D198C12E48A43E6B6D6E1151DDE90EB18A5B65CAE99698AA1BFB`.

## 1.43.0 — 2026-08-26

Status: self-contained Windows x64 release built and verified.

- Completes backlog B-01 through B-18.
- Adds migrations `0131_ticket_live_updates` and `0132_service_module_links`.
- Required database revision is `0132_service_module_links`.
- Ruff passed; MyPy passed across 142 source files; all 287 backend tests passed.
- Frontend ESLint, all 12 Vitest tests, TypeScript, and the production build passed.
- Standalone runtime `--help`, manifest version/database head, ZIP integrity, migration inclusion, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.43.0.zip` (42,272,413 bytes; 1,671 entries).
- SHA-256: `A49DA7907AD5084D01CA2AF30A17C8102BF5C66DA1C36C94CDAD46F723093583`.

## 1.42.0 — 2026-08-25

Status: self-contained Windows x64 release built and verified.

- Improves Forgot Password delivery for username-or-email requests.
- Sends recovery only to the matching active user's registered email and includes the username plus a secure one-time reset link.
- Attempts delivery immediately when SMTP is enabled while retaining queued retry and dead-letter diagnostics.
- Prevents expired queued reset links from being delivered after SMTP is restored.
- Includes the guarded master-preserving transaction-reset SQL script.
- Database revision remains `0130_shift_type_defaults`; no new migration is required.
- Ruff passed; MyPy passed across 141 source files; all 282 backend tests passed.
- Frontend ESLint, all 12 Vitest tests, TypeScript, and the production build passed.
- Standalone runtime `--help`, manifest version/database head, ZIP integrity, reset-script inclusion, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.42.0.zip` (42,248,377 bytes; 1,666 entries).
- SHA-256: `6982FCF3DDBD6E5B29E67BA74FCD522BF84AC1A197ACE674CEBEA06B8CFF85AB`.

## Unreleased — Password recovery email delivery — 2026-08-25

Status: implemented and verified; included in release 1.42.0 (not in immutable release 1.41.0).

- Keeps username-or-email recovery lookup and sends only to the matching active user's registered email.
- Attempts password-reset email delivery immediately when SMTP is enabled while retaining retry/dead-letter processing.
- Includes the username and secure one-time reset link in the email; plaintext reusable passwords are not emailed.
- Prevents expired queued reset links from being delivered after SMTP is restored.
- Clarifies the Forgot Password screen and preserves the generic response that prevents account discovery.
- Focused Ruff, MyPy, 16 backend recovery/email tests, frontend ESLint, and TypeScript passed.

## Unreleased — Master-preserving transaction reset — 2026-08-25

Status: script created and packaged in release 1.42.0; not executed against any database and not included in immutable release 1.41.0.

- Adds `scripts/Reset-SupportHubTransactions.sql` for guarded SQL Server operational-data cleanup.
- Defaults to preview-only and requires exact database-name plus confirmation-phrase checks before execution.
- Resets tickets, Shifts/scheduling, Internal Operations, scheduled Visits, communications, import history, and audit/auth logs while preserving master/configuration data.
- Provides disabled-by-default switches for finance, onboarding assignments, renewals, and project handovers.
- Runs in one transaction, reseeds selected identity tables, and revalidates all constraints before commit.

## 1.41.0 — 2026-08-25

Status: self-contained Windows x64 release built and verified.

- Makes unassigned and understaffed calendar coverage details directly actionable.
- Adds an Assign Engineers button showing the number of open positions.
- Opens Quick Shift with the coverage date, Shift Type, and team prefilled while retaining availability, eligibility, workload, and conflict validation.
- Hides assignment actions for fully staffed slots and users without Shift creation permission.
- Database revision remains `0130_shift_type_defaults`; no new migration is required.
- Verification passed: Ruff; strict MyPy over 141 source files; 281 backend tests; ESLint; 12 frontend tests; TypeScript; and Vite production build.
- Standalone runtime `--help`, manifest version/database head, ZIP integrity, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.41.0.zip` (42,244,945 bytes; 1,665 entries).
- SHA-256: `C9D02E4DFEA8F8FA0E8BA3BB4FFE266B2056C9C1425628DD5DD89BC62AA11F54`.

## Unreleased — Assign from calendar coverage details — 2026-08-25

Status: implemented and focused frontend validation passed; included in release 1.41.0 (not in immutable release 1.40.0).

- Adds an Assign Engineers action to unassigned and understaffed coverage-slot cards.
- Opens Quick Shift with the coverage date, Shift Type, and team prefilled while retaining availability and conflict validation.
- Shows the exact number of open positions and hides the action when the slot is already fully staffed or the user cannot create Shifts.
- Frontend ESLint, TypeScript, and focused Quick Shift tests passed.

## 1.40.0 — 2026-08-25

Status: self-contained Windows x64 release built and verified.

- Extends Quick Shift from one date to an inclusive Date From / Date To range of up to 31 days.
- Requires Manual and Suggested engineers to be available across the whole range and recalculates Auto Balance independently per day.
- Creates or reuses daily coverage slots and creates all range assignments transactionally.
- Retains backward compatibility for legacy single-date Quick Shift API requests.
- Database revision remains `0130_shift_type_defaults`; no new migration is required.
- Verification passed: Ruff; strict MyPy over 141 source files; 281 backend tests; ESLint; 12 frontend tests; TypeScript; and Vite production build.
- Standalone runtime `--help`, manifest version/database head, ZIP integrity, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.40.0.zip` (42,244,712 bytes; 1,665 entries).
- SHA-256: `AC060D390760E9D1A80DFCCF33502B6D77F220E0C3F1FB9AC7CCBD7198FFDBFC`.

## Unreleased — Quick Shift date range — 2026-08-25

Status: implemented and focused validation passed; included in release 1.40.0 (not in immutable release 1.39.0).

- Replaces the one-date Quick Shift input with inclusive Date From / Date To fields, limited to 31 days.
- Manual and Suggested assignment require engineers to be available across the full range; Auto Balance selects independently per day.
- Creates daily coverage slots and all Draft Shifts in one transaction, with backward compatibility for the legacy single-date API payload.
- Focused backend Ruff, MyPy, and Shift tests passed; frontend ESLint, TypeScript, and Quick Shift test passed.

## 1.39.0 — 2026-08-25

Status: self-contained Windows x64 release built and verified.

- Simplifies normal scheduling to Date → Shift Type → Engineers → Create through the responsive Quick Shift workflow.
- Adds canonical Shift Type start/end times and required headcount through additive revision `0130_shift_type_defaults` without rewriting historical Shift timestamps.
- Enforces active Shift participation independently from optional Shift Type eligibility and provides batched conflict/workload context for Manual, Suggested, and Auto Balance assignment.
- Simplifies Shift Workload and moves expert planner tools behind progressive disclosure while retaining generator, coverage, recipes, rotations, and calendar functionality.
- Pre-release validation passed: clean migration to `0130_shift_type_defaults`; Ruff; strict MyPy over 141 source files; 280 backend tests; ESLint; 12 frontend tests; TypeScript; and Vite production build.
- Standalone runtime `--help`, manifest version/database head, ZIP integrity, and forbidden-file inspection passed.
- Package: `releases/SupportHub-1.39.0.zip` (42,240,846 bytes; 1,665 entries).
- SHA-256: `8F8E3BFB4F1CE82F5314B3DE8B860E428CDF3D74A423D8A5094D429A19092D90`.

## 1.37.2 — 2026-08-24

Status: release built and verified.

- Corrects the omitted `shift_patterns.effective_from` and `shift_patterns.effective_to` schema migration.
- Preserves existing shift-pattern rows with nullable effective dates.
- Database migration head: `0125_shift_pattern_dates`.
- Verification: clean migration passed; Ruff and strict MyPy passed for 136 source files; 263 backend tests and 9 frontend tests passed; ESLint, TypeScript, and Vite production build passed.
- Standalone runtime smoke test passed; ZIP contains 1,650 entries and zero forbidden cache/development entries.
- Package: `releases/SupportHub-1.37.2.zip` (42,071,800 bytes).
- SHA-256: `0FF88CD16F4809E1F1954C11FADDBA1F3ACD6DA7F8AA363B55A57ECBBD95A1C3`.

## 1.37.1 — 2026-08-24

Status: release built and verified.

- Corrected ticket client-name rendering and mutually exclusive fast-action filters.
- Hardened package hygiene to exclude generated Python cache and bytecode files.
- Database migration head: `0124_template_effective_dates`.
- Verification: Ruff passed; strict MyPy passed for 136 source files; 263 backend tests passed; 9 frontend tests passed; ESLint, TypeScript, and Vite production build passed.
- Standalone runtime `--help` smoke test passed; ZIP contains 1,649 entries and zero forbidden cache/development entries.
- Package: `releases/SupportHub-1.37.1.zip` (42,069,355 bytes).
- SHA-256: `ECFABA65EB5E8E88599864BD8314D129307E9F707E2789E5864C9E15639A8E00`.

## 1.37.0 — 2026-08-24

Status: release verification and packaging in progress.

- Adds persisted effective Date From / Date To fields to reusable roster and internal-operation templates through revision `0124_template_effective_dates`.
- Restores Material Type and URL to Training Material create/edit and expands checklist-item editing.
- Adds audited, history-preserving employee onboarding unassignment.
- Adds Horizontal and Vertical people hierarchy modes with profile photos in Onboarding and Users.
- Replaces the user-creation image URL with managed JPG, PNG, or WebP selection and upload.
- Includes the populated SQL Server onboarding-index correction from revision `0123_onboarding_programs`.

## 1.36.0 — 2026-08-24

Status: self-contained Windows x64 release generated and verified.

- Renames the unified planner to Shifts Calendar and nests permission-isolated Internal Operations and Visit Operations beneath Operation Jobs while retaining legacy links.
- Makes weekly roster templates user-independent and applies them to selected engineers across an inclusive Date From / Date To range.
- Makes hidden roster rows interactively expandable and aligns Internal Operations controls with exact backend function permissions.
- Corrects all nullable onboarding code indexes in revision `0123_onboarding_programs` for populated SQL Server databases by using filtered unique indexes.
- Retains database compatibility revision `0123_onboarding_programs`.
- Verification passed: Ruff, strict MyPy across 136 source files, all 262 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.
- Packaged runtime help, manifest version/database head, ZIP integrity, and forbidden-data inspection passed.
- Release artifact: `releases/SupportHub-1.36.0.zip` (43,915,149 bytes).
- SHA-256: `A03E0831D713788AAC09960130D039007EABA2D74DAF39A3611E4D8F3A229E50`.

## 1.35.0 — 2026-08-24

Status: self-contained Windows x64 release generated and verified.

- Consolidates My Queue, engineer/team/department queues, and CSV export in the ticket Fast Actions bar; moves Columns and Save View into a fully clickable filter bar.
- Adds saved Group By behavior for status, priority, engineer, team, department, client, source, and entitlement, plus filters for ticket text, operational attributes, safety flags, and additional lifecycle date ranges.
- Expands onboarding templates with stable codes, categories, duration/order, task types, completion rules, availability offsets, due offsets, and approval requirements.
- Adds reusable role-program bundles, single-plan bundle snapshots, employee submission, manager/override approval, required-task rules, and automatic plan completion.
- Adds idempotent default onboarding catalogs and PACS, RIS, and general-support programs without inserting resource URLs.
- Database compatibility advances to additive revision `0123_onboarding_programs`.
- Verification passed: clean migration rehearsal, Ruff, strict MyPy across 136 source files, all 260 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.
- Packaged runtime help, manifest/web.config version `1.35.0`, database head `0123_onboarding_programs`, ZIP integrity, and forbidden-data inspection passed.
- Release artifact: `releases/SupportHub-1.35.0.zip` (43,910,641 bytes).
- SHA-256: `062B0B6DA984C5E1B9ED2B7ABD9C77381BB5F89965B70028070190C68E09593C`.

## 1.34.0 — 2026-08-24

Status: self-contained Windows x64 release generated and verified.

- Adds edit and safe-delete administration for training material categories, training materials, their resources, and checklist templates. Delete deactivates referenced records so existing employee onboarding snapshots remain intact.
- Adds From/To operation-template scheduling synchronized with selectable weeks 1–4 and weekdays; generated operations must match the chosen date range, week, and day filters.
- Adds `Outdoor / field visit` to operation-template creation and creates governed client-visit occurrences when such a template is applied, including client and entitlement validation.
- No database migration is required for these enhancements.
- Verification passed: Ruff, strict MyPy across 136 source files, all 259 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.
- Packaged runtime help, manifest/web.config version `1.34.0`, database head `0122_operations_permissions`, ZIP integrity, and forbidden-data inspection passed.
- Release artifact: `releases/SupportHub-1.34.0.zip` (43,874,354 bytes).
- SHA-256: `63B25B1100C0A033763BC975B0BAF754D6A7CB6635495C7819BFD7BFEC41ED63`.

## 1.33.1 — 2026-08-24

Status: self-contained Windows x64 corrective release generated and verified.

- Corrects the SQL Server-reserved `current` alias in migration `0122_operations_permissions`.
- Keeps the migration idempotent so a failed 1.33.0 deployment can safely rerun `migrate` with 1.33.1.
- Adds regression coverage for the SQL Server-safe alias and includes all 1.33.0 functionality.
- Verification passed: Ruff, strict MyPy, all 258 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.
- Packaged runtime help, manifest version, database revision, ZIP integrity, and forbidden-data inspection passed.
- Release artifact: `releases/SupportHub-1.33.1.zip` (43,865,568 bytes).
- SHA-256: `79C035DDC3CFC994C92C1AB3F30791E870745D3A7CDB682963CD1740F2730518`.

## 1.33.0 — 2026-08-24

Status: self-contained Windows x64 release generated and verified.

- Replaces the standalone Shift Calendar entry with one permission-aware Operations Workspace while preserving authorized shift scheduling through the merged calendar.
- Separates shifts, internal operations, and field visits by their own effective page, source, and function permissions.
- Adds granular Internal Operations rights and additive database revision `0122_operations_permissions`, with backward-compatible inheritance for existing profiles.
- Keeps Contract Financials visible, permission-explanatory, and directly addressable through contract/tab query parameters.
- Verification passed: clean migration rehearsal, Ruff, strict MyPy across 136 source files, all 257 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.
- Packaged runtime help, manifest version, database revision, self-contained runtime, ZIP integrity, and forbidden-data inspection passed.
- Release artifact: `releases/SupportHub-1.33.0.zip` (43,866,289 bytes).
- SHA-256: `7DCF7979F64EAE34A9AFB74CF18B9053002DF4E89CDB7D14C87C871ACC99A732`.

## 1.32.1 — 2026-08-24

Status: self-contained Windows x64 release generated and verified.

- Add permission-controlled Onboarding Administration screens and APIs for categories, materials/resources, checklist templates/items, and employee assignment.
- Keep the contract Financials tab visible to contract viewers and show a clear permission explanation when `finance.view` is not effective instead of silently removing the tab.
- Preserve immutable release `1.32.0`; all changes will be packaged under a new semantic version after full verification.
- Verification passed: Ruff, strict MyPy across 136 source files, all 257 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.
- Packaged runtime help, manifest version, database revision, and self-contained runtime were verified.
- Release artifact: `releases/SupportHub-1.32.1.zip` (43,862,887 bytes).
- SHA-256: `17F996B9972DFAE23FB8B281FAB3FA90E26884E0D15C9476AD44D0F96E041490`.

## 1.32.0 — 2026-08-24

Status: self-contained Windows x64 release generated and verified.

- Replaces the 200-customer contract Autocomplete with paginated explicit and server-resolved all-matching selection, independent linked-customer search, preview counts, exclusions, and enforced primary-customer retention.
- Always queues eligible password-reset email events and adds administrator delivery diagnostics for queued, retrying, sent, and dead messages without weakening the generic public response.
- Makes Today's Tickets deterministic and adds a permission-controlled operational fast-action ribbon for today's unassigned, personal, due-soon, and breached queues.
- Makes Internal Operations calendar-first by reusing the workforce calendar and extends reusable operation templates with monthly, specific-date, and From/To selection while retaining governed Visit Operations.
- Adds employee Onboarding checklist snapshots, training-material/resource indexing, Reports-To hierarchy visualization, permissions, API, UI, and additive database revision `0121_employee_onboarding`.
- Includes the previously verified flexible shift-template date-selection enhancement.
- Release gates passed: clean migration rehearsal, Ruff, strict MyPy across 136 source files, all 256 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.
- Packaged runtime help, manifest version, IIS configuration version, database head, and self-contained runtime presence were verified.
- Release artifact: `releases/SupportHub-1.32.0.zip` (43,841,024 bytes).
- SHA-256: `3B9D281B4CAC90AC8130646883E5A67D9173A30E6AEDBB5723372335956372C1`.

## Unreleased — Flexible shift-template date selection — 2026-08-24

Status: implemented and verified; not included in immutable release 1.31.5.

- Adds Monthly pattern, Specific dates, and Date range modes when applying reusable shift templates.
- Shows the exact selected dates and projected engineer-shift count before generation.
- Deduplicates specific dates, supports weekday filtering within ranges, and limits a range to 366 inclusive calendar days.
- Preserves the existing monthly API behavior and conflict-skipping protections.
- Verification passed: Ruff, strict MyPy, all 255 backend tests, ESLint, all nine frontend tests, TypeScript, and the production Vite build.

## 1.31.5 — 2026-08-24

Status: self-contained Windows x64 release generated and verified.

- Hardens the IIS backend for 20–50 or more concurrent users with four HttpPlatformHandler processes and bounded per-process SQL connection pools.
- Coordinates the escalation/email/Outlook scheduler across processes with a SQL Server application lock.
- Bounds concurrent Argon2 password verification per process so login bursts cannot exhaust backend memory.
- Returns a structured retryable 503 when the SQL pool is temporarily exhausted and adds startup retries, regression coverage, and an operator login-load utility.
- Retains database compatibility revision `0120_internal_ops_lifecycle`; no migration is required.
- Backend Ruff and MyPy passed across 133 source files; all 253 backend tests passed.
- Frontend ESLint, all six tests, TypeScript, and the production Vite build passed.
- Packaged runtime help, manifest/version, IIS process/pool settings, login-load utility inclusion, ZIP integrity, and forbidden-data inspection passed.
- Release artifact: `releases/SupportHub-1.31.5.zip` (43,783,504 bytes).
- SHA-256: `3DED259C40FD2138500B1447E8BB71880C236164F116CFBDA92A217FC9307772`.

## 1.31.4 — 2026-08-23

Status: self-contained Windows x64 release generated and verified.

- Removes the remaining Shift Planning template dependency on the administrative `/users` endpoint and `user.manage` permission.
- Uses the scoped shift employee selector in reusable and weekly roster templates.
- Keeps Templates and Settings tabs visible but disabled when `shift.manage` is missing, with an explicit permission explanation.
- Adds an idempotent SQL Server seed script for the centralized `DEFAULT_SUPPORT` SLA calendar, targets, and immutable version snapshots.
- Retains database compatibility revision `0120_internal_ops_lifecycle`; no migration is required.
- Backend Ruff, MyPy across 133 source files, and all 249 tests passed.
- Frontend ESLint, all six tests, TypeScript, and the production Vite build passed.
- Standalone runtime check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Release artifact: `releases/SupportHub-1.31.4.zip` (43,766,909 bytes).
- SHA-256: `8384E6CE465D417AD6AFE42CE697FD5118876F33AF3AD07E86B33E27E834F9B1`.

## 1.31.3 — 2026-08-23

Status: self-contained Windows x64 release generated and verified.

- Adds Created by, Department, and hierarchy-aware Parent department ticket filters and optional columns.
- Extends saved views and ticket CSV export with the new organizational filters and fields.
- Corrects environment catalog authorization for legitimate ticket/client/contract readers while preserving management controls.
- Removes the Shift Calendar dependency on `user.manage` by introducing a scoped shift-employee selector.
- Includes all `1.31.2` and `1.31.1` corrections.
- Retains database compatibility revision `0120_internal_ops_lifecycle`; no migration is required.
- Backend Ruff, MyPy across 133 source files, and all 249 tests passed.
- Frontend ESLint, all six tests, TypeScript, and the production Vite build passed.
- Standalone runtime check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Release artifact: `releases/SupportHub-1.31.3.zip` (43,764,080 bytes).
- SHA-256: `1EF634E8134673DD608AF453AF366CEF93C8081ED188AB200A11BB0CA4809155`.

## 1.31.2 — 2026-08-23

Status: self-contained Windows x64 release generated and verified.

- Replaces profile permission autocomplete behavior with separate granted and available-right workspaces.
- Adds searchable permission descriptions, bounded scrolling, high-risk indicators, checkbox multi-selection, and bulk addition.
- Excludes already-granted rights from selection and retains explicit removal controls.
- Includes all `1.31.1` ticket ownership and inactive-client protections.
- Retains database compatibility revision `0120_internal_ops_lifecycle`; no migration is required.
- Backend Ruff, MyPy across 133 source files, and all 247 tests passed.
- Frontend ESLint, all six tests, TypeScript, and the production Vite build passed.
- Standalone runtime check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Release artifact: `releases/SupportHub-1.31.2.zip` (43,745,892 bytes).
- SHA-256: `8359FBC3231267CADA7B4AE0BBA66BE32EA1116ADD8C02855288D4A0954B0CD6`.

## 1.31.1 — 2026-08-23

Status: self-contained Windows x64 corrective release generated and verified.

- Enforces exact ticket assignment for Resolve, Escalate, and Request Help in both the API and ticket UI.
- Makes inactive-client tickets require management entitlement approval and prevents inactive client contracts, products, modules, services, or SLA coverage from being applied.
- Prevents SLA clocks and automatic assignment while inactive-client approval is pending.
- Retains database compatibility revision `0120_internal_ops_lifecycle`; no migration is required from `1.31.0`.
- Backend Ruff and full pytest gates passed; frontend ESLint, TypeScript, and production build gates passed before packaging.
- Standalone runtime check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Release artifact: `releases/SupportHub-1.31.1.zip` (43,745,821 bytes).
- SHA-256: `6C2E341C15012A3BDE3C3EBCD3609A6A401B6C1E2FEA6E3C623B30D57A22E726`.

## 1.31.0 — 2026-08-23

Status: RELEASED — self-contained feature package verified.

- Visit scheduling now automatically creates an approved Outdoor / field visit shift when the selected engineer has no same-day shift.
- Removed `NO_SHIFT_COVERAGE` as a blocking planner conflict.
- Added an in-system decision popup whenever the engineer already has a same-day shift.
- Added options to keep the existing shift and create visit coverage, or transfer the selected shift to another engineer and create visit coverage for the visit engineer.
- Shift transfer validates permissions, active replacement status, and replacement shift overlap.
- Added separate audit evidence for automatic visit-shift creation and same-day shift transfer.
- Added structured conflict details to application error envelopes for decision-oriented UI workflows.
- Added regression coverage for no-shift creation, popup decision details, and transfer-and-create behavior.
- No database migration is required; database head remains `0120_internal_ops_lifecycle`.
- Full release gates passed: Ruff, MyPy over 133 source files, 247 backend tests, frontend ESLint, 6 frontend tests, TypeScript, and the production Vite build.
- Standalone packaged runtime command smoke check passed; Python installation is not required on the server.
- Packaged manifest reports version `1.31.0`, database head `0120_internal_ops_lifecycle`, and `self-contained-windows-x64` deployment mode.
- ZIP integrity inspection passed with 1,946 entries and no `.env`, database, SQLite, or other forbidden data files.
- Release artifact: `releases/SupportHub-1.31.0.zip` (43,741,923 bytes).
- SHA-256: `BF2105BD90B9098C3A4A6DF408615E107A94EA0E8A83464CB702668137E2A663`.

## 1.30.2 — 2026-08-23

## 1.30.2 — 2026-08-23

Status: RELEASED — self-contained hotfix packaged and verified.

- Added a system-wide notification layer for backend conflicts, validation failures, authorization failures, and unexpected API errors.
- Added global required-field warnings that identify the missing field on native and MUI-backed forms.
- Added readable extraction for standard error envelopes and FastAPI validation details, with short-window duplicate suppression.
- Added an inline Visit Entitlement error using the backend message, including `VISIT_PERIOD_OUTSIDE_CONTRACT` guidance.
- Added frontend regression coverage for API messages and required-field warnings.
- Includes the SQL Server-safe, retryable `0120_internal_ops_lifecycle` migration from 1.30.1.
- No new database migration is required; database head remains `0120_internal_ops_lifecycle`.
- Full release gates passed: Ruff, MyPy over 133 source files, 244 backend tests, frontend ESLint, 6 frontend tests, TypeScript, and the production Vite build.
- Standalone packaged runtime command smoke check passed; Python installation is not required on the server.
- Packaged manifest reports version `1.30.2`, database head `0120_internal_ops_lifecycle`, and `self-contained-windows-x64` deployment mode.
- ZIP integrity inspection passed with 1,946 entries and no `.env`, database, SQLite, or other forbidden data files.
- Release artifact: `releases/SupportHub-1.30.2.zip` (43,727,512 bytes).
- SHA-256: `22AD2841190E000C8A3584760D2730D7440A908C0CFBB4BFC747BFDBC0D36D51`.

## 1.30.1 — 2026-08-23

## 1.30.1 — 2026-08-23

Status: RELEASED — self-contained SQL Server migration hotfix packaged and verified.

- Corrected migration `0120_internal_ops_lifecycle` for SQL Server by replacing the nullable-column UNIQUE constraint with a filtered unique index using `WHERE visit_occurrence_id IS NOT NULL`.
- Made revision `0120` safe to retry after a failed deployment by detecting existing columns, foreign keys, and the filtered index.
- Updated ORM metadata to match the SQL Server filtered-index schema.
- Added SQL Server dialect regression coverage and verified a clean migration through `0120_internal_ops_lifecycle`.
- Includes the Internal Operations enhancement and assigned-engineer display correction from 1.30.0.
- Release 1.30.0 must not be retried; deploy 1.30.1 instead.
- Full release gates passed: Ruff, MyPy over 133 source files, 244 backend tests, frontend ESLint, 4 frontend tests, TypeScript, and the production Vite build.
- Standalone packaged runtime command smoke check passed; Python installation is not required on the server.
- Packaged manifest reports version `1.30.1`, database head `0120_internal_ops_lifecycle`, and `self-contained-windows-x64` deployment mode.
- ZIP integrity inspection passed with 1,946 entries and no `.env`, database, SQLite, or other forbidden data files.
- Release artifact: `releases/SupportHub-1.30.1.zip` (43,726,059 bytes).
- SHA-256: `A9FB76BAE2E9AEC5D01CCEEC37863B841C033A92732C6AF6E30F053BF05D3201`.

## 1.30.0 — 2026-08-23

## 1.30.0 — 2026-08-23

Status: withdrawn; replaced by 1.30.1 because migration `0120` used a nullable UNIQUE constraint that fails on populated SQL Server databases.

- Added the Internal Operations lifecycle foundation with a unified tabbed workspace for operational records, templates, types, assignments, scheduling, reporting, and audit-oriented lifecycle tracking.
- Added migration `0120_internal_ops_lifecycle`; SQL Server is the deployment database and no SQLite-specific production migration is required.
- Fixed automatic-assignment engineer labels when **Show only online engineers in assignment** is enabled.
- The current ticket assignee is now always available for display, while online/availability restrictions continue to govern new assignment choices.
- Full release gates passed: Ruff, MyPy over 133 source files, 243 backend tests, frontend ESLint, 4 frontend tests, TypeScript, and the production Vite build.
- Required database revision: `0120_internal_ops_lifecycle`.
- Packaged manifest reports version `1.30.0` and database head `0120_internal_ops_lifecycle`.
- ZIP integrity inspection passed with 698 entries and no `.env`, database, SQLite, or other forbidden data files.
- Release artifact: `releases/SupportHub-1.30.0.zip` (3,271,129 bytes).
- SHA-256: `A1AD6E41D28FCCAF34A9A001541DF8E33266F243594C78A37AB6B2E19BDEE5FE`.

## 1.29.2 — 2026-08-23

Status: RELEASED — immutable artifact packaged and verified.

- Added ticket-first Manager Ticket Finance payments with the ticket's authoritative linked client displayed and locked.
- Added atomic automatic invoice creation when a payment has insufficient existing invoice balance.
- Added confirmed collection entry with required method/reference and idempotent retry behavior.
- Preserved multiple/partial payments, separate currencies, client statements, dashboards, and optional Advanced Ledger actions.
- Added separate automatic-invoice and payment audit evidence.
- No migration is required; database head remains `0119_client_profile_permission`.
- Source verification passed: Ruff, 7 focused finance tests, TypeScript, and production frontend build.
- Full release gates passed: Ruff, MyPy over 132 source files, 242 backend tests, frontend ESLint, 4 frontend tests, TypeScript, and production Vite build.
- Packaged manifest reports version `1.29.2` and database head `0119_client_profile_permission`.
- ZIP integrity inspection passed with 693 entries and no `.env`, database, or SQLite files.
- Release artifact: `releases/SupportHub-1.29.2.zip` (3,249,915 bytes).
- SHA-256: `26F640F82A2F96666E91DFFB93C70922E9EB95724398A2051950FD209F5B0642`.

## 1.29.1 — 2026-08-23

Status: replacement hotfix packaged and verified.

- Added the dedicated `client.profile.view` permission for interactive Client Profile access.
- Removed the Client Profile's dependency on broad `report.view` and `contract.view` permissions.
- Preserved access for the L2 Support, L3 Support, Support Manager, Top Management, and Administrator system profiles.
- Updated the permission catalog workbook with 124 rights and a corrected Client Profile access guide.
- Added migration `0119_client_profile_permission`.
- Required database revision: `0119_client_profile_permission`.
- Verification passed: Ruff, MyPy across 132 source files, 241 backend tests, ESLint, four frontend tests, TypeScript, and the Vite production build.
- Packaged verification passed: standalone runtime help, included permissions workbook, clean packaged migration through `0119_client_profile_permission`, manifest/version consistency, and ZIP integrity.
- Release artifact: `releases/SupportHub-1.29.1.zip` (43,679,839 bytes).
- SHA-256: `2FE3A8093E0D20A78AE6A5539F4D1D9F7A405C1BA78533474AD3D6C17C8734E0`.

## 1.29.0 — 2026-08-23

Status: self-contained Windows x64 release packaged and verified.

- Automatically generates governed identifiers when omitted for employees, contacts, clients, branches, locations, contracts, projects, and supported master-data records.
- Added payment-method capture for ticket-finance collections.
- Added managed contract-template types with seeded Global, HIS, RIS / PACS, Workstation, and Vision Tools choices.
- Granted the Top Management profile read-only access to the financial dashboard.
- Added migrations `0116_finance_payment_methods`, `0117_contract_template_types`, and `0118_top_mgmt_finance`.
- Required database revision: `0118_top_mgmt_finance`.
- Verification passed: Ruff, MyPy across 132 source files, 240 backend tests, ESLint, four frontend tests, TypeScript, and the Vite production build.
- Packaged verification passed: standalone runtime help, clean packaged migration through `0118_top_mgmt_finance`, manifest/version consistency, and ZIP integrity.
- Release artifact: `releases/SupportHub-1.29.0.zip` (43,664,212 bytes).
- SHA-256: `2D3EC69CBCB4AFC50508BC8CE9962D2512E3785EF7319AB773426D8CDA0B14EF`.

## 1.28.1 — 2026-08-23

Status: replacement hotfix packaged and verified.

- Corrected migration `0114_contract_templates` for populated SQL Server databases by making nullable contact-code and onboarding-idempotency uniqueness indexes filtered with `IS NOT NULL`.
- Updated the ORM metadata to use the same filtered-index behavior on SQL Server and SQLite.
- Added SQL Server dialect regression coverage for both filtered unique indexes.
- Includes all department collaboration, client sharing, escalation queues, and contract-template features from 1.28.0.
- Database head remains `0115_client_department_sharing`.
- Release 1.28.0 is withdrawn and must not be deployed.
- Verification passed: Ruff, MyPy across 132 source files, 236 backend tests, SQL Server dialect assertions, ESLint, four frontend tests, TypeScript, and Vite production build.
- Packaged verification passed: corrected migration inspection, standalone runtime help, clean packaged migration and seed through `0115_client_department_sharing`, manifest/version consistency, ZIP integrity, and forbidden-file inspection.
- Release artifact: `releases/SupportHub-1.28.1.zip` (43,607,393 bytes).
- SHA-256: `3904648FE1CC0DDB449536BC6BBBDF45AA11C8A95A659048E90067E111036B9F`.

## 1.28.0 — 2026-08-22

Status: withdrawn; replaced by 1.28.1 because migration `0114` was not safe for multiple existing NULL contact codes on SQL Server.

- Added controlled cross-department ticket help requests with department/team/engineer routing, return-to-Support results, notifications, audit evidence, and Saved View filters.
- Added an Escalations workspace with Received, Sent, and Returned queues while preserving Support ownership of the parent ticket.
- Added client primary-owner and normalized multi-department sharing, available during client creation and editing without granting blanket ticket visibility.
- Automatically provisions department-scoped escalation Saved Views when a department is created; authorization continues to use generic department permissions and membership scope.
- Added reusable contract templates, default/clone/version administration, contract provenance, acceptance dates, generated identifiers, atomic client onboarding, and existing-client contract creation.
- Added migrations `0113_department_collaboration`, `0114_contract_templates`, and `0115_client_department_sharing`.
- Required database revision: `0115_client_department_sharing`.
- Pre-release verification passed: Ruff, MyPy across 132 source files, 235 backend tests, ESLint, four frontend tests, TypeScript, and Vite production build.
- Packaged verification passed: standalone runtime help, clean packaged migration and seed through `0115_client_department_sharing`, manifest/version consistency, ZIP integrity, and forbidden-file inspection.
- Release artifact: `releases/SupportHub-1.28.0.zip` (43,603,382 bytes).
- SHA-256: `884F81BEE49427F1736D5733ED2AEC5A884C9184DA33739087BB887FF61E4B79`.

## 1.27.0 — 2026-08-22

Status: self-contained feature release packaged and verified.

- Consolidated Manager Finance and Invoices & Payments into one Financial workspace with executive dashboard, invoice/payment, and ticket-finance tabs.
- Added governed draft invoice creation, uncollected invoice editing, confirmation, cancellation, and payment permissions with mandatory audited reasons.
- Added currency-safe portfolio and per-contract totals for contract value, invoice value, paid, remaining, discount, and additional values.
- Added `finance.dashboard.view` and financial normal-dashboard widgets assignable to specific profiles.
- Added migration `0112_financial_governance`; existing `finance.manage` profiles inherit the granular finance permissions.
- Pre-release verification passed: clean migration, Ruff, MyPy, 227 backend tests, ESLint, TypeScript, four frontend tests, and Vite production build.
- Packaged verification passed: standalone runtime help, packaged clean migration through `0112_financial_governance`, manifest/version consistency, and forbidden-file inspection.
- Release artifact: `releases/SupportHub-1.27.0.zip` (42,275,618 bytes).
- SHA-256: `1A0926BB869E80264F7CBC760857E6B1D6F399BAC3D93B133FDECD898C6F27BA`.

## 1.26.2 — 2026-08-22

Status: self-contained release packaged and verified.

- Added repair migration `0111_finance_schema_repair` for incomplete finance schemas that were incorrectly recorded as current.
- Added correlation-aware traceback logging for unexpected API failures.
- Reworked Invoices & Payments into one editable transaction row per scheduled invoice and exposed adjustment reason codes in-row.
- Retained permission-controlled client statements in Invoices & Payments and Client Profile.
- Prevented an API failure from also displaying the misleading empty-schedule message.
- Verification passed: clean migration through `0111_finance_schema_repair`, packaged-runtime migration, Ruff, MyPy, 226 backend tests, ESLint, four frontend tests, TypeScript, Vite production build, and standalone runtime help.
- Release artifact: `releases/SupportHub-1.26.2.zip` (42,263,376 bytes).
- SHA-256: `1F6124282CABCCB043C06E665552773612B14A863D724DCB86F91CFECAE48CE1`.

## 1.26.1 — 2026-08-22

Status: replacement hotfix packaged and verified.

- Corrected the contract collection workspace response for historical invoice rows whose stored status or values do not satisfy current invoice-creation validation.
- Separated permissive historical invoice reads from strict invoice-write validation; no database migration is required.
- Added regression coverage for a legacy `PAID` invoice with zero values and a short historical reason.
- Database compatibility remains `0110_contract_finance_simplified`.
- Verification passed: Ruff, MyPy, 226 backend tests, ESLint, four frontend tests, TypeScript, Vite production build, standalone runtime smoke check, ZIP integrity, and forbidden-file inspection.
- Release artifact: `releases/SupportHub-1.26.1.zip` (43,449,940 bytes).
- SHA-256: `32374933B2C0F9D3BDFB48C17E021F97F54AC8AE5753D53A6AA6461BA8A50690`.

## 1.26.0 — 2026-08-22

Status: self-contained Windows x64 release generated and verified.

- Replaced the noisy contract invoice/payment workflow with one contract financial profile and automatically generated monthly, quarterly, or annual invoice schedules.
- Added EGP-default multi-currency selection, contract value, optional fixed invoice amount, billing day, and safe short-month date handling.
- Added a one-click collection workflow with invoice value, actual payment, discount, additional value, governed reason, optional notes, payment reference, and collection date.
- Added governed adjustment-reason master data with SLA deduction, business required deduction, and exception defaults.
- Added per-client statements in Invoices & Payments and Client Profile, plus permission-controlled Excel export and client account activation.
- Preserved legacy manual invoices, receipts, allocations, ticket finance, and API payloads; manual schedules and collected schedules are protected from regeneration.
- Database compatibility revision: `0110_contract_finance_simplified`.
- Verification passed: Ruff, MyPy, 225 backend tests, ESLint, four frontend tests, TypeScript, Vite production build, clean migration, populated upgrade rehearsal, runtime command smoke check, ZIP integrity, and forbidden-file inspection.
- Release artifact: `releases/SupportHub-1.26.0.zip` (43,450,012 bytes).
- SHA-256: `8551C3EA34D5FB36E97CC086C9F8481661DA23F6C4B6C37E7F63BA2355D06CC7`.

## 1.25.3 — 2026-08-21

Status: replacement hotfix packaging complete.

- Corrected the Visit Types active-row predicate to compile as `is_active = 1` on SQL Server instead of invalid `is_active IS 1`.
- Added a SQL Server dialect regression test; no database migration is required.
- Verification passed: Ruff, MyPy, 224 backend tests, ESLint, four frontend tests, TypeScript, Vite production build, and self-contained runtime command smoke check.
- Release artifact: `releases/SupportHub-1.25.3.zip` (43,400,786 bytes).
- SHA-256: `C93E794DB3C92820F42A23F530EDF539BD9C424C2D7D7BD0A10D5A1262850D8E`.

## 1.25.2 — 2026-08-21

Status: hotfix packaging complete.

- Hardened the Visit Types API for SQL Server with explicit required-column queries and a direct operation-type join.
- Preserved idempotent Outdoor / field visit master-data repair without writing when the relationship is already correct.
- No database migration is required; compatibility remains at `0109_shift_rosters`.
- Verification passed: Ruff, MyPy, 223 backend tests, ESLint, four frontend tests, TypeScript, Vite production build, and self-contained runtime command smoke check.
- Release artifact: `releases/SupportHub-1.25.2.zip` (43,400,454 bytes).
- SHA-256: `01CD5F8B9CD5F9997A2D868916656F6CED309C7C18386C9481747DD5FCE813F3`.

## 1.25.1 — 2026-08-21

Status: release packaging complete for visit-type rendering and optional knowledge-article workflows.

- Fixed asynchronous Visit type selection and added visible visit-type labels to entitlement cards.
- Made resolution-generated knowledge articles opt-in through a checkbox in the Resolve Ticket dialog.
- Added an explicit system confirmation to unlink ticket associations before deleting an in-use knowledge article.
- No database migration is required; compatibility remains at `0109_shift_rosters`.
- Target deployment: self-contained Windows x64 under IIS with `/SupportHub/` and `/SupportHub/backend` defaults.
- Verification passed: Ruff, MyPy, 223 backend tests, ESLint, four frontend tests, TypeScript, and the Vite production build.
- Self-contained runtime command smoke check passed; Python installation is not required on the server.
- Release artifact: `releases/SupportHub-1.25.1.zip` (43,398,832 bytes).
- SHA-256: `B5F771977B59C6015780A3500752E932BABC4EBC64CF3EAB202760C57D7EC7E5`.

## 1.25.0 — 2026-08-21

Status: release packaging complete from the verified workforce and operations checkpoint.

- Packages the unreleased scope recorded below: persisted template defaults, unified workforce calendar, internal-operation templates/types and automatic titles, unified Operations Workspace, ticket-ranked visit client paging and multi-client filters, shared outdoor visit master data, and editable weekly shift roster templates.
- Database compatibility revision: `0109_shift_rosters`.
- Target deployment: self-contained Windows x64 under IIS with `/SupportHub/` and `/SupportHub/backend` defaults.
- Verification passed: Ruff, MyPy, 223 backend tests, ESLint, four frontend tests, TypeScript, and the Vite production build.
- Standalone runtime smoke testing passed for `serve`, `migrate`, `seed`, and `recover-admin`.
- Package inspection found no embedded `.env`, database, or SQLite data files.
- Release artifact: `releases/SupportHub-1.25.0.zip` (43,397,717 bytes).
- SHA-256: `6F373355F1D083857224B08EA3924DC1005A6E29A78014D712A783734551AD97`.

## Unreleased — Editable weekly shift roster templates — 2026-08-21

Status: implemented and verified; not included in immutable release 1.24.0.

- Added revision `0109_shift_rosters` with reusable roster templates, independent weekday/shift rows, and per-row engineer assignments.
- Each roster row stores Weeks 1–4, weekday, shift type, From/To time, work location, notes, and one or multiple engineers.
- Added in-system create, full edit, delete, monthly preview, and generation workflows with automatic stable roster codes.
- Supports WFH rotations such as one engineer every Sunday and another every Tuesday, plus mixed office, night, weekend, hybrid, and custom shift types in the same roster.
- Monthly application uses the configured week-start anchor, validates department membership and active master data, skips overlaps safely, reports created/skipped totals, and records audit evidence.
- Shift types referenced by roster rows are protected from deletion.
- Clean SQLite migration passed at `0109_shift_rosters`; Ruff and MyPy passed across 132 source files; all 223 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.

## Unreleased — Shared outdoor visit type — 2026-08-21

Status: implemented and verified; not included in immutable release 1.24.0.

- Added revision `0108_visit_operation_type` to explicitly link contractual visit types with governed Internal Operations types.
- Seeded/backfilled active visit type `OUTDOOR_VISIT` as **Outdoor / field visit** and linked it to the matching Internal Operations type.
- Contract Visit Entitlements now select Outdoor / field visit by default and explain the shared linkage; legacy visit types and existing entitlements remain valid.
- Entitlement API callers may omit `visit_type_id`, in which case the linked Outdoor / field visit type is applied safely.
- The linked Internal Operations type is protected from deletion while it is referenced by contractual visit master data.
- Clean SQLite migration passed at `0108_visit_operation_type`; Ruff and MyPy passed across 132 source files; all 222 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.

## Unreleased — Unified operations workspace and visit client paging — 2026-08-21

Status: implemented and verified; not included in immutable release 1.24.0.

- Consolidated Internal Operations, Visit Operations, and Operational Reports under permission-aware workspace tabs and one sidebar entry.
- Preserved `/visit-operations` and `/operational-reports` as compatibility links that open their corresponding workspace tabs.
- Visit Operations initially requests only 20 clients, ranked by ticket count so clients with ticket activity appear first, with an explicit **View 20 more** action up to 200.
- Added server-side client code/name search, searchable multi-client selection, and exact multi-client filtering across visit summary cards and planner occurrences.
- No database migration was required; database head remains `0107_operation_types`.
- Ruff and MyPy passed across 132 source files; all 221 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.

## Unreleased — Governed shift and operation types — 2026-08-21

Status: implemented and verified; not included in immutable release 1.24.0.

- Added revision `0107_operation_types` with idempotent master data for work-from-home, outdoor visit, meeting, demo, and after-shift operation types.
- Added in-system create, edit, and delete controls for operation types; stable codes are generated automatically and remain unchanged when display names are edited.
- Added shift-type edit and delete controls. Types referenced by existing schedules or reusable templates are protected from deletion with an in-system conflict message.
- Internal-operation creation now fills the free-text title from the selected operation type and refreshes it when the type changes; managers can override the title before saving.
- Type creation, editing, and deletion remain permission controlled and audited.
- Clean SQLite migration passed through `0107_operation_types`; Ruff and MyPy passed across 132 source files; all 221 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.

## Unreleased — Unified workforce calendar and operation templates — 2026-08-21

Status: implemented and verified; not included in immutable release 1.24.0.

- Added revision `0106_operation_templates` and reusable WFH, meeting, demo, and after-shift templates with automatic codes, department scope, saved Weeks 1–4/days/week-start defaults, time/location/instructions, edit/delete, and conflict-skipping monthly application.
- Outdoor visits intentionally remain in governed Visit Operations so templates cannot bypass exact-client entitlement consumption.
- Added operation-template access from Internal Operations with application dialogs and employee bulk selection.
- Unified the Shift Planning calendar across shifts, internal operations, and field visits with source filtering and distinct visual treatment.
- Added manager/department/HR summary cards for available-now coverage, active visits, WFH, meetings, night shifts, and weekend shifts, including employee names and From–To evidence.
- Availability means active shift coverage without an overlapping visit or internal operation; it does not treat every active account as available.
- Clean SQLite migration and runtime compatibility passed at `0106_operation_templates`.
- Ruff and MyPy passed across 132 files; all 219 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.

## Unreleased — Persisted shift template defaults — 2026-08-21

Status: implemented and verified; not included in immutable release 1.24.0.

- Added revision `0105_shift_pattern_defaults` to persist default Weeks 1–4, included weekdays, and the week-start weekday for every reusable shift template.
- Existing templates are safely backfilled to Weeks 1–4, Sunday–Friday, with Sunday as the week start.
- Creating or editing a template now saves its default weeks and days; **Use template** opens with those saved selections.
- Added visible template schedule chips plus in-system Edit and Delete dialogs.
- Template update and deletion remain permission controlled and audited; deleting a template does not remove previously generated shifts.
- Clean SQLite migration and runtime compatibility passed at `0105_shift_pattern_defaults`.
- Ruff and MyPy passed across 132 files; all 217 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.

## Unreleased — Monthly shift week alignment — 2026-08-21

Status: implemented and verified; not included in immutable release 1.24.0.

- Week 1 now begins on the first configured week-start weekday inside the selected month instead of the calendar week containing the first day.
- Weeks 2, 3, and 4 begin at seven-day intervals from that anchor; Sunday remains the default.
- Added a Week starts on selector to the template application dialog and limited generated month buckets to Weeks 1–4.
- Added regression evidence proving September 2026 Sunday buckets begin on September 6, 13, 20, and 27.
- Ruff, MyPy, six shift tests, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- No database migration was required; database head remains `0104_workflow_templates`.

## Unreleased — Shift Planning UX — 2026-08-20

Status: implemented and verified; not yet packaged.

- Split Shift Planning into Calendar, Templates, and Settings tabs and removed Visit Operations from the shift page.
- Added visual reusable-template cards, a focused creation dialog, searchable department-engineer selection, and an in-system monthly application workflow.
- Shift type and template codes are now generated automatically when omitted; existing API callers may still provide governed codes.
- Added preview-first bulk deletion for one engineer by month, optional shift type, and status, with protected completed shifts, stale-selection rejection, and a consolidated audit record.
- Replaced browser prompt/confirmation usage in Shift Planning with application dialogs and Snackbar results.
- Ruff and MyPy passed across 132 source files; all 216 backend tests passed. Frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- No database migration was required; database head remains `0104_workflow_templates`.

## 1.24.0 — 2026-08-20

Status: self-contained Windows x64 release generated and verified.

- Packages the completed Shift Planning UX scope recorded above.
- Database compatibility remains `0104_workflow_templates`; no migration is required from 1.23.0.
- Pre-package verification: Ruff and MyPy passed across 132 source files; all 216 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Standalone runtime smoke check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Package inspection confirmed version `1.24.0`, database head `0104_workflow_templates`, self-contained deployment, and no `.env` or database files.
- Artifact: `releases/SupportHub-1.24.0.zip` (43,294,971 bytes).
- SHA-256: `FBFCA63BF6D3C244CE9B27247B686B17A26BFF099802007C70DF15776621E455`.

## Working rules

1. Add an `Unreleased` entry before starting a feature. State the goal and files expected to change.
2. After each meaningful change, record the completed behavior, migrations, and verification performed.
3. Never overwrite a release directory or ZIP. Increment the semantic version and generate a new immutable artifact.
4. Before packaging, create `docs/RELEASE-<version>.md`, move the relevant work into a versioned section below, and synchronize application version metadata.
5. The release builder rejects missing notes, missing log entries, lint/type/test failures, and frontend warnings.
6. Store protected production secrets outside the source tree. Never copy development `.env` files or databases into a release.

## Unreleased — Unified master plan Wave 0 — 2026-08-20

Status: done; Wave 0 governance and architecture baseline approved.

- Started Wave 0 of the unified development master plan.
- Added `docs/Completed/Plans/WAVE_0_FOUNDATION_BASELINE.md` with the current architecture/data-ownership inventory, canonical KPI formula draft, proposed visit-entitlement policy, and a 14-item decision register.
- Confirmed the existing database has one Alembic head, `0092_client_profile`; no migration or application code was added.
- Project Owner explicitly approved the recommended D-001 through D-014 defaults on 2026-08-20 by directing completion of Wave 0.
- Added initial management targets, RAG thresholds, minimum-evidence rules, and an approved control that prevents individual composite engineer scores until a later versioned fairness/visibility policy is approved.
- Wave 0 is complete. Wave 1 remains untouched and requires a separate explicit continuation instruction.
- Verification: documentation inspection and `alembic heads` passed. Application test suites were not required because runtime code and schema were unchanged.

## Unreleased — Unified master plan Wave 1 — 2026-08-20

Status: done; implementation and SQLite/SQL Server gates passed.

- Added client hierarchy revision `0093_client_hierarchy`, the centralized traversal/validation service, hierarchy APIs, cycle/missing-parent/delete protection, old/new path audits, and backward-compatible root defaults.
- Added optional parent selection to client creation/editing plus breadcrumb/tree navigation and direct/total descendant counts.
- Reused and regression-tested the existing department master foundation from revision `0091`; no duplicate department schema was added.
- Routed the legacy SLA target helper through the canonical specificity resolver, fixing priority fallback when another service has an override.
- Updated production compatibility guards to require `0093_client_hierarchy` and `clients.parent_client_id`.
- Clean and populated SQLite migration rehearsals reached `0093`; temporary rehearsal databases were removed.
- Verification: Ruff passed; mypy passed across 120 source files; 182 backend tests passed; frontend ESLint, 3 Vitest tests, TypeScript, and production build passed.
- SQL Server clean-install initially exposed non-portable `ON DELETE RESTRICT` syntax in the current ORM metadata. The self-reference now relies on restrictive default/`NO ACTION` behavior, while revision `0093` explicitly uses SQLite `RESTRICT` and SQL Server `NO ACTION`.
- SQL Server clean install, seed, and runtime compatibility passed at `0093_client_hierarchy`.
- A populated SQL Server `0092` baseline with one client upgraded to `0093`; the client was preserved as a root, and column/index/foreign-key assertions passed.
- The two explicitly named disposable SQL Server rehearsal databases were removed after verification; production databases were not touched.
- Targeted verification after the portability correction: Ruff passed, mypy passed, and 11 hierarchy/SLA/compatibility/revision tests passed. The earlier complete gates remain 182 backend tests and all frontend gates passed.
- Wave 1 is complete; Wave 2 has not started.
- Detailed handoff: `docs/Completed/Plans/WAVE_1_IMPLEMENTATION_STATUS.md`.

## Unreleased — Unified master plan Wave 2 — 2026-08-20

Status: done; hierarchy-aware portal flow, scalable contract selection, and shift masters verified.

- Added revision `0094_scope_shift` for explicit portal hierarchy modes, shift-type metadata, and department-specific shift patterns.
- Existing portal assignments remain exact-client through the `CLIENT_ONLY` default; direct-child and all-descendant modes expand only client scope, never exact branch scope.
- Removed the portal form's `client_ids[0]` behavior and added mandatory affected-client selection for multi-client users.
- Added governed shift-type and shift-pattern APIs with cross-midnight and uniqueness validation.
- Added a total-aware paginated customer search contract and server-side all-matching preview/apply semantics with explicit exclusions and auditable selection intent.
- Added permission-gated shift master administration, pattern updates, and audit coverage for shift type/pattern creation and changes.
- Clean SQLite and SQL Server installs reached `0094` and passed compatibility; disposable rehearsal databases were removed.
- Full verification: Ruff passed; Mypy passed across 120 source files; 184 backend tests passed; frontend ESLint, 3 Vitest tests, TypeScript, and production build passed.
- Populated SQLite upgrade from revision `0015` and populated SQL Server upgrade from seeded revision `0093` both reached `0094_scope_shift` and passed compatibility.
- All named disposable rehearsal databases were removed. Wave 2 is complete; Wave 2A has not started.
- Detailed handoff: `docs/Completed/Plans/WAVE_2_IMPLEMENTATION_STATUS.md`.

## Unreleased — Unified master plan Wave 2A — 2026-08-20

Status: done; durable portal/internal creation notifications and semantic navigation verified.

- Added normalized, audited portal ticket email configuration with disabled-by-default behavior.
- Portal ticket creation now records an idempotent asynchronous email event in the same transaction; the existing worker delivers it independently of ticket creation.
- Added a shared semantic link primitive for the application-wide browser-native navigation conversion.
- Added revision `0095_ticket_notify`, stable-ID internal notification rules, rule matching/versioning, coalesced recipients, and the optional user Support Notification Email.
- Added audited/versioned rule updates, portal/rule administration UI, User Setup notification-email editing, and unsaved-value test queueing without ticket creation.
- Added selected-engineer entry-only reassignment events, missing-address warning snapshots, and editable/versioned creation templates with per-event snapshots.
- Converted the main navigation, user hierarchy/create, and client edit/access destinations to semantic links; added an anchor/href test and remaining-link audit.
- Added semantic ticket, portal request, notification, and executive contract destinations.
- Full gates: Ruff, Mypy across 121 files, 188 backend tests, frontend ESLint, 4 Vitest tests, TypeScript, and production build passed.
- Populated SQLite and SQL Server upgrade rehearsals reached `0095_ticket_notify`, preserved fixture data, and passed runtime compatibility; disposable databases were removed.
- Wave 2A is complete; Wave 2B has not started.
- Ruff, Mypy across 121 source files, 35 affected tests, and a clean SQLite migration to `0095_ticket_notify` pass.
- Remaining work is recorded in `docs/Completed/Plans/WAVE_2A_IMPLEMENTATION_STATUS.md`; Wave 2B has not started.

## Unreleased — Roadmap release boundary — 2026-08-20

Status: ready for release generation; no artifact has been generated by this entry.

- Froze the implemented release scope after Wave 2A at database revision `0095_ticket_notify`.
- Created `docs/Completed/Plans/ROADMAP_RELEASE_STOP_POINT_2026-08-20.md` as the authoritative packaging handoff.
- Added execution plans for Waves 2B through 9; these files are planning documentation only and their features are explicitly excluded from this release.
- The next release must use a new immutable semantic version, rerun all builder gates against the packaging source, and record the resulting artifact and SHA-256 here.
- No runtime code or database schema changed while establishing this release boundary; documentation structure validation passed for all 16 remaining-wave files.

## Unreleased — Unified master plan Wave 2B — 2026-08-20

Status: done; categorized Site Settings implemented and verified.

- Added eight responsive, URL-addressable Site Settings categories under `/system?tab=<category>`.
- Added permission-protected category inventory and isolated, optimistic-concurrency updates for General settings.
- Preserved specialized notification, ticket-form, SMTP, storage, feature-policy, Outlook integration, system-status, and backup contracts.
- Added category-scoped audit evidence and stale-update rejection without requiring a database migration; schema remains `0095_ticket_notify`.
- Backend Ruff and Mypy passed; 190 backend tests passed.
- Frontend ESLint, 4 Vitest tests, TypeScript, and production build passed; the existing non-blocking vendor chunk advisory remains.
- Detailed checkpoint: `docs/Completed/Plans/WAVE_2B_SITE_SETTINGS_EXECUTION_PLAN.md`.
- Wave 2C is next; Waves 2C through 7C remain unimplemented.

## Unreleased — Unified master plan Wave 2C — 2026-08-20

Status: done; authorized ticket-number list search implemented and verified.

- Added a dedicated, trimmed, case-insensitive partial `ticket_number` filter to internal and portal ticket lists and the portal export.
- Full numbers, configured prefixes, and numeric portions match across the authorized dataset before pagination/limits are applied.
- Added dedicated internal and portal fields with URL persistence, filter composition, clearing, pagination reset, and syntax guidance.
- Exact out-of-scope portal ticket-number searches return an indistinguishable empty result.
- No migration was required; database revision remains `0095_ticket_notify`.
- Backend Ruff and Mypy passed; 190 backend tests passed.
- Frontend ESLint, 4 Vitest tests, TypeScript, and production build passed; the existing non-blocking vendor chunk advisory remains.
- Detailed checkpoint: `docs/Completed/Plans/WAVE_2C_TICKET_NUMBER_SEARCH_EXECUTION_PLAN.md`.
- Wave 2D is next; Waves 2D through 7C remain unimplemented.

## Unreleased — Unified master plan Wave 2D — 2026-08-20

Status: done; effective-dated organizational hierarchy implemented and verified.

- Added revision `0096_org_hierarchy` with department parent/head mirrors plus append-only hierarchy, primary membership, and reporting-line history.
- Added centralized bounded as-of traversal, descendant, cycle, missing-parent, overlap, vacancy, membership, and reporting validation.
- Added governed and audited hierarchy/history APIs; existing user creation/editing writes the same canonical history.
- Added parent/head/effective-date department management, Department Structure as-of views, vacancy display, and User Setup organization history.
- Clean and populated SQLite and SQL Server rehearsals reached `0096`, preserved/backfilled fixture records, and passed runtime compatibility.
- Both named disposable SQL Server rehearsal databases and both workspace SQLite rehearsal databases were removed.
- Ruff passed; Mypy passed across 122 files; 192 backend tests passed.
- Frontend ESLint, 4 Vitest tests, TypeScript, and production build passed; the existing non-blocking vendor chunk advisory remains.
- Detailed checkpoint: `docs/Completed/Plans/WAVE_2D_ORGANIZATION_HIERARCHY_EXECUTION_PLAN.md`.
- Wave 3 is next; Waves 3 through 7C remain unimplemented.

## 1.20.8 — 2026-08-16

Status: ready; standalone release generated and independently validated.

- Goal: streamline dashboard navigation and filters, add Top Management as a user-selectable login destination, paginate and search the customer portfolio, and make repeated-issue investigation scalable and client-aware.
- Added `Top management profile` to the validated profile-preference default pages and login routing for authorized executive-dashboard users.
- Customer Success Portfolio now shows 20 rows per page with Previous/Next controls, client-name search, and a bounded scrollable Show All mode.
- Online Engineers and Service Health now appear in Overview.
- Consolidated the main dashboard from six tabs into Overview and Performance & Detailed Analysis without removing the existing operational, team, product/client, SLA, or detailed-report content.
- Top Repeated Issues now appears once in Overview as a grid with rank, issue, count, action, ten-row paging, and scrollable Show All mode; ticket drilldowns preserve the selected client filter.
- Main Dashboard, Top Management Dashboard, and Tickets filters are collapsible.
- Targeted verification before packaging: frontend TypeScript and Vite production build passed; 3 Vitest tests passed; 13 backend phase/profile-preference tests passed.
- Database revision remains `0092_client_profile`; no migration is required.
- Release gates: Ruff passed; mypy passed across 119 source files; 178 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.8`; deployment mode is self-contained Windows x64 and does not require a Python installation.
- Artifact inspection found no `.env`, SQLite, or database files in the package.
- Artifact: `releases/SupportHub-1.20.8.zip` (42,634,944 bytes).
- SHA-256: `9804594E750096AED1878233E061959D26E80255F372F20DC57029C63B36ED9D`.

## 1.23.0 — 2026-08-20

Status: self-contained Windows x64 release generated and verified.

- Added reusable shift-pattern application by month/week/day with multiple department engineers and configurable hours.
- Added bulk ad-hoc and internal-operation visits, exact-client allowance validation, optional ticket/operation links, and quarter/normal visit workspaces with period/client filters and entitlement cards.
- Outdoor client operations now create linked visit occurrences; governed completion consumes the exact client allowance once.
- Root causes now control whether resolution outcome and permanent-fix evidence are required; resolved tickets create linked internal knowledge drafts automatically.
- Added automatic `INV-YYYY-000001` invoice numbering with authorized overrides, multi-currency/EGP support, visible payments, receipt allocation, and received/unallocated cards.
- Database compatibility revision advances to `0104_workflow_templates`.
- Verification before packaging: Ruff passed; MyPy passed across 132 source files; 214 backend tests passed; frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite installation and runtime compatibility passed at `0104_workflow_templates`.
- Standalone runtime smoke check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Package inspection confirmed version `1.23.0`, the required migration head, self-contained deployment, and no `.env` or database files.
- Artifact: `releases/SupportHub-1.23.0.zip` (43,280,753 bytes).
- SHA-256: `88F41437043883520F0DEF6028D7A322BB49A641A939E503CD456511E27936D8`.

## Recovery after an interrupted editor or machine session

1. Do not generate a release immediately.
2. Read the newest entry in this file and inspect the files and migrations it names.
3. Run `backend\.venv\Scripts\python.exe -m alembic heads` and confirm exactly one head.
4. From `backend`, run Ruff, mypy, and pytest.
5. From `frontend`, run ESLint, Vitest, TypeScript, and Vite using the local Node executables. The project path contains `&`, so direct local executables are safer than npm's Windows command wrapper.
6. Verify `APP_VERSION`, `backend/pyproject.toml`, `frontend/package.json`, release notes, and the requested release version agree.
7. Generate the package only after every gate passes, then inspect the manifest and packaged `web.config`.

## Unreleased — Contract commercial lifecycle plan — 2026-08-15

Status: planning documentation completed; no application, database, version, or release artifact changed.

- Added `docs/CONTRACT_RENEWAL_FINANCE_DEVELOPMENT_PLAN.md` as the durable implementation specification for repeat and partial renewals, safe service removal, governed dynamic SLA versions, optional contract finance, payment schedules, chargeable tickets, permissions, contract-workspace UX, dashboards, reports, client profiles, and exports.
- Defined financial reporting semantics so contracted, billable, invoiced, collected, outstanding, and overdue amounts cannot be confused; only collected client-attributed payments are income.
- Recorded phased delivery, minimum acceptance criteria, historical-data protections, shared-contract allocation requirements, and product decisions required before database implementation.
- Documentation-only change; no tests or release package are required. The latest deployable release remains `1.20.4`.

## 1.20.7 — 2026-08-15

Status: ready; standalone release generated and independently validated.

- Goal: make dashboard clicks open clear calculation evidence, remove the response/resolution distribution charts, repair empty created-versus-resolved trends, count active incidents across every priority, and prevent no-data clients from appearing 100% healthy.
- Services provided will show a distinct service/operation-type delivery summary; business hours saved will show the contributing SLA rows; total working hours will show ticket and internal-operation sources.
- Every revised card, trend, and evidence view must preserve the selected client/period and reconcile to its displayed total.
- Expected changes: management analytics, client-profile report data, dashboard/profile frontend views, tests, release notes, version metadata, and this recovery log.
- Removed the Response time distribution and Resolution time distribution widgets; sample size is now shown directly in each governed average card.
- Created-versus-resolved trend now selects daily buckets up to 45 days, weekly buckets up to 180 days, and monthly buckets for longer periods. Resolutions are counted by resolution date even when creation occurred earlier; visible points and a clear no-activity state prevent blank charts.
- Replaced P1-only critical counting with active `INCIDENT` ticket-type counting across every priority and exact incident evidence.
- Clients without ticket activity in the selected period now show `INSUFFICIENT DATA`, no numeric health score, unavailable resolution, and are excluded from average health.
- Added exact-record evidence dialogs for management response, resolution, incidents, and trend widgets.
- Added a dedicated client evidence page and reconciled tables for distinct services provided, signed SLA business hours saved, and combined ticket/operation working hours.
- Services provided now counts distinct resolved ticket services and completed internal-operation types rather than treating every ticket as a separate service.
- Targeted verification: Ruff and mypy passed; 7 management/client-profile regression tests passed; frontend ESLint passed with zero warnings and TypeScript passed.
- Database revision remains `0092_client_profile`; no migration is required.
- The first release-gate attempt stopped safely before packaging when the clean production TypeScript build found an `unknown` evidence-link rendering type. The source was corrected to an explicit boolean render condition; no partial release directory or ZIP existed, and clean TypeScript/Vite validation passed before rebuilding.
- Release gates: Ruff passed; mypy passed across 119 source files; 178 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, clean TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.7`; deployment mode is self-contained Windows x64 and does not require a Python installation.
- Artifact: `releases/SupportHub-1.20.7.zip` (42,632,958 bytes).
- SHA-256: `4A1EE0427D3DEC9427DFF469DFC56DE096A281165AF0F54198EBC62C9D3D7509`.

## 1.20.5 — 2026-08-15

Status: ready; standalone release generated and independently validated.

- Goal: replace the eight-section Top Management dashboard with two focused tabs: `Executive Overview` and `Customer Service Success`.
- Preserve the shared filters, presentation mode, export, clickable source drilldowns, client-name filter, and direct client-profile navigation.
- Add an explainable client-health portfolio using available SLA, satisfaction, resolution, critical-ticket, reopen, and contract-renewal-risk evidence. Missing SLA or satisfaction evidence must be unavailable and excluded from weighting, never silently scored as zero.
- Expected changes: management analytics API and tests, Top Management frontend, version metadata, release notes, and this recovery log.
- Implemented the two server-backed dashboard tabs and removed the obsolete eight-tab navigation.
- Executive Overview now concentrates tickets, resolutions, SLA, open P1 incidents, response/resolution time, active clients/contracts, expirations, trends, status, priority, product demand, SLA breaches, root causes, engineer workload, and countries supported.
- Customer Service Success now provides health, SLA, satisfaction, critical-ticket KPIs, a health distribution, a searchable client selector, and a risk-sorted portfolio with direct client-profile navigation.
- Client health is calculated from available SLA, satisfaction, resolution, open P1, reopen, and contract-expiry evidence; missing SLA and satisfaction evidence is displayed as unavailable and excluded from weighting.
- Targeted verification: Ruff passed, mypy passed, 4 management dashboard tests passed, frontend ESLint passed with zero warnings, and frontend TypeScript passed.
- Database revision remains `0092_client_profile`; no migration is required.
- Release gates: Ruff passed; mypy passed across 119 source files; 177 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.5`; deployment mode is self-contained Windows x64 and does not require a Python installation.
- Artifact: `releases/SupportHub-1.20.5.zip` (42,609,349 bytes).
- SHA-256: `381D334C8C72E6BFA5B400C87AC0F89BF72F48536FF96472B6417AE666F450C6`.

## 1.20.6 — 2026-08-15

Status: ready; standalone release generated and independently validated.

- Goal: replace inflated raw calendar-hour response and resolution averages with governed SLA business-time measures.
- Average response will use completed First Response SLA clocks and the applicable business calendar. Average resolution will use completed accountable Resolution SLA evidence, including customer-pending and escalation policy rules.
- Add median, P90, and included-ticket sample sizes with ticket drilldowns so management can understand skew and calculation coverage.
- Correct completed resolution evidence to stop at the persisted SLA-clock completion time when a closed timestamp is unavailable.
- Expected changes: SLA calculation service, management analytics API/tests, Top Management frontend rendering if required, release notes, version metadata, and this recovery log.
- Implemented average First Response business hours from completed First Response SLA clocks and their persisted calendar/policy evidence.
- Implemented average accountable Resolution hours from completed Resolution SLA evidence, respecting business schedules, holidays, customer-pending time, and policy-controlled escalation time.
- Added median, nearest-rank P90, and included-ticket counts for both distributions; all widgets retain ticket-list drilldowns.
- Corrected resolution evidence to use the persisted SLA clock completion time before a report `as_of` time when a closed timestamp is absent, preventing completed tickets from continuing to accumulate hours.
- Targeted verification: Ruff and mypy passed; 14 management/SLA lifecycle tests passed, including outlier distribution and persisted-completion regression coverage.
- Database revision remains `0092_client_profile`; no migration is required.
- Release gates: Ruff passed; mypy passed across 119 source files; 178 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.6`; deployment mode is self-contained Windows x64 and does not require a Python installation.
- Artifact: `releases/SupportHub-1.20.6.zip` (42,615,342 bytes).
- SHA-256: `C867197A1B2D02FB8772D817ACB4263B4809049471B007C8217579F554F41A03`.

## 1.20.4 — 2026-08-14

Status: ready; standalone hotfix generated and independently validated.

- Goal: add a clearly visible client-name filter directly inside the Top Management Client Profiles tab and generate hotfix `1.20.4`.
- Added a dedicated `Client name` selector directly below the Client Profiles tab, with `All client profiles` and every active client as choices.
- The selector reuses the server-side `client_id` analytics filter, clears incompatible location selection through the existing filter handler, and leaves each filtered client card clickable to the full profile.
- Pre-release verification: 4 management dashboard tests passed; frontend ESLint and TypeScript passed.
- Release gates: Ruff passed; mypy passed across 119 source files; 177 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.4`; database revision remains `0092_client_profile`, so no new migration is required from `1.20.3`.
- Release notes and `LOGIN-RECOVERY.md` are included in the package.
- Artifact: `releases/SupportHub-1.20.4.zip` (42,611,090 bytes).
- SHA-256: `1A0E4C054F4A023848716B314219307B6644DE18E86D747FC78BDEBFE32B7C0B`.

## 1.20.3 — 2026-08-14

Status: ready; standalone release generated and independently validated.

- Goal: add client profiles to Top Management, honor the existing Client filter, and open the advanced client profile by clicking the client name/card.
- Added a dedicated `Client Profiles` Top Management tab containing one clickable card per active client, sorted by client name and showing the selected-period ticket count.
- Each client card drills directly to `/clients/{client_id}/profile`; the existing Client dashboard filter reduces the tab to the selected client.
- The profile drilldown carries the selected dashboard reporting dates, while the dashboard remains read-only under `dashboard.executive` and `report.view` permissions.
- Added a regression test that creates an isolated active client, filters Top Management by it, and verifies exactly one profile card with the correct client name and profile route.
- Verification: Ruff passed across `app`; mypy passed across 119 source files; 6 management/client-profile tests passed; frontend ESLint and TypeScript passed; 3 Vitest tests and production Vite build passed. Vite retains its non-blocking vendor chunk advisory.
- Changed files: `backend/app/modules/dashboards/management.py`, `backend/app/tests/test_management_dashboards.py`, `frontend/src/pages/ManagementDashboardsPage.tsx`, and this recovery log.
- Release gates: Ruff passed; mypy passed across 119 source files; 177 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.3`; database revision remains `0092_client_profile`, so no new migration is required from `1.20.2`.
- Release notes and `LOGIN-RECOVERY.md` are included in the package.
- Artifact: `releases/SupportHub-1.20.3.zip` (42,611,588 bytes).
- SHA-256: `BB2DE0D442EB4D04E54057A6F6D3AE9C13EAB76B513936FBB10F1E968B064475`.

## 1.20.2 — 2026-08-14

Status: ready; standalone release generated and independently validated.

- Goal: calculate Total working hours from both ticket SLA-accountable business time and completed client-operation engineer-hours, with separate drilldowns to both evidence sources.
- Total working hours now equals `ticket_working_hours + operation_working_hours`.
- Ticket working hours use the existing auditable SLA `spent_business_hours` value: accountable business minutes for completed tickets, excluding customer-pending time according to SLA rules.
- Operation working hours remain completed operation duration multiplied by assigned engineer count.
- The API exposes both component values and separate ticket/operation evidence URLs; the total KPI opens the completed-ticket evidence, while Client engagement and the operation source open the completed client operations.
- The matching Word report now lists Ticket spent business hours, Operation engineer-hours, and Combined working hours in its supporting evidence.
- Verification: Ruff passed across `app`; mypy passed across 119 source files; 2 client-profile tests passed; frontend ESLint and TypeScript passed.
- Follow-up completed: Management Dashboard `Countries supported` now derives exclusively from structured countries linked directly to active clients or through their active locations.
- Each country value is the number of unique linked clients, not ticket volume. This keeps supported countries visible even when they have no tickets in the selected period and excludes unrelated country-master entries.
- Country, client, zone, and location dashboard filters are honored; map labels/tooltips now explicitly describe linked-client counts.
- Added a regression test proving a linked zero-ticket country appears with one client while an unlinked country is absent.
- Geography verification: Ruff passed across `app`; mypy passed across 119 source files; 5 management/client-profile tests passed; frontend ESLint and TypeScript passed.
- Additional changed files: `backend/app/modules/dashboards/management.py`, `backend/app/tests/test_management_dashboards.py`, and `frontend/src/pages/ManagementDashboardsPage.tsx`.
- Release gates: Ruff passed; mypy passed across 119 source files; 176 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.2`; database revision remains `0092_client_profile`, so no new migration is required from `1.20.1`.
- Release notes and `LOGIN-RECOVERY.md` are included in the package.
- Artifact: `releases/SupportHub-1.20.2.zip` (42,608,443 bytes).
- SHA-256: `AAA016F7ECC2E7AEB3F99904E06062D7C0BF9B073A9F47680AD0FEBC90DD0C0F`.

## 1.20.1 — 2026-08-14

Status: ready; standalone release generated and independently validated.

- Goal: make the client-profile Word export follow the same visual order, colors, KPI cards, chart panels, impact cards, and critical-ticket details as the interactive system page.
- Rebuilt the Word layout in landscape format with the matching navy client banner and reporting period, six KPI cards, ticket-volume trend, priority/status/product/module/service panels, two-column business-impact cards, critical-ticket details, and supporting client/contract/calculation evidence.
- Preserved Word-friendly static chart representations and the same Millensys blue, teal, severity, muted-text, border, header, and footer styling. Web-only interactions and responsive animations remain UI behavior and cannot execute inside a DOCX.
- Added DOCX structure assertions that open the generated file and verify its orientation and every matching visual section.
- Verification: Ruff passed across `app`; mypy passed across 119 source files; 4 client-profile and release-revision tests passed. Only existing third-party deprecation warnings remain.
- Changed files: `backend/app/modules/reports/client_profile.py`, `backend/app/tests/test_client_profile_report.py`, and this recovery log.
- Follow-up completed: `Services provided` now counts completed ticket resolutions/closures plus completed client-linked operations instead of only operations, preventing an incorrect zero when service was delivered through tickets.
- Added `Total working hours`, calculated as the scheduled duration of each completed client operation multiplied by its assigned engineer count. This is recorded work evidence and does not estimate unrecorded ticket labor.
- Added server-provided, period- and client-scoped drilldown links for every KPI, the ticket trend, every priority/status/product/module/service chart item, and every business-impact card. Critical-ticket rows and the client banner remain direct navigation targets.
- Added `client_id` filtering to Internal Operations and made its status/date filters honor drilldown query parameters, so working-hour evidence opens on the exact completed client records.
- Updated the matching Word report with the Total working hours KPI card.
- Follow-up verification: Ruff passed across `app`; mypy passed across 119 source files; client-profile tests passed with a completed two-hour operation proving `Services provided = 1`, `Total working hours = 2`, and exact source filtering; frontend ESLint and TypeScript passed; 3 Vitest tests and production Vite build passed. Vite retains its non-blocking large vendor chunk advisory.
- Additional changed files: `backend/app/modules/internal_operations/routes.py` and `frontend/src/pages/InternalOperationsPage.tsx`.
- Release gates: Ruff passed; mypy passed across 119 source files; 175 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports only its existing non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration report version `1.20.1`; database revision remains `0092_client_profile`, so no new migration is required from `1.20.0`.
- Release notes and `LOGIN-RECOVERY.md` are included in the package.
- Artifact: `releases/SupportHub-1.20.1.zip` (42,601,193 bytes).
- SHA-256: `100987E046FF5BE67A50CC199870D7A6B55CF1BF8F2024703234F6D6089ECA5A`.

## 1.20.0 — 2026-08-14

Status: ready; standalone release generated and independently validated.

- Client country, city, and primary location are now optional during creation and editing.
- Client creation only creates a primary location when both a country and city are selected.
- The client import template now supports optional support-start date, country, city, primary-location, zone, and coordinate columns. Blank geography is accepted; supplied references and coordinates are validated.
- Added a dedicated interactive client profile system page with KPI cards, clickable donut/bar charts, ticket-volume trends, business-impact panels, critical-ticket navigation, period filters, and Word/Excel actions.
- Extended the profile API with daily created/resolved trend data and ticket identifiers for safe drilldown navigation.
- Enhanced the branded Word export with matching status, priority, product, module, service, and daily trend visualizations plus the existing detailed evidence sections.
- Added a governed `MASTER_DATA` import covering countries, cities, departments, products/modules, services, vendors, client/ticket statuses, ticket types, environments, ticket categories/subcategories, root causes, skills, and support teams.
- Enhanced the Data Migration page with a dedicated Master Data catalog task and dependency guidance; contacts and installations have dedicated import workflows, so every Master Data tab dataset is covered.
- Release gates: Ruff passed; mypy passed across 119 source files; 175 backend tests passed; frontend ESLint passed with zero warnings; 3 Vitest tests, TypeScript, and the production Vite build passed.
- Vite reports a non-blocking large vendor chunk advisory.
- Standalone runtime smoke check passed and exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Package manifest and IIS configuration both report version `1.20.0`; database revision remains `0092_client_profile`, so no new migration is required from `1.19.2`.
- `LOGIN-RECOVERY.md` is included in the package.
- Artifact: `releases/SupportHub-1.20.0.zip` (42,583,244 bytes).
- SHA-256: `C5763B7894BC01FD54642DA49048054C5D26A1DBF10CBB82E9A0116BFCC922A8`.

## 1.19.2 — 2026-08-14

Status: ready; database compatibility hotfix generated and validated.

- Production health showed revision `0092_client_profile` but returned `MIGRATION_REQUIRED`.
- Root cause: `EXPECTED_DATABASE_REVISION` was stale at `0090_country_city_masters` even though the release manifest and database were correctly at `0092_client_profile`.
- Corrected the compatibility revision and added schema checks for client city/support date, user department, and department master data.
- Replaced the fragile hardcoded unit assertion with a comparison against Alembic's actual current head.
- No database migration is required for databases already at `0092_client_profile`.
- Ruff and mypy passed across 119 source files; 173 backend tests passed.
- Frontend ESLint, 3 Vitest tests, TypeScript, and production build passed.
- Artifact: `releases/SupportHub-1.19.2.zip` (42,546,097 bytes).
- SHA-256: `DB3CB585E1D5646BAFE88304ACA0277B41FA102B7A33CF2B5AFA39C3A7F8094D`.

## 1.19.1 — 2026-08-14

Status: ready; login recovery patch generated and validated.

- Root cause: generated releases correctly excluded production credentials, but a clean database had no safe packaged command to create an initial administrator; locked or forgotten administrator credentials also lacked a standalone recovery path.
- Added interactive `SupportHubBackend.exe recover-admin --login <name> [--email <address>]` without accepting passwords on the command line.
- The command creates a missing administrator or resets, activates, and unlocks an existing administrator, forcing a password change on next login.
- Added `docs/LOGIN_RECOVERY.md` and included it in release packages.
- Version metadata advanced to immutable patch release `1.19.1`; database head remains `0092_client_profile`.
- Ruff passed; mypy passed across 119 source files.
- Backend pytest: 173 passed; frontend ESLint, 3 Vitest tests, TypeScript, and production build passed.
- Standalone runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Artifact: `releases/SupportHub-1.19.1.zip` (42,545,165 bytes).
- SHA-256: `5DEFD61B94990D733149987050A54FCED85CFE550985613D12A36D460249FFE7`.

## 1.19.0 — 2026-08-14

Status: ready; self-contained release generated and validated.

Recovered and completed work:

- KPI and Top Management dashboard filtering, KPI review locking, geographic analytics, countries, cities, client locations, department masters, and client profile reporting.
- Confirmed the interrupted feature work exists through database revisions `0089_kpi_review_lock`, `0090_country_city_masters`, `0091_department_master`, and `0092_client_profile`.
- Corrected strict backend typing in notifications, IAM reporting hierarchy, satisfaction endpoints, configuration updates, dashboard analytics, and client profile reports.
- Added mandatory release gates and version/log validation to `scripts/Build-SupportHubRelease.ps1`.
- Synchronized backend, frontend, environment example, and IIS application versions to `1.19.0`.

Verification record:

- Ruff: passed.
- mypy: passed, 118 source files.
- Backend pytest: 171 passed (2 third-party deprecation warnings).
- Frontend ESLint: passed with zero warnings.
- Frontend Vitest: 3 passed.
- Frontend TypeScript and production Vite build: passed. Vite reports a non-blocking large vendor chunk advisory.
- Clean database migration: passed from an empty SQLite database through the single head `0092_client_profile`.
- Standalone runtime smoke check: `SupportHubBackend.exe --help` passed and exposed `serve`, `migrate`, and `seed`.
- Package manifest: version `1.19.0`, database revision `0092_client_profile`, self-contained Windows x64.
- Packaged IIS configuration: `APP_VERSION=1.19.0` and runtime executable path confirmed.
- Artifact: `releases/SupportHub-1.19.0.zip` (42,532,496 bytes).
- SHA-256: `BCC4016858D1ED413F6011B8E20BDF1B9D383CDC5398C20A291AF750C2AD1B04`.

Known superseded artifact:

- `1.18.0` must not be deployed. Its manifest reports `0088_shift_handovers` and its packaged backend reports application version `1.16.1`, while current source requires `0092_client_profile`.
## Wave 3 checkpoint — 2026-08-20

Status: implementation checkpoint ready; database head `0097_service_governance`.

- Added published immutable SLA policy/target versions and ticket clock policy/context snapshots.
- Added governed ticket/task worklogs with overlap validation, owner workflow, manager decisions, concurrency checks, and audit evidence.
- Added feedback source/eligibility controls with the approved 10-request minimum and no individual composite engineer scoring.
- Added controlled resolution outcomes and permanent-fix status/evidence in the API and ticket UI.
- Ruff, MyPy (122 source files), the full backend test suite, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0097_service_governance`.
- Next wave: Wave 3A — Ticket Exception Approvals and Manager Finance.
## Wave 3A checkpoint — 2026-08-20

Status: implementation checkpoint ready; database head `0098_exception_finance`.

- Added exact-operation, single-use exception approval controls with revocation, expiry, separation of duties, notifications, and append-only evidence.
- Added fixed-precision commercial decisions and manager ledger facts with idempotency, confirmed-collection controls, per-currency totals, and ticket drill-through.
- Added the permission-aware Manager Finance UI and operating runbook.
- Ruff, MyPy (126 source files), the full backend suite, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0098_exception_finance`.
- Next wave: Wave 3B — Effective-Dated Coverage and Renewal Lifecycle.

## Wave 3B checkpoint — 2026-08-20

Status: implementation checkpoint ready; database head `0099_coverage_renewals`.

- Added effective-dated coverage revisions, retirement evidence, historical eligibility explanations, and contract-date guards.
- Added idempotent renewal opportunities, per-line full/partial/lost outcomes, owner tasks and notifications, validated successor links, and SLA continuity.
- Added manager-facing renewal controls and the coverage/renewal operating runbook.
- Ruff, MyPy (126 source files), 202 backend tests, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0099_coverage_renewals`.
- Next wave: Wave 3C — Optional Contract Finance.

## Wave 3C checkpoint — 2026-08-20

Status: implementation checkpoint ready; database head `0100_contract_finance`.

- Added optional fixed-precision contract finance profiles, schedules, invoice/credit evidence, receipt/reversal evidence, and explicit allocations.
- Added idempotent posting, currency and balance controls, collected-income reconciliation, audit evidence, authorized ledgers, and a contract Financials tab.
- Ruff, MyPy (126 source files), 205 backend tests, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0100_contract_finance`.
- Next wave: Wave 4 — Visit Entitlement Ledger and Occurrence Generation.

## Wave 4 checkpoint — 2026-08-20

Status: implementation checkpoint ready; database head `0101_visit_entitlements`.

- Added exact-client contractual visit entitlements, append-only quantity evidence, deterministic idempotent occurrence generation, exception queue, completion consumption, and compensating reopen.
- Added permission-controlled APIs and contract workspace summaries without treating hierarchy as a shared allowance pool.
- Ruff, MyPy (130 source files), 208 backend tests, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0101_visit_entitlements`.
- Next wave: Wave 5 — Weekly Shift Planner and Visit Planner.

## Wave 5 checkpoint — 2026-08-20

Status: implementation checkpoint ready; database head `0102_visit_planner`.

- Added stable visit assignments with explicit timezone, optimistic concurrency, shift/leave/visit/window/department conflict detection, and controlled override evidence.
- Added unassigned queues, workload reconciliation, deduplicated assignee notifications, and a responsive keyboard-accessible visit planner integrated with the shift calendar.
- Ruff, MyPy (130 source files), 209 backend tests, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0102_visit_planner`.
- Next wave: Wave 6 — Bulk Coverage, Imports, and Visit Completion/Documents.

## Wave 6 checkpoint — 2026-08-20

Status: implementation checkpoint ready; database head `0103_visit_completion`.

- Added effective-dated exact-client coverage imports with inclusions/exclusions, preview validation, attributable error export, and safe idempotent application.
- Added governed visit start/complete/cancel/reopen transitions, actual times, structured outcome and acknowledgement evidence, immutable completion snapshots, and exactly-once entitlement posting.
- Added secured visit-document upload/download with size, name, MIME/signature, hash, scan, retention, supersession, authorization, and audit controls.
- Ruff, MyPy (131 source files), 209 backend tests, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0103_visit_completion`.
- Next wave: Wave 7 — Client, Department, Shift, and Visit Reports.

## Wave 7 through 7C checkpoint — 2026-08-20

Status: release checkpoint ready; database head remains `0103_visit_completion`.

- Added canonical client, entitlement, department, shift, visit, and exception operational reports with live metric definitions and matching CSV exports.
- Added dashboard inventory `WAVE7A-1.0`, canonical ownership, compatibility routing, and filter/evidence contracts.
- Added effective-dated department structure, deduplicated headcount, vacancies, and scope-restricted evidence.
- Added `TICKETS-WORKED-1.0`, historical department attribution, deterministic distinct-ticket evidence, sample disclosure, and no individual leaderboard.
- Ruff, MyPy (132 source files), 211 backend tests, frontend ESLint, four Vitest tests, TypeScript, and production build passed.
- Clean SQLite/SQL Server and populated SQL Server migrations passed through revision `0103_visit_completion`.
- Next wave: Wave 8 — Engineer Scorecards, RAG Trends, and Renewal Intelligence.

## 1.21.0 — 2026-08-20

Status: release generated from the completed Wave 7C checkpoint.

- Includes roadmap Waves 3 through 7C, with the Wave 7 operational reporting, dashboard evidence, organization structure, and department achievement release scope.
- Database compatibility revision: `0103_visit_completion`.
- Deployment remains self-contained Windows x64 under IIS with `/SupportHub/` and `/SupportHub/backend` defaults.
- Standalone runtime smoke check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Artifact: `releases/SupportHub-1.21.0.zip` (43,215,824 bytes).
- SHA-256: `8DE29B32F72903E2B8277CD0E30A69F42B218B2C3C83DD266CD0A4E4AA4CF201`.

Superseded: do not deploy `1.21.0` when `DATABASE_URL` uses `mssql+pyodbc`. Its populated `0097` migration can retain an open result cursor on connections without MARS.

## 1.21.1 — 2026-08-20

Status: corrected release candidate.

- Buffers and closes the `0097` SLA policy/target and `0099` coverage backfill cursors before nested SQL commands, supporting SQL Server `pyodbc` connections without MARS.
- Makes the `0097` baseline inserts safe to retry after an interrupted migration.
- Retains the Wave 7C scope and database head `0103_visit_completion`.
- All 211 backend tests and frontend lint/test/type/build gates passed; a clean SQL Server upgrade through `0103` passed after the correction.
- Standalone runtime smoke check passed.
- Artifact: `releases/SupportHub-1.21.1.zip` (43,215,875 bytes).
- SHA-256: `90508219D68C9E1D6D86F431966EAC5D62B02278A54D871D3A445C680116CA0B`.

## 1.22.0 — 2026-08-20

Status: self-contained Windows x64 release generated and verified.

- Adds human-readable engineer/customer references, discoverable Visit Operations and Operational Reports pages, Manager Finance currency cards and ticket lookup, and Department Achievement cards.
- Adds 20-row server-side pagination to Clients and reliable linked-customer code/name filtering in the contract workspace.
- Retains database compatibility revision `0103_visit_completion`; no new migration is required from `1.21.1`.
- Backend Ruff, MyPy, and all 211 tests passed; frontend ESLint, Vitest, TypeScript, and production build gates passed.
- Standalone runtime smoke check passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Artifact: `releases/SupportHub-1.22.0.zip` (43,225,098 bytes).
- SHA-256: `C5E22E54046ABF2CCE0A2C4A4F3552C4A14C29894558A97D6DD1F6770D0DBEB1`.
## 1.38.0 — 2026-08-25

Status: ready; self-contained Windows x64 release generated and verified.

- Adds the unified Overview, Planner, Workload, and Setup scheduling workspace.
- Adds participation, Shift Type eligibility, coverage/headcount, Auto Balance, cyclic Rotations, Schedule Recipes, Paint Mode, enhanced Copy Week, and stale-safe Preview/Apply generation.
- Adds recurring Operation generation and exact-client Outdoor Visit entitlement preview.
- Database compatibility revision: `0129_operation_generation`; migrations `0126` through `0129` are additive and preserve existing schedules.
- Backend Ruff and MyPy passed; all 277 backend tests passed.
- Frontend ESLint, 11 Vitest tests, TypeScript, and production build passed.
- Clean SQLite migration through `0129_operation_generation` passed.
- Packaged manifest reports version `1.38.0`, database head `0129_operation_generation`, and no Python installation requirement.
- Packaged IIS configuration uses `SupportHubBackend.exe`, `APP_VERSION=1.38.0`, and `/SupportHub/backend`.
- Standalone runtime smoke test passed and exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Artifact: `releases/SupportHub-1.38.0.zip` (42,228,210 bytes).
- SHA-256: `57A88608CAF4C43395D6D1FACDE444D6B138D007F730318C227BC63599EBDF05`.
# B-40 implementation checkpoint (2026-08-27)

- Compact Contract Workspace customer previews open a searchable, server-paginated linked-customer dialog.
- Project Delivery uses six dedicated supporting permissions and minimum-data `/project-handovers` APIs without Clients, Contracts, or Operations workspace access.
- Migration `0143_project_delivery` replaces legacy broad permissions on the Project Handover profile; credential reveal remains excluded.
- Verification passed: Ruff, strict MyPy, frontend ESLint, TypeScript, production build, corrected compatibility tests, and a clean migration through `0143_project_delivery`. The full backend run passed 304 tests and exposed only the stale revision assertion, which was then corrected.

## 1.55.1 — 2026-09-01

Status: corrective self-contained Windows x64 release generated and verified.

- Corrects assignment of `project_handover.edit_pending` to Project Handover and Administrator profiles through migration `0162_handover_edit_permission`.
- Improves responsive widths for product, module, service, delivery, and pending-point controls in Project Handover and for product/module controls in Client Portal ticket creation.
- Replaces raw Project Handover translation keys and the technical edit-permission code with user-friendly English and Arabic labels.
- Database compatibility revision: `0162_handover_edit_permission`.
- Backend Ruff and strict MyPy passed; all 332 backend tests passed.
- Frontend ESLint, all 47 Vitest tests, TypeScript compilation, and production build passed.
- The packaged standalone executable exposed `serve`, `migrate`, `seed`, and `recover-admin`; a clean packaged migration passed through revision `0162_handover_edit_permission`.
- Artifact: `releases/SupportHub-1.55.1.zip` (42,845,497 bytes; 1,747 entries).
- SHA-256: `FE44A19AE920EFE6D39A7220856481154CFB196A626E064AC71F03F99F5F356A`.

## 1.56.0 — 2026-09-02

Status: ready; self-contained Windows x64 release generated and verified.

- Adds governed quarterly KPI submission, bulk containers, notifications, HR acknowledgement, controlled reopen, history, comparisons, and exports.
- Adds configurable Cairo-time cutoff policy and documented permission-controlled late overrides.
- Consolidates legacy profile dashboard queries in Dashboard Administration with collapsed-by-default panels.
- Corrects Top Management profile landing synchronization and adds per-tab Top Management widget visibility customization.
- Database compatibility revision: `0165_kpi_submission_batches`.
- Backend Ruff and strict MyPy passed; all 335 backend tests passed.
- Frontend ESLint, all 47 Vitest tests, TypeScript compilation, and production build passed.
- The packaged standalone executable exposed `serve`, `migrate`, `seed`, and `recover-admin`; clean packaged migration and seed passed through `0165_kpi_submission_batches`.
- Artifact: `releases/SupportHub-1.56.0.zip` (42,885,782 bytes; 1,750 entries before final documentation refresh).
- Initial packaged SHA-256 before final documentation refresh: `FBB781D7D038BB61B98653F61F14AA6C1E86A1CDA0A5B23B5CE1A8E8A654E270`.
- Final artifact after documentation refresh: `releases/SupportHub-1.56.0.zip` (42,885,884 bytes; 1,750 entries).
- Final SHA-256: `44E6FA6908D7EEB2BBDEAFE9FD4F51B57F0205381E2196AE10DEDFA94DA182E6`.

## 1.56.1 — 2026-09-02

Status: ready; corrective self-contained Windows x64 release generated and verified.

- Integrates effective Dashboard Administration assignments into Top Management rendering and widget customization.
- Adds Draft KPI reopening/editing and audited deletion of never-submitted Drafts while protecting submission history.
- Database compatibility revision remains `0165_kpi_submission_batches`; no new migration is required from `1.56.0`.
- Backend Ruff and strict MyPy passed; all 336 backend tests passed.
- Frontend ESLint, all 47 Vitest tests, TypeScript compilation, and production build passed.
- The packaged standalone executable exposed `serve`, `migrate`, `seed`, and `recover-admin`; clean packaged migration and seed passed through `0165_kpi_submission_batches`.
- Artifact before final documentation refresh: `releases/SupportHub-1.56.1.zip` (42,888,979 bytes; 1,749 entries).
- Initial packaged SHA-256 before final documentation refresh: `B8C8A6FC221494DFFEE610C3226C29F9E91FB25F589BAB1AEDE9B29D530F6F81`.
- Final artifact after documentation refresh: `releases/SupportHub-1.56.1.zip` (42,889,049 bytes; 1,749 entries).
- Final SHA-256: `065DACAF5B5FA8B0FFCFD9BC16E7F030213EE0ADE11C0FF0E86B5A44FFA8104F`.
## 1.66.7 — 2026-09-08

Status: superseded before deployment by `1.66.8`; do not deploy. The artifact predates restoration of the inactive-client approval selection flow.

- Adds the Support Assistant Backlog and its permission, Site Settings, sorting, intervals, warning controls, and Mine status controls.
- Corrects Follow-up to contain only manually marked tickets.
- Aligns main and Top Management dashboard widget values with their ticket drill-downs, including SLA, resolution, status, priority, product, root cause, workload, satisfaction, archived-ticket, date, and timezone behavior.
- Database compatibility revision: `0189_support_assistant_backlog`.

## 1.66.8 — 2026-09-08

Status: ready; corrected self-contained Windows x64 release generated and verified.

- Retains the Support Assistant and complete dashboard drill-down accuracy scope from `1.66.7`.
- Restores inactive and ticket-restricted clients as selectable red entries in Ticket creation so the existing confirmation and management-approval workflow can execute.
- Database compatibility revision: `0189_support_assistant_backlog`.
- Backend Ruff and strict MyPy passed; all 385 backend tests passed.
- Frontend ESLint, all 68 Vitest tests, TypeScript compilation, and production build passed.
- The packaged executable exposed `serve`, `migrate`, `seed`, and `recover-admin`; a clean packaged migration passed through `0189_support_assistant_backlog`.
- Final artifact: `releases/SupportHub-1.66.8.zip` (43,127,283 bytes; 1,793 entries).
- SHA-256: `1B9558193E3444F7C3C634BDF6309A0BC6BA507E5717769D973738C1FA60BD78`.

## 1.66.9 — 2026-09-08

Status: ready; self-contained Windows x64 release generated and verified.

- Adds the configurable inbound requests API and dedicated Site Settings tab.
- Routes ticket and call requests to the Pre-Ticket review queue with structured external metadata and idempotency.
- Includes a local PowerShell integration test requiring no third-party service.
- Database compatibility revision: `0190_inbound_pre_ticket`.
- Backend Ruff and strict MyPy passed; all 386 backend tests passed.
- Frontend ESLint, all 68 Vitest tests, TypeScript, and production build passed.
- Clean packaged migration passed through `0190_inbound_pre_ticket`.
- Artifact: `releases/SupportHub-1.66.9.zip` (43,149,729 bytes).
- SHA-256: `8B6BBDB14AA5F13978F598CCE9695E5FA26ACFE0B27CD64191EBB1B427496528`.

## 1.66.10 — 2026-09-08

Status: ready; self-contained Windows x64 release generated and verified.

- Consolidates Outlook, SMTP, and WhatsApp settings into the Third-party Integration workspace.
- Adds an in-app integration test console, stable v1 API, vendor client lookup, request-status lookup, and structured validation feedback.
- Preserves the existing unversioned inbound request endpoint for compatibility.
- Database compatibility revision remains `0190_inbound_pre_ticket`.
- Backend Ruff and strict MyPy passed; all 386 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and production build passed.
- The packaged runtime exposes all supported operational commands.
- Artifact: `releases/SupportHub-1.66.10.zip` (43,153,930 bytes).
- SHA-256: `46D0A2A64E843A7730A5A08FD394C0C890A1B26A099014F174721997FD980208`.
## 1.66.49 — 2026-09-21

Status: ready for controlled UAT deployment.

- Completes Smart UAT with checklist Excel import, expanded combined analysis and PDF results export.
- Reconciles UAT implementation progress through database revision `0221_uat_completion`.
- Backend Ruff and strict MyPy passed; all 421 backend tests passed.
- Frontend ESLint, all 80 Vitest tests, TypeScript compilation and production build passed.

## 1.66.61 — 2026-09-23

Status: ready for controlled deployment; self-contained Windows x64 release.

- Adds configurable per-contract product-led entitlement validation, expiry grace periods, and approval routing.
- Allows covered contracts without SLA to create normal tickets without SLA clocks.
- Routes expired-after-grace, out-of-scope, and inactive-client requests to Pending Approval instead of blocking them.
- Extends reusable contract templates with the same ticket-policy settings.
- Database compatibility revision: `0227_contract_ticket_policy`.
- Backend and frontend quality gates passed before packaging.

## 1.66.62 — 2026-09-24

Status: ready for controlled deployment; self-contained Windows x64 release.

- Adds bulk SLA target creation from assigned contract coverage and multiple priorities.
- Reorganizes Site Settings using the existing SLA operational values without duplicate storage.
- Makes Contract Types, Contract Templates, and SLA Templates dedicated Contract Management tabs.
- Database compatibility revision advances to `0230_dynamic_reports_center`.
- Complete backend and frontend release quality gates run during packaging.

## 1.66.63 — 2026-09-24

Status: ready for controlled deployment; self-contained Windows x64 release.

- Shows assigned engineers on Operations Planner cards and identifies unassigned operations.
- Opens operation details from the planner without triggering calendar creation actions.
- Refreshes planner data immediately after shift or operation creation.
- Database compatibility revision remains `0227_contract_ticket_policy`.
- Complete backend and frontend release quality gates run during packaging.

## 1.66.64 — 2026-09-24

Status: ready for controlled deployment; self-contained Windows x64 release.

- Shows assigned engineers, client identity, and operation status on Support Now planner cards.
- Excludes rejected operations from the Support Now calendar.
- Opens operation details in place without triggering calendar creation actions.
- Refreshes Support Now planner data immediately after operation or shift creation.
- Database compatibility revision remains `0230_dynamic_reports_center`.
- Complete backend and frontend release quality gates run during packaging.

## 1.66.65 — 2026-09-24

Status: ready for controlled deployment; self-contained Windows x64 release.

- Fixes SQL Server SLA-template creation when the code is generated automatically.
- Adds the standard L1–L4 SLA preset and safer code validation.
- Fixes null-priority contract SLA target updates.
- Seeds governed client-dependency SLA-pause reasons.
- Retains the audited business-calendar pause and resume lifecycle.
- Database compatibility revision advances to `0231_sla_client_dependency_flags`.
- Complete backend and frontend release quality gates run during packaging.

## 1.66.66 — 2026-09-24

Status: ready for controlled deployment; self-contained Windows x64 release.

- Allows the Tickets page general search to find tickets by partial client name and client code.
- Keeps client matching within the permission-aware server query so paging, totals, and sorting remain correct.
- Keeps a synchronized horizontal scrollbar at the viewport bottom while a wide ticket grid continues below the visible area.
- Database compatibility revision remains `0231_sla_client_dependency_flags`.
- Complete backend and frontend release quality gates run during packaging.

## 1.66.67 — 2026-09-24

Status: ready for controlled deployment; self-contained Windows x64 release.

- Adds five modern, server-backed per-user color themes with light, dark, and device modes.
- Makes Support Now Operations Planner cards follow the active theme palette and typography.
- Adds compact real-time online-engineer cards to the Support Now Live Operations header.
- Corrects the ticket-grid horizontal scrollbar using a viewport-fixed document portal that tracks application-shell scrolling.
- Database compatibility revision remains `0231_sla_client_dependency_flags`.
- Complete backend and frontend release quality gates run during packaging.

## 1.66.74 — 2026-09-26

Status: ready for controlled deployment; self-contained Windows x64 release.

- Replaces generic ticket-report exports with distinct professional Ticket Service Report and Incident Report structures.
- Adds structured system and manual timelines, report-only events, corrective actions and permanent ticket events.
- Adds a privacy-aware external-AI prompt assistant for ready-to-copy human report content.
- Modernizes the report editor, Reports tab and mobile-responsive secure shared-report page.
- Adds branded, compact PDF and Word output with controlled table pagination and text-only Word headers and footers.
- Database compatibility revision remains `0233_ticket_reports`; no new migration is required from `1.66.73`.
- Backend Ruff and strict MyPy passed; all 451 backend tests passed.
- Frontend ESLint, all 87 Vitest tests, TypeScript compilation and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.74`, database head `0233_ticket_reports`, ZIP readability and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.74.zip` (52,892,494 bytes; 1,981 entries).
- Final SHA-256: `931C3CF9541DEB6D2B2CED286507DEF9668D5DD2D3F5F45F75B36BE57BCF83C3`.

## 1.66.75 — 2026-09-27

Status: ready for controlled deployment; self-contained Windows x64 release.

- Categorizes the Reports Center catalog and adds searchable, permission-aware lookup filters with dependent selections.
- Adds the expanded report-catalog SQL utility to the release database tools.
- Enhances the organization hierarchy with responsive Chart and Outline views, search, expansion, zoom, pan, fit and full-screen controls.
- Unifies the Support Now and Onboarding hierarchy presentation while preserving their existing data sources.
- Database compatibility revision remains `0233_ticket_reports`; no new schema migration is required from `1.66.74`.
- Backend Ruff and strict MyPy passed; all 454 backend tests passed.
- Frontend ESLint, all 87 Vitest tests, TypeScript compilation and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.75`, database head `0233_ticket_reports`, report-catalog SQL inclusion, ZIP readability and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.75.zip` (52,914,194 bytes; 1,985 entries).
- Final SHA-256: `136752E6F5126936B56B63F43C0BB5C80C473FBF0FC13DB70776A33679F78B96`.
## 1.66.87 — 2026-09-29

Status: ready for controlled deployment; self-contained Windows x64 release.

- Redesigns recurring Service Checklists around engineer/client cards, reusable events, history, reminders, exports, sharing, transfers, ticket-task synchronization, and manager monitoring.
- Adds checklist status color coding and Client Safeguard metrics to Customer Success, Client Profile, and Support Now.
- Makes Support Now checklist safeguard cards clickable and filter-aware.
- Changes the Support Assistant Ops tab to show only the logged-in user's assigned operations in place.
- Includes ticket-board, complaint caller validation, approval-popup, and Operational Board checklist fixes.
- Database compatibility revision advances to `0235_service_checklist_shares`.

## 1.66.88 — 2026-09-29

Status: ready for controlled deployment; self-contained Windows x64 release.

- Adds a date-aware Contract Lifecycle board for active, expiring, renewing, renewed, expired, and inactive contracts.
- Adds governed drag-and-drop lifecycle transitions and compact manager actions.
- Calculates client contract-service status across all contracts so one expired agreement does not disable otherwise active coverage.
- Routes product-specific tickets with expired or inactive coverage to approval.
- Adds reusable visit types and contract visit allowances aligned with the client operational visit cycle.
- Database compatibility revision advances to `0236_client_contract_status`.
- Backend Ruff and strict MyPy passed across 193 source files; all 463 backend tests passed.
- Frontend ESLint, all 95 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest version `1.66.88`, database head `0236_client_contract_status`, ZIP readability, and standalone packaging passed.
- Final artifact: `releases/SupportHub-1.66.88.zip` (53,021,966 bytes; 1,996 entries).
- Final SHA-256: `FD174D0D73FA63B9DAB285BB2CCC5FA4A41EF309EA2507607D57F241D6CF01C2`.

## 1.66.89 — 2026-09-29

Status: ready for controlled deployment; self-contained Windows x64 release.

- Replaces full running-SLA discovery with an indexed, due-time escalation work queue.
- Backfills existing clocks and transactionally maintains queue state for SLA lifecycle changes.
- Reschedules queue work when warning configuration or escalation rules change.
- Adds queue counts and next evaluation visibility to System Operations.
- Keeps renewal, reminders, email, and Outlook as independent measured scheduler stages.
- Database compatibility revision advances to `0237_escalation_work_queue`.
- Backend Ruff and strict MyPy passed across 193 source files; all 464 backend tests passed.
- Frontend ESLint, all 95 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest version `1.66.89`, database head `0237_escalation_work_queue`, ZIP readability, and standalone packaging passed.
- Final artifact: `releases/SupportHub-1.66.89.zip` (53,034,534 bytes; 1,997 entries).
- Final SHA-256: `1C131130F0EA09CC96B7FA423A2ABA25B23DE0CECEA1EDF68F78E67A9FD347F7`.
## 1.66.93 — 2026-09-30

Status: self-contained Windows x64 release build requested.

- Uses governed system-user selections for contract-expiration To and CC recipients.
- Delivers expiration reminders through both the in-system notification center and email.
- Adds immediate rule evaluation, missed-milestone catch-up, and per-recipient duplicate prevention.
- Records channel delivery state, timestamps, recipients, and errors in a durable database ledger.
- Adds recent contract notification activity to the Contract workspace.
- Database compatibility revision advances to `0239_contract_notify_log`.
- Backend Ruff and strict MyPy passed across 196 source files; all 493 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.93`, database head `0239_contract_notify_log`, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.93.zip` (53,106,972 bytes; 2,009 entries).
- Final SHA-256: `6555A8D80D46764977DDD7104D953F7F0F6BEF2902B76570373C4D430598224F`.

## 1.66.97 — 2026-09-30

Status: contract-expiration email idempotency hotfix; self-contained Windows x64 release.

- Serializes contract lifecycle notification evaluation across SQL Server/IIS workers.
- Enforces one outbox event for each contract, term, and expiration milestone.
- Quarantines historical duplicate events and suppresses duplicates again before SMTP delivery.
- Retains grouped email delivery with proper To and CC headers.
- Database compatibility revision advances to `0242_contract_email_key`.
- Backend Ruff and strict MyPy passed across 196 source files; all 493 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and production build passed.
- Clean migration and standalone runtime command checks passed; the package contains 2,012 entries and no forbidden generated or secret files.

## 1.66.98 — 2026-09-30

Status: presence concurrency hotfix; self-contained Windows x64 release.

- Uses an atomic update for presence heartbeats so overlapping tabs do not create stale ORM updates.
- Suppresses global UI errors for best-effort presence telemetry failures.
- Makes the generic database concurrency response entity-neutral instead of incorrectly naming tickets.
- Includes the 1.66.97 contract email idempotency protections and database head `0242_contract_email_key`.

## 1.66.101 — 2026-10-01

Standalone release for SQL Server email-claim handling with unknown row counts.
Uses the returned record ID to confirm ownership. Retains transaction and
uncertain-delivery protections. Database head: `0242_contract_email_key`.

## 1.66.100 — 2026-10-01

Standalone release for corrected scheduler transaction ownership and expiration
email outcome persistence. Uncertain SMTP outcomes stop automatic retries.
Database head remains `0242_contract_email_key`. Review legacy pending messages
before enabling SMTP; prior sends may have lost database evidence.

## 1.66.99 — 2026-10-01

Status: email queue processing hotfix; self-contained Windows x64 release.

- Isolates scheduled stages so unrelated failures no longer prevent email delivery.
- Adds an audited administrator action to process the email queue from System Operations.
- Expands email diagnostics beyond password resets to all queued email event types.
- Database compatibility remains `0242_contract_email_key`.

## 1.66.105 — 2026-10-01

Status: ready for controlled deployment; self-contained Windows x64 release.

- Aligns the login page with the SupportHub executive presentation identity.
- Replaces the image and square/grid treatment with navy/teal gradients and circular orbit motion.
- Adds a responsive mobile login composition and platform-proposition footer.
- Preserves existing authentication, session, return-path, and password-reset behavior.
- Database compatibility remains `0243_contract_email_subject`.
- Backend Ruff and strict MyPy passed across 196 source files; all 500 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.105`, database head `0243_contract_email_subject`, ZIP readability, and standalone metadata passed.
- Final artifact: `releases/SupportHub-1.66.105.zip` (53,130,192 bytes; 2,015 entries).
- Final SHA-256: `AAB8B8E378BA1D939B73780B1315D524C4E593FF27C9005AF4BD83DCB5EA92C2`.

## 1.66.106 — 2026-10-01

Status: ready for controlled deployment; self-contained Windows x64 release.

- Corrects the login composition for English LTR and Arabic RTL.
- Localizes the presentation statement, description, tags, and secure-workspace label.
- Keeps credential entry LTR while mirroring the surrounding Arabic interface.
- Adds short-screen scrolling and responsive mobile footer behavior.
- Applies language-appropriate modern display-font stacks to the hero statement.
- Database compatibility remains `0243_contract_email_subject`.
- Backend Ruff and strict MyPy passed across 196 source files; all 500 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.106`, database head `0243_contract_email_subject`, ZIP readability, and standalone metadata passed.
- Final artifact: `releases/SupportHub-1.66.106.zip` (53,130,607 bytes; 2,015 entries).
- Final SHA-256: `433DEEB6313D0CC7F94C490074580BFD6143A93D159494A5FAFE9A43D7FAD4E7`.

## 1.66.107 — 2026-10-02

Status: ready for controlled deployment; self-contained Windows x64 release.

- Reduces the desktop login orbit footprint.
- Animates the outer and inner orbit rings independently in opposing directions.
- Prevents the mobile login form from clipping by allowing safe vertical
  scrolling, respecting device insets, and compacting short-screen spacing.
- Preserves reduced-motion handling and existing login behavior.
- Adds governed default service-checklist template selection and restores the
  published-template immutability guard.
- Database compatibility advances to `0244_checklist_default_template`.
- Backend Ruff and strict MyPy passed across 196 source files; all 500 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.107`, database head `0244_checklist_default_template`, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.107.zip` (53,133,864 bytes; 2,016 entries).
- Final SHA-256: `8BDD9F8123FFE7DE73A227322ECD2BA3F3798C4636A6FFDDEC5A28B92DBAE2AD`.

## 1.66.108 — 2026-10-03

Status: ready for controlled deployment; self-contained Windows x64 release.

- Runs two bounded backend processes per IIS application and enables startup retries.
- Recycles packaged workers after a configurable, jittered request count to control long-running process memory.
- Adds automated capacity-configuration coverage and includes the latest service-checklist workspace refinement.
- Database compatibility remains at `0244_checklist_default_template`.
- Backend Ruff and strict MyPy passed across 196 source files; all 500 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.108`, database head `0244_checklist_default_template`, ZIP readability, standalone metadata, IIS capacity settings, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.108.zip` (53,134,170 bytes; 2,016 entries).
- Final SHA-256: `370C91C707F6B1487AEA1B8FC960D85DA1AB2232D7E7C330F1E1DD16F7B9FC64`.
## 1.66.109 — 2026-10-03

Status: release built and verified from the current validated source.

- Supersedes `1.66.108` as the next immutable deployment package.
- Retains database compatibility at `0244_checklist_default_template`; no new migration is required.
- Builds the production frontend and the self-contained Windows x64 backend runtime.
- Runs backend lint, strict typing and tests plus frontend lint, tests and TypeScript compilation before packaging.
- Manifest version `1.66.109`, database head `0244_checklist_default_template`, ZIP readability, standalone metadata, runtime presence, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.109.zip` (53,134,454 bytes; 2,016 entries), SHA-256 `9D36CFE3A87A13319B3496D1388F3109C56F7B5A017C12E88543A0246561A863`.

## 1.66.110 — 2026-10-03

Status: login orbit visibility correction built and verified.

- Supersedes `1.66.109` with the corrected desktop login animation stacking order.
- Adds regression coverage for a visible orbit stacking level.
- Retains database compatibility at `0244_checklist_default_template`; no new migration is required.
- Builds the production frontend and self-contained Windows x64 backend runtime.
- Backend lint, strict typing and 500 tests passed; frontend lint, 98 tests, TypeScript compilation and production build passed.
- Manifest version `1.66.110`, database head `0244_checklist_default_template`, standalone metadata, runtime presence, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.110.zip` (53,134,536 bytes; 2,016 entries), SHA-256 `E0A062D0CB46426930938C5F13B405262F02995C68FB44E0D66B811F65828C8F`.

## 1.66.111 — 2026-10-03

Status: animated login background built and verified.

- Supersedes `1.66.110` with explicit grid-drift and ambient-glow background motion.
- Retains the login orbit visibility correction and reduced-motion accessibility fallback.
- Adds regression coverage for the login background animation contract.
- Retains database compatibility at `0244_checklist_default_template`; no new migration is required.
- Backend lint, strict typing and 500 tests passed; frontend lint, 98 tests, TypeScript compilation and production build passed.
- Manifest version `1.66.111`, database head `0244_checklist_default_template`, standalone metadata, runtime presence, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.111.zip` (53,135,451 bytes; 2,016 entries), SHA-256 `FCC5479B43423813D8850D24C8AEA222BFC9920FC58DBC914EE5EA64C2960BC7`.

## 1.66.112 — 2026-10-03

Status: login orbit-motion correction built and verified as a self-contained Windows x64 release.

- Supersedes `1.66.111` with explicit, continuous motion for both login orbit rings.
- Rotates the outer and inner rings independently in opposite directions while keeping the SH tile stable.
- Preserves the established login colors, ambient background animation, layout, and authentication behavior.
- Retains database compatibility at `0244_checklist_default_template`; no new migration is required.
- Backend Ruff and strict MyPy passed across 196 source files; all 500 backend tests passed.
- Frontend ESLint, all 98 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.112`, database head `0244_checklist_default_template`, ZIP readability, standalone metadata, runtime presence, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.112.zip` (53,145,333 bytes; 2,016 entries), SHA-256 `02C628A89D4DF2C96D8CAC5C4A007C8B7A638BDA0F7721B613F8CD06B9BCD221`.

## 1.66.115 — 2026-10-03

Status: built and verified; self-contained Windows x64 release.

- Adds optional product, module, and client applicability selection to Knowledge Base article creation and editing.
- Adds Knowledge Base filters for category, product, module, and client.
- Retains database compatibility at `0245_knowledge_resolution`; no new migration is required.

## 1.66.116 — 2026-10-03

Status: release build requested; self-contained Windows x64 release.

- Makes the status-change reason optional when moving a ticket to Resolved while preserving configured closure requirements.
- Populates ticket-generated Knowledge Base drafts from the ticket client, product, module, root causes, resolution, outcome, provided services, and permanent-fix fields.
- Includes the Knowledge Base article applicability selectors and filters from `1.66.115`.
- Retains database compatibility at `0245_knowledge_resolution`; no new migration is required.
- Backend Ruff and strict MyPy passed across 196 source files; all 507 backend tests passed.
- Frontend ESLint, all 100 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest version `1.66.116`, database head `0245_knowledge_resolution`, standalone runtime commands, ZIP readability, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.116.zip` (53,178,422 bytes; 2,017 entries), SHA-256 `F3C48186F31D048D906A98F74F0D51805BC9F6E0C991B2177C0D2B7523F48FBF`.

## 1.66.117 — 2026-10-04

Status: built and verified; self-contained Windows x64 IIS backend availability hotfix release.

- Removes Uvicorn request-count self-termination from IIS-hosted backend workers.
- Keeps IIS responsible for process lifetime while retaining SQL Server connection health and pool recycling protections.
- Includes the latest ticket workflow and service-checklist scheduling refinements.
- Retains database compatibility at `0245_knowledge_resolution`; no migration is required.
- Backend Ruff and strict MyPy passed across 196 source files; all 507 backend tests passed.
- Frontend ESLint, all 100 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest version `1.66.117`, database head `0245_knowledge_resolution`, standalone runtime commands, ZIP readability, required contents, IIS configuration, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.117.zip` (53,180,362 bytes; 2,017 entries), SHA-256 `9801DD7B4D3AB1C7F6A5EB5C3A3245DF573849FAE8E8FB3D84F8256DB314A956`.

## 1.66.118 — 2026-10-05

Status: built and verified; self-contained Windows x64 stability and client portal release.

- Hardens scheduler resource handling and adds per-stage working-set diagnostics.
- Corrects transient-401 session handling, reopened-ticket resolution/closure, and resolution attachment access.
- Adds protected portal satisfaction submission, a separately authorized client profile, and portal Change Request creation.
- Advances database compatibility to `0248_portal_client_profile`; migration is required.
- Backend Ruff and strict MyPy passed across 196 source files; all 512 backend tests passed.
- Frontend ESLint, all 102 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.118`, database head `0248_portal_client_profile`, ZIP readability, standalone metadata, and required runtime contents passed.
- Final artifact: `releases/SupportHub-1.66.118.zip` (53,198,343 bytes; 2,021 entries), SHA-256 `C7C7843CFF22A7E531A06427EAE575FC9B1F80C85E1EC337DBE47F8E3AE6173C`.

## 1.66.119 — 2026-10-06

Status: built and verified; self-contained Windows x64 resolution workflow release.

- Adds attachment selection to the quick ticket-card Resolve and Close dialog.
- Adds Knowledge Base search and application within that resolution dialog.
- Adds a preview-first SQL Server utility for conservatively migrating missing structured ticket root causes.
- Retains database compatibility at `0248_portal_client_profile`; migration is required when upgrading from `1.66.117` or earlier.
- Backend Ruff and strict MyPy passed across 196 source files; all 512 backend tests passed.
- Frontend ESLint, all 104 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.119`, database head `0248_portal_client_profile`, ZIP readability, standalone runtime, release notes, and packaged root-cause migration utility passed.
- Final artifact: `releases/SupportHub-1.66.119.zip` (53,205,775 bytes; 2,022 entries), SHA-256 `AF66136979A5E4BF3542CDDD3B2C0BEA49BD91036315C51EC6787A52DBBCF857`.

## 1.66.120 — 2026-10-06

Status: built and verified; self-contained Windows x64 closure-workflow release.

- Makes the Support App resolved-awaiting-closure shortcut respect the active date filters and show only the logged-in engineer's resolved tickets that still need required closure details.
- Makes Support Now show every authorized ticket matching those missing-detail criteria, regardless of assignee.
- Orders closure work by oldest resolution date and adds the resolution timestamp plus a direct Close action to Support Now.
- Retains the governed closure dialog, attachments, Knowledge Base resolution application, workflow validation, and permissions.
- Retains database compatibility at `0248_portal_client_profile`; migration is required when upgrading from `1.66.117` or earlier.
- Backend Ruff and strict MyPy passed across 196 source files; all 512 backend tests passed.
- Frontend ESLint, all 105 Vitest tests, TypeScript compilation, and the production build passed.
- Manifest/IIS version `1.66.120`, database head `0248_portal_client_profile`, standalone runtime commands, ZIP readability, required contents, and forbidden-file inspection passed.
- Final artifact: `releases/SupportHub-1.66.120.zip` (53,205,192 bytes; 2,022 entries), SHA-256 `19AA6AB5194073AEDE0E123B00845308353A29E492B4A46BD0D81022E037E6A8`.

## 1.66.121 — 2026-10-08

Status: built and verified; self-contained Windows x64 operational-management release.

- Adds the service-management workspaces and configurable dashboard widgets for Changes, Problems, and Major Incidents.
- Adds the interactive management client-location map and selected-engineer KPI workbook naming.
- Adds activity-aware presence badges to running shift cards, controlled independently by `shift.presence.view`.
- Advances database compatibility to `0254_shift_presence_permission`; migration is required.
- Backend Ruff and strict MyPy passed across 201 source files; all 539 backend tests passed.
- Frontend ESLint, all 117 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.121`, database head `0254_shift_presence_permission`, packaged migration presence, ZIP readability, standalone metadata, and forbidden-file inspection passed (`local-ai/.env.example` is the expected non-secret template).
- Final artifact: `releases/SupportHub-1.66.121.zip` (54,024,639 bytes; 2,055 entries), SHA-256 `CECD39066F1572BB6ED028305C0C83FC5DB71721E16C7F2064A4F2BDAAFBFC50`.

## 1.66.122 — 2026-10-08

Status: built and verified; self-contained Windows x64 production correction.

- Makes the management world map self-contained so production network restrictions cannot leave it blank.
- Adds Current Shift Availability to Support Now for all current shifts, including Active, Idle, and Offline engineers.
- Keeps these status details controlled only by `shift.presence.view`.
- Retains database compatibility at `0254_shift_presence_permission`.
- Backend Ruff and strict MyPy passed across 201 source files; all 539 backend tests passed.
- Frontend ESLint, all 117 Vitest tests, TypeScript compilation, and the production build passed.
- The packaged map contains no reference to the former public tile host; migration `0254_shift_presence_permission` and the standalone runtime are included.
- Final artifact: `releases/SupportHub-1.66.122.zip` (54,026,102 bytes; 2,055 entries), SHA-256 `F8D21D6C272A12FB19A91B09AF3238971AB162C89BD0866BD5D91D15DBA9D80A`.

## 1.66.123 — 2026-10-08

Status: self-contained Windows x64 release built and verified; ready for controlled deployment.

- Fixes the inline map-style load race that could leave only the sea background visible.
- Embeds base land and border layers in the initial style and installs client overlays through race-safe initialization.
- Shows permission-controlled Active, Idle, or Offline status directly on currently running shift cards in the Support Now Operations planner and retains database compatibility at `0254_shift_presence_permission`.
- Backend lint and strict type checking passed; 539 backend tests and 117 frontend tests passed.
- Manifest version `1.66.123`, database head `0254_shift_presence_permission`, packaged migration presence, standalone runtime help, ZIP readability, and absence of external map-provider references were verified.
- Final artifact: `releases/SupportHub-1.66.123.zip` (54,024,839 bytes; 2,055 entries), SHA-256 `FB60A5169DB00D14FA036812BDCD10FED9D094EE08D25041EEEFE66634345534`.
## 1.66.151 — 2026-10-16

Status: full self-contained Windows x64 deployment Word-report release built and verified.

- Redesigns deployment issues in Word exports as readable ticket-register tables with discrete intake, workflow, and resolution columns.
- Uses A3 landscape sizing, fixed widths, wrapping, repeating headers, alternating rows, and protected row splitting.
- Applies to internal and shared deployment Word reports.
- Retains database compatibility at `0272_deployment_issue_types`; no new migration is required from `1.66.150`.
- Full release gates passed: Ruff, strict MyPy across 203 backend source files, 550 backend tests, frontend lint, 121 frontend tests, TypeScript, production frontend build, and PyInstaller runtime assembly.
- Manifest version, database head, packaged runtime, ZIP readability, and 2,082 archive entries were verified.
- Final artifact: `releases/SupportHub-1.66.151.zip` (53,957,265 bytes; 2,082 entries).
- SHA-256: `54084D915BE57B870E821F4D1900251E4399FA9F7FB1FEC32340C59D3C8F6FE8`.

