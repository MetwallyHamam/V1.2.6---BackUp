# SupportHub 1.64.0 — Daily Support Assistant

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Fixes the SQL Server Top Support Agents dashboard query by joining distinct breached resolution-SLA tickets instead of aggregating an expression containing a subquery.
- Refocuses the Support Assistant on today's operational work with Queue, Mine, Follow-up, SLA Risk, and Pre-Tickets tabs.
- Adds independent permissions for showing or hiding each Assistant tab.
- Adds live tab counters, including completed/total progress for Mine.
- Defines SLA Risk from 50% resolution-SLA consumption.
- Adds an audited Mark/Clear Follow-up action and includes active Call Center-created work in Follow-up.
- Adds permission-governed Create Ticket and Create Pre-Ticket quick actions.
- Adds an explicit Back action after opening ticket details.
- Refreshes cards and counters through the authenticated WebSocket channel, with a 60-second recovery poll.

## Database

- Required Alembic head: `0187_support_assistant_daily`.
- The migration adds `tickets.support_follow_up_flag` and five Support Assistant tab permissions.
- Existing eligible profiles receive compatible tab permissions with `scope_type='NONE'`.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Confirm Alembic reaches `0187_support_assistant_daily`.
5. Verify the Top Support Agents widget and permission-controlled Assistant tabs.

## Verification

- Ruff and strict MyPy passed.
- All 380 backend tests passed.
- All 25 frontend test files and 50 tests passed.
- Frontend lint, TypeScript, and production Vite build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- A packaged upgrade rehearsal passed from `0186_support_assistant_prefs` to `0187_support_assistant_daily`.
- Archive inspection found 1,791 entries, all required deployment files, and no forbidden source/cache/secrets files.

Artifact: `releases/SupportHub-1.64.0.zip` (`43,098,504` bytes).

SHA-256: `092770F1E4C5990EEB4C14312311D7B572EDFE229AE68BC0A5B81063CF49A349`.
