import { describe, expect, it } from "vitest";
import { currentMonthToDate } from "../utils/dateRange";
import { selectTopSupportAgents } from "../utils/dashboardAgents";

describe("dashboard default period", () => {
  it("uses the current local calendar month through today", () => {
    expect(currentMonthToDate(new Date(2026, 7, 29, 23, 45))).toEqual({
      dateFrom: "2026-08-01",
      dateTo: "2026-08-29",
    });
  });

  it("limits the trophy leaderboard to Support users with period tickets", () => {
    const rows = [
      { agent: "Support winner", department: "Support", assigned: 9 },
      { agent: "HR user", department: "HR", assigned: 12 },
      { agent: "Support inactive", department: "Support", assigned: 0 },
      { agent: "Support second", department: " support ", assigned: 4 },
    ];
    expect(selectTopSupportAgents(rows).map((row) => row.agent)).toEqual([
      "Support winner",
      "Support second",
    ]);
  });
});
