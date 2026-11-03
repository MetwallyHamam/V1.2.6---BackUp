# Remaining Product Backlog

Last prioritized: 2026-08-28; B-46 is verified in the working tree after corrected release 1.48.1; database head remains `0144_handover_cleanup`

This file is the canonical implementation queue. Full requirements and historical decisions remain in `Notes.md`.

## P1 — High priority

1. **B-41 — Engineer Intake to Call Center Queue**
   - Replace WhatsApp registration requests with a feature-controlled structured intake, dedicated permissions, a Call Center queue, atomic conversion to an official ticket, and measurable submission/claim/conversion timestamps.

## Sequencing notes

- B-36 is implemented and verified in the working tree: IIS/Uvicorn logs remain unchanged, while daily error/exception files use inter-process locking, redaction, retention, compression, and stream fallback. Do not redo it.
- The B-32 notification correction is implemented and verified in the working tree without changing token lifetimes. Do not redo it.
- B-39's confirmed workflow is implemented and verified in the working tree: missing access shows only a compact icon; its dialog can send a normal request or permanently grant the capability to the shared primary profile using authorized approver credentials and full source-action evidence. Do not redo it.
- The unified B-24 communication action registry is implemented; extend it instead of adding page-specific send controls.
- B-34 and B-35 now share the consolidated Contract Workspace; preserve its permission-aware section navigation in later changes.
- B-40 must reuse B-34's compact linked-customer interaction where practical. Its dedicated Project Delivery endpoints must return minimum scoped data and must not reuse general Clients, Contracts, Users, or Operations APIs that would require or expose master-workspace permissions.
- B-40 is implemented and verified in the working tree at database head `0143_project_delivery`; do not redo it.
- B-41 must remain a separate intake domain until conversion, reuse the standard ticket-creation validation transaction, and report intake-to-registration separately from a true Engineer Response KPI.
- B-42 is implemented and verified in the working tree. Shared responsive safeguards and targeted fixes cover Tickets, Saved Views, Complaints, Knowledge Base, Profile Privileges, Master Data, and Data Imports without changing permissions or page state. Do not redo it.
- B-43 is implemented in the working tree: Client Portal training now lives in the existing Knowledge Base tab, the legacy standalone URL redirects safely, and the existing portal publication flag, feed, and permission remain authoritative. Do not recreate a separate portal training page.
- B-44/B-38 are implemented and verified together in the working tree through one explicit Mosaic mode. The portal uses responsive Product → Module → linked Service cards, while server-side catalog scope and relationship validation remain authoritative. Do not create a parallel form or weaken normal portal creation.
- B-45 is implemented and verified in the working tree. Its shared theme-level searchable menu covers MUI form selects, while existing scoped autocomplete/server-loading controls remain authoritative. Do not apply it to action or navigation menus.
- B-46 is implemented and verified in the working tree. It reuses the existing satisfaction record through atomic idempotent submission, derives inline availability server-side without exposing the satisfaction token, shows only generic public escalation evidence, and preserves B-22 polling. Do not broaden its public payload.
- B-29 and B-30 are both implemented and may be bundled as a Clients-page/reporting release.


## Resume marker

Next point: **B-41 — Engineer Intake to Call Center Queue**. Database head: **`0144_handover_cleanup`**. B-44/B-38 and B-46 are verified in the working tree after corrected release 1.48.1. Confirm before continuing.
