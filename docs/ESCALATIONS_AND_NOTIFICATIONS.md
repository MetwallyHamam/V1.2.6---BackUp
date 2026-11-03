# Escalations and Notifications

Implemented foundations:

- Configurable SLA clock/threshold escalation rules
- Default 50%, 75%, and 100% first-response rules
- Default 75% and 100% resolution rules
- Unique clock/rule constraint preventing duplicate escalation events
- Notification records with severity, deep link, read state, and deduplication key
- Transactional outbox records created with escalation events
- Assignee and support-manager recipient selection
- Manual authorized evaluation endpoint, ready to be invoked by a durable scheduler
- Configurable in-process evaluation scheduler with run locking and administrator status visibility
- Notification center and escalation administration screens
- Authenticated WebSocket notification-count updates using one-time, 30-second
  connection tickets; the UI reconnects automatically and retains polling as a fallback
- Per-user browser sound preferences, including a user-initiated test tone and
  automatic tones when the live unread count increases

The SQL database remains the source of truth. Redis fan-out across multiple application
instances, email workers, retries, quiet hours, desktop push notifications, and an external
distributed scheduler are the next operational layer. The bundled scheduler requires
one application worker and is suitable for the current single-instance deployment.
