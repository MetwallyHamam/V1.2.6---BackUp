import {
  ViewKanban,
  TableRows,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  alpha,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TechnicalText } from "../components/TechnicalText";

type ChangeRow = {
  id: number | null;
  ticket_id: number;
  ticket_number: string;
  subject: string;
  client_name: string;
  ticket_status: string;
  change_status: string;
  request_kind?: string | null;
  requested_priority: string;
  risk_level?: string | null;
  target_release?: string | null;
  planned_start_at?: string | null;
  planned_end_at?: string | null;
};
type ChangeSummary = {
  total: number;
  active: number;
  awaiting_approval: number;
  implementing: number;
  validation: number;
  overdue: number;
  details_required: number;
};
type FilterOptions = {
  clients: Array<{ id: number; name: string }>;
  products: Array<{ id: number; name: string }>;
  modules: Array<{ id: number; product_id: number; name: string }>;
};
const inputDate = (value: Date) => {
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 10);
};
const statuses = [
  "",
  "DETAILS_REQUIRED",
  "SUBMITTED",
  "UNDER_ASSESSMENT",
  "AWAITING_APPROVAL",
  "APPROVED",
  "REJECTED",
  "PLANNED",
  "PENDING_DEPLOYMENT",
  "IMPLEMENTING",
  "VALIDATION",
  "COMPLETED",
  "FAILED",
  "ROLLED_BACK",
  "CANCELLED",
];
const transitions: Record<string, string[]> = {
  SUBMITTED: ["UNDER_ASSESSMENT", "CANCELLED"],
  UNDER_ASSESSMENT: ["AWAITING_APPROVAL", "CANCELLED"],
  AWAITING_APPROVAL: ["APPROVED", "REJECTED", "UNDER_ASSESSMENT"],
  APPROVED: ["PLANNED", "CANCELLED"],
  PLANNED: ["PENDING_DEPLOYMENT", "CANCELLED"],
  PENDING_DEPLOYMENT: ["IMPLEMENTING", "CANCELLED"],
  IMPLEMENTING: ["VALIDATION", "FAILED", "ROLLED_BACK"],
  VALIDATION: ["PENDING_DEPLOYMENT", "COMPLETED", "FAILED", "ROLLED_BACK"],
  FAILED: ["UNDER_ASSESSMENT", "ROLLED_BACK"],
  REJECTED: ["UNDER_ASSESSMENT"],
  ROLLED_BACK: ["UNDER_ASSESSMENT"],
  COMPLETED: ["UNDER_ASSESSMENT"],
  CANCELLED: ["UNDER_ASSESSMENT"],
};
const transitionPermission: Record<string, string> = {
  UNDER_ASSESSMENT: "change_request.assess",
  AWAITING_APPROVAL: "change_request.assess",
  CANCELLED: "change_request.assess",
  APPROVED: "change_request.approve",
  REJECTED: "change_request.approve",
  PLANNED: "change_request.plan",
  PENDING_DEPLOYMENT: "change_request.plan",
  IMPLEMENTING: "change_request.implement",
  VALIDATION: "change_request.validate",
  COMPLETED: "change_request.complete",
  FAILED: "change_request.implement",
  ROLLED_BACK: "change_request.rollback",
};
const statusColors: Record<string, string> = {
  DETAILS_REQUIRED: "#f57c00",
  SUBMITTED: "#607d8b", UNDER_ASSESSMENT: "#0288d1", AWAITING_APPROVAL: "#ed6c02",
  APPROVED: "#2e7d32", REJECTED: "#d32f2f", PLANNED: "#7b1fa2",
  PENDING_DEPLOYMENT: "#5d4037", IMPLEMENTING: "#1565c0", VALIDATION: "#00897b",
  COMPLETED: "#1b5e20", FAILED: "#c62828", ROLLED_BACK: "#6d4c41", CANCELLED: "#616161",
};
type BoardLane = {
  key: string;
  title: string;
  statuses: string[];
  color: string;
};
const activeBoardLanes: BoardLane[] = [
  { key: "INTAKE", title: "Intake", statuses: ["DETAILS_REQUIRED", "SUBMITTED"], color: "#607d8b" },
  { key: "ASSESSMENT", title: "Assessment", statuses: ["UNDER_ASSESSMENT"], color: "#0288d1" },
  { key: "APPROVAL", title: "Approval", statuses: ["AWAITING_APPROVAL"], color: "#ed6c02" },
  { key: "PLANNING", title: "Planning", statuses: ["APPROVED", "PLANNED"], color: "#7b1fa2" },
  { key: "DEPLOYMENT", title: "Deployment", statuses: ["PENDING_DEPLOYMENT", "IMPLEMENTING"], color: "#1565c0" },
  { key: "VALIDATION", title: "Validation", statuses: ["VALIDATION"], color: "#00897b" },
  { key: "EXCEPTIONS", title: "Exceptions", statuses: ["REJECTED", "FAILED", "ROLLED_BACK"], color: "#c62828" },
];
const closedBoardLane: BoardLane = {
  key: "CLOSED",
  title: "Closed",
  statuses: ["COMPLETED", "CANCELLED"],
  color: "#455a64",
};
const label = (value?: string | null) =>
  value ? value.replaceAll("_", " ") : "—";
export function ChangeRequestsPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const [view, setView] = useState<"board" | "table">("board");
  const [dragged, setDragged] = useState<ChangeRow | null>(null);
  const [dropLane, setDropLane] = useState("");
  const [boardMessage, setBoardMessage] = useState("");
  const [showClosed, setShowClosed] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [clientId, setClientId] = useState("");
  const [productId, setProductId] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [duration, setDuration] = useState("ALL");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const dates = (() => {
    const today = new Date();
    if (duration === "TODAY") return { created_from: inputDate(today), created_to: inputDate(today) };
    if (["7_DAYS", "30_DAYS"].includes(duration)) {
      const start = new Date(today);
      start.setDate(today.getDate() - (duration === "7_DAYS" ? 6 : 29));
      return { created_from: inputDate(start), created_to: inputDate(today) };
    }
    if (duration === "CUSTOM") return { created_from: dateFrom || undefined, created_to: dateTo || undefined };
    return {};
  })();
  const filterOptions = useQuery({
    queryKey: ["change-request-filter-options"],
    queryFn: async () => (await api.get<FilterOptions>("/change-requests/filter-options")).data,
  });
  const rows = useQuery({
    queryKey: ["change-requests", search, status, clientId, productId, moduleId, dates],
    queryFn: async () =>
      (
        await api.get<ChangeRow[]>("/change-requests", {
          params: {
            search: search.trim() || undefined,
            change_status: status || undefined,
            client_id: clientId || undefined,
            product_id: productId || undefined,
            product_module_id: moduleId || undefined,
            ...dates,
          },
        })
      ).data,
  });
  const summary = useQuery({
    queryKey: ["change-requests-summary", search, status, clientId, productId, moduleId, dates],
    queryFn: async () =>
      (await api.get<ChangeSummary>("/change-requests/summary", { params: {
        search: search.trim() || undefined,
        change_status: status || undefined,
        client_id: clientId || undefined,
        product_id: productId || undefined,
        product_module_id: moduleId || undefined,
        ...dates,
      } })).data,
  });
  async function exportExcel() {
    const response = await api.get("/change-requests/export.xlsx", {
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "change_requests.xlsx";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <Stack gap={2}>
      <Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          alignItems={{ sm: "center" }}
        >
          <Typography variant="h4" sx={{ flexGrow: 1 }}>
            Change Requests
          </Typography>
          <Button variant="outlined" onClick={() => void exportExcel()}>
            Export Excel
          </Button>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={view}
            onChange={(_, value: "board" | "table" | null) => value && setView(value)}
          >
            <ToggleButton value="board"><ViewKanban fontSize="small" sx={{ mr: 0.5 }} />Board</ToggleButton>
            <ToggleButton value="table"><TableRows fontSize="small" sx={{ mr: 0.5 }} />Table</ToggleButton>
          </ToggleButtonGroup>
          {view === "board" && (
            <FormControlLabel
              control={
                <Switch
                  checked={showClosed}
                  onChange={(event) => setShowClosed(event.target.checked)}
                />
              }
              label="Show closed"
            />
          )}
        </Stack>
        <Typography color="text.secondary">
          Assessment, approvals, implementation planning, rollback, and
          validation.
        </Typography>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2,1fr)", md: "repeat(6,1fr)" },
          gap: 1.5,
        }}
      >
        {[
          ["Total", summary.data?.total],
          ["Active", summary.data?.active],
          ["Awaiting approval", summary.data?.awaiting_approval],
          ["Implementing", summary.data?.implementing],
          ["Validation", summary.data?.validation],
          ["Overdue", summary.data?.overdue],
          ["Details required", summary.data?.details_required],
        ].map(([title, value]) => (
          <Paper key={String(title)} variant="outlined" sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">
              {title}
            </Typography>
            <Typography
              variant="h5"
              color={
                title === "Overdue" && Number(value) > 0
                  ? "error.main"
                  : "text.primary"
              }
            >
              {value ?? "…"}
            </Typography>
          </Paper>
        ))}
      </Box>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} gap={2} flexWrap="wrap">
          <TextField
            fullWidth
            label="Search ticket, client, subject, or purpose"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <TextField
            select
            sx={{ minWidth: 240 }}
            label="Change status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {statuses.map((value) => (
              <MenuItem key={value || "ALL"} value={value}>
                {value ? label(value) : "All statuses"}
              </MenuItem>
            ))}
          </TextField>
          <TextField select sx={{ minWidth: 210 }} label="Client" value={clientId} onChange={(event) => setClientId(event.target.value)}>
            <MenuItem value="">All clients</MenuItem>
            {filterOptions.data?.clients.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField select sx={{ minWidth: 210 }} label="Product" value={productId} onChange={(event) => { setProductId(event.target.value); setModuleId(""); }}>
            <MenuItem value="">All products</MenuItem>
            {filterOptions.data?.products.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField select sx={{ minWidth: 210 }} label="Module" value={moduleId} onChange={(event) => setModuleId(event.target.value)}>
            <MenuItem value="">All modules</MenuItem>
            {filterOptions.data?.modules.filter((item) => !productId || item.product_id === Number(productId)).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField select sx={{ minWidth: 190 }} label="Duration" value={duration} onChange={(event) => setDuration(event.target.value)}>
            <MenuItem value="ALL">All dates</MenuItem>
            <MenuItem value="TODAY">Today</MenuItem>
            <MenuItem value="7_DAYS">Last 7 days</MenuItem>
            <MenuItem value="30_DAYS">Last 30 days</MenuItem>
            <MenuItem value="CUSTOM">Custom date</MenuItem>
          </TextField>
          {duration === "CUSTOM" && <>
            <TextField type="date" label="From" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField type="date" label="To" value={dateTo} onChange={(event) => setDateTo(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          </>}
          <Button onClick={() => { setSearch(""); setStatus(""); setClientId(""); setProductId(""); setModuleId(""); setDuration("ALL"); setDateFrom(""); setDateTo(""); }}>Clear filters</Button>
        </Stack>
      </Paper>
      {rows.isLoading && <CircularProgress />}
      {rows.isError && (
        <Alert severity="error">Change Requests could not be loaded.</Alert>
      )}
      {boardMessage && <Alert severity="warning" onClose={() => setBoardMessage("")}>{boardMessage}</Alert>}
      {rows.data?.length === 0 && (
        <Alert severity="info">
          No Change Requests match the current filters.
        </Alert>
      )}
      {!!rows.data?.length && view === "board" && (
        <Box sx={{ display: "flex", gap: 1.5, overflowX: "auto", pb: 1.5, alignItems: "flex-start" }}>
          {[
            ...activeBoardLanes,
            ...(showClosed || closedBoardLane.statuses.includes(status)
              ? [closedBoardLane]
              : []),
          ].map((lane) => {
            const cards = rows.data.filter((row) =>
              lane.statuses.includes(row.change_status),
            );
            const color = lane.color;
            const dropTarget = dragged
              ? (transitions[dragged.change_status] ?? []).find(
                  (target) =>
                    lane.statuses.includes(target) &&
                    hasPermission(
                      transitionPermission[target] ?? "change_request.assess",
                    ),
                )
              : undefined;
            const canDrop = Boolean(dropTarget);
            return (
              <Paper
                key={lane.key}
                variant="outlined"
                onDragOver={(event) => {
                  if (!canDrop) return;
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                  setDropLane(lane.key);
                }}
                onDragLeave={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDropLane("");
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  if (!dragged || !canDrop) return;
                  navigate(`/tickets/${dragged.ticket_id}/change-request?target=${dropTarget}`);
                  setDragged(null);
                  setDropLane("");
                }}
                sx={{
                  width: 285, minWidth: 285, overflow: "hidden", borderRadius: 2,
                  bgcolor: dropLane === lane.key ? alpha(color, 0.12) : alpha(color, 0.025),
                  borderColor: dropLane === lane.key ? color : alpha(color, 0.3),
                  outline: dropLane === lane.key ? `2px dashed ${color}` : "none", outlineOffset: -4,
                }}
              >
                <Stack direction="row" alignItems="center" gap={1} sx={{ p: 1.25, borderTop: `4px solid ${color}`, bgcolor: alpha(color, 0.08) }}>
                  <Typography fontWeight={850} flex={1}>{lane.title}</Typography>
                  <Chip size="small" label={cards.length} sx={{ bgcolor: alpha(color, 0.15), color, fontWeight: 850 }} />
                </Stack>
                <Stack gap={1} sx={{ p: 1, minHeight: 110 }}>
                  {cards.map((row) => {
                    const canDrag = (transitions[row.change_status] ?? []).some((target) =>
                      hasPermission(transitionPermission[target] ?? "change_request.assess"),
                    );
                    return (
                      <Paper
                        key={row.ticket_id}
                        draggable={canDrag}
                        onDragStart={(event) => {
                          event.dataTransfer.effectAllowed = "move";
                          event.dataTransfer.setData("text/change-ticket-id", String(row.ticket_id));
                          setDragged(row);
                          setBoardMessage("");
                        }}
                        onDragEnd={() => { setDragged(null); setDropLane(""); }}
                        onClick={() => navigate(`/tickets/${row.ticket_id}/change-request`)}
                        elevation={0}
                        sx={{ p: 1.25, cursor: canDrag ? "grab" : "pointer", border: "1px solid", borderColor: "divider", borderLeft: `4px solid ${color}`, borderRadius: 1.5, opacity: dragged?.ticket_id === row.ticket_id ? 0.55 : 1, "&:hover": { boxShadow: 3, transform: "translateY(-1px)" }, transition: "all .15s" }}
                      >
                        <Typography variant="caption" color="primary.main" fontWeight={850}><TechnicalText>{row.ticket_number}</TechnicalText></Typography>
                        <Typography fontWeight={750} sx={{ mt: 0.5 }}>{row.subject}</Typography>
                        <Typography variant="body2" color="text.secondary">{row.client_name}</Typography>
                        <Stack direction="row" gap={0.5} flexWrap="wrap" mt={1}>
                          <Chip
                            size="small"
                            label={label(row.change_status)}
                            sx={{
                              color: statusColors[row.change_status] ?? color,
                              borderColor: statusColors[row.change_status] ?? color,
                              fontWeight: 750,
                            }}
                            variant="outlined"
                          />
                          <Chip size="small" label={label(row.requested_priority)} />
                          {row.risk_level && <Chip size="small" variant="outlined" label={`Risk: ${label(row.risk_level)}`} />}
                          {row.target_release && <Chip size="small" variant="outlined" label={row.target_release} />}
                        </Stack>
                      </Paper>
                    );
                  })}
                </Stack>
              </Paper>
            );
          })}
        </Box>
      )}
      {!!rows.data?.length && view === "table" && (
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Ticket</TableCell>
                <TableCell>Client / subject</TableCell>
                <TableCell>Change status</TableCell>
                <TableCell>Ticket status</TableCell>
                <TableCell>Priority / risk</TableCell>
                <TableCell>Target release</TableCell>
                <TableCell>Planned window</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.data.map((row) => (
                <TableRow
                  hover
                  key={row.ticket_id}
                  onClick={() =>
                    navigate(`/tickets/${row.ticket_id}/change-request`)
                  }
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>
                    <TechnicalText>{row.ticket_number}</TechnicalText>
                    <Typography variant="caption" display="block">
                      {label(row.request_kind)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight={600}>{row.client_name}</Typography>
                    <Typography variant="body2">{row.subject}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={
                        row.change_status === "DETAILS_REQUIRED"
                          ? "warning"
                          : "primary"
                      }
                      variant="outlined"
                      label={label(row.change_status)}
                    />
                  </TableCell>
                  <TableCell>{label(row.ticket_status)}</TableCell>
                  <TableCell>
                    {label(row.requested_priority)} / {label(row.risk_level)}
                  </TableCell>
                  <TableCell>{row.target_release || "—"}</TableCell>
                  <TableCell>
                    {row.planned_start_at
                      ? new Date(row.planned_start_at).toLocaleString()
                      : "—"}
                    <Typography variant="caption" display="block">
                      {row.planned_end_at
                        ? `to ${new Date(row.planned_end_at).toLocaleString()}`
                        : ""}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Stack>
  );
}
