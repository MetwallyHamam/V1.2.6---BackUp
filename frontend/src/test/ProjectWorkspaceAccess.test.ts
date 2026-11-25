import { describe, expect, it } from "vitest";
import { isProjectWorkspaceRoute, usesProjectWorkspace } from "../auth/projectWorkspaceAccess";

describe("Project Workspace access", () => {
  it("selects the isolated shell for assigned project managers even with ticket permissions", () => {
    const permissions = new Set(["project.portfolio.view", "project.manage.assigned", "ticket.view.own"]);
    expect(usesProjectWorkspace("EMPLOYEE", (permission) => permissions.has(permission))).toBe(true);
    permissions.add("project.manage");
    expect(usesProjectWorkspace("EMPLOYEE", (permission) => permissions.has(permission))).toBe(false);
    expect(usesProjectWorkspace("EMPLOYEE", (permission) => permission === "ticket.view.own")).toBe(false);
  });

  it("allows project and account routes while excluding support routes", () => {
    for (const route of ["/project-workspace", "/project-my-work", "/project-management", "/projects/3/work-packages", "/change-password", "/notifications"]) {
      expect(isProjectWorkspaceRoute(route)).toBe(true);
    }
    for (const route of ["/support-workspace", "/support-assistant-app", "/tickets/3", "/projects-other"]) {
      expect(isProjectWorkspaceRoute(route)).toBe(false);
    }
  });
});
