# SupportHub 1.66.30 — Management Map and Realtime Reliability

Status: **RELEASE VERIFICATION AND PACKAGING IN PROGRESS**

## Highlights

- Modernizes the Top Management world map with a responsive heat-map presentation, country hover highlighting, actual linked-client names, keyboard focus support, and existing country drill-down behavior.
- Corrects notification WebSocket authentication in the production multi-worker deployment by using short-lived signed tickets that every backend worker can validate.
- Modernizes the shared HTML email presentation used for Support Hub notifications.
- Separates ticket templates from similar-ticket lookup in Ticket and Pre-Ticket creation. A normal subject shows matching templates; a trailing `*` requests similar tickets and is removed before submission.
- Adds permission-controlled ticket-template editing and soft deletion.
- Groups the Tickets and Support Assistant fast-action menus and adds Open WhatsApp for tickets with a usable client contact number.

## Security

- The application Content Security Policy remains strict. Unapproved Segment, advertising, or extension-injected scripts are not permitted.
- WebSocket tickets expire after 30 seconds and are signed with the configured application secret.

## Database

- Database head remains `0199_ticket_templates`; no new migration is required.
- Run the packaged seed command during deployment so permission and reference-data registrations remain current.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

Release gates and final artifact details are recorded in `RELEASE_STEPS.md`.
