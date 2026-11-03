# Ticket workflow approval matrix

Status: **Approved through Phase 2 resume instruction on 2026-08-05**  
Phase 2 checkpoint: `P2.1.1`

This document becomes the single business specification for ticket status changes. After approval, backend, bulk actions, portal actions, and frontend buttons must derive from the same centralized workflow engine.

## Proposed status meanings

| Status | Meaning | Active work? | Terminal? |
|---|---|---:|---:|
| `NEW` | Created but not yet reviewed or assigned. | No | No |
| `TRIAGED` | Reviewed and classified, awaiting assignment or work. | No | No |
| `ASSIGNED` | Owned by an engineer/team but work has not started. | No | No |
| `IN_PROGRESS` | Engineer is actively working on the ticket. | Yes | No |
| `PENDING_CLIENT` | Waiting for information/action from the customer. | No | No |
| `PENDING_INTERNAL` | Waiting for another internal employee/team. | No | No |
| `PENDING_VENDOR` | Waiting for an external vendor. | No | No |
| `RESOLVED` | A resolution and root cause were supplied; confirmation/closure remains. | No | No |
| `CLIENT_CONFIRMATION` | Waiting for customer confirmation of the resolution. | No | No |
| `CLOSED` | Work is complete and the ticket is locked except for reopening. | No | Yes |
| `CANCELLED` | Ticket was invalid, duplicate, or withdrawn. | No | Yes |
| `REOPENED` | A resolved/closed ticket was reopened and needs reassignment or work. | No | No |

## Proposed transition matrix

| From | Allowed destinations | Required information |
|---|---|---|
| `NEW` | `TRIAGED`, `ASSIGNED`, `IN_PROGRESS`, `PENDING_INTERNAL`, `CANCELLED` | Cancellation/pending requires reason. Assignment requires owner. |
| `TRIAGED` | `ASSIGNED`, `IN_PROGRESS`, `PENDING_INTERNAL`, `CANCELLED` | Cancellation/pending requires reason. Assignment requires owner. |
| `ASSIGNED` | `IN_PROGRESS`, `PENDING_CLIENT`, `PENDING_INTERNAL`, `PENDING_VENDOR`, `RESOLVED`, `CANCELLED` | Pending/cancellation requires reason. Resolution requires resolution and root cause. |
| `IN_PROGRESS` | `PENDING_CLIENT`, `PENDING_INTERNAL`, `PENDING_VENDOR`, `RESOLVED`, `CANCELLED` | Pending/cancellation requires reason. Resolution requires resolution and root cause. |
| `PENDING_CLIENT` | `IN_PROGRESS`, `RESOLVED`, `CANCELLED` | Resolution requires resolution and root cause; cancellation requires reason. |
| `PENDING_INTERNAL` | `IN_PROGRESS`, `RESOLVED`, `CANCELLED` | Resolution requires resolution and root cause; cancellation requires reason. |
| `PENDING_VENDOR` | `IN_PROGRESS`, `RESOLVED`, `CANCELLED` | Resolution requires resolution and root cause; cancellation requires reason. |
| `RESOLVED` | `CLIENT_CONFIRMATION`, `CLOSED`, `REOPENED` | Reopen requires reason. |
| `CLIENT_CONFIRMATION` | `CLOSED`, `REOPENED` | Reopen requires reason. |
| `CLOSED` | `REOPENED` | Reopen requires reason. |
| `CANCELLED` | `REOPENED` | Reopen requires reason. |
| `REOPENED` | `ASSIGNED`, `IN_PROGRESS`, `PENDING_INTERNAL`, `CANCELLED` | Assignment requires owner; pending/cancellation requires reason. |

Direct `NEW`/`TRIAGED → RESOLVED` is intentionally removed: a ticket must have an owner and a recorded work state before resolution. `ASSIGNED → RESOLVED` remains allowed for quick fixes that are completed immediately.

## Proposed action and permission rules

| Action | Permission | Additional rule |
|---|---|---|
| Change ordinary status | `ticket.change.status` | Actor must be allowed to view the ticket. |
| Start work | `ticket.change.status` | “Start progress” changes status to `IN_PROGRESS`. |
| Resolve | `ticket.change.status` + `ticket.resolve` | Resolution summary and root cause are mandatory. |
| Close | `ticket.change.status` + `ticket.close` | Closing after resolution uses the same permission. |
| Reopen | `ticket.change.status` + `ticket.reopen` | Reopen reason is mandatory. |
| Cancel | `ticket.change.status` + proposed `ticket.cancel` | Cancellation reason is mandatory. |
| Assign to me | `ticket.assign.self` | Assigns logged-in user; `NEW`/`TRIAGED` becomes `ASSIGNED`. |
| Assign/reassign another engineer/team | `ticket.assign.team` | Assignee must be active and eligible under site settings. |
| Bulk status change | Same permissions and transition rules as individual changes | Entire request is atomic; one invalid ticket rejects all. |

## Escalation parent/child rule

When an escalation creates a child ticket, closing the child may resolve and close the parent only when:

1. the child is explicitly linked as the parent’s escalation child;
2. no other open escalation child remains;
3. the parent-assigned engineer is recorded as its resolver/closer (falling back to the child closer only when the parent is unassigned), while the actual child closer remains in the audit payload; and
4. both changes are committed atomically and audited.

The parent must not say it was solved by the employee who originally escalated it.

## Implementation gaps recorded at approval time

All gaps below were resolved during P2.1 and are retained as historical review evidence.

1. Backend and frontend contain separate hard-coded transition maps.
2. Backend allows `ASSIGNED → RESOLVED`; frontend currently hides it.
3. Bulk status updates do not call the central transition validation routine.
4. Bulk updates do not enforce the same resolve/close/reopen permissions as individual updates.
5. `CANCELLED` has no dedicated permission and cannot currently be reopened.
6. Pending reasons are not consistently mandatory and there is no follow-up deadline yet.
7. Assignment and status transition can be separate writes, creating inconsistent intermediate states.
8. UI exposes both shortcut buttons and a generic status dialog from its own transition list.

## Approval record

The resumed implementation adopts:

- the proposed transition matrix;
- whether cancelled tickets may be reopened;
- whether direct `NEW`/`TRIAGED → RESOLVED` is prohibited;
- the dedicated `ticket.cancel` permission; and
- the escalation parent/child closure rule.

This specification is the acceptance source for `P2.1.2–P2.1.9`. Requested business-rule changes must update this file and the centralized workflow tests together.
