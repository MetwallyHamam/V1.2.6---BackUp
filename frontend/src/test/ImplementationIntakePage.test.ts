import { describe, expect, it } from "vitest";
import { filterIntakeRequests } from "../pages/ImplementationIntakePage";

const request = (id: number, status: string) => ({
  id,
  project_id: id,
  project_number: `PRJ-${id}`,
  project_name: `Project ${id}`,
  project_status: "AWAITING_IMPLEMENTATION_ACCEPTANCE",
  priority: "NORMAL",
  requested_department_id: 7,
  requested_team_id: null,
  requested_start_date: null,
  requested_end_date: null,
  capability_notes: null,
  status,
  row_version: 1,
  response_notes: null,
  created_at: "2026-11-24T10:00:00Z",
});

describe("ImplementationIntakePage", () => {
  it("keeps the department inbox filter explicit and supports an all view", () => {
    const rows = [request(1, "PENDING"), request(2, "ACCEPTED")];
    expect(filterIntakeRequests(rows, "PENDING").map((row) => row.id)).toEqual([1]);
    expect(filterIntakeRequests(rows, "ALL").map((row) => row.id)).toEqual([1, 2]);
  });
});
