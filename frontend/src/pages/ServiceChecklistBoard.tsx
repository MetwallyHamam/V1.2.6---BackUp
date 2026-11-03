import { Add, PlayArrow, Save } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Option = { id: number; name?: string; full_name?: string };
type Template = {
  id: number;
  name: string;
  publication_status: string;
  schedule_mode: string;
};
type Item = {
  id: number;
  title: string;
  is_required: boolean;
  responsibility: string;
  evidence_required: boolean;
  evidence_reference: string | null;
  evidence_id: number | null;
  state: string;
  resource_type: string;
  resource_path: string | null;
  check_date: string | null;
};
type Occurrence = {
  id: number;
  occurrence_number: string;
  template_name: string;
  client_id: number;
  client_name: string;
  assigned_user_id: number | null;
  assigned_user_name: string | null;
  scheduled_at: string;
  due_at: string;
  recurrence_days: number | null;
  status: string;
  workflow_status: string;
  effective_lane: string;
  blocked_party: string | null;
  blocked_reason: string | null;
  version: number;
  required_complete: number;
  required_total: number;
  evidence_gaps: number;
  items: Item[] | null;
};
type Preview = {
  can_complete: boolean;
  eligible_item_ids: number[];
  blocking_items: string[];
  client_handoffs: string[];
  evidence_gaps: string[];
};

const lanes = [
  "SCHEDULED",
  "DUE_TODAY",
  "IN_PROGRESS",
  "BLOCKED",
  "OVERDUE",
  "COMPLETED",
] as const;
const laneLabel: Record<string, string> = {
  SCHEDULED: "Scheduled",
  DUE_TODAY: "Due Today",
  IN_PROGRESS: "In Progress",
  BLOCKED: "Blocked",
  OVERDUE: "Overdue",
  COMPLETED: "Completed",
};
export const occurrenceLane = (
  row: Pick<Occurrence, "effective_lane" | "status" | "due_at">,
  now = new Date(),
) => {
  if (lanes.includes(row.effective_lane as (typeof lanes)[number]))
    return row.effective_lane;
  if (row.status === "SCHEDULED") {
    const due = new Date(row.due_at);
    if (due.getTime() < now.getTime()) return "OVERDUE";
    if (due.toDateString() === now.toDateString()) return "DUE_TODAY";
  }
  if (row.status === "IN_PROGRESS" && new Date(row.due_at) < now)
    return "OVERDUE";
  return lanes.includes(row.status as (typeof lanes)[number])
    ? row.status
    : "SCHEDULED";
};
const rowLabels: Record<string, string> = {
  DATABASE: "Database Backup",
  SYSTEM_FOLDER: "Millensys Folder",
  SERVICE: "Millensys Services",
  REPORT: "System Reports",
  PROFILE: "System Profiles",
  CUSTOM: "Custom Check",
};

export function ServiceChecklistBoard({
  templates,
}: {
  templates: Template[];
}) {
  const { hasPermission } = useAuth();
  const cache = useQueryClient();
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<Occurrence | null>(null);
  const [blockTarget, setBlockTarget] = useState<Occurrence | null>(null);
  const [completeTarget, setCompleteTarget] = useState<Occurrence | null>(null);
  const [cancelTarget, setCancelTarget] = useState<Occurrence | null>(null);
  const [handoffItem, setHandoffItem] = useState<Item | null>(null);
  const [addRowOpen, setAddRowOpen] = useState(false);
  const [addRowType, setAddRowType] = useState("CUSTOM");
  const occurrences = useQuery({
    queryKey: ["service-checklist-occurrences"],
    queryFn: async () =>
      (await api.get<Occurrence[]>("/service-checklists/occurrences")).data,
  });
  const clients = useQuery({
    queryKey: ["clients", "checklists"],
    queryFn: async () =>
      (await api.get<Option[]>("/clients", { params: { limit: 200 } })).data,
    enabled: createOpen,
  });
  const users = useQuery({
    queryKey: ["service-checklist-assignees"],
    queryFn: async () =>
      (await api.get<Option[]>("/service-checklists/assignees")).data,
    enabled:
      createOpen ||
      (Boolean(selected) && hasPermission("service_checklist.reassign")),
  });
  const detail = useQuery({
    queryKey: ["service-checklist-occurrence", selected?.id],
    queryFn: async () =>
      (
        await api.get<Occurrence>(
          `/service-checklists/occurrences/${selected!.id}`,
        )
      ).data,
    enabled: Boolean(selected),
  });
  const preview = useQuery({
    queryKey: ["service-checklist-preview", completeTarget?.id],
    queryFn: async () =>
      (
        await api.get<Preview>(
          `/service-checklists/occurrences/${completeTarget!.id}/completion-preview`,
        )
      ).data,
    enabled: Boolean(completeTarget),
  });
  const refresh = async () => {
    await cache.invalidateQueries({
      queryKey: ["service-checklist-occurrence"],
    });
    await cache.invalidateQueries({
      queryKey: ["service-checklist-occurrences"],
    });
  };
  const action = useMutation({
    mutationFn: async ({
      url,
      body,
      method = "post",
    }: {
      url: string;
      body: object;
      method?: "post" | "put";
    }) => api[method](url, body),
    onSuccess: async () => {
      setBlockTarget(null);
      setCompleteTarget(null);
      setHandoffItem(null);
      setAddRowOpen(false);
      await refresh();
    },
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The checklist action could not be completed."),
      ),
  });
  const create = useMutation({
    mutationFn: async (body: object) =>
      api.post("/service-checklists/occurrences", body),
    onSuccess: async () => {
      setCreateOpen(false);
      await refresh();
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "The occurrence could not be created.")),
  });
  const submitHandoff = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!detail.data || !handoffItem) return;
    const values = new FormData(event.currentTarget);
    const file = values.get("evidence_file");
    if (!(file instanceof File) || !file.size) {
      setError("An evidence file is required.");
      return;
    }
    try {
      const upload = new FormData();
      upload.append("upload", file);
      const evidence = (
        await api.post<{ id: number }>(
          `/service-checklists/occurrences/${detail.data.id}/evidence`,
          upload,
        )
      ).data;
      action.mutate({
        url: `/service-checklists/occurrences/${detail.data.id}/items/${handoffItem.id}/client-handoff`,
        body: {
          version: detail.data.version,
          client_contact: values.get("contact"),
          handoff_note: values.get("note"),
          evidence_id: evidence.id,
          expected_at: values.get("expected_at") || null,
        },
      });
    } catch (cause) {
      setError(apiErrorMessage(cause, "The evidence could not be uploaded."));
    }
  };
  const openDetail = async (row: Occurrence) => {
    setSelected(row);
    await cache.invalidateQueries({
      queryKey: ["service-checklist-occurrence", row.id],
    });
  };
  const drop = (event: React.DragEvent, lane: string) => {
    event.preventDefault();
    const id = Number(event.dataTransfer.getData("text/plain"));
    const row = occurrences.data?.find((entry) => entry.id === id);
    if (!row) return;
    if (
      lane === "IN_PROGRESS" &&
      ["SCHEDULED", "DUE_TODAY", "BLOCKED", "OVERDUE"].includes(
        occurrenceLane(row),
      )
    )
      action.mutate({
        url: `/service-checklists/occurrences/${id}/start`,
        body: { version: row.version },
      });
    else if (lane === "BLOCKED" && row.status === "IN_PROGRESS")
      setBlockTarget(row);
    else if (
      lane === "COMPLETED" &&
      ["IN_PROGRESS", "OVERDUE", "BLOCKED"].includes(occurrenceLane(row))
    )
      setCompleteTarget(row);
  };
  return (
    <Stack spacing={2}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ sm: "center" }}
        gap={1}
      >
        <Box flex={1}>
          <Typography variant="h5" fontWeight={850}>
            Operational board
          </Typography>
          <Typography color="text.secondary">
            Drag cards to perform controlled workflow transitions.
          </Typography>
        </Box>
        {hasPermission("service_checklist.schedule.manage") && (
          <Button
            startIcon={<Add />}
            variant="outlined"
            onClick={() => setCreateOpen(true)}
          >
            Create occurrence
          </Button>
        )}
      </Stack>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      <Box>
        <Typography variant="h6" fontWeight={850} mb={1}>
          Engineer and client checklists
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridAutoFlow: "column",
            gridAutoColumns: { xs: "280px", md: "320px" },
            gap: 1.5,
            overflowX: "auto",
            pb: 1,
          }}
        >
          {Array.from(
            new Set(
              (occurrences.data ?? []).map(
                (row) => row.assigned_user_name || "Unassigned",
              ),
            ),
          ).map((engineer) => (
            <Paper key={engineer} variant="outlined" sx={{ p: 1.25 }}>
              <Typography fontWeight={900} mb={1}>
                {engineer}
              </Typography>
              <Stack spacing={1}>
                {(occurrences.data ?? [])
                  .filter(
                    (row) =>
                      (row.assigned_user_name || "Unassigned") === engineer &&
                      row.status !== "COMPLETED",
                  )
                  .map((row) => (
                    <Paper
                      key={row.id}
                      component="button"
                      type="button"
                      onClick={() => void openDetail(row)}
                      sx={{
                        p: 1.25,
                        textAlign: "left",
                        border: 0,
                        cursor: "pointer",
                        bgcolor: "action.hover",
                      }}
                    >
                      <Typography fontWeight={800}>
                        {row.client_name}
                      </Typography>
                      <Typography variant="caption">
                        {row.template_name}
                      </Typography>
                      <Stack
                        direction="row"
                        justifyContent="space-between"
                        mt={0.5}
                      >
                        <Chip
                          size="small"
                          label={row.workflow_status.replaceAll("_", " ")}
                          color={
                            row.workflow_status === "NEED_ATTENTION"
                              ? "warning"
                              : row.workflow_status === "CLIENT_RESPONSIBILITY"
                                ? "info"
                                : "default"
                          }
                        />
                        <Typography variant="caption">
                          {row.required_complete}/{row.required_total}
                        </Typography>
                      </Stack>
                    </Paper>
                  ))}
              </Stack>
            </Paper>
          ))}
        </Box>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "repeat(6,minmax(270px,1fr))",
            lg: "repeat(6,minmax(220px,1fr))",
          },
          gap: 1.5,
          overflowX: "auto",
          pb: 1,
        }}
      >
        {lanes.map((lane) => (
          <Paper
            key={lane}
            variant="outlined"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => drop(event, lane)}
            sx={{
              p: 1.25,
              minHeight: 310,
              bgcolor: "action.hover",
              borderTop: 4,
              borderTopColor:
                lane === "OVERDUE"
                  ? "error.main"
                  : lane === "BLOCKED" || lane === "DUE_TODAY"
                    ? "warning.main"
                    : lane === "COMPLETED"
                      ? "success.main"
                      : "primary.main",
            }}
          >
            <Typography fontWeight={850} mb={1}>
              {laneLabel[lane]}{" "}
              <Chip
                size="small"
                label={
                  occurrences.data?.filter((row) => occurrenceLane(row) === lane)
                    .length ?? 0
                }
              />
            </Typography>
            <Stack spacing={1}>
              {occurrences.data
                ?.filter((row) => occurrenceLane(row) === lane)
                .map((row) => (
                  <Paper
                    key={row.id}
                    draggable
                    onDragStart={(event) =>
                      event.dataTransfer.setData("text/plain", String(row.id))
                    }
                    onClick={() => void openDetail(row)}
                    sx={{
                      p: 1.5,
                      cursor: "grab",
                      boxShadow: 2,
                      "&:hover": {
                        boxShadow: 5,
                        transform: "translateY(-1px)",
                      },
                      transition: "120ms ease",
                    }}
                  >
                    <Stack direction="row" justifyContent="space-between">
                      <Typography fontWeight={900} color="primary.main">
                        {row.occurrence_number}
                      </Typography>
                      {row.evidence_gaps > 0 && (
                        <Chip
                          size="small"
                          color="warning"
                          label={`${row.evidence_gaps} evidence`}
                        />
                      )}
                    </Stack>
                    <Typography fontWeight={750}>{row.client_name}</Typography>
                    <Typography variant="body2">{row.template_name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {row.assigned_user_name || "Unassigned"} · Due{" "}
                      {new Date(row.due_at).toLocaleString()}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={
                        row.required_total
                          ? (row.required_complete / row.required_total) * 100
                          : 100
                      }
                      sx={{ mt: 1 }}
                    />
                    <Typography variant="caption">
                      {row.required_complete} / {row.required_total} required
                      tasks
                    </Typography>
                  </Paper>
                ))}
            </Stack>
          </Paper>
        ))}
      </Box>
      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            create.mutate({
              template_id: Number(values.get("template_id")),
              client_id: Number(values.get("client_id")),
              assigned_user_id: values.get("assigned_user_id")
                ? Number(values.get("assigned_user_id"))
                : null,
              scheduled_at: values.get("scheduled_at"),
              due_at: values.get("due_at"),
              recurrence_days: values.get("recurrence_days")
                ? Number(values.get("recurrence_days"))
                : null,
            });
          }}
        >
          <DialogTitle>Create checklist occurrence</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              <TextField
                select
                required
                name="template_id"
                label="Published template"
              >
                {templates
                  .filter((row) => row.publication_status === "PUBLISHED")
                  .map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {row.name}
                    </MenuItem>
                  ))}
              </TextField>
              <TextField select required name="client_id" label="Client">
                {clients.data?.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="assigned_user_id"
                label="Assigned engineer"
              >
                <MenuItem value="">Unassigned</MenuItem>
                {users.data?.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.full_name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                required
                name="scheduled_at"
                label="Scheduled"
                type="datetime-local"
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                required
                name="due_at"
                label="Due"
                type="datetime-local"
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                name="recurrence_days"
                label="Repeat every (days)"
                type="number"
                inputProps={{ min: 1, max: 366 }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Create
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {detail.data?.occurrence_number} · {detail.data?.client_name}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={1.25}>
            {detail.data?.blocked_reason && (
              <Alert severity="warning">
                {detail.data.blocked_party}: {detail.data.blocked_reason}
              </Alert>
            )}
            {detail.data?.items?.map((item) => (
              <Paper
                key={`${item.id}-${detail.data?.version}`}
                component="form"
                variant="outlined"
                sx={{ p: 1.5 }}
                onSubmit={(event: FormEvent<HTMLFormElement>) => {
                  event.preventDefault();
                  const values = new FormData(event.currentTarget);
                  action.mutate({
                    url: `/service-checklists/occurrences/${detail.data!.id}/items/${item.id}`,
                    method: "put",
                    body: {
                      version: detail.data!.version,
                      resource_type: values.get("resource_type"),
                      title: values.get("title"),
                      resource_path: values.get("resource_path"),
                      check_date: values.get("check_date"),
                      status: values.get("status"),
                    },
                  });
                }}
              >
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  gap={1}
                  alignItems={{ sm: "center" }}
                >
                  <TextField
                    select
                    size="small"
                    name="resource_type"
                    label="Type"
                    defaultValue={item.resource_type || "CUSTOM"}
                    onChange={(event) => {
                      const input =
                        event.currentTarget.form?.elements.namedItem("title");
                      if (
                        input instanceof HTMLInputElement &&
                        (!input.value ||
                          Object.values(rowLabels).includes(input.value))
                      )
                        input.value =
                          rowLabels[event.target.value] ?? rowLabels.CUSTOM;
                    }}
                    sx={{ minWidth: 145 }}
                  >
                    {Object.entries(rowLabels).map(([value, label]) => (
                      <MenuItem key={value} value={value}>
                        {label}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    size="small"
                    name="title"
                    label="Label"
                    defaultValue={item.title}
                    sx={{ flex: 1 }}
                  />
                  <TextField
                    size="small"
                    name="resource_path"
                    label="Path or URL"
                    defaultValue={item.resource_path ?? ""}
                    sx={{ flex: 1.5 }}
                  />
                  <TextField
                    size="small"
                    name="check_date"
                    label="Date"
                    type="date"
                    defaultValue={(
                      item.check_date ?? new Date().toISOString()
                    ).slice(0, 10)}
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <TextField
                    select
                    size="small"
                    name="status"
                    label="Status"
                    defaultValue={
                      item.state === "COMPLETED"
                        ? "COMPLETE"
                        : item.state === "CLIENT_RESPONSIBLE"
                          ? "CLIENT_RESPONSIBILITY"
                          : item.state
                    }
                    sx={{ minWidth: 170 }}
                  >
                    {[
                      "PENDING",
                      "COMPLETE",
                      "NEED_ATTENTION",
                      "CLIENT_RESPONSIBILITY",
                    ].map((value) => (
                      <MenuItem key={value} value={value}>
                        {value.replaceAll("_", " ")}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Button type="submit" startIcon={<Save />}>
                    Save
                  </Button>
                </Stack>
              </Paper>
            ))}
            {detail.data && detail.data.status !== "COMPLETED" && (
              <Button
                startIcon={<Add />}
                onClick={() => {
                  setAddRowType("CUSTOM");
                  setAddRowOpen(true);
                }}
              >
                Add checklist row
              </Button>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          {hasPermission("service_checklist.reassign") && detail.data && (
            <TextField
              select
              size="small"
              label="Reassign"
              value={detail.data.assigned_user_id ?? ""}
              onChange={(event) =>
                action.mutate({
                  url: `/service-checklists/occurrences/${detail.data!.id}/reassign`,
                  body: {
                    version: detail.data!.version,
                    assigned_user_id: Number(event.target.value),
                    reason: "Reassigned from operational board",
                  },
                })
              }
              sx={{ minWidth: 180 }}
            >
              {users.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.full_name}
                </MenuItem>
              ))}
            </TextField>
          )}
          {hasPermission("service_checklist.schedule.manage") &&
            detail.data?.status !== "COMPLETED" && (
              <Button
                color="error"
                onClick={() => setCancelTarget(detail.data!)}
              >
                Cancel checklist
              </Button>
            )}
          <Button onClick={() => setSelected(null)}>Close</Button>
          {detail.data?.status === "SCHEDULED" && (
            <Button
              startIcon={<PlayArrow />}
              onClick={() =>
                action.mutate({
                  url: `/service-checklists/occurrences/${detail.data!.id}/start`,
                  body: { version: detail.data!.version },
                })
              }
            >
              Start
            </Button>
          )}
        </DialogActions>
      </Dialog>
      <Dialog
        open={addRowOpen}
        onClose={() => setAddRowOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            if (!detail.data) return;
            const values = new FormData(event.currentTarget);
            action.mutate({
              url: `/service-checklists/occurrences/${detail.data.id}/items`,
              body: {
                resource_type: addRowType,
                title: String(values.get("title") ?? "").trim(),
                resource_path: String(values.get("resource_path") ?? "").trim() || null,
                check_date: values.get("check_date") || null,
              },
            });
          }}
        >
          <DialogTitle>Add checklist row</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              <Alert severity="info">
                This adds one task to the current event only. Edit the checklist template
                when the task should appear in every future event.
              </Alert>
              <TextField
                select
                required
                label="Type"
                value={addRowType}
                onChange={(event) => setAddRowType(event.target.value)}
              >
                {Object.entries(rowLabels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                required
                name="title"
                label="Task name"
                defaultValue={rowLabels.CUSTOM}
                inputProps={{ minLength: 2, maxLength: 200 }}
              />
              <TextField name="resource_path" label="Path or URL" />
              <TextField
                name="check_date"
                label="Check date"
                type="date"
                defaultValue={new Date().toISOString().slice(0, 10)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAddRowOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={action.isPending}>
              Add row
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(blockTarget)}
        onClose={() => setBlockTarget(null)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            action.mutate({
              url: `/service-checklists/occurrences/${blockTarget!.id}/block`,
              body: {
                version: blockTarget!.version,
                blocked_party: values.get("party"),
                reason: values.get("reason"),
                follow_up_at: values.get("follow_up_at"),
              },
            });
          }}
        >
          <DialogTitle>Block checklist</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              <TextField
                select
                required
                name="party"
                label="Waiting for"
                defaultValue="INTERNAL"
              >
                <MenuItem value="INTERNAL">Internal dependency</MenuItem>
                <MenuItem value="CLIENT">Client action</MenuItem>
              </TextField>
              <TextField
                required
                name="reason"
                label="Reason"
                multiline
                minRows={3}
              />
              <TextField
                required
                name="follow_up_at"
                label="Expected follow-up"
                type="datetime-local"
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setBlockTarget(null)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Block
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(handoffItem)}
        onClose={() => setHandoffItem(null)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitHandoff}>
          <DialogTitle>Transfer task to Client Responsibility</DialogTitle>
          <DialogContent>
            <Alert severity="info">
              This records a documented handoff; it does not mark the task
              completed.
            </Alert>
            <Stack spacing={2} mt={2}>
              <TextField
                required
                name="contact"
                label="Client contact/person"
              />
              <TextField
                required
                name="note"
                label="Required action and engineer note"
                multiline
                minRows={3}
              />
              <Button component="label" variant="outlined">
                Attach email, screenshot, PDF, or document
                <input
                  hidden
                  required
                  name="evidence_file"
                  type="file"
                  accept=".eml,.msg,.png,.jpg,.jpeg,.pdf,.docx"
                />
              </Button>
              <TextField
                name="expected_at"
                label="Expected client completion"
                type="datetime-local"
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setHandoffItem(null)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Upload evidence and record handoff
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(completeTarget)}
        onClose={() => setCompleteTarget(null)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            action.mutate({
              url: `/service-checklists/occurrences/${completeTarget!.id}/complete`,
              body: {
                version: completeTarget!.version,
                service_provided: values.get("service"),
                completion_summary: values.get("summary"),
                complete_eligible_remaining: true,
              },
            });
          }}
        >
          <DialogTitle>Complete checklist</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              {preview.data?.blocking_items.map((value) => (
                <Alert key={value} severity="error">
                  Blocking: {value}
                </Alert>
              ))}
              {preview.data?.evidence_gaps.map((value) => (
                <Alert key={value} severity="warning">
                  Missing evidence: {value}
                </Alert>
              ))}
              {Boolean(preview.data?.eligible_item_ids.length) && (
                <Alert severity="info">
                  {preview.data!.eligible_item_ids.length} eligible confirmation
                  tasks will be completed.
                </Alert>
              )}
              <TextField
                required
                name="service"
                label="Service provided"
                multiline
                minRows={2}
              />
              <TextField
                required
                name="summary"
                label="Client-visible completion summary"
                multiline
                minRows={3}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCompleteTarget(null)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!preview.data?.can_complete}
            >
              Complete and schedule next
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(cancelTarget)}
        onClose={() => setCancelTarget(null)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            action.mutate({
              url: `/service-checklists/occurrences/${cancelTarget!.id}/cancel`,
              body: {
                version: cancelTarget!.version,
                reason: values.get("reason"),
              },
            });
            setCancelTarget(null);
          }}
        >
          <DialogTitle>Cancel checklist</DialogTitle>
          <DialogContent>
            <TextField
              required
              fullWidth
              margin="normal"
              name="reason"
              label="Cancellation reason"
              multiline
              minRows={3}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCancelTarget(null)}>
              Keep checklist
            </Button>
            <Button color="error" type="submit">
              Cancel checklist
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
