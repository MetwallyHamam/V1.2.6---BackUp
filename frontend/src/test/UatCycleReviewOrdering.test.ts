// @vitest-environment jsdom

import { describe, expect, it } from "vitest";
import { availableUatActions, orderUatTests } from "../pages/UatCycleReview";

const tests = [
  { id: 20, display_order: 1, snapshot: { code: "TC-10", title: "Second", priority: "LOW" }, priority: "LOW", due_date: null, workflow_status: "COMPLETED", test_result: "PASS", retest_count: 0, linked_ticket_number: null, owner_user_id: 1 },
  { id: 10, display_order: 2, snapshot: { code: "TC-2", title: "First", priority: "CRITICAL" }, priority: "CRITICAL", due_date: "2026-10-10", workflow_status: "READY", test_result: "NOT_TESTED", retest_count: 0, linked_ticket_number: null, owner_user_id: 1 },
];
const sourceOrder = new Map([[20, 0], [10, 1]]);

describe("UAT workspace ordering", () => {
  it("keeps template sequence as the default order", () => {
    expect(orderUatTests(tests, "template_order", "asc", sourceOrder).map((test) => test.id)).toEqual([20, 10]);
  });

  it("sorts codes naturally and priorities by business importance", () => {
    expect(orderUatTests(tests, "code", "asc", sourceOrder).map((test) => test.id)).toEqual([10, 20]);
    expect(orderUatTests(tests, "priority", "asc", sourceOrder).map((test) => test.id)).toEqual([10, 20]);
  });

  it("exposes only backend-valid next actions", () => {
    const ready = { ...tests[1], workflow_status: "READY" };
    const waiting = { ...tests[1], workflow_status: "WAITING_FIX" };
    expect(availableUatActions(ready, false, 1).map((action) => action.value)).toEqual(["OPEN", "IN_PROGRESS", "PASS", "FAIL", "BLOCKED"]);
    expect(availableUatActions(waiting, false, 1).map((action) => action.value)).toEqual(["OPEN"]);
    expect(availableUatActions({ ...tests[1], workflow_status: "BLOCKED" }, true, 1).map((action) => action.value)).toEqual(["OPEN", "READY"]);
  });
});
