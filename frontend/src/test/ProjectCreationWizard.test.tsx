import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ProjectCreationWizard } from "../components/ProjectCreationWizard";
import { api } from "../api/client";

const storage = vi.hoisted(() => ({ draft: null as { version: number; checkpoint: unknown } | null }));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: 99 } }) }));
vi.mock("../api/client", () => ({
  api: {
    get: vi.fn(async (path: string) => ({ data: path === "/projects/options"
      ? {
        accounts: [], organizations: [], clients: [], departments: [], managers: [], teams: [],
        products: [{ id: 1, name: "ERP" }, { id: 2, name: "HIS" }],
        modules: [{ id: 11, product_id: 1, name: "Inventory" }, { id: 12, product_id: 1, name: "Payroll" }],
      }
      : path === "/projects/wizard-draft" ? storage.draft : [] })),
    post: vi.fn(),
    put: vi.fn(async (_path: string, body: { checkpoint: unknown }) => {
      storage.draft = { version: 1, checkpoint: body.checkpoint };
      return { data: { version: 1 } };
    }),
    delete: vi.fn(async () => { storage.draft = null; }),
  },
  apiErrorMessage: String,
}));

it("saves an incomplete checkpoint and blocks publishing until its checklist passes", async () => {
  storage.draft = null;
  const close = vi.fn();
  const wrapper = () => (
    <QueryClientProvider client={new QueryClient()}>
      <ProjectCreationWizard open onClose={close} onCreated={vi.fn()} />
    </QueryClientProvider>
  );
  const first = render(wrapper());
  const save = screen.getByRole("button", { name: "Save and exit" });
  await waitFor(() => expect(save).toBeEnabled());
  fireEvent.click(save);
  await waitFor(() => expect(close).toHaveBeenCalledOnce());
  expect(storage.draft).toMatchObject({ checkpoint: { step: 0, form: { client_id: "" } } });
  first.unmount();
  const saved = JSON.parse(JSON.stringify(storage.draft)) as { version: number; checkpoint: Record<string, unknown> };
  storage.draft = { ...saved, checkpoint: { ...saved.checkpoint, step: 1 } };
  const products = render(wrapper());
  fireEvent.click(await screen.findByRole("button", { name: "Resume draft" }));
  fireEvent.click(await screen.findByRole("button", { name: /^ERP/ }));
  expect(screen.getByRole("checkbox", { name: "Inventory" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "Payroll" })).toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Clear selection" }));
  fireEvent.click(screen.getByRole("button", { name: /^HIS/ }));
  fireEvent.click(screen.getByRole("button", { name: /^ERP/ }));
  expect(screen.getByRole("checkbox", { name: "Inventory" })).not.toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Select all" }));
  expect(screen.getByRole("checkbox", { name: "Inventory" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "Payroll" })).toBeChecked();
  products.unmount();
  storage.draft = { ...saved, checkpoint: {
    ...saved.checkpoint, step: 4,
    form: { ...(saved.checkpoint.form as object), product_ids: [1], module_ids: [11, 12] },
    phases: [{
      name: "Installation", planned_start_at: "2026-12-01T09:00", planned_end_at: "2026-12-01T11:00", product_ids: [1], module_ids: [11],
      tasks: [{ task_number: "", title: "Configure ERP", product_id: "", product_module_id: "", owner_user_id: "",
        planned_start_at: "2026-12-01T09:00", planned_end_at: "2026-12-01T10:00", estimate_minutes: "60" }],
    }],
  } };
  const planning = render(wrapper());
  fireEvent.click(await screen.findByRole("button", { name: "Resume draft" }));
  expect(screen.getByRole("combobox", { name: "Product" })).toHaveTextContent("ERP");
  const taskModule = screen.getByRole("combobox", { name: "Module (optional)" });
  expect(taskModule).toHaveTextContent("Inventory");
  fireEvent.mouseDown(taskModule);
  fireEvent.click(await screen.findByRole("option", { name: "Payroll" }));
  expect(taskModule).toHaveTextContent("Payroll");
  expect(screen.getByRole("checkbox", { name: "Payroll" })).toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Save as template" }));
  const templateDialog = within(screen.getByRole("dialog", { name: "Save as template" }));
  fireEvent.change(templateDialog.getByRole("textbox", { name: "Template name" }), { target: { value: "ERP rollout" } });
  fireEvent.click(templateDialog.getByRole("button", { name: "Save template" }));
  expect(await templateDialog.findByText(/ERP rollout.*ready to reuse/)).toBeVisible();
  expect(api.post).toHaveBeenCalledWith("/project-templates", expect.objectContaining({ name: "ERP rollout", publish: true }));
  fireEvent.click(templateDialog.getByRole("button", { name: "Close" }));
  expect(await screen.findByRole("textbox", { name: "Task title" })).toHaveValue("Configure ERP");
  planning.unmount();
  // Simulate a resumed review after an earlier section became incomplete.
  storage.draft = { ...saved, checkpoint: { ...saved.checkpoint, step: 6 } };
  render(wrapper());
  fireEvent.click(await screen.findByRole("button", { name: "Resume draft" }));
  expect(screen.getByRole("heading", { name: "Publish readiness" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Publish to Implementation" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Review Customer" }));
  fireEvent.click(screen.getByRole("button", { name: "Discard saved draft" }));
  await waitFor(() => expect(storage.draft).toBeNull());
});
