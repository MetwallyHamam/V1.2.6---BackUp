# SupportHub 1.66.31 — Management Map and Realtime Reliability

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

This release replaces withdrawn source-only package `1.66.30` and must be used for deployment.

## Highlights

- Modernizes the Top Management world map with a responsive heat-map presentation, country hover highlighting, actual linked-client names, keyboard focus support, and country drill-down behavior.
- Corrects notification WebSocket authentication in the production multi-worker deployment by using short-lived signed tickets that every backend worker can validate.
- Modernizes the shared HTML email presentation used for Support Hub notifications.
- Separates ticket templates from similar-ticket lookup in Ticket and Pre-Ticket creation. A normal subject shows matching templates; a trailing `*` requests similar tickets and is removed before submission.
- Adds permission-controlled ticket-template editing and soft deletion.
- Groups the Tickets and Support Assistant fast-action menus and adds Open WhatsApp for tickets with a usable client contact number.

## Security

- The strict Content Security Policy remains unchanged; unapproved Segment, advertising, and extension-injected scripts remain blocked.
- WebSocket tickets expire after 30 seconds and are signed with the configured application secret.

## Database

- Database head remains `0199_ticket_templates`; no new migration is required.
- Run the packaged seed command during deployment.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 397 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and the production build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, database head, deployment mode, required contents, ZIP integrity, and forbidden-file inspection passed.
- Final artifact details are recorded in `RELEASE_STEPS.md`.
