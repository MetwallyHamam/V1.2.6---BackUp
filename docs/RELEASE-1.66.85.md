# SupportHub 1.66.85 - Checklist client lookup fix

Release date: 2026-09-28

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Client checklist assignments

- Fixes the `422 VALIDATION_ERROR` caused by requesting 500 clients from an endpoint capped at 200.
- Loads the complete client list through the paginated client-search API in supported 200-row batches.
- Includes inactive clients so existing checklist plans display the client name instead of a `Client #ID` fallback.
- Keeps bulk client assignment, engineer transfer, and Excel import/export behavior from 1.66.84.

## Deployment

- Database revision remains `0234_simple_checklist_rows`; no migration is required.
- Deploy the packaged frontend and backend together.

## Verification

- Frontend lint, TypeScript compilation, and production bundling pass.
- Full release validation and packaged-runtime inspection are executed by the self-contained release builder.
