import { AccountTreeOutlined, ArrowBack, AssignmentOutlined, FactCheckOutlined, FolderOutlined, HistoryOutlined, HubOutlined, SpaceDashboardOutlined, TimelineOutlined, WarningAmberOutlined } from "@mui/icons-material";
import { Alert, Avatar, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useOutletContext, useParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { implementationWorkspacePermission } from "../auth/projectWorkspaceAccess";
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
  client_id?: number;
  planned_end_date?: string | null;
  planned_start_date?: string | null;
  priority?: string;
  health?: string;
};

export function ProjectWorkspacePage() {
  const { id } = useParams();
  const { pathname } = useLocation();
  const { hasPermission, user } = useAuth();
  const [editing, setEditing] = useState(false);
  const project = useQuery({
    queryKey: ["project", Number(id)],
    queryFn: async () => (await api.get<Project>(`/projects/${id}`)).data,
  });
  const options = useQuery({
    queryKey: ["project-options"],
    queryFn: async () => (await api.get<{ clients: { id: number; name: string }[]; managers: { id: number; name: string }[] }>("/projects/options")).data,
  });
  const root = `/projects/${id}`;
  const groups = [
    { label: "Overview", views: [
      { path: "", label: "Overview", icon: <SpaceDashboardOutlined />, visible: true },
    ] },
    { label: "Plan", views: [
      { path: "work-packages", label: "Work packages", icon: <AssignmentOutlined />, visible: true },
      { path: "schedule", label: "Schedule", icon: <TimelineOutlined />, visible: true },
      { path: "revisions", label: "Schedule revisions", icon: <HistoryOutlined />, visible: project.data?.status !== "DRAFT" },
      { path: "register", label: "Risks and changes", icon: <WarningAmberOutlined />, visible: true },
    ] },
    { label: "Delivery", views: [
      { path: "intake", label: "Intake decisions", icon: <AccountTreeOutlined />, visible: true },
      { path: "execution", label: "Implementation", icon: <AssignmentOutlined />, visible: hasPermission("implementation.task.view") },
      { path: "collaboration", label: "Collaboration", icon: <HubOutlined />, visible: hasPermission("cross_department.request.create") },
    ] },
    { label: "Handover", views: [
      { path: "handover", label: "Support handover", icon: <FactCheckOutlined />, visible: hasPermission("handover.view") },
    ] },
  ].map((group) => ({ ...group, views: group.views.filter((view) => view.visible) }))
    .filter((group) => group.views.length);
  const viewPath = (path: string) => path ? `${root}/${path}` : root;
  const activeGroup = groups.find((group) => group.views.some((view) => viewPath(view.path) === pathname)) ?? groups[0];
  const canEdit = hasPermission("project.manage")
    || (hasPermission("project.manage.assigned") && project.data?.project_manager_user_id === user?.id);
  const clientName = options.data?.clients.find((client) => client.id === project.data?.client_id)?.name;
  const managerName = options.data?.managers.find((manager) => manager.id === project.data?.project_manager_user_id)?.name;
  const status = project.data?.status;
  const nextAction = status === "DRAFT" && canEdit
    ? { label: "Review project plan", path: "work-packages" }
    : status && ["AWAITING_IMPLEMENTATION_ACCEPTANCE", "INTAKE_PROPOSED", "INTAKE_RETURNED", "INTAKE_REJECTED"].includes(status)
      ? { label: "Review intake status", path: "intake" }
      : status && ["HANDOVER_PREPARATION", "SUPPORT_REVIEW", "STABILIZATION"].includes(status) && hasPermission("handover.view")
        ? { label: "Review handover", path: "handover" }
        : undefined;

  return (
    <Stack spacing={2.5} sx={{ minWidth: 0 }}>
      {!project.data && <Button component={Link} to="/projects" sx={{ alignSelf: "flex-start" }}>Project portfolio</Button>}
      {project.isPending && <LinearProgress aria-label="Loading project" />}
      {project.isError && <Alert severity="error">{apiErrorMessage(project.error)}</Alert>}
      {project.data && (
        <>
          <Box sx={{ minWidth: 0, borderBottom: 1, borderColor: "divider", pb: 2 }}>
            <Stack gap={1.5}>
              <Button component={Link} to="/projects" startIcon={<ArrowBack />} size="small"
                sx={{ alignSelf: "flex-start", textTransform: "none" }}>Project portfolio</Button>
              <Stack direction="row" gap={1.5} alignItems="center">
                <Avatar variant="rounded" sx={{ bgcolor: "primary.main", color: "primary.contrastText" }}><FolderOutlined /></Avatar>
                <Box sx={{ minWidth: 0 }}>
                  <Typography component="h1" variant="h5" fontWeight={800} sx={{ overflowWrap: "anywhere" }}>{project.data.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {[project.data.project_number, clientName, managerName && `Manager: ${managerName}`].filter(Boolean).join(" · ")}
                  </Typography>
                </Box>
              </Stack>
              <Stack direction="row" gap={1} flexWrap="wrap">
                <Chip size="small" color="primary" label={project.data.status.replaceAll("_", " ")} />
                {project.data.planned_end_date && <Chip size="small" variant="outlined" label={`Planned finish ${project.data.planned_end_date}`} />}
                {canEdit && <Button size="small" variant="outlined" onClick={() => setEditing(true)}>Edit project</Button>}
                {nextAction && <Button size="small" variant="contained" component={Link} to={viewPath(nextAction.path)}>{nextAction.label}</Button>}
              </Stack>
            </Stack>
          </Box>
          <Stack gap={1}>
            <Stack component="nav" aria-label="Project sections" direction="row" flexWrap="wrap" gap={0.75}>
              {groups.map((group) => <Button key={group.label} component={Link} to={viewPath(group.views[0].path)}
                aria-current={group === activeGroup ? "true" : undefined}
                variant={group === activeGroup ? "contained" : "text"} sx={{ textTransform: "none" }}>{group.label}</Button>)}
            </Stack>
            {activeGroup.views.length > 1 && <Stack component="nav" aria-label={`${activeGroup.label} views`}
              direction="row" flexWrap="wrap" gap={0.5} sx={{ borderBottom: 1, borderColor: "divider", pb: 1 }}>
              {activeGroup.views.map((view) => <Button key={view.path} component={NavLink} end to={viewPath(view.path)}
                size="small" startIcon={view.icon} sx={{ textTransform: "none", color: "text.secondary",
                  "&[aria-current=page]": { bgcolor: "action.selected", color: "primary.main", fontWeight: 750 } }}>{view.label}</Button>)}
            </Stack>}
          </Stack>
          <Box sx={{ minWidth: 0 }}><Outlet context={project.data} /></Box>
          {editing && canEdit && <ProjectEditDialog project={project.data} onClose={() => setEditing(false)} />}
        </>
      )}
    </Stack>
  );
}

function ProjectEditDialog({ project, onClose }: { project: Project; onClose: () => void }) {
  const cache = useQueryClient();
  const [version] = useState(project.row_version);
  const [form, setForm] = useState({
    name: project.name, description: project.description ?? "", priority: project.priority ?? "NORMAL",
    planned_start_date: project.planned_start_date ?? "", planned_end_date: project.planned_end_date ?? "",
  });
  const invalidDates = Boolean(form.planned_start_date && form.planned_end_date && form.planned_end_date < form.planned_start_date);
  const save = useMutation({
    mutationFn: async () => (await api.patch<Project>(`/projects/${project.id}`, {
      ...form, name: form.name.trim(), description: form.description.trim() || null,
      planned_start_date: form.planned_start_date || null, planned_end_date: form.planned_end_date || null,
      expected_version: version,
    })).data,
    onSuccess: (updated) => {
      cache.setQueryData(["project", project.id], updated);
      for (const key of ["projects", "project-summary", "project-plan"]) void cache.invalidateQueries({ queryKey: [key] });
      onClose();
    },
  });
  return <Dialog open fullWidth maxWidth="sm" onClose={() => !save.isPending && onClose()}>
    <DialogTitle>Edit project · {project.project_number}</DialogTitle>
    <DialogContent>
      <Stack gap={2} mt={1}>
        {save.isError && <Alert severity="error">{apiErrorMessage(save.error)}</Alert>}
        <TextField label="Project name" value={form.name} inputProps={{ maxLength: 200 }}
          onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <TextField label="Description" multiline minRows={3} value={form.description}
          onChange={(event) => setForm({ ...form, description: event.target.value })} />
        <TextField select label="Priority" value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })}>
          {[...new Set(["LOW", "NORMAL", "HIGH", "CRITICAL", project.priority ?? "NORMAL"])].map((priority) =>
            <MenuItem key={priority} value={priority}>{priority}</MenuItem>)}
        </TextField>
        <Stack gap={1.5} direction={{ xs: "column", sm: "row" }}>
          <TextField fullWidth type="date" label="Planned start" InputLabelProps={{ shrink: true }} value={form.planned_start_date}
            onChange={(event) => setForm({ ...form, planned_start_date: event.target.value })} />
          <TextField fullWidth type="date" label="Planned finish" InputLabelProps={{ shrink: true }} value={form.planned_end_date}
            error={invalidDates} helperText={invalidDates ? "Finish must be on or after start." : undefined}
            onChange={(event) => setForm({ ...form, planned_end_date: event.target.value })} />
        </Stack>
      </Stack>
    </DialogContent>
    <DialogActions><Button onClick={onClose} disabled={save.isPending}>Cancel</Button>
      <Button variant="contained" disabled={save.isPending || invalidDates || !form.name.trim()} onClick={() => save.mutate()}>Save changes</Button>
    </DialogActions>
  </Dialog>;
}

function DeliverySubmissionCard({ project }: { project: Project }) {
  const client = useQueryClient();
  const [summary, setSummary] = useState("");
  const key = ["project-delivery-submission", project.id];
  const path = `/projects/${project.id}/delivery-submission`;
  const latest = useQuery({
    queryKey: key,
    queryFn: async () => (await api.get<{
      submitted_at: string; project_version: number; summary: string;
      task_count: number; evidence_count: number; is_current: boolean;
    } | null>(path)).data,
  });
  const readiness = useQuery({
    queryKey: ["project-delivery-readiness", project.id],
    queryFn: async () => (await api.get<{
      in_review: boolean; has_tasks: boolean; open_tasks: number; has_shared_evidence: boolean; can_submit: boolean;
    }>(`/projects/${project.id}/delivery-readiness`)).data,
    enabled: project.status === "DELIVERY_REVIEW",
    refetchOnMount: "always",
  });
  const submit = useMutation({
    mutationFn: () => api.post(path, { expected_version: project.row_version, summary: summary.trim() }),
    onSuccess: async () => {
      setSummary("");
      await client.invalidateQueries({ queryKey: key });
    },
  });
  const requirements = readiness.data;
  const canSubmit = requirements?.can_submit && requirements.in_review && latest.isSuccess && !latest.data?.is_current;
  const ready = requirements?.has_tasks && requirements.open_tasks === 0 && requirements.has_shared_evidence;
  if (latest.isSuccess && !latest.data && project.status !== "DELIVERY_REVIEW") return null;
  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
      <Stack spacing={1}>
        <Typography component="h2" variant="h6">Delivery submission</Typography>
        {latest.isPending && <LinearProgress aria-label="Loading delivery submission" />}
        {(latest.isError || readiness.isError || submit.isError) && <Alert severity="error">{apiErrorMessage(latest.error ?? readiness.error ?? submit.error)}</Alert>}
        {project.status === "DELIVERY_REVIEW" && readiness.isPending && <LinearProgress aria-label="Loading delivery requirements" />}
        {requirements && project.status === "DELIVERY_REVIEW" && <Stack direction="row" gap={1} flexWrap="wrap">
          <Chip size="small" color={requirements.has_tasks && !requirements.open_tasks ? "success" : "warning"}
            label={!requirements.has_tasks ? "Delivery tasks missing" : requirements.open_tasks ? `${requirements.open_tasks} open tasks` : "Delivery tasks complete"} />
          <Chip size="small" color={requirements.has_shared_evidence ? "success" : "warning"}
            label={requirements.has_shared_evidence ? "Shared evidence available" : "Shared evidence missing"} />
          <Button component={Link} to="work-packages" size="small">View work packages</Button>
        </Stack>}
        {requirements && !requirements.can_submit && !latest.data?.is_current &&
          <Typography variant="body2" color="text.secondary">The assigned Implementation department submits delivery for acceptance.</Typography>}
        {latest.data && (
          <>
            <Typography variant="body2">
              Submitted {new Date(latest.data.submitted_at).toLocaleString()} · Plan version {latest.data.project_version}
              {" · "}{latest.data.task_count} tasks · {latest.data.evidence_count} evidence items
            </Typography>
            <Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{latest.data.summary}</Typography>
            {!latest.data.is_current && <Typography variant="caption" color="text.secondary">The project version has changed since submission.</Typography>}
          </>
        )}
        {canSubmit && (
          <Stack component="form" spacing={1} onSubmit={(event) => { event.preventDefault(); submit.mutate(); }}>
            <TextField multiline required label="Delivery summary" value={summary} onChange={(event) => setSummary(event.target.value)}
              slotProps={{ htmlInput: { maxLength: 2000 } }} helperText="Complete the delivery tasks and add shared project evidence before submitting." />
            <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}
              disabled={!ready || submit.isPending || summary.trim().length < 3}>Submit for delivery acceptance</Button>
          </Stack>
        )}
      </Stack>
    </Paper>
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
      {["DELIVERY_REVIEW", "HANDOVER_PREPARATION", "SUPPORT_REVIEW", "STABILIZATION", "COMPLETED"].includes(project.status)
        && <DeliverySubmissionCard project={project} />}
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
  const project = useOutletContext<Project>();
  const { user, hasPermission } = useAuth();
  const client = useQueryClient();
  const [draft, setDraft] = useState<{ id: number; start: string; end: string; notes: string } | null>(null);
  const plan = useQuery({
    queryKey: ["project-plan", id],
    queryFn: async () => (await api.get<{ assignment_requests: IntakeRequest[] }>(`/projects/${id}/plan`)).data,
    refetchOnMount: "always",
  });
  const requests = plan.data?.assignment_requests ?? [];
  const latest = requests.reduce<IntakeRequest | undefined>((current, item) =>
    !current || item.id > current.id ? item : current, undefined);
  const canResubmit = hasPermission("project.assignment.request")
    && (user?.id === project.project_manager_user_id || hasPermission("project.manage"))
    && ["INTAKE_PROPOSED", "INTAKE_RETURNED"].includes(project.status)
    && latest && ["PROPOSED", "RETURNED"].includes(latest.status);
  const resubmit = useMutation({
    mutationFn: (values: NonNullable<typeof draft>) => api.post(
      `/projects/${id}/assignment-requests/${values.id}/resubmit`, {
        expected_version: project.row_version, requested_start_date: values.start,
        requested_end_date: values.end, notes: values.notes.trim(),
      },
    ),
    onSuccess: async () => {
      setDraft(null);
      await Promise.all([
        client.invalidateQueries({ queryKey: ["project-plan", id] }),
        client.invalidateQueries({ queryKey: ["project", project.id] }),
        client.invalidateQueries({ queryKey: ["projects"] }),
        client.invalidateQueries({ queryKey: ["project-summary"] }),
        client.invalidateQueries({ queryKey: ["implementation-intake"] }),
      ]);
    },
  });
  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
        <Typography component="h2" variant="h6">Implementation intake decisions</Typography>
        {hasPermission(implementationWorkspacePermission) && hasPermission("project.assignment.respond") && (
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
            {canResubmit && request.id === latest.id && draft?.id !== request.id && (
              <Button sx={{ alignSelf: "flex-start" }} onClick={() => {
                resubmit.reset();
                setDraft({ id: request.id, start: request.requested_start_date ?? "", end: request.requested_end_date ?? "", notes: "" });
              }}>Revise and resubmit</Button>
            )}
            {canResubmit && request.id === latest.id && draft?.id === request.id && (
              <Stack component="form" gap={1} onSubmit={(event) => { event.preventDefault(); resubmit.mutate(draft); }}>
                <TextField type="date" required label="Revised start" value={draft.start} slotProps={{ inputLabel: { shrink: true } }}
                  onChange={(event) => setDraft({ ...draft, start: event.target.value })} />
                <TextField type="date" required label="Revised finish" value={draft.end} slotProps={{ inputLabel: { shrink: true } }}
                  onChange={(event) => setDraft({ ...draft, end: event.target.value })} />
                <TextField multiline required label="Reason for resubmission" value={draft.notes} slotProps={{ htmlInput: { maxLength: 500 } }}
                  onChange={(event) => setDraft({ ...draft, notes: event.target.value })} />
                {resubmit.isError && <Alert severity="error">{apiErrorMessage(resubmit.error)}</Alert>}
                <Stack direction="row" gap={1}>
                  <Button onClick={() => setDraft(null)} disabled={resubmit.isPending}>Cancel</Button>
                  <Button type="submit" variant="contained" disabled={resubmit.isPending || !draft.start || !draft.end || draft.end < draft.start || !draft.notes.trim()}>
                    Send to Implementation
                  </Button>
                </Stack>
              </Stack>
            )}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

export function ProjectWorkspaceHandover() {
  const project = useOutletContext<Project>();
  const client = useQueryClient();
  const [department, setDepartment] = useState("");
  const key = ["project-handover-routing", project.id];
  const path = `/projects/${project.id}/handover-routing`;
  const routing = useQuery({
    queryKey: key,
    queryFn: async () => (await api.get<{
      department: { id: number; name: string } | null;
      can_edit: boolean;
      options: { id: number; name: string }[];
    }>(path)).data,
  });
  const save = useMutation({
    mutationFn: () => api.put(path, {
      department_id: Number(department),
      expected_department_id: routing.data?.department?.id ?? null,
    }),
    onSuccess: async () => {
      setDepartment("");
      await Promise.all([
        client.invalidateQueries({ queryKey: key }),
        client.invalidateQueries({ queryKey: ["support-handover-inbox"] }),
      ]);
    },
  });
  return (
    <Stack gap={2}>
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
        <Stack gap={1}>
          <Typography component="h2" variant="h6">Receiving Support department</Typography>
          {routing.isPending && <LinearProgress aria-label="Loading handover routing" />}
          {(routing.isError || save.isError) && <Alert severity="error">{apiErrorMessage(routing.error ?? save.error)}</Alert>}
          {routing.isSuccess && <Typography color="text.secondary">
            {routing.data.department?.name ?? "No single receiving department is assigned."}
          </Typography>}
          {routing.data?.can_edit && (
            <Stack component="form" direction={{ xs: "column", sm: "row" }} gap={1}
              onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
              <TextField select label="Receiving department" value={department} size="small" sx={{ minWidth: 220 }}
                onChange={(event) => setDepartment(event.target.value)}>
                {routing.data.options.map((option) => <MenuItem key={option.id} value={String(option.id)}>{option.name}</MenuItem>)}
              </TextField>
              <Button type="submit" variant="outlined" disabled={!department || save.isPending || Number(department) === routing.data.department?.id}>
                Save routing
              </Button>
            </Stack>
          )}
        </Stack>
      </Paper>
      <ProjectSupportHandoverPanel projectId={project.id} projectStatus={project.status} projectVersion={project.row_version} />
    </Stack>
  );
}
