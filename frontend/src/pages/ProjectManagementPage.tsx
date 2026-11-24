import { Add, ArrowForward, AssignmentOutlined, FolderOpenOutlined, WarningAmber } from "@mui/icons-material";
import { Alert, Box, Button, Chip, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ProjectCreationWizard } from "../components/ProjectCreationWizard";

type Summary = { total: number; at_risk: number; pending_assignment_requests: number };
type Project = {
  id: number; project_number: string; name: string; status: string; health: string;
  progress_percent: number; planned_end_date: string | null; project_manager_user_id: number;
};
const attention = (project: Project) =>
  ["AT_RISK", "CRITICAL"].includes(project.health) ||
  ["INTAKE_RETURNED", "INTAKE_PROPOSED", "INTAKE_REJECTED", "ON_HOLD"].includes(project.status);

export function ProjectManagementPage() {
  const { user, hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [view, setView] = useState<"attention" | "mine" | "all">("mine");
  const summary = useQuery({
    queryKey: ["project-summary"],
    queryFn: async () => (await api.get<Summary>("/projects/portfolio-summary")).data,
  });
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: async () => (await api.get<Project[]>("/projects")).data,
  });
  const rows = (projects.data ?? []).filter((project) =>
    view === "attention" ? attention(project) : view === "mine" ? project.project_manager_user_id === user?.id : true,
  ).slice(0, 8);
  const metrics = [
    { title: "Projects in scope", value: summary.data?.total, icon: <FolderOpenOutlined />, color: "primary.main" },
    { title: "At risk", value: summary.data?.at_risk, icon: <WarningAmber />, color: "warning.main" },
    { title: "Pending intake", value: summary.data?.pending_assignment_requests, icon: <AssignmentOutlined />, color: "info.main" },
  ];

  return (
    <Stack gap={3} sx={{ p: { xs: 2, md: 3, xl: 4 }, maxWidth: 1440, mx: "auto" }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }} gap={2}>
        <Box>
          <Typography variant="h4" component="h1" fontWeight={800}>Project overview</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>Track delivery, intake decisions, and projects that need your attention.</Typography>
        </Box>
        {hasPermission("project.create") && (
          <Button variant="contained" startIcon={<Add />} onClick={() => setWizardOpen(true)} sx={{ flexShrink: 0 }}>
            New project
          </Button>
        )}
      </Stack>
      {(summary.isError || projects.isError) && <Alert severity="error">{apiErrorMessage(summary.error ?? projects.error)}</Alert>}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" }, gap: 2 }}>
        {metrics.map(({ title, value, icon, color }) => (
          <Paper key={title} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
              <Typography color="text.secondary" variant="body2">{title}</Typography>
              <Box sx={{ color, display: "flex" }}>{icon}</Box>
            </Stack>
            <Typography variant="h4" fontWeight={800} sx={{ mt: 1 }}>{value ?? "—"}</Typography>
          </Paper>
        ))}
      </Box>
      <Paper variant="outlined" sx={{ borderRadius: 3, overflow: "hidden" }}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1} sx={{ p: 2 }}>
          <Typography variant="h6" component="h2" fontWeight={750}>Project queue</Typography>
          <Button component={Link} to="/projects" endIcon={<ArrowForward />}>Open portfolio</Button>
        </Stack>
        <Stack direction="row" gap={1} flexWrap="wrap" sx={{ px: 2, pb: 2 }}>
          {([["attention", "Needs attention"], ["mine", "My projects"], ["all", "All visible"]] as const).map(([key, label]) => (
            <Button key={key} size="small" aria-pressed={view === key} variant={view === key ? "contained" : "outlined"}
              onClick={() => setView(key)}>{label}</Button>
          ))}
        </Stack>
        {projects.isPending && <LinearProgress />}
        {projects.isSuccess && !rows.length && (
          <Typography color="text.secondary" sx={{ borderTop: 1, borderColor: "divider", p: 3 }}>
            {view === "attention" ? "No projects need attention right now." : "There are no projects in this view."}
          </Typography>
        )}
        {rows.map((project) => (
          <Stack key={project.id} direction={{ xs: "column", md: "row" }} alignItems={{ md: "center" }} gap={1.5}
            sx={{ py: 1.5, px: 2, borderTop: 1, borderColor: "divider" }}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography fontWeight={750}>{project.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {project.project_number}{project.planned_end_date ? ` · Due ${project.planned_end_date}` : ""}
              </Typography>
            </Box>
            <Chip size="small" label={project.status.replaceAll("_", " ")} variant="outlined" sx={{ alignSelf: { xs: "start", md: "center" } }} />
            <Box sx={{ width: { xs: "100%", md: 100 } }}>
              <Typography variant="caption">{project.progress_percent}% complete</Typography>
              <LinearProgress variant="determinate" value={project.progress_percent} />
            </Box>
            <Button size="small" component={Link} to={`/projects/${project.id}/schedule`}>Schedule</Button>
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
