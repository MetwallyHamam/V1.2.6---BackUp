import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { HomePage } from "../pages/HomePage";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    hasPermission: (permission: string) =>
      permission === "dashboard.online_engineers.view",
    user: null,
  }),
}));

vi.mock("../api/client", () => ({
  api: {
    get: vi.fn().mockImplementation((url: string) =>
      Promise.resolve({
        data:
          url === "/dashboards/online-engineers"
            ? [
                {
                  user_id: 9,
                  engineer: "Mona Engineer",
                  department: "Support L2",
                  status: "AVAILABLE",
                  active_ticket_count: 0,
                },
              ]
            : {
                generated_at: "2026-09-14T11:00:00+03:00",
                today: "2026-09-14",
                cache_seconds: 30,
                capabilities: { internal_operations: true },
                tickets: {
                  total: 20,
                  open: 8,
                  in_progress: 4,
                  unassigned: 2,
                  needs_attention: 3,
                  created_today: 5,
                  pending_approval: 2,
                  pending: 2,
                },
                operations: {
                  online_engineers: 6,
                  active_shifts: 4,
                  active_operations: 2,
                  blocked_operations: 1,
                },
                attention: [
                  {
                    id: 7,
                    ticket_number: "T-0007",
                    subject: "Critical scanner",
                    priority: "P1",
                    status: "IN_PROGRESS",
                    client: "Hospital",
                    assigned: true,
                    last_activity_at: "2026-09-14T10:00:00+03:00",
                  },
                ],
              },
      }),
    ),
  },
}));

test("renders the lightweight operational snapshot and current-day drill-down", async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Support Operations")).toBeInTheDocument();
  expect(screen.getByText("Mon, September 14")).toBeInTheDocument();
  expect(await screen.findByText("Mona Engineer")).toBeInTheDocument();
  expect(screen.getByText("Mona Engineer").closest("a")).toHaveAttribute(
    "href",
    "/tickets?assigned_user_id=9&open_only=true",
  );
  expect(screen.queryByText("Critical scanner")).not.toBeInTheDocument();
  expect(screen.getByText("Need attention").closest("a")).toHaveAttribute(
    "href",
    "/tickets?needs_attention=true",
  );
  expect(screen.getByText("Waiting for approval").closest("a")).toHaveAttribute(
    "href",
    "/tickets?entitlement_status=PENDING_APPROVAL",
  );
  expect(screen.getByText("Pending tickets").closest("a")).toHaveAttribute(
    "href",
    "/tickets?status_code=PENDING_CLIENT%2CPENDING_INTERNAL%2CPENDING_VENDOR",
  );
  expect(
    screen.queryByText("Tickets needing attention"),
  ).not.toBeInTheDocument();
  expect(screen.getByText("Created today").closest("a")).toHaveAttribute(
    "href",
    "/tickets?created_from=2026-09-14&created_to=2026-09-14",
  );
});
