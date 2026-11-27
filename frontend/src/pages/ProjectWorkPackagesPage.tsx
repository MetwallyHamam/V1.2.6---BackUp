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
type Dependency = { task_id: number; depends_on_task_id: number; dependency_type: string };
type MilestoneRevision = {
  id: number; milestone_id: number; previous_due_date: string | null; due_date: string | null;
  reason: string; status: string; requested_by_user_id: number; project_version: number;
  task_id?: number; task_number?: string; task_title?: string;
  previous?: RevisionPlan; proposed?: RevisionPlan;
};
type RevisionPlan = { planned_start_date?: string | null; planned_end_date?: string | null; predecessor_ids?: number[] };

function revisionPlan(plan?: RevisionPlan) {
  if (plan?.predecessor_ids) return plan.predecessor_ids.length
    ? `Predecessor IDs ${plan.predecessor_ids.join(", ")}` : "No predecessors";
  return `${plan?.planned_start_date ?? "Unscheduled"} → ${plan?.planned_end_date ?? "Unscheduled"}`;
}

function useMilestoneRevisions(projectId: number) {
  return useQuery({
    queryKey: ["project-milestone-revisions", projectId],
    queryFn: async () => (await api.get<MilestoneRevision[]>(`/projects/${projectId}/milestone-revisions`)).data,
  });
}

function proposedVariance(baseline: string | null | undefined, proposed: string | null) {
  if (!baseline || !proposed) return "—";
  const days = (Date.parse(proposed) - Date.parse(baseline)) / 86_400_000;
  if (!Number.isFinite(days)) return "—";
  if (days === 0) return "On baseline";
  const distance = Math.abs(days);
  return `${distance} ${distance === 1 ? "day" : "days"} ${days > 0 ? "later" : "earlier"}`;
}

export function ProjectRevisionQueue() {
  const project = useOutletContext<Project>();
  const [params] = useSearchParams();
  const revisionFilter = params.get("revision");
  const revisions = useMilestoneRevisions(project.id);
  const plan = useQuery({
    queryKey: ["project-plan", String(project.id)],
    queryFn: async () => (await api.get<{ milestones: Milestone[] }>(`/projects/${project.id}/plan`)).data,
  });
  const baseline = useQuery({
    queryKey: ["project-schedule-baseline", String(project.id)],
    queryFn: async () => (await api.get<{
      items: { Milestone?: Record<string, { end: string | null }> };
    } | null>(`/projects/${project.id}/schedule-baseline`)).data,
  });
  const [status, setStatus] = useState(revisionFilter ? "" : "PENDING");
  const milestones = new Map((plan.data?.milestones ?? []).map((item) => [item.id, item.name]));
  const rows = (revisions.data ?? []).filter((revision) =>
    (!status || revision.status === status) && (!revisionFilter || String(revision.id) === revisionFilter));
  const error = revisions.error ?? plan.error;

  return (
    <Stack spacing={2}>
      <Typography component="h2" variant="h6">Schedule revisions</Typography>
      <TextField select size="small" label="Revision status" value={status} sx={{ alignSelf: "flex-start", minWidth: 170 }}
        onChange={(event) => setStatus(event.target.value)}>
        <MenuItem value="">All statuses</MenuItem>
        <MenuItem value="PENDING">Pending</MenuItem>
        <MenuItem value="APPROVED">Approved</MenuItem>
        <MenuItem value="REJECTED">Rejected</MenuItem>
      </TextField>
      {revisionFilter && <Button component={Link} to="../revisions" sx={{ alignSelf: "flex-start" }}>Show all revisions</Button>}
      {(revisions.isPending || plan.isPending) && <LinearProgress aria-label="Loading schedule revisions" />}
      {error && <Alert severity="error">{apiErrorMessage(error)}</Alert>}
      {baseline.isError && <Alert severity="warning">The schedule baseline could not be loaded.</Alert>}
      {revisions.isSuccess && !rows.length && <Typography>No matching revisions.</Typography>}
      <TableContainer>
        <Table size="small" aria-label="Project schedule revisions">
          <TableHead><TableRow>
            <TableCell>Work package</TableCell>
            {baseline.data && <TableCell>Baseline finish</TableCell>}
            <TableCell>Previous plan</TableCell>
            <TableCell>Proposed plan</TableCell>
            {baseline.data && <TableCell>Proposed variance</TableCell>}
            <TableCell>Status</TableCell><TableCell>Reason</TableCell>
          </TableRow></TableHead>
          <TableBody>{rows.map((revision) => (
            <TableRow key={revision.id}>
              <TableCell component="th" scope="row">
                <Button component={Link} to={`../work-packages?item=${revision.task_id ? `task-${revision.task_id}` : `milestone-${revision.milestone_id}`}`}
                  sx={{ textTransform: "none", textAlign: "start" }}>
                  {revision.task_id ? `${revision.task_number} · ${revision.task_title}` : milestones.get(revision.milestone_id) ?? `Milestone #${revision.milestone_id}`}
                </Button>
              </TableCell>
              {baseline.data && (
                <TableCell>{baseline.data.items.Milestone?.[revision.milestone_id]?.end ?? "—"}</TableCell>
              )}
              <TableCell>{revision.task_id ? revisionPlan(revision.previous) : revision.previous_due_date ?? "Unscheduled"}</TableCell>
              <TableCell>{revision.task_id ? revisionPlan(revision.proposed) : revision.due_date ?? "Unscheduled"}</TableCell>
              {baseline.data && (
                <TableCell>{proposedVariance(baseline.data.items.Milestone?.[revision.milestone_id]?.end, revision.due_date)}</TableCell>
              )}
              <TableCell>
                {revision.status}
                {revision.status === "PENDING" && revision.project_version !== project.row_version && (
                  <Typography variant="caption" display="block" color="warning.main">Plan version changed</Typography>
                )}
              </TableCell>
              <TableCell sx={{ overflowWrap: "anywhere" }}>{revision.reason}</TableCell>
            </TableRow>
          ))}</TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}
type Task = {
  id: number;
  task_number: string;
  title: string;
  status: string;
  planned_start_date: string | null;
  planned_start_at?: string | null;
  planned_end_date: string | null;
  planned_end_at?: string | null;
  owner_user_id: number;
  progress_percent: number;
  actual_minutes: number;
};

function DependencyEditor({ project, taskId, tasks, predecessors }: {
  project: Project; taskId: number; tasks: Task[]; predecessors: number[];
}) {
  const client = useQueryClient();
  const [version, setVersion] = useState(project.row_version);
  const [selected, setSelected] = useState(predecessors);
  const [reason, setReason] = useState("");
  const published = project.status !== "DRAFT";
  const save = useMutation({
    mutationFn: async () => published
      ? (await api.post(`/projects/${project.id}/tasks/${taskId}/revisions`, {
        reason: reason.trim(), dependencies: { expected_version: version, predecessor_ids: selected },
      })).data
      : (await api.put<{ row_version: number }>(
      `/projects/${project.id}/tasks/${taskId}/dependencies`,
      { expected_version: version, predecessor_ids: selected },
    )).data,
    onSuccess: async (result) => {
      if (published) {
        setReason("");
        await client.invalidateQueries({ queryKey: ["project-milestone-revisions", project.id] });
        return;
      }
      setVersion(result.row_version);
      await Promise.all([
        client.invalidateQueries({ queryKey: ["project", project.id] }),
        client.invalidateQueries({ queryKey: ["project-task-dependencies", String(project.id)] }),
      ]);
    },
  });
  return (
    <Stack component="form" spacing={1} onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
      <Typography component="label" htmlFor="task-predecessors">Task predecessors</Typography>
      <select id="task-predecessors" multiple value={selected.map(String)} disabled={save.isPending}
        onChange={(event) => setSelected(Array.from(event.target.selectedOptions, (option) => Number(option.value)))}>
        {tasks.filter((task) => task.id !== taskId).map((task) => (
          <option key={task.id} value={task.id}>{task.task_number} · {task.title}</option>
        ))}
      </select>
      {published && <TextField label="Dependency change reason" required value={reason}
        onChange={(event) => setReason(event.target.value)} slotProps={{ htmlInput: { maxLength: 500 } }} />}
      {save.isError && <Alert severity="error">{apiErrorMessage(save.error)}</Alert>}
      {version !== project.row_version && !save.isPending && <Alert severity="warning">Reopen the task to load the latest plan.</Alert>}
      <Button type="submit" disabled={save.isPending || version !== project.row_version || (published && !reason.trim())}>
        {published ? "Propose predecessors" : "Save predecessors"}
      </Button>
    </Stack>
  );
}

function MilestoneRevisions({ project, milestone, task }: { project: Project; milestone?: Milestone; task?: Task }) {
  const { hasPermission, user } = useAuth();
  const client = useQueryClient();
  const [date, setDate] = useState(milestone?.due_date ?? "");
  const [reason, setReason] = useState("");
  const key = ["project-milestone-revisions", project.id];
  const revisions = useMilestoneRevisions(project.id);
  const request = useMutation({
    mutationFn: () => api.post(`/projects/${project.id}/milestones/${milestone?.id}/revisions`, {
      due_date: date || null, reason: reason.trim(), expected_version: project.row_version,
    }),
    onSuccess: async () => {
      setReason("");
      await client.invalidateQueries({ queryKey: key });
    },
  });
  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: number; decision: "APPROVED" | "REJECTED" }) =>
      api.post(`/projects/${project.id}/milestone-revisions/${id}/decision`, {
        decision, expected_version: project.row_version,
      }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: key }),
        client.invalidateQueries({ queryKey: ["project", project.id] }),
        client.invalidateQueries({ queryKey: ["project-plan", String(project.id)] }),
        client.invalidateQueries({ queryKey: ["project-tasks", project.id] }),
        client.invalidateQueries({ queryKey: ["project-schedule-tasks", String(project.id)] }),
        client.invalidateQueries({ queryKey: ["project-task-dependencies", String(project.id)] }),
      ]);
    },
  });
  const reviewer = hasPermission("project.manage");
  const canRequest = ["AWAITING_IMPLEMENTATION_ACCEPTANCE", "READY_FOR_EXECUTION", "IN_EXECUTION", "ON_HOLD"].includes(project.status)
    && (reviewer || (hasPermission("project.manage.assigned") && user?.id === project.project_manager_user_id));
  const error = revisions.error ?? request.error ?? decide.error;
  const rows = (revisions.data ?? []).filter((revision) => task
    ? revision.task_id === task.id : revision.milestone_id === milestone?.id && !revision.task_id);
  return (
    <Stack spacing={1}>
      <Typography component="h3" variant="subtitle1">Schedule revisions</Typography>
      {error && <Alert severity="error">{apiErrorMessage(error)}</Alert>}
      {revisions.isPending && <LinearProgress aria-label="Loading revisions" />}
      {revisions.isSuccess && !rows.length && <Typography>No schedule revisions.</Typography>}
      {rows.map((revision) => (
        <Stack key={revision.id} spacing={0.5}>
          <Typography>{revision.task_id ? revisionPlan(revision.previous) : revision.previous_due_date ?? "Unscheduled"} → {revision.task_id ? revisionPlan(revision.proposed) : revision.due_date ?? "Unscheduled"} · {revision.status}</Typography>
          <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>{revision.reason}</Typography>
          {reviewer && revision.status === "PENDING" && revision.requested_by_user_id !== user?.id && (
            <Stack direction="row">
              <Button disabled={decide.isPending || revision.project_version !== project.row_version}
                onClick={() => decide.mutate({ id: revision.id, decision: "APPROVED" })}>Approve</Button>
              <Button disabled={decide.isPending}
                onClick={() => decide.mutate({ id: revision.id, decision: "REJECTED" })}>Reject</Button>
            </Stack>
          )}
        </Stack>
      ))}
      {canRequest && milestone && (
        <Stack component="form" spacing={1} onSubmit={(event) => { event.preventDefault(); request.mutate(); }}>
          <TextField type="date" label="Proposed finish" slotProps={{ inputLabel: { shrink: true } }}
            value={date} onChange={(event) => setDate(event.target.value)} />
          <TextField label="Reason" required multiline value={reason} onChange={(event) => setReason(event.target.value)}
            slotProps={{ htmlInput: { maxLength: 500 } }} />
          <Button type="submit" disabled={request.isPending || !reason.trim() || date === (milestone.due_date ?? "")}>Request revision</Button>
        </Stack>
      )}
    </Stack>
  );
}

function DeliveryOwnerEditor({ project, task }: { project: Project; task: Task }) {
  const client = useQueryClient();
  const [owner, setOwner] = useState("");
  const options = useQuery({
    queryKey: ["delivery-owner-options", project.id],
    queryFn: async () => (await api.get<{ id: number; name: string }[]>(
      `/projects/${project.id}/delivery-owner-options`,
    )).data,
    retry: false,
  });
  const save = useMutation({
    mutationFn: () => api.put(`/project-tasks/${task.id}/owner`, {
      expected_owner_user_id: task.owner_user_id, owner_user_id: Number(owner),
    }),
    onSuccess: async () => {
      setOwner("");
      await Promise.all([
        client.invalidateQueries({ queryKey: ["project-tasks", project.id] }),
        client.invalidateQueries({ queryKey: ["implementation-my-work"] }),
        client.invalidateQueries({ queryKey: ["implementation-delivery-attention"] }),
      ]);
    },
  });
  if (options.isPending) return <LinearProgress aria-label="Loading eligible engineers" />;
  if (options.isError) return <Alert severity="info">Owner assignment is unavailable for this delivery team.</Alert>;
  const eligible = options.data.filter((option) => option.id !== task.owner_user_id);
  if (!eligible.length) return <Typography variant="body2" color="text.secondary">No other eligible owner is available.</Typography>;
  return (
    <Stack component="form" spacing={1} onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
      <TextField select label="New accountable owner" value={owner} onChange={(event) => setOwner(event.target.value)}>
        {eligible.map((option) => <MenuItem key={option.id} value={String(option.id)}>{option.name}</MenuItem>)}
      </TextField>
      {save.isError && <Alert severity="error">{apiErrorMessage(save.error)}</Alert>}
      <Button type="submit" disabled={!owner || save.isPending}>Change task owner</Button>
    </Stack>
  );
}

function TaskScheduleEditor({ project, task }: { project: Project; task: Task }) {
  const client = useQueryClient();
  const [start, setStart] = useState((task.planned_start_at ?? task.planned_start_date)?.slice(0, 10) ?? "");
  const [end, setEnd] = useState((task.planned_end_at ?? task.planned_end_date)?.slice(0, 10) ?? "");
  const [version, setVersion] = useState(project.row_version);
  const [reason, setReason] = useState("");
  const published = project.status !== "DRAFT";
  const save = useMutation({
    mutationFn: async () => {
      const schedule = { expected_version: version, planned_start_date: start, planned_end_date: end };
      if (published) {
        await api.post(`/projects/${project.id}/tasks/${task.id}/revisions`, { reason: reason.trim(), schedule });
      } else {
        await api.patch(`/projects/${project.id}/tasks/${task.id}/schedule`, schedule);
      }
    },
    onSuccess: async () => {
      if (published) {
        setReason("");
        await client.invalidateQueries({ queryKey: ["project-milestone-revisions", project.id] });
        return;
      }
      setVersion(version + 1);
      await Promise.all([
        client.invalidateQueries({ queryKey: ["project", project.id] }),
        client.invalidateQueries({ queryKey: ["project-tasks", project.id] }),
        client.invalidateQueries({ queryKey: ["project-schedule-tasks", String(project.id)] }),
      ]);
    },
  });
  return (
    <Stack component="form" spacing={1} onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
      <Typography component="h3" variant="subtitle1">Task schedule</Typography>
      <TextField type="date" required label="Planned start" slotProps={{ inputLabel: { shrink: true } }}
        value={start} onChange={(event) => setStart(event.target.value)} />
      <TextField type="date" required label="Planned finish" slotProps={{ inputLabel: { shrink: true } }}
        value={end} onChange={(event) => setEnd(event.target.value)} />
      {save.isError && <Alert severity="error">{apiErrorMessage(save.error)}</Alert>}
      {published && <TextField label="Schedule change reason" required value={reason} onChange={(event) => setReason(event.target.value)}
        slotProps={{ htmlInput: { maxLength: 500 } }} />}
      {save.isSuccess && <Alert severity="success">{published ? "Schedule revision submitted." : "Task schedule saved."}</Alert>}
      {version !== project.row_version && !save.isPending && <Alert severity="warning">Reopen the task to load the latest plan.</Alert>}
      <Button type="submit" disabled={save.isPending || !start || !end || end < start || version !== project.row_version || (published && !reason.trim())}>
        {published ? "Propose task schedule" : "Save task schedule"}
      </Button>
    </Stack>
  );
}

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
  const canManagePlan = (
    hasPermission("project.manage")
    || (hasPermission("project.manage.assigned") && project.project_manager_user_id === user?.id)
  );
  const canEditSchedule = project.status === "DRAFT" && canManagePlan;
  const canPropose = canManagePlan && ["AWAITING_IMPLEMENTATION_ACCEPTANCE", "READY_FOR_EXECUTION", "IN_EXECUTION", "ON_HOLD"].includes(project.status);
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
  const taskId = selected?.task?.id;
  const dependencies = useQuery({
    queryKey: ["project-task-dependencies", id],
    queryFn: async () => (await api.get<Dependency[]>(`/projects/${id}/task-dependencies`)).data,
    enabled: canViewTasks && taskId !== undefined,
  });
  const taskById = new Map((canViewTasks ? tasks.data ?? [] : []).map((task) => [task.id, task]));
  const relations = (dependencies.data ?? []).flatMap((dependency) => {
    const predecessor = dependency.task_id === taskId;
    if (!predecessor && dependency.depends_on_task_id !== taskId) return [];
    const related = taskById.get(predecessor ? dependency.depends_on_task_id : dependency.task_id);
    return related ? [{
      task: related,
      direction: predecessor ? "Predecessor" : "Successor",
      type: dependency.dependency_type.replaceAll("_", " ").toLowerCase(),
    }] : [];
  });
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
                  {hasPermission("implementation.task.assign")
                    && ["READY_FOR_EXECUTION", "IN_EXECUTION"].includes(project.status)
                    && ["BACKLOG", "READY"].includes(selected.task.status) && (
                    <DeliveryOwnerEditor key={`owner-${selected.key}`} project={project} task={selected.task} />
                  )}
                  {(canEditSchedule || canPropose) && <TaskScheduleEditor key={selected.key} project={project} task={selected.task} />}
                  {project.status !== "DRAFT" && <MilestoneRevisions key={`revisions-${selected.key}`} project={project} task={selected.task} />}
                  <Typography component="h3" variant="subtitle1">Dependencies</Typography>
                  {dependencies.isPending && <LinearProgress aria-label="Loading dependencies" />}
                  {dependencies.isError && <Alert severity="error">{apiErrorMessage(dependencies.error)}</Alert>}
                  {dependencies.isSuccess && !relations.length && <Typography>No task dependencies.</Typography>}
                  {relations.map(({ task, direction, type }) => (
                    <Stack key={`${direction}-${task.id}`}>
                      <Typography variant="caption">{direction} · {type}</Typography>
                      <Button component={Link} to={itemLocation(`task-${task.id}`)} sx={{ alignSelf: "flex-start", textTransform: "none" }}>
                        {task.task_number} · {task.title}
                      </Button>
                    </Stack>
                  ))}
                  {(canEditSchedule || canPropose) && dependencies.isSuccess && (
                      <DependencyEditor key={`dependencies-${selected.key}`} project={project} taskId={selected.task.id}
                      tasks={tasks.data ?? []}
                      predecessors={relations.filter((relation) => relation.direction === "Predecessor").map((relation) => relation.task.id)} />
                  )}
                  <Button component={Link} to="../execution" sx={{ alignSelf: "flex-start" }}>Open Implementation board</Button>
                </>
              )}
              {!selected.task && <Button component={Link} to="../schedule" sx={{ alignSelf: "flex-start" }}>Open schedule</Button>}
              {canEditSchedule && selected.milestone && (
                <MilestoneScheduleEditor key={selected.key} project={project} milestone={selected.milestone} />
              )}
              {project.status !== "DRAFT" && selected.milestone && (
                <MilestoneRevisions key={selected.key} project={project} milestone={selected.milestone} />
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
