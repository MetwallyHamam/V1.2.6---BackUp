import { describe, expect, it } from "vitest";
import { dashboardCardDrilldownFilters } from "../pages/DashboardPage";

describe("dashboard card drill-down mappings", () => {
  it.each([
    ["total_open", { open_only: "true" }],
    ["my_open", { assigned_user_id: "17", open_only: "true" }],
    ["unassigned", { strictly_unassigned_only: "true", open_only: "true" }],
    ["critical", { priority: "P1", open_only: "true" }],
    ["breached", { breached_only: "true" }],
    ["due_soon", { due_soon: "true" }],
    ["shift_handovers", { shift_handover_only: "true" }],
  ] as const)("maps %s to its matching ticket filters", (key, expected) => {
    expect(dashboardCardDrilldownFilters(key, 17)).toEqual(expected);
  });
});
