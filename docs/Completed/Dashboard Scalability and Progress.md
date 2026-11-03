# Dashboard Scalability and Loading Progress

## Status

**IN PROGRESS — activated 2026-08-30.** Language enhancement is paused at its recorded checkpoint and dashboard scalability is now the active workstream.

Current production-scale report: approximately 30,000 tickets; Top Management and Executive dashboard requests cannot reliably return one year or longer ranges.

## Current investigation checkpoint

Confirmed from the current implementation:

* Both `/dashboards/summary` and `/management-dashboards/analytics` materialize broad ticket collections as ORM objects and perform major aggregation in Python.
* The general dashboard additionally materializes SLA clocks and status histories for all matched ticket IDs.
* Top Management repeatedly scans the ticket collection for trend buckets and per-client health calculations, and returns uncapped ticket evidence for some widgets.
* Ticket creation/resolution and common scope indexes already exist; indexes alone will not remove the application-memory and repeated-scan bottlenecks.
* The first implementation phase will preserve formulas while moving scope filters, counts, breakdowns, and trends into SQL and limiting evidence rows. SLA business-calendar measures will use a separately optimized/pre-aggregated path.

## 2026-08-30 local production-copy benchmark

Database: SQL Server `MillensysSupportHub`, 20,648 tickets, 20,396 SLA clocks, ticket creation range 2024-09-09 through 2026-08-30.

Completed first-response hot-path correction:

* [x] Reproduced the Top Management full-range delay: 39.99 seconds before the calendar fix (48.03 seconds under profiler instrumentation).
* [x] Identified 20,395 calls to `calculate_working_minutes`, causing approximately 61,362 SQL executions and 43.4 profiled seconds.
* [x] Bulk-load each relevant business calendar, working-day schedule, and holiday set once, while preserving the existing business-minute formula for every response clock.
* [x] Reduced the same Top Management full-range calculation to 2.85 seconds (approximately 14x faster).
* [x] Replaced quadratic breakdown counting and repeated trend scans with `Counter`/single-pass calculations.
* [x] Grouped client tickets, SLA results, contracts, and complaints once instead of rescanning all collections for every client.
* [x] Capped inline widget evidence at 100 rows; full results remain reachable through governed drilldown routes.
* [x] Benchmarked the general Executive dashboard over the same range at 3.69 seconds.
* [x] Passed 15 focused dashboard/database regression tests; Ruff and strict MyPy pass for the changed backend files.

Migration compatibility discovered and corrected during benchmarking:

* [x] SQL Server revision 0147 now safely captures, drops, and recreates non-constraint indexes that include ticket columns being converted to Unicode. This was required by the production-copy covering index `IX_tickets_client_id_created_at`.
* [x] Local production copy upgraded successfully from revision 0145 to current head 0147 without deleting ticket data.

Remaining scale work:

* [x] Push common Executive dashboard HR-department, personal scope, client, product, engineer, and team filters into SQL before ORM ticket materialization; the focused dashboard suite passes 7/7 with Ruff and MyPy.
* [x] Move Executive geographic filtering plus pending/handover counts, priority/status matrices, open backlog client/product/module/engineer/team breakdowns, aging buckets, and seven-day inflow/closure trends into grouped/conditional SQL; the response schema is preserved and 7/7 dashboard tests pass with Ruff and MyPy.
* [x] Push Top Management client/product/engineer/department/team/country/zone/location scope into SQL and compute current/previous totals plus variable-period trend buckets with conditional SQL aggregation; Ruff, MyPy, and 5/5 management-dashboard tests pass.
* [x] Consolidate Executive and Top Management trend buckets into one conditional-aggregate query per dashboard instead of one SQL round trip per bucket.
* [x] Rebenchmark the local SQL Server production copy after SQL pushdown: the full 2024-09-09 through 2026-08-30 range over 20,648 tickets completes in 2.936 seconds (down from the intermediate 9.186-second per-bucket-query result); 12/12 combined dashboard tests pass with Ruff and MyPy.
* [x] Move Executive agent assigned/open/resolved/status totals and product/module total/open/resolved aggregation into SQL; governed SLA breach and business-time evidence remains on the specialized calculation path.
* [x] Benchmark both dashboards together after KPI aggregation: Top Management completes in 2.954 seconds and Executive in 4.703 seconds over the full 20,648-ticket range; the Executive response total matches the SQL Server ticket count exactly.
* [x] Add a rollback-only SQL Server million-row core-aggregation benchmark using a connection-local temporary table. It validates exact totals, top-group result limits, elapsed time, and Python peak allocation without modifying application data.
* [x] Run the million-row core benchmark: 1,000,000 rows aggregated in 0.178 seconds with 0.014 MB peak Python allocation; totals were 1,000,000 overall, 666,667 open, 333,333 closed, and 250,000 P1.
* [x] Instrument the real full endpoints with SQL query counts and Python peak allocation. At 20,648 tickets, Top Management executes 181 statements with a 129.757 MB peak and Executive executes 178 with a 136.442 MB peak before SLA batch tuning; this identifies the specialized SLA evidence path as the remaining materialization bottleneck.
* [x] Increase SLA/dashboard ID batches safely from 1,000 to 1,900 while retaining margin below SQL Server's 2,100-parameter ceiling. The parameter-limit regression caught and rejected an unsafe 2,000-ID attempt; the corrected batch passes 21/21 dashboard/SLA tests and reduces instrumented query counts to 111 Top Management and 118 Executive.
* [x] Persist completed resolution-SLA outcome snapshots in revision `0148_sla_outcome_snapshots`, populate them when a resolution clock completes, clear them when a ticket reopens, and provide a cursor-safe historical backfill. The local SQL Server copy upgraded from 0147 to 0148 and backfilled its one eligible historical clock with zero skips; Ruff, MyPy, and 17 focused lifecycle/migration tests pass.
* [x] Rebenchmark after SLA snapshots: full-range instrumented query counts fall to 105 Top Management and 112 Executive. Tracemalloc-instrumented timings are 15.942/15.145 seconds with 130.868/137.421 MB peaks; the authoritative uninstrumented timings remain 2.954/4.703 seconds because allocation tracing materially distorts endpoint time.
* [x] Stop materializing the previous creation period in Top Management analytics after its comparison/trend aggregates moved to SQL; fetch created-or-resolved trend evidence through a separate ordered query capped at 100 rows, with regression coverage for older tickets resolved inside the selected period.
* [x] Move Top Management client-health ticket totals, open/P1 counts, resolution/reopen inputs, and complaint/open-complaint counts into grouped SQL; remove per-client Python ticket/complaint collections and preserve the CUSTOMER_SUCCESS_V1 score in a fixed comparison fixture.
* [x] Narrow the remaining Top Management current-period ORM ticket load to the columns consumed by SLA, evidence, and legacy breakdown formulas; omit large text/routing fields and batch-load status records. Apply an even narrower projection to the capped trend-evidence query.
* [x] Rebenchmark the 20,648-ticket SQL Server production copy after the materialization reductions: Top Management measures 9.093 seconds cold and 4.426 seconds warm; the instrumented run is 7.328 seconds, 104 queries, and 111.965 MB peak versus the prior approximately 130.868 MB peak. The warm Executive control is 3.082 seconds; its instrumented path remains 11.408 seconds, 116 queries, and 134.755 MB peak.
* [x] Restrict Top Management resolution-SLA calculation to current-period tickets that actually have resolution clocks, and derive completed-clock evidence from the same batched clock query. On the 20,648-ticket SQL Server copy, Top Management measures 2.881 seconds normally and 5.556 seconds instrumented, with queries reduced from 104 to 71 and peak allocation reduced from 111.965 MB to 111.439 MB. The Executive control measures 2.959 seconds normally and 11.281 seconds instrumented, with 116 queries and 135.778 MB peak.
* [x] Move Top Management status, priority, product-demand, and engineer-workload breakdowns from repeated Python scans to grouped SQL over the filtered ticket subquery; remove the unbounded Product/User lookup loads and add breakdown-total invariants. The 20,648-ticket SQL Server copy measures 1.973 seconds normally and 5.519 seconds instrumented, with 73 queries and 111.365 MB peak. The Executive control measures 2.903 seconds normally and 11.145 seconds instrumented, with 116 queries and 135.892 MB peak.
* [ ] Move general dashboard counts, breakdowns, aging, and agent/product KPI aggregation into SQL so memory use does not grow linearly with ticket history.
* [ ] Move Top Management scope filtering and core count/breakdown aggregation into SQL; the current 2.85-second result still materializes ticket rows.
* [x] Add a rollback-only representative 30K full-endpoint fixture with total reconciliation and elapsed-time, query-count, and peak-memory ceilings. Cloned tickets preserve the production copy's client/status/product/assignee distribution and are removed in `finally`; the database returned to 20,648 tickets after both runs. At 30,000 tickets, Top Management measures 7.164 seconds normally and 11.859 seconds instrumented, with 93 queries and 142.222 MB peak; Executive measures 10.125 seconds normally and 21.094 seconds instrumented, with 146 queries and 171.288 MB peak. Both endpoint totals reconcile to 30,000. Full endpoint-scale SLA-clock cloning remains separate because the rollback fixture deliberately adds no synthetic SLA evidence.
* [x] Move Top Management resolved and active-incident totals to SQL, cap active-incident evidence at the query, and narrow the remaining current-period SLA/evidence ticket projection to ID, ticket number, client, priority, and closed time. At 20,648 tickets, instrumented peak falls from 111.365 MB to 106.996 MB with 75 queries. At 30,000 rollback-only tickets, Top Management measures 6.809 seconds normally and 10.745 seconds instrumented, with 95 queries and 135.053 MB peak versus 142.216 MB before this reduction; Executive remains the control at 10.020 seconds normally, 146 queries, and 168.671 MB instrumented peak.
* [x] Eliminate the remaining all-current-ticket ORM/identity collection from Top Management. Join response clocks, resolution clocks, clock-bearing ticket projections, satisfaction ratings, and root causes directly to the filtered ticket subquery; only clock-bearing tickets become ORM objects. This removes dashboard-side ID batching and preserves client-health attribution. On the dense-clock 20,648-ticket copy, Top Management measures 3.685 seconds instrumented, 34 queries, and 106.852 MB peak. On the rollback-only 30K fixture, it measures 1.692 seconds normally and 3.768 seconds instrumented, with the same 34 queries and 106.863 MB peak; Executive remains the control at 7.676 seconds normally, 146 queries, and 168.930 MB peak.
* [x] Add an opt-in rollback-only dense SLA fixture that clones governed response/resolution clocks and completed outcome snapshots from each cloned ticket's source, enforces at least 90% clocks per ticket, reconciles endpoint totals, and rolls back both entity types. At 30,000 tickets and 29,657 clocks, Top Management measures 2.384 seconds normally and 5.138 seconds instrumented, with 34 queries and 150.263 MB peak. Executive measures 11.109 seconds normally and 19.706 seconds instrumented, with 146 queries and 185.666 MB peak. After both runs, the configured database was verified at exactly 20,648 tickets and 20,396 clocks.
* [x] Consume completed resolution outcomes directly from scalar snapshot rows and load ORM tickets only for incomplete/unresolved resolution clocks; scalarize completed first-response clock rows as well. On the 30K/29,657-clock dense fixture, Top Management peak falls from 150.263 MB to 26.562 MB before response snapshot backfill, while query count falls to 33 and normal elapsed time reaches 1.148 seconds.
* [x] Persist first-response actual business minutes in revision `0153_response_sla_snapshot`, populate them when clocks complete, retain governed calendar fallback for legacy rows, and provide a cursor-safe bulk-calendar backfill. The local SQL Server copy upgraded transactionally from 0149 through 0153; all 20,395 eligible historical first-response clocks backfilled in 6.6 seconds with zero skips. The dense fixture then measures 1.203 seconds normally and 8.432 seconds under allocation tracing, with 33 queries and 27.026 MB Top Management peak. The current-head Executive control is 19.871 seconds, 146 queries, and 228.898 MB peak, now tracked under a temporary explicit 240 MB ceiling pending its separate clock-materialization reduction.
* [x] Narrow the general Executive ticket ORM projection to the 16 fields consumed by legacy KPI formulas, then replace batched full-clock ORM loads with one scoped scalar query for clock presence and due-soon state. On the 30K/29,657-clock dense fixture, Executive falls from 228.898 MB and 146 queries to 130.480 MB and 131 queries under allocation tracing; normal elapsed time is 6.462 seconds. Its enforced peak ceiling is restored and tightened to 160 MB. Top Management remains 1.182 seconds normally, 33 queries, and approximately 27 MB peak.
* [x] Extend the rollback-only million-row SQL Server benchmark to dense scalar SLA history: 1,000,000 tickets plus 2,000,000 response/resolution facts. It reconciles 1,000,000 response snapshots, 333,333 completed resolution snapshots, 666,667 due-soon running clocks, top ticket groups, and client SLA aggregates in 0.434 seconds with 0.028 MB Python peak. No daily fact table is introduced because indexed scalar aggregation remains far below the interactive target.
* [x] Add a reusable read-only SQL Server plan/IO diagnostic for ticket totals, response/resolution snapshots, and client SLA grouping. Estimated plans select `ix_tickets_created_status` for ticket totals and `ix_sla_clock_outcome_snapshot` for resolution/client SLA work; the full-range response branch may also scan an existing requester-contact index because nearly all tickets qualify. The configured `pymssql` driver does not expose `STATISTICS IO` informational messages, so logical-read capture remains open and no production index is replaced without that evidence.
* [ ] Review the unusually wide production covering index and replace it with purpose-built dashboard indexes after capturing SQL Server execution plans and logical reads.
* [ ] Introduce incremental daily facts only for measures that fail the interactive target after grouped-SQL optimization.

Latest continuation point (2026-09-01): both historical dashboard endpoints pass the rollback-only 30K dense-SLA budgets after scalar/snapshot optimization. With 30,000 tickets and 29,657 clocks, Top Management measures 1.182 seconds normally, 33 queries, and approximately 27 MB instrumented peak; Executive measures 6.462 seconds normally, 131 queries, and 130.480 MB instrumented peak. The expanded generated benchmark validates 1,000,000 tickets and 2,000,000 dense SLA facts in 0.434 seconds with 0.028 MB Python peak, so daily facts are not currently justified for these scalar measures.

Release regression checkpoint (2026-08-31): a cold full-range run measured 12.259 seconds Top Management and 8.530 seconds Executive on 20,648 tickets, leaving insufficient margin under the frontend's ordinary 15-second timeout for the 30K production database. Release 1.52.3 applies a 120-second window only to the two historical analytics requests while retaining the 15-second default elsewhere. A warm rerun measured 3.429/3.689 seconds. This restores delivery of long-range results but does not replace the remaining client-health/pre-aggregation work.

## Reported problem

Long dashboard ranges, including ranges beginning in 2024, can exceed the current request timeout while analysing more than 20,000 tickets. The system is expected to retain millions of tickets over its lifetime, so dashboard cost must not grow by loading all matching ticket rows into application memory.

## Required outcome

* Interactive dashboard summaries remain responsive as ticket history grows into millions of rows.
* Date, scope, department, client, product, status, and permission filters are applied in SQL before aggregation.
* Dashboard APIs return aggregate result sets, not entire ticket/entity collections for Python-side analysis.
* Queries use reviewed covering/filtered indexes based on actual execution plans and production filter patterns.
* Expensive historical calculations use incremental/pre-aggregated summary tables where live SQL aggregation cannot meet the agreed response target.
* Normal interactive ranges remain synchronous and fast.
* Very large or export-grade analyses run as asynchronous jobs with persisted states such as `QUEUED`, `RUNNING`, `COMPLETED`, and `FAILED`.
* The frontend shows determinate progress only when the backend can report real completed work units. Otherwise it shows an honest indeterminate loading indicator rather than a fabricated percentage.
* Cancellation, retry, failure details, authorization, and stale-result handling are supported for asynchronous jobs.
* Increasing Axios, reverse-proxy, IIS, or application timeouts is not considered the scalability fix.

## Investigation scope

1. Capture timings and SQL Server execution plans for the general and Top Management dashboard endpoints using representative small, 20K+, and projected million-row datasets.
2. Identify endpoints that materialize tickets, clients, contracts, users, products, or branches and aggregate them in Python.
3. Inventory current indexes on ticket date columns and common dashboard filter/join columns.
4. Confirm whether creation, resolution, and closure date bases can share query/index strategies or need separate paths.
5. Measure query duration, logical reads, rows returned, Python processing time, response size, and peak memory.
6. Preserve all existing KPI formulas and compare old/new results over fixed datasets before switching implementations.

## Proposed architecture

### Interactive summaries

Use grouped SQL queries with conditional aggregates and narrow joins. Fetch only the dimensions and measures required by each dashboard widget. Execute independent aggregate queries concurrently only where SQL Server capacity testing shows that this improves total latency.

### Historical scale

Introduce daily summary/fact tables only for calculations that remain too expensive after query and index optimization. Update summaries incrementally and provide an auditable rebuild command for corrections or deployments. Recent/open-ticket values that can change must be refreshed safely.

### Progress-capable analysis

For analysis that cannot meet the interactive response target:

1. `POST` creates an analysis job and returns its identifier.
2. A worker processes known partitions, such as monthly date slices or defined aggregation stages.
3. The job stores completed units, total units, percentage, current stage, timestamps, and sanitized failure details.
4. The frontend polls or subscribes to job status and renders a determinate progress bar.
5. Completion returns a stable result identifier; reopening the page can recover the active/completed job.

The percentage must represent actual completed partitions/stages. It must not be based on elapsed time or simulated timers.

## Acceptance criteria

* Dashboard queries do not load every matching ticket into Python.
* A 20K-ticket historical range completes within the agreed interactive target without HTTP 502/timeout.
* Million-row performance is demonstrated using a representative generated or restored dataset and documented SQL Server measurements.
* Existing dashboard totals and drill-through counts match the pre-change implementation on comparison fixtures.
* Top Management follows the same scalable data path and preserves its permission/scope rules.
* Long jobs expose accurate progress and survive page reload.
* The UI displays loading, progress, completion, empty, cancellation, and failure states.
* Automated tests cover aggregation correctness, authorization, job progress, retry/idempotency, and frontend state recovery.

## Known existing audit finding

The prior codebase audit already identified that the Top Management dashboard loads broad entity collections and performs filtering/aggregation in Python (`PERF-01`), and that contract-renewal analysis includes an O(n²) path (`PERF-02`). These findings must be revalidated against the current code and addressed in this performance phase.
