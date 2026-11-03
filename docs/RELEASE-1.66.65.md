# SupportHub 1.66.65 — SLA hardening and client-dependency controls

Release date: 2026-09-24

Status: **READY FOR CONTROLLED DEPLOYMENT**

## SLA improvements

- Fixes SLA-template creation with an automatically generated code on SQL Server.
- Normalizes manually entered SLA codes and improves validation guidance.
- Adds a transactional standard L1–L4 SLA preset using the selected business calendar.
- Fixes contract SLA-target editing so disabled scope fields retain their priority and context.
- Prevents contract SLA requests from submitting a null priority.
- Seeds governed pause reasons for client infrastructure, client access, customer information, and third-party dependencies.
- Preserves audited pause/resume intervals and business-calendar deadline extension behavior.

## Ticket-creation safeguards

- Retains validation of client, requester, branch, product, module, service, contract and entitlement relationships.
- Retains explicit contract selection where multiple eligible contracts exist.
- Retains pending-approval routing when contractual entitlement is unavailable or restricted.
- Retains SLA-policy and scoped-target resolution before creating contractual clocks.

## Deployment

- Database migration advances to `0231_sla_client_dependency_flags`.
- Back up the production database before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.65.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify normal and standard-preset SLA creation, contract target editing, and governed SLA-pause flags.

## Verification

- The standard standalone release pipeline runs backend lint, strict type checking, and all backend tests.
- The pipeline also runs frontend lint, all frontend tests, TypeScript compilation, production build, and Windows runtime packaging.
