import { describe, expect, it } from "vitest";

import { ticketStatusLaneId } from "../pages/TicketsPage";
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
    { id: 2, code: "IN_PROGRESS" },
    { id: 3, code: "PENDING_CLIENT" },
    { id: 4, code: "PENDING_INTERNAL" },
  ];

  it("keeps client-pending work in its pending lane after progress started", () => {
    expect(
      ticketStatusLaneId(
        { status_id: 3, progress_started_at: "2026-10-23T10:00:00Z" },
        statuses,
      ),
    ).toBe(3);
  });

  it("keeps internal-pending work in its pending lane after progress started", () => {
    expect(
      ticketStatusLaneId(
        { status_id: 4, progress_started_at: "2026-10-23T10:00:00Z" },
        statuses,
      ),
    ).toBe(4);
  });
});
