import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import i18n from "../i18n/config";

const apiMock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../api/client", () => ({ api: apiMock }));

import { PortalTicketDetailPage } from "../pages/PortalTicketDetailPage";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/portal/tickets/7"]}>
        <Routes>
          <Route
            path="/portal/tickets/:id"
            element={<PortalTicketDetailPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("ar");
  document.documentElement.dir = "rtl";
  apiMock.get.mockReset();
  apiMock.get.mockImplementation((url: string) => {
    if (url === "/portal/tickets/7")
      return Promise.resolve({
        data: {
          id: 7,
          ticket_number: "TKT00000007",
          subject: "Service interruption",
          description: "Description",
          priority: "P2",
          version: 1,
        },
      });
    if (url === "/portal/catalog")
      return Promise.resolve({ data: { products: [], services: [] } });
    if (url === "/portal/tickets/7/satisfaction")
      return Promise.resolve({ data: { state: "UNAVAILABLE" } });
    if (url === "/portal/tickets/7/service-advisories")
      return Promise.resolve({
        data: {
          major_incidents: [
            {
              id: 2,
              major_incident_number: "MI00000002",
              severity: "SEV1",
              status: "MONITORING",
              updates: [
                {
                  id: 3,
                  message: "الخدمة مستقرة وتحت المراقبة",
                  published_at: "2026-10-07T10:00:00Z",
                },
              ],
            },
          ],
          knowledge: [
            {
              problem_number: "PRB00000004",
              article_id: 5,
              link_type: "WORKAROUND",
              title: "حل مؤقت معتمد",
              summary: "ملخص آمن للعميل",
              body: "اتبع الخطوات المعتمدة.",
              updated_at: "2026-10-07T11:00:00Z",
            },
          ],
        },
      });
    return Promise.resolve({ data: [] });
  });
});

afterEach(async () => {
  await i18n.changeLanguage("en");
  document.documentElement.dir = "ltr";
});

test("Portal ticket renders only the returned client-safe service advisories", async () => {
  renderPage();
  expect(await screen.findByText("تحديثات حادث الخدمة")).toBeInTheDocument();
  expect(screen.getByText("الخدمة مستقرة وتحت المراقبة")).toBeInTheDocument();
  expect(
    screen.getByText("حلول مؤقتة وإرشادات خدمة معتمدة"),
  ).toBeInTheDocument();
  expect(screen.getByText("حل مؤقت معتمد")).toBeInTheDocument();
  expect(screen.getByText("MI00000002")).toHaveStyle({ direction: "ltr" });
  expect(screen.getByText("PRB00000004")).toHaveStyle({ direction: "ltr" });
  expect(apiMock.get).toHaveBeenCalledWith(
    "/portal/tickets/7/service-advisories",
  );
});
