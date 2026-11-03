import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import "../i18n/config";

const apiMock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../api/client", () => ({ api: apiMock, apiErrorMessage: () => "Save failed" }));
import { ContractClientBulkSelector } from "../pages/ContractClientBulkSelector";

test("the original client is removable without being forced back into the payload", async () => {
  const clients = [{ id: 1, code: "FIRST", name: "First client" }, { id: 2, code: "SECOND", name: "Second client" }];
  apiMock.get.mockImplementation((url: string) => Promise.resolve({ data: url.includes("search-page") ? { items: clients, total: 2, offset: 0, limit: 50 } : clients }));
  apiMock.post.mockResolvedValue({ data: { id: 5, client_id: 2, linked_client_ids: [2], is_shared_default: false } });
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><ContractClientBulkSelector contractId={5} canManage onApplied={vi.fn()} /></QueryClientProvider>);
  const first = await screen.findByRole("checkbox", { name: /FIRST/ });
  await waitFor(() => expect(first).toBeChecked());
  expect(first).toBeEnabled();
  fireEvent.click(first);
  fireEvent.click(screen.getByRole("button", { name: /^Apply/ }));
  await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith("/contracts/5/client-selection/apply", { mode: "EXPLICIT", search: null, excluded_ids: [], explicit_ids: [2] }));
});
