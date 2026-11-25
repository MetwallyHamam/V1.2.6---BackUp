import { Add, ArrowForward, AssignmentOutlined, CalendarTodayOutlined, FolderOpenOutlined, WarningAmber } from "@mui/icons-material";
import { Alert, Avatar, Box, Button, Chip, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { projectMyWorkPath, projectWorkspacePath } from "../auth/projectWorkspaceAccess";
import { ProjectCreationWizard } from "../components/ProjectCreationWizard";

type Summary = { total: number; at_risk: number; pending_assignment_requests: number };
type Project = {
  id: number; project_number: string; name: string; status: string; health: string;
  progress_percent: number; planned_end_date: string | null; project_manager_user_id: number;
};
const attention = (project: Project) =>
  ["AT_RISK", "CRITICAL"].includes(project.health) ||
  ["INTAKE_RETURNED", "INTAKE_PROPOSED", "INTAKE_REJECTED", "ON_HOLD"].includes(project.status);
const isIntake = (project: Project) =>
  ["AWAITING_IMPLEMENTATION_ACCEPTANCE", "INTAKE_RETURNED", "INTAKE_PROPOSED", "INTAKE_REJECTED"].includes(project.status);
const isHandover = (project: Project) =>
  ["DELIVERY_REVIEW", "HANDOVER_PREPARATION", "SUPPORT_REVIEW", "STABILIZATION"].includes(project.status);
const isActive = (project: Project) => !["COMPLETED", "CANCELLED", "ARCHIVED"].includes(project.status);

export function ProjectManagementPage({ personal = false }: { personal?: boolean }) {
  const { user, hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [view, setView] = useState("mine");
  const summary = useQuery({
    queryKey: ["project-summary"],
    queryFn: async () => (await api.get<Summary>("/projects/portfolio-summary")).data,
    enabled: !personal,
  });
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: async () => (await api.get<Project[]>("/projects")).data,
  });
  const assigned = (projects.data ?? []).filter((project) => project.project_manager_user_id === user?.id);
  const today = new Date().toLocaleDateString("sv-SE");
  const overdue = (project: Project) => isActive(project) && project.status !== "DRAFT"
    && Boolean(project.planned_end_date && project.planned_end_date < today);
  const needsAttention = (project: Project) => isActive(project) && (attention(project) || overdue(project));
  const personalFilters = [
    { key: "mine", label: "All assigned", matches: () => true },
    { key: "attention", label: "Needs attention", matches: needsAttention },
    { key: "draft", label: "Drafts", matches: (project: Project) => project.status === "DRAFT" },
    { key: "intake", label: "Implementation intake", matches: isIntake },
    { key: "handover", label: "Support handover", matches: isHandover },
  ];
  const visible = personal
    ? assigned.filter(personalFilters.find((filter) => filter.key === view)?.matches ?? (() => true))
      .sort((left, right) => Number(needsAttention(right)) - Number(needsAttention(left))
        || (left.planned_end_date ?? "9999").localeCompare(right.planned_end_date ?? "9999"))
    : (projects.data ?? []).filter((project) =>
      view === "attention" ? attention(project) : view === "mine" ? project.project_manager_user_id === user?.id : true,
    ).slice(0, 8);
  const metrics = personal ? [
    { title: "Assigned projects", value: projects.data && assigned.length, icon: <FolderOpenOutlined />, color: "primary.main", filter: "mine" },
    { title: "Needs attention", value: projects.data && assigned.filter(needsAttention).length, icon: <WarningAmber />, color: "warning.main", filter: "attention" },
    { title: "Implementation intake", value: projects.data && assigned.filter(isIntake).length, icon: <AssignmentOutlined />, color: "info.main", filter: "intake" },
  ] : [
    { title: "Projects in scope", value: summary.data?.total, icon: <FolderOpenOutlined />, color: "primary.main" },
    { title: "At risk", value: summary.data?.at_risk, icon: <WarningAmber />, color: "warning.main" },
    { title: "Pending intake", value: summary.data?.pending_assignment_requests, icon: <AssignmentOutlined />, color: "info.main" },
  ];

  return (
    <Stack gap={3} sx={{ p: { xs: 2, md: 3, xl: 4 }, maxWidth: 1440, mx: "auto" }}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ md: "center" }} gap={2}
        sx={personal ? (theme) => ({
          p: { xs: 2.5, md: 4 }, borderRadius: 4, border: 1, borderColor: "divider",
          background: `linear-gradient(118deg, ${alpha(theme.palette.primary.main, 0.16)}, ${theme.palette.background.paper} 72%)`,
        }) : undefined}>
        <Box>
          <Typography variant="h4" component="h1" fontWeight={800}>{personal ? "My Project Work" : "Project Workspace"}</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>{personal
            ? "Follow up on your assigned projects, intake decisions, and Support handovers."
            : "Track delivery, intake decisions, and projects that need your attention."}</Typography>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap">
          {(hasPermission("project.manage.assigned") || hasPermission("project.manage")) && <Button component={Link} to={personal ? projectWorkspacePath : projectMyWorkPath}>
            {personal ? "Project Workspace" : "My Project Work"}
          </Button>}
        {hasPermission("project.create") && (
          <Button variant="contained" startIcon={<Add />} onClick={() => setWizardOpen(true)} sx={{ flexShrink: 0 }}>
            New project
          </Button>
        )}
        </Stack>
      </Stack>
      {(summary.isError || projects.isError) && <Alert severity="error">{apiErrorMessage(summary.error ?? projects.error)}</Alert>}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" }, gap: 2 }}>
        {metrics.map((metric) => {
          const { title, value, icon, color } = metric;
          const filter = "filter" in metric ? metric.filter : undefined;
          return (
          <Paper key={title} variant="outlined" sx={{ borderRadius: 3, overflow: "hidden", borderColor: filter === view ? color : "divider" }}>
          <Box component={filter ? "button" : "div"} {...(filter ? { type: "button", "aria-pressed": filter === view, onClick: () => setView(filter) } : {})}
            sx={{ display: "block", width: "100%", textAlign: "start", p: 2.25, border: 0, bgcolor: "transparent",
              color: "text.primary", font: "inherit", cursor: filter ? "pointer" : "default",
              "&:hover": filter ? { bgcolor: "action.hover" } : undefined, "&:focus-visible": { outline: "2px solid", outlineOffset: -3 } }}>
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
              <Typography color="text.secondary" variant="body2">{title}</Typography>
              <Avatar variant="rounded" sx={{ color, bgcolor: "action.selected", width: 36, height: 36 }}>{icon}</Avatar>
            </Stack>
            <Typography variant="h4" fontWeight={800} sx={{ mt: 1 }}>{value ?? "—"}</Typography>
          </Box>
          </Paper>
        );})}
      </Box>
      <Paper variant="outlined" sx={{ borderRadius: 3, overflow: "hidden" }}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1} sx={{ p: 2 }}>
          <Typography variant="h6" component="h2" fontWeight={750}>{personal ? "My project queue" : "Project queue"}</Typography>
          <Button component={Link} to="/projects" endIcon={<ArrowForward />}>Open portfolio</Button>
        </Stack>
        <Stack direction="row" gap={1} flexWrap="wrap" sx={{ px: 2, pb: 2 }}>
          {(personal ? personalFilters.map(({ key, label }) => [key, label])
            : [["attention", "Needs attention"], ["mine", "My projects"], ["all", "All visible"]]).map(([key, label]) => (
            <Button key={key} size="small" aria-pressed={view === key} variant={view === key ? "contained" : "outlined"}
              onClick={() => setView(key)}>{label}</Button>
          ))}
        </Stack>
        {projects.isPending && <LinearProgress />}
        {projects.isSuccess && !visible.length && (
          <Typography color="text.secondary" sx={{ borderTop: 1, borderColor: "divider", p: 3 }}>
            {view === "attention" ? "No projects need attention right now." : "There are no projects in this view."}
          </Typography>
        )}
        {personal && visible.length > 0 && (
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "repeat(2, minmax(0, 1fr))" }, gap: 1.5, p: 2, bgcolor: "action.hover" }}>
            {visible.map((project) => {
              const path = `/projects/${project.id}`;
              const action = isIntake(project) ? { label: "Review intake", path: `${path}/intake` }
                : isHandover(project) && hasPermission("handover.view") ? { label: "Open handover", path: `${path}/handover` }
                : overdue(project) ? { label: "Review schedule", path: `${path}/schedule` }
                : { label: "Open project", path };
              return (
                <Paper key={project.id} variant="outlined" sx={{ p: 2, borderRadius: 3, minWidth: 0,
                  borderInlineStartWidth: 4, borderInlineStartColor: needsAttention(project) ? "warning.main" : "primary.main" }}>
                  <Stack spacing={1.5} height="100%">
                    <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="flex-start">
                      <Box sx={{ minWidth: 0 }}>
                        <Typography variant="caption" color="text.secondary">{project.project_number}</Typography>
                        <Typography component="h3" fontWeight={750} sx={{ overflowWrap: "anywhere" }}>{project.name}</Typography>
                      </Box>
                      {overdue(project) && <Chip size="small" color="warning" label="Overdue" />}
                    </Stack>
                    <Stack direction="row" gap={1} flexWrap="wrap" alignItems="center">
                      <Chip size="small" variant="outlined" label={project.status.replaceAll("_", " ")} />
                      {project.planned_end_date && <Stack direction="row" gap={0.5} alignItems="center" color="text.secondary">
                        <CalendarTodayOutlined sx={{ fontSize: 14 }} />
                        <Typography variant="caption">Due {project.planned_end_date}</Typography>
                      </Stack>}
                    </Stack>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="caption" color="text.secondary">{project.progress_percent}% complete</Typography>
                      <LinearProgress aria-label={`Progress for ${project.name}`} variant="determinate"
                        value={project.progress_percent} sx={{ mt: 0.5, height: 6, borderRadius: 5 }} />
                    </Box>
                    <Button size="small" component={Link} to={action.path} endIcon={<ArrowForward />}
                      sx={{ alignSelf: "flex-start", textTransform: "none" }}>{action.label}</Button>
                  </Stack>
                </Paper>
              );
            })}
          </Box>
        )}
        {!personal && visible.map((project) => (
          <Stack key={project.id} direction={{ xs: "column", md: "row" }} alignItems={{ md: "center" }} gap={1.5}
            sx={{ py: 1.5, px: 2, borderTop: 1, borderColor: "divider" }}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography fontWeight={750}>{project.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {project.project_number}{project.planned_end_date ? ` · Due ${project.planned_end_date}` : ""}
              </Typography>
            </Box>
            <Chip size="small" label={project.status.replaceAll("_", " ")} variant="outlined" sx={{ alignSelf: { xs: "start", md: "center" } }} />
            {personal && overdue(project) && <Chip size="small" color="warning" label="Overdue" />}
            <Box sx={{ width: { xs: "100%", md: 100 } }}>
              <Typography variant="caption">{project.progress_percent}% complete</Typography>
              <LinearProgress variant="determinate" value={project.progress_percent} />
            </Box>
            <Button size="small" component={Link} to={`/projects/${project.id}/schedule`}>Schedule</Button>
            {isIntake(project) && (
              <Button size="small" component={Link} to={`/projects/${project.id}/intake`}>Intake decisions</Button>
            )}
            {personal && isHandover(project) && hasPermission("handover.view") && (
              <Button size="small" component={Link} to={`/projects/${project.id}/handover`}>Support handover</Button>
            )}
            <Button size="small" component={Link} to={`/projects/${project.id}`}>Open project</Button>
          </Stack>
        ))}
      </Paper>
      {wizardOpen && <ProjectCreationWizard open onClose={() => setWizardOpen(false)} onCreated={() => {
        void queryClient.invalidateQueries({ queryKey: ["projects"] });
        void queryClient.invalidateQueries({ queryKey: ["project-summary"] });
      }} />}
    </Stack>
  );
}
