import { describe, expect, it, vi } from "vitest";
import {
  deliveryWorkspaceLanding, implementationWorkspacePermission, isAllowedDeliveryRoute,
  projectWorkspacePermission, supportWorkspacePermission,
  preferredWorkspace, rememberWorkspace,
} from "../auth/projectWorkspaceAccess";

describe("Project Workspace access", () => {
  it("uses explicit workspace grants instead of shared task or ticket permissions", () => {
    const permissions = new Set([projectWorkspacePermission, "implementation.task.view", "ticket.view.own"]);
    const has = (permission: string) => permissions.has(permission);
    expect(deliveryWorkspaceLanding("EMPLOYEE", has)).toBe("/project-workspace");
    expect(isAllowedDeliveryRoute("/implementation-workspace", has)).toBe(false);
    expect(isAllowedDeliveryRoute("/projects/3/execution", has)).toBe(true);
    permissions.add(implementationWorkspacePermission);
    expect(isAllowedDeliveryRoute("/implementation-workspace", has)).toBe(true);
    permissions.delete(projectWorkspacePermission);
    expect(deliveryWorkspaceLanding("EMPLOYEE", has)).toBe("/implementation-workspace");
    expect(isAllowedDeliveryRoute("/project-workspace", has)).toBe(false);
    permissions.add(supportWorkspacePermission);
    expect(deliveryWorkspaceLanding("EMPLOYEE", has)).toBeNull();
  });

  it("allows project and account routes while excluding support routes", () => {
    const has = (permission: string) => permission === projectWorkspacePermission;
    for (const route of ["/project-workspace", "/project-my-work", "/project-management", "/projects/3/work-packages", "/change-password", "/notifications"]) {
      expect(isAllowedDeliveryRoute(route, has)).toBe(true);
    }
    for (const route of ["/support-workspace", "/support-assistant-app", "/tickets/3", "/projects-other"]) {
      expect(isAllowedDeliveryRoute(route, has)).toBe(false);
    }
  });

  it("remembers the chosen workspace per user and ignores a withdrawn grant", () => {
    const values = new Map<string, string>();
    const restoreStorage = vi.spyOn(window, "localStorage", "get").mockReturnValue({
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => { values.set(key, value); },
      removeItem: (key) => { values.delete(key); },
      clear: () => values.clear(),
      key: (index) => [...values.keys()][index] ?? null,
      get length() { return values.size; },
    });
    const grants = new Set([implementationWorkspacePermission, projectWorkspacePermission, "project.portfolio.view"]);
    const has = (permission: string) => grants.has(permission);
    rememberWorkspace(100, "implementation");
    expect(preferredWorkspace(100, has)?.path).toBe("/implementation-workspace");
    expect(preferredWorkspace(101, has)).toBeUndefined();
    grants.delete(implementationWorkspacePermission);
    expect(preferredWorkspace(100, has)).toBeUndefined();
    restoreStorage.mockRestore();
  });
});
