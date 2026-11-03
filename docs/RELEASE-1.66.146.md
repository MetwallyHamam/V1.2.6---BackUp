# Support Hub 1.66.146

Release date: 2026-10-15

## Highlights

- Adds Quarter filtering to KPI History and Comparison.
- Includes submitted and finalized KPI reviews in the governed bulk Excel download.
- Names finalized KPI workbooks with the engineer and quarter instead of the internal review identifier.
- Adds Ticket Type, Product, Module, Reporter / Caller, and Description directly to deployment issue entry.
- Uses the selected client Contact as both the deployment issue reporter and linked-ticket caller.
- Copies the selected Ticket Type, Product, Module, Caller, description, and priority into the linked ticket.
- Validates required linked-ticket fields before creating the deployment issue and ticket.

## Database

- Retains database compatibility at `0268_deployment_links`; no new migration is required.

## Deployment notes

1. Deploy `1.66.146` and allow the startup migration check to confirm `0268_deployment_links`.
2. Retain production configuration and recycle the Support Hub application pool.
3. Create a deployment issue with a linked ticket and confirm Ticket Type, Product, Module, and Caller are copied.
4. Verify KPI History quarter filtering and bulk workbook filenames.
