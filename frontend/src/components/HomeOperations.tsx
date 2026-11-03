import {
  Business,
  Check,
  Close,
  DirectionsCar,
  Groups,
  PlayArrow,
  TaskAlt,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { InternalOperationsPage } from "../pages/InternalOperationsPage";
import { ShiftPaintMode } from "../pages/ShiftPaintMode";
import { serverDateInput } from "../utils/serverTime";

type CalendarItem = {
  id: number;
  title?: string;
  name?: string;
  operation_type?: string;
  status: string;
  starts_at: string;
  ends_at: string;
  client_name?: string;
  client_code?: string;
  employee_name?: string;
  presence_status?: "ACTIVE" | "IDLE" | "OFFLINE" | null;
  last_seen_at?: string | null;
  assignees?: Array<{ id: number; full_name: string }>;
};
type ClientPage = {
  items: Array<{ id: number; code: string; name: string }>;
  total: number;
};
type Approval = {
  id: number;
  ticket_id?: number;
  requested_action: string;
  justification?: string;
  status: string;
  requester_name?: string;
  version: number;
};
type Operation = {
  id: number;
  title: string;
  operation_type: string;
  status: string;
  starts_at: string;
  ends_at: string;
  client_name?: string;
  assignees: Array<{ id: number; full_name: string }>;
  version: number;
};

const isoDate = (date: Date) => serverDateInput(date);
const calendarDate = (value: string) => new Date(`${value}T12:00:00Z`);
const rangeFor = (mode: string, referenceToday = serverDateInput()) => {
  const now = calendarDate(referenceToday),
    start = new Date(now),
    end = new Date(now);
  if (mode === "week") {
    start.setUTCDate(now.getUTCDate() - now.getUTCDay());
    end.setUTCDate(start.getUTCDate() + 6);
  } else if (mode === "month") {
    start.setUTCDate(1);
    end.setUTCMonth(now.getUTCMonth() + 1, 0);
  }
  return { from: isoDate(start), to: isoDate(end) };
};
const statusColor = (
  status: string,
): "default" | "warning" | "success" | "error" | "info" =>
  status === "PENDING_APPROVAL"
    ? "warning"
    : status === "APPROVED" || status === "SCHEDULED"
      ? "info"
      : status === "IN_PROGRESS"
        ? "warning"
        : status === "COMPLETED"
          ? "success"
          : status === "REJECTED" || status === "CANCELLED"
            ? "error"
            : "default";

type ShiftTimeState = "UPCOMING" | "ACTIVE" | "ENDED";
export const shiftTimeState = (
  startsAt: string,
  endsAt: string,
  now = Date.now(),
): ShiftTimeState =>
  now < new Date(startsAt).getTime()
    ? "UPCOMING"
    : now <= new Date(endsAt).getTime()
      ? "ACTIVE"
      : "ENDED";

const shiftTimePresentation: Record<
  ShiftTimeState,
  {
    label: string;
    background: string;
    border: string;
    foreground: string;
    badgeBackground: string;
  }
> = {
  UPCOMING: {
    label: "Upcoming",
    background: "#2563a6",
    border: "#174a7e",
    foreground: "#ffffff",
    badgeBackground: "rgba(255,255,255,0.18)",
  },
  ACTIVE: {
    label: "In progress",
    background: "#087f6b",
    border: "#056253",
    foreground: "#ffffff",
    badgeBackground: "rgba(255,255,255,0.18)",
  },
  ENDED: {
    label: "Ended",
    background: "#e7ebf0",
    border: "#aab4c2",
    foreground: "#263548",
    badgeBackground: "#d3dae3",
  },
};

export function HomePlanner({ today }: { today?: string }) {
  const { hasPermission } = useAuth(),
    queryClient = useQueryClient(),
    [mode, setMode] = useState("day"),
    initial = rangeFor("day", today),
    [from, setFrom] = useState(initial.from),
    [to, setTo] = useState(initial.to),
    [selectedDate, setSelectedDate] = useState<string | null>(null),
    [selectedOperation, setSelectedOperation] = useState<CalendarItem | null>(
      null,
    ),
    [createMode, setCreateMode] = useState<"operation" | "shift" | null>(null),
    [clock, setClock] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!today || mode === "custom") return;
    const range = rangeFor(mode, today);
    setFrom(range.from);
    setTo(range.to);
  }, [mode, today]);
  const refreshPlanner = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["home-planner-shifts"] }),
      queryClient.invalidateQueries({ queryKey: ["home-planner-operations"] }),
    ]);
  };
  const setPreset = (value: string) => {
    setMode(value);
    if (value !== "custom") {
      const range = rangeFor(value, today);
      setFrom(range.from);
      setTo(range.to);
    }
  };
  const canShifts = hasPermission("shift.view"),
    canViewShiftPresence = hasPermission("shift.presence.view"),
    canOps = hasPermission("internal_operation.view");
  const shifts = useQuery({
    queryKey: ["home-planner-shifts", from, to],
    enabled: canShifts,
    queryFn: async () =>
      (
        await api.get<CalendarItem[]>("/shift-calendar", {
          params: {
            ends_after: `${from}T00:00:00`,
            starts_before: `${to}T23:59:59`,
          },
        })
      ).data,
    refetchInterval: canViewShiftPresence ? 60_000 : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
  const operations = useQuery({
    queryKey: ["home-planner-operations", from, to],
    enabled: canOps,
    queryFn: async () =>
      (
        await api.get<CalendarItem[]>("/internal-operations", {
          params: { date_from: from, date_to: to },
        })
      ).data,
  });
  const items = useMemo(
    () =>
      [
        ...(shifts.data ?? []).map((x) => ({ ...x, kind: "Shift" })),
        ...(operations.data ?? [])
          .filter((x) => x.status !== "REJECTED")
          .map((x) => ({ ...x, kind: "Operation" })),
      ].sort((a, b) => a.starts_at.localeCompare(b.starts_at)),
    [shifts.data, operations.data],
  );
  const days = useMemo(() => {
    const result: Date[] = [],
      cursor = calendarDate(from),
      end = calendarDate(to);
    while (cursor <= end && result.length < 42) {
      result.push(new Date(cursor));
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    return result;
  }, [from, to]);
  return (
    <Paper sx={{ p: 2.5 }}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        gap={1}
        alignItems={{ md: "center" }}
        mb={2}
      >
        <Box flex={1}>
          <Typography variant="h6" fontWeight={850}>
            Operations planner
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Shifts and internal operations in one calendar range
          </Typography>
        </Box>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={mode}
          onChange={(_, v) => v && setPreset(v)}
        >
          {["day", "week", "month", "custom"].map((v) => (
            <ToggleButton key={v} value={v}>
              {v}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        {mode === "custom" && (
          <>
            <TextField
              size="small"
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
            <TextField
              size="small"
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </>
        )}
      </Stack>
      {(shifts.isError || operations.isError) && (
        <Alert severity="error">Planner data could not be loaded.</Alert>
      )}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: mode === "day" ? "1fr" : "repeat(7,minmax(0,1fr))",
          },
          borderTop: 1,
          borderLeft: 1,
          borderColor: "divider",
        }}
      >
        {mode !== "day" &&
          Array.from({ length: 7 }, (_, index) => (
            <Box
              key={`weekday-${index}`}
              sx={{
                p: 0.75,
                textAlign: "center",
                fontWeight: 900,
                bgcolor: "action.hover",
                borderRight: 1,
                borderBottom: 1,
                borderColor: "divider",
              }}
            >
              {new Date(2026, 7, 2 + index).toLocaleDateString(undefined, {
                weekday: "short",
              })}
            </Box>
          ))}
        {mode === "month" &&
          Array.from({ length: days[0]?.getUTCDay() ?? 0 }, (_, index) => (
            <Box
              key={`blank-${index}`}
              sx={{
                minHeight: 135,
                bgcolor: "action.hover",
                borderRight: 1,
                borderBottom: 1,
                borderColor: "divider",
              }}
            />
          ))}
        {days.map((day) => {
          const key = isoDate(day),
            dayItems = items.filter(
              (item) => isoDate(new Date(item.starts_at)) === key,
            );
          return (
            <Box
              key={key}
              onDoubleClick={(event) => {
                if (
                  !(event.target as HTMLElement).closest(
                    "[data-home-planner-card]",
                  )
                )
                  setSelectedDate(key);
              }}
              sx={{
                minHeight: mode === "month" ? 135 : mode === "week" ? 230 : 320,
                p: 1,
                borderRight: 1,
                borderBottom: 1,
                borderColor: "divider",
                bgcolor: "background.paper",
                cursor: "default",
              }}
            >
              <Typography fontWeight={900} mb={0.75}>
                {day.toLocaleDateString(undefined, {
                  weekday: "short",
                  day: "numeric",
                  month: mode === "day" ? "long" : "short",
                })}
              </Typography>
              <Stack spacing={0.5}>
                {dayItems.map((item, index) => {
                  const shiftTiming =
                    item.kind === "Shift"
                      ? shiftTimePresentation[
                          shiftTimeState(item.starts_at, item.ends_at, clock)
                        ]
                      : null;
                  return (
                    <Box
                    key={`${item.kind}-${item.id}-${index}`}
                    data-home-planner-card
                    role={item.kind === "Operation" ? "button" : undefined}
                    tabIndex={item.kind === "Operation" ? 0 : undefined}
                    onDoubleClick={(event) => {
                      event.stopPropagation();
                      if (item.kind === "Operation") setSelectedOperation(item);
                    }}
                    onKeyDown={(event) => {
                      if (
                        item.kind === "Operation" &&
                        (event.key === "Enter" || event.key === " ")
                      ) {
                        event.preventDefault();
                        setSelectedOperation(item);
                      }
                    }}
                    sx={{
                      p: 0.65,
                      borderRadius: 1,
                      color:
                        item.kind === "Shift"
                          ? shiftTiming?.foreground
                          : "secondary.contrastText",
                      bgcolor:
                        item.kind === "Shift"
                          ? shiftTiming?.background
                          : "secondary.main",
                      fontFamily: "inherit",
                      border: 1,
                      borderColor:
                        item.kind === "Shift"
                          ? shiftTiming?.border
                          : "secondary.dark",
                      cursor: item.kind === "Operation" ? "pointer" : "default",
                      "&:hover":
                        item.kind === "Operation"
                          ? { boxShadow: 3 }
                          : undefined,
                    }}
                  >
                    <Stack direction="row" alignItems="center" gap={0.5}>
                      <Typography
                        variant="caption"
                        fontWeight={800}
                        display="block"
                        noWrap
                        flexGrow={1}
                      >
                        {item.title ?? item.name ?? `${item.kind} #${item.id}`}
                      </Typography>
                      {shiftTiming && (
                        <Chip
                          size="small"
                          label={shiftTiming.label}
                          sx={{
                            height: 19,
                            bgcolor: shiftTiming.badgeBackground,
                            color: shiftTiming.foreground,
                            border: `1px solid ${shiftTiming.border}`,
                            fontWeight: 850,
                            "& .MuiChip-label": { px: 0.75 },
                          }}
                        />
                      )}
                    </Stack>
                    <Typography variant="caption">
                      {new Date(item.starts_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      –
                      {new Date(item.ends_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </Typography>
                    {item.kind === "Shift" && item.employee_name && (
                      <Stack gap={0.5}>
                        <Stack direction="row" gap={0.5} alignItems="center">
                          <Groups sx={{ fontSize: 14 }} />
                          <Typography variant="caption" fontWeight={700} noWrap>
                            {item.employee_name}
                          </Typography>
                        </Stack>
                        {canViewShiftPresence &&
                          item.presence_status &&
                          Date.now() >= new Date(item.starts_at).getTime() &&
                          Date.now() <= new Date(item.ends_at).getTime() && (
                            <Chip
                              size="small"
                              label={
                                item.presence_status === "ACTIVE"
                                  ? "Active now"
                                  : item.presence_status === "IDLE"
                                    ? "Idle"
                                    : "Offline"
                              }
                              title={
                                item.last_seen_at
                                  ? `Last activity: ${new Date(item.last_seen_at).toLocaleString()}`
                                  : "No recent system activity"
                              }
                              sx={{
                                alignSelf: "flex-start",
                                height: 20,
                                bgcolor:
                                  item.presence_status === "ACTIVE"
                                    ? "success.light"
                                    : item.presence_status === "IDLE"
                                      ? "warning.light"
                                      : "grey.300",
                                color: "grey.900",
                                fontWeight: 850,
                                "& .MuiChip-label": { px: 0.8 },
                              }}
                            />
                          )}
                      </Stack>
                    )}
                    {item.kind === "Operation" && (
                      <>
                        <Stack direction="row" gap={0.5} alignItems="center">
                          <Groups sx={{ fontSize: 14 }} />
                          <Typography variant="caption" fontWeight={700} noWrap>
                            {item.assignees?.length
                              ? item.assignees
                                  .map((engineer) => engineer.full_name)
                                  .join(", ")
                              : "Unassigned"}
                          </Typography>
                        </Stack>
                        {item.client_name && (
                          <Stack direction="row" gap={0.5} alignItems="center">
                            <Business sx={{ fontSize: 14 }} />
                            <Typography variant="caption" noWrap>
                              {item.client_code
                                ? `${item.client_code} — ${item.client_name}`
                                : item.client_name}
                            </Typography>
                          </Stack>
                        )}
                        <Chip
                          size="small"
                          label={item.status.replaceAll("_", " ")}
                          color={statusColor(item.status)}
                          sx={{
                            mt: 0.5,
                            height: 20,
                            fontWeight: 800,
                          }}
                        />
                      </>
                    )}
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          );
        })}
      </Box>
      {!items.length && !shifts.isLoading && !operations.isLoading && (
        <Alert severity="info">No shifts or operations in this period.</Alert>
      )}
      <Dialog
        open={selectedOperation !== null}
        onClose={() => setSelectedOperation(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {selectedOperation?.title ?? "Operation details"}
        </DialogTitle>
        <DialogContent dividers>
          {selectedOperation && (
            <Stack spacing={2}>
              <Stack direction="row" gap={0.75} flexWrap="wrap">
                <Chip
                  label={
                    selectedOperation.operation_type?.replaceAll("_", " ") ??
                    "Operation"
                  }
                  color="secondary"
                />
                <Chip
                  label={selectedOperation.status.replaceAll("_", " ")}
                  color={statusColor(selectedOperation.status)}
                />
              </Stack>
              <Typography>
                <b>Schedule:</b>{" "}
                {new Date(selectedOperation.starts_at).toLocaleString()} —{" "}
                {new Date(selectedOperation.ends_at).toLocaleString()}
              </Typography>
              {selectedOperation.client_name && (
                <Stack direction="row" gap={1} alignItems="center">
                  <Business color="action" />
                  <Typography>
                    <b>Client:</b>{" "}
                    {selectedOperation.client_code
                      ? `${selectedOperation.client_code} — ${selectedOperation.client_name}`
                      : selectedOperation.client_name}
                  </Typography>
                </Stack>
              )}
              <Box>
                <Stack direction="row" gap={1} alignItems="center" mb={1}>
                  <Groups color="action" />
                  <Typography fontWeight={800}>Assigned engineers</Typography>
                </Stack>
                <Stack direction="row" gap={0.75} flexWrap="wrap">
                  {selectedOperation.assignees?.length ? (
                    selectedOperation.assignees.map((engineer) => (
                      <Chip
                        key={engineer.id}
                        label={engineer.full_name}
                        color="primary"
                        variant="outlined"
                      />
                    ))
                  ) : (
                    <Alert severity="warning" sx={{ width: "100%" }}>
                      No engineers are assigned.
                    </Alert>
                  )}
                </Stack>
              </Box>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedOperation(null)}>Close</Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(selectedDate) && !createMode}
        onClose={() => setSelectedDate(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Calendar actions · {selectedDate}</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} mt={1}>
            {(hasPermission("internal_operation.create") ||
              hasPermission("internal_operation.manage")) && (
              <Button
                variant="contained"
                onClick={() => setCreateMode("operation")}
              >
                Create internal operation
              </Button>
            )}
            {(hasPermission("shift.create") ||
              hasPermission("shift.manage")) && (
              <Button variant="outlined" onClick={() => setCreateMode("shift")}>
                Paint a shift
              </Button>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedDate(null)}>Cancel</Button>
        </DialogActions>
      </Dialog>
      {createMode === "operation" && selectedDate && (
        <InternalOperationsPage
          dialogOnly
          initialCreateDate={selectedDate}
          onCreated={refreshPlanner}
          onClose={() => {
            setCreateMode(null);
            setSelectedDate(null);
          }}
        />
      )}
      <Dialog
        open={createMode === "shift"}
        onClose={() => {
          setCreateMode(null);
          setSelectedDate(null);
        }}
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle>Paint a shift · {selectedDate}</DialogTitle>
        <DialogContent dividers>
          {selectedDate && (
            <ShiftPaintMode
              initialDate={selectedDate}
              defaultExpanded
              onApplied={() => {
                setCreateMode(null);
                setSelectedDate(null);
                void refreshPlanner();
              }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setCreateMode(null);
              setSelectedDate(null);
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

export function InactiveClientsGrid() {
  const { hasPermission } = useAuth(),
    [page, setPage] = useState(0),
    [rows, setRows] = useState(5);
  const query = useQuery({
    queryKey: ["home-inactive-clients", page, rows],
    enabled: hasPermission("client.view"),
    queryFn: async () =>
      (
        await api.get<ClientPage>("/clients/search-page", {
          params: {
            account_status: "INACTIVE",
            active_only: false,
            limit: rows,
            offset: page * rows,
          },
        })
      ).data,
  });
  if (!hasPermission("client.view")) return null;
  return (
    <Paper sx={{ p: 2.5 }}>
      <Stack direction="row">
        <Box flex={1}>
          <Typography variant="h6" fontWeight={850}>
            Inactive clients
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {query.data?.total ?? 0} clients
          </Typography>
        </Box>
        <Button component={Link} to="/clients?account_status=INACTIVE">
          Show all
        </Button>
      </Stack>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Code</TableCell>
              <TableCell>Client</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {query.data?.items.map((row) => (
              <TableRow hover key={row.id}>
                <TableCell dir="ltr">{row.code}</TableCell>
                <TableCell>{row.name}</TableCell>
                <TableCell>
                  <Chip size="small" label="Inactive" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={query.data?.total ?? 0}
        page={page}
        onPageChange={(_, v) => setPage(v)}
        rowsPerPage={rows}
        onRowsPerPageChange={(e) => {
          setRows(Number(e.target.value));
          setPage(0);
        }}
        rowsPerPageOptions={[5, 10, 25, 50, 100]}
      />
    </Paper>
  );
}

export function TicketApprovals() {
  const { hasPermission } = useAuth(),
    cache = useQueryClient(),
    allowed = hasPermission("entitlement_approval.decide");
  const query = useQuery({
    queryKey: ["home-ticket-approvals"],
    enabled: allowed,
    queryFn: async () =>
      (
        await api.get<Approval[]>("/entitlement-approvals", {
          params: { status: "PENDING" },
        })
      ).data,
  });
  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: number; decision: string }) =>
      api.post(`/entitlement-approvals/${id}/decision`, {
        decision,
        comment:
          decision === "APPROVED"
            ? "Approved from home dashboard"
            : "Rejected from home dashboard",
      }),
    onSuccess: () =>
      cache.invalidateQueries({ queryKey: ["home-ticket-approvals"] }),
  });
  if (!allowed) return null;
  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography variant="h6" fontWeight={850}>
        Ticket approvals
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Request</TableCell>
              <TableCell>Requester</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {query.data?.map((row) => (
              <TableRow key={row.id}>
                <TableCell>
                  {row.ticket_id ? (
                    <Button component={Link} to={`/tickets/${row.ticket_id}`}>
                      Ticket #{row.ticket_id}
                    </Button>
                  ) : (
                    `Request #${row.id}`
                  )}
                  <Typography variant="caption" display="block">
                    {row.justification ?? row.requested_action}
                  </Typography>
                </TableCell>
                <TableCell>{row.requester_name ?? "—"}</TableCell>
                <TableCell align="right">
                  <Button
                    color="error"
                    startIcon={<Close />}
                    onClick={() =>
                      decide.mutate({ id: row.id, decision: "REJECTED" })
                    }
                  >
                    Reject
                  </Button>
                  <Button
                    color="success"
                    startIcon={<Check />}
                    onClick={() =>
                      decide.mutate({ id: row.id, decision: "APPROVED" })
                    }
                  >
                    Approve
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {!query.data?.length && !query.isLoading && (
        <Alert severity="success">No ticket approvals are waiting.</Alert>
      )}
    </Paper>
  );
}

export function OperationPanels({ personalOnly = false }: { personalOnly?: boolean }) {
  const { hasPermission, user } = useAuth(),
    cache = useQueryClient(),
    allowed = hasPermission("internal_operation.view"),
    manager = hasPermission("internal_operation.manage");
  const query = useQuery({
    queryKey: ["home-user-operations"],
    enabled: allowed,
    queryFn: async () =>
      (await api.get<Operation[]>("/internal-operations")).data,
  });
  const mine = (query.data ?? []).filter((row) =>
    row.assignees.some((x) => x.id === user?.id),
  );
  const pending = (query.data ?? []).filter(
    (row) =>
      row.operation_type === "OUTDOOR_VISIT" &&
      row.status === "PENDING_APPROVAL",
  );
  const transition = useMutation({
    mutationFn: ({ row, status }: { row: Operation; status: string }) =>
      api.post(`/internal-operations/${row.id}/transition`, {
        to_status: status,
        expected_version: row.version,
        reason: `${status.replaceAll("_", " ")} from home dashboard`,
      }),
    onSuccess: () =>
      cache.invalidateQueries({ queryKey: ["home-user-operations"] }),
  });
  if (!allowed) return null;
  return (
    <>
      {manager && !personalOnly && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" fontWeight={850}>
            Operation approvals
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={1}>
            Visit requests awaiting manager or team-leader action
          </Typography>
          {pending.map((row) => (
            <Stack
              key={row.id}
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              alignItems={{ sm: "center" }}
              py={1}
            >
              <DirectionsCar color="primary" />
              <Box flex={1}>
                <Typography fontWeight={800}>{row.title}</Typography>
                <Typography variant="caption">
                  {row.client_name ?? "No client"} ·{" "}
                  {new Date(row.starts_at).toLocaleString()}
                </Typography>
              </Box>
              <Button
                color="error"
                onClick={() => transition.mutate({ row, status: "REJECTED" })}
              >
                Reject
              </Button>
              <Button
                color="success"
                variant="contained"
                onClick={() => transition.mutate({ row, status: "APPROVED" })}
              >
                Approve
              </Button>
            </Stack>
          ))}
          {!pending.length && !query.isLoading && (
            <Alert severity="success">No visit approvals are waiting.</Alert>
          )}
        </Paper>
      )}
      <Box>
        <Typography variant="h6" fontWeight={850} mb={1}>
          My operations
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "repeat(2,1fr)",
              xl: "repeat(3,1fr)",
            },
            gap: 1.5,
          }}
        >
          {mine.map((row) => (
            <Card key={row.id} variant="outlined" sx={{ p: 2 }}>
              <Stack direction="row">
                <Box flex={1}>
                  <Typography fontWeight={850}>{row.title}</Typography>
                  <Typography variant="caption">
                    {new Date(row.starts_at).toLocaleString()}
                  </Typography>
                </Box>
                <Chip
                  size="small"
                  color={statusColor(row.status)}
                  label={row.status.replaceAll("_", " ")}
                />
              </Stack>
              <Stack direction="row" gap={1} mt={1.5}>
                {["APPROVED", "SCHEDULED", "CONFIRMED"].includes(
                  row.status,
                ) && (
                  <Button
                    startIcon={<PlayArrow />}
                    onClick={() =>
                      transition.mutate({
                        row,
                        status: "IN_PROGRESS",
                      })
                    }
                  >
                    Start work
                  </Button>
                )}
                {row.status === "IN_PROGRESS" && (
                  <Button
                    color="success"
                    startIcon={<TaskAlt />}
                    onClick={() =>
                      transition.mutate({ row, status: "COMPLETED" })
                    }
                  >
                    Complete
                  </Button>
                )}
              </Stack>
            </Card>
          ))}
        </Box>
        {!mine.length && !query.isLoading && (
          <Alert severity="info">You have no operations in this view.</Alert>
        )}
      </Box>
      {transition.isError && (
        <Alert severity="error">{apiErrorMessage(transition.error)}</Alert>
      )}
    </>
  );
}
