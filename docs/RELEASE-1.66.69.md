# SupportHub 1.66.69 — Manual organization hierarchy

Release date: 2026-09-25

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Organization hierarchy

- Replaces the department-based hierarchy presentation with an independent manual organization chart.
- Allows authorized administrators to create executives, managers, teams, team members, and custom roles without using User Setup or department relationships.
- Supports custom names, positions, parent relationships, portraits, contact details, notes, active status, and display order.
- Protects the chart from self-parenting and hierarchy cycles and prevents deletion while child nodes remain.
- Records create, update, and delete actions in the audit trail.

## User experience

- Presents each person with a large circular portrait floating above a modern gradient card.
- Shows the position prominently with the person or team name beneath it.
- Gives team nodes a distinct group-icon treatment.
- Includes search, responsive horizontal navigation, connecting hierarchy lines, and theme-aware styling.
- Keeps the published view read-only while exposing add, edit, and delete actions in configuration mode.

## Deployment

- Advances the database revision to `0232_manual_org_chart`.
- Back up the production database and configuration before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.69.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify manual node creation, editing, parent selection, cycle protection, portrait cards, team cards, and the read-only hierarchy view.

## Verification

- The standalone release pipeline runs backend lint, strict type checking, the complete backend test suite, frontend lint and tests, TypeScript compilation, production build, and Windows runtime packaging.
- All release gates passed: 448 backend tests and 86 frontend tests completed successfully.
- Artifact: `releases/SupportHub-1.66.69.zip` (52,807,675 bytes; 1,971 entries).
- SHA-256: `31E6DD6F851BDA892D0691FA109EC022BE1C2FA7908E67D0065D74E388F1829A`.
