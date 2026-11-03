# Ticket Queue, Filters, and Views

The ticket queue is server-paginated and returns its total through `X-Total-Count`. It supports controlled sorting and filters for status, priority, client, branch, requester, assignee/team, type, product/module, environment, service, category/subcategory, entitlement, SLA state, and created/updated/resolved dates.

The queue opens with a compact filter toolbar instead of the full filter grid.
Users add only the filters they need, remove them individually, or clear the
complete set. URL filters and saved/default views automatically restore their
corresponding controls, while the My Tickets and My Team Tickets shortcuts remain
available for one-click scoping. Status, Engineer (when permitted), Created from,
and Created to are the compact controls shown by default; their values remain
empty until selected.

`POST /api/v1/tickets/advanced-search` accepts a validated nested AND/OR tree. Only registered fields and operators are compiled to SQLAlchemy expressions; raw SQL is never accepted. Every advanced result begins with the caller's object-level visibility query.

Saved views retain filters, visible columns, and sort order. Views can be private,
shared with an authorized support team, or global (administrators only). Team
visibility is derived from active team leadership/membership on the backend. A
user's default view is restored on the ticket page. The column chooser always
requires at least one visible column.

Task and checklist endpoints enforce ticket visibility, active assignees, audit
creation and state changes, update ticket activity/version, and retain the user
and time of completion. Bulk assignment validates every selected ticket and the
target team/engineer, records correlated audit events, and creates assignment
notifications.
