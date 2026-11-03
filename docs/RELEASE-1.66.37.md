# SupportHub 1.66.37 — Dashboard Navigation Correction

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Correction

- Restores the existing Dashboard entry in the desktop sidebar for users with `dashboard.agent` or `dashboard.manager`.
- Keeps Support Operations Home as the default post-login page.
- Includes all Home, Quick Actions, field-visit, saved-view date, timeout, and performance changes from `1.66.36`.

## Database

- Database head remains `0205_self_field_visit`. Environments already migrated for `1.66.36` need no additional migration.

## Verification

- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 78 tests, TypeScript compilation, and production build passed.
- Runtime commands, manifest version `1.66.37`, database head `0205_self_field_visit`, ZIP readability, and forbidden-file inspection passed (1,840 entries).
- Initial artifact: `releases/SupportHub-1.66.37.zip` (43,371,782 bytes), SHA-256 `CCCA6BB673DB4B520CE89852CB076D27E982268C1778109B46216FD1F29B652C`.
