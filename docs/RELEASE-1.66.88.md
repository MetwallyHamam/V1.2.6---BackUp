# Millensys Support Hub 1.66.88

## Highlights

- Adds a dedicated contract lifecycle board with date-aware lanes for active, expiring within 60 days, renewing, renewed, expired, and inactive contracts.
- Supports manager drag-and-drop lifecycle actions and concise card actions while preserving governed status transitions.
- Synchronizes client contract-service availability from all of the client's contracts instead of treating one expired contract as the whole client relationship.
- Resolves ticket entitlement against the selected client, product, and contract; tickets against expired or inactive product coverage require approval.
- Adds reusable visit types and contract visit entitlements for annual, urgent, and other governed visit allowances.
- Aligns visit consumption and availability with the client's operational visit cycle and the exact contract/product entitlement.
- Improves contract, SLA, renewal, expiry, and visit visibility without adding a long multi-step workflow.

## Business Rules

- A client remains contract-active while at least one qualifying contract is active.
- An expired contract does not automatically disable a client that has another active contract.
- Ticket creation for a product whose applicable contract is expired or inactive is routed through approval rather than silently granting coverage.
- Reactivating or renewing qualifying coverage restores the calculated client contract-service status.
- Visit usage is evaluated by visit type, contract, product scope, allowance, and operational cycle.

## Database

- Database revision: `0236_client_contract_status`.
- Apply migrations before starting the upgraded application.

## Deployment

- Self-contained Windows x64 backend runtime; no server-side Python installation is required.
- Review and merge `backend/web_1.66.88.config` without overwriting the active server configuration.
- Complete backend and frontend release quality gates run during packaging.
