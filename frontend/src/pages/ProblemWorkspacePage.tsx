import { ArrowBack, AttachFile, Edit, LinkOff } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TechnicalText } from "../components/TechnicalText";

type Problem = {
  id: number;
  problem_number: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  business_impact?: string | null;
  symptoms?: string | null;
  workaround?: string | null;
  known_error_summary?: string | null;
  root_cause_summary?: string | null;
  permanent_fix_summary?: string | null;
  target_resolution_date?: string | null;
  version: number;
};
type Comment = {
  id: number;
  body: string;
  author_user_id: number;
  created_at: string;
};
type Task = {
  id: number;
  title: string;
  description?: string | null;
  status: string;
  due_at?: string | null;
  version: number;
};
type Attachment = {
  id: number;
  original_filename: string;
  size_bytes: number;
  scan_status: string;
  created_at: string;
};
type History = {
  id: number;
  from_status: string;
  to_status: string;
  reason?: string | null;
  changed_by_name: string;
  changed_at: string;
};
type Link = {
  id?: number;
  ticket_id?: number;
  ticket_number?: string | null;
  subject?: string;
  article_id?: number;
  title?: string;
  link_type: string;
};
type Option = {
  id: number;
  name?: string;
  title?: string;
  status?: string;
  ticket_number?: string;
  subject?: string;
  ticket_id?: number;
  version?: number;
};

const transitions: Record<string, string[]> = {
  NEW: ["INVESTIGATING", "CANCELLED"],
  INVESTIGATING: ["ROOT_CAUSE_IDENTIFIED", "CANCELLED"],
  ROOT_CAUSE_IDENTIFIED: ["KNOWN_ERROR", "FIX_PROPOSED", "CANCELLED"],
  KNOWN_ERROR: ["FIX_PROPOSED", "CANCELLED"],
  FIX_PROPOSED: ["FIX_IMPLEMENTED", "CANCELLED"],
  FIX_IMPLEMENTED: ["MONITORING"],
  MONITORING: ["CLOSED", "INVESTIGATING"],
  CLOSED: ["INVESTIGATING"],
  CANCELLED: ["INVESTIGATING"],
};
const label = (value?: string | null) =>
  value ? value.replaceAll("_", " ") : "—";
const optional = (value: FormDataEntryValue | null) =>
  String(value ?? "").trim() || null;
const dateInput = (value?: string | null) => (value ? value.slice(0, 16) : "");
function Detail({ title, value }: { title: string; value?: string | null }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {title}
      </Typography>
      <Typography sx={{ whiteSpace: "pre-wrap" }}>{value || "—"}</Typography>
    </Box>
  );
}

export function ProblemWorkspacePage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const problemId = Number(id);
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  const [relationOpen, setRelationOpen] = useState(false);
  const [relationKind, setRelationKind] = useState("ticket");
  const [unlinkTicket, setUnlinkTicket] = useState<Link | null>(null);
  const [unlinkReason, setUnlinkReason] = useState("");
  const [error, setError] = useState("");
  const problem = useQuery({
    queryKey: ["problem", problemId],
    queryFn: async () =>
      (await api.get<Problem>(`/problems/${problemId}`)).data,
    enabled: Number.isFinite(problemId),
  });
  const comments = useQuery({
    queryKey: ["problem-comments", problemId],
    queryFn: async () =>
      (await api.get<Comment[]>(`/problems/${problemId}/comments`)).data,
    enabled: !!problem.data,
  });
  const tasks = useQuery({
    queryKey: ["problem-tasks", problemId],
    queryFn: async () =>
      (await api.get<Task[]>(`/problems/${problemId}/tasks`)).data,
    enabled: !!problem.data,
  });
  const attachments = useQuery({
    queryKey: ["problem-attachments", problemId],
    queryFn: async () =>
      (await api.get<Attachment[]>(`/problems/${problemId}/attachments`)).data,
    enabled: !!problem.data,
  });
  const history = useQuery({
    queryKey: ["problem-history", problemId],
    queryFn: async () =>
      (await api.get<History[]>(`/problems/${problemId}/history`)).data,
    enabled: !!problem.data,
  });
  const tickets = useQuery({
    queryKey: ["problem-tickets", problemId],
    queryFn: async () =>
      (await api.get<Link[]>(`/problems/${problemId}/tickets`)).data,
    enabled: !!problem.data,
  });
  const changes = useQuery({
    queryKey: ["problem-changes", problemId],
    queryFn: async () =>
      (await api.get<Link[]>(`/problems/${problemId}/changes`)).data,
    enabled: !!problem.data,
  });
  const knowledge = useQuery({
    queryKey: ["problem-knowledge", problemId],
    queryFn: async () =>
      (await api.get<Link[]>(`/problems/${problemId}/knowledge`)).data,
    enabled: !!problem.data,
  });
  const rootCauses = useQuery({
    queryKey: ["problem-root-causes", problemId],
    queryFn: async () =>
      (await api.get<Option[]>(`/problems/${problemId}/root-causes`)).data,
    enabled: !!problem.data,
  });
  const ticketOptions = useQuery({
    queryKey: ["problem-ticket-options"],
    queryFn: async () =>
      (await api.get<Option[]>("/tickets", { params: { limit: 200 } })).data,
    enabled: relationOpen && relationKind === "ticket",
  });
  const changeOptions = useQuery({
    queryKey: ["problem-change-options"],
    queryFn: async () =>
      (await api.get<Option[]>("/change-requests", { params: { limit: 200 } }))
        .data,
    enabled: relationOpen && relationKind === "change",
  });
  const knowledgeOptions = useQuery({
    queryKey: ["problem-knowledge-options"],
    queryFn: async () =>
      (
        await api.get<Option[]>("/knowledge", {
          params: { published_only: true, limit: 200 },
        })
      ).data,
    enabled: relationOpen && relationKind === "knowledge",
  });
  const rootCauseOptions = useQuery({
    queryKey: ["problem-root-cause-options"],
    queryFn: async () => (await api.get<Option[]>("/root-causes")).data,
    enabled: relationOpen && relationKind === "root_cause",
  });
  const refresh = () =>
    queryClient.invalidateQueries({
      predicate: (query) => String(query.queryKey[0]).startsWith("problem"),
    });
  const mutate = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.patch(`/problems/${problemId}`, payload)).data,
    onSuccess: async () => {
      setEditOpen(false);
      setError("");
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const move = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post(`/problems/${problemId}/transition`, payload)).data,
    onSuccess: async () => {
      setMoveOpen(false);
      setError("");
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const addComment = useMutation({
    mutationFn: (body: string) =>
      api.post(`/problems/${problemId}/comments`, { body, is_internal: true }),
    onSuccess: () => refresh(),
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const addTask = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post(`/problems/${problemId}/tasks`, payload),
    onSuccess: () => refresh(),
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const updateTask = useMutation({
    mutationFn: ({ task, status }: { task: Task; status: string }) =>
      api.patch(`/problems/${problemId}/tasks/${task.id}`, {
        status,
        version: task.version,
      }),
    onSuccess: () => refresh(),
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const upload = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api.post(`/problems/${problemId}/attachments`, body);
    },
    onSuccess: () => refresh(),
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const relationship = useMutation({
    mutationFn: async (data: FormData) => {
      const selectedIds = String(data.get("selected_id") ?? "")
        .split(",")
        .map(Number)
        .filter((value) => Number.isInteger(value) && value > 0);
      const selectedId = selectedIds[0];
      const linkType = String(data.get("link_type") ?? "RELATED");
      const version = problem.data?.version;
      if (!version) throw new Error("Problem version is unavailable.");
      if (relationKind === "ticket")
        return api.post(`/problems/${problemId}/tickets`, {
          ticket_ids: selectedIds,
          link_type: linkType,
          version,
        });
      if (relationKind === "change")
        return api.post(`/problems/${problemId}/changes`, {
          ticket_id: selectedId,
          link_type: linkType,
          version,
        });
      if (relationKind === "knowledge")
        return api.post(`/problems/${problemId}/knowledge`, {
          article_id: selectedId,
          link_type: linkType,
          version,
        });
      return api.post(`/problems/${problemId}/root-causes`, {
        root_cause_ids: [
          ...new Set([
            ...(rootCauses.data ?? []).map((item) => item.id),
            selectedId,
          ]),
        ],
        version,
      });
    },
    onSuccess: async () => {
      setRelationOpen(false);
      setError("");
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const unlinkRelationship = useMutation({
    mutationFn: async ({ ticketId, reason }: { ticketId: number; reason: string }) => {
      const version = problem.data?.version;
      if (!version) throw new Error("Problem version is unavailable.");
      return api.delete(`/problems/${problemId}/tickets/${ticketId}`, {
        data: { version, reason },
      });
    },
    onSuccess: async () => {
      setUnlinkTicket(null);
      setUnlinkReason("");
      setError("");
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const draftKnowledge = useMutation({
    mutationFn: (contentType: string) =>
      api.post(`/problems/${problemId}/knowledge/draft`, {
        content_type: contentType,
        version: problem.data?.version,
      }),
    onSuccess: async () => {
      setError("");
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  if (problem.isLoading) return <CircularProgress />;
  if (problem.isError || !problem.data)
    return (
      <Alert severity="error">
        {t("serviceManagement.problems.workspace.loadFailed")}
      </Alert>
    );
  const row = problem.data;
  const relationOptions =
    relationKind === "ticket"
      ? ticketOptions.data
      : relationKind === "change"
        ? changeOptions.data
        : relationKind === "knowledge"
          ? knowledgeOptions.data
          : rootCauseOptions.data;
  const submitEdit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    mutate.mutate({
      title: String(data.get("title")),
      description: String(data.get("description")),
      priority: String(data.get("priority")),
      business_impact: optional(data.get("business_impact")),
      symptoms: optional(data.get("symptoms")),
      workaround: optional(data.get("workaround")),
      known_error_summary: optional(data.get("known_error_summary")),
      root_cause_summary: optional(data.get("root_cause_summary")),
      permanent_fix_summary: optional(data.get("permanent_fix_summary")),
      target_resolution_date: optional(data.get("target_resolution_date")),
      version: row.version,
    });
  };
  return (
    <Stack gap={2}>
      <Paper sx={{ p: 3, borderLeft: 5, borderLeftColor: "warning.main" }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={1.5}
          alignItems={{ md: "center" }}
        >
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate("/problems")}
          >
            {t("serviceManagement.problems.title")}
          </Button>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="overline">
              {t("serviceManagement.problems.workspace.title")}
            </Typography>
            <Typography variant="h4">
              <TechnicalText>{row.problem_number}</TechnicalText> · {row.title}
            </Typography>
          </Box>
          <Chip label={label(row.status)} color="warning" variant="outlined" />
          <Chip label={label(row.priority)} />
          {hasPermission("problem.edit") && (
            <>
              <Button startIcon={<Edit />} onClick={() => setEditOpen(true)}>
                {t("serviceManagement.actions.edit")}
              </Button>
              {(transitions[row.status] ?? []).map((status) => (
                <Button
                  key={status}
                  variant="contained"
                  onClick={() => {
                    setTargetStatus(status);
                    setMoveOpen(true);
                  }}
                >
                  {label(status)}
                </Button>
              ))}
            </>
          )}
        </Stack>
      </Paper>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t("serviceManagement.problems.workspace.investigation")}
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" },
            gap: 3,
          }}
        >
          <Detail
            title={t("serviceManagement.fields.description")}
            value={row.description}
          />
          <Detail
            title={t("serviceManagement.fields.businessImpact")}
            value={row.business_impact}
          />
          <Detail
            title={t("serviceManagement.fields.symptoms")}
            value={row.symptoms}
          />
          <Detail
            title={t("serviceManagement.fields.workaround")}
            value={row.workaround}
          />
          <Detail
            title={t("serviceManagement.fields.knownError")}
            value={row.known_error_summary}
          />
          <Detail
            title={t("serviceManagement.fields.rootCause")}
            value={row.root_cause_summary}
          />
          <Detail
            title={t("serviceManagement.fields.permanentFix")}
            value={row.permanent_fix_summary}
          />
          <Detail
            title={t("serviceManagement.fields.targetResolution")}
            value={
              row.target_resolution_date
                ? new Date(row.target_resolution_date).toLocaleString(
                    i18n.language,
                  )
                : null
            }
          />
        </Box>
      </Paper>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "repeat(2, 1fr)" },
          gap: 2,
        }}
      >
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6">
            {t("serviceManagement.problems.workspace.comments")}
          </Typography>
          {comments.data?.map((item) => (
            <Box
              key={item.id}
              sx={{ py: 1, borderBottom: 1, borderColor: "divider" }}
            >
              <Typography sx={{ whiteSpace: "pre-wrap" }}>
                {item.body}
              </Typography>
              <Typography variant="caption">
                User {item.author_user_id} ·{" "}
                {new Date(item.created_at).toLocaleString()}
              </Typography>
            </Box>
          ))}
          {hasPermission("problem.edit") && (
            <Box
              component="form"
              sx={{ mt: 2 }}
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                const form = event.currentTarget;
                const body = String(
                  new FormData(form).get("body") ?? "",
                ).trim();
                if (body) {
                  addComment.mutate(body);
                  form.reset();
                }
              }}
            >
              <TextField
                name="body"
                label={t(
                  "serviceManagement.problems.workspace.addInternalComment",
                )}
                fullWidth
                multiline
                minRows={2}
                required
              />
              <Button type="submit" sx={{ mt: 1 }}>
                {t("serviceManagement.actions.addComment")}
              </Button>
            </Box>
          )}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6">
            {t("serviceManagement.problems.workspace.tasks")}
          </Typography>
          {tasks.data?.map((task) => (
            <Stack
              key={task.id}
              direction="row"
              gap={1}
              alignItems="center"
              sx={{ py: 1, borderBottom: 1, borderColor: "divider" }}
            >
              <Box sx={{ flexGrow: 1 }}>
                <Typography>{task.title}</Typography>
                <Typography
                  variant="caption"
                  color={
                    task.due_at &&
                    new Date(task.due_at) < new Date() &&
                    !["COMPLETED", "CANCELLED"].includes(task.status)
                      ? "error"
                      : "text.secondary"
                  }
                >
                  {label(task.status)}
                  {task.due_at
                    ? ` · due ${new Date(task.due_at).toLocaleString()}`
                    : ""}
                </Typography>
              </Box>
              {hasPermission("problem.edit") && task.status !== "COMPLETED" && (
                <Button
                  size="small"
                  onClick={() =>
                    updateTask.mutate({ task, status: "COMPLETED" })
                  }
                >
                  {t("serviceManagement.actions.complete")}
                </Button>
              )}
            </Stack>
          ))}
          {hasPermission("problem.edit") && (
            <Box
              component="form"
              sx={{ mt: 2 }}
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                addTask.mutate({
                  title: String(data.get("title")),
                  due_at: optional(data.get("due_at")),
                });
                form.reset();
              }}
            >
              <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                <TextField
                  name="title"
                  label={t("serviceManagement.problems.workspace.newTask")}
                  required
                  fullWidth
                />
                <TextField
                  name="due_at"
                  label={t("serviceManagement.fields.due")}
                  type="datetime-local"
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <Button type="submit">
                  {t("serviceManagement.actions.add")}
                </Button>
              </Stack>
            </Box>
          )}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" alignItems="center">
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("serviceManagement.problems.workspace.evidence")}
            </Typography>
            {hasPermission("problem.edit") && (
              <Button component="label" startIcon={<AttachFile />}>
                {t("serviceManagement.actions.upload")}
                <input
                  hidden
                  type="file"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) upload.mutate(file);
                  }}
                />
              </Button>
            )}
          </Stack>
          {attachments.data?.map((item) => (
            <Stack key={item.id} direction="row" gap={1} sx={{ py: 1 }}>
              <Typography sx={{ flexGrow: 1 }}>
                {item.original_filename}
              </Typography>
              <Chip size="small" label={label(item.scan_status)} />
              <Button
                size="small"
                onClick={async () => {
                  const response = await api.get(
                    `/problems/${problemId}/attachments/${item.id}/download`,
                    { responseType: "blob" },
                  );
                  const url = URL.createObjectURL(response.data);
                  window.open(url);
                  setTimeout(() => URL.revokeObjectURL(url), 10000);
                }}
              >
                {t("serviceManagement.actions.download")}
              </Button>
            </Stack>
          ))}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" alignItems="center">
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("serviceManagement.problems.workspace.relationships")}
            </Typography>
            {(hasPermission("problem.link_ticket") ||
              hasPermission("problem.edit") ||
              hasPermission("problem.identify_root_cause") ||
              hasPermission("problem.publish_known_error")) && (
              <Button
                onClick={() => {
                  setRelationKind(
                    hasPermission("problem.link_ticket")
                      ? "ticket"
                      : hasPermission("problem.identify_root_cause")
                        ? "root_cause"
                        : hasPermission("problem.edit")
                          ? "change"
                          : "knowledge",
                  );
                  setRelationOpen(true);
                }}
              >
                {t("serviceManagement.problems.workspace.addRelationship")}
              </Button>
            )}
          </Stack>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            {t("serviceManagement.problems.workspace.rootCauses")}
          </Typography>
          {rootCauses.data?.map((item) => (
            <Chip
              key={item.id}
              size="small"
              label={item.name}
              sx={{ mr: 0.5, mb: 0.5 }}
            />
          ))}
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            {t("serviceManagement.problems.tickets")}
          </Typography>
          {tickets.data?.map((item) => (
            <Stack key={item.id} direction="row" alignItems="center" gap={0.5}>
              <Button onClick={() => navigate(`/tickets/${item.ticket_id}`)}>
                <TechnicalText>{item.ticket_number}</TechnicalText>&nbsp;·{" "}
                {item.subject} ({label(item.link_type)})
              </Button>
              {hasPermission("problem.link_ticket") && item.ticket_id && (
                <Button
                  size="small"
                  color="error"
                  startIcon={<LinkOff />}
                  onClick={() => {
                    setUnlinkReason("");
                    setUnlinkTicket(item);
                  }}
                >
                  {t("serviceManagement.actions.remove")}
                </Button>
              )}
            </Stack>
          ))}
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            {t("serviceManagement.problems.workspace.changes")}
          </Typography>
          {changes.data?.map((item) => (
            <Button
              key={item.id}
              onClick={() =>
                navigate(`/tickets/${item.ticket_id}/change-request`)
              }
            >
              <TechnicalText>{item.ticket_number}</TechnicalText>&nbsp;·{" "}
              {item.subject}
            </Button>
          ))}
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            {t("serviceManagement.problems.workspace.knowledge")}
          </Typography>
          {knowledge.data?.map((item) => (
            <Typography key={item.article_id}>
              {item.title} · {label(item.link_type)}
            </Typography>
          ))}
          {hasPermission("problem.publish_known_error") && (
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              sx={{ mt: 1 }}
            >
              <Button
                size="small"
                disabled={!row.workaround || draftKnowledge.isPending}
                onClick={() => draftKnowledge.mutate("WORKAROUND")}
              >
                {t(
                  "serviceManagement.problems.workspace.createWorkaroundDraft",
                )}
              </Button>
              <Button
                size="small"
                disabled={
                  !row.permanent_fix_summary || draftKnowledge.isPending
                }
                onClick={() => draftKnowledge.mutate("PERMANENT_FIX")}
              >
                {t(
                  "serviceManagement.problems.workspace.createPermanentFixDraft",
                )}
              </Button>
            </Stack>
          )}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, gridColumn: { lg: "1 / -1" } }}>
          <Typography variant="h6">
            {t("serviceManagement.fields.lifecycleHistory")}
          </Typography>
          {history.data?.map((item) => (
            <Box
              key={item.id}
              sx={{ py: 1, borderBottom: 1, borderColor: "divider" }}
            >
              <Typography>
                {label(item.from_status)} → {label(item.to_status)}
              </Typography>
              <Typography variant="caption">
                {item.changed_by_name} ·{" "}
                {new Date(item.changed_at).toLocaleString()}
                {item.reason ? ` · ${item.reason}` : ""}
              </Typography>
            </Box>
          ))}
        </Paper>
      </Box>
      <Dialog
        open={Boolean(unlinkTicket)}
        onClose={() => setUnlinkTicket(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {t("serviceManagement.problems.workspace.removeTicketTitle")}
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mt: 1, mb: 1 }}>
            {t("serviceManagement.problems.workspace.removeTicketHelp", {
              ticket: unlinkTicket?.ticket_number,
            })}
          </Alert>
          <TextField
            autoFocus
            required
            fullWidth
            multiline
            rows={3}
            label={t("serviceManagement.fields.reason")}
            value={unlinkReason}
            onChange={(event) => setUnlinkReason(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUnlinkTicket(null)}>
            {t("serviceManagement.actions.cancel")}
          </Button>
          <Button
            color="error"
            variant="contained"
            disabled={unlinkReason.trim().length < 3 || unlinkRelationship.isPending}
            onClick={() => {
              if (unlinkTicket?.ticket_id) {
                unlinkRelationship.mutate({
                  ticketId: unlinkTicket.ticket_id,
                  reason: unlinkReason.trim(),
                });
              }
            }}
          >
            {t("serviceManagement.actions.remove")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={relationOpen}
        onClose={() => setRelationOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            relationship.mutate(new FormData(event.currentTarget));
          }}
        >
          <DialogTitle>
            {t("serviceManagement.problems.workspace.addRelationship")}
          </DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              <TextField
                autoFocus
                select
                label={t("serviceManagement.fields.relationshipArea")}
                value={relationKind}
                onChange={(event) => setRelationKind(event.target.value)}
              >
                {hasPermission("problem.link_ticket") && (
                  <MenuItem value="ticket">
                    {t("serviceManagement.relationships.affectedTicket")}
                  </MenuItem>
                )}
                {hasPermission("problem.identify_root_cause") && (
                  <MenuItem value="root_cause">
                    {t("serviceManagement.fields.rootCause")}
                  </MenuItem>
                )}
                {hasPermission("problem.edit") && (
                  <MenuItem value="change">
                    {t("serviceManagement.relationships.permanentFixChange")}
                  </MenuItem>
                )}
                {hasPermission("problem.publish_known_error") && (
                  <MenuItem value="knowledge">
                    {t("serviceManagement.relationships.knowledgeArticle")}
                  </MenuItem>
                )}
              </TextField>
              <TextField
                key={relationKind}
                select
                name="selected_id"
                label={
                  relationKind === "root_cause"
                    ? "Root cause"
                    : relationKind === "knowledge"
                      ? "Published article"
                      : relationKind === "change"
                        ? "Change Request"
                        : "Ticket"
                }
                required
                defaultValue={relationKind === "ticket" ? [] : ""}
                SelectProps={{ multiple: relationKind === "ticket" }}
              >
                {relationOptions?.map((item) => {
                  const value =
                    relationKind === "change" ? item.ticket_id : item.id;
                  return (
                    <MenuItem key={value} value={value}>
                      {item.ticket_number
                        ? `${item.ticket_number} · ${item.subject ?? item.title ?? ""}`
                        : (item.name ?? item.title)}
                    </MenuItem>
                  );
                })}
              </TextField>
              {relationKind === "ticket" && (
                <TextField
                  select
                  name="link_type"
                  label={t("serviceManagement.relationships.relationship")}
                  defaultValue="AFFECTED_INCIDENT"
                >
                  <MenuItem value="AFFECTED_INCIDENT">
                    {t("serviceManagement.relationships.affectedIncident")}
                  </MenuItem>
                  <MenuItem value="EVIDENCE">
                    {t("serviceManagement.problems.workspace.evidence")}
                  </MenuItem>
                  <MenuItem value="RELATED">
                    {t("serviceManagement.relationships.related")}
                  </MenuItem>
                </TextField>
              )}
              {relationKind === "change" && (
                <TextField
                  select
                  name="link_type"
                  label={t("serviceManagement.relationships.relationship")}
                  defaultValue="PERMANENT_FIX"
                >
                  <MenuItem value="PERMANENT_FIX">
                    {t("serviceManagement.fields.permanentFix")}
                  </MenuItem>
                  <MenuItem value="RELATED">
                    {t("serviceManagement.relationships.related")}
                  </MenuItem>
                </TextField>
              )}
              {relationKind === "knowledge" && (
                <TextField
                  select
                  name="link_type"
                  label={t("serviceManagement.relationships.useAs")}
                  defaultValue="RELATED"
                >
                  <MenuItem value="WORKAROUND">
                    {t("serviceManagement.fields.workaround")}
                  </MenuItem>
                  <MenuItem value="PERMANENT_FIX">
                    {t("serviceManagement.fields.permanentFix")}
                  </MenuItem>
                  <MenuItem value="RELATED">
                    {t("serviceManagement.relationships.related")}
                  </MenuItem>
                </TextField>
              )}
              {relationKind === "root_cause" && (
                <Alert severity="info">
                  {t("serviceManagement.problems.workspace.rootCauseHelp")}
                </Alert>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setRelationOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={relationship.isPending}
            >
              {t("serviceManagement.actions.add")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={editOpen}
        onClose={() => setEditOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <Box component="form" onSubmit={submitEdit}>
          <DialogTitle>
            {t("serviceManagement.problems.workspace.editProblem")}
          </DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              <TextField
                autoFocus
                name="title"
                label={t("serviceManagement.fields.title")}
                defaultValue={row.title}
                required
              />
              <TextField
                name="description"
                label={t("serviceManagement.fields.description")}
                defaultValue={row.description}
                required
                multiline
                minRows={3}
              />
              <TextField
                name="priority"
                label={t("serviceManagement.priority")}
                select
                defaultValue={row.priority}
              >
                {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
              {[
                ["business_impact", "Business impact"],
                ["symptoms", "Symptoms"],
                ["workaround", "Workaround"],
                ["known_error_summary", "Known error"],
                ["root_cause_summary", "Root cause"],
                ["permanent_fix_summary", "Permanent fix"],
              ].map(([name, title]) => (
                <TextField
                  key={name}
                  name={name}
                  label={title}
                  defaultValue={row[name as keyof Problem] ?? ""}
                  multiline
                  minRows={2}
                />
              ))}
              <TextField
                name="target_resolution_date"
                label={t("serviceManagement.fields.targetResolution")}
                type="datetime-local"
                defaultValue={dateInput(row.target_resolution_date)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("serviceManagement.actions.save")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            move.mutate({
              status: targetStatus,
              version: row.version,
              reason: optional(data.get("reason")),
              ...(targetStatus === "CLOSED"
                ? {
                    root_cause_summary: String(data.get("root_cause_summary") ?? "").trim(),
                    permanent_fix_summary: String(data.get("permanent_fix_summary") ?? "").trim(),
                  }
                : {}),
            });
          }}
        >
          <DialogTitle>
            {t("serviceManagement.actions.moveTo", {
              status: label(targetStatus),
            })}
          </DialogTitle>
          <DialogContent>
            {targetStatus === "CLOSED" && (
              <Stack gap={2} sx={{ mt: 1 }}>
                <Alert severity="info">
                  {t("serviceManagement.problems.workspace.closeRequirements")}
                </Alert>
                <TextField
                  autoFocus
                  required
                  name="root_cause_summary"
                  label={t("serviceManagement.fields.rootCause")}
                  defaultValue={row.root_cause_summary ?? ""}
                  fullWidth
                  multiline
                  minRows={3}
                />
                <TextField
                  required
                  name="permanent_fix_summary"
                  label={t("serviceManagement.fields.permanentFix")}
                  defaultValue={row.permanent_fix_summary ?? ""}
                  fullWidth
                  multiline
                  minRows={3}
                />
              </Stack>
            )}
            <TextField
              autoFocus={targetStatus !== "CLOSED"}
              name="reason"
              label={t("serviceManagement.fields.reason")}
              fullWidth
              multiline
              minRows={3}
              sx={{ mt: targetStatus === "CLOSED" ? 2 : 1 }}
              required={
                ["CANCELLED"].includes(targetStatus) ||
                ["CLOSED", "CANCELLED"].includes(row.status)
              }
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setMoveOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("serviceManagement.actions.confirm")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
