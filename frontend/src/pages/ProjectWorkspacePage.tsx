import { Alert, Button, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, Outlet, useOutletContext, useParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ProjectCollaborationPanel } from "../components/ProjectCollaborationPanel";
import { ProjectSupportHandoverPanel } from "../components/ProjectSupportHandoverPanel";

export type Project = {
  id: number;
  name: string;
  project_number: string;
  description: string | null;
  status: string;
  progress_percent: number;
  row_version: number;
  project_manager_user_id: number;
};

export function ProjectWorkspacePage() {
  const { id } = useParams();
  const { hasPermission } = useAuth();
  const project = useQuery({
    queryKey: ["project", Number(id)],
    queryFn: async () => (await api.get<Project>(`/projects/${id}`)).data,
  });
  const tabs = [
    { path: ".", label: "Overview", visible: true },
    { path: "work-packages", label: "Work packages", visible: true },
    { path: "schedule", label: "Schedule", visible: true },
    { path: "execution", label: "Implementation", visible: hasPermission("implementation.task.view") },
    { path: "collaboration", label: "Collaboration", visible: hasPermission("cross_department.request.create") },
    { path: "handover", label: "Support handover", visible: hasPermission("handover.view") },
  ];

  return (
    <Stack spacing={2} sx={{ p: { xs: 2, md: 3 } }}>
      <Button component={Link} to="/projects" sx={{ alignSelf: "flex-start" }}>All projects</Button>
      {project.isPending && <LinearProgress aria-label="Loading project" />}
      {project.isError && <Alert severity="error">{apiErrorMessage(project.error)}</Alert>}
      {project.data && (
        <>
          <Typography component="h1" variant="h4">{project.data.name}</Typography>
          <Typography color="text.secondary">{project.data.project_number}</Typography>
          <Stack component="nav" aria-label="Project views" direction="row" gap={1} flexWrap="wrap">
            {tabs.filter((tab) => tab.visible).map((tab) => (
              <Button key={tab.path} component={NavLink} end to={tab.path}
                sx={{ "&[aria-current=page]": { bgcolor: "action.selected" } }}>
                {tab.label}
              </Button>
            ))}
          </Stack>
          <Outlet context={project.data} />
        </>
      )}
    </Stack>
  );
}

export function ProjectWorkspaceOverview() {
  const project = useOutletContext<Project>();
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1}>
        <Typography component="h2" variant="h6">Delivery status</Typography>
        <Typography>{project.status.replaceAll("_", " ")}</Typography>
        <Typography>{project.progress_percent}% complete</Typography>
        <LinearProgress aria-label="Project progress" variant="determinate" value={project.progress_percent} />
        {project.description && <Typography sx={{ whiteSpace: "pre-wrap" }}>{project.description}</Typography>}
      </Stack>
    </Paper>
  );
}

export function ProjectWorkspaceCollaboration() {
  const { id } = useOutletContext<Project>();
  return <ProjectCollaborationPanel projectId={id} />;
}

export function ProjectWorkspaceHandover() {
  const project = useOutletContext<Project>();
  return <ProjectSupportHandoverPanel projectId={project.id} projectStatus={project.status} projectVersion={project.row_version} />;
}
