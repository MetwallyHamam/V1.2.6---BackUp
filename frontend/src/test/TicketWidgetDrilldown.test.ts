import { describe, expect, it } from "vitest";

import {
  dateSelectionFromFilters,
  filtersFromSearchParams,
} from "../pages/TicketsPage";

describe("ticket widget drill-down filters", () => {
  it("preserves the caller filter used by Show contact tickets", () => {
    const filters = filtersFromSearchParams(
      new URLSearchParams("requester_contact_id=42"),
    );

    expect(filters.requester_contact_id).toBe("42");
    expect(filters.created_from).toBe("");
    expect(filters.created_to).toBe("");
  });

  it("replaces unspecified filters instead of retaining the previous view", () => {
    const filters = filtersFromSearchParams(
      new URLSearchParams("priority=P1&open_only=true"),
    );

    expect(filters.priority).toBe("P1");
    expect(filters.open_only).toBe("true");
    expect(filters.client_id).toBe("");
    expect(filters.assigned_user_id).toBe("");
    expect(filters.created_from).toBe("");
    expect(filters.created_to).toBe("");
  });

  it("recognizes an explicit widget date range as a custom period", () => {
    const filters = filtersFromSearchParams(
      new URLSearchParams("created_from=2026-09-01&created_to=2026-09-12"),
    );

    expect(dateSelectionFromFilters(filters)).toEqual({
      dateType: "created",
      datePreset: "custom",
    });
  });
});
