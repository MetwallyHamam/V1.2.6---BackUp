import { describe, expect, it } from "vitest";

import { showsResolutionWorkspace } from "../pages/TicketDetailPage";

describe("ticket resolution workspace visibility", () => {
  it("always shows the complete workspace for an explicit close", () => {
    expect(showsResolutionWorkspace("CLOSED", true)).toBe(true);
    expect(showsResolutionWorkspace("CLOSED", false)).toBe(true);
  });

  it("shows it at resolve when requirements are collected during resolution", () => {
    expect(showsResolutionWorkspace("RESOLVED", false)).toBe(true);
    expect(showsResolutionWorkspace("RESOLVED", true)).toBe(false);
  });

  it("does not show it for unrelated transitions", () => {
    expect(showsResolutionWorkspace("IN_PROGRESS", true)).toBe(false);
  });
});
