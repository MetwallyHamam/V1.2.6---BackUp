# Visit Completion and Coverage Import Operations

Use the coverage import preview before commit. Correct every invalid contract, catalog code, effective date, or exact-client scope reported by the row results; the CSV error export is the operational handoff for rejected rows. Reusing the same source and idempotency identity is safe and must not create duplicate coverage revisions.

A scheduled visit is started before completion. Completion requires offset-aware actual times, a structured outcome, result notes, and at least one validated, non-rejected current document. Customer acknowledgement records the name and time when supplied. Completion stores an immutable evidence version and consumes the entitlement once; repeated requests cannot consume it again.

Authorized reopen creates compensating entitlement evidence and retains prior completion and document history. Never delete completion evidence to correct a visit. Upload a replacement document, supersede the prior version, and complete under the new optimistic version.

Daily controls:

- Export and resolve failed coverage-import rows before committing a corrected batch.
- Reconcile completed occurrences to completion evidence, current documents, and entitlement ledger entries.
- Investigate rejected or pending document scans and attempted unauthorized downloads.
- Review reopened visits and confirm their compensating ledger entries and reasons.
- Retain documents according to their recorded retention date and approved storage policy.

Before release, run import retry and validation tests, visit race/exact-once tests, document authorization checks, all backend/frontend gates, and clean/populated migration rehearsals through `0103_visit_completion`.
