import { Alert, Box, Button, LinearProgress, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Window = {
  id: number;
  status: string;
  planned_start_at?: string | null;
  planned_end_at?: string | null;
  planned_start_date?: string | null;
  planned_end_date?: string | null;
};
type Plan = {
  phases: (Window & { name: string })[];
  milestones: { id: number; name: string; due_date: string | null; status: string }[];
};
type Task = Window & { task_number: string; title: string };
type ProjectDates = {
  planned_start_date: string | null; planned_end_date: string | null;
  actual_start_date: string | null; actual_end_date: string | null;
};
const variance = (planned: string | null, actual: string | null) => {
  if (!planned || !actual) return "—";
  const days = (Date.parse(actual) - Date.parse(planned)) / 86_400_000;
  return days === 0 ? "On plan" : `${Math.abs(days)} days ${days > 0 ? "late" : "early"}`;
};

export function ProjectSchedulePage() {
  const { id } = useParams();
  const { hasPermission } = useAuth();
  const canViewTasks = hasPermission("implementation.task.view");
  const datesQuery = useQuery({
    queryKey: ["project-schedule-dates", id],
    queryFn: async () => (await api.get<ProjectDates>(`/projects/${id}`)).data,
  });
  const plan = useQuery({
    queryKey: ["project-plan", id],
    queryFn: async () => (await api.get<Plan>(`/projects/${id}/plan`)).data,
  });
  const tasks = useQuery({
    queryKey: ["project-schedule-tasks", id],
    queryFn: async () => (await api.get<Task[]>(`/projects/${id}/tasks`)).data,
    enabled: canViewTasks,
  });
  const rows = [
    ...(plan.data?.phases ?? []).map((phase) => ({ ...phase, label: phase.name, kind: "Phase" })),
    ...(tasks.data ?? []).map((task) => ({ ...task, label: `${task.task_number} · ${task.title}`, kind: "Task" })),
    ...(plan.data?.milestones ?? []).map((milestone) => ({
      ...milestone, label: milestone.name, kind: "Milestone", planned_start_date: milestone.due_date,
      planned_end_date: milestone.due_date, planned_start_at: null, planned_end_at: null,
    })),
  ].map((row) => {
    const start = row.planned_start_at ?? row.planned_start_date;
    const end = row.planned_end_at ?? row.planned_end_date ?? start;
    return { ...row, start, end };
  });
  const dates = rows.flatMap(({ start, end }) => [start, end].flatMap((date) => date ? [Date.parse(date)] : [])).filter(Number.isFinite);
  const first = Math.min(...dates);
  const span = Math.max(1, Math.max(...dates) - first);
  const loading = plan.isPending || (canViewTasks && tasks.isPending);
  const error = datesQuery.error ?? plan.error ?? tasks.error;
  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack direction="row" gap={1} mb={2}>
        <Button component={Link} to="/projects">Projects</Button>
        <Button component={Link} to={`/projects/${id}/execution`}>Execution</Button>
      </Stack>
      <Typography variant="h4" component="h1" gutterBottom>Gantt &amp; Schedule</Typography>
      {datesQuery.data && (
        <Table size="small" aria-label="Project date variance" sx={{ mb: 3, maxWidth: 680 }}>
          <TableHead><TableRow>
            <TableCell>Project date</TableCell><TableCell>Planned</TableCell>
            <TableCell>Actual</TableCell><TableCell>Variance</TableCell>
          </TableRow></TableHead>
          <TableBody>
            {(["start", "end"] as const).map((event) => {
              const planned = datesQuery.data?.[`planned_${event}_date`] ?? null;
              const actual = datesQuery.data?.[`actual_${event}_date`] ?? null;
              return <TableRow key={event}>
                <TableCell component="th" scope="row">{event === "start" ? "Start" : "Completion"}</TableCell>
                <TableCell>{planned ?? "—"}</TableCell><TableCell>{actual ?? "—"}</TableCell>
                <TableCell>{variance(planned, actual)}</TableCell>
              </TableRow>;
            })}
          </TableBody>
        </Table>
      )}
      {loading && <LinearProgress />}
      {error && <Alert severity="error">{apiErrorMessage(error)}</Alert>}
      {!loading && !error && !rows.length && <Alert severity="info">This project has no schedule entries yet.</Alert>}
      {rows.length > 0 && (
        <TableContainer>
          <Table size="small" aria-label="Project schedule">
            <TableHead><TableRow>
              <TableCell>Item</TableCell><TableCell>Status</TableCell><TableCell>Planned start</TableCell>
              <TableCell>Planned end</TableCell><TableCell sx={{ minWidth: 240 }}>Timeline</TableCell>
            </TableRow></TableHead>
            <TableBody>{rows.map((row) => {
              const start = row.start ? Date.parse(row.start) : NaN;
              const end = row.end ? Date.parse(row.end) : NaN;
              return <TableRow key={`${row.kind}-${row.id}`}>
                <TableCell component="th" scope="row">{row.kind} · {row.label}</TableCell>
                <TableCell>{row.status.replaceAll("_", " ")}</TableCell>
                <TableCell>{row.start?.slice(0, 16).replace("T", " ") ?? "—"}</TableCell>
                <TableCell>{row.end?.slice(0, 16).replace("T", " ") ?? "—"}</TableCell>
                <TableCell>{Number.isFinite(start) && Number.isFinite(end) && (
                  <Box aria-hidden sx={{ position: "relative", height: 12, bgcolor: "action.hover" }}>
                    <Box sx={{ position: "absolute", insetBlock: 0, insetInlineStart: `${(start - first) / span * 100}%`,
                      width: `${Math.max(0, end - start) / span * 100}%`, minWidth: 3,
                      bgcolor: row.kind === "Milestone" ? "warning.main" : "primary.main", borderRadius: 1 }} />
                  </Box>
                )}</TableCell>
              </TableRow>;
            })}</TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
