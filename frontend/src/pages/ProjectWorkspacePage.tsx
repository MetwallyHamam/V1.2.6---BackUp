import { AccountTreeOutlined, ArrowBack, AssignmentOutlined, FactCheckOutlined, FolderOutlined, HistoryOutlined, HubOutlined, SpaceDashboardOutlined, TimelineOutlined, WarningAmberOutlined } from "@mui/icons-material";
import { Alert, Avatar, Box, Button, Chip, LinearProgress, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, Outlet, useLocation, useNavigate, useOutletContext, useParams } from "react-router-dom";
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
  planned_end_date?: string | null;
  health?: string;
};

export function ProjectWorkspacePage() {
  const { id } = useParams();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const project = useQuery({
    queryKey: ["project", Number(id)],
    queryFn: async () => (await api.get<Project>(`/projects/${id}`)).data,
  });
  const root = `/projects/${id}`;
  const groups = [
    { label: "Project", views: [
      { path: "", label: "Overview", icon: <SpaceDashboardOutlined />, visible: true },
    ] },
    { label: "Plan", views: [
      { path: "work-packages", label: "Work packages", icon: <AssignmentOutlined />, visible: true },
      { path: "schedule", label: "Schedule", icon: <TimelineOutlined />, visible: true },
      { path: "revisions", label: "Schedule revisions", icon: <HistoryOutlined />, visible: project.data?.status !== "DRAFT" },
      { path: "register", label: "Risks and changes", icon: <WarningAmberOutlined />, visible: true },
    ] },
    { label: "Deliver", views: [
      { path: "intake", label: "Intake decisions", icon: <AccountTreeOutlined />, visible: true },
      { path: "execution", label: "Implementation", icon: <AssignmentOutlined />, visible: hasPermission("implementation.task.view") },
      { path: "collaboration", label: "Collaboration", icon: <HubOutlined />, visible: hasPermission("cross_department.request.create") },
    ] },
    { label: "Hand over", views: [
      { path: "handover", label: "Support handover", icon: <FactCheckOutlined />, visible: hasPermission("handover.view") },
    ] },
  ].map((group) => ({ ...group, views: group.views.filter((view) => view.visible) }))
    .filter((group) => group.views.length);
  const viewPath = (path: string) => path ? `${root}/${path}` : root;
  const views = groups.flatMap((group) => group.views);

  return (
    <Stack spacing={2.5} sx={{ minWidth: 0 }}>
      {!project.data && <Button component={Link} to="/projects" sx={{ alignSelf: "flex-start" }}>Project portfolio</Button>}
      {project.isPending && <LinearProgress aria-label="Loading project" />}
      {project.isError && <Alert severity="error">{apiErrorMessage(project.error)}</Alert>}
      {project.data && (
        <>
          <Paper variant="outlined" sx={{ borderRadius: 3, minWidth: 0, overflow: "hidden" }}>
            <Stack gap={1.5} sx={{ px: { xs: 2, md: 3 }, py: 2 }}>
              <Button component={Link} to="/projects" startIcon={<ArrowBack />} size="small"
                sx={{ alignSelf: "flex-start", textTransform: "none" }}>Project portfolio</Button>
              <Stack direction="row" gap={1.5} alignItems="center">
                <Avatar variant="rounded" sx={{ bgcolor: "primary.main", color: "primary.contrastText" }}><FolderOutlined /></Avatar>
                <Box sx={{ minWidth: 0 }}>
                  <Typography component="h1" variant="h5" fontWeight={800} sx={{ overflowWrap: "anywhere" }}>{project.data.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{project.data.project_number}</Typography>
                </Box>
              </Stack>
              <Stack direction="row" gap={1} flexWrap="wrap">
                <Chip size="small" color="primary" label={project.data.status.replaceAll("_", " ")} />
                {project.data.planned_end_date && <Chip size="small" variant="outlined" label={`Planned finish ${project.data.planned_end_date}`} />}
              </Stack>
            </Stack>
          </Paper>
          <TextField select fullWidth size="small" label="Project view"
            value={views.some((view) => viewPath(view.path) === pathname) ? pathname : root}
            onChange={(event) => navigate(event.target.value)} sx={{ display: { xs: "block", lg: "none" } }}>
            {views.map((view) => <MenuItem key={view.path} value={viewPath(view.path)}>{view.label}</MenuItem>)}
          </TextField>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "190px minmax(0, 1fr)" } }}>
            <Paper component="nav" aria-label="Project views" variant="outlined"
              sx={{ display: { xs: "none", lg: "block" }, alignSelf: "start", p: 1, borderRadius: 3 }}>
              <Stack gap={1.25}>
                {groups.map((group) => (
                  <Stack key={group.label} gap={0.25}>
                    <Typography variant="overline" color="text.secondary" sx={{ px: 1.25, lineHeight: 2 }}>{group.label}</Typography>
                    {group.views.map((view) => (
                      <Button key={view.path} component={NavLink} end to={viewPath(view.path)} startIcon={view.icon}
                        sx={{ justifyContent: "flex-start", textAlign: "start", textTransform: "none", px: 1.25, color: "text.secondary",
                          "&[aria-current=page]": { bgcolor: "action.selected", color: "primary.main", fontWeight: 750 } }}>
                        {view.label}
                      </Button>
                    ))}
                  </Stack>
                ))}
              </Stack>
            </Paper>
            <Box sx={{ minWidth: 0 }}><Outlet context={project.data} /></Box>
          </Box>
        </>
      )}
    </Stack>
  );
}

export function ProjectWorkspaceOverview() {
  const project = useOutletContext<Project>();
  const { hasPermission } = useAuth();
  const plan = useQuery({
    queryKey: ["project-plan", String(project.id)],
    queryFn: async () => (await api.get<{
      milestones: { id: number; name: string; due_date: string | null; status: string }[];
    }>(`/projects/${project.id}/plan`)).data,
  });
  const milestones = (plan.data?.milestones ?? [])
    .filter((item) => !["DONE", "COMPLETED", "CANCELLED", "ACHIEVED"].includes(item.status))
    .sort((left, right) => (left.due_date ?? "9999").localeCompare(right.due_date ?? "9999"))
    .slice(0, 4);
  const next = ["AWAITING_IMPLEMENTATION_ACCEPTANCE", "INTAKE_PROPOSED", "INTAKE_RETURNED", "INTAKE_REJECTED"].includes(project.status)
    ? { text: "Review Implementation intake", path: "intake" }
    : ["DELIVERY_REVIEW", "HANDOVER_PREPARATION", "SUPPORT_REVIEW", "STABILIZATION"].includes(project.status) && hasPermission("handover.view")
      ? { text: "Review Support handover", path: "handover" }
      : { text: "Review work packages", path: "work-packages" };
  return (
    <Stack gap={2}>
      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 }, borderRadius: 3 }}>
        <Stack direction={{ xs: "column", md: "row" }} gap={2} justifyContent="space-between" alignItems={{ md: "center" }}>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography component="h2" variant="h6" fontWeight={750}>Delivery progress</Typography>
            <Stack direction="row" my={1} gap={1} alignItems="center" flexWrap="wrap">
              <Typography variant="h4" fontWeight={800}>{project.progress_percent}%</Typography>
              {project.health && <Chip size="small" variant="outlined" label={project.health.replaceAll("_", " ")}
                color={["AT_RISK", "CRITICAL"].includes(project.health) ? "warning" : "default"} />}
            </Stack>
            <LinearProgress aria-label="Project progress" variant="determinate" value={project.progress_percent}
              sx={{ maxWidth: 460, height: 7, borderRadius: 4 }} />
          </Box>
          <Button component={Link} to={next.path} variant="contained" sx={{ alignSelf: { xs: "flex-start", md: "center" }, textTransform: "none" }}>
            {next.text}
          </Button>
        </Stack>
      </Paper>
      <Paper variant="outlined" sx={{ borderRadius: 3, p: 2 }}>
        <Stack direction="row" gap={1} justifyContent="space-between" alignItems="center">
          <Typography component="h2" variant="h6" fontWeight={750}>Open milestones</Typography>
          <Button component={Link} to="schedule" size="small">View schedule</Button>
        </Stack>
        {plan.isPending && <LinearProgress aria-label="Loading milestones" />}
        {plan.isError && <Alert severity="error">{apiErrorMessage(plan.error)}</Alert>}
        {plan.isSuccess && !milestones.length && <Typography color="text.secondary" sx={{ pt: 1 }}>No open milestones.</Typography>}
        {milestones.map((item) => (
          <Stack key={item.id} direction="row" justifyContent="space-between" alignItems="center" gap={1}
            sx={{ borderTop: 1, borderColor: "divider", py: 1 }}>
            <Button component={Link} to={`work-packages?item=milestone-${item.id}`}
              sx={{ textTransform: "none", textAlign: "start" }}>{item.name}</Button>
            <Typography variant="body2" color="text.secondary">{item.due_date ?? "Unscheduled"}</Typography>
          </Stack>
        ))}
      </Paper>
      {project.description && <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
        <Typography component="h2" variant="h6" fontWeight={750} gutterBottom>Project brief</Typography>
        <Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{project.description}</Typography>
      </Paper>}
    </Stack>
  );
}

export function ProjectWorkspaceCollaboration() {
  const { id } = useOutletContext<Project>();
  return <ProjectCollaborationPanel projectId={id} />;
}

type IntakeRequest = {
  id: number;
  status: string;
  requested_start_date: string | null;
  requested_end_date: string | null;
  response_notes: string | null;
  responded_at: string | null;
  created_at: string;
};

export function ProjectWorkspaceIntake() {
  const { id } = useParams();
  const { hasPermission } = useAuth();
  const plan = useQuery({
    queryKey: ["project-plan", id],
    queryFn: async () => (await api.get<{ assignment_requests: IntakeRequest[] }>(`/projects/${id}/plan`)).data,
    refetchOnMount: "always",
  });
  const requests = plan.data?.assignment_requests ?? [];
  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
        <Typography component="h2" variant="h6">Implementation intake decisions</Typography>
        {hasPermission("project.assignment.respond") && (
          <Button component={Link} to={`/implementation-intake?project=${id}`}>Open Implementation inbox</Button>
        )}
      </Stack>
      {plan.isPending && <LinearProgress aria-label="Loading intake decisions" />}
      {plan.isError && <Alert severity="error">{apiErrorMessage(plan.error)}</Alert>}
      {plan.isSuccess && !requests.length && <Alert severity="info">No intake requests for this project.</Alert>}
      {requests.map((request) => (
        <Paper key={request.id} variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Typography component="h3" variant="subtitle1">Request #{request.id}</Typography>
              <Chip size="small" label={request.status.replaceAll("_", " ")} />
            </Stack>
            <Typography variant="body2">Submitted {new Date(request.created_at).toLocaleString()}</Typography>
            {(request.requested_start_date || request.requested_end_date) && (
              <Typography variant="body2">
                Delivery window {request.requested_start_date ?? "—"} to {request.requested_end_date ?? "—"}
              </Typography>
            )}
            {request.responded_at && (
              <Typography variant="body2">Responded {new Date(request.responded_at).toLocaleString()}</Typography>
            )}
            {request.response_notes && <Typography sx={{ whiteSpace: "pre-wrap" }}>{request.response_notes}</Typography>}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

export function ProjectWorkspaceHandover() {
  const project = useOutletContext<Project>();
  return <ProjectSupportHandoverPanel projectId={project.id} projectStatus={project.status} projectVersion={project.row_version} />;
}
