export const projectWorkspacePath = "/project-workspace";
export const projectMyWorkPath = "/project-my-work";

// The assigned Project Manager capability selects the dedicated workspace.
// Company-wide project administrators keep the full application shell.
export function usesProjectWorkspace(
  userType: string | undefined,
  hasPermission: (permission: string) => boolean,
) {
  return userType === "EMPLOYEE"
    && hasPermission("project.portfolio.view")
    && hasPermission("project.manage.assigned")
    && !hasPermission("project.manage");
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
