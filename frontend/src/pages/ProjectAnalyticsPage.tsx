import {
  Analytics,
  ArrowForward,
  CalendarMonth,
  CheckCircleOutline,
  FilterAltOff,
  InfoOutlined,
  WarningAmber,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Drawer,
  LinearProgress,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { projectMyWorkPath, projectWorkspacePermission } from "../auth/projectWorkspaceAccess";
import { AnalyticsRateChart } from "../components/AnalyticsRateChart";

type Option = { id: number; name: string; account_id?: number; organization_id?: number };
type Options = {
  accounts: Option[];
  organizations: Option[];
  clients: Option[];
  departments: Option[];
  managers: Option[];
};
type Metric = {
  code: string;
  name: string;
  domain: string;
  status: "READY" | "UNAVAILABLE";
  value: number | null;
  unit: string;
  numerator: number | null;
  denominator: number | null;
  eligible_count: number;
  drilldown_count: number;
  unavailable_reason?: string | null;
};
type Scope = {
  account_id: number | null;
  organization_id: number | null;
  client_id: number | null;
  department_id: number | null;
  project_id: number | null;
  effective_department_ids: number[];
  global_scope: boolean;
};
type Projection = {
  domain: string;
  period_start: string;
  period_end: string;
  generated_at: string;
  scope: Scope;
  metrics: Metric[];
};
type DrilldownRow = {
  record_type: string;
  record_id: number;
  project_id: number | null;
  project_number: string | null;
  client_id: number | null;
  department_id: number | null;
  label: string;
  numerator_contribution: number | null;
  denominator_contribution: number | null;
  measured_value: number | null;
  occurred_at: string | null;
  status: string | null;
};
type Drilldown = { projection: Metric; scope: Scope; period_start: string; period_end: string; rows: DrilldownRow[] };
type Filters = { period_start: string; period_end: string; account_id: string; organization_id: string; client_id: string; department_id: string };

export function localDateValue(value: Date) {
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 10);
}

export function projectAnalyticsParams(filters: Filters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== ""),
  );
}

function initialFilters(): Filters {
  const end = new Date();
  const start = new Date(end.getFullYear(), end.getMonth(), 1);
  return {
    period_start: localDateValue(start),
    period_end: localDateValue(end),
    account_id: "",
    organization_id: "",
    client_id: "",
    department_id: "",
  };
}

function metricValue(metric: Metric) {
  if (metric.status === "UNAVAILABLE") return "Unavailable";
  if (metric.value === null) return "—";
  if (metric.unit === "PERCENT") return `${metric.value.toLocaleString()}%`;
  if (metric.unit === "HOURS") return `${metric.value.toLocaleString()}h`;
  return metric.value.toLocaleString();
}

function MetricCard({ metric, onOpen }: { metric: Metric; onOpen: (metric: Metric) => void }) {
  const unavailable = metric.status === "UNAVAILABLE";
  const noPopulation = metric.status === "READY" && metric.value === null;
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        minHeight: 138,
        borderColor: unavailable ? "warning.light" : "divider",
        bgcolor: unavailable ? "warning.50" : "background.paper",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1}>
        <Typography variant="body2" fontWeight={800}>{metric.name}</Typography>
        {unavailable ? <WarningAmber color="warning" fontSize="small" /> : <CheckCircleOutline color="success" fontSize="small" />}
      </Stack>
      <Typography variant="h4" fontWeight={850} mt={0.5} color={unavailable ? "warning.dark" : "text.primary"}>
        {metricValue(metric)}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ minHeight: 34 }}>
        {unavailable
          ? metric.unavailable_reason
          : noPopulation
            ? "No eligible records in this period"
            : `${metric.eligible_count} eligible · ${metric.drilldown_count} detail rows`}
      </Typography>
      <Button
        size="small"
        endIcon={<ArrowForward fontSize="small" />}
        onClick={() => onOpen(metric)}
        disabled={unavailable}
        sx={{ mt: "auto", alignSelf: "flex-start", px: 0 }}
      >
        View exact records
      </Button>
    </Paper>
  );
}

export function ProjectAnalyticsPage() {
  const { hasPermission } = useAuth();
  const canViewExecutiveRisk = hasPermission("analytics.executive.view");
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [selectedMetric, setSelectedMetric] = useState<Metric | null>(null);
  const params = useMemo(() => projectAnalyticsParams(filters), [filters]);
  const invalidPeriod = filters.period_start > filters.period_end;
  const options = useQuery({
    queryKey: ["project-options", "analytics"],
    queryFn: async () => (await api.get<Options>("/projects/options")).data,
  });
  const projection = useQuery({
    queryKey: ["project-analytics", "PROJECT", params],
    queryFn: async () => (await api.get<Projection>("/project-analytics/projections/PROJECT", { params })).data,
    enabled: !invalidPeriod,
  });
  const drilldown = useQuery({
    queryKey: ["project-analytics-drilldown", selectedMetric?.code, params],
    queryFn: async () => (await api.get<Drilldown>(`/project-analytics/projections/kpi/${selectedMetric?.code}/drilldown`, { params })).data,
    enabled: Boolean(selectedMetric && !invalidPeriod),
  });
  const attentionMetric = canViewExecutiveRisk ? "AT_RISK_PROJECT_COUNT" : "PROJECT_ON_TIME_RATE";
  const risk = useQuery({
    queryKey: ["project-analytics-drilldown", attentionMetric, params],
    queryFn: async () => (await api.get<Drilldown>(`/project-analytics/projections/kpi/${attentionMetric}/drilldown`, { params })).data,
    enabled: !invalidPeriod,
  });
  const attentionRows = (risk.data?.rows ?? []).filter((row) => canViewExecutiveRisk || row.status === "OVERDUE");
  const organizations = (options.data?.organizations ?? []).filter(
    (item) => !filters.account_id || String(item.account_id) === filters.account_id,
  );
  const clients = (options.data?.clients ?? []).filter(
    (item) => !filters.organization_id || String(item.organization_id) === filters.organization_id,
  );
  const clearScope = () => setFilters((current) => ({ ...current, account_id: "", organization_id: "", client_id: "", department_id: "" }));

  return (
    <Box sx={{ width: "100%", minWidth: 0 }}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={1.5} mb={2}>
        <Box>
          <Stack direction="row" gap={1} alignItems="center">
            <Analytics color="primary" />
            <Typography variant="h4" fontWeight={850}>Project Management analytics</Typography>
          </Stack>
          <Typography color="text.secondary">Governed delivery health with permission-filtered totals and exact-record reconciliation.</Typography>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap">
          {hasPermission(projectWorkspacePermission) && hasPermission("project.portfolio.view") &&
            <Button component={Link} to={`${projectMyWorkPath}?action=Schedule`}>My schedule decisions</Button>}
          <Button component={Link} to="/projects" variant="outlined">Open portfolio</Button>
        </Stack>
      </Stack>

      <Paper variant="outlined" sx={{ p: 1.5, mb: 1.5 }}>
        <Stack direction={{ xs: "column", lg: "row" }} gap={1} alignItems={{ lg: "center" }}>
          <TextField size="small" type="date" label="From" value={filters.period_start} onChange={(event) => setFilters({ ...filters, period_start: event.target.value })} InputLabelProps={{ shrink: true }} sx={{ minWidth: 155 }} />
          <TextField size="small" type="date" label="To" value={filters.period_end} onChange={(event) => setFilters({ ...filters, period_end: event.target.value })} InputLabelProps={{ shrink: true }} sx={{ minWidth: 155 }} />
          <TextField select size="small" label="Account" value={filters.account_id} onChange={(event) => setFilters({ ...filters, account_id: event.target.value, organization_id: "", client_id: "" })} sx={{ minWidth: 170 }}><MenuItem value="">All authorized</MenuItem>{options.data?.accounts.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
          <TextField select size="small" label="Organization" value={filters.organization_id} onChange={(event) => setFilters({ ...filters, organization_id: event.target.value, client_id: "" })} sx={{ minWidth: 180 }}><MenuItem value="">All authorized</MenuItem>{organizations.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
          <TextField select size="small" label="Client" value={filters.client_id} onChange={(event) => setFilters({ ...filters, client_id: event.target.value })} sx={{ minWidth: 180 }}><MenuItem value="">All authorized</MenuItem>{clients.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
          <TextField select size="small" label="Department" value={filters.department_id} onChange={(event) => setFilters({ ...filters, department_id: event.target.value })} sx={{ minWidth: 180 }}><MenuItem value="">My effective scope</MenuItem>{options.data?.departments.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
          <Tooltip title="Clear customer and department filters"><Button size="small" startIcon={<FilterAltOff />} onClick={clearScope}>Clear scope</Button></Tooltip>
        </Stack>
        {invalidPeriod && <Alert severity="error" sx={{ mt: 1 }}>The end date cannot precede the start date.</Alert>}
      </Paper>

      {projection.isLoading && <Stack direction="row" gap={1}>{[1, 2, 3].map((item) => <Skeleton key={item} variant="rounded" height={138} sx={{ flex: 1 }} />)}</Stack>}
      {projection.isError && <Alert severity="error">{apiErrorMessage(projection.error)}</Alert>}
      {projection.data && (
        <>
          <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }} mb={1.25}>
            <Chip size="small" icon={<CalendarMonth />} label={`${projection.data.period_start} → ${projection.data.period_end}`} />
            <Chip size="small" color={projection.data.scope.global_scope ? "secondary" : "primary"} variant="outlined" label={projection.data.scope.global_scope ? "Company-authorized scope" : `${projection.data.scope.effective_department_ids.length} effective department${projection.data.scope.effective_department_ids.length === 1 ? "" : "s"}`} />
            <Typography variant="caption" color="text.secondary" sx={{ ml: { sm: "auto" } }}>Generated {new Date(projection.data.generated_at).toLocaleString()}</Typography>
          </Stack>
          <AnalyticsRateChart title="Schedule performance" metrics={projection.data.metrics} onOpen={setSelectedMetric} />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" }, gap: 1.25 }}>
            {projection.data.metrics.map((metric) => <MetricCard key={metric.code} metric={metric} onOpen={setSelectedMetric} />)}
          </Box>
        </>
      )}

      <Paper variant="outlined" sx={{ mt: 1.5, overflow: "hidden" }}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1} p={1.5} alignItems={{ sm: "center" }}>
          <Box>
            <Typography fontWeight={850}>{canViewExecutiveRisk ? "Projects requiring attention" : "Schedule exceptions"}</Typography>
            <Typography variant="body2" color="text.secondary">{canViewExecutiveRisk
              ? "Projects flagged at risk or critical."
              : "Projects that finished late or were overdue at the reporting cutoff."}</Typography>
          </Box>
          {risk.data && <Chip size="small" color={attentionRows.length ? "error" : "default"}
            label={`${attentionRows.length} ${canViewExecutiveRisk ? "at risk" : "late or overdue"}`} />}
        </Stack>
        <Divider />
        {risk.isLoading && <LinearProgress />}
        {risk.isError && <Alert severity="error" sx={{ m: 1.5 }}>{apiErrorMessage(risk.error)}</Alert>}
        {risk.data && attentionRows.length === 0 && <Stack alignItems="center" py={4} gap={0.5}><CheckCircleOutline color="success" /><Typography fontWeight={750}>{canViewExecutiveRisk ? "No at-risk projects in this scope" : "No schedule exceptions found"}</Typography></Stack>}
        {attentionRows.length > 0 && <TableContainer><Table size="small"><TableHead><TableRow><TableCell>Project</TableCell><TableCell>Status</TableCell><TableCell>Measured at</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead><TableBody>{attentionRows.map((row) => <TableRow key={row.record_id} hover><TableCell><Typography fontWeight={750}>{row.project_number}</Typography><Typography variant="caption" color="text.secondary">{row.label}</Typography></TableCell><TableCell><Chip size="small" color="error" variant="outlined" label={row.status?.replaceAll("_", " ") ?? "AT RISK"} /></TableCell><TableCell>{row.occurred_at ? new Date(row.occurred_at).toLocaleDateString() : "—"}</TableCell><TableCell align="right"><Button component={Link} to={`/projects/${row.project_id}/schedule`} size="small">Open schedule</Button></TableCell></TableRow>)}</TableBody></Table></TableContainer>}
      </Paper>

      <Alert severity="info" icon={<InfoOutlined />} sx={{ mt: 1.5 }}>Metrics with missing authoritative evidence are shown as unavailable. The dashboard never substitutes record update time for completion evidence.</Alert>

      <Drawer anchor="right" open={Boolean(selectedMetric)} onClose={() => setSelectedMetric(null)} PaperProps={{ sx: { width: { xs: "100%", sm: 620 }, p: 2 } }}>
        <Stack gap={1.5}>
          <Stack direction="row" justifyContent="space-between" gap={1}><Box><Typography variant="overline">Exact-record drilldown</Typography><Typography variant="h5" fontWeight={850}>{selectedMetric?.name}</Typography></Box><Chip label={selectedMetric ? metricValue(selectedMetric) : ""} color="primary" /></Stack>
          <Divider />
          {drilldown.isLoading && <Stack alignItems="center" py={6}><CircularProgress /></Stack>}
          {drilldown.isError && <Alert severity="error">{apiErrorMessage(drilldown.error)}</Alert>}
          {drilldown.data && <><Stack direction="row" gap={1} flexWrap="wrap"><Chip size="small" label={`Numerator: ${drilldown.data.projection.numerator ?? "—"}`} /><Chip size="small" label={`Denominator: ${drilldown.data.projection.denominator ?? "—"}`} /><Chip size="small" label={`${drilldown.data.rows.length} records`} /></Stack>{drilldown.data.rows.length === 0 ? <Alert severity="info">No eligible records for this metric and scope.</Alert> : <Stack gap={1}>{drilldown.data.rows.map((row) => <Paper variant="outlined" key={`${row.record_type}-${row.record_id}`} sx={{ p: 1.25 }}><Stack direction="row" justifyContent="space-between" gap={1}><Box sx={{ minWidth: 0 }}><Typography fontWeight={750}>{row.project_number} · {row.label}</Typography><Typography variant="caption" color="text.secondary">{row.record_type.replaceAll("_", " ")} #{row.record_id}{row.occurred_at ? ` · ${new Date(row.occurred_at).toLocaleString()}` : ""}</Typography></Box><Chip size="small" variant="outlined" label={row.status?.replaceAll("_", " ") ?? "Included"} /></Stack><Stack direction="row" gap={2} mt={1}><Typography variant="caption">Numerator: {row.numerator_contribution ?? "—"}</Typography><Typography variant="caption">Denominator: {row.denominator_contribution ?? "—"}</Typography></Stack>{row.project_id && <Button component={Link} to={`/projects/${row.project_id}/execution`} size="small" sx={{ mt: 0.5, px: 0 }}>Open project</Button>}</Paper>)}</Stack>}</>}
          <Button onClick={() => setSelectedMetric(null)}>Close</Button>
        </Stack>
      </Drawer>
    </Box>
  );
}
