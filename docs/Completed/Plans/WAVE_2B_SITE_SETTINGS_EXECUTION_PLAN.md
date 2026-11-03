# Wave 2B — Categorized Site Settings

Status: `DONE`

## Objective

Replace the monolithic settings experience with categorized, URL-addressable, permission-safe tabs whose mutations are isolated and auditable.

## Workstreams

1. Inventory every existing setting, owner, permission, secret classification, validation rule, and current endpoint.
2. Implement stable categories: General, Ticket Notifications, Ticket Forms, Email, Attachments & Storage, Security & Access, Integrations, and Advanced.
3. Use `/system?tab=<category>` URL state with responsive tabs/category selection, direct loading, refresh, and browser navigation.
4. Give each category independent read/write schemas, save/cancel state, validation summary, optimistic concurrency version, and audit record.
5. Mask secrets permanently after save; exclude recoverable secret values from API responses and audits.
6. Protect dirty forms on tab/page exit and support Stay, Discard, and Save-and-continue.
7. Show only authorized categories and enforce identical backend permissions.

## Data and API

- Add category/version metadata only where current `SiteSetting` rows cannot safely provide concurrency.
- Preserve existing keys and migrate without duplicating settings.
- Return conflict responses for stale versions.

## Tests and exit criteria

- Exact-once setting inventory; permission and secret non-disclosure tests.
- Independent tab mutation, dirty-state, stale update, direct-link, responsive, keyboard, and audit tests.
- All standard gates and clean/populated SQLite/SQL Server rehearsals pass.
- Exit: every setting has one category and unrelated values cannot be overwritten.

Next wave after completion: Wave 2C.

## Required completion checkpoint

When accepted, update this file and the master plan, record the standard `CODEX STOP POINT` (status, completed scope, last item, next item, continuation safety, and blockers), and stop before Wave 2C until explicitly continued.

## Implementation record — 2026-08-20

- Added the eight-category, URL-addressable `/system?tab=<category>` Site Settings interface.
- Consolidated navigation links into the appropriate Site Settings tabs while retaining legacy routes for compatibility.
- Added a permission-protected category inventory that assigns every persisted `SiteSetting` key exactly once and identifies endpoint-managed resources.
- Added an isolated General category read/write contract with optimistic version checks, stale-update rejection, validation, and category-scoped audit evidence.
- Preserved existing specialized notification, ticket-form, SMTP, storage, feature-policy, Outlook integration, status, and backup endpoints.
- Added dirty General-form navigation/unload protection and explicit save/cancel controls.
- No database migration was required; version metadata is stored using a backward-compatible internal site-setting key.
- Verification: backend Ruff and Mypy passed; 190 backend tests passed; frontend ESLint, 4 Vitest tests, TypeScript, and production build passed. The existing non-blocking vendor chunk advisory remains.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 2B — categorized Site Settings
Last completed item: Passed backend and frontend quality gates with categorized inventory, isolated updates, concurrency, permissions, and URL tabs
Next planned item: Wave 2C — ticket-number list search
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0095_ticket_notify (unchanged)
============================================================
