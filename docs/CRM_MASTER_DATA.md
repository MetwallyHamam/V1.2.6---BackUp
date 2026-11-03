# CRM Master Data

The CRM increment adds:

- Client statuses and client organizations
- Branches/sites
- Support contacts
- Products and product modules
- Production, UAT, DR, Training, and Test environments
- Client installation profiles without credential fields
- Service catalog items
- Ticket categories with nested, independently active subcategories
- Support teams, team leaders, multi-team membership, and support skills
- Vendors

All client writes require `client.manage`; contact writes require
`contact.manage`; product and installation writes require
`installation.manage`. Reads are separately protected. Client and branch
changes create audit-log entries, unique codes are enforced in the database,
and branch/contact relationships are validated server-side.

Main endpoints:

- `GET|POST /api/v1/clients`
- `GET|PATCH /api/v1/clients/{client_id}`
- `GET|POST /api/v1/clients/{client_id}/branches`
- `GET|POST /api/v1/contacts`
- `GET|POST /api/v1/products`
- `POST /api/v1/products/{product_id}/modules`
- `GET|POST /api/v1/installations`
- `GET /api/v1/client-statuses`
- `GET /api/v1/environments`
- `GET|POST /api/v1/services`
- `GET|POST /api/v1/ticket-categories`
- `GET|POST /api/v1/ticket-categories/{category_id}/subcategories`
- `GET|POST /api/v1/support-teams`
- `GET|POST /api/v1/skills`
- `GET|POST /api/v1/vendors`
