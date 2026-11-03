import { describe, expect, it } from "vitest";
import { occurrenceLane } from "../pages/ServiceChecklistBoard";

describe("service checklist operational lanes", () => {
  const now = new Date("2026-09-28T12:00:00+03:00");

  it("uses the API effective lane when it is present", () => {
    expect(
      occurrenceLane(
        {
          effective_lane: "IN_PROGRESS",
          status: "SCHEDULED",
          due_at: "2026-09-30T12:00:00+03:00",
        },
        now,
      ),
    ).toBe("IN_PROGRESS");
  });

  it("derives a visible lane when an older API omits effective_lane", () => {
    expect(
      occurrenceLane(
        {
          effective_lane: "",
          status: "SCHEDULED",
          due_at: "2026-09-30T12:00:00+03:00",
        },
        now,
      ),
    ).toBe("SCHEDULED");
    expect(
      occurrenceLane(
        {
          effective_lane: "",
          status: "COMPLETED",
          due_at: "2026-09-27T12:00:00+03:00",
        },
        now,
      ),
    ).toBe("COMPLETED");
  });
});
