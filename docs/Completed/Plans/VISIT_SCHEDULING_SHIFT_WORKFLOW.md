# Visit Scheduling and Shift Workflow

Status: Implemented

## Purpose

Visit scheduling provisions the engineer's visit coverage instead of requiring a separately prepared shift.

## Behavior

### Engineer has no same-day shift

- The visit is scheduled normally.
- The system creates an approved **Outdoor / field visit** shift matching the visit start and end.
- The generated shift is linked through its audit evidence to the visit occurrence and selected engineer.

### Engineer already has a same-day shift

- Scheduling pauses and opens an in-system decision dialog.
- The dialog displays the existing shift number, time, and status.
- The scheduler can keep the existing shift and add the visit shift.
- An authorized scheduler can transfer the selected existing shift to another active engineer and create the visit shift for the original engineer.
- A reason of at least five characters is mandatory for either decision.

### Transfer controls

- Shift transfer requires `shift.assign_employee` or `shift.manage`.
- The replacement engineer must be active and must not have an overlapping shift.
- The transfer and generated visit shift are recorded separately in the audit log.

## Remaining planner protections

- Visit outside its entitlement occurrence window.
- Another assigned visit overlaps the requested time.
- Engineer is on leave.
- Engineer department does not match the entitlement department.

These conflicts still require correction or an authorized visit-conflict override. Missing shift coverage is no longer a blocking conflict.
