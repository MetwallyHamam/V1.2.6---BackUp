# Unified Company Operations — Restored-Copy Rehearsal Record

**Status:** PARTIAL PASS — populated SQL Server restored-copy rehearsal complete; pilot approvals and operational activation evidence pending  
**Rehearsed:** 2026-11-24  
**Package:** `UNIFIED_COMPANY_OPERATIONS_PILOT_RELEASE_PACKAGE.md`  
**Database head:** `0292_unified_ops_hardening`  
**Environment changed:** Isolated SQLite files plus one uniquely named local SQL Server restored-copy database; source database unchanged

## 1. Outcome

The clean installation, seed, file-level restore, compatibility diagnosis, rollback cycle, read-only reconciliation and focused authorization/security suite passed. A native SQL Server backup was verified and restored into a uniquely named local rehearsal database; the populated restored copy also completed its rollback/re-upgrade cycle. The local IIS test backend and frontend were subsequently refreshed over timestamped rollback copies. The source business data, production/remote systems, customer mappings and permission assignments were not changed.

This is not a production `GO`. The restored SQL Server copy contains the current 422 Clients and 76 Branches but no approved Organization mappings or unified Projects. Approved pilot mapping, named participants, monitoring delivery and a signed feature-control decision remain required.

## 2. Rehearsal evidence

Evidence directory:

```text
backend/.rehearsals/uco-20261124-105025
```

| Check | Result |
|---|---|
| Clean migration | Full Alembic chain upgraded successfully to `0292_unified_ops_hardening`. |
| Idempotent seed | `supporthub_runtime.py seed` completed successfully. |
| Restore-copy integrity | Source and copied database initially had the same SHA-256: `CB5ED4F1D6425289F689C59CDB963EC667F0080C751AF4884CCD7CDD08904A9F`. |
| Compatibility before rollback | `READY`; revision `0292_unified_ops_hardening`; no missing table or column. |
| Rollback cycle | Restored copy downgraded to `0291_project_kpi_dictionary` and re-upgraded to `0292_unified_ops_hardening`. |
| Compatibility after rollback | `READY`; revision `0292_unified_ops_hardening`; no missing table or column. |
| Final restored-copy SHA-256 | `162692F331B3B364143E0DFB4B481DCC4B1E48C015409013EFA585DFCA6693C9` after the expected rollback/re-upgrade writes. |
| Read-only reconciliation | `DRY_RUN_READ_ONLY`; 0 Clients, 0 Projects, 0 exceptions and 0 automatic changes. |
| Reconciliation formats | `reconciliation.json`, `exceptions.csv` and `reconciliation.md` created successfully. |
| Focused tests | 35 passed; no failures. |
| Unified Operations frontend tests | 15 tests across 11 files passed. |
| Focused frontend lint | Passed for the Unified Operations pages, components and tests. |
| TypeScript | Project build/type check passed. |
| Production frontend build | Passed; dedicated Unified Operations chunks were emitted. |
| Backend static verification | Ruff passed; strict MyPy passed across 232 source files. |
| Permission withdrawal drill | Passed on the designated testing database: the same token received `200` before profile removal and `403` afterward; synthetic user/profile cleanup passed. |

The changed final hash is expected because the downgrade/re-upgrade cycle rewrote database metadata and indexes. Restore-copy integrity is demonstrated by the identical hashes immediately after the copy and before that cycle.

## 3. Focused verification scope

The passing suite covered:

- customer hierarchy and effective department policy behavior;
- Project portfolio authorization and hierarchy validation;
- planned/unplanned execution, work logs, evidence, reviews and active-timer hardening;
- cross-department request, response, shared/private history and same-client ticket links;
- Support readiness, handover decisions, stabilization and activation controls;
- governed analytics permissions, evidence drilldown and Support-readiness queue;
- read-only migration reconciliation and zero automatic changes;
- release head compatibility and reversible hardening migration metadata.

Command executed from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  app\tests\test_customer_structure.py `
  app\tests\test_project_portfolio.py `
  app\tests\test_project_execution.py `
  app\tests\test_project_collaboration.py `
  app\tests\test_project_support_handover.py `
  app\tests\test_project_analytics_dictionary.py `
  app\tests\test_company_migration_reconciliation.py `
  app\tests\test_release_database_revision.py -q
```

Non-blocking warnings were the existing Starlette `httpx` deprecation warning and Alembic `path_separator` deprecation warnings.

The frontend production build retained the known mixed static/dynamic import and shared-chunk size warnings. Full-repository ESLint also found one unrelated existing error (`openHistory` is unused in `SimpleChecklistWorkspace.tsx`) and one existing UAT hook-dependency warning. Those unrelated user changes were not modified; focused lint for the Unified Operations scope passed.

## 4. Package evidence status

| Evidence ID | Rehearsal result |
|---|---|
| `UCO-PILOT-01` | Pending named scope and business approvals. |
| `UCO-PILOT-02` | Source revision verified; deployable artifact/version/checksum still pending selection. |
| `UCO-PILOT-03` | Local pass: native SQL Server backup verification, unique restored copy and rollback/re-upgrade proof passed; independent operational backup owner sign-off remains pending. |
| `UCO-PILOT-04` | Partial: populated SQL Server reconciliation passed with zero automatic changes and 422 known mapping exceptions; approved pilot mapping remains pending. |
| `UCO-PILOT-05` | Technical pass: focused authorization tests and same-token `200 → 403` profile-withdrawal drill passed with complete synthetic identity cleanup; production named-user approval/export remains pending. |
| `UCO-PILOT-06` | Pending signed choice: dedicated backend feature control or accepted permission-withdrawal exception. |
| `UCO-PILOT-07` | Partial: backend functional/security, 15 focused frontend tests, focused lint, TypeScript and production build passed; populated end-to-end/manual accessibility acceptance remains pending. |
| `UCO-PILOT-08` | Pending alert delivery and owner acknowledgement. |
| `UCO-PILOT-09` | Partial: schema rollback cycle passed; full application/storage recovery drill pending. |
| `UCO-PILOT-10` | `NO-GO`; signed decision pending. |

## 5. Remaining completion gates

Step 8.11 remains in progress until all of the following are complete:

1. Obtain operational owner sign-off for the verified local SQL Server backup/restored-copy evidence.
2. Review the populated reconciliation output and obtain approval for the pilot-only Account/Organization/Client/Branch mapping.
3. Obtain production named-user approval/export; the synthetic same-token permission withdrawal mechanism has been proven successfully on the designated testing database.
4. Rehearse the signed runtime-control choice. The current code has no dedicated Unified Operations kill switch.
5. Execute the complete pilot workflow with one synthetic or approved pilot Project, including private-history denial and aggregate/drilldown reconciliation.
6. Complete manual responsive/accessibility checks and ordinary ticket/SLA regression smoke against the rehearsed artifact; the automated frontend tests, focused lint, TypeScript and production build have passed.
7. Deliver test alerts to named owners and rehearse application/storage recovery.
8. Complete evidence `UCO-PILOT-01` through `UCO-PILOT-09` and obtain the signed deployment decision.

Until then, the deployment decision remains `NO-GO` and production activation is not authorized.

## 6. SQL Server restored-copy rehearsal

**Attempted:** 2026-11-24  
**Initial result:** BLOCKED BEFORE AUTHENTICATION  
**Retried after SQL Server licensing repair:** PASSED

- The configured connection to `127.0.0.1/MillensysSupportHub` was refused because the `MSSQLSERVER` database-engine service was stopped.
- `SQLBrowser`, SQL telemetry and SQL VSS Writer were running, but they do not provide the database engine.
- An authorized attempt to start `MSSQLSERVER` failed with Windows service exit code `17051`.
- The Windows Application event log reported SQL Server event `17051`: the installed SQL Server evaluation period has expired.
- This failure occurs before SQL authentication. No supplied credential was written to this record, repository content or generated evidence.
- No database was created, restored, migrated, downgraded or changed by this attempt.

After the local SQL Server licensing repair, the engine started as SQL Server 2019 Standard Edition (`15.0.2210.4`) and connected successfully as the configured administrative login. The source was confirmed at `0292_unified_ops_hardening`.

### 6.1 Native backup and restore

- Created and checksum-verified a copy-only native backup of `MillensysSupportHub`.
- The first restore target used SQL Server's default `C:` data path and failed safely before database creation because only about 2 GB was free while the database files required about 7.8 GB.
- Retried using `D:\SupportHub\DB`, which had about 36.3 GB free.
- Restored successfully to `MillensysSupportHub_UCO_Rehearsal_20261124_131106`; the database is `ONLINE` and `MULTI_USER`.
- The source database was never overwritten, detached, downgraded or placed into restricted access.

### 6.2 Populated reconciliation and rollback

- Compatibility on the restored copy reported `READY` at `0292_unified_ops_hardening`.
- Before counts were 422 Clients, 0 Accounts, 0 Organizations, 76 Branches and 0 unified Projects.
- Read-only reconciliation reported 422 known missing-Organization mapping exceptions and zero automatic changes; JSON, CSV and Markdown evidence is stored under `backend/.rehearsals/uco-sqlserver-20261124-131106`.
- The restored copy completed `0292 → 0291 → 0292` successfully and returned to `READY`.
- After counts exactly matched the before counts.
- The hierarchy, portfolio, handover queue and work-log hardening indexes were present after re-upgrade.
- A final read-only source check confirmed `MillensysSupportHub` remained at `0292` with the same monitored counts.

The restored rehearsal database and backup are retained temporarily as evidence. They are not authorized for application traffic or pilot activation.

## 7. Testing-database permission and SQL compatibility follow-up

The operator clarified that `MillensysSupportHub` is the designated local testing database. Subsequent non-production verification therefore used that database directly.

- The database was already at `0292`, but its application seed was incomplete: `project.portfolio.view` and `handover.view` were absent.
- The normal idempotent IAM seed was run through the working application configuration. Permission inventory increased from 284 to 312 and the Unified Operations permissions became available.
- The packaged runtime initially failed because `web.config` contained the unresolved `REPLACE_WITH_SECRET_IN_SERVER_ENVIRONMENT` placeholder. The loader treated that marker as a real `DATABASE_URL`, masking the valid encoded URL supplied by `.env`/the host environment.
- `supporthub_runtime.py` now ignores unresolved `REPLACE_*` template values while preserving explicit host environment values. It never logs or persists the resolved secret.
- Nineteen focused capacity/runtime/release tests, Ruff and MyPy passed for this correction.
- With no `DATABASE_URL` process override, the packaged runtime successfully ran `diagnose-db`, the idempotent `seed`, and a second `diagnose-db`; both diagnoses returned `READY` at `0292` with no missing table or column.
- The first live Project API request uncovered SQL Server-invalid `WHERE company_projects.is_active IS 1` syntax caused by ORM `.is_(True)` filters.
- All affected Project portfolio, options, collaboration-user and active-timer Boolean filters were changed to dialect-aware equality against `true()`.
- A regression guard now rejects `.is_(True)` in the Project modules.
- Ruff, MyPy and 21 focused portfolio, execution, collaboration, handover and release-revision tests passed after the fix.
- The repeated live permission drill used one signed token. `GET /api/v1/projects` returned `200` while the synthetic profile assignment existed and `403` immediately after it was removed.
- The synthetic user and profile were deleted successfully after the drill. No customer, ticket, Project or hierarchy record was created or changed.

## 8. Local IIS compatibility deployment

The visible application reported a database incompatibility after the testing database reached `0292`. Investigation proved that the active IIS backend was an older November 22 executable whose deployed compatibility contract expected `0284_customer_follow_up_report`; its own `diagnose-db` reported `MIGRATION_REQUIRED` against the newer `0292` database. The database was not downgraded.

- Rebuilt the self-contained Windows backend from the verified source.
- Added `pymssql` as an explicit PyInstaller hidden import after the first candidate build exposed the missing SQL Server driver before deployment.
- The rebuilt candidate reported `READY` at `0292` before IIS changes.
- Stopped only the `SupportHubBackEnd` application pool.
- Preserved the former runtime, application source and Alembic directory under timestamped deployment backups with stamp `20261124-142957`.
- Deployed the current runtime, application source, migrations and Alembic configuration to `D:\SupportHub\Release\backend`.
- The deployed executable completed `diagnose-db → seed → diagnose-db`; both diagnoses reported `READY` at `0292` with no missing table or column.
- Restarted `SupportHubBackEnd`; IIS created a new worker successfully.
- Live `GET /SupportHub/backend/api/v1/health` returned service status `ok`.
- Live `GET /SupportHub/backend/api/v1/health/database` returned database `reachable`, schema `compatible`, revision `0292_unified_ops_hardening`.
- The tested frontend build was deployed to the local IIS test site over rollback copy `D:\SupportHub\Release\frontend.pre-uco-20261124-143819`.
- The home page and the `company-operations-setup`, `customer-structure` and `project-analytics` SPA routes returned HTTP `200`; their dedicated build chunks were present in the deployed assets.
- A browser hard refresh may still be required to discard previously cached assets and the earlier compatibility result.

Rollback remains recoverable from the `*.pre-uco-20261124-142957` directories, but using the old backend against `0292` would intentionally restore the compatibility banner and is not an acceptable steady state.

## 9. Bulk client organization assignment follow-up

The local test release now includes a governed bulk action in Customer Structure for assigning multiple clients to the selected Organization. The selector loads all paginated clients, supports name/code search and clearly marks reassignments. Submission is atomic, requires `client.manage` and an audit reason, deduplicates selected IDs, validates that every Client and the target Organization exist, and writes one `client.organization_bulk_assigned` audit event for each changed Client. Focused backend tests cover assignment, reassignment, deduplication, audit evidence and atomic failure; frontend type checking, focused lint/test and the production build passed.

The backend runtime, source snapshot and frontend were deployed to the local IIS test site with rollback stamp `20261124-145532`. Live database health remained compatible at `0292`, the Customer Structure route returned HTTP `200`, and an unauthenticated request to the new endpoint returned the expected `401`, proving route registration without changing customer data.
