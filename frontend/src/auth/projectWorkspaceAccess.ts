export const projectWorkspacePath = "/project-workspace";
export const projectMyWorkPath = "/project-my-work";
export const implementationWorkspacePath = "/implementation-workspace";
export const projectWorkspacePermission = "workspace.project_management.access";
export const implementationWorkspacePermission = "workspace.implementation.access";
export const supportWorkspacePermission = "workspace.support.access";

const workspaceChoices = [
  { id: "project", path: projectWorkspacePath, permission: projectWorkspacePermission, label: "Project Workspace" },
  { id: "implementation", path: implementationWorkspacePath, permission: implementationWorkspacePermission, label: "Implementation Workspace" },
  { id: "support", path: "/support-workspace", permission: supportWorkspacePermission, label: "Support Workspace" },
] as const;

export function authorizedWorkspaces(hasPermission: (permission: string) => boolean) {
  return workspaceChoices.filter((workspace) => hasPermission(workspace.permission)
    && (workspace.id !== "project" || hasPermission("project.portfolio.view"))
    && (workspace.id !== "support" || [
      "ticket.view.own", "ticket.view.team", "ticket.view.department", "ticket.view.all",
      "ticket.pre_ticket.view.own", "ticket.pre_ticket.queue.view",
    ].some(hasPermission)));
}

const preferenceKey = (userId: number) => `supporthub:workspace:v1:${userId}`;

export function preferredWorkspace(userId: number, hasPermission: (permission: string) => boolean) {
  try {
    const id = window.localStorage.getItem(preferenceKey(userId));
    return authorizedWorkspaces(hasPermission).find((workspace) => workspace.id === id);
  } catch {
    return undefined;
  }
}

export function rememberWorkspace(userId: number, workspace: typeof workspaceChoices[number]["id"]) {
  try {
    window.localStorage.setItem(preferenceKey(userId), workspace);
  } catch {
    // Navigation still works when persistent storage is unavailable.
  }
}

export function deliveryWorkspaceLanding(userType: string | undefined, hasPermission: (permission: string) => boolean) {
  if (userType !== "EMPLOYEE" || hasPermission(supportWorkspacePermission)) return null;
  if (hasPermission(projectWorkspacePermission)) return projectWorkspacePath;
  if (hasPermission(implementationWorkspacePermission)) return implementationWorkspacePath;
  return null;
}

const projectWorkspaceRoutes = [
  projectWorkspacePath,
  projectMyWorkPath,
  "/project-management",
  "/projects",
  "/project-templates",
  "/project-analytics",
  "/clients",
  "/notifications",
  "/change-password",
  "/unauthorized",
];

export function isProjectWorkspaceRoute(pathname: string) {
  return projectWorkspaceRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function isAllowedDeliveryRoute(pathname: string, hasPermission: (permission: string) => boolean) {
  if (hasPermission(projectWorkspacePermission) && isProjectWorkspaceRoute(pathname)) return true;
  return hasPermission(implementationWorkspacePermission) && [
    implementationWorkspacePath, "/implementation-intake", "/implementation-analytics",
    "/projects", "/notifications", "/change-password", "/unauthorized",
  ].some((route) => pathname === route || pathname.startsWith(`${route}/`));
}
