import { describe, expect, it } from "vitest";
import { localDateValue, projectAnalyticsParams } from "../pages/ProjectAnalyticsPage";

describe("Project Analytics filters", () => {
  it("serializes only active bounded filters", () => {
    expect(
      projectAnalyticsParams({
        period_start: "2026-11-01",
        period_end: "2026-11-30",
        account_id: "4",
        organization_id: "",
        client_id: "9",
        department_id: "",
      }),
    ).toEqual({ period_start: "2026-11-01", period_end: "2026-11-30", account_id: "4", client_id: "9" });
  });

  it("formats local dates without a UTC day shift", () => {
    expect(localDateValue(new Date(2026, 10, 24, 8, 30))).toBe("2026-11-24");
  });
});
