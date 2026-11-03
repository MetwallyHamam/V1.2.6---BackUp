# Wave 7A — Dashboard Inventory and Consolidation Execution Plan

Status: DONE — release checkpoint verified 2026-08-20

## Objective

Inventory and consolidate dashboards so each metric has a clear purpose, owner, formula, audience, and canonical location.

## Prerequisites

- Wave 7 is complete.
- Current dashboard routes, cards, charts, queries, permissions, and usage evidence have been inventoried.

## Workstreams

1. Catalog every dashboard element, owner, audience, formula, source, scope, freshness, evidence link, and cost.
2. Decide keep, merge, move, rename, replace, or retire with product-owner approval.
3. Assign one canonical location/query for each retained metric and remove semantic duplication.
4. Standardize layout, filters, empty/error/loading states, terminology, responsiveness, and accessibility.
5. Add performance budgets and measure query/card latency before and after consolidation.
6. Redirect retired routes and document user-facing changes.

## Migration and compatibility

- Preserve bookmarks through redirects or an explicit compatibility period.
- Compare old/new values under identical filters before switching canonical ownership.
- Remove old queries only after consumers and exports are traced.

## Verification

- Automated inventory checks cover registered dashboard components and routes.
- Golden fixtures reconcile retained cards with Wave 7 reports.
- Test role variants, saved URLs, empty data, responsive layouts, accessibility, and performance.
- Obtain owner sign-off for every removal or semantic change.

## Exit criteria

- No retained metric lacks an owner, definition, source, scope, and evidence destination.
- Duplicate metrics are consolidated or intentionally documented.
- Compatibility, reconciliation, accessibility, and performance checks pass.

## Next wave

Wave 7B — Dashboard Evidence Links and Department Structure.

## Required completion checkpoint

When accepted, record the standard `CODEX STOP POINT` and stop before Wave 7B until explicitly continued.

## Completion record

- Published dashboard inventory version `WAVE7A-1.0` with canonical owners, audiences, routes, evidence contracts, decisions, and freshness rules.
- Consolidated the new operational measures into `/operational-reports` while retaining `/` as the compatibility dashboard route.
- Automated verification confirms no duplicate canonical metric codes.
