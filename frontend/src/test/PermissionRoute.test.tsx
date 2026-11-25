import { render, screen } from "@testing-library/react";
import { MemoryRouter, Outlet, Route, Routes, useOutletContext } from "react-router-dom";
import { expect, it, vi } from "vitest";
import { PermissionRoute } from "../routes/PermissionRoute";

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ hasPermission: (permission: string) => permission === "cross_department.request.create" }),
}));

function Collaboration() {
  const { id } = useOutletContext<{ id: number }>();
  return <div>Collaboration for project {id}</div>;
}

it("preserves the project context through a nested permission route", () => {
  render(
    <MemoryRouter initialEntries={["/projects/3/collaboration"]}>
      <Routes>
        <Route path="projects/:id" element={<Outlet context={{ id: 3 }} />}>
          <Route element={<PermissionRoute anyOf={["cross_department.request.create"]} />}>
            <Route path="collaboration" element={<Collaboration />} />
          </Route>
        </Route>
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText("Collaboration for project 3")).toBeInTheDocument();
});
