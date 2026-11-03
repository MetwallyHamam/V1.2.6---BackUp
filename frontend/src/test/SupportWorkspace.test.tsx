import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import "../i18n/config";

const state = vi.hoisted(() => ({
  permissions: new Set<string>(),
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 41 },
    hasPermission: (permission: string) => state.permissions.has(permission),
  }),
}));
vi.mock("../api/client", () => ({
  api: { get: state.get, post: state.post, put: state.put },
}));

import { SupportWorkspacePage } from "../pages/SupportWorkspacePage";

beforeEach(() => {
  state.permissions = new Set();
  state.get.mockReset();
  state.post.mockReset();
  state.put.mockReset();
});

function authMe() {
  return {
    data: { permissions: [...state.permissions] },
    headers: {},
  };
}

function renderWorkspace() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SupportWorkspacePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("a Pre-Ticket-only user opens the available module without loading tickets", async () => {
  state.permissions = new Set([
    "ticket.pre_ticket.create",
    "ticket.pre_ticket.view.own",
    "support_assistant.pre_ticket.view",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : Promise.resolve({
          data: [
            {
              id: 1,
              pre_ticket_number: "PRE-000001",
              title: "RIS workstation",
              proposed_priority: "P2",
              status: "SUBMITTED",
              submitted_at: "2026-09-06T10:00:00Z",
            },
          ],
          headers: {},
        }),
  );
  renderWorkspace();
  expect(await screen.findByText("PRE-000001")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Create ticket" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Create pre-ticket" }),
  ).not.toBeInTheDocument();
  expect(state.get).toHaveBeenCalledWith(
    "/pre-tickets/mine",
    expect.objectContaining({
      params: expect.objectContaining({ unconverted_only: true }),
    }),
  );
  expect(state.get).not.toHaveBeenCalledWith("/tickets", expect.anything());
});

test("an authorized ticket user receives the compact open queue", async () => {
  state.permissions = new Set([
    "ticket.view.team",
    "ticket.create",
    "support_assistant.queue.view",
    "support_assistant.ops.view",
    "internal_operation.view",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [{ id: 1, code: "NEW", name: "New" }],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : url === "/internal-operations"
            ? Promise.resolve({ data: [], headers: {} })
            : Promise.resolve({
                data: [
                  {
                    id: 7,
                    ticket_number: "INC-000007",
                    subject: "Payment callback",
                    client_name: "Millensys",
                    priority: "P1",
                    status_id: 1,
                    version: 3,
                    sla_resolution_target_minutes: 60,
                    sla_actual_business_minutes: 15,
                    updated_at: "2026-09-06T10:00:00Z",
                  },
                ],
                headers: { "x-total-count": "1" },
              }),
  );
  renderWorkspace();
  expect(await screen.findByText("INC-000007")).toBeInTheDocument();
  const opsTab = screen.getByRole("tab", { name: "Ops" });
  expect(opsTab).not.toHaveAttribute("href");
  fireEvent.click(opsTab);
  expect(await screen.findByText("My operations")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: /Queue/ }));
  fireEvent.contextMenu(screen.getByRole("tab", { name: /Queue/ }));
  const tabMenu = screen.getByRole("menu");
  expect(tabMenu).toHaveTextContent("Set as default tab");
  expect(tabMenu).not.toHaveTextContent("Ops");
  fireEvent.click(screen.getByRole("menuitem", { name: "Set as default tab" }));
  expect(
    screen.queryByText(
      "A compact operational workspace using your existing Support Hub access.",
    ),
  ).not.toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "About Support Assistant" }),
  );
  expect(
    screen.getByText(
      "A compact operational workspace using your existing Support Hub access.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Open Support Hub" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Assistant width" }));
  expect(
    screen.getByRole("menuitem", { name: "Compact · 480 px" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("menuitem", { name: "Standard · 760 px" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("menuitem", { name: "Wide · 1080 px" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("menuitem", { name: "Compact · 480 px" }));
  expect(
    screen.getByRole("button", { name: "Expanded mode" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Resize Support Assistant" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Millensys")).toBeInTheDocument();
  expect(screen.getByText("New")).toBeInTheDocument();
  expect(screen.getByText("SLA: 45 min remaining")).toBeInTheDocument();
  expect(
    screen.getByLabelText(
      "INC-000007 draggable ticket card; right-click for actions",
    ),
  ).not.toHaveAttribute("data-sla-alert");
  expect(
    screen.queryByRole("button", { name: "Create ticket" }),
  ).not.toBeInTheDocument();
  fireEvent.contextMenu(
    screen.getByLabelText(
      "INC-000007 draggable ticket card; right-click for actions",
    ),
  );
  expect(
    screen.getByRole("menuitem", { name: "Pin to top" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "More ticket actions" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Open ticket" }),
  ).not.toBeInTheDocument();
  expect(state.get).toHaveBeenCalledWith(
    "/tickets",
    expect.objectContaining({
      params: expect.objectContaining({
        assistant_module: "queue",
        limit: 12,
        sort_by: "created_at",
        sort_direction: "asc",
      }),
    }),
  );
  expect(state.get).not.toHaveBeenCalledWith(
    "/tickets",
    expect.objectContaining({
      params: expect.objectContaining({ assistant_module: "ops" }),
    }),
  );
});

test("shows active SEV1 major incidents without a scheduler", async () => {
  state.permissions = new Set([
    "ticket.view.team",
    "support_assistant.queue.view",
    "major_incident.view",
  ]);
  state.get.mockImplementation((url: string) => {
    if (url === "/auth/me") return Promise.resolve(authMe());
    if (url === "/major-incident-portfolio")
      return Promise.resolve({
        data: [
          {
            id: 9,
            major_incident_number: "MI00000009",
            severity: "SEV1",
            status: "RESPONSE_ACTIVE",
            client_name: "Critical Client",
            subject: "Production outage",
            current_status_summary: "Response active",
          },
        ],
        headers: {},
      });
    if (url === "/ticket-statuses")
      return Promise.resolve({
        data: [{ id: 1, code: "NEW", name: "New" }],
        headers: {},
      });
    if (url === "/tickets/support-assistant/preferences")
      return Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} });
    if (url === "/system/site-settings")
      return Promise.resolve({ data: {}, headers: {} });
    return Promise.resolve({ data: [], headers: { "x-total-count": "0" } });
  });
  renderWorkspace();
  expect(
    await screen.findByText("Active major incidents require attention"),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /MI00000009.*SEV1.*Critical Client/ }),
  ).toBeInTheDocument();
  expect(state.get).toHaveBeenCalledWith("/major-incident-portfolio", {
    params: { limit: 50 },
  });
});

test("marks running tickets past half of their resolution SLA as near breach", async () => {
  state.permissions = new Set([
    "ticket.view.team",
    "support_assistant.queue.view",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [{ id: 1, code: "NEW", name: "New", color: "#2563eb" }],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 8,
                  ticket_number: "INC-000008",
                  subject: "SLA approaching",
                  client_name: "Millensys",
                  priority: "P1",
                  status_id: 1,
                  version: 1,
                  sla_resolution_target_minutes: 60,
                  sla_actual_business_minutes: 31,
                  sla_overrun_minutes: 0,
                  sla_resolution_state: "RUNNING",
                  created_at: "2026-09-07T09:00:00Z",
                  updated_at: "2026-09-07T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "1" },
            }),
  );

  renderWorkspace();

  expect(
    await screen.findByLabelText(
      "INC-000008 draggable ticket card; right-click for actions",
    ),
  ).toHaveAttribute("data-sla-alert", "near-breach");
});

test("marks an overrun ticket as breached without the near-breach state", async () => {
  state.permissions = new Set([
    "ticket.view.team",
    "support_assistant.queue.view",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [{ id: 1, code: "NEW", name: "New", color: "#2563eb" }],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 10,
                  ticket_number: "INC-000010",
                  subject: "SLA breached",
                  client_name: "Millensys",
                  priority: "P1",
                  status_id: 1,
                  version: 1,
                  sla_resolution_target_minutes: 60,
                  sla_actual_business_minutes: 65,
                  sla_overrun_minutes: 5,
                  sla_resolution_state: "RUNNING",
                  created_at: "2026-09-07T09:00:00Z",
                  updated_at: "2026-09-07T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "1" },
            }),
  );

  renderWorkspace();

  expect(
    await screen.findByLabelText(
      "INC-000010 draggable ticket card; right-click for actions",
    ),
  ).toHaveAttribute("data-sla-alert", "breached");
});

test("self assignment calls the existing claim endpoint with optimistic version", async () => {
  state.permissions = new Set([
    "ticket.view.team",
    "ticket.assign.self",
    "support_assistant.queue.view",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [{ id: 1, code: "NEW", name: "New" }],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 9,
                  ticket_number: "INC-000009",
                  subject: "RIS is unavailable",
                  client_name: "Hospital",
                  priority: "P2",
                  status_id: 1,
                  version: 6,
                  updated_at: "2026-09-06T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "1" },
            }),
  );
  state.post.mockResolvedValue({ data: {} });
  renderWorkspace();
  fireEvent.click(await screen.findByRole("button", { name: "Assign to me" }));
  await waitFor(() =>
    expect(state.post).toHaveBeenCalledWith("/tickets/9/claim", { version: 6 }),
  );
});

test("assign and start claims first and transitions with the returned version", async () => {
  state.permissions = new Set([
    "ticket.assign.self",
    "ticket.change.status",
    "ticket.start.progress",
    "support_assistant.queue.view",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [{ id: 1, code: "NEW", name: "New", color: "#123456" }],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 12,
                  ticket_number: "INC-000012",
                  subject: "Queue work",
                  client_name: "Hospital",
                  priority: "P2",
                  status_id: 1,
                  version: 4,
                  updated_at: "2026-09-07T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "1" },
            }),
  );
  state.post.mockImplementation((url: string) =>
    url.endsWith("/claim")
      ? Promise.resolve({ data: { version: 5 } })
      : Promise.resolve({ data: { version: 6 } }),
  );
  renderWorkspace();
  fireEvent.click(
    await screen.findByRole("button", { name: "Assign & start progress" }),
  );
  await waitFor(() => {
    expect(state.post).toHaveBeenNthCalledWith(1, "/tickets/12/claim", {
      version: 4,
    });
    expect(state.post).toHaveBeenNthCalledWith(2, "/tickets/12/transition", {
      to_status_code: "IN_PROGRESS",
      reason: "Work started from Support Assistant",
      version: 5,
    });
  });
});

test("mine cards expose the operational lifecycle actions", async () => {
  state.permissions = new Set([
    "support_assistant.mine.view",
    "ticket.change.status",
    "ticket.start.progress",
    "ticket.resolve",
    "ticket.escalate",
    "ticket.assign.team",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [
              {
                id: 2,
                code: "IN_PROGRESS",
                name: "In progress",
                color: "#008577",
              },
            ],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 15,
                  ticket_number: "INC-000015",
                  subject: "My work",
                  assigned_user_id: 41,
                  priority: "P3",
                  status_id: 2,
                  version: 7,
                  updated_at: "2026-09-07T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "1" },
            }),
  );
  renderWorkspace();
  expect(
    await screen.findByRole("button", { name: "Resolve" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Pending" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Escalate" })).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Handover" }),
  ).not.toBeInTheDocument();
});

test("assigned Mine cards expose Start Progress", async () => {
  state.permissions = new Set([
    "support_assistant.mine.view",
    "ticket.change.status",
    "ticket.start.progress",
    "ticket.assign.team",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [
              { id: 5, code: "ASSIGNED", name: "Assigned", color: "#1976d2" },
            ],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 18,
                  ticket_number: "INC-000018",
                  subject: "Assigned work",
                  assigned_user_id: 41,
                  priority: "P3",
                  status_id: 5,
                  version: 3,
                  updated_at: "2026-09-07T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "1" },
            }),
  );
  state.post.mockResolvedValue({ data: { version: 4 } });
  renderWorkspace();
  await waitFor(() =>
    expect(state.get).toHaveBeenCalledWith(
      "/tickets",
      expect.objectContaining({
        params: expect.objectContaining({
          assistant_module: "mine",
          sort_by: "updated_at",
          sort_direction: "desc",
        }),
      }),
    ),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Start progress" }),
  );
  expect(screen.getByRole("button", { name: "Handover" })).toBeInTheDocument();
  await waitFor(() =>
    expect(state.post).toHaveBeenCalledWith("/tickets/18/transition", {
      to_status_code: "IN_PROGRESS",
      reason: "Work started from Support Assistant",
      version: 3,
    }),
  );
});

test("dragging Assistant cards saves the personal order", async () => {
  state.permissions = new Set(["support_assistant.mine.view"]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [{ id: 5, code: "ASSIGNED", name: "Assigned" }],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 21,
                  ticket_number: "INC-000021",
                  subject: "First",
                  assigned_user_id: 41,
                  priority: "P3",
                  status_id: 5,
                  version: 1,
                  created_at: "2026-09-07T11:00:00Z",
                  updated_at: "2026-09-07T11:00:00Z",
                },
                {
                  id: 20,
                  ticket_number: "INC-000020",
                  subject: "Second",
                  assigned_user_id: 41,
                  priority: "P3",
                  status_id: 5,
                  version: 1,
                  created_at: "2026-09-07T10:00:00Z",
                  updated_at: "2026-09-07T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "2" },
            }),
  );
  state.put.mockResolvedValue({ data: { pinned_ticket_ids: [20, 21] } });
  renderWorkspace();
  const first = await screen.findByLabelText(
    "INC-000021 draggable ticket card; right-click for actions",
  );
  const second = screen.getByLabelText(
    "INC-000020 draggable ticket card; right-click for actions",
  );
  const dataTransfer = {
    effectAllowed: "none",
    dropEffect: "none",
    setData: vi.fn(),
  };
  fireEvent.dragStart(first, { dataTransfer });
  fireEvent.dragOver(second, { dataTransfer });
  fireEvent.drop(second, { dataTransfer });
  await waitFor(() =>
    expect(state.put).toHaveBeenCalledWith(
      "/tickets/support-assistant/preferences",
      expect.objectContaining({ pinned_ticket_ids: [20, 21] }),
    ),
  );
});

test("resolved queue prioritizes oldest closure and exposes the close action", async () => {
  state.permissions = new Set([
    "support_assistant.mine.view",
    "ticket.change.status",
  ]);
  state.get.mockImplementation(
    (url: string, config?: { params?: Record<string, unknown> }) =>
      url === "/auth/me"
        ? Promise.resolve(authMe())
        : url === "/ticket-statuses"
          ? Promise.resolve({
              data: [{ id: 8, code: "RESOLVED", name: "Resolved" }],
              headers: {},
            })
          : url === "/tickets/support-assistant/preferences"
            ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
            : Promise.resolve({
                data:
                  config?.params?.assistant_module === "resolved" &&
                  config?.params?.limit !== 1
                    ? [
                        {
                          id: 27,
                          ticket_number: "INC-000027",
                          subject: "Ready for closure",
                          assigned_user_id: 41,
                          assigned_user_name: "Ahmed Engineer",
                          priority: "P3",
                          status_id: 8,
                          version: 2,
                          created_at: "2026-09-01T08:00:00Z",
                          updated_at: "2026-09-08T09:00:00Z",
                          resolved_at: "2026-09-08T08:00:00Z",
                        },
                      ]
                    : [],
                headers: { "x-total-count": "1" },
              }),
  );
  renderWorkspace();
  fireEvent.click(
    await screen.findByRole("tab", { name: /Resolved awaiting closure/ }),
  );
  expect(
    await screen.findByRole("button", { name: "Close ticket" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/Awaiting closure since/)).toBeInTheDocument();
  expect(screen.getByText("Closure details required")).toBeInTheDocument();
  expect(screen.getByText("Engineer: Ahmed Engineer")).toBeInTheDocument();
  await waitFor(() =>
    expect(state.get).toHaveBeenCalledWith(
      "/tickets",
      expect.objectContaining({
        params: expect.objectContaining({
          assistant_module: "resolved",
          incomplete_resolution_only: true,
          sort_by: "resolved_at",
          sort_direction: "asc",
        }),
      }),
    ),
  );
});

test("terminal Mine cards hide actions that cannot be performed", async () => {
  state.permissions = new Set([
    "support_assistant.mine.view",
    "ticket.change.status",
    "ticket.start.progress",
    "ticket.escalate",
    "ticket.assign.team",
  ]);
  state.get.mockImplementation((url: string) =>
    url === "/auth/me"
      ? Promise.resolve(authMe())
      : url === "/ticket-statuses"
        ? Promise.resolve({
            data: [
              { id: 3, code: "CLOSED", name: "Closed" },
              { id: 4, code: "RESOLVED", name: "Resolved" },
            ],
            headers: {},
          })
        : url === "/tickets/support-assistant/preferences"
          ? Promise.resolve({ data: { pinned_ticket_ids: [] }, headers: {} })
          : Promise.resolve({
              data: [
                {
                  id: 16,
                  ticket_number: "INC-000016",
                  subject: "Completed work",
                  assigned_user_id: 41,
                  priority: "P3",
                  status_id: 3,
                  version: 8,
                  updated_at: "2026-09-07T10:00:00Z",
                },
                {
                  id: 17,
                  ticket_number: "INC-000017",
                  subject: "Resolved work",
                  assigned_user_id: 41,
                  priority: "P3",
                  status_id: 4,
                  version: 9,
                  updated_at: "2026-09-07T10:00:00Z",
                },
              ],
              headers: { "x-total-count": "2" },
            }),
  );
  renderWorkspace();
  expect(await screen.findByText("INC-000016")).toBeInTheDocument();
  expect(screen.getByText("INC-000017")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Pending" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Escalate" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Handover" }),
  ).not.toBeInTheDocument();
});
