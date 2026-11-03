# SupportHub 1.66.36 — Operations Home and Mobile Quick Actions

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Adds the lightweight Support Operations Home as the default landing page for all users.
- Adds responsive operational cards, workload bars, queue pulse, and priority-focused attention rows without additional dashboard queries.
- Adds a permission-aware Quick Actions launcher for desktop and mobile: Create Ticket, Create Pre-Ticket, Request Field Visit, and Support Assistant.
- Adds self-assigned field-visit requests with Date from/Date to, client, notes, team-leader approval, an engineer-owned visit list, and document upload.
- Recomputes relative saved-view date presets when opened so `Today` always means the current day.
- Raises the ordinary API timeout to 30 seconds and provides clearer timeout/gateway messages with correlation references.

## Database

- Advances the database head to `0205_self_field_visit`.
- Adds the `visit.field.create.self` permission. Assign it only to engineer profiles that may request their own field visits.

## Deployment

Deploy frontend and backend together. Back up SQL Server, run the packaged migration command, assign the new permission to the intended profiles, switch both IIS paths, recycle the application pool, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 78 tests, TypeScript compilation, and production build passed.
- Runtime commands, manifest version `1.66.36`, database head `0205_self_field_visit`, ZIP readability, and forbidden-file inspection passed (1,840 entries).
- Initial artifact: `releases/SupportHub-1.66.36.zip` (43,371,836 bytes), SHA-256 `8E7559BCD917026BEB239A4852D4F21937D2E34038A85FF315B914EF30C357B7`.
