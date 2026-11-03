import {
  Add,
  Download,
  Pause,
  PlayArrow,
  SwapHoriz,
  Upload,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChangeEvent, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Option = {
  id: number;
  name?: string;
  full_name?: string;
  username?: string;
};
type ClientPage = {
  items: Option[];
  total: number;
  limit: number;
  offset: number;
};
type Template = {
  id: number;
  code: string;
  name: string;
  is_default?: boolean;
};
type Schedule = {
  id: number;
  name: string;
  template_id: number;
  client_id: number;
  assigned_user_id: number | null;
  starts_at: string;
  next_generate_at: string;
  interval_days: number;
  duration_minutes: number;
  is_paused: boolean;
  version: number;
  last_completed_at?: string | null;
  last_required_complete?: number;
  last_required_total?: number;
};
type Occurrence = {
  id: number;
  occurrence_number: string;
  template_name: string;
  client_id: number;
  client_name: string;
  assigned_user_id: number | null;
  assigned_user_name: string | null;
  due_at: string;
  status: string;
  workflow_status: string;
  required_complete: number;
  required_total: number;
  evidence_gaps: number;
  items: { state: string; responsibility: string }[] | null;
};

const frequency = (days: number) =>
  days === 1
    ? "Daily"
    : days === 7
      ? "Weekly"
      : days === 30
        ? "Monthly"
        : `Every ${days} days`;

export function ServiceChecklistAssignments({
  board = false,
  templates,
}: {
  board?: boolean;
  templates: Template[];
}) {
  const { hasPermission } = useAuth();
  const cache = useQueryClient();
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [assignOpen, setAssignOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [bulkClientIds, setBulkClientIds] = useState<number[]>([]);
  const [clientSearch, setClientSearch] = useState("");
  const schedules = useQuery({
    queryKey: ["service-checklist-schedules"],
    queryFn: async () =>
      (await api.get<Schedule[]>("/service-checklists/schedules")).data,
  });
  const occurrences = useQuery({
    queryKey: ["service-checklist-occurrences"],
    queryFn: async () =>
      (await api.get<Occurrence[]>("/service-checklists/occurrences")).data,
    enabled: board,
  });
  const clients = useQuery({
    queryKey: ["clients", "checklist-assignment"],
    queryFn: async () => {
      const items: Option[] = [];
      const limit = 200;
      let offset = 0;
      while (true) {
        const page = (
          await api.get<ClientPage>("/clients/search-page", {
            params: { active_only: false, limit, offset },
          })
        ).data;
        items.push(...page.items);
        offset += page.items.length;
        if (!page.items.length || offset >= page.total) break;
      }
      return items;
    },
  });
  const engineers = useQuery({
    queryKey: ["service-checklist-assignees"],
    queryFn: async () =>
      (await api.get<Option[]>("/service-checklists/assignees")).data,
  });
  const clientName = (id: number) =>
    clients.data?.find((row) => row.id === id)?.name ?? `Client #${id}`;
  const engineerName = (id: number | null) =>
    engineers.data?.find((row) => row.id === id)?.full_name ?? "Unassigned";
  const templateName = (id: number) =>
    templates.find((row) => row.id === id)?.name ?? `Template #${id}`;
  const assignedClientIds = new Set(
    (schedules.data ?? []).map((row) => row.client_id),
  );
  const unassignedClients = (clients.data ?? []).filter(
    (row) => !assignedClientIds.has(row.id),
  );
  const visibleAssignmentClients = (clients.data ?? []).filter((row) =>
    (row.name ?? "")
      .toLocaleLowerCase()
      .includes(clientSearch.trim().toLocaleLowerCase()),
  );
  const defaultTemplate = templates.find((row) => row.is_default);
  const occurrenceGroups = (() => {
    const result = new Map<string, Occurrence[]>();
    for (const row of occurrences.data ?? []) {
      const key = row.assigned_user_name || engineerName(row.assigned_user_id);
      result.set(key, [...(result.get(key) ?? []), row]);
    }
    return result;
  })();
  const reassign = useMutation({
    mutationFn: ({ row, userId }: { row: Schedule; userId: number }) =>
      api.post(`/service-checklists/schedules/${row.id}/reassign`, {
        version: row.version,
        assigned_user_id: userId,
        reason: "Individual plan transfer",
      }),
    onSuccess: () =>
      cache.invalidateQueries({ queryKey: ["service-checklist-schedules"] }),
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The client assignment could not be changed."),
      ),
  });
  const bulkAssign = useMutation({
    mutationFn: (body: object) =>
      api.post("/service-checklists/schedules/bulk-assign", body),
    onSuccess: async () => {
      setAssignOpen(false);
      setSelected([]);
      await cache.invalidateQueries({
        queryKey: ["service-checklist-schedules"],
      });
      await cache.invalidateQueries({
        queryKey: ["service-checklist-occurrences"],
      });
    },
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The bulk assignment could not be completed."),
      ),
  });
  const bulkTransfer = useMutation({
    mutationFn: (body: object) =>
      api.post("/service-checklists/schedules/bulk-transfer", body),
    onSuccess: async () => {
      setTransferOpen(false);
      setSelected([]);
      await cache.invalidateQueries({
        queryKey: ["service-checklist-schedules"],
      });
      await cache.invalidateQueries({
        queryKey: ["service-checklist-occurrences"],
      });
    },
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The selected plans could not be transferred."),
      ),
  });
  const scheduleState = useMutation({
    mutationFn: (row: Schedule) =>
      api.post(`/service-checklists/schedules/${row.id}/state`, {
        version: row.version,
        paused: !row.is_paused,
      }),
    onSuccess: () =>
      cache.invalidateQueries({ queryKey: ["service-checklist-schedules"] }),
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The checklist schedule could not be changed."),
      ),
  });
  const download = async () => {
    const response = await api.get(
      "/service-checklists/assignments/import-template",
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "service-checklist-assignments.xlsx";
    link.click();
    URL.revokeObjectURL(url);
  };
  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("upload", file);
    try {
      const result = (
        await api.post<{ created: number; failed: number }>(
          "/service-checklists/assignments/import",
          body,
        )
      ).data;
      setError(
        result.failed
          ? `Imported ${result.created}; ${result.failed} rows need correction.`
          : `Imported ${result.created} assignments.`,
      );
      await cache.invalidateQueries({
        queryKey: ["service-checklist-schedules"],
      });
    } catch (cause) {
      setError(
        apiErrorMessage(
          cause,
          "The assignment workbook could not be imported.",
        ),
      );
    }
    event.target.value = "";
  };
  if (board)
    return (
      <Stack spacing={2}>
        {error && (
          <Alert severity="info" onClose={() => setError("")}>
            {error}
          </Alert>
        )}
        <Stack direction="row" gap={1} flexWrap="wrap">
          <Alert severity="success">
            Completed:{" "}
            {
              (occurrences.data ?? []).filter(
                (row) => row.status === "COMPLETED",
              ).length
            }
          </Alert>
          <Alert severity="warning">
            Open:{" "}
            {
              (occurrences.data ?? []).filter(
                (row) => !["COMPLETED", "CANCELLED"].includes(row.status),
              ).length
            }
          </Alert>
          <Alert severity="info">
            Client responsibility:{" "}
            {
              (occurrences.data ?? []).filter(
                (row) => row.workflow_status === "CLIENT_RESPONSIBILITY",
              ).length
            }
          </Alert>
        </Stack>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "repeat(3,minmax(280px,1fr))",
            },
            gap: 2,
          }}
        >
          {[...occurrenceGroups.entries()].map(([engineer, rows]) => (
            <Paper key={engineer} variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" fontWeight={850}>
                {engineer}
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={1.5}>
                {rows.length} checklists
              </Typography>
              <Stack spacing={1}>
                {rows.map((row) => (
                  <Paper key={row.id} sx={{ p: 1.25, bgcolor: "action.hover" }}>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      gap={1}
                    >
                      <Box>
                        <Typography fontWeight={750}>
                          {row.client_name}
                        </Typography>
                        <Typography variant="body2">
                          {row.template_name}
                        </Typography>
                      </Box>
                      <Typography variant="caption" fontWeight={700}>
                        {row.workflow_status.replaceAll("_", " ")}
                      </Typography>
                    </Stack>
                    <Typography variant="caption" color="text.secondary">
                      {row.required_complete}/{row.required_total} complete ·
                      Due {new Date(row.due_at).toLocaleString()}
                      {row.evidence_gaps
                        ? ` · ${row.evidence_gaps} evidence gaps`
                        : ""}
                    </Typography>
                  </Paper>
                ))}
              </Stack>
            </Paper>
          ))}
        </Box>
      </Stack>
    );
  if (!hasPermission("service_checklist.schedule.manage"))
    return (
      <Alert severity="info">
        Assignment maintenance is available to checklist managers. Use Engineer
        Board to monitor your permitted clients and checklists.
      </Alert>
    );
  return (
    <Stack spacing={2}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Box flex={1}>
          <Typography variant="h5" fontWeight={850}>
            Client assignments
          </Typography>
          <Typography color="text.secondary">
            Link every client to an engineer, checklist template, and
            recurrence.
          </Typography>
        </Box>
        <Button
          startIcon={<Add />}
          variant="contained"
          onClick={() => setAssignOpen(true)}
        >
          Bulk assign clients
        </Button>
        <Button
          startIcon={<SwapHoriz />}
          disabled={!selected.length}
          onClick={() => setTransferOpen(true)}
        >
          Transfer selected
        </Button>
        <Button startIcon={<Download />} onClick={() => void download()}>
          Export Excel
        </Button>
        <Button component="label" startIcon={<Upload />}>
          Import Excel
          <input
            hidden
            type="file"
            accept=".xlsx"
            onChange={(event) => void upload(event)}
          />
        </Button>
      </Stack>
      {error && (
        <Alert severity="info" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={2}
          alignItems={{ md: "center" }}
        >
          <Box flex={1}>
            <Typography variant="h6" fontWeight={850}>
              Not assigned clients
            </Typography>
            <Typography color="text.secondary">
              {unassignedClients.length} clients do not have a checklist plan.
            </Typography>
          </Box>
          <Button
            variant="outlined"
            disabled={!unassignedClients.length}
            onClick={() => {
              setBulkClientIds(unassignedClients.map((row) => row.id));
              setAssignOpen(true);
            }}
          >
            Select all and assign
          </Button>
        </Stack>
      </Paper>
      <FormControlLabel
        control={
          <Checkbox
            checked={
              Boolean(schedules.data?.length) &&
              selected.length === schedules.data?.length
            }
            indeterminate={
              selected.length > 0 &&
              selected.length < (schedules.data?.length ?? 0)
            }
            onChange={(event) =>
              setSelected(
                event.target.checked
                  ? (schedules.data ?? []).map((row) => row.id)
                  : [],
              )
            }
          />
        }
        label={`Select all plans (${selected.length} selected)`}
      />
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>Client</TableCell>
              <TableCell>Dedicated engineer</TableCell>
              <TableCell>Template / frequency</TableCell>
              <TableCell>Last completed</TableCell>
              <TableCell>Next checklist</TableCell>
              <TableCell align="right">Completed tasks</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {schedules.data?.map((row) => (
              <TableRow hover key={row.id}>
                <TableCell padding="checkbox">
                  <Checkbox
                    checked={selected.includes(row.id)}
                    onChange={(event) =>
                      setSelected((current) =>
                        event.target.checked
                          ? [...current, row.id]
                          : current.filter((id) => id !== row.id),
                      )
                    }
                    inputProps={{
                      "aria-label": `Select ${clientName(row.client_id)}`,
                    }}
                  />
                </TableCell>
                <TableCell>
                  <Typography fontWeight={800}>
                    {clientName(row.client_id)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <TextField
                    select
                    size="small"
                    variant="standard"
                    value={row.assigned_user_id ?? ""}
                    sx={{ minWidth: 190 }}
                    onChange={(event) =>
                      reassign.mutate({
                        row,
                        userId: Number(event.target.value),
                      })
                    }
                  >
                    {engineers.data?.map((engineer) => (
                      <MenuItem key={engineer.id} value={engineer.id}>
                        {engineer.full_name}
                      </MenuItem>
                    ))}
                  </TextField>
                </TableCell>
                <TableCell>
                  {templateName(row.template_id)} ·{" "}
                  {frequency(row.interval_days)}
                  <Button
                    size="small"
                    sx={{ ml: 1, minWidth: 0, px: 0.75 }}
                    startIcon={row.is_paused ? <PlayArrow /> : <Pause />}
                    onClick={() => scheduleState.mutate(row)}
                  >
                    {row.is_paused ? "Enable" : "Disable"}
                  </Button>
                </TableCell>
                <TableCell>
                  {row.last_completed_at
                    ? new Date(row.last_completed_at).toLocaleString()
                    : "Never"}
                </TableCell>
                <TableCell>
                  {new Date(row.next_generate_at).toLocaleString()}
                </TableCell>
                <TableCell align="right">
                  {row.last_required_complete ?? 0}/
                  {row.last_required_total ?? 0}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Dialog
        open={assignOpen}
        onClose={() => setAssignOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            bulkAssign.mutate({
              client_ids: bulkClientIds,
              assigned_user_id: Number(values.get("assigned_user_id")),
              template_id: Number(values.get("template_id")),
              starts_at: values.get("starts_at"),
              interval_days: Number(values.get("interval_days")),
              duration_minutes: Number(values.get("duration_minutes")),
            });
          }}
        >
          <DialogTitle>Bulk assign client plans</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              <TextField
                label="Search clients"
                value={clientSearch}
                onChange={(event) => setClientSearch(event.target.value)}
              />
              <Stack direction="row" gap={1} alignItems="center">
                <Button
                  size="small"
                  onClick={() =>
                    setBulkClientIds((current) => [
                      ...new Set([
                        ...current,
                        ...visibleAssignmentClients.map((row) => row.id),
                      ]),
                    ])
                  }
                >
                  Select all matching
                </Button>
                <Button size="small" onClick={() => setBulkClientIds([])}>
                  Clear all
                </Button>
                <Typography variant="caption">
                  {bulkClientIds.length} selected
                </Typography>
              </Stack>
              <Paper
                variant="outlined"
                sx={{ maxHeight: 260, overflowY: "auto", p: 0.5 }}
              >
                {visibleAssignmentClients.map((client) => (
                  <MenuItem
                    key={client.id}
                    onClick={() =>
                      setBulkClientIds((current) =>
                        current.includes(client.id)
                          ? current.filter((id) => id !== client.id)
                          : [...current, client.id],
                      )
                    }
                  >
                    <Checkbox checked={bulkClientIds.includes(client.id)} />
                    {client.name}
                  </MenuItem>
                ))}
              </Paper>
              <TextField
                select
                required
                name="assigned_user_id"
                label="Engineer"
              >
                <MenuItem value="">Select engineer</MenuItem>
                {engineers.data?.map((engineer) => (
                  <MenuItem key={engineer.id} value={engineer.id}>
                    {engineer.full_name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                required
                name="template_id"
                label="Published template"
                defaultValue={defaultTemplate?.id ?? ""}
              >
                <MenuItem value="">Select template</MenuItem>
                {templates.map((template) => (
                  <MenuItem key={template.id} value={template.id}>
                    {template.name}
                    {template.is_default ? " (Default)" : ""}
                  </MenuItem>
                ))}
              </TextField>
              <input type="hidden" name="interval_days" value="7" />
              <Alert severity="info">
                A weekly schedule is created automatically. The assigned
                engineer can disable or re-enable it from the assignment row.
              </Alert>
              <TextField
                required
                type="datetime-local"
                name="starts_at"
                label="First due date"
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                required
                type="number"
                name="duration_minutes"
                label="Allowed completion minutes"
                defaultValue={120}
                inputProps={{ min: 15 }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAssignOpen(false)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={bulkAssign.isPending || !bulkClientIds.length}
            >
              Assign clients
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={transferOpen}
        onClose={() => setTransferOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            bulkTransfer.mutate({
              items: (schedules.data ?? [])
                .filter((row) => selected.includes(row.id))
                .map((row) => ({ schedule_id: row.id, version: row.version })),
              assigned_user_id: Number(values.get("assigned_user_id")),
              reason: values.get("reason"),
            });
          }}
        >
          <DialogTitle>Transfer {selected.length} client plans</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              <Alert severity="info">
                Future and unfinished checklists move to the new engineer.
                Completed history remains unchanged.
              </Alert>
              <TextField
                select
                required
                name="assigned_user_id"
                label="New engineer"
              >
                <MenuItem value="">Select engineer</MenuItem>
                {engineers.data?.map((engineer) => (
                  <MenuItem key={engineer.id} value={engineer.id}>
                    {engineer.full_name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                required
                multiline
                minRows={2}
                name="reason"
                label="Transfer reason"
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTransferOpen(false)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={bulkTransfer.isPending}
            >
              Transfer plans
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
