# SupportHub 1.66.61 — Contract ticket policy

Release date: 2026-09-23

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Contract and ticket improvements

- Adds per-contract entitlement validation levels: contract, product, product and module, or full scope.
- Makes product coverage the default ticket entitlement rule without requiring service validation.
- Adds configurable post-expiry grace days and an optional approval group per contract.
- Preserves ticket requests after grace, out-of-scope, or inactive-client validation by routing them to Pending Approval instead of blocking creation.
- Allows active covered contracts without SLA to create normal tickets without starting SLA clocks.
- Adds the same policy fields to reusable contract templates and template application flows.
- Preserves legacy ticket creation with a `NO_CONTRACT` entitlement when no contract exists.

## Deployment

- Database migration: `0227_contract_ticket_policy`.
- Back up the production database before deployment.
- Deploy the packaged frontend and backend together; do not combine them with an older release.
- Preserve production settings when activating `backend/web_1.66.61.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify active non-SLA contracts, grace-period tickets, expired-contract approvals, and contract-template reuse after deployment.

## Verification

- Backend Ruff, strict MyPy, the complete backend test suite, and a clean migration through `0227_contract_ticket_policy` passed.
- Frontend ESLint, TypeScript compilation, all 86 Vitest tests, and the production build passed.
