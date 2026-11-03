# SupportHub 1.66.68 — Department hierarchy workspace

Release date: 2026-09-24

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Department hierarchy

- Adds the dedicated organization hierarchy workspace with tree and configuration views.
- Supports parent-department and department-head assignments with effective dates.
- Supports historical **As of** views, hierarchy search, vacancy indicators, and department paths.
- Allows administrators to stage multiple hierarchy changes and publish them atomically.
- Protects the organization structure from self-parenting, cycles, missing parents, and overlapping effective periods.
- Preserves governed organization history, authorization checks, and audit evidence.

## Deployment

- Database compatibility revision remains at the current migration head; no new schema migration is introduced by this release.
- Back up the production database and configuration before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.68.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify the organization tree, hierarchy configuration, effective-date lookup, vacancy display, and multi-change publishing.

## Verification

- The standalone release pipeline runs backend lint, strict type checking, and the complete backend test suite.
- The pipeline also runs frontend lint, all frontend tests, TypeScript compilation, production build, and Windows runtime packaging.
- All release gates passed: 447 backend tests and 86 frontend tests completed successfully.
- Artifact: `releases/SupportHub-1.66.68.zip` (52,798,177 bytes; 1,970 entries).
- SHA-256: `31FDA343E3CDEFABF25D13A07C6229FCA85E1CF82B95DCB389001AF18A09731A`.
