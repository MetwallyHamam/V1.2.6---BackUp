# SupportHub 1.66.13 — Support Assistant Personal Workspace

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Adds durable per-user Support Assistant defaults, workspace layout, density, page size, card visibility, tab sorting, and filters.
- Adds custom personal tabs with editing, duplication, default selection, deletion, keyboard context menus, and drag or menu reordering.
- Adds a single-click ticket preview with description, client, SLA, recent comments, attachments, and direct operational actions.
- Adds compact sticky navigation, active-filter chips, Cards/List layouts, loading skeletons, improved empty states, and mobile actions.
- Preserves the existing full-card flashing behavior for overdue unreceived and SLA-risk tickets.
- Improves Notifications navigation and collapses notification filters by default.
- Returns resolved or closed tickets to the Support Assistant tab from which they were opened.

## Database

- Alembic head advances to `0193_assistant_user_state`.
- Adds `default_tab`, `workspace_state_json`, and `custom_tabs_json` to `support_assistant_preferences`.
- Existing users default to Queue with the standard comfortable Cards layout.

## Deployment

Back up the production database before deployment. Deploy to a new versioned directory, run `backend\runtime\SupportHubBackend.exe migrate`, switch IIS paths, and verify personal Assistant settings with a test engineer account.

## Verification

- Backend Ruff and strict MyPy passed.
- All 392 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The package was generated with database head `0193_assistant_user_state`.
