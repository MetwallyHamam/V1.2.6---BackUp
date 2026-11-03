import { describe, expect, it } from "vitest";

import {
  resolveTicketListColumns,
  resolveTicketViewMode,
} from "../pages/TicketsPage";

describe("ticket workflow tab layouts", () => {
  it.each(["escalations", "handovers", "approvals", "trash"] as const)(
    "forces %s into the list layout",
    (tab) => {
      expect(resolveTicketViewMode("CARDS", tab)).toBe("GRID");
    },
  );

  it("preserves the selected layout for regular tickets", () => {
    expect(resolveTicketViewMode("CARDS", "all")).toBe("CARDS");
  });

  it("leaves pre-tickets on its dedicated page layout", () => {
    expect(resolveTicketViewMode("CARDS", "pre-tickets")).toBe("CARDS");
  });

  it("uses workflow-specific columns instead of the saved ticket columns", () => {
    expect(resolveTicketListColumns(["description"], "escalations")).toEqual([
      "ticket_number",
      "subject",
      "client",
      "priority",
      "status",
      "department",
      "assigned_engineer",
      "escalation_engineer",
      "updated_at",
    ]);
    expect(resolveTicketListColumns(["description"], "trash")).toContain(
      "archived_at",
    );
  });

  it("preserves saved columns only for regular tickets", () => {
    expect(resolveTicketListColumns(["description"], "all")).toEqual([
      "description",
    ]);
  });
});
