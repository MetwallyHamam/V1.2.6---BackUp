import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  LinearProgress,
  MenuItem,
  Paper,
  Radio,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Edit, Menu as MenuIcon } from "@mui/icons-material";
import { alpha } from "@mui/material/styles";
import type { Theme } from "@mui/material/styles";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { copyText } from "../utils/clipboard";
import { TicketFlagsPanel } from "../components/TicketFlagsPanel";

type Step = {
  id: number;
  title: string;
  description?: string;
  owner_user_id?: number;
  owner_name?: string;
  display_order: number;
  planned_duration_minutes: number;
  actual_duration_minutes: number;
  planned_start_at?: string;
  planned_end_at?: string;
  actual_started_at?: string;
  actual_finished_at?: string;
  status: string;
  completion_comment?: string;
};
type Issue = {
  id: number;
  step_id?: number;
  title: string;
  description: string;
  record_type: "ISSUE" | "CHANGE_REQUEST";
  issue_type_id?: number;
  issue_type_name?: string;
  implementation_phase?: string;
  occurrence_stage: string;
  affects_workflow: boolean;
  update_needed: boolean;
  priority: string;
  status: string;
  version: number;
  owner_user_id?: number;
  owner_name?: string;
  reporter_contact_id?: number;
  reporter_user_id?: number;
  reporter_name?: string;
  reported_at?: string;
  responsible_party?: string;
  responsible_party_detail?: string;
  resolver_department_id?: number;
  resolver_department_name?: string;
  resolved_by_user_id?: number;
  resolved_by_name?: string;
  root_cause_id?: number;
  root_cause_name?: string;
  root_cause_ids?: number[];
  root_cause_names?: string[];
  resolution_service_ids?: number[];
  resolution_service_names?: string[];
  investigation_reason?: string;
  in_progress_reason?: string;
  pending_reason?: string;
  reopen_reason?: string;
  next_action?: string;
  resolution_summary?: string;
  resolved_at?: string;
  delivered: boolean;
  delivered_at?: string;
  history?: { id: number; previous_status: string; new_status: string; actor_name?: string; change_summary?: string; changed_at: string }[];
  due_at?: string;
  client_visible?: boolean;
  linked_ticket_id?: number;
  linked_ticket_number?: string;
  knowledge_article_id?: number;
  linked_problems?: { id: number; number: string; title: string }[];
  created_at: string;
  evidence: { id: number; evidence_type: string; label?: string; external_url?: string; original_filename?: string }[];
};
type Plan = {
  id: number;
  code: string;
  name: string;
  client_id: number;
  uat_cycle_id?: number;
  owner_user_id: number;
  owner_name?: string;
  planned_start_at: string;
  planned_end_at: string;
  actual_started_at?: string;
  actual_finished_at?: string;
  status: string;
  description?: string;
  rollback_plan?: string;
  approved_software_version?: string;
  products: { id: number; product_id: number; product_name: string; approved_version: string; is_main: boolean }[];
  documents: { id: number; original_filename: string; size_bytes: number }[];
  final_summary?: string;
  final_process_summary?: string;
  final_follow_up_summary?: string;
  final_next_action?: string;
  summary: {
    planned_minutes: number;
    actual_minutes: number;
    variance_minutes: number;
    completed_steps: number;
    total_steps: number;
    completion_percent: number;
    total_issues: number;
    open_issues: number;
    pending_implementation_phases: number;
    issues_by_status: Record<string, number>;
  };
  steps: Step[];
  issues: Issue[];
  comments: {
    id: number;
    author_name?: string;
    body: string;
    created_at: string;
  }[];
};
type Meta = {
  clients: { id: number; name: string }[];
  products: { id: number; name: string }[];
  users: { id: number; name: string; user_type: string }[];
};
type Cycle = {
  id: number;
  code: string;
  title: string;
  client_id: number;
  status: string;
};
type ShareLink = {
  id: number;
  created_at: string;
  expires_at: string;
  revoked_at?: string;
};
type IssueOptions = {
  client_contacts: { id: number; name: string }[];
  products: { id: number; name: string; approved_version?: string; is_main?: boolean }[];
  main_product_id?: number;
  product_modules: { id: number; product_id: number; name: string }[];
  ticket_types: { id: number; code: string; name: string }[];
  issue_types: { id: number; code: string; name: string; is_default: boolean }[];
  default_issue_type_id?: number;
  client_users: { id: number; name: string }[];
  departments: { id: number; name: string }[];
  engineers: { id: number; name: string; department_id?: number; job_title?: string }[];
  root_causes: { id: number; name: string }[];
  resolution_services: { id: number; name: string }[];
  default_root_cause_id?: number;
  default_resolution_service_id?: number;
  incidents: { id: number; number: string; subject: string; status: string }[];
  problems: { id: number; number: string; title: string }[];
  can_link_problem: boolean;
};
const local = (value?: string) =>
  value ? new Date(value).toLocaleString() : "—";
const dateTimeLocal = (value?: string) => {
  const date = value ? new Date(value) : new Date();
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
};
const dateTimeIso = (value: FormDataEntryValue | null) => {
  const raw = String(value || "").trim();
  return raw ? new Date(raw).toISOString() : null;
};
const duration = (minutes: number) =>
  minutes >= 60
    ? `${Math.floor(minutes / 60)}h ${minutes % 60}m`
    : `${minutes}m`;
const workflowTargets: Record<string, string[]> = {
  OPEN: ["OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"],
  INVESTIGATION: ["OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"],
  IN_PROGRESS: ["OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"],
  PENDING: ["OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"],
  PENDING_IMPLEMENTATION: ["OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"],
  RESOLVED: ["REOPENED", "RESOLVED", "DELIVERED"],
  DELIVERED: ["REOPENED", "DELIVERED", "CLOSED"],
  CLOSED: ["REOPENED", "CLOSED"],
  REOPENED: ["REOPENED", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"],
};

const issueStatusColor = (theme: Theme, status: string) =>
  status === "OPEN"
    ? theme.palette.warning.main
    : status === "IN_PROGRESS"
      ? theme.palette.primary.main
      : ["PENDING", "PENDING_IMPLEMENTATION"].includes(status)
        ? theme.palette.warning.dark
        : status === "RESOLVED"
          ? theme.palette.success.main
          : status === "DELIVERED"
            ? theme.palette.info.main
            : theme.palette.grey[theme.palette.mode === "dark" ? 400 : 600];

const issueStatusSurface = (theme: Theme, status: string, card = false) =>
  alpha(
    issueStatusColor(theme, status),
    theme.palette.mode === "dark" ? (card ? 0.14 : 0.2) : card ? 0.035 : 0.07,
  );

export function DeploymentTracker({ portal = false }: { portal?: boolean }) {
  const { user, hasPermission } = useAuth();
  const cache = useQueryClient(),
    [selected, setSelected] = useState<number | null>(null),
    [creating, setCreating] = useState(false),
    [plansCollapsed, setPlansCollapsed] = useState(false),
    [editing, setEditing] = useState(false),
    [advancedPlan, setAdvancedPlan] = useState(false),
    [advancedIssue, setAdvancedIssue] = useState(false),
    [linkedIncident, setLinkedIncident] = useState(""),
    [selectedIssueProduct, setSelectedIssueProduct] = useState(""),
    [planProducts, setPlanProducts] = useState([{ product_id: "", approved_version: "", is_main: true }]),
    [editPlanProducts, setEditPlanProducts] = useState<Array<{ product_id: number | ""; approved_version: string; is_main: boolean }>>([]),
    [issueStageFilter, setIssueStageFilter] = useState("ALL"),
    [resolutionChange, setResolutionChange] = useState<{
      issue: Issue;
      status: string;
    } | null>(null),
    [editingIssue, setEditingIssue] = useState<Issue | null>(null),
    [resolverDepartment, setResolverDepartment] = useState<number | "">(""),
    [resolverUser, setResolverUser] = useState<number | "">(""),
    [workflowDateError, setWorkflowDateError] = useState(""),
    [draggedIssueId, setDraggedIssueId] = useState<number | null>(null),
    [dragOverStatus, setDragOverStatus] = useState(""),
    [finalizing, setFinalizing] = useState(false),
    [shareUrl, setShareUrl] = useState(""),
    [error, setError] = useState(""),
    [steps, setSteps] = useState([
      {
        title: "Preparation and backup",
        duration: 30,
        owner: 0,
        start: "",
        end: "",
      },
      { title: "Deploy release", duration: 60, owner: 0, start: "", end: "" },
      {
        title: "Validation and handover",
        duration: 30,
        owner: 0,
        start: "",
        end: "",
      },
    ]);
  const plans = useQuery({
    queryKey: ["deployment-plans", portal],
    queryFn: async () =>
      (await api.get<Plan[]>(portal ? "/portal/deployments" : "/deployments"))
        .data,
    refetchInterval: 30_000,
  });
  const meta = useQuery({
    queryKey: ["uat-metadata"],
    enabled: !portal,
    queryFn: async () => (await api.get<Meta>("/uat/metadata")).data,
  });
  const cycles = useQuery({
    queryKey: ["uat-cycles"],
    enabled: !portal,
    queryFn: async () => (await api.get<Cycle[]>("/uat/cycles")).data,
  });
  const current = plans.data?.find((x) => x.id === selected) ?? plans.data?.[0];
  const issueOptions = useQuery({
    queryKey: ["deployment-issue-options", current?.id],
    enabled: !portal && !!current,
    queryFn: async () =>
      (await api.get<IssueOptions>(`/deployments/${current!.id}/issue-options`)).data,
  });
  useEffect(() => {
    setSelectedIssueProduct(
      issueOptions.data?.main_product_id
        ? String(issueOptions.data.main_product_id)
        : "",
    );
  }, [current?.id, issueOptions.data?.main_product_id]);
  const shareLinks = useQuery({
    queryKey: ["deployment-share-links", current?.id],
    enabled: !portal && !!current,
    queryFn: async () =>
      (await api.get<ShareLink[]>(`/deployments/${current!.id}/share-links`)).data,
  });
  const refresh = () =>
    Promise.all([
      cache.invalidateQueries({ queryKey: ["deployment-plans"] }),
      cache.invalidateQueries({ queryKey: ["deployment-issue-options"] }),
    ]);
  const action = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: async () => {
      setError("");
      await refresh();
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "Deployment action failed.")),
  });
  function openIssueForm() {
    const form = document.getElementById("deployment-add-issue");
    form?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(
      () => form?.querySelector<HTMLInputElement>('input[name="title"]')?.focus(),
      350,
    );
  }
  function submitDeploymentIssue(form: HTMLFormElement, createTicket: boolean) {
    if (!current) return;
    const f = new FormData(form),
      title = String(f.get("title")),
      reporterReference = String(f.get("reporter_reference") || ""),
      ticketType = issueOptions.data?.ticket_types.find((item) => item.id === Number(f.get("ticket_type_id")));
    if (createTicket && (!f.get("ticket_product_id") || !reporterReference.startsWith("contact:") || !ticketType)) {
      setError("Choose Ticket Type, Product, and a client Contact reporter before creating the linked ticket.");
      return;
    }
    action.mutate(() =>
      api
        .post(`${portal ? "/portal" : ""}/deployments/${current.id}/issues`, {
          title: f.get("title"),
          record_type: ticketType?.code === "CHANGE_REQUEST" ? "CHANGE_REQUEST" : "ISSUE",
          issue_type_id: f.get("issue_type_id") ? Number(f.get("issue_type_id")) : issueOptions.data?.default_issue_type_id || null,
          description:
            f.get("description") ||
            `Deployment ${ticketType?.code === "CHANGE_REQUEST" ? "change request" : "issue"} reported: ${title}`,
          implementation_phase: f.get("phase") || null,
          occurrence_stage: f.get("occurrence_stage"),
          affects_workflow: f.get("affects_workflow") === "on",
          update_needed: f.get("update_needed") === "on",
          priority: f.get("priority"),
          reporter_contact_id: reporterReference.startsWith("contact:") ? Number(reporterReference.split(":")[1]) : null,
          reporter_user_id: reporterReference.startsWith("user:") ? Number(reporterReference.split(":")[1]) : null,
          reported_at: dateTimeIso(f.get("reported_at")),
          responsible_party: f.get("responsible_party") || "OTHER",
          responsible_party_detail: f.get("responsible_party_detail") || null,
          next_action: f.get("next_action") || null,
          client_visible: advancedIssue ? f.get("client_visible") === "on" : true,
          create_ticket: createTicket,
          linked_ticket_id: linkedIncident ? Number(linkedIncident) : null,
          problem_id: f.get("problem_id") ? Number(f.get("problem_id")) : null,
          ticket_product_id: createTicket ? Number(f.get("ticket_product_id")) : null,
          ticket_product_module_id: createTicket && f.get("ticket_product_module_id") ? Number(f.get("ticket_product_module_id")) : null,
          ticket_requester_contact_id: createTicket ? Number(reporterReference.split(":")[1]) : null,
          ticket_type_id: createTicket ? ticketType?.id : null,
        })
        .then(async (r) => {
          const issueId = r.data.created_issue_id, file = f.get("evidence_file"), url = String(f.get("evidence_url") || "");
          if (issueId && file instanceof File && file.size) { const body = new FormData(); body.append("upload", file); await api.post(`${portal ? "/portal" : ""}/deployments/issues/${issueId}/evidence/files`, body); }
          if (issueId && url) await api.post(`${portal ? "/portal" : ""}/deployments/issues/${issueId}/evidence/links`, { url, label: f.get("evidence_label") || null, client_visible: true });
          form.reset(); setLinkedIncident(""); setSelectedIssueProduct(""); return r;
        }),
    );
  }
  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    action.mutate(() =>
      api
        .post("/deployments", {
          name: f.get("name"),
          client_id: Number(f.get("client_id")),
          uat_cycle_id: f.get("uat_cycle_id")
            ? Number(f.get("uat_cycle_id"))
            : null,
          owner_user_id: Number(
            f.get("owner_user_id") ||
              user?.id ||
              meta.data?.users.find((x) => x.user_type === "EMPLOYEE")?.id,
          ),
          planned_start_at: f.get("planned_start_at"),
          planned_end_at: f.get("planned_end_at"),
          description: f.get("description"),
          rollback_plan: f.get("rollback_plan") || null,
          approved_software_version: null,
          products: planProducts.map((item) => ({
            product_id: Number(item.product_id),
            approved_version: item.approved_version,
            is_main: item.is_main,
          })),
          client_visible: true,
          steps: steps.map((s, index) => ({
            title: s.title,
            owner_user_id: s.owner || null,
            planned_start_at: s.start || null,
            planned_end_at: s.end || null,
            planned_duration_minutes: s.duration,
            display_order: index + 1,
          })),
        })
        .then((r) => {
          setSelected(r.data.id);
          setCreating(false);
          return r;
        }),
    );
  }
  async function downloadAttachment(path: string, filename: string) {
    try {
      const response = await api.get(path, { responseType: "blob" });
      const url = URL.createObjectURL(response.data), link = document.createElement("a");
      link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
    } catch (cause) { setError(apiErrorMessage(cause, "Could not download the attachment.")); }
  }
  async function exportReport(plan: Plan, format: "pdf" | "docx") {
    try {
      const response = await api.get(
        `${portal ? "/portal" : ""}/deployments/${plan.id}/report.${format}`,
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(response.data),
        link = document.createElement("a");
      link.href = url;
      const disposition = String(response.headers["content-disposition"] ?? ""),
        match = disposition.match(/filename="?([^";]+)"?/i);
      link.download = match?.[1] ?? `${plan.code}-deployment-report.${format}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setError(
        apiErrorMessage(cause, "Could not export the deployment report."),
      );
    }
  }
  async function createShareLink() {
    if (!current) return;
    try {
      const response = await api.post<ShareLink & { token: string }>(
        `/deployments/${current.id}/share-links`,
        { expires_in_hours: 168 },
      );
      const url = `${window.location.origin}${import.meta.env.BASE_URL}deployment-live/${response.data.token}`;
      setShareUrl(url);
      await copyText(url);
      await shareLinks.refetch();
      setError("");
    } catch (cause) {
      setError(apiErrorMessage(cause, "Could not create the live tracking link."));
    }
  }
  return (
    <Stack spacing={2}>
      <Paper
        sx={{
          p: 2.5,
          background: "linear-gradient(135deg,#102a43,#1f6f8b)",
          color: "white",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          alignItems={{ md: "center" }}
          gap={1}
        >
          <Box flex={1}>
            <Typography variant="h5" fontWeight={800}>
              Deployment live tracking
            </Typography>
            <Typography sx={{ opacity: 0.86 }}>
              A shared timeline from preparation through production handover.
            </Typography>
          </Box>
          {!portal && (
            <Button
              variant="contained"
              color="inherit"
              onClick={() => setCreating(!creating)}
            >
              Create deployment plan
            </Button>
          )}
        </Stack>
      </Paper>
      {error && <Alert severity="error">{error}</Alert>}
      {creating && meta.data && (
        <Paper component="form" onSubmit={create} sx={{ p: 2 }}>
          <Stack spacing={1.5}>
            <Typography variant="h6">New deployment plan</Typography>
            <TextField required name="name" label="Plan name" />
            <Stack direction={{ xs: "column", md: "row" }} gap={1}>
              <TextField
                required
                select
                name="client_id"
                label="Client"
                fullWidth
              >
                {meta.data.clients.map((x) => (
                  <MenuItem key={x.id} value={x.id}>
                    {x.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="uat_cycle_id"
                label="Signed-off UAT (optional)"
                defaultValue=""
                fullWidth
              >
                <MenuItem value="">No linked UAT</MenuItem>
                {cycles.data
                  ?.filter((x) => x.status === "COMPLETED")
                  .map((x) => (
                    <MenuItem key={x.id} value={x.id}>
                      {x.code} · {x.title}
                    </MenuItem>
                  ))}
              </TextField>
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} gap={1}>
              <TextField
                required
                type="datetime-local"
                name="planned_start_at"
                label="Planned start"
                slotProps={{ inputLabel: { shrink: true } }}
                fullWidth
              />
              <TextField
                required
                type="datetime-local"
                name="planned_end_at"
                label="Planned end"
                slotProps={{ inputLabel: { shrink: true } }}
                fullWidth
              />
            </Stack>
            <Stack spacing={1}>
              <Typography fontWeight={700}>Products and approved versions</Typography>
              {planProducts.map((item, index) => (
                <Stack key={index} direction={{ xs: "column", md: "row" }} gap={1} alignItems={{ md: "center" }}>
                  <TextField select required label="Product" value={item.product_id} onChange={(event) => setPlanProducts(planProducts.map((row, rowIndex) => rowIndex === index ? { ...row, product_id: event.target.value } : row))} fullWidth>
                    <MenuItem value="">Select product</MenuItem>
                    {meta.data.products.filter((product) => !planProducts.some((row, rowIndex) => rowIndex !== index && Number(row.product_id) === product.id)).map((product) => <MenuItem key={product.id} value={product.id}>{product.name}</MenuItem>)}
                  </TextField>
                  <TextField required label="Approved version" value={item.approved_version} onChange={(event) => setPlanProducts(planProducts.map((row, rowIndex) => rowIndex === index ? { ...row, approved_version: event.target.value } : row))} fullWidth />
                  <FormControlLabel control={<Radio checked={item.is_main} onChange={() => setPlanProducts(planProducts.map((row, rowIndex) => ({ ...row, is_main: rowIndex === index })))} />} label="Main" />
                  <Button color="error" disabled={planProducts.length === 1} onClick={() => { const next = planProducts.filter((_, rowIndex) => rowIndex !== index); if (item.is_main && next.length) next[0] = { ...next[0], is_main: true }; setPlanProducts(next); }}>Remove</Button>
                </Stack>
              ))}
              <Button sx={{ alignSelf: "flex-start" }} onClick={() => setPlanProducts([...planProducts, { product_id: "", approved_version: "", is_main: false }])}>Add product</Button>
            </Stack>
            <Stack direction="row" alignItems="center">
              <Typography fontWeight={700} flex={1}>
                Deployment steps
              </Typography>
              <Button onClick={() => setAdvancedPlan(!advancedPlan)}>
                {advancedPlan ? "Hide options" : "More options"}
              </Button>
            </Stack>
            {advancedPlan && (
              <>
                <TextField
                  select
                  name="owner_user_id"
                  label="Plan owner"
                  defaultValue={user?.id ?? ""}
                >
                  {meta.data.users
                    .filter((x) => x.user_type === "EMPLOYEE")
                    .map((x) => (
                      <MenuItem key={x.id} value={x.id}>
                        {x.name}
                      </MenuItem>
                    ))}
                </TextField>
                <TextField
                  name="description"
                  label="Scope and notes (optional)"
                  multiline
                  minRows={2}
                />
                <TextField
                  name="rollback_plan"
                  label="Rollback plan"
                  placeholder="Trigger, restoration steps, owner, validation and communication"
                  multiline
                  minRows={3}
                />
              </>
            )}
            {steps.map((step, index) => (
              <Stack
                key={index}
                direction={{ xs: "column", lg: "row" }}
                gap={1}
              >
                <TextField
                  required
                  label={`Step ${index + 1}`}
                  value={step.title}
                  onChange={(e) =>
                    setSteps(
                      steps.map((x, i) =>
                        i === index ? { ...x, title: e.target.value } : x,
                      ),
                    )
                  }
                  fullWidth
                />
                {advancedPlan && (
                  <TextField
                    select
                    label="Step owner"
                    value={step.owner}
                    onChange={(e) =>
                      setSteps(
                        steps.map((x, i) =>
                          i === index
                            ? { ...x, owner: Number(e.target.value) }
                            : x,
                        ),
                      )
                    }
                    sx={{ minWidth: 190 }}
                  >
                    <MenuItem value={0}>Plan owner</MenuItem>
                    {meta.data.users
                      .filter((x) => x.user_type === "EMPLOYEE")
                      .map((x) => (
                        <MenuItem key={x.id} value={x.id}>
                          {x.name}
                        </MenuItem>
                      ))}
                  </TextField>
                )}
                {advancedPlan && (
                  <TextField
                    type="datetime-local"
                    label="Step start"
                    value={step.start}
                    onChange={(e) =>
                      setSteps(
                        steps.map((x, i) =>
                          i === index ? { ...x, start: e.target.value } : x,
                        ),
                      )
                    }
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                )}
                {advancedPlan && (
                  <TextField
                    type="datetime-local"
                    label="Step end"
                    value={step.end}
                    onChange={(e) =>
                      setSteps(
                        steps.map((x, i) =>
                          i === index ? { ...x, end: e.target.value } : x,
                        ),
                      )
                    }
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                )}
                <TextField
                  required
                  type="number"
                  label="Minutes"
                  value={step.duration}
                  onChange={(e) =>
                    setSteps(
                      steps.map((x, i) =>
                        i === index
                          ? { ...x, duration: Number(e.target.value) }
                          : x,
                      ),
                    )
                  }
                  sx={{ width: 140 }}
                />
                <Button
                  color="error"
                  disabled={steps.length === 1}
                  onClick={() => setSteps(steps.filter((_, i) => i !== index))}
                >
                  Remove
                </Button>
              </Stack>
            ))}
            <Button
              onClick={() =>
                setSteps([
                  ...steps,
                  { title: "", duration: 30, owner: 0, start: "", end: "" },
                ])
              }
            >
              Add step
            </Button>
            <Button type="submit" variant="contained">
              Create plan
            </Button>
          </Stack>
        </Paper>
      )}
      <Stack
        direction={{ xs: "column", md: "row" }}
        gap={2}
        alignItems="flex-start"
      >
        <Paper
          sx={{
            p: plansCollapsed ? 0.75 : 1.5,
            width: { xs: "100%", md: plansCollapsed ? 56 : 330 },
            minWidth: { md: plansCollapsed ? 56 : 330 },
            maxWidth: { xs: "100%", md: plansCollapsed ? 56 : 330 },
            flex: { md: `0 0 ${plansCollapsed ? 56 : 330}px` },
            overflow: "hidden",
            transition: (theme) =>
              theme.transitions.create(["width", "min-width", "max-width", "flex-basis", "padding"]),
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent={plansCollapsed ? "center" : "flex-start"}
            mb={plansCollapsed ? 0 : 1}
          >
            <IconButton
              size="small"
              aria-label={plansCollapsed ? "Expand deployment plans" : "Collapse deployment plans"}
              aria-expanded={!plansCollapsed}
              onClick={() => setPlansCollapsed((value) => !value)}
            >
              <MenuIcon />
            </IconButton>
            {!plansCollapsed && (
              <Typography fontWeight={800} ml={0.75}>
                Deployment plans
              </Typography>
            )}
          </Stack>
          {!plansCollapsed && (
            <Stack spacing={1}>
              {plans.data?.map((plan) => (
                <Paper
                  key={plan.id}
                  variant="outlined"
                  onClick={() => setSelected(plan.id)}
                  sx={{
                    p: 1.25,
                    cursor: "pointer",
                    borderColor:
                      current?.id === plan.id ? "primary.main" : "divider",
                  }}
                >
                  <Stack direction="row" justifyContent="space-between">
                    <Typography fontWeight={750}>{plan.name}</Typography>
                    <Chip size="small" label={plan.status} />
                  </Stack>
                  <Typography variant="caption">
                    {plan.code} · {plan.summary.completion_percent}% complete
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={plan.summary.completion_percent}
                    sx={{ mt: 1 }}
                  />
                </Paper>
              ))}
            </Stack>
          )}
        </Paper>
        {current && (
          <Stack spacing={1.5} flex={1} width="100%" minWidth={0}>
            <Paper sx={{ p: 2 }}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                justifyContent="space-between"
              >
                <Box>
                  <Typography variant="h5" fontWeight={800}>
                    {current.name}
                  </Typography>
                  <Typography color="text.secondary">
                    {current.code} · Owner: {current.owner_name ?? "—"}
                  </Typography>
                  <Typography variant="body2">
                    Window: {local(current.planned_start_at)} →{" "}
                    {local(current.planned_end_at)}
                  </Typography>
                </Box>
                <Chip
                  label={current.status}
                  color={
                    current.status === "COMPLETED"
                      ? "success"
                      : current.status === "ACTIVE"
                        ? "primary"
                        : "default"
                  }
                />
                <Stack direction="row" gap={0.5}>
                  {!portal && (
                    <>
                      <Button onClick={() => { setEditPlanProducts(current.products.length ? current.products.map((item) => ({ product_id: item.product_id, approved_version: item.approved_version, is_main: item.is_main })) : [{ product_id: "", approved_version: current.approved_software_version || "", is_main: true }]); setEditing(!editing); }}>Edit plan</Button>
                      <Button variant="outlined" onClick={createShareLink}>
                        Share live tracking
                      </Button>
                    </>
                  )}
                  <Button
                    variant="outlined"
                    onClick={() => exportReport(current, "pdf")}
                  >
                    PDF
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => exportReport(current, "docx")}
                  >
                    Word report
                  </Button>
                </Stack>
              </Stack>
              {!portal && editing && meta.data && (
                <Stack component="form" spacing={1.25} mt={2} onSubmit={(event) => {
                  event.preventDefault();
                  const form = event.currentTarget, values = new FormData(form);
                  action.mutate(() => api.put(`/deployments/${current.id}`, {
                    name: values.get("name"),
                    owner_user_id: Number(values.get("owner_user_id")),
                    planned_start_at: values.get("planned_start_at"),
                    planned_end_at: values.get("planned_end_at"),
                    description: values.get("description") || null,
                    rollback_plan: values.get("rollback_plan") || null,
                    approved_software_version: null,
                    products: editPlanProducts.map((item) => ({ product_id: Number(item.product_id), approved_version: item.approved_version, is_main: item.is_main })),
                  }).then((response) => { setEditing(false); return response; }));
                }}>
                  <Typography fontWeight={850}>{current.status === "COMPLETED" ? "Edit finalized plan" : "Edit deployment plan"}</Typography>
                  <TextField required name="name" label="Plan name" defaultValue={current.name} />
                  <Stack spacing={1}>
                    <Typography fontWeight={700}>Products and approved versions</Typography>
                    {editPlanProducts.map((item, index) => <Stack key={index} direction={{ xs: "column", md: "row" }} gap={1} alignItems={{ md: "center" }}>
                      <TextField select required label="Product" value={item.product_id} onChange={(event) => setEditPlanProducts(editPlanProducts.map((row, rowIndex) => rowIndex === index ? { ...row, product_id: Number(event.target.value) } : row))} fullWidth>
                        <MenuItem value="">Select product</MenuItem>{meta.data.products.filter((product) => !editPlanProducts.some((row, rowIndex) => rowIndex !== index && Number(row.product_id) === product.id)).map((product) => <MenuItem key={product.id} value={product.id}>{product.name}</MenuItem>)}
                      </TextField>
                      <TextField required label="Approved version" value={item.approved_version} onChange={(event) => setEditPlanProducts(editPlanProducts.map((row, rowIndex) => rowIndex === index ? { ...row, approved_version: event.target.value } : row))} fullWidth />
                      <FormControlLabel control={<Radio checked={item.is_main} onChange={() => setEditPlanProducts(editPlanProducts.map((row, rowIndex) => ({ ...row, is_main: rowIndex === index })))} />} label="Main" />
                      <Button color="error" disabled={editPlanProducts.length === 1} onClick={() => { const next = editPlanProducts.filter((_, rowIndex) => rowIndex !== index); if (item.is_main && next.length) next[0] = { ...next[0], is_main: true }; setEditPlanProducts(next); }}>Remove</Button>
                    </Stack>)}
                    <Button sx={{ alignSelf: "flex-start" }} onClick={() => setEditPlanProducts([...editPlanProducts, { product_id: "", approved_version: "", is_main: false }])}>Add product</Button>
                  </Stack>
                  <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                    <TextField required select name="owner_user_id" label="Plan owner" defaultValue={current.owner_user_id} fullWidth>{meta.data.users.filter((person) => person.user_type === "EMPLOYEE").map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField>
                    <TextField required type="datetime-local" name="planned_start_at" label="Planned start" defaultValue={current.planned_start_at.slice(0, 16)} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
                    <TextField required type="datetime-local" name="planned_end_at" label="Planned end" defaultValue={current.planned_end_at.slice(0, 16)} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
                  </Stack>
                  <TextField name="description" label="Scope and notes" defaultValue={current.description ?? ""} multiline minRows={2} />
                  <TextField name="rollback_plan" label="Rollback plan" defaultValue={current.rollback_plan ?? ""} placeholder="Trigger, restoration steps, responsible owner, validation and communication" multiline minRows={3} />
                  <Stack direction="row" gap={1}><Button type="submit" variant="contained">Save plan</Button><Button onClick={() => setEditing(false)}>Cancel</Button></Stack>
                </Stack>
              )}
              {!portal && shareUrl && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  <Typography fontWeight={800}>Live tracking link created and copied</Typography>
                  <Stack direction={{ xs: "column", sm: "row" }} gap={1} mt={1}>
                    <TextField size="small" fullWidth value={shareUrl} slotProps={{ input: { readOnly: true } }} />
                    <Button onClick={() => copyText(shareUrl)}>Copy</Button>
                  </Stack>
                  <Typography variant="caption">The link is read-only and expires in 7 days.</Typography>
                </Alert>
              )}
              {!portal && !!shareLinks.data?.filter((link) => !link.revoked_at).length && (
                <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                  {shareLinks.data.filter((link) => !link.revoked_at).length} active stakeholder link(s)
                </Typography>
              )}
              <Stack direction="row" gap={1} flexWrap="wrap" mt={2}>
                {current.products.map((product) => <Chip key={product.id} label={`${product.product_name} · ${product.approved_version}${product.is_main ? " · Main" : ""}`} color={product.is_main ? "success" : "default"} />)}
                {!current.products.length && current.approved_software_version && <Chip label={`Legacy approved version ${current.approved_software_version}`} color="success" />}
                <Chip
                  label={`Planned ${duration(current.summary.planned_minutes)}`}
                />
                <Chip
                  label={`Actual ${duration(current.summary.actual_minutes)}`}
                  color="info"
                />
                <Chip
                  label={`Variance ${duration(Math.abs(current.summary.variance_minutes))} ${current.summary.variance_minutes > 0 ? "over" : "under"}`}
                  color={
                    current.summary.variance_minutes > 0 ? "warning" : "success"
                  }
                />
                <Chip
                  label={`${current.summary.total_issues} issues`}
                  color={current.summary.open_issues ? "warning" : "success"}
                />
                <Chip
                  label={`${current.summary.open_issues} open`}
                  color={current.summary.open_issues ? "error" : "success"}
                />
                <Chip
                  label={`${current.summary.pending_implementation_phases} pending phases`}
                />
              </Stack>
              {current.rollback_plan && <Alert severity="info" sx={{ mt: 2 }}><Typography fontWeight={850}>Rollback plan</Typography><Typography sx={{ whiteSpace: "pre-wrap" }}>{current.rollback_plan}</Typography></Alert>}
              <Stack component="form" direction={{ xs: "column", sm: "row" }} gap={1} mt={2} onSubmit={(event) => {
                event.preventDefault(); const form = event.currentTarget, values = new FormData(form), upload = values.get("upload");
                if (!(upload instanceof File) || !upload.size) return;
                const body = new FormData(); body.append("upload", upload);
                action.mutate(() => api.post(`${portal ? "/portal" : ""}/deployments/${current.id}/documents`, body).then((response) => { form.reset(); return response; }));
              }}>
                <Button component="label" variant="outlined">Attach deployment document<input hidden type="file" name="upload" required /></Button>
                <Button type="submit">Upload selected file</Button>
              </Stack>
              {!!current.documents.length && <Stack mt={1}>{current.documents.map((document) => <Button key={document.id} size="small" sx={{ alignSelf: "flex-start" }} onClick={() => downloadAttachment(`${portal ? "/portal" : ""}/deployments/${current.id}/documents/${document.id}/download`, document.original_filename)}>{document.original_filename}</Button>)}</Stack>}
            </Paper>
            {current.status === "COMPLETED" && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" fontWeight={800}>
                  Deployment closure
                </Typography>
                <Typography>
                  <b>Plan outcome:</b> {current.final_summary}
                </Typography>
                <Typography>
                  <b>Process:</b> {current.final_process_summary}
                </Typography>
                <Typography>
                  <b>Follow-up:</b> {current.final_follow_up_summary}
                </Typography>
                <Typography>
                  <b>Next action:</b> {current.final_next_action}
                </Typography>
              </Paper>
            )}
            <Box
              sx={{
                position: "relative",
                py: 1,
              }}
            >
              {current.steps.map((step, index) => (
                <Box
                  key={step.id}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "48px minmax(0, 1fr)",
                    position: "relative",
                    pb: index === current.steps.length - 1 ? 0 : 2,
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "center",
                      position: "relative",
                      "&::after":
                        index === current.steps.length - 1
                          ? undefined
                          : {
                              content: '""',
                              position: "absolute",
                              top: 36,
                              bottom: -16,
                              width: 3,
                              borderRadius: 4,
                              bgcolor:
                                step.status === "COMPLETED"
                                  ? "success.light"
                                  : "divider",
                            },
                    }}
                  >
                    <Box
                      sx={{
                        width: 34,
                        height: 34,
                        borderRadius: "50%",
                        display: "grid",
                        placeItems: "center",
                        zIndex: 1,
                        fontWeight: 900,
                        color: "common.white",
                        boxShadow: 2,
                        bgcolor:
                          step.status === "COMPLETED"
                            ? "success.main"
                            : step.status === "IN_PROGRESS"
                              ? "primary.main"
                              : step.status === "BLOCKED"
                                ? "error.main"
                                : "grey.500",
                      }}
                    >
                      {step.display_order}
                    </Box>
                  </Box>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 1.75,
                      borderRadius: 2.5,
                      borderLeft: "4px solid",
                      borderLeftColor:
                        step.status === "COMPLETED"
                          ? "success.main"
                          : step.status === "IN_PROGRESS"
                            ? "primary.main"
                            : step.status === "BLOCKED"
                              ? "error.main"
                              : "grey.400",
                    }}
                  >
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    gap={1}
                    alignItems={{ sm: "center" }}
                  >
                    <Box flex={1}>
                      <Typography fontWeight={800}>
                        {step.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {step.owner_name ?? "Unassigned"} · Planned{" "}
                        {duration(step.planned_duration_minutes)} · Actual{" "}
                        {duration(step.actual_duration_minutes)}
                      </Typography>
                      <Typography variant="caption">
                        Planned window: {local(step.planned_start_at)} →{" "}
                        {local(step.planned_end_at)}
                      </Typography>
                      {(step.actual_started_at || step.actual_finished_at) && (
                        <Typography variant="caption" display="block" color="text.secondary">
                          Actual: {local(step.actual_started_at)} →{" "}
                          {local(step.actual_finished_at)}
                        </Typography>
                      )}
                      {step.completion_comment && (
                        <Typography mt={0.5}>
                          {step.completion_comment}
                        </Typography>
                      )}
                    </Box>
                    <Chip
                      label={step.status}
                      color={
                        step.status === "COMPLETED"
                          ? "success"
                          : step.status === "IN_PROGRESS"
                            ? "primary"
                            : step.status === "BLOCKED"
                              ? "error"
                              : "default"
                      }
                    />
                    {!portal && current.status !== "COMPLETED" && (
                      <Stack direction="row" gap={0.5}>
                        {step.status === "PENDING" && (
                          <Button
                            onClick={() =>
                              action.mutate(() =>
                                api.put(
                                  `/deployments/steps/${step.id}/status`,
                                  { status: "IN_PROGRESS" },
                                ),
                              )
                            }
                          >
                            Start
                          </Button>
                        )}
                        {step.status === "IN_PROGRESS" && (
                          <Button
                            variant="contained"
                            onClick={() =>
                              action.mutate(() =>
                                api.put(
                                  `/deployments/steps/${step.id}/status`,
                                  { status: "COMPLETED" },
                                ),
                              )
                            }
                          >
                            Complete
                          </Button>
                        )}
                        <Button
                          color="error"
                          onClick={() =>
                            action.mutate(() =>
                              api.put(`/deployments/steps/${step.id}/status`, {
                                status: "BLOCKED",
                              }),
                            )
                          }
                        >
                          Block
                        </Button>
                      </Stack>
                    )}
                  </Stack>
                  </Paper>
                </Box>
              ))}
            </Box>
            <Paper sx={{ p: 2 }}>
              <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>
                <Typography variant="h6" fontWeight={800} flex={1}>
                  Deployment items and follow-up board
                </Typography>
                <Button
                  variant="contained"
                  onClick={openIssueForm}
                >
                  {portal ? "Report issue" : "Add issue"}
                </Button>
                <TextField
                  select
                  size="small"
                  label="Item stage"
                  value={issueStageFilter}
                  onChange={(event) => setIssueStageFilter(event.target.value)}
                  sx={{ minWidth: 220 }}
                >
                  <MenuItem value="ALL">All stages</MenuItem>
                  <MenuItem value="BEFORE_DEPLOYMENT">Before deployment</MenuItem>
                  <MenuItem value="DURING_DEPLOYMENT">During deployment</MenuItem>
                  <MenuItem value="AFTER_DEPLOYMENT">After deployment</MenuItem>
                </TextField>
              </Stack>
              <Box
                sx={{
                  mt: 1,
                  overflowX: "auto",
                  pb: 1,
                  scrollbarWidth: "thin",
                }}
              >
              <Stack
                direction="row"
                gap={1.5}
                alignItems="stretch"
                sx={{ width: "max-content", minWidth: "100%" }}
              >
                {[
                  "OPEN",
                  "INVESTIGATION",
                  "IN_PROGRESS",
                  "PENDING",
                  "RESOLVED",
                  "DELIVERED",
                  "CLOSED",
                ].map((status) => (
                  <Paper
                    key={status}
                    variant="outlined"
                    onDragOver={(event) => {
                      if (portal || draggedIssueId === null) return;
                      event.preventDefault();
                      event.dataTransfer.dropEffect = "move";
                      setDragOverStatus(status);
                    }}
                    onDragLeave={(event) => {
                      if (!event.currentTarget.contains(event.relatedTarget as Node)) {
                        setDragOverStatus("");
                      }
                    }}
                    onDrop={(event) => {
                      event.preventDefault();
                      const issue = current.issues.find((item) => item.id === draggedIssueId);
                      setDraggedIssueId(null);
                      setDragOverStatus("");
                      if (!issue || issue.status === status) return;
                      if (!(workflowTargets[issue.status] || []).includes(status)) {
                        setError(
                          `${issue.status.replaceAll("_", " ")} cannot move directly to ${status.replaceAll("_", " ")}.`,
                        );
                        return;
                      }
                      setWorkflowDateError("");
                      setResolverDepartment(issue.resolver_department_id || "");
                      setResolverUser(issue.resolved_by_user_id || "");
                      setResolutionChange({ issue, status });
                    }}
                    onDoubleClick={status === "OPEN" ? openIssueForm : undefined}
                    title={status === "OPEN" ? "Double-click to add a new issue" : undefined}
                    sx={(theme) => ({
                      p: 1.25,
                      width: 320,
                      minWidth: 0,
                      flex: "0 0 320px",
                      overflow: "hidden",
                      borderTop: "4px solid",
                      borderTopColor: issueStatusColor(theme, status),
                      backgroundColor: issueStatusSurface(theme, status),
                      color: "text.primary",
                      outline: dragOverStatus === status ? "3px dashed" : "none",
                      outlineColor: "primary.main",
                      outlineOffset: -4,
                    })}
                  >
                    <Typography fontWeight={800} variant="body2" noWrap>
                      {status.replaceAll("_", " ")} ·{" "}
                      {current.summary.issues_by_status?.[status] ?? 0}
                    </Typography>
                    <Stack
                      spacing={1}
                      mt={1}
                      sx={{
                        maxHeight: "min(72vh, 900px)",
                        overflowY: "auto",
                        overflowX: "hidden",
                        overscrollBehavior: "contain",
                        pr: 0.5,
                        scrollbarWidth: "thin",
                        scrollbarGutter: "stable",
                        "& > .MuiPaper-root": { flexShrink: 0 },
                        "&::-webkit-scrollbar": { width: 8 },
                        "&::-webkit-scrollbar-thumb": {
                          backgroundColor: "rgba(15, 74, 94, 0.38)",
                          borderRadius: 8,
                        },
                      }}
                    >
                      {current.issues
                        .filter(
                          (issue) =>
                            issue.status === status &&
                            (issueStageFilter === "ALL" ||
                              issue.occurrence_stage === issueStageFilter),
                        )
                        .map((issue) => (
                          <Paper
                            key={issue.id}
                            draggable={!portal && !action.isPending}
                            onDragStart={(event) => {
                              setDraggedIssueId(issue.id);
                              event.dataTransfer.effectAllowed = "move";
                              event.dataTransfer.setData("text/plain", String(issue.id));
                            }}
                            onDragEnd={() => {
                              setDraggedIssueId(null);
                              setDragOverStatus("");
                            }}
                            onDoubleClick={(event) => event.stopPropagation()}
                            sx={(theme) => ({
                              p: 1,
                              flex: "0 0 auto",
                              flexShrink: 0,
                              alignSelf: "stretch",
                              height: "auto",
                              minWidth: 0,
                              maxWidth: "100%",
                              overflow: "hidden",
                              cursor: portal ? "default" : "grab",
                              opacity: draggedIssueId === issue.id ? 0.58 : 1,
                              borderLeft: "4px solid",
                              borderLeftColor: issueStatusColor(theme, status),
                              backgroundColor: issueStatusSurface(theme, status, true),
                              color: "text.primary",
                              boxShadow: 1,
                            })}
                          >
                            <Stack
                              direction="row"
                              gap={0.5}
                              alignItems="center"
                              sx={{ minWidth: 0 }}
                            >
                              <Typography
                                fontWeight={750}
                                flex={1}
                                sx={{ minWidth: 0, overflowWrap: "anywhere" }}
                              >
                                {issue.title}
                              </Typography>
                              <Chip
                                size="small"
                                label={issue.record_type === "CHANGE_REQUEST" ? "CR" : "Issue"}
                                color={issue.record_type === "CHANGE_REQUEST" ? "info" : "default"}
                                variant="outlined"
                              />
                              {issue.issue_type_name && <Chip size="small" variant="outlined" label={issue.issue_type_name} />}
                              <Chip
                                size="small"
                                label={issue.priority}
                                sx={{ flexShrink: 0 }}
                                color={
                                  issue.priority === "CRITICAL"
                                    ? "error"
                                    : issue.priority === "HIGH"
                                      ? "warning"
                                      : "default"
                                }
                              />
                            </Stack>
                            <Typography
                              variant="caption"
                              display="block"
                              sx={{ overflowWrap: "anywhere" }}
                            >
                              {issue.occurrence_stage.replaceAll("_", " ")} ·{" "}
                              {issue.implementation_phase || "General"} ·{" "}
                              {issue.owner_name || "Unassigned"}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Affects workflow: {issue.affects_workflow ? "Yes" : "No"}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Update needed: {issue.update_needed ? "Yes" : "No"}
                            </Typography>
                            <Typography
                              variant="body2"
                              mt={0.5}
                              sx={{ overflowWrap: "anywhere" }}
                            >
                              {issue.description}
                            </Typography>
                            {issue.next_action && (
                              <Typography
                                variant="body2"
                                sx={{ overflowWrap: "anywhere" }}
                              >
                                <b>Next:</b> {issue.next_action}
                              </Typography>
                            )}
                            <Typography variant="caption" display="block">
                              Reporter: {issue.reporter_name || "Not recorded"} · {local(issue.reported_at)}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Responsible: {(issue.responsible_party || "OTHER").replaceAll("_", " ")}
                              {issue.responsible_party_detail ? ` · ${issue.responsible_party_detail}` : ""}
                            </Typography>
                            {issue.resolved_at && <Typography variant="caption" display="block">Resolved {local(issue.resolved_at)} by {issue.resolved_by_name || "Not assigned"}</Typography>}
                            {issue.delivered && <Typography variant="caption" display="block">Delivered {local(issue.delivered_at)}</Typography>}
                            {issue.linked_ticket_number && (
                              <Chip
                                size="small"
                                sx={{ mt: 0.5 }}
                                label={`Ticket ${issue.linked_ticket_number}`}
                              />
                            )}{" "}
                            {issue.linked_problems?.map((problem) => (
                              <Chip key={problem.id} size="small" color="secondary" sx={{ mt: 0.5, mr: 0.5 }} label={`Problem ${problem.number}`} />
                            ))}
                            {!!issue.evidence?.length && <Stack mt={0.5} sx={{ minWidth: 0 }}>{issue.evidence.map((evidence) => evidence.evidence_type === "LINK" ? <Button key={evidence.id} size="small" component="a" href={evidence.external_url} target="_blank" rel="noreferrer" sx={{ overflowWrap: "anywhere" }}>{evidence.label || "Shared evidence"}</Button> : <Button key={evidence.id} size="small" onClick={() => downloadAttachment(`${portal ? "/portal" : ""}/deployments/issues/${issue.id}/evidence/${evidence.id}/download`, evidence.original_filename || "evidence")} sx={{ overflowWrap: "anywhere" }}>{evidence.original_filename || "Attachment"}</Button>)}</Stack>}
                            {!portal && (
                              <Stack gap={1} mt={1} sx={{ minWidth: 0 }}>
                              <TextField
                                select
                                fullWidth
                                size="small"
                                label="Item stage"
                                value={issue.occurrence_stage}
                                disabled={action.isPending}
                                onChange={(event) =>
                                  action.mutate(() =>
                                    api.put(`/deployments/issues/${issue.id}`, {
                                      status: issue.status,
                                      priority: issue.priority,
                                      version: issue.version,
                                      occurrence_stage: event.target.value,
                                    }),
                                  )
                                }
                              >
                                <MenuItem value="BEFORE_DEPLOYMENT">Before deployment</MenuItem>
                                <MenuItem value="DURING_DEPLOYMENT">During deployment</MenuItem>
                                <MenuItem value="AFTER_DEPLOYMENT">After deployment</MenuItem>
                              </TextField>
                              <TextField
                                select
                                fullWidth
                                size="small"
                                label="Issue status"
                                value={issue.status}
                                disabled={action.isPending}
                                sx={{
                                  width: "100%",
                                  minWidth: 0,
                                  "& .MuiSelect-select": {
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                    lineHeight: 1.35,
                                  },
                                  "& .MuiFormHelperText-root": {
                                    mx: 0,
                                    overflowWrap: "anywhere",
                                  },
                                }}
                                helperText="Select the next workflow status"
                                onChange={(event) => {
                                  const nextStatus = event.target.value;
                                  setResolverDepartment(issue.resolver_department_id || "");
                                  setResolverUser(issue.resolved_by_user_id || "");
                                  setResolutionChange({ issue, status: nextStatus });
                                }}
                              >
                                {(workflowTargets[issue.status] || ["OPEN"]).map((target) => (
                                  <MenuItem key={target} value={target}>{target.replaceAll("_", " ")}</MenuItem>
                                ))}
                              </TextField>
                              <Button size="small" onClick={() => { setResolverDepartment(issue.resolver_department_id || ""); setResolverUser(issue.resolved_by_user_id || ""); setResolutionChange({ issue, status: issue.status }); }}>Update workflow details</Button>
                              <Button size="small" startIcon={<Edit />} onClick={() => setEditingIssue(issue)}>Edit issue content</Button>
                              </Stack>
                            )}
                            {!portal && issue.linked_ticket_id && (
                              <TicketFlagsPanel ticketId={issue.linked_ticket_id} />
                            )}
                          </Paper>
                        ))}
                    </Stack>
                  </Paper>
                ))}
              </Stack>
              </Box>
              {(
                <Stack
                  id="deployment-add-issue"
                  component="form"
                  spacing={1}
                  mt={2}
                  sx={{ scrollMarginTop: 16 }}
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = e.currentTarget,
                      submitter = (e.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null,
                      createTicket = !portal && submitter?.value === "create-ticket";
                    submitDeploymentIssue(form, createTicket);
                  }}
                >
                  <Stack direction="row" alignItems="center">
                    <Typography fontWeight={800} flex={1}>
                      Add issue
                    </Typography>
                    {!portal && <Button
                      size="small"
                      onClick={() => setAdvancedIssue(!advancedIssue)}
                    >
                      {advancedIssue ? "Fewer fields" : "More options"}
                    </Button>}
                  </Stack>
                  <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                    <TextField
                      required
                      name="title"
                      label="Item title"
                      fullWidth
                    />
                    {!portal && <TextField
                      select
                      name="issue_type_id"
                      label="Issue type"
                      defaultValue={issueOptions.data?.default_issue_type_id || ""}
                      sx={{ minWidth: 160 }}
                    >
                      {(issueOptions.data?.issue_types || []).map((type) => <MenuItem key={type.id} value={type.id}>{type.name}</MenuItem>)}
                    </TextField>}
                    <TextField
                      select
                      name="ticket_type_id"
                      label="Ticket type"
                      defaultValue=""
                      sx={{ minWidth: 175 }}
                    >
                      <MenuItem value="">Select type</MenuItem>
                      {(issueOptions.data?.ticket_types || []).map((type) => <MenuItem key={type.id} value={type.id}>{type.name}</MenuItem>)}
                    </TextField>
                    <TextField
                      select
                      name="occurrence_stage"
                      label="Issue stage"
                      defaultValue={
                        current.status === "COMPLETED"
                          ? "AFTER_DEPLOYMENT"
                          : "DURING_DEPLOYMENT"
                      }
                      sx={{ minWidth: 190 }}
                    >
                      <MenuItem value="BEFORE_DEPLOYMENT">Before deployment</MenuItem>
                      <MenuItem value="DURING_DEPLOYMENT">During deployment</MenuItem>
                      <MenuItem value="AFTER_DEPLOYMENT">After deployment</MenuItem>
                    </TextField>
                    {advancedIssue && (
                      <TextField
                        name="phase"
                        label="Implementation phase"
                        fullWidth
                      />
                    )}
                    <TextField
                      select
                      name="priority"
                      label="Priority"
                      defaultValue="MEDIUM"
                      sx={{ minWidth: 150 }}
                    >
                      {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((v) => (
                        <MenuItem key={v} value={v}>
                          {v}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Stack>
                  {!portal && advancedIssue && (
                    <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                      <TextField select label="Existing Incident (optional)" value={linkedIncident} onChange={(event) => setLinkedIncident(event.target.value)} fullWidth helperText="Several deployment issues can share the same Incident.">
                        <MenuItem value="">No existing Incident</MenuItem>
                        {(issueOptions.data?.incidents || []).map((incident) => <MenuItem key={incident.id} value={incident.id}>{incident.number} · {incident.subject} · {incident.status}</MenuItem>)}
                      </TextField>
                      {issueOptions.data?.can_link_problem && (
                        <TextField select name="problem_id" label="Problem (optional)" defaultValue="" fullWidth helperText="Links the selected or newly created Incident to this Problem.">
                          <MenuItem value="">No Problem link</MenuItem>
                          {(issueOptions.data?.problems || []).map((problem) => <MenuItem key={problem.id} value={problem.id}>{problem.number} · {problem.title}</MenuItem>)}
                        </TextField>
                      )}
                    </Stack>
                  )}
                  <Stack spacing={1}>
                    <TextField name="description" label="Description" multiline minRows={2} />
                    {!portal && (
                      <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                        <TextField select name="ticket_product_id" label="Product" value={selectedIssueProduct} onChange={(event) => setSelectedIssueProduct(event.target.value)} fullWidth helperText="Required when creating a ticket.">
                          <MenuItem value="">Select product</MenuItem>
                          {(issueOptions.data?.products || []).map((product) => <MenuItem key={product.id} value={product.id}>{product.name}{product.approved_version ? ` · ${product.approved_version}` : ""}{product.is_main ? " · Main" : ""}</MenuItem>)}
                        </TextField>
                        <TextField select name="ticket_product_module_id" label="Module" defaultValue="" fullWidth disabled={!selectedIssueProduct}>
                          <MenuItem value="">No module</MenuItem>
                          {(issueOptions.data?.product_modules || []).filter((module) => module.product_id === Number(selectedIssueProduct)).map((module) => <MenuItem key={module.id} value={module.id}>{module.name}</MenuItem>)}
                        </TextField>
                        <TextField select name="reporter_reference" label="Reporter / Caller" defaultValue="" fullWidth helperText="A client Contact is required when creating a ticket.">
                          <MenuItem value="">Logged-in system user</MenuItem>
                          {(issueOptions.data?.client_contacts || []).map((contact) => <MenuItem key={`contact:${contact.id}`} value={`contact:${contact.id}`}>{contact.name} · Contact</MenuItem>)}
                          {(issueOptions.data?.client_users || []).map((clientUser) => <MenuItem key={`user:${clientUser.id}`} value={`user:${clientUser.id}`}>{clientUser.name} · Portal user</MenuItem>)}
                        </TextField>
                      </Stack>
                    )}
                    {advancedIssue && (
                      <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                        <TextField name="reported_at" type="datetime-local" label="Reported date" helperText="Leave blank to use server time." InputLabelProps={{ shrink: true }} fullWidth />
                        <TextField select name="responsible_party" label="Item owner" defaultValue="OTHER" fullWidth>
                          <MenuItem value="CLIENT">Client</MenuItem><MenuItem value="VENDOR">Vendor</MenuItem><MenuItem value="THIRD_PARTY">Third party</MenuItem><MenuItem value="OTHER">Other</MenuItem>
                        </TextField>
                      </Stack>
                    )}
                    {advancedIssue && <TextField name="responsible_party_detail" label="Item owner details" />}
                  </Stack>
                  {advancedIssue && (
                    <TextField name="next_action" label="Next action" />
                  )}
                  <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                    <Button component="label" variant="outlined">Attach evidence<input hidden type="file" name="evidence_file" /></Button>
                    <TextField name="evidence_url" type="url" label="Shared file or recorded video URL" fullWidth />
                    <TextField name="evidence_label" label="Link label" />
                  </Stack>
                  {advancedIssue && (
                    <Stack direction="row" gap={2}>
                      <FormControlLabel
                        control={
                          <Checkbox name="client_visible" defaultChecked />
                        }
                        label="Show to client"
                      />
                      <FormControlLabel control={<Checkbox name="affects_workflow" />} label="Affects workflow" />
                      <FormControlLabel control={<Checkbox name="update_needed" />} label="Update needed" />
                    </Stack>
                  )}
                  {!advancedIssue && <Stack direction="row" gap={2}><FormControlLabel control={<Checkbox name="affects_workflow" />} label="Affects workflow" /><FormControlLabel control={<Checkbox name="update_needed" />} label="Update needed" /></Stack>}
                  <Stack direction="row" gap={1} sx={{ alignSelf: "flex-start" }}>
                    <Button type="submit" value="add-only" variant={portal ? "contained" : "outlined"}>
                      {portal ? "Report issue" : linkedIncident ? "Add and link issue" : "Add issue"}
                    </Button>
                    {!portal && <Button type="submit" value="create-ticket" variant="contained" disabled={Boolean(linkedIncident)}>Add + create ticket</Button>}
                  </Stack>
                </Stack>
              )}
            </Paper>
            <Paper
              component="form"
              sx={{ p: 2 }}
              onSubmit={(e) => {
                e.preventDefault();
                const form = e.currentTarget,
                  body = String(new FormData(form).get("body"));
                action.mutate(() =>
                  api
                    .post(
                      `${portal ? "/portal" : ""}/deployments/${current.id}/comments`,
                      { body, is_client_visible: true },
                    )
                    .then((r) => {
                      form.reset();
                      return r;
                    }),
                );
              }}
            >
              <Typography fontWeight={800}>
                Live updates and comments
              </Typography>
              {current.comments.map((c) => (
                <Box key={c.id} py={0.75}>
                  <Typography variant="body2" fontWeight={700}>
                    {c.author_name ?? "User"} · {local(c.created_at)}
                  </Typography>
                  <Typography>{c.body}</Typography>
                </Box>
              ))}
              <Stack direction="row" gap={1} mt={1}>
                <TextField
                  required
                  name="body"
                  label="Add a live update"
                  fullWidth
                />
                <Button type="submit" variant="contained">
                  Post
                </Button>
              </Stack>
            </Paper>
            {!portal &&
              current.status !== "COMPLETED" &&
              current.summary.completed_steps === current.summary.total_steps &&
              current.summary.open_issues === 0 && (
                <Button
                  variant="contained"
                  color="success"
                  onClick={() => setFinalizing(true)}
                >
                  Finalize deployment
                </Button>
              )}
          </Stack>
        )}
      </Stack>
      <Dialog
        open={Boolean(editingIssue)}
        onClose={() => !action.isPending && setEditingIssue(null)}
        fullWidth
        maxWidth="sm"
      >
        <Stack component="form" onSubmit={(event) => {
          event.preventDefault();
          if (!editingIssue) return;
          const values = new FormData(event.currentTarget);
          action.mutate(() => api.put(`/deployments/issues/${editingIssue.id}`, {
            status: editingIssue.status,
            version: editingIssue.version,
            title: String(values.get("title") || "").trim(),
            description: String(values.get("description") || "").trim(),
            record_type: values.get("record_type") || editingIssue.record_type,
            issue_type_id: values.get("issue_type_id") ? Number(values.get("issue_type_id")) : null,
            occurrence_stage: values.get("occurrence_stage"),
            affects_workflow: values.get("affects_workflow") === "on",
            update_needed: values.get("update_needed") === "on",
            implementation_phase: String(values.get("implementation_phase") || "").trim() || null,
            priority: values.get("priority"),
            owner_user_id: values.get("owner_user_id") ? Number(values.get("owner_user_id")) : null,
            responsible_party: values.get("responsible_party") || "OTHER",
            responsible_party_detail: String(values.get("responsible_party_detail") || "").trim() || null,
            next_action: String(values.get("next_action") || "").trim() || null,
            due_at: dateTimeIso(values.get("due_at")),
            client_visible: values.get("client_visible") === "on",
          }).then((response) => { setEditingIssue(null); return response; }));
        }}>
          <DialogTitle>Edit deployment issue</DialogTitle>
          <DialogContent>
            <Stack spacing={2} pt={0.5}>
              <TextField required name="title" label="Issue title" defaultValue={editingIssue?.title || ""} />
              <TextField required multiline minRows={4} name="description" label="Description" defaultValue={editingIssue?.description || ""} />
              <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                <TextField select fullWidth name="record_type" label="Record type" defaultValue={editingIssue?.record_type || "ISSUE"}>
                  <MenuItem value="ISSUE">Issue</MenuItem><MenuItem value="CHANGE_REQUEST">Change Request</MenuItem>
                </TextField>
                <TextField select fullWidth name="issue_type_id" label="Issue type" defaultValue={editingIssue?.issue_type_id || issueOptions.data?.default_issue_type_id || ""}>
                  {(issueOptions.data?.issue_types || []).map((type) => <MenuItem key={type.id} value={type.id}>{type.name}</MenuItem>)}
                </TextField>
              </Stack>
              <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                <TextField select fullWidth name="occurrence_stage" label="Issue stage" defaultValue={editingIssue?.occurrence_stage || "DURING_DEPLOYMENT"}>
                  <MenuItem value="BEFORE_DEPLOYMENT">Before deployment</MenuItem><MenuItem value="DURING_DEPLOYMENT">During deployment</MenuItem><MenuItem value="AFTER_DEPLOYMENT">After deployment</MenuItem>
                </TextField>
                <TextField select fullWidth name="priority" label="Priority" defaultValue={editingIssue?.priority || "MEDIUM"}>
                  {['LOW','MEDIUM','HIGH','CRITICAL'].map((priority) => <MenuItem key={priority} value={priority}>{priority}</MenuItem>)}
                </TextField>
              </Stack>
              <TextField name="implementation_phase" label="Implementation phase" defaultValue={editingIssue?.implementation_phase || ""} />
              <FormControlLabel control={<Checkbox name="affects_workflow" defaultChecked={editingIssue?.affects_workflow ?? false} />} label="Affects workflow" />
              <FormControlLabel control={<Checkbox name="update_needed" defaultChecked={editingIssue?.update_needed ?? false} />} label="Update needed" />
              <TextField select fullWidth name="owner_user_id" label="Issue owner" defaultValue={editingIssue?.owner_user_id || ""}>
                <MenuItem value="">Unassigned</MenuItem>{(issueOptions.data?.engineers || []).map((engineer) => <MenuItem key={engineer.id} value={engineer.id}>{engineer.name}</MenuItem>)}
              </TextField>
              <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                <TextField select fullWidth name="responsible_party" label="Responsible party" defaultValue={editingIssue?.responsible_party || "OTHER"}>
                  <MenuItem value="CLIENT">Client</MenuItem><MenuItem value="VENDOR">Vendor</MenuItem><MenuItem value="THIRD_PARTY">Third party</MenuItem><MenuItem value="OTHER">Other</MenuItem>
                </TextField>
                <TextField fullWidth name="responsible_party_detail" label="Responsible-party details" defaultValue={editingIssue?.responsible_party_detail || ""} />
              </Stack>
              <TextField multiline minRows={2} name="next_action" label="Next action" defaultValue={editingIssue?.next_action || ""} />
              <TextField name="due_at" type="datetime-local" label="Due date" defaultValue={editingIssue?.due_at ? dateTimeLocal(editingIssue.due_at) : ""} InputLabelProps={{ shrink: true }} />
              <FormControlLabel control={<Checkbox name="client_visible" defaultChecked={editingIssue?.client_visible ?? true} />} label="Show to client" />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditingIssue(null)} disabled={action.isPending}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={action.isPending}>Save issue</Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={!!resolutionChange}
        onClose={() => !action.isPending && setResolutionChange(null)}
        fullWidth
        maxWidth="sm"
      >
        <Stack
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!resolutionChange) return;
            const values = new FormData(event.currentTarget);
            const { issue, status } = resolutionChange;
            const value = (name: string) => String(values.get(name) || "").trim() || null;
            const reportedAt = dateTimeIso(values.get("reported_at"));
            const resolvedAt = dateTimeIso(values.get("resolved_at"));
            const deliveredAt = dateTimeIso(values.get("delivered_at"));
            if (resolvedAt && reportedAt && new Date(resolvedAt) < new Date(reportedAt)) {
              setWorkflowDateError("Resolved date must be on or after the reported date.");
              return;
            }
            if (deliveredAt && resolvedAt && new Date(deliveredAt) < new Date(resolvedAt)) {
              setWorkflowDateError("Delivered date must be on or after the resolved date.");
              return;
            }
            setWorkflowDateError("");
            const reporterReference = String(values.get("reporter_reference") || "unchanged");
            const reporterPayload = reporterReference === "unchanged" ? {} : {
              reporter_contact_id: reporterReference.startsWith("contact:") ? Number(reporterReference.split(":")[1]) : null,
              reporter_user_id: reporterReference.startsWith("user:") ? Number(reporterReference.split(":")[1]) : null,
            };
            action.mutate(() =>
              api
                .put(`/deployments/issues/${issue.id}`, {
                  status,
                  priority: issue.priority,
                  record_type: value("record_type") || issue.record_type || "ISSUE",
                  issue_type_id: values.get("issue_type_id") ? Number(values.get("issue_type_id")) : issue.issue_type_id || null,
                  version: issue.version,
                  ...reporterPayload,
                  reported_at: reportedAt,
                  responsible_party: value("responsible_party") || "OTHER",
                  responsible_party_detail: value("responsible_party_detail"),
                  next_action: value("next_action"),
                  ...(status === "INVESTIGATION" ? { investigation_reason: value("investigation_reason") } : {}),
                  ...(status === "IN_PROGRESS" ? { in_progress_reason: value("in_progress_reason") } : {}),
                  ...(["PENDING", "PENDING_IMPLEMENTATION"].includes(status) ? { pending_reason: value("pending_reason") } : {}),
                  ...(status === "REOPENED" ? { reopen_reason: value("reopen_reason") } : {}),
                  ...(["RESOLVED", "DELIVERED", "CLOSED"].includes(status) ? {
                    resolution_summary: value("resolution_summary"),
                    resolver_department_id: values.get("resolver_department_id") ? Number(values.get("resolver_department_id")) : null,
                    resolved_by_user_id: values.get("resolved_by_user_id") ? Number(values.get("resolved_by_user_id")) : null,
                    root_cause_id: values.get("root_cause_id") ? Number(values.get("root_cause_id")) : null,
                    root_cause_ids: values.get("root_cause_id") ? [Number(values.get("root_cause_id"))] : [],
                    resolution_service_ids: values.get("resolution_service_id") ? [Number(values.get("resolution_service_id"))] : [],
                    resolved_at: resolvedAt,
                    create_knowledge_article:
                      values.get("create_knowledge_article") === "on",
                  } : {}),
                  ...(["DELIVERED", "CLOSED"].includes(status) ? { delivered: true, delivered_at: deliveredAt } : {}),
                })
                .then((response) => {
                  setWorkflowDateError("");
                  setResolutionChange(null);
                  return response;
                }),
            );
          }}
        >
          <DialogTitle>
            Update deployment item · {resolutionChange?.status.replaceAll("_", " ")}
          </DialogTitle>
          <DialogContent sx={{ pt: 1 }}>
            <Typography color="text.secondary" mb={2}>
              {resolutionChange?.issue.title}
            </Typography>
            <Stack spacing={2}>
              {workflowDateError && <Alert severity="error">{workflowDateError}</Alert>}
              <TextField select fullWidth name="record_type" label="Type" defaultValue={resolutionChange?.issue.record_type || "ISSUE"}>
                <MenuItem value="ISSUE">Issue</MenuItem>
                <MenuItem value="CHANGE_REQUEST">Change Request</MenuItem>
              </TextField>
              <TextField select fullWidth name="issue_type_id" label="Issue type" defaultValue={resolutionChange?.issue.issue_type_id || issueOptions.data?.default_issue_type_id || ""}>
                {(issueOptions.data?.issue_types || []).map((type) => <MenuItem key={type.id} value={type.id}>{type.name}</MenuItem>)}
              </TextField>
              <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                <TextField select fullWidth name="reporter_reference" label="Item reporter" defaultValue={resolutionChange?.issue.reporter_contact_id ? `contact:${resolutionChange.issue.reporter_contact_id}` : resolutionChange?.issue.reporter_user_id && (issueOptions.data?.client_users || []).some((clientUser) => clientUser.id === resolutionChange.issue.reporter_user_id) ? `user:${resolutionChange.issue.reporter_user_id}` : "unchanged"}>
                  <MenuItem value="unchanged">Keep current reporter</MenuItem>
                  <MenuItem value="actor">Logged-in system user</MenuItem>
                  {(issueOptions.data?.client_users || []).map((clientUser) => <MenuItem key={`user:${clientUser.id}`} value={`user:${clientUser.id}`}>{clientUser.name} · Portal user</MenuItem>)}
                  {(issueOptions.data?.client_contacts || []).map((contact) => <MenuItem key={`contact:${contact.id}`} value={`contact:${contact.id}`}>{contact.name} · Contact</MenuItem>)}
                </TextField>
                <TextField required fullWidth name="reported_at" type="datetime-local" label="Reported date" defaultValue={dateTimeLocal(resolutionChange?.issue.reported_at)} InputLabelProps={{ shrink: true }} />
              </Stack>
              <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                <TextField select fullWidth name="responsible_party" label="Item owner" defaultValue={resolutionChange?.issue.responsible_party || "OTHER"}>
                  <MenuItem value="CLIENT">Client</MenuItem><MenuItem value="VENDOR">Vendor</MenuItem><MenuItem value="THIRD_PARTY">Third party</MenuItem><MenuItem value="OTHER">Other</MenuItem>
                </TextField>
                <TextField fullWidth name="responsible_party_detail" label="Owner details" defaultValue={resolutionChange?.issue.responsible_party_detail || ""} />
              </Stack>
              {resolutionChange?.status === "INVESTIGATION" && <TextField required autoFocus multiline minRows={3} name="investigation_reason" label="Investigation reason and findings" defaultValue={resolutionChange.issue.investigation_reason || ""} />}
              {resolutionChange?.status === "IN_PROGRESS" && <TextField required autoFocus multiline minRows={3} name="in_progress_reason" label="In-progress reason / work underway" defaultValue={resolutionChange.issue.in_progress_reason || ""} />}
              {["PENDING", "PENDING_IMPLEMENTATION"].includes(resolutionChange?.status || "") && <TextField required autoFocus multiline minRows={3} name="pending_reason" label="Pending reason" defaultValue={resolutionChange?.issue.pending_reason || ""} />}
              {resolutionChange?.status === "REOPENED" && <TextField required autoFocus multiline minRows={3} name="reopen_reason" label="Reopen reason" defaultValue={resolutionChange?.issue.reopen_reason || ""} />}
              <TextField multiline minRows={2} name="next_action" label="Next action" defaultValue={resolutionChange?.issue.next_action || ""} />
              {["RESOLVED", "DELIVERED", "CLOSED"].includes(resolutionChange?.status || "") && <>
                <TextField required multiline minRows={4} name="resolution_summary" label="Resolution" helperText="Describe the implemented solution and validation result." defaultValue={resolutionChange?.issue.resolution_summary || ""} />
                <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                  <TextField select fullWidth name="resolver_department_id" label="Resolver department" value={resolverDepartment} onChange={(e) => { setResolverDepartment(e.target.value ? Number(e.target.value) : ""); setResolverUser(""); }}>
                    <MenuItem value="">Not selected</MenuItem>{(issueOptions.data?.departments || []).map((department) => <MenuItem key={department.id} value={department.id}>{department.name}</MenuItem>)}
                  </TextField>
                  <TextField select fullWidth name="resolved_by_user_id" label="Resolved by" value={resolverUser} onChange={(e) => setResolverUser(e.target.value ? Number(e.target.value) : "")}>
                    <MenuItem value="">Not selected</MenuItem>{(issueOptions.data?.engineers || []).filter((engineer) => !resolverDepartment || engineer.department_id === resolverDepartment).map((engineer) => <MenuItem key={engineer.id} value={engineer.id}>{engineer.name}{engineer.job_title ? ` · ${engineer.job_title}` : ""}</MenuItem>)}
                  </TextField>
                </Stack>
                <TextField select fullWidth name="root_cause_id" label="Root cause" defaultValue={resolutionChange?.issue.root_cause_id || issueOptions.data?.default_root_cause_id || ""}>
                  <MenuItem value="">Not selected</MenuItem>{(issueOptions.data?.root_causes || []).map((cause) => <MenuItem key={cause.id} value={cause.id}>{cause.name}</MenuItem>)}
                </TextField>
                <TextField select fullWidth name="resolution_service_id" label="Service provided" defaultValue={resolutionChange?.issue.resolution_service_ids?.[0] || issueOptions.data?.default_resolution_service_id || ""}>
                  <MenuItem value="">Use ticket default</MenuItem>{(issueOptions.data?.resolution_services || []).map((service) => <MenuItem key={service.id} value={service.id}>{service.name}</MenuItem>)}
                </TextField>
                <TextField name="resolved_at" type="datetime-local" label="Resolved date" helperText="Leave blank to use server time." defaultValue={resolutionChange?.issue.resolved_at ? dateTimeLocal(resolutionChange.issue.resolved_at) : ""} InputLabelProps={{ shrink: true }} />
                {hasPermission("knowledge.create") && !resolutionChange?.issue.knowledge_article_id && (
                  <FormControlLabel
                    control={<Checkbox name="create_knowledge_article" />}
                    label="Create a Knowledge Base draft from this resolution"
                  />
                )}
                {resolutionChange?.issue.knowledge_article_id && (
                  <Alert severity="success">
                    Knowledge Base draft #{resolutionChange.issue.knowledge_article_id} is linked to this issue.
                  </Alert>
                )}
              </>}
              {["DELIVERED", "CLOSED"].includes(resolutionChange?.status || "") && <TextField name="delivered_at" type="datetime-local" label="Delivered date" helperText="Leave blank to use server time." defaultValue={resolutionChange?.issue.delivered_at ? dateTimeLocal(resolutionChange.issue.delivered_at) : ""} InputLabelProps={{ shrink: true }} />}
              {resolutionChange?.status === "CLOSED" && <Alert severity="info">Closing preserves the resolved and delivered dates. The issue can be reopened later.</Alert>}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => setResolutionChange(null)}
              disabled={action.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" variant="contained" disabled={action.isPending}>
              Save workflow
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={finalizing}
        onClose={() => !action.isPending && setFinalizing(false)}
        fullWidth
        maxWidth="sm"
      >
        <Stack
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!current) return;
            const values = new FormData(event.currentTarget);
            action.mutate(() =>
              api
                .post(`/deployments/${current.id}/finalize`, {
                  final_summary: values.get("final_summary"),
                  process_summary: `${current.summary.completed_steps} of ${current.summary.total_steps} planned activities completed. Planned ${duration(current.summary.planned_minutes)}; actual ${duration(current.summary.actual_minutes)}.`,
                  follow_up_summary: `${current.summary.total_issues} issues recorded; all issues addressed before closure.`,
                  next_action: values.get("next_action"),
                })
                .then((response) => {
                  setFinalizing(false);
                  return response;
                }),
            );
          }}
        >
          <DialogTitle>Finalize deployment</DialogTitle>
          <DialogContent>
            <Stack spacing={2} pt={0.5}>
              <TextField
                required
                autoFocus
                multiline
                minRows={3}
                name="final_summary"
                label="Final deployment outcome"
              />
              <TextField
                required
                multiline
                minRows={2}
                name="next_action"
                label="Next action"
                defaultValue="Monitor production and confirm stability."
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setFinalizing(false)} disabled={action.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="contained" color="success" disabled={action.isPending}>
              Finalize deployment
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
    </Stack>
  );
}
