# Department Collaboration Stop Point — 2026-08-22

Status: DONE

## Extension — Multi-department clients and escalation workspace

Status: DONE

### Agreed rules

- A client has one primary owner department and may be shared with multiple additional departments.
- Client sharing is stored as normalized department links and is managed with a multi-select.
- Sharing a client does not expose every Support ticket to every shared department.
- An explicit help request/escalation grants the receiving department access to its linked departmental work item while Support retains the parent ticket and workflow ownership.
- During active collaboration, both the sending department and receiving department can see their linked ticket records and updates.
- Permissions remain generic (`ticket.view.department`, `ticket.help.request`, and `ticket.help.return`) and are evaluated against department membership. New permission codes are not generated for each department.
- Creating a department automatically provisions department-scoped escalation Saved Views using the existing Saved View engine.

### Delivery checklist

- [x] Add primary-owner plus normalized multi-department client sharing model.
- [x] Add multi-select department sharing to client onboarding.
- [x] Preserve explicit ticket escalation as the ticket-security boundary.
- [x] Automatically provision Received, New, In Progress, Sent, and Returned department queues when creating a department.
- [x] Add an Escalations tab with Received, Sent, and Returned sub-tabs to Tickets.
- [x] Complete migration, backend regression, TypeScript, and production-build verification.

## Completed scope

- Controlled cross-department help requests keep the original Support ticket owner and create a linked departmental work item.
- Requests can target an active department, an optional department-owned team, and an optional eligible team engineer.
- Routed department members receive scoped ticket visibility; request and return actions use separate permissions.
- The ticket page now provides department/team/engineer selection, routing-state presentation, result return, and returned-result presentation.
- Notifications and audit records cover both request and return events.
- Regression coverage verifies linkage, routing fields, returned results, notifications, and audit evidence.
- Support parent tickets display every linked department request and its returned result.
- Ticket filtering supports routed department/team, routing status, department work, team work, and escalations sent while still starting from the authoritative visibility query.
- Users can install seven standard private department queues through the existing Saved View engine; installation is idempotent.
- Department-scoped Saved Views can be shared by authorized department users.
- Profile Dashboard configuration now exposes the previously omitted live-ticket widgets plus New, In Progress, and Returned department-request widgets.
- Support-skill create/update compatibility was restored after department ownership was added to the shared support-catalog schema.

## Validation

- Full backend suite: passed.
- Department collaboration, dashboard-widget, standard-queue, and support-team regression checks: passed.
- Ruff checks: passed.
- TypeScript: passed.
- Frontend production build: passed.
- Full backend suite exposed one support-skill compatibility regression; it was corrected and its affected regression test now passes.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Controlled cross-department collaboration, Saved View queues, parent result visibility, routing filters, profile widgets, and regression coverage
Last completed item: Passed the full backend suite and frontend production build with the completed department queue/dashboard workflow
Next planned item: UAT with representative Support, Team Lead, Department Manager, and Management profiles; then release packaging for revision 0113_department_collaboration
Safe to continue from here: YES
Blocking decision(s): Select the next immutable semantic release version before packaging
Database revision: 0115_client_department_sharing

## Follow-up: unified escalation entry point

Status: **Done in source**

- Ticket detail now shows one `Escalate / Request Help` action.
- `Within my department` uses the internal escalation workflow and lists only colleagues in the current user's department.
- `Another department` uses the controlled department-help workflow while Support keeps the original ticket.
- The internal escalation API rejects `OTHER_DEPARTMENT` and cross-department assignees, preventing UI bypass.
============================================================
