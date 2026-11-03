import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import "../i18n/config";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  put: vi.fn(),
  post: vi.fn(),
}));
vi.mock("../api/client", () => ({
  api: apiMock,
  apiErrorMessage: () => "Save failed",
}));
import { ContractRenewalsPanel } from "../pages/ContractRenewalsPanel";

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.get.mockImplementation((url: string) =>
    Promise.resolve({
      data: url.endsWith("/renewal-opportunities")
        ? [
            {
              id: 4,
              stage: "NEGOTIATION",
              outcome: null,
              owner_user_id: 7,
              target_close_date: "2027-01-01",
              reason: "Signed next term",
              version: 3,
              lines: [{ id: 9, coverage_id: 10, outcome: "PENDING" }],
            },
          ]
        : url.endsWith("/renewal-owners")
          ? [{ id: 7, full_name: "Renewal manager" }]
          : url === "/contracts"
            ? [
                {
                  id: 1,
                  client_id: 2,
                  contract_number: "SOURCE",
                  start_date: "2026-01-01",
                  end_date: "2026-12-31",
                  status: "ACTIVE",
                  is_active: true,
                },
                {
                  id: 2,
                  client_id: 2,
                  contract_number: "NEXT",
                  start_date: "2027-01-01",
                  end_date: "2027-12-31",
                  status: "DRAFT",
                  is_active: true,
                },
                {
                  id: 3,
                  client_id: 2,
                  contract_number: "OVERLAP",
                  start_date: "2026-12-01",
                  end_date: "2027-12-31",
                  status: "ACTIVE",
                  is_active: true,
                },
              ]
            : [{ id: 20, product_id: 5, service_id: 8, is_covered: true }],
    }),
  );
  apiMock.put.mockResolvedValue({ data: {} });
});

function mount() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ContractRenewalsPanel contractId={1} coverage={[{ id: 10 }]} canManage />
    </QueryClientProvider>,
  );
}

async function choose(label: string, option: string) {
  fireEvent.mouseDown(screen.getByRole("combobox", { name: label }));
  fireEvent.click(await screen.findByRole("option", { name: option }));
}

test("successful renewal sends reviewed successor mappings and optimistic version", async () => {
  mount();
  await screen.findByRole("button", { name: "Save renewal" });
  await choose("Stage", "CLOSED");
  await choose("Final outcome", "RENEWED");
  fireEvent.mouseDown(
    screen.getByRole("combobox", { name: "Successor contract" }),
  );
  expect(
    screen.queryByRole("option", { name: /OVERLAP/ }),
  ).not.toBeInTheDocument();
  fireEvent.click(await screen.findByRole("option", { name: /NEXT/ }));
  await choose("Coverage outcome", "RENEWED");
  await choose(
    "Successor coverage",
    "#20 · Product 5 · Module Any · Service 8",
  );
  fireEvent.click(screen.getByRole("button", { name: "Save renewal" }));
  await waitFor(() =>
    expect(apiMock.put).toHaveBeenCalledWith(
      "/contracts/1/renewal-opportunities/4",
      expect.objectContaining({
        stage: "CLOSED",
        outcome: "RENEWED",
        successor_contract_id: 2,
        version: 3,
        lines: [
          expect.objectContaining({
            coverage_id: 10,
            outcome: "RENEWED",
            successor_coverage_id: 20,
          }),
        ],
      }),
    ),
  );
});

test("failed saves preserve editable renewal values and show an error", async () => {
  apiMock.put.mockRejectedValue(new Error("Conflict"));
  mount();
  await screen.findByRole("button", { name: "Save renewal" });
  fireEvent.change(screen.getByLabelText(/Reason for this update/), {
    target: { value: "Keep my update reason" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save renewal" }));
  expect(await screen.findByText("Save failed")).toBeInTheDocument();
  expect(screen.getByLabelText(/Reason for this update/)).toHaveValue(
    "Keep my update reason",
  );
});
