import {
  Alert, Button, Drawer, LinearProgress, MenuItem, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useOutletContext, useParams, useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Project } from "./ProjectWorkspacePage";

type Milestone = { id: number; name: string; status: string; due_date: string | null };
type Task = {
  id: number;
  task_number: string;
  title: string;
  status: string;
  planned_end_date: string | null;
  planned_end_at?: string | null;
  owner_user_id: number;
  progress_percent: number;
  actual_minutes: number;
};

function MilestoneScheduleEditor({ project, milestone }: { project: Project; milestone: Milestone }) {
  const queryClient = useQueryClient();
  const [date, setDate] = useState(milestone.due_date ?? "");
  const [version, setVersion] = useState(project.row_version);
  const save = useMutation({
    mutationFn: () => api.patch(`/projects/${project.id}/milestones/${milestone.id}/schedule`, {
      due_date: date || null,
      expected_version: version,
    }),
    onSuccess: async () => {
      setVersion(version + 1);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project", project.id] }),
        queryClient.invalidateQueries({ queryKey: ["project-plan", String(project.id)] }),
      ]);
    },
  });
  return (
    <Stack component="form" spacing={1} onSubmit={(event) => {
      event.preventDefault();
      save.mutate();
    }}>
      <TextField type="date" label="Planned finish" slotProps={{ inputLabel: { shrink: true } }}
        value={date} onChange={(event) => setDate(event.target.value)} />
      {save.isError && <Alert severity="error">{apiErrorMessage(save.error)}</Alert>}
      {save.isSuccess && <Alert severity="success">Milestone schedule saved.</Alert>}
      <Button type="submit" variant="contained" disabled={save.isPending || date === (milestone.due_date ?? "") || version !== project.row_version}>
        Save planned finish
      </Button>
    </Stack>
  );
}

export function ProjectWorkPackagesPage() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const { hasPermission, user } = useAuth();
  const project = useOutletContext<Project>();
  const canEditSchedule = project.status === "DRAFT" && (
    hasPermission("project.manage")
    || (hasPermission("project.manage.assigned") && project.project_manager_user_id === user?.id)
  );
  const canViewTasks = hasPermission("implementation.task.view");
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const plan = useQuery({
    queryKey: ["project-plan", id],
    queryFn: async () => (await api.get<{ milestones: Milestone[] }>(`/projects/${id}/plan`)).data,
  });
  const tasks = useQuery({
    queryKey: ["project-tasks", Number(id)],
    queryFn: async () => (await api.get<Task[]>(`/projects/${id}/tasks`)).data,
    enabled: canViewTasks,
  });
  const rows = [
    ...(plan.data?.milestones ?? []).map((item) => ({
      key: `milestone-${item.id}`, kind: "Milestone", label: item.name,
      status: item.status, due: item.due_date, task: null, milestone: item,
    })),
    ...(canViewTasks ? tasks.data ?? [] : []).map((item) => ({
      key: `task-${item.id}`, kind: "Task", label: `${item.task_number} · ${item.title}`,
      status: item.status, due: item.planned_end_at ?? item.planned_end_date, task: item, milestone: null,
    })),
  ];
  const states = [...new Set(rows.map((row) => row.status))].sort();
  const selectedStatus = states.includes(status) ? status : "";
  const visible = rows.filter((row) =>
    (!kind || row.kind === kind) && (!selectedStatus || row.status === selectedStatus)
    && row.label.toLowerCase().includes(search.trim().toLowerCase()),
  );
  const loading = plan.isPending || (canViewTasks && tasks.isPending);
  const error = plan.error ?? (canViewTasks ? tasks.error : null);
  const itemKey = params.get("item");
  const selected = rows.find((row) => row.key === itemKey);
  const owners = useQuery({
    queryKey: ["project-options"],
    queryFn: async () => (await api.get<{ managers: { id: number; name: string }[] }>("/projects/options")).data,
    enabled: Boolean(selected?.task),
  });
  const ownerId = selected?.task?.owner_user_id;
  const owner = owners.data?.managers.find((manager) => manager.id === ownerId);

  function itemLocation(key: string) {
    const next = new URLSearchParams(params);
    next.set("item", key);
    return { search: next.toString() };
  }

  function closeDetails() {
    const next = new URLSearchParams(params);
    next.delete("item");
    setParams(next, { replace: true });
  }

  return (
    <Stack spacing={2}>
      <Typography component="h2" variant="h6">Work packages</Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField size="small" label="Search work packages" value={search} onChange={(event) => setSearch(event.target.value)} />
        <TextField select size="small" label="Type" value={kind} onChange={(event) => setKind(event.target.value)} sx={{ minWidth: 140 }}>
          <MenuItem value="">All types</MenuItem>
          <MenuItem value="Milestone">Milestone</MenuItem>
          {canViewTasks && <MenuItem value="Task">Task</MenuItem>}
        </TextField>
        <TextField select size="small" label="Status" value={selectedStatus} onChange={(event) => setStatus(event.target.value)} sx={{ minWidth: 170 }}>
          <MenuItem value="">All statuses</MenuItem>
          {states.map((state) => <MenuItem key={state} value={state}>{state.replaceAll("_", " ")}</MenuItem>)}
        </TextField>
      </Stack>
      {loading && <LinearProgress aria-label="Loading work packages" />}
      {error && <Alert severity="error">{apiErrorMessage(error)}</Alert>}
      <TableContainer>
        <Table size="small" aria-label="Project work packages">
          <TableHead>
            <TableRow><TableCell>Work package</TableCell><TableCell>Type</TableCell><TableCell>Status</TableCell><TableCell>Planned finish</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {visible.map((row) => (
              <TableRow key={row.key}>
                <TableCell component="th" scope="row">
                  <Button component={Link} to={itemLocation(row.key)} sx={{ textAlign: "start", textTransform: "none" }}>
                    {row.label}
                  </Button>
                </TableCell>
                <TableCell>{row.kind}</TableCell>
                <TableCell>{row.status.replaceAll("_", " ")}</TableCell>
                <TableCell>{row.due?.slice(0, 10) ?? "—"}</TableCell>
              </TableRow>
            ))}
            {!loading && !error && !visible.length && (
              <TableRow><TableCell colSpan={4}>No matching work packages.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <Drawer anchor="right" open={Boolean(itemKey)} onClose={closeDetails}>
        <Stack role="region" aria-label="Work package details" spacing={2} sx={{ p: 3, width: { xs: "100vw", sm: 420 } }}>
          <Button onClick={closeDetails} sx={{ alignSelf: "flex-start" }}>Close details</Button>
          {selected ? (
            <>
              <Typography component="h2" variant="h5">{selected.label}</Typography>
              <Typography>{selected.kind} · {selected.status.replaceAll("_", " ")}</Typography>
              <Typography>Planned finish {selected.due?.slice(0, 10) ?? "—"}</Typography>
              {selected.task && (
                <>
                  <Typography>Owner {owner?.name ?? `#${ownerId}`}</Typography>
                  <Typography>{selected.task.progress_percent}% complete · {selected.task.actual_minutes ?? 0} min logged</Typography>
                  <Button component={Link} to="../execution" sx={{ alignSelf: "flex-start" }}>Open Implementation board</Button>
                </>
              )}
              {!selected.task && <Button component={Link} to="../schedule" sx={{ alignSelf: "flex-start" }}>Open schedule</Button>}
              {canEditSchedule && selected.milestone && (
                <MilestoneScheduleEditor key={selected.key} project={project} milestone={selected.milestone} />
              )}
            </>
          ) : loading ? <LinearProgress aria-label="Loading work package" /> : (
            <Alert severity="info">{error ? apiErrorMessage(error) : "This work package is unavailable."}</Alert>
          )}
        </Stack>
      </Drawer>
    </Stack>
  );
}
