# Client Portal

The client portal is a separate, simplified experience for identities with the
`CLIENT_PORTAL` profile.

Capabilities:

- Portal dashboard and request count
- Create incident or service-request tickets
- View only tickets in assigned client/branch scopes
- Add public replies
- View public conversation only
- Confirm a resolution
- Reopen with a mandatory reason
- Empty announcement feed ready for the later notification module

Security boundaries:

- Portal APIs require a `CLIENT_PORTAL` identity.
- Client and branch scopes are checked server-side for every ticket.
- Ticket creation cannot target another client or unauthorized branch.
- Internal notes are filtered in the query and never serialized.
- Internal assignee/team fields are absent from portal response schemas.
- Guessed cross-client identifiers return `403`.
- Portal users may create only incidents and service requests.

Portal endpoints use the `/api/v1/portal` prefix.

