# UAT operations

The internal UAT portfolio is available from **Service Management → UAT**. It consolidates active and historical cycles, client/release/coordinator filters, due-state and attention filters, completion/pass metrics, open defects, sign-off state, and the next recommended action.

## Governed execution flow

1. Create a cycle from governed test cases/templates and assign internal engineers, coordinators, and client testers.
2. Publish the cycle and configure its client access window and allowed portal actions.
3. Activate the cycle. Assigned portal testers see it under **Active UAT**; unrelated portal users cannot discover it.
4. Record Pass, Fail, or Blocked with the required explanation and evidence.
5. For a failure, use **Create defect ticket**. The generated ticket subject and description preserve the release, cycle, test, attempt, failure, severity, and client-safe evidence context.
6. Assignment or active ticket work moves the UAT test to **Fix in progress**. Ticket resolution moves it to **Ready for retest**. A failed retest returns it to **Waiting fix**; a passed retest completes the test and notifies ticket owners that closure is ready.

UAT defect tickets are governed system-generated records. They use the cycle/test product context when available and are not blocked by interactive-only ticket-form requirements such as Caller, which the UAT defect action does not collect.

## Sign-off readiness

The sign-off panel checks mandatory completion, failed tests, blocked tests, open linked defects, required evidence, and 100% completion. It links each failure to the affected test or ticket and also warns about unpublished/expired portal access, missing testers, disabled result actions, and invalid approvers. Sign-off remains disabled while a blocking condition exists.

## Release-gate evidence

Migration `0282_uat_defect_links` adds the structured one-ticket-per-test link and backfills legacy `linked_ticket_id` values. On 2026-11-21, the local IIS workflow passed against `http://localhost/SupportHub`: portfolio, portal Active UAT, failure, ticket creation/discovery, assignment, resolution, and retest. Evidence: cycle `UAT-IIS-20261121182546`, ticket `INC-2026-021555`.