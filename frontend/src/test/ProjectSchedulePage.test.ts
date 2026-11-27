import { expect, it } from "vitest";
import { forecastVariance } from "../pages/ProjectSchedulePage";

it("compares forecast calendar days to the baseline across datetime formats", () => {
  expect(forecastVariance("2026-12-01 12:30:00", "2026-12-03T08:00:00+02:00")).toBe(2);
  expect(forecastVariance("2026-12-01", "2026-11-30")).toBe(-1);
  expect(forecastVariance("2026-12-01 12:30:00", "2026-12-01T23:00:00+02:00")).toBe(0);
  expect(forecastVariance(undefined, "2026-12-03")).toBeNull();
});
