# Wave 2C — Ticket-number List Search

Status: `DONE`

## Objective

Provide fast, authorization-safe ticket-number search across the complete internal and portal datasets.

## Workstreams

1. Add a dedicated Ticket number field to internal and portal ticket lists.
2. Support exact full number, numeric portion, configured prefix, case-insensitive partial value, and trimmed input.
3. Compose with all existing filters using `AND`, preserve sort, and reset pagination on changes.
4. Store the value in URL query state for refresh, sharing, Back/Forward, and new-tab behavior.
5. Query server-side across the authorized dataset; out-of-scope numbers return an indistinguishable empty result.
6. Add clear/reset, syntax guidance, loading, no-match, and semantic ticket links.
7. Add/index a normalized lookup column only if query-plan evidence requires it.

## Tests and exit criteria

- Exact, partial, numeric, mixed-case, whitespace, invalid, no-match, and clearing tests.
- Filter composition, pagination reset, URL restoration, portal isolation, authorization non-disclosure, and representative-scale query-plan tests.
- All standard gates and migration rehearsals pass.
- Exit: an authorized ticket is findable regardless of its current loaded page.

Next wave after completion: Wave 2D.

## Required completion checkpoint

When accepted, update this file and the master plan, record the standard `CODEX STOP POINT` (status, completed scope, last item, next item, continuation safety, and blockers), and stop before Wave 2D until explicitly continued.

## Implementation record — 2026-08-20

- Added a dedicated `ticket_number` query contract to internal and portal ticket lists and portal exports.
- Matching is trimmed, case-insensitive, partial, and therefore supports full numbers, configured prefixes, and numeric portions.
- The filter is applied server-side after the user's visibility scope and composes with all existing filters.
- Added the dedicated field to internal and portal list interfaces with syntax guidance, clear behavior, pagination reset, and URL persistence.
- Portal isolation tests prove that an exact out-of-scope ticket number returns an ordinary empty result.
- Existing ticket-number indexes and the bounded partial-search behavior were retained; no schema migration was justified.
- Verification: backend Ruff and Mypy passed; 190 backend tests passed; frontend ESLint, 4 Vitest tests, TypeScript, and production build passed. The existing non-blocking vendor chunk advisory remains.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 2C — ticket-number list search
Last completed item: Passed full gates with internal/portal URL filters and authorization non-disclosure tests
Next planned item: Wave 2D — user and department hierarchy foundation
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0095_ticket_notify (unchanged)
============================================================
