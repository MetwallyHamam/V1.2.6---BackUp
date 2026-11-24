import { describe, expect, it } from "vitest";

import {
  DEFAULT_STATUS_LANE_CODES,
  PENDING_BOARD_LANE_KEY,
  defaultStatusLaneRank,
  ticketStatusLaneId,
} from "../pages/TicketsPage";
import { resolveTicketsNavigationPath } from "../utils/ticketNavigation";

describe("Tickets navigation date filter", () => {
  it("keeps today's filter when Tickets is clicked again", () => {
    expect(resolveTicketsNavigationPath("/tickets", "")).toBe("/tickets");
  });

  it("returns to today from all time or another ticket route", () => {
    expect(resolveTicketsNavigationPath("/tickets", "?period=all")).toBe(
      "/tickets",
    );
    expect(resolveTicketsNavigationPath("/tickets/42", "")).toBe("/tickets");
  });
});

describe("ticket status board lane", () => {
  const statuses = [
    { id: 1, code: "ASSIGNED" },
    { id: 2, code: "IN_PROGRESS" },
    { id: 3, code: "PENDING_CLIENT" },
    { id: 4, code: "PENDING_INTERNAL" },
  ];

  it("groups client-pending work in the unified pending lane", () => {
    expect(
      ticketStatusLaneId(
        { status_id: 3, progress_started_at: "2026-10-23T10:00:00Z" },
        statuses,
      ),
    ).toBe(PENDING_BOARD_LANE_KEY);
  });

  it("groups internal-pending work in the unified pending lane", () => {
    expect(
      ticketStatusLaneId(
        { status_id: 4, progress_started_at: "2026-10-23T10:00:00Z" },
        statuses,
      ),
    ).toBe(PENDING_BOARD_LANE_KEY);
  });

  it("keeps an assigned ticket in Assigned even when it was started before", () => {
    expect(
      ticketStatusLaneId(
        { status_id: 1, progress_started_at: "2026-10-23T10:00:00Z" },
        statuses,
      ),
    ).toBe(1);
  });
});

describe("default ticket lane order", () => {
  it("uses the requested operational lane sequence", () => {
    expect(DEFAULT_STATUS_LANE_CODES).toEqual([
      "NEW",
      "ASSIGNED",
      "IN_PROGRESS",
      "RESOLVED",
      "CLOSED",
      "PENDING",
    ]);
    expect(defaultStatusLaneRank("PENDING")).toBeGreaterThan(
      defaultStatusLaneRank("CLOSED"),
    );
  });
});
