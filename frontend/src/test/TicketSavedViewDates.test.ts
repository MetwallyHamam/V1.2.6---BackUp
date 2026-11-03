import { describe, expect, it } from "vitest";

import { resolveSavedViewDates } from "../pages/TicketsPage";

describe("ticket saved-view date periods", () => {
  it("recalculates a relative Today view when it is opened on a later day", () => {
    const result = resolveSavedViewDates(
      {
        created_from: "2026-09-13",
        created_to: "2026-09-13",
        __date_type: "created",
        __date_preset: "today",
      },
      "2026-09-14",
    );

    expect(result.dateType).toBe("created");
    expect(result.datePreset).toBe("today");
    expect(result.filters.created_from).toBe("2026-09-14");
    expect(result.filters.created_to).toBe("2026-09-14");
    expect(result.filters).not.toHaveProperty("__date_type");
    expect(result.filters).not.toHaveProperty("__date_preset");
  });

  it("treats legacy absolute dates as Custom instead of falsely labelling them Today", () => {
    const result = resolveSavedViewDates(
      { resolved_from: "2026-09-01", resolved_to: "2026-09-13" },
      "2026-09-14",
    );

    expect(result.dateType).toBe("resolved");
    expect(result.datePreset).toBe("custom");
    expect(result.filters.resolved_from).toBe("2026-09-01");
    expect(result.filters.resolved_to).toBe("2026-09-13");
  });
});
