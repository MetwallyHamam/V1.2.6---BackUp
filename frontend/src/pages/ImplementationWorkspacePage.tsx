import { Alert, Box, Button, Chip, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Intake = { id: number; project_id: number; project_number: string; project_name: string; status: string };
type Task = { id: number; project_id: number; task_number: string; title: string; status: string; planned_end_date: string | null };
type DeliveryProject = {
  project_id: number; project_number: string; name: string; status: string; progress_percent: number;
  team_name: string | null; start_date: string | null; end_date: string | null;
};
type CapacityPlan = {
  week_starts: string[];
  teams: Array<{ team_id: number; team_name: string; member_count: number; weeks: Array<{
    week_start: string; planned_minutes: number; capacity_minutes: number; overbooked: boolean;
  }> }>;
  unassigned_projects: Array<{ project_id: number; project_number: string; name: string; start_date: string | null; end_date: string | null }>;
};

export function ImplementationWorkspacePage() {
  const { hasPermission } = useAuth();
  const canReviewIntake = hasPermission("project.assignment.respond");
  const canViewTasks = hasPermission("implementation.task.view");
  const canReviewTasks = hasPermission("implementation.task.review");
  const canViewDelivery = canReviewIntake || hasPermission("implementation.task.assign");
  const inbox = useQuery({
    queryKey: ["implementation-intake"],
    queryFn: async () => (await api.get<Intake[]>("/projects/assignment-requests/inbox")).data,
    enabled: canReviewIntake,
  });
  const work = useQuery({
    queryKey: ["implementation-my-work"],
    queryFn: async () => (await api.get<Task[]>("/project-tasks/my-work")).data,
    enabled: canViewTasks,
  });
  const delivery = useQuery({
    queryKey: ["implementation-delivery-attention"],
    queryFn: async () => (await api.get<Task[]>("/project-tasks/delivery-attention")).data,
    enabled: canReviewTasks,
  });
  const teamDelivery = useQuery({
    queryKey: ["implementation-team-delivery"],
    queryFn: async () => (await api.get<DeliveryProject[]>("/project-tasks/team-delivery")).data,
    enabled: canViewDelivery,
  });
  const capacity = useQuery({
    queryKey: ["implementation-capacity-plan"],
    queryFn: async () => (await api.get<CapacityPlan>("/project-tasks/capacity-plan")).data,
    enabled: canViewDelivery,
  });
  const pending = (inbox.data ?? []).filter((request) => request.status === "PENDING");

  return (
    <Stack spacing={2} sx={{ width: "100%", minWidth: 0 }}>
      <Stack direction={{ xs: "column", sm: "row" }} gap={1} justifyContent="space-between" alignItems={{ sm: "center" }}>
        <Typography component="h1" variant="h4" fontWeight={800}>Implementation Workspace</Typography>
        {hasPermission("analytics.implementation.view") && (
          <Button component={Link} to="/implementation-analytics" variant="outlined">Implementation dashboard</Button>
        )}
      </Stack>
      {canReviewIntake && (
        <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
          <Stack direction={{ xs: "column", sm: "row" }} gap={1} justifyContent="space-between">
            <Typography component="h2" variant="h6">Pending intake {inbox.isSuccess && <Chip size="small" label={pending.length} />}</Typography>
            <Button component={Link} to="/implementation-intake">Open queued projects</Button>
          </Stack>
          {inbox.isPending && <LinearProgress aria-label="Loading intake" />}
          {inbox.isError && <Alert severity="error">{apiErrorMessage(inbox.error)}</Alert>}
          {inbox.isSuccess && !pending.length && <Typography color="text.secondary">No pending intake requests.</Typography>}
          {pending.slice(0, 5).map((request) => (
            <Stack key={request.id} direction="row" gap={1} alignItems="center" justifyContent="space-between"
              sx={{ borderTop: 1, borderColor: "divider", py: 1 }}>
              <Typography>{request.project_number} · {request.project_name}</Typography>
              <Button component={Link} to={`/implementation-intake?project=${request.project_id}`}>Review</Button>
            </Stack>
          ))}
        </Paper>
      )}
      {canViewDelivery && (
        <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
          <Stack direction={{ xs: "column", sm: "row" }} gap={1} justifyContent="space-between">
            <Box><Typography component="h2" variant="h6">Capacity planning</Typography><Typography variant="body2" color="text.secondary">Eight-week forecast at 40 hours per active team member.</Typography></Box>
            <Button component={Link} to="/implementation-intake?view=queue">Assign queued work</Button>
          </Stack>
          {capacity.isPending && <LinearProgress aria-label="Loading capacity plan" sx={{ mt: 1 }} />}
          {capacity.isError && <Alert severity="error">{apiErrorMessage(capacity.error)}</Alert>}
          {!!capacity.data?.unassigned_projects.length && <Alert severity="warning" sx={{ my: 1 }}>{capacity.data.unassigned_projects.length} accepted project(s) still need a delivery team.</Alert>}
          <Box sx={{ overflowX: "auto", mt: 1 }}>
            <Box sx={{ display: "grid", gridTemplateColumns: `minmax(150px, 1.4fr) repeat(${capacity.data?.week_starts.length ?? 0}, minmax(105px, 1fr))`, minWidth: 900, gap: .75 }}>
              {capacity.data && <><Typography fontWeight={800}>Team</Typography>{capacity.data.week_starts.map((week) => <Typography key={week} variant="caption" fontWeight={800}>{new Date(`${week}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</Typography>)}
              {capacity.data.teams.map((team) => <Box key={team.team_id} sx={{ display: "contents" }}><Box><Typography fontWeight={750}>{team.team_name}</Typography><Typography variant="caption" color="text.secondary">{team.member_count} member(s)</Typography></Box>{team.weeks.map((week) => { const percent = week.capacity_minutes ? Math.round(week.planned_minutes / week.capacity_minutes * 100) : week.planned_minutes ? 100 : 0; return <Paper key={week.week_start} variant="outlined" sx={{ p: .75, bgcolor: week.overbooked ? "error.main" : percent >= 80 ? "warning.light" : "background.paper", color: week.overbooked ? "error.contrastText" : "text.primary" }}><Typography fontWeight={800}>{percent}%</Typography><Typography variant="caption">{Math.round(week.planned_minutes / 60)}h / {Math.round(week.capacity_minutes / 60)}h</Typography></Paper>; })}</Box>)}
              {!capacity.data.teams.length && <Typography color="text.secondary">No active delivery teams are available in your scope.</Typography>}</>}
            </Box>
          </Box>
        </Paper>
      )}
      {canViewDelivery && (
        <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
          <Typography component="h2" variant="h6" gutterBottom>Team delivery</Typography>
          {teamDelivery.isPending && <LinearProgress aria-label="Loading team delivery" />}
          {teamDelivery.isError && <Alert severity="error">{apiErrorMessage(teamDelivery.error)}</Alert>}
          {teamDelivery.isSuccess && !teamDelivery.data.length && <Typography color="text.secondary">No accepted projects in your delivery scope.</Typography>}
          {(teamDelivery.data ?? []).map((project) => (
            <Stack key={project.project_id} direction={{ xs: "column", sm: "row" }} gap={1.5}
              alignItems={{ sm: "center" }} sx={{ borderTop: 1, borderColor: "divider", py: 1.5 }}>
              <Stack sx={{ flex: 1, minWidth: 0 }}>
                <Typography fontWeight={750}>{project.project_number} · {project.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {project.team_name ?? "Team unassigned"} · {project.start_date ?? "No start"} to {project.end_date ?? "No finish"}
                </Typography>
              </Stack>
              <Chip size="small" label={project.status.replaceAll("_", " ")} sx={{ alignSelf: "flex-start" }} />
              <Typography variant="body2">{project.progress_percent}% complete</Typography>
              {canViewTasks && hasPermission("project.portfolio.view") && (
                <Button component={Link} to={`/projects/${project.project_id}/execution`}>Open delivery plan</Button>
              )}
            </Stack>
          ))}
          {teamDelivery.data?.length === 50 && <Typography variant="caption">Showing the first 50 accepted projects.</Typography>}
        </Paper>
      )}
      {canViewTasks && (
        <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
          <Typography component="h2" variant="h6" gutterBottom>My assigned tasks</Typography>
          {work.isPending && <LinearProgress aria-label="Loading assigned tasks" />}
          {work.isError && <Alert severity="error">{apiErrorMessage(work.error)}</Alert>}
          {work.isSuccess && !work.data.length && <Typography color="text.secondary">No active assigned tasks.</Typography>}
          {(work.data ?? []).map((task) => (
            <Stack key={task.id} direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}
              sx={{ borderTop: 1, borderColor: "divider", py: 1 }}>
              <Stack sx={{ flex: 1, minWidth: 0 }}>
                <Typography fontWeight={700}>{task.title}</Typography>
                <Typography variant="caption" color="text.secondary">{task.task_number}{task.planned_end_date && ` · Due ${task.planned_end_date}`}</Typography>
              </Stack>
              <Chip size="small" label={task.status.replaceAll("_", " ")} sx={{ alignSelf: "flex-start" }} />
              {hasPermission("project.portfolio.view") && (
                <Button component={Link} to={`/projects/${task.project_id}/work-packages?item=task-${task.id}`}>Open task</Button>
              )}
            </Stack>
          ))}
        </Paper>
      )}
      {canReviewTasks && (
        <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
          <Typography component="h2" variant="h6">Delivery attention</Typography>
          {delivery.isPending && <LinearProgress aria-label="Loading delivery attention" />}
          {delivery.isError && <Alert severity="error">{apiErrorMessage(delivery.error)}</Alert>}
          {delivery.isSuccess && !delivery.data.length && <Typography color="text.secondary">No blocked tasks or tasks awaiting review in your delivery department.</Typography>}
          {(delivery.data ?? []).map((task) => (
            <Stack key={task.id} direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}
              sx={{ borderTop: 1, borderColor: "divider", py: 1 }}>
              <Typography sx={{ flex: 1 }}>{task.task_number} · {task.title}</Typography>
              <Chip size="small" label={task.status === "REVIEW" ? "Ready for review" : "Blocked"} sx={{ alignSelf: "flex-start" }} />
              {canViewTasks && hasPermission("project.portfolio.view") && (
                <Button component={Link} to={`/projects/${task.project_id}/work-packages?item=task-${task.id}`}>Open task</Button>
              )}
            </Stack>
          ))}
          {delivery.data?.length === 30 && <Typography variant="caption">Showing the first 30 tasks by planned finish.</Typography>}
        </Paper>
      )}
    </Stack>
  );
}
