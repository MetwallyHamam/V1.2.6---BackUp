# Millensys Support Hub 1.66.91

## Three-character ticket-template discovery

- Starts approved ticket-template suggestions after three characters so short technical terms such as `HL7` can match one or more templates.
- Applies the same threshold to normal ticket creation and Pre-Ticket creation.
- Accepts three-character similar-ticket searches and ranks direct partial subject matches correctly.
- Keeps the existing five-character minimum for the final ticket subject; only discovery behavior changes.

## Support Assistant

- Stops the Operations tab counter from sending `assistant_module=ops` to the ticket API, eliminating the invalid-data message when users open Support Assistant with Operations access.
- Keeps Operations on its dedicated operational data source rather than treating it as a ticket queue.

## Database and deployment

- Database compatibility remains at `0237_escalation_work_queue`; no migration is introduced.
- Deploy the packaged frontend and backend together.
- Run `backend/runtime/SupportHubBackend.exe migrate` before starting the upgraded application.
