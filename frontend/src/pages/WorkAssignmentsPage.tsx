import {
  Add,
  AttachFile,
  AssignmentTurnedIn,
  Edit,
  FilterAltOff,
  Groups,
  PlayArrow,
  Share,
  TaskAlt,
  Visibility,
} from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  LinearProgress,
  MenuItem,
  Slider,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { copyText } from "../utils/clipboard";

type Person = { id: number; full_name: string };
type Client = { id: number; name: string };
type Ticket = { id: number; ticket_number: string; subject: string };
type Assignee = {
  user_id: number;
  name: string;
  role: string;
  contribution_percent: number;
};
type WorkAssignment = {
  id: number;
  title: string;
  description: string;
  assignment_type: string;
  activity_classification: string;
  status: string;
  priority: string;
  complexity: string;
  created_by_user_id: number;
  owner_user_id?: number | null;
  planned_start_at?: string | null;
  due_at?: string | null;
  requires_review: boolean;
  kpi_source_type: string;
  kpi_source_id?: number | null;
  progress_percent: number;
  version: number;
  context: Record<string, string>;
  assignees: Assignee[];
  clients: Array<{ client_id: number; name: string; status: string }>;
  links: Array<{
    target_type: string;
    target_id: number;
    relation_type: string;
    label?: string | null;
  }>;
  evidence: Array<{
    id: number;
    evidence_type: string;
    note: string;
    original_filename?: string | null;
    size_bytes?: number | null;
    uploaded_by_user_id: number;
    created_at: string;
  }>;
};
type Draft = {
  title: string;
  description: string;
  assignment_type: string;
  activity_classification: string;
  priority: string;
  complexity: string;
  planned_start_at: string;
  due_at: string;
  client_ids: number[];
  engineer_ids: number[];
  related_ticket_ids: number[];
  requires_review: boolean;
  context: Record<string, string>;
};

const taskTypes = [
  "GENERAL",
  "TICKET_FOLLOW_UP",
  "CLIENT_REQUEST",
  "SYSTEM_UPGRADE",
  "CHECKLIST",
  "REMOTE_ACTIVITY",
  "VISIT_CANDIDATE",
  "TICKET_CANDIDATE",
  "INTERNAL_OPERATION",
];
const clientTaskTypes = new Set([
  "CLIENT_REQUEST",
  "SYSTEM_UPGRADE",
  "REMOTE_ACTIVITY",
  "VISIT_CANDIDATE",
  "TICKET_CANDIDATE",
]);
const requiredContext: Record<string, string[]> = {
  GENERAL: ["expected_outcome"],
  CLIENT_REQUEST: ["request_reference"],
  SYSTEM_UPGRADE: ["target_version"],
  CHECKLIST: ["checklist_name", "checklist_items"],
  REMOTE_ACTIVITY: ["remote_method"],
  VISIT_CANDIDATE: ["visit_location"],
  TICKET_CANDIDATE: ["issue_summary"],
  INTERNAL_OPERATION: ["operation_type"],
};
const terminal = new Set(["COMPLETED", "CANCELLED"]);
const boardLanes = [
  { status: "ASSIGNED", label: "Assigned", color: "info.main" },
  { status: "ACCEPTED", label: "Accepted", color: "secondary.main" },
  { status: "IN_PROGRESS", label: "In progress", color: "warning.main" },
  { status: "BLOCKED", label: "Blocked", color: "error.main" },
  { status: "AWAITING_REVIEW", label: "Review", color: "primary.main" },
  { status: "COMPLETED", label: "Completed", color: "success.main" },
] as const;

function localDateTime(date: Date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}
function newDraft(): Draft {
  const now = new Date();
  return {
    title: "",
    description: "",
    assignment_type: "GENERAL",
    activity_classification: "EXTERNAL",
    priority: "MEDIUM",
    complexity: "STANDARD",
    planned_start_at: localDateTime(now),
    due_at: localDateTime(new Date(now.getTime() + 60 * 60_000)),
    client_ids: [],
    engineer_ids: [],
    related_ticket_ids: [],
    requires_review: false,
    context: {},
  };
}

export function WorkAssignmentsPage() {
  const { user, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightedAssignmentId =
    Number(searchParams.get("assignment_id")) || null;
  const cache = useQueryClient();
  const [scope, setScope] = useState("MINE"),
    [tab, setTab] = useState(0),
    [open, setOpen] = useState(
      () =>
        searchParams.get("create") === "1" &&
        hasPermission("work_assignment.create"),
    );
  const [draft, setDraft] = useState<Draft>(newDraft),
    [ticketSearch, setTicketSearch] = useState("");
  const [editing, setEditing] = useState<WorkAssignment | null>(null);
  const [selectedTickets, setSelectedTickets] = useState<Ticket[]>([]);
  const [detail, setDetail] = useState<WorkAssignment | null>(null);
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [engineerFilter, setEngineerFilter] = useState("ALL");
  const [clientFilter, setClientFilter] = useState("ALL");
  const [evidenceTransition, setEvidenceTransition] = useState<{ item: WorkAssignment; action: "BLOCK" | "COMPLETE" | "APPROVE" } | null>(null);
  const [evidenceNote, setEvidenceNote] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const assignments = useQuery({
    queryKey: ["work-assignments", scope],
    queryFn: async () =>
      (
        await api.get<WorkAssignment[]>("/work-assignments", {
          params: { scope },
        })
      ).data,
    refetchInterval: 30000,
  });
  const people = useQuery({
    queryKey: ["work-assignment-users"],
    enabled: open,
    queryFn: async () =>
      (await api.get<Person[]>("/work-assignments/eligible-assignees")).data,
  });
  const clients = useQuery({
    queryKey: ["work-assignment-clients"],
    enabled: open,
    queryFn: async () => {
      const all: Client[] = [];
      for (let offset = 0; ; offset += 200) {
        const page = (
          await api.get<Client[]>("/clients", {
            params: { limit: 200, offset },
          })
        ).data;
        all.push(...page);
        if (page.length < 200) return all;
      }
    },
  });
  const tickets = useQuery({
    queryKey: ["work-assignment-ticket-search", ticketSearch],
    enabled:
      open &&
      draft.assignment_type === "TICKET_FOLLOW_UP" &&
      ticketSearch.trim().length >= 2,
    queryFn: async () =>
      (
        await api.get<Ticket[]>("/tickets", {
          params: { search: ticketSearch.trim(), limit: 50 },
        })
      ).data,
  });
  const invalidate = () =>
    cache.invalidateQueries({ queryKey: ["work-assignments"] });
  const assignmentPayload = () => {
    const equal = Math.floor(100 / draft.engineer_ids.length);
    const remainder = 100 - equal * draft.engineer_ids.length;
    return {
      ...draft,
      planned_start_at: new Date(draft.planned_start_at).toISOString(),
      due_at: new Date(draft.due_at).toISOString(),
      owner_user_id: draft.engineer_ids[0] ?? null,
      assignees: draft.engineer_ids.map((id, index) => ({
        user_id: id,
        role: index === 0 ? "OWNER" : "CONTRIBUTOR",
        contribution_percent: equal + (index === 0 ? remainder : 0),
      })),
    };
  };
  const closeEditor = () => {
    setOpen(false);
    setEditing(null);
    setDraft(newDraft());
    setSelectedTickets([]);
    setTicketSearch("");
  };
  const create = useMutation({
    mutationFn: async () => api.post("/work-assignments", assignmentPayload()),
    onSuccess: () => {
      closeEditor();
      void invalidate();
    },
  });
  const updateAssignment = useMutation({
    mutationFn: async () =>
      api.put(`/work-assignments/${editing?.id}`, {
        ...assignmentPayload(),
        expected_version: editing?.version,
      }),
    onSuccess: () => {
      closeEditor();
      void invalidate();
    },
  });
  const transition = useMutation({
    mutationFn: async ({
      item,
      action,
    }: {
      item: WorkAssignment;
      action: string;
    }) =>
      api.post(`/work-assignments/${item.id}/transition`, {
        action,
        expected_version: item.version,
        detail: null,
      }),
    onSuccess: () => {
      setDetail(null);
      void invalidate();
    },
  });
  const submitEvidence = useMutation({
    mutationFn: async () => {
      if (!evidenceTransition) return;
      const body = new FormData();
      body.append("action", evidenceTransition.action);
      body.append("expected_version", String(evidenceTransition.item.version));
      body.append("detail", evidenceNote.trim());
      if (evidenceFile) body.append("file", evidenceFile);
      return api.post(`/work-assignments/${evidenceTransition.item.id}/transition-with-evidence`, body);
    },
    onSuccess: () => {
      setEvidenceTransition(null);
      setEvidenceNote("");
      setEvidenceFile(null);
      setDetail(null);
      void invalidate();
    },
  });
  const claim = useMutation({
    mutationFn: async (id: number) => api.post(`/work-assignments/${id}/claim`),
    onSuccess: invalidate,
  });
  const share = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<{ url_token: string }>(
        `/work-assignments/${id}/shares`,
        {},
      );
      const url = new URL(
        `${import.meta.env.BASE_URL.replace(/\/$/, "")}/work-assignment-live/${response.data.url_token}`,
        window.location.origin,
      ).toString();
      if (!(await copyText(url))) throw new Error("The browser could not copy the live link.");
      return url;
    },
  });
  const rows = useMemo(() => assignments.data ?? [], [assignments.data]);
  const filteredRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    return rows.filter(
      (item) =>
        (!term ||
          item.title.toLowerCase().includes(term) ||
          item.description.toLowerCase().includes(term) ||
          item.clients.some((client) => client.name.toLowerCase().includes(term))) &&
        (priorityFilter === "ALL" || item.priority === priorityFilter) &&
        (typeFilter === "ALL" || item.assignment_type === typeFilter) &&
        (engineerFilter === "ALL" || item.assignees.some((assignee) => String(assignee.user_id) === engineerFilter)) &&
        (clientFilter === "ALL" || item.clients.some((client) => String(client.client_id) === clientFilter)),
    );
  }, [clientFilter, engineerFilter, priorityFilter, rows, search, typeFilter]);
  const filterEngineers = useMemo(() => Array.from(new Map(rows.flatMap((item) => item.assignees.map((assignee) => [assignee.user_id, assignee.name] as const))).entries()), [rows]);
  const filterClients = useMemo(() => Array.from(new Map(rows.flatMap((item) => item.clients.map((client) => [client.client_id, client.name] as const))).entries()), [rows]);
  useEffect(() => {
    if (
      !highlightedAssignmentId ||
      !rows.some((item) => item.id === highlightedAssignmentId)
    )
      return;
    document
      .getElementById(`work-assignment-${highlightedAssignmentId}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlightedAssignmentId, rows]);
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((old) => ({ ...old, [key]: value }));
  const setContext = (key: string, value: string) =>
    setDraft((old) => ({ ...old, context: { ...old.context, [key]: value } }));
  const changeType = (value: string) =>
    setDraft((old) => ({
      ...old,
      assignment_type: value,
      context: {},
      related_ticket_ids: [],
      client_ids: [],
    }));
  const editAssignment = (item: WorkAssignment) => {
    setEditing(item);
    setSelectedTickets(
      item.links
        .filter(
          (link) =>
            link.target_type === "TICKET" && link.relation_type === "RELATED",
        )
        .map((link) => ({
          id: link.target_id,
          ticket_number: link.label ?? `#${link.target_id}`,
          subject: "Linked ticket",
        })),
    );
    setDraft({
      title: item.title,
      description: item.description,
      assignment_type: item.assignment_type,
      activity_classification: item.activity_classification,
      priority: item.priority,
      complexity: item.complexity,
      planned_start_at: localDateTime(
        item.planned_start_at ? new Date(item.planned_start_at) : new Date(),
      ),
      due_at: localDateTime(
        item.due_at
          ? new Date(item.due_at)
          : new Date(Date.now() + 60 * 60_000),
      ),
      client_ids: item.clients.map((client) => client.client_id),
      engineer_ids: item.assignees
        .filter((assignee) => assignee.role !== "REVIEWER")
        .sort((a) => (a.role === "OWNER" ? -1 : 1))
        .map((assignee) => assignee.user_id),
      related_ticket_ids: item.links
        .filter(
          (link) =>
            link.target_type === "TICKET" && link.relation_type === "RELATED",
        )
        .map((link) => link.target_id),
      requires_review: item.requires_review,
      context: item.context,
    });
    setOpen(true);
  };
  const needsClient = clientTaskTypes.has(draft.assignment_type);
  const hasRequiredContext = (
    requiredContext[draft.assignment_type] ?? []
  ).every((key) => draft.context[key]?.trim());
  const validDates = Boolean(
    draft.planned_start_at &&
    draft.due_at &&
    new Date(draft.due_at) > new Date(draft.planned_start_at),
  );
  const contextField = (
    key: string,
    label: string,
    required = true,
    multiline = false,
  ) => (
    <Grid size={{ xs: 12, md: multiline ? 12 : 6 }}>
      <TextField
        fullWidth
        required={required}
        multiline={multiline}
        minRows={multiline ? 2 : undefined}
        label={label}
        value={draft.context[key] ?? ""}
        onChange={(e) => setContext(key, e.target.value)}
      />
    </Grid>
  );

  const transitionForDrop = (item: WorkAssignment, target: string) => {
    if (item.status === target) return;
    const action =
      target === "ACCEPTED" && item.status === "ASSIGNED"
        ? "ACCEPT"
        : target === "IN_PROGRESS" && item.status === "BLOCKED"
          ? "RESUME"
          : target === "IN_PROGRESS" && ["ASSIGNED", "ACCEPTED", "RETURNED"].includes(item.status)
            ? "START"
            : target === "BLOCKED" && ["ACCEPTED", "IN_PROGRESS", "RETURNED"].includes(item.status)
              ? "BLOCK"
              : target === "AWAITING_REVIEW" && ["IN_PROGRESS", "RETURNED"].includes(item.status)
                ? "SUBMIT"
                : target === "COMPLETED" && item.status === "AWAITING_REVIEW"
                  ? "APPROVE"
                  : target === "COMPLETED" && ["IN_PROGRESS", "RETURNED"].includes(item.status)
                    ? "COMPLETE"
                    : target === "ASSIGNED" && terminal.has(item.status)
                      ? "REOPEN"
                      : null;
    if (action && ["BLOCK", "COMPLETE", "APPROVE"].includes(action)) {
      setEvidenceNote("");
      setEvidenceFile(null);
      setEvidenceTransition({ item, action: action as "BLOCK" | "COMPLETE" | "APPROVE" });
    } else if (action) transition.mutate({ item, action });
  };

  const requestTransition = (item: WorkAssignment, action: string) => {
    if (["BLOCK", "COMPLETE", "APPROVE"].includes(action)) {
      setEvidenceNote("");
      setEvidenceFile(null);
      setEvidenceTransition({ item, action: action as "BLOCK" | "COMPLETE" | "APPROVE" });
      return;
    }
    transition.mutate({ item, action });
  };

  const renderCard = (item: WorkAssignment, board = false) => (
    <Card
      key={item.id}
      id={`work-assignment-${item.id}`}
      draggable={
        board &&
        !terminal.has(item.status) &&
        (item.assignees.some((assignee) => assignee.user_id === user?.id) ||
          item.created_by_user_id === user?.id ||
          hasPermission("work_assignment.manage"))
      }
      onDragStart={() => setDraggedId(item.id)}
      onDragEnd={() => setDraggedId(null)}
      onClick={() => setDetail(item)}
      variant="outlined"
      sx={{
        cursor: "pointer",
        borderRadius: 3,
        borderColor:
          item.id === highlightedAssignmentId ? "primary.main" : "divider",
        borderWidth: item.id === highlightedAssignmentId ? 2 : 1,
        boxShadow: board ? "0 8px 24px rgba(15,23,42,.07)" : undefined,
        opacity: draggedId === item.id ? 0.55 : 1,
        transition: "transform .16s ease, box-shadow .16s ease",
        "&:hover": { transform: "translateY(-2px)", boxShadow: 4 },
      }}
    >
      <CardContent sx={{ p: board ? 1.5 : 2, "&:last-child": { pb: board ? 1.5 : 2 } }}>
        <Stack direction="row" gap={0.75} flexWrap="wrap" alignItems="center">
          <Chip size="small" label={item.priority} color={item.priority === "CRITICAL" ? "error" : item.priority === "HIGH" ? "warning" : "default"} />
          <Chip size="small" variant="outlined" label={item.assignment_type.replaceAll("_", " ")} />
          {item.requires_review && <Chip size="small" color="info" label="Review" />}
        </Stack>
        <Typography fontWeight={800} mt={1}>{item.title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", minHeight: 40 }}>
          {item.description}
        </Typography>
        {!!item.clients.length && <Typography variant="caption" color="primary.main" display="block" mt={1}>{item.clients.map((client) => client.name).join(", ")}</Typography>}
        <Stack direction="row" gap={0.5} alignItems="center" mt={1}><Groups fontSize="small" color="action" /><Typography variant="caption" color="text.secondary">{item.assignees.map((assignee) => assignee.name).join(", ") || "Team queue"}</Typography></Stack>
        {item.due_at && <Typography variant="caption" color={new Date(item.due_at) < new Date() && !terminal.has(item.status) ? "error.main" : "text.secondary"} display="block" mt={0.5}>Due {new Date(item.due_at).toLocaleString()}</Typography>}
        <Box mt={1}><Slider size="small" value={item.progress_percent} disabled /><Typography variant="caption">{item.progress_percent}% complete</Typography></Box>
        <Stack direction="row" gap={0.5} flexWrap="wrap" mt={1} onClick={(event) => event.stopPropagation()}>
          {scope === "QUEUE" && item.owner_user_id == null && <Button size="small" onClick={() => claim.mutate(item.id)}>Claim</Button>}
          {item.status === "ASSIGNED" && item.assignees.some((assignee) => assignee.user_id === user?.id) && <Button size="small" onClick={() => transition.mutate({ item, action: "ACCEPT" })}>Accept</Button>}
          {["ASSIGNED", "ACCEPTED", "RETURNED"].includes(item.status) && item.assignees.some((assignee) => assignee.user_id === user?.id) && <Button size="small" onClick={() => transition.mutate({ item, action: "START" })}>Start</Button>}
          <Button size="small" startIcon={<Visibility />} onClick={() => setDetail(item)}>Details</Button>
          {!terminal.has(item.status) && (item.created_by_user_id === user?.id || hasPermission("work_assignment.manage")) && <Button size="small" startIcon={<Edit />} onClick={() => editAssignment(item)}>Edit</Button>}
          {hasPermission("work_assignment.share") && <Button size="small" startIcon={<Share />} onClick={() => share.mutate(item.id)}>Live link</Button>}
        </Stack>
      </CardContent>
    </Card>
  );

  return (
    <Stack spacing={2}>
      {(assignments.isLoading ||
        create.isPending ||
        updateAssignment.isPending ||
        transition.isPending) && <LinearProgress />}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Box flexGrow={1}>
          <Typography variant="h4" fontWeight={850}>
            Work Assignments
          </Typography>
          <Typography color="text.secondary">
            Assign, claim, track, convert, and measure team work without
            duplicating tickets or visits.
          </Typography>
        </Box>
        {hasPermission("work_assignment.create") && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setEditing(null);
              setDraft(newDraft());
              setSelectedTickets([]);
              setOpen(true);
            }}
          >
            Assign task
          </Button>
        )}
      </Stack>
      <Tabs
        value={tab}
        onChange={(_, value) => {
          setTab(value);
          setScope(["MINE", "CREATED", "TEAM", "QUEUE"][value]);
        }}
        variant="scrollable"
      >
        <Tab label="My tasks" />
        <Tab label="Created by me" />
        <Tab label="Team" />
        <Tab label="Queue" />
      </Tabs>
      {assignments.isError && (
        <Alert severity="error">
          Tasks could not be loaded. Check your assignment permissions.
        </Alert>
      )}
      {transition.isError && (
        <Alert severity="error">
          That workflow move is not allowed from the task's current status or
          by your permissions. Refresh and try again.
        </Alert>
      )}
      {share.isSuccess && (
        <Alert severity="success" action={<Button color="inherit" size="small" onClick={() => window.open(share.data, "_blank", "noopener,noreferrer")}>Open link</Button>}>Live update link copied. It is ready to share.</Alert>
      )}
      {share.isError && <Alert severity="error">The live link could not be created or copied. Check sharing permission and browser clipboard access.</Alert>}
      {!rows.length && !assignments.isLoading && (
        <Alert severity="info">No work assignments in this view.</Alert>
      )}
      <Card variant="outlined" sx={{ borderRadius: 3 }}>
        <CardContent>
          <Stack direction={{ xs: "column", lg: "row" }} gap={1} alignItems={{ lg: "center" }}>
            <TextField size="small" label="Search tasks or clients" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ minWidth: 240 }} />
            <TextField size="small" select label="Priority" value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)} sx={{ minWidth: 130 }}><MenuItem value="ALL">All priorities</MenuItem>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField>
            <TextField size="small" select label="Task type" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} sx={{ minWidth: 170 }}><MenuItem value="ALL">All types</MenuItem>{taskTypes.map((value) => <MenuItem key={value} value={value}>{value.replaceAll("_", " ")}</MenuItem>)}</TextField>
            <TextField size="small" select label="Engineer" value={engineerFilter} onChange={(event) => setEngineerFilter(event.target.value)} sx={{ minWidth: 170 }}><MenuItem value="ALL">All engineers</MenuItem>{filterEngineers.map(([id, name]) => <MenuItem key={id} value={String(id)}>{name}</MenuItem>)}</TextField>
            <TextField size="small" select label="Client" value={clientFilter} onChange={(event) => setClientFilter(event.target.value)} sx={{ minWidth: 170 }}><MenuItem value="ALL">All clients</MenuItem>{filterClients.map(([id, name]) => <MenuItem key={id} value={String(id)}>{name}</MenuItem>)}</TextField>
            <Button startIcon={<FilterAltOff />} onClick={() => { setSearch(""); setPriorityFilter("ALL"); setTypeFilter("ALL"); setEngineerFilter("ALL"); setClientFilter("ALL"); }}>Clear</Button>
            <Chip label={`${filteredRows.length} tasks`} color="primary" variant="outlined" />
          </Stack>
        </CardContent>
      </Card>
      {(scope === "MINE" || scope === "CREATED") && (
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(270px, 1fr))", gap: 1.5, overflowX: "auto", pb: 1 }}>
          {boardLanes.map((lane) => {
            const laneRows = filteredRows.filter((item) => item.status === lane.status || (lane.status === "ASSIGNED" && item.status === "RETURNED") || (lane.status === "COMPLETED" && item.status === "CANCELLED"));
            return <Box key={lane.status} onDragOver={(event) => event.preventDefault()} onDrop={() => { const item = rows.find((row) => row.id === draggedId); if (item) transitionForDrop(item, lane.status); setDraggedId(null); }} sx={{ bgcolor: "action.hover", borderRadius: 3, p: 1, minHeight: 420, border: 1, borderColor: "divider" }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}><Stack direction="row" alignItems="center" gap={1}><Box sx={{ width: 9, height: 9, borderRadius: "50%", bgcolor: lane.color }} /><Typography fontWeight={800}>{lane.label}</Typography></Stack><Chip size="small" label={laneRows.length} /></Stack>
              <Stack spacing={1}>{laneRows.map((item) => renderCard(item, true))}{!laneRows.length && <Box sx={{ py: 5, textAlign: "center", color: "text.secondary", border: "1px dashed", borderColor: "divider", borderRadius: 2 }}><Typography variant="caption">Drop valid tasks here</Typography></Box>}</Stack>
            </Box>;
          })}
        </Box>
      )}
      <Grid container spacing={2} sx={{ display: scope === "MINE" || scope === "CREATED" ? "none" : undefined }}>
        {filteredRows.map((item) => (
          <Grid key={item.id} size={{ xs: 12, md: 6, xl: 4 }}>
            <Card
              id={`work-assignment-${item.id}`}
              variant="outlined"
              sx={{
                height: "100%",
                borderRadius: 3,
                borderColor:
                  item.id === highlightedAssignmentId
                    ? "primary.main"
                    : undefined,
                borderWidth: item.id === highlightedAssignmentId ? 2 : 1,
              }}
            >
              <CardContent>
                <Stack direction="row" gap={1} flexWrap="wrap">
                  <Chip
                    size="small"
                    label={item.status.replaceAll("_", " ")}
                    color={
                      item.status === "COMPLETED"
                        ? "success"
                        : item.status === "BLOCKED"
                          ? "error"
                          : "default"
                    }
                  />
                  <Chip
                    size="small"
                    label={item.priority}
                    color={item.priority === "CRITICAL" ? "error" : "default"}
                  />
                  <Chip size="small" label={item.activity_classification} />
                  <Chip
                    size="small"
                    variant="outlined"
                    label={item.assignment_type.replaceAll("_", " ")}
                  />
                </Stack>
                <Typography variant="h6" fontWeight={800} mt={1}>
                  {item.title}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {item.description}
                </Typography>
                {item.links
                  .filter((link) => link.target_type === "TICKET")
                  .map((link) => (
                    <Button
                      key={link.target_id}
                      size="small"
                      sx={{ mt: 1 }}
                      onClick={() => navigate(`/tickets/${link.target_id}`)}
                    >
                      {link.relation_type === "CONVERTED_TO"
                        ? "Open converted ticket"
                        : "Open linked ticket"}{" "}
                      #{link.target_id}
                    </Button>
                  ))}
                <Stack direction="row" gap={0.5} alignItems="center" mt={2}>
                  <Groups fontSize="small" />
                  <Typography variant="body2">
                    {item.assignees
                      .map((a) => `${a.name} (${a.contribution_percent}%)`)
                      .join(", ") || "Team queue"}
                  </Typography>
                </Stack>
                <Box mt={2}>
                  <Typography variant="caption">
                    Progress {item.progress_percent}%
                  </Typography>
                  <Slider size="small" value={item.progress_percent} disabled />
                </Box>
                <Stack direction="row" gap={1} flexWrap="wrap" mt={1}>
                  {scope === "QUEUE" && item.owner_user_id == null && (
                    <Button size="small" onClick={() => claim.mutate(item.id)}>
                      Claim
                    </Button>
                  )}
                  {item.status === "ASSIGNED" &&
                    item.assignees.some((a) => a.user_id === user?.id) && (
                      <Button
                        size="small"
                        startIcon={<AssignmentTurnedIn />}
                        onClick={() =>
                          transition.mutate({ item, action: "ACCEPT" })
                        }
                      >
                        Accept
                      </Button>
                    )}
                  {["ASSIGNED", "ACCEPTED", "RETURNED"].includes(item.status) &&
                    item.assignees.some((a) => a.user_id === user?.id) && (
                      <Button
                        size="small"
                        startIcon={<PlayArrow />}
                        onClick={() =>
                          transition.mutate({ item, action: "START" })
                        }
                      >
                        Start
                      </Button>
                    )}
                  {item.status === "IN_PROGRESS" &&
                    item.assignees.some((a) => a.user_id === user?.id) && (
                      <Button
                        size="small"
                        startIcon={<TaskAlt />}
                        onClick={() =>
                          requestTransition(item, "COMPLETE")
                        }
                      >
                        Complete
                      </Button>
                    )}
                  {!terminal.has(item.status) &&
                    item.kpi_source_type === "ASSIGNMENT" &&
                    hasPermission("ticket.create") &&
                    item.assignees.some((a) => a.user_id === user?.id) && (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() =>
                          navigate(
                            `/tickets/create?work_assignment_id=${item.id}`,
                            { state: { returnTo: "/work-assignments" } },
                          )
                        }
                      >
                        Convert to ticket
                      </Button>
                    )}
                  {!terminal.has(item.status) &&
                    (item.created_by_user_id === user?.id ||
                      hasPermission("work_assignment.manage")) && (
                      <Button
                        size="small"
                        startIcon={<Edit />}
                        onClick={() => editAssignment(item)}
                      >
                        Edit
                      </Button>
                    )}
                  {hasPermission("work_assignment.share") && (
                    <Button
                      size="small"
                      startIcon={<Share />}
                      onClick={() => share.mutate(item.id)}
                    >
                      Copy live link
                    </Button>
                  )}
                  {terminal.has(item.status) && (
                    <Chip size="small" label="KPI finalized" color="success" />
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
      <Dialog open={Boolean(evidenceTransition)} onClose={() => !submitEvidence.isPending && setEvidenceTransition(null)} fullWidth maxWidth="sm">
        <DialogTitle>{evidenceTransition?.action === "BLOCK" ? "Block task with evidence" : "Close task with evidence"}</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>Written evidence is required. You may also attach a supporting screenshot, document, or log file.</Alert>
          <TextField autoFocus fullWidth required multiline minRows={4} label={evidenceTransition?.action === "BLOCK" ? "Blocking reason and evidence" : "Completion evidence and result"} value={evidenceNote} onChange={(event) => setEvidenceNote(event.target.value)} />
          <Stack direction="row" gap={1} alignItems="center" mt={2}>
            <Button component="label" variant="outlined" startIcon={<AttachFile />}>Attach evidence<input hidden type="file" onChange={(event) => setEvidenceFile(event.target.files?.[0] ?? null)} /></Button>
            <Typography variant="body2" color="text.secondary">{evidenceFile?.name ?? "No file selected"}</Typography>
          </Stack>
          {submitEvidence.isError && <Alert severity="error" sx={{ mt: 2 }}>The evidence or workflow change could not be saved. Refresh the task and try again.</Alert>}
        </DialogContent>
        <DialogActions><Button disabled={submitEvidence.isPending} onClick={() => setEvidenceTransition(null)}>Cancel</Button><Button variant="contained" disabled={evidenceNote.trim().length < 3 || submitEvidence.isPending} onClick={() => submitEvidence.mutate()}>{submitEvidence.isPending ? "Saving…" : evidenceTransition?.action === "BLOCK" ? "Block task" : "Close task"}</Button></DialogActions>
      </Dialog>
      <Dialog open={Boolean(detail)} onClose={() => setDetail(null)} fullWidth maxWidth="md">
        {detail && <>
          <DialogTitle><Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}><Box><Typography variant="overline">Task #{detail.id} · {detail.assignment_type.replaceAll("_", " ")}</Typography><Typography variant="h5" fontWeight={850}>{detail.title}</Typography></Box><Chip label={detail.status.replaceAll("_", " ")} color={detail.status === "COMPLETED" ? "success" : detail.status === "BLOCKED" ? "error" : "primary"} /></Stack></DialogTitle>
          <DialogContent>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 8 }}><Typography color="text.secondary" whiteSpace="pre-wrap">{detail.description}</Typography></Grid>
              <Grid size={{ xs: 12, md: 4 }}><Card variant="outlined"><CardContent><Typography variant="caption" color="text.secondary">Progress</Typography><Typography variant="h4" fontWeight={850}>{detail.progress_percent}%</Typography><Slider value={detail.progress_percent} disabled /></CardContent></Card></Grid>
              <Grid size={{ xs: 12, md: 6 }}><Typography fontWeight={800}>Schedule</Typography><Typography variant="body2">Planned: {detail.planned_start_at ? new Date(detail.planned_start_at).toLocaleString() : "Not set"}</Typography><Typography variant="body2">Due: {detail.due_at ? new Date(detail.due_at).toLocaleString() : "Not set"}</Typography><Typography variant="body2">Priority: {detail.priority} · Complexity: {detail.complexity}</Typography></Grid>
              <Grid size={{ xs: 12, md: 6 }}><Typography fontWeight={800}>Engineers</Typography>{detail.assignees.map((assignee) => <Typography key={assignee.user_id} variant="body2">{assignee.name} · {assignee.role.replaceAll("_", " ")} · {assignee.contribution_percent}%</Typography>)}</Grid>
              {!!detail.clients.length && <Grid size={{ xs: 12, md: 6 }}><Typography fontWeight={800}>Clients</Typography><Stack direction="row" gap={0.5} flexWrap="wrap">{detail.clients.map((client) => <Chip key={client.client_id} size="small" label={client.name} />)}</Stack></Grid>}
              {!!Object.keys(detail.context).length && <Grid size={{ xs: 12, md: 6 }}><Typography fontWeight={800}>Task details</Typography>{Object.entries(detail.context).filter(([, value]) => value).map(([key, value]) => <Box key={key} mt={0.5}><Typography variant="caption" color="text.secondary">{key.replaceAll("_", " ")}</Typography><Typography variant="body2" whiteSpace="pre-wrap">{value}</Typography></Box>)}</Grid>}
              {!!detail.links.length && <Grid size={12}><Typography fontWeight={800}>Linked records</Typography><Stack direction="row" gap={1} flexWrap="wrap">{detail.links.filter((link) => link.target_type === "TICKET").map((link) => <Button key={`${link.relation_type}-${link.target_id}`} variant="outlined" size="small" onClick={() => navigate(`/tickets/${link.target_id}`)}>{link.relation_type === "CONVERTED_TO" ? "Converted ticket" : "Related ticket"} {link.label ?? `#${link.target_id}`}</Button>)}</Stack></Grid>}
              {!!detail.evidence.length && <Grid size={12}><Typography fontWeight={800}>Status evidence</Typography><Stack gap={1} mt={0.5}>{detail.evidence.map((item) => <Card key={item.id} variant="outlined"><CardContent sx={{ py: 1.25, "&:last-child": { pb: 1.25 } }}><Stack direction="row" justifyContent="space-between" gap={1}><Chip size="small" label={item.evidence_type} color={item.evidence_type === "BLOCK" ? "error" : "success"} /><Typography variant="caption" color="text.secondary">{new Date(item.created_at).toLocaleString()}</Typography></Stack><Typography variant="body2" whiteSpace="pre-wrap" mt={1}>{item.note}</Typography>{item.original_filename && <Typography variant="caption" color="text.secondary" display="block" mt={0.5}><AttachFile sx={{ fontSize: 14, verticalAlign: "text-bottom" }} /> {item.original_filename}</Typography>}</CardContent></Card>)}</Stack></Grid>}
            </Grid>
          </DialogContent>
          <DialogActions sx={{ flexWrap: "wrap" }}>
            {detail.status === "ASSIGNED" && detail.assignees.some((assignee) => assignee.user_id === user?.id) && <Button onClick={() => transition.mutate({ item: detail, action: "ACCEPT" })}>Accept</Button>}
            {["ASSIGNED", "ACCEPTED", "RETURNED"].includes(detail.status) && detail.assignees.some((assignee) => assignee.user_id === user?.id) && <Button startIcon={<PlayArrow />} onClick={() => transition.mutate({ item: detail, action: "START" })}>Start</Button>}
            {detail.status === "IN_PROGRESS" && detail.assignees.some((assignee) => assignee.user_id === user?.id) && <Button onClick={() => requestTransition(detail, detail.requires_review ? "SUBMIT" : "COMPLETE")}>{detail.requires_review ? "Submit for review" : "Complete"}</Button>}
            {detail.status === "AWAITING_REVIEW" && (detail.created_by_user_id === user?.id || hasPermission("work_assignment.manage")) && <Button onClick={() => requestTransition(detail, "APPROVE")}>Approve and close</Button>}
            {!terminal.has(detail.status) && detail.kpi_source_type === "ASSIGNMENT" && hasPermission("ticket.create") && detail.assignees.some((assignee) => assignee.user_id === user?.id) && <Button onClick={() => navigate(`/tickets/create?work_assignment_id=${detail.id}`, { state: { returnTo: "/work-assignments" } })}>Convert to ticket</Button>}
            {!terminal.has(detail.status) && (detail.created_by_user_id === user?.id || hasPermission("work_assignment.manage")) && <Button startIcon={<Edit />} onClick={() => { setDetail(null); editAssignment(detail); }}>Edit</Button>}
            {hasPermission("work_assignment.share") && <Button startIcon={<Share />} onClick={() => share.mutate(detail.id)}>Copy live link</Button>}
            <Button onClick={() => setDetail(null)}>Close</Button>
          </DialogActions>
        </>}
      </Dialog>
      <Dialog open={open} onClose={closeEditor} fullWidth maxWidth="md">
        <DialogTitle>
          {editing
            ? `Edit work assignment #${editing.id}`
            : "Assign work to one or more engineers"}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} mt={0.2}>
            <Grid size={{ xs: 12, md: 8 }}>
              <TextField
                fullWidth
                required
                label="Title"
                value={draft.title}
                onChange={(e) => set("title", e.target.value)}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                select
                fullWidth
                label="Priority"
                value={draft.priority}
                onChange={(e) => set("priority", e.target.value)}
              >
                {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((x) => (
                  <MenuItem key={x} value={x}>
                    {x}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth
                required
                multiline
                minRows={3}
                label="Instructions"
                value={draft.description}
                onChange={(e) => set("description", e.target.value)}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                select
                fullWidth
                label="Task type"
                value={draft.assignment_type}
                onChange={(e) => changeType(e.target.value)}
              >
                {taskTypes.map((x) => (
                  <MenuItem key={x} value={x}>
                    {x.replaceAll("_", " ")}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                select
                fullWidth
                label="KPI classification"
                value={draft.activity_classification}
                onChange={(e) => set("activity_classification", e.target.value)}
              >
                {["EXTERNAL", "INTERNAL", "MIXED", "NOT_APPLICABLE"].map(
                  (x) => (
                    <MenuItem key={x} value={x}>
                      {x}
                    </MenuItem>
                  ),
                )}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                required
                type="datetime-local"
                label="Planned start"
                slotProps={{ inputLabel: { shrink: true } }}
                value={draft.planned_start_at}
                onChange={(e) => set("planned_start_at", e.target.value)}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                required
                type="datetime-local"
                label="Due"
                error={!validDates}
                helperText={
                  !validDates ? "Due time must be after the planned start." : ""
                }
                slotProps={{ inputLabel: { shrink: true } }}
                value={draft.due_at}
                onChange={(e) => set("due_at", e.target.value)}
              />
            </Grid>
            {draft.assignment_type === "GENERAL" &&
              contextField("expected_outcome", "Expected outcome")}
            {draft.assignment_type === "CLIENT_REQUEST" &&
              contextField(
                "request_reference",
                "Client request / contact reference",
              )}
            {draft.assignment_type === "SYSTEM_UPGRADE" && (
              <>
                {contextField("current_version", "Current version", false)}
                {contextField("target_version", "Target version")}
              </>
            )}
            {draft.assignment_type === "CHECKLIST" && (
              <>
                {contextField("checklist_name", "Checklist name")}
                {contextField(
                  "checklist_items",
                  "Checklist items (one per line)",
                  true,
                  true,
                )}
              </>
            )}
            {draft.assignment_type === "REMOTE_ACTIVITY" && (
              <>
                {contextField("remote_method", "Remote access method")}
                {contextField(
                  "connection_reference",
                  "Connection / session reference",
                  false,
                )}
              </>
            )}
            {draft.assignment_type === "VISIT_CANDIDATE" && (
              <>
                {contextField("visit_location", "Visit location")}
                {contextField(
                  "preferred_window",
                  "Preferred visit window",
                  false,
                )}
              </>
            )}
            {draft.assignment_type === "TICKET_CANDIDATE" &&
              contextField("issue_summary", "Issue summary", true, true)}
            {draft.assignment_type === "INTERNAL_OPERATION" && (
              <>
                {contextField("operation_type", "Operation type")}
                {contextField("operation_location", "Location / system", false)}
              </>
            )}
            {draft.assignment_type === "TICKET_FOLLOW_UP" && (
              <Grid size={12}>
                <Autocomplete
                  multiple
                  options={tickets.data ?? []}
                  value={selectedTickets}
                  loading={tickets.isFetching}
                  filterOptions={(options) => options}
                  getOptionLabel={(ticket) =>
                    `${ticket.ticket_number} — ${ticket.subject}`
                  }
                  isOptionEqualToValue={(option, value) =>
                    option.id === value.id
                  }
                  onInputChange={(_, value) => setTicketSearch(value)}
                  onChange={(_, value) => {
                    setSelectedTickets(value);
                    set(
                      "related_ticket_ids",
                      value.map((ticket) => ticket.id),
                    );
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      required
                      label="Search and link tickets"
                      helperText="Type at least 2 characters. Linked tickets are clickable from the task."
                    />
                  )}
                />
              </Grid>
            )}
            {needsClient && (
              <Grid size={12}>
                <TextField
                  select
                  required
                  fullWidth
                  label="Clients (multiple allowed)"
                  value={draft.client_ids.map(String)}
                  onChange={(e) =>
                    set(
                      "client_ids",
                      (typeof e.target.value === "string"
                        ? e.target.value.split(",")
                        : e.target.value
                      ).map(Number),
                    )
                  }
                  slotProps={{ select: { multiple: true } }}
                >
                  {clients.data?.map((client) => (
                    <MenuItem key={client.id} value={String(client.id)}>
                      {client.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
            )}
            <Grid size={12}>
              <TextField
                select
                required
                fullWidth
                label="Support engineers (multiple allowed)"
                value={draft.engineer_ids.map(String)}
                onChange={(e) =>
                  set(
                    "engineer_ids",
                    (typeof e.target.value === "string"
                      ? e.target.value.split(",")
                      : e.target.value
                    ).map(Number),
                  )
                }
                slotProps={{ select: { multiple: true } }}
              >
                {people.data?.map((person) => (
                  <MenuItem key={person.id} value={String(person.id)}>
                    {person.full_name}
                  </MenuItem>
                ))}
              </TextField>
              <Typography variant="caption">
                The first engineer is accountable; KPI credit is split equally
                and stored per engineer.
              </Typography>
            </Grid>
            <Grid size={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={draft.requires_review}
                    onChange={(e) => set("requires_review", e.target.checked)}
                  />
                }
                label="Require manager review before completion"
              />
            </Grid>
          </Grid>
          {(create.isError || updateAssignment.isError) && (
            <Alert severity="error" sx={{ mt: 2 }}>
              The assignment could not be saved. Verify assignees, clients,
              linked tickets, required fields, and whether another user changed
              it.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeEditor}>Cancel</Button>
          <Button
            variant="contained"
            disabled={
              draft.title.trim().length < 3 ||
              draft.description.trim().length < 3 ||
              !draft.engineer_ids.length ||
              !hasRequiredContext ||
              (draft.assignment_type === "TICKET_FOLLOW_UP" &&
                !draft.related_ticket_ids.length) ||
              (needsClient && !draft.client_ids.length) ||
              !validDates ||
              create.isPending ||
              updateAssignment.isPending
            }
            onClick={() =>
              editing ? updateAssignment.mutate() : create.mutate()
            }
          >
            {editing ? "Save changes" : "Create assignment"}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
