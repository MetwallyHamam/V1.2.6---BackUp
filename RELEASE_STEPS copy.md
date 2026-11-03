# Release Steps and Development Recovery Log

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
