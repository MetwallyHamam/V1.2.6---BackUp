import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import i18n from "../i18n/config";

const apiMock = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../api/client", () => ({ api: apiMock }));

import { MajorIncidentsPage } from "../pages/MajorIncidentsPage";
import { ProblemsPage } from "../pages/ProblemsPage";

function renderPage(page: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(async () => {
  apiMock.get.mockReset();
  await i18n.changeLanguage("ar");
  document.documentElement.dir = "rtl";
});

afterEach(async () => {
  await i18n.changeLanguage("en");
  document.documentElement.dir = "ltr";
});

test("Problem portfolio renders localized Arabic headings and isolated numbers", async () => {
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data:
        url === "/problem-portfolio/summary"
          ? { total: 1, active: 1, known_errors: 0, overdue: 0, unassigned: 0 }
          : [
              {
                id: 1,
                problem_number: "PRB00000001",
                title: "Recurring issue",
                status: "INVESTIGATING",
                priority: "HIGH",
                owner_name: null,
                linked_ticket_count: 2,
                open_task_count: 1,
                overdue_task_count: 0,
                updated_at: "2026-10-07T10:00:00Z",
              },
            ],
    }),
  );
  renderPage(<ProblemsPage />);
  expect(await screen.findByText("إدارة المشكلات")).toBeInTheDocument();
  expect(await screen.findByText("المهام المفتوحة")).toBeInTheDocument();
  expect(screen.getByText("PRB00000001").closest("span")).toHaveStyle({
    direction: "ltr",
  });
});

test("Major-Incident portfolio renders Arabic management labels", async () => {
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data:
        url === "/major-incident-portfolio/summary"
          ? {
              total: 0,
              active: 0,
              active_sev1: 0,
              updates_overdue: 0,
              awaiting_pir: 0,
            }
          : [],
    }),
  );
  renderPage(<MajorIncidentsPage />);
  expect(await screen.findByText("الحوادث الجسيمة")).toBeInTheDocument();
  expect(screen.getByText("تحديثات متأخرة")).toBeInTheDocument();
  expect(
    await screen.findByText("لا توجد حوادث جسيمة تطابق عوامل التصفية."),
  ).toBeInTheDocument();
});
