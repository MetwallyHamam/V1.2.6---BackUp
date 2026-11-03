# SupportHub 1.66.28 — Ticket Templates and Cards Workflow

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Moving an active ticket into the Closed Cards lane now opens the complete inline resolution workflow and resolves plus closes atomically.
- The Closed destination omits the redundant close-after-resolution checkbox.
- Cards quick preview now clears the fixed header and displays resolution SLA target, actual time, balance, state, and matching evidence.
- Ticket context menus provide Task, Worklog, Checklist, related-ticket, Knowledge Base, and create-template actions; applicable actions are also available in Support Assistant.
- Ticket and Pre-Ticket creation provide automatic keyword-ranked reusable-ticket and governed-template suggestions.
- Resolution provides published Knowledge Base suggestions that can prefill editable resolution text.
- Authorized users can save an existing ticket as a reusable template with Global, Client, Product, or Module scope and optional Client Portal visibility.
- Templates exclude requester, SLA state, comments, worklogs, attachments, and audit history.

## Database

- Database head advances to `0199_ticket_templates`; run the packaged migration before starting the application.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 396 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript compilation, and the production build passed.
- The packaged backend runtime command passed.
- ZIP integrity, required entries, and forbidden generated-file inspection passed (1,811 entries).
