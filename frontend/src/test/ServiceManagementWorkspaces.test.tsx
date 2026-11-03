import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import i18n from "../i18n/config";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
}));
const authState = vi.hoisted(() => ({ permissions: new Set<string>() }));
vi.mock("../api/client", () => ({
  api: apiMock,
  apiErrorMessage: () => "error",
}));
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    hasPermission: (permission: string) =>
      authState.permissions.has(permission),
  }),
}));

import { MajorIncidentWorkspacePage } from "../pages/MajorIncidentWorkspacePage";
import { ProblemWorkspacePage } from "../pages/ProblemWorkspacePage";

function renderRoute(path: string, route: string, page: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={route} element={page} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(async () => {
  apiMock.get.mockReset();
  apiMock.patch.mockReset();
  authState.permissions.clear();
  await i18n.changeLanguage("ar");
  document.documentElement.dir = "rtl";
});

afterEach(async () => {
  await i18n.changeLanguage("en");
  document.documentElement.dir = "ltr";
});

test("Problem workspace renders its Arabic investigation sections", async () => {
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data:
        url === "/problems/1"
          ? {
              id: 1,
              problem_number: "PRB00000001",
              title: "Recurring issue",
              description: "Description",
              status: "INVESTIGATING",
              priority: "HIGH",
              version: 1,
            }
          : [],
    }),
  );
  renderRoute("/problems/1", "/problems/:id", <ProblemWorkspacePage />);
  expect(await screen.findByText("مساحة عمل المشكلة")).toBeInTheDocument();
  expect(screen.getByText("التحقيق")).toBeInTheDocument();
  expect(screen.getByText("تعليقات التحقيق")).toBeInTheDocument();
  expect(screen.getByText("PRB00000001")).toHaveStyle({ direction: "ltr" });
});

test("Major Incident workspace renders its Arabic command sections", async () => {
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data:
        url === "/major-incidents/1"
          ? {
              id: 1,
              major_incident_number: "MI00000001",
              primary_ticket_id: 10,
              severity: "SEV1",
              status: "DECLARED",
              incident_commander_user_id: 1,
              business_impact: "Impact",
              current_status_summary: "Investigating",
              version: 1,
              declared_at: "2026-10-07T10:00:00Z",
            }
          : url === "/major-incidents/1/scopes"
            ? {
                client_ids: [],
                product_ids: [],
                product_module_ids: [],
                service_ids: [],
                environment_ids: [],
              }
            : [],
    }),
  );
  renderRoute(
    "/major-incidents/1",
    "/major-incidents/:id",
    <MajorIncidentWorkspacePage />,
  );
  expect(await screen.findByText("مساحة عمل قائد الحادث")).toBeInTheDocument();
  expect(screen.getAllByText("الوضع الحالي")).toHaveLength(2);
  expect(screen.getByText("تحديثات الحادث")).toBeInTheDocument();
  expect(screen.getByText("MI00000001")).toHaveStyle({ direction: "ltr" });
});

test("Problem edit action opens an accessible localized dialog and saves", async () => {
  authState.permissions.add("problem.edit");
  apiMock.patch.mockResolvedValue({ data: {} });
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data:
        url === "/problems/1"
          ? {
              id: 1,
              problem_number: "PRB00000001",
              title: "Recurring issue",
              description: "Description",
              status: "INVESTIGATING",
              priority: "HIGH",
              version: 1,
            }
          : [],
    }),
  );
  renderRoute("/problems/1", "/problems/:id", <ProblemWorkspacePage />);
  const editButton = await screen.findByRole("button", { name: "تعديل" });
  editButton.focus();
  fireEvent.click(editButton);
  const dialog = screen.getByRole("dialog", { name: "تعديل المشكلة" });
  expect(dialog).toBeInTheDocument();
  expect(dialog.querySelector('input[name="title"]')).toHaveFocus();
  fireEvent.submit(dialog.querySelector("form")!);
  await waitFor(() =>
    expect(apiMock.patch).toHaveBeenCalledWith(
      "/problems/1",
      expect.objectContaining({ title: "Recurring issue", version: 1 }),
    ),
  );
  editButton.focus();
  fireEvent.click(editButton);
  const reopenedDialog = await screen.findByRole("dialog", {
    name: "تعديل المشكلة",
  });
  fireEvent.click(
    reopenedDialog.querySelector('button[type="button"]')!,
  );
  await waitFor(() => expect(editButton).toHaveFocus());
});

test("Major Incident client-safe update publishes the client message", async () => {
  authState.permissions.add("major_incident.publish_update");
  apiMock.post.mockReset();
  apiMock.post.mockResolvedValue({ data: {} });
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data:
        url === "/major-incidents/1"
          ? {
              id: 1,
              major_incident_number: "MI00000001",
              primary_ticket_id: 10,
              severity: "SEV1",
              status: "DECLARED",
              incident_commander_user_id: 1,
              business_impact: "Impact",
              current_status_summary: "Investigating",
              version: 1,
              declared_at: "2026-10-07T10:00:00Z",
            }
          : url === "/major-incidents/1/scopes"
            ? {
                client_ids: [],
                product_ids: [],
                product_module_ids: [],
                service_ids: [],
                environment_ids: [],
              }
            : [],
    }),
  );
  renderRoute(
    "/major-incidents/1",
    "/major-incidents/:id",
    <MajorIncidentWorkspacePage />,
  );
  await screen.findByText("تحديثات الحادث");
  const message = document.querySelector<HTMLTextAreaElement>(
    'textarea[name="message"]',
  )!;
  expect(message).toBeInTheDocument();
  fireEvent.change(message, { target: { value: "تمت استعادة الخدمة جزئياً" } });
  const form = message.closest("form")!;
  const updateType = form.querySelector('input[name="update_type"]')!;
  fireEvent.change(updateType, { target: { value: "CLIENT" } });
  fireEvent.submit(form);
  await waitFor(() =>
    expect(apiMock.post).toHaveBeenCalledWith("/major-incidents/1/updates", {
      update_type: "CLIENT",
      internal_message: null,
      client_message: "تمت استعادة الخدمة جزئياً",
    }),
  );
});

test("Major Incident affected-ticket dialog links a visible ticket", async () => {
  authState.permissions.add("major_incident.link_ticket");
  apiMock.post.mockReset();
  apiMock.post.mockResolvedValue({ data: {} });
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data:
        url === "/major-incidents/1"
          ? {
              id: 1,
              major_incident_number: "MI00000001",
              primary_ticket_id: 10,
              severity: "SEV1",
              status: "DECLARED",
              incident_commander_user_id: 1,
              business_impact: "Impact",
              current_status_summary: "Investigating",
              version: 4,
              declared_at: "2026-10-07T10:00:00Z",
            }
          : url === "/major-incidents/1/scopes"
            ? {
                client_ids: [],
                product_ids: [],
                product_module_ids: [],
                service_ids: [],
                environment_ids: [],
              }
            : url === "/tickets"
              ? [
                  {
                    id: 22,
                    ticket_number: "TKT00000022",
                    subject: "Affected client",
                  },
                ]
              : [],
    }),
  );
  renderRoute(
    "/major-incidents/1",
    "/major-incidents/:id",
    <MajorIncidentWorkspacePage />,
  );
  const trigger = await screen.findByRole("button", { name: "ربط تذكرة" });
  fireEvent.click(trigger);
  const dialog = await screen.findByRole("dialog", {
    name: "ربط تذكرة حادث متأثرة",
  });
  const ticketSelect = await screen.findByRole("combobox", {
    name: "تذكرة مفتوحة متاحة",
  });
  fireEvent.mouseDown(ticketSelect);
  fireEvent.click(await screen.findByRole("option", { name: /TKT00000022/ }));
  fireEvent.submit(dialog.querySelector("form")!);
  await waitFor(() =>
    expect(apiMock.post).toHaveBeenCalledWith("/major-incidents/1/tickets", {
      ticket_id: 22,
      link_type: "AFFECTED",
      version: 4,
    }),
  );
});
