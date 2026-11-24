import { DashboardOutlined, FolderOutlined, GroupsOutlined, LibraryBooksOutlined } from "@mui/icons-material";
import { AppBar, Avatar, Box, Button, Paper, Stack, Toolbar, Typography } from "@mui/material";
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function ProjectManagementLayout() {
  const { hasPermission, logout, user } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  if (pathname === "/" || pathname === "/home") {
    return <Navigate to="/project-management" replace />;
  }

  const links = [
    { label: "Overview", path: "/project-management", icon: <DashboardOutlined /> },
    { label: "Projects", path: "/projects", icon: <FolderOutlined /> },
    ...(hasPermission("project.create")
      ? [{ label: "Project Templates", path: "/project-templates", icon: <LibraryBooksOutlined /> }]
      : []),
    ...(hasPermission("client.view")
      ? [{ label: "Customers", path: "/clients", icon: <GroupsOutlined /> }]
      : []),
  ];
  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default" }}>
      <AppBar position="sticky" elevation={0} color="default" sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "background.paper" }}>
        <Toolbar sx={{ justifyContent: "space-between", gap: 2 }}>
          <Stack direction="row" alignItems="center" gap={1.5}>
            <Avatar variant="rounded" sx={{ bgcolor: "primary.main", width: 34, height: 34 }}><FolderOutlined fontSize="small" /></Avatar>
            <Typography variant="h6" fontWeight={800}>Project Management</Typography>
          </Stack>
          <Stack direction="row" alignItems="center" gap={1}>
            <Typography variant="body2" sx={{ display: { xs: "none", sm: "block" } }}>{user?.full_name}</Typography>
            <Button color="inherit" size="small" onClick={async () => {
              await logout();
              navigate("/login", { replace: true });
            }}>Sign out</Button>
          </Stack>
        </Toolbar>
      </AppBar>
      <Stack direction={{ xs: "column", md: "row" }}>
        <Paper component="nav" aria-label="Project Management navigation" square elevation={0}
          sx={{ width: { md: 240 }, minHeight: { md: "calc(100dvh - 65px)" }, flexShrink: 0,
            borderInlineEnd: { md: 1 }, borderBottom: { xs: 1, md: 0 }, borderColor: "divider", p: { xs: 1, md: 2 } }}>
          <Stack direction={{ xs: "row", md: "column" }} gap={1} flexWrap="wrap">
            {links.map(({ label, path, icon }) => (
              <Button key={path} component={NavLink} to={path} startIcon={icon}
                sx={{ justifyContent: "flex-start", textAlign: "start", py: 1, px: 1.5,
                  color: "text.secondary", "&[aria-current=page]": { bgcolor: "action.selected", color: "primary.main" } }}>
                {label}
              </Button>
            ))}
          </Stack>
        </Paper>
        <Box component="main" sx={{ flex: 1, minWidth: 0 }}><Outlet /></Box>
      </Stack>
    </Box>
  );
}
