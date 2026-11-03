import { ServiceManagementWidget } from "../components/ServiceManagementCards";
import {
  Approval,
  AssignmentLate,
  ConfirmationNumber,
  ErrorOutline,
  ExpandLess,
  ExpandMore,
  Insights,
  PersonOff,
  Refresh,
  Schedule,
  SwapHoriz,
  TaskAlt,
  TrendingUp,
  AspectRatio,
  DragIndicator,
  Save,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, DASHBOARD_ANALYSIS_TIMEOUT_MS } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { FinancialDashboardWidget } from "../components/FinancialAnalyticsDashboard";
import { ClientHoursWidget } from "../components/ClientHoursWidget";
import { InactiveClientsKpi } from "../components/InactiveClientsKpi";
import { dashboardTicketCardSx } from "../components/dashboardCardStyles";
import { currentMonthToDate } from "../utils/dateRange";
import { selectTopSupportAgents } from "../utils/dashboardAgents";
import { DashboardCustomizer, type Widget } from "./DashboardCustomizer";
import { ManagerOverview, type ManagerSummary } from "./ManagerOverview";
import { useTranslation } from "react-i18next";
import { serverDateInput } from "../utils/serverTime";

type DashboardFilterOption = { id: number; name: string; client_id?: number };
type DashboardFilterMetadata = {
  countries: DashboardFilterOption[];
  zones: string[];
  clients: DashboardFilterOption[];
  locations: DashboardFilterOption[];
  products: DashboardFilterOption[];
  teams: DashboardFilterOption[];
  engineers: DashboardFilterOption[];
};

type AgentKpi = {
  user_id: number | null;
  agent: string;
  department?: string | null;
  assigned: number;
  open: number;
  resolved: number;
  breached: number;
  sla_compliance_percent: number | null;
  average_resolution_hours: number | null;
  tickets_by_status: Record<string, number>;
  escalation_assignments: number;
  average_response_hours: number | null;
  reopened_tickets: number;
  external_activities: number;
  after_shift_work: number;
  after_shift_hours: number;
  training_attended: number;
  training_delivered: number;
  meetings: number;
  tasks_created: number;
  knowledge_articles: number;
  follower_assignments: number;
  dedicated_clients: number;
  dedicated_client_tickets: number;
};
type TopSupportAgentsResponse = {
  date_from: string;
  date_to: string;
  date_basis: "RESOLUTION";
  agents: Array<
    Pick<
      AgentKpi,
      "user_id" | "agent" | "department" | "assigned" | "resolved" | "breached"
    >
  >;
};
type ProductKpi = {
  product: string;
  module: string;
  total: number;
  open: number;
  resolved: number;
  breached: number;
  average_resolution_hours: number | null;
};
type AvailableEmployee = {
  user_id: number;
  employee: string;
  shift_name: string;
  shift_color: string;
  starts_at: string;
  ends_at: string;
  team?: string;
};
type OnlineEngineer = {
  user_id: number;
  engineer: string;
  department?: string;
  status: "AVAILABLE" | "WORKING_ON_TICKET";
  ticket_number?: string;
  active_ticket_count: number;
  tickets_by_priority: Record<string, number>;
};
type Summary = {
  total_tickets: number;
  created_today: number;
  closed_today: number;
  total_open: number;
  my_open: number;
  unassigned: number;
  critical: number;
  breached: number;
  due_soon: number;
  shift_handovers: number;
  department_new: number;
  department_in_progress: number;
  department_returned: number;
  resolved: number;
  closed: number;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
  backlog_by_client: Record<string, number>;
  backlog_by_product: Record<string, number>;
  backlog_by_module: Record<string, number>;
  workload_by_engineer: Record<string, number>;
  backlog_by_team: Record<string, number>;
  sla_compliance_percent: number | null;
  aging_buckets: Record<string, number>;
  inflow_last_7_days: Record<string, number>;
  closures_last_7_days: Record<string, number>;
  average_resolution_hours: number | null;
  reopen_rate_percent: number;
  active_escalations: number;
  top_categories: Record<string, number>;
  top_repeated_issues: Record<string, number>;
  expiring_contracts: number;
  agent_kpis: AgentKpi[];
  product_kpis: ProductKpi[];
  kpi_month: string;
  available_employees: AvailableEmployee[];
  online_engineers: OnlineEngineer[];
  financial_contracts: number;
  financial_invoices: number;
  financial_contract_value: number;
  financial_contract_expiry: number;
  financial_discounts: number;
  financial_adjustments: number;
  hr_total_employees: number;
  hr_active_employees: number;
  hr_inactive_employees: number;
  hr_departments: number;
  hr_head_vacancies: number;
  hr_reporting_exceptions: number;
  hr_kpi_pending: number;
  hr_kpi_finalized: number;
  hr_onboarding_in_progress: number;
  hr_unscheduled_employees: number;
  project_total: number;
  project_delivered: number;
  project_in_progress: number;
  project_awaiting_acceptance: number;
  project_pending_products: number;
  project_pending_points: number;
  projects_by_status: Record<string, number>;
  projects_by_client: Record<string, number>;
};

type SummaryWithApprovals = Summary &
  ManagerSummary & {
    pending_approvals: number;
    priority_by_status: Record<string, Record<string, number>>;
  };

type TicketDrilldownFilters = Partial<
  Record<
    | "assigned_user_id"
    | "open_only"
    | "unassigned_only"
    | "strictly_unassigned_only"
    | "priority"
    | "breached_only"
    | "shift_handover_only"
    | "due_soon"
    | "status_code"
    | "routing_status"
    | "entitlement_status"
    | "search"
    | "tab"
    | "created_from"
    | "created_to"
    | "resolved_from"
    | "resolved_to"
    | "assigned_from"
    | "assigned_to"
    | "timezone_offset_minutes"
    | "country_id"
    | "zone"
    | "client_id"
    | "location_id"
    | "product_id"
    | "team_id"
    | "engineer_id",
    string
  >
>;

const cards = [
  {
    key: "total_open",
    label: "openTicketsCard",
    icon: <ConfirmationNumber />,
    color: "#2563eb",
  },
  {
    key: "my_open",
    label: "assignedToMe",
    icon: <TaskAlt />,
    color: "#0891b2",
  },
  {
    key: "unassigned",
    label: "unassigned",
    icon: <PersonOff />,
    color: "#64748b",
  },
  {
    key: "critical",
    label: "p1Critical",
    icon: <ErrorOutline />,
    color: "#e11d48",
  },
  {
    key: "breached",
    label: "slaBreached",
    icon: <AssignmentLate />,
    color: "#dc2626",
  },
  {
    key: "due_soon",
    label: "dueInFourHours",
    icon: <Schedule />,
    color: "#d97706",
  },
  {
    key: "shift_handovers",
    label: "shiftHandovers",
    icon: <SwapHoriz />,
    color: "#7c3aed",
  },
] as const;

export function dashboardCardDrilldownFilters(
  key: (typeof cards)[number]["key"],
  userId?: number,
): TicketDrilldownFilters {
  if (key === "total_open") return { open_only: "true" };
  if (key === "my_open")
    return { assigned_user_id: String(userId ?? ""), open_only: "true" };
  if (key === "unassigned")
    return { strictly_unassigned_only: "true", open_only: "true" };
  if (key === "critical") return { priority: "P1", open_only: "true" };
  if (key === "breached") return { breached_only: "true" };
  if (key === "shift_handovers") return { shift_handover_only: "true" };
  return { due_soon: "true" };
}

function BreakdownPanel({
  title,
  values,
  color = "#2563eb",
}: {
  title: string;
  values?: Record<string, number> | null;
  color?: string;
}) {
  const { t } = useTranslation();
  const safeValues = values ?? {};
  const maximum = Math.max(...Object.values(safeValues), 1);
  return (
    <Paper
      sx={{
        ...dashboardTicketCardSx(color),
        p: 2.5,
        height: "100%",
      }}
    >
      <Typography fontWeight={700} mb={2}>
        {title}
      </Typography>
      {!Object.keys(safeValues).length && (
        <Typography color="text.secondary">
          {t("employeeDashboard.noData")}
        </Typography>
      )}
      {Object.entries(safeValues)
        .slice(0, 8)
        .map(([label, count]) => (
          <Box key={label} sx={{ mb: 1.5 }}>
            <Stack direction="row">
              <Typography variant="body2" noWrap title={label}>
                {label}
              </Typography>
              <Typography
                variant="body2"
                sx={{ marginInlineStart: "auto" }}
                fontWeight={700}
              >
                {count}
              </Typography>
            </Stack>
            <LinearProgress
              variant="determinate"
              value={(count * 100) / maximum}
              sx={{
                mt: 0.6,
                height: 7,
                borderRadius: 4,
                bgcolor: "action.hover",
                "& .MuiLinearProgress-bar": { bgcolor: color },
              }}
            />
          </Box>
        ))}
    </Paper>
  );
}

function TrendChart({
  inflow,
  closures,
}: {
  inflow?: Record<string, number> | null;
  closures?: Record<string, number> | null;
}) {
  const { i18n, t } = useTranslation();
  const safeInflow = inflow ?? {};
  const safeClosures = closures ?? {};
  const days = Object.keys(safeInflow);
  const max = Math.max(
    ...Object.values(safeInflow),
    ...Object.values(safeClosures),
    1,
  );
  const points = (values: Record<string, number>) =>
    days
      .map(
        (day, i) =>
          `${(i * 100) / Math.max(days.length - 1, 1)},${92 - ((values[day] ?? 0) * 78) / max}`,
      )
      .join(" ");
  return (
    <Paper
      sx={{
        ...dashboardTicketCardSx("#0891b2"),
        p: 2.5,
        height: "100%",
      }}
    >
      <Stack direction="row" alignItems="center">
        <Box>
          <Typography fontWeight={700}>
            {t("employeeDashboard.volumeTrend")}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("employeeDashboard.trendHint")}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} sx={{ marginInlineStart: "auto" }}>
          <Chip
            size="small"
            label={t("employeeDashboard.created")}
            color="primary"
          />
          <Chip
            size="small"
            label={t("employeeDashboard.completed")}
            color="success"
          />
        </Stack>
      </Stack>
      <Box sx={{ mt: 2, height: 190 }}>
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          width="100%"
          height="160"
          aria-label={t("employeeDashboard.ticketTrend")}
        >
          <line x1="0" y1="92" x2="100" y2="92" stroke="#cbd5e1" />
          <polyline
            points={points(safeInflow)}
            fill="none"
            stroke="#2563eb"
            strokeWidth="2.2"
            vectorEffect="non-scaling-stroke"
          />
          <polyline
            points={points(safeClosures)}
            fill="none"
            stroke="#16a34a"
            strokeWidth="2.2"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <Stack direction="row" justifyContent="space-between">
          {days.map((day) => (
            <Typography key={day} variant="caption" color="text.secondary">
              {new Date(`${day}T00:00:00`).toLocaleDateString(
                i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                {
                  weekday: "short",
                },
              )}
            </Typography>
          ))}
        </Stack>
      </Box>
    </Paper>
  );
}

const percentColor = (value: number | null) =>
  value === null
    ? "text.secondary"
    : value >= 95
      ? "success.main"
      : value >= 85
        ? "warning.main"
        : "error.main";

function StatusPie({
  values,
  onStatus,
  title,
}: {
  values?: Record<string, number> | null;
  onStatus?: (status: string) => void;
  title?: string;
}) {
  const { t } = useTranslation();
  const entries = Object.entries(values ?? {}).filter(([, value]) => value > 0);
  const total = entries.reduce((sum, [, value]) => sum + value, 0);
  const colors = [
    "#2563eb",
    "#0891b2",
    "#7c3aed",
    "#16a34a",
    "#f59e0b",
    "#e11d48",
    "#64748b",
  ];
  let cursor = 0;
  const gradient = entries
    .map(([, value], index) => {
      const start = cursor;
      cursor += (value * 100) / Math.max(total, 1);
      return `${colors[index % colors.length]} ${start}% ${cursor}%`;
    })
    .join(", ");
  return (
    <Paper
      sx={{
        ...dashboardTicketCardSx("#7c3aed"),
        p: 2.5,
        height: "100%",
      }}
    >
      <Typography fontWeight={700}>
        {title ?? t("employeeDashboard.ticketsByStatus")}
      </Typography>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems="center"
        spacing={3}
        mt={2}
      >
        <Box
          sx={{
            width: 150,
            height: 150,
            borderRadius: "50%",
            background: total ? `conic-gradient(${gradient})` : "#e2e8f0",
            position: "relative",
            flexShrink: 0,
            display: "grid",
            placeItems: "center",
            "&::after": {
              content: '""',
              position: "absolute",
              inset: 34,
              borderRadius: "50%",
              bgcolor: "background.paper",
            },
          }}
        >
          <Typography fontWeight={900} sx={{ zIndex: 1 }}>
            {total}
          </Typography>
        </Box>
        <Stack spacing={0.75}>
          {entries.slice(0, 7).map(([status, count], index) => (
            <Stack
              component="button"
              type="button"
              onClick={() => onStatus?.(status)}
              key={status}
              direction="row"
              alignItems="center"
              spacing={1}
              sx={{
                border: 0,
                bgcolor: "transparent",
                cursor: onStatus ? "pointer" : "default",
                color: "text.primary",
                p: 0.5,
                borderRadius: 1,
                "&:hover": { bgcolor: "action.hover" },
              }}
            >
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  bgcolor: colors[index % colors.length],
                }}
              />
              <Typography variant="body2">
                {status.replaceAll("_", " ")}: <b>{count}</b>
              </Typography>
            </Stack>
          ))}
        </Stack>
      </Stack>
    </Paper>
  );
}

function PriorityStatus({
  data,
  onOpen,
}: {
  data: SummaryWithApprovals;
  onOpen: (status: string, priority: string) => void;
}) {
  const { t } = useTranslation();
  const priorities = ["P1", "P2", "P3", "P4"];
  const colors = ["#dc2626", "#f59e0b", "#2563eb", "#64748b"];
  return (
    <Paper
      sx={{
        ...dashboardTicketCardSx("#dc2626"),
        p: 2.5,
        height: "100%",
      }}
    >
      <Typography fontWeight={700}>
        {t("employeeDashboard.priorityByStatus")}
      </Typography>
      <Stack spacing={1.2} mt={2}>
        {Object.entries(data.by_status).map(([status, total]) => (
          <Box key={status}>
            <Stack direction="row">
              <Typography variant="caption">
                {status.replaceAll("_", " ")}
              </Typography>
              <Typography
                variant="caption"
                sx={{ marginInlineStart: "auto" }}
                fontWeight={700}
              >
                {total}
              </Typography>
            </Stack>
            <Stack
              direction="row"
              height={18}
              borderRadius={1}
              overflow="hidden"
            >
              {priorities.map((priority, index) => {
                const count = data.priority_by_status[status]?.[priority] ?? 0;
                return count > 0 ? (
                  <Box
                    component="button"
                    type="button"
                    key={priority}
                    title={`${priority}: ${count}`}
                    onClick={() => onOpen(status, priority)}
                    sx={{
                      border: 0,
                      width: `${(count * 100) / Math.max(total, 1)}%`,
                      bgcolor: colors[index],
                      cursor: "pointer",
                    }}
                  />
                ) : null;
              })}
            </Stack>
          </Box>
        ))}
      </Stack>
    </Paper>
  );
}

function CustomerMetricCard({title,period,rows,onClient,error,loading,unit}:{title:string;period:string;rows:{key:string;label:string;value:number}[];onClient:(id:string)=>void;error:boolean;loading:boolean;unit:string}) {
  const [clientId,setClientId]=useState('');
  const shown=clientId?rows.filter(row=>row.key===clientId):rows.slice(0,10);
  const maximum=Math.max(...shown.map(row=>row.value),1);
  return <Card sx={{p:2.5,height:'100%'}}><Typography variant="h6" fontWeight={800}>{title}</Typography><Typography variant="caption" color="text.secondary">{period}</Typography><TextField select fullWidth size="small" label="Client" value={clientId} onChange={event=>setClientId(event.target.value)} sx={{mt:2}}><MenuItem value="">All clients</MenuItem>{rows.map(row=><MenuItem key={row.key} value={row.key}>{row.label}</MenuItem>)}</TextField>{error&&<Alert severity="error">Could not load customer measures.</Alert>}{loading&&<Typography sx={{mt:2}}>Loading…</Typography>}{!loading&&!error&&!rows.length&&<Typography color="text.secondary" sx={{mt:2}}>No customer work hours or tickets in this period.</Typography>}<Stack spacing={1.5} mt={2}>{shown.map(row=><Box key={row.key} component="button" onClick={()=>onClient(row.key)} sx={{width:'100%',border:0,bgcolor:'transparent',color:'text.primary',cursor:'pointer',textAlign:'left',p:0}}><Stack direction="row" justifyContent="space-between" gap={1}><Typography noWrap title={row.label}>{row.label}</Typography><Typography fontWeight={800} whiteSpace="nowrap">{row.value} {unit}</Typography></Stack><Box sx={{height:12,bgcolor:'action.hover',borderRadius:6,overflow:'hidden',mt:.5}}><Box height="100%" width={`${row.value/maximum*100}%`} bgcolor="primary.main" borderRadius={6}/></Box></Box>)}</Stack></Card>
}

export function DashboardPage({
  visibleWidgetCodes,
  dashboardType = "EXECUTIVE",
}: {
  visibleWidgetCodes?: ReadonlySet<string>;
  dashboardType?: "EXECUTIVE" | "TOP_MANAGEMENT";
} = {}) {
  const { t } = useTranslation();
  const defaultPeriod = currentMonthToDate();
  const [dashboardSection, setDashboardSection] = useState("OVERVIEW");
  const { hasPermission, user } = useAuth();
  const layoutKey = `supporthub-dashboard-layout-${user?.id ?? "anonymous"}-${dashboardType}`;
  const [personalLayout, setPersonalLayout] = useState<Record<string, { order: number; width: number }>>({});
  const [layoutDirty, setLayoutDirty] = useState(false);
  const [draggedWidget, setDraggedWidget] = useState<string | null>(null);
  useEffect(() => {
    try { setPersonalLayout(JSON.parse(localStorage.getItem(layoutKey) || "{}")); }
    catch { setPersonalLayout({}); }
    setLayoutDirty(false);
  }, [layoutKey]);
  function widgetWidth(code: string, fallback: number) { return personalLayout[code]?.width ?? fallback; }
  function resizeWidget(code: string, fallback: number) {
    const sizes = [4, 6, 8, 12];
    const current = widgetWidth(code, fallback);
    setPersonalLayout(value => ({ ...value, [code]: { order: value[code]?.order ?? 0, width: sizes[(Math.max(0, sizes.indexOf(current)) + 1) % sizes.length] } }));
    setLayoutDirty(true);
  }
  function moveWidget(target: string, codes: string[], defaults: Record<string, number>) {
    if (!draggedWidget || draggedWidget === target) return;
    const from = codes.indexOf(draggedWidget), to = codes.indexOf(target);
    if (from < 0 || to < 0) return;
    codes.splice(to, 0, codes.splice(from, 1)[0]);
    setPersonalLayout(value => ({ ...value, ...Object.fromEntries(codes.map((code, order) => [code, { order, width: value[code]?.width ?? defaults[code] }])) }));
    setDraggedWidget(null);
    setLayoutDirty(true);
  }
  function layoutControls(code: string, fallback: number) { return <Stack direction="row" sx={{ position: "absolute", zIndex: 5, top: 8, insetInlineEnd: 8, bgcolor: "background.paper", borderRadius: 1, boxShadow: 2 }}><IconButton size="small" draggable onDragStart={event => { event.stopPropagation(); setDraggedWidget(code); }} onDragEnd={() => setDraggedWidget(null)} aria-label={`Move ${code}`} title="Drag to move"><DragIndicator fontSize="small" /></IconButton><IconButton size="small" onClick={() => resizeWidget(code, fallback)} aria-label={`Resize ${code}`} title="Resize widget"><AspectRatio fontSize="small" /></IconButton></Stack>; }
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [agent, setAgent] = useState("ALL");
  const [product, setProduct] = useState("ALL");
  const [dashboardFilters, setDashboardFilters] = useState<
    Record<string, string>
  >({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [repeatedIssuesPage, setRepeatedIssuesPage] = useState(0);
  const [showAllRepeatedIssues, setShowAllRepeatedIssues] = useState(false);
  const [month, setMonth] = useState(() => serverDateInput().slice(0, 7));
  const [periodMode, setPeriodMode] = useState<"MONTH" | "QUARTER" | "CUSTOM">(
    "CUSTOM",
  );
  const [reportYear, setReportYear] = useState(() => new Date().getFullYear());
  const [quarter, setQuarter] = useState(
    () => Math.floor(new Date().getMonth() / 3) + 1,
  );
  const [dateFrom, setDateFrom] = useState(() => defaultPeriod.dateFrom);
  const [dateTo, setDateTo] = useState(() => defaultPeriod.dateTo);
  const [dateBasis, setDateBasis] = useState<
    "CREATION" | "RESOLUTION" | "ASSIGNMENT"
  >("CREATION");
  const [activityDialog, setActivityDialog] = useState(false);
  const [celebrate, setCelebrate] = useState(false);
  const [exportingHr, setExportingHr] = useState(false);
  const [exportError, setExportError] = useState("");
  const periodParams =
    periodMode === "MONTH"
      ? { kpi_month: month }
      : periodMode === "QUARTER"
        ? { kpi_quarter: `${reportYear}-Q${quarter}` }
        : { date_from: dateFrom, date_to: dateTo, date_basis: dateBasis };
  const query = useQuery({
    queryKey: [
      "dashboard-summary",
      user?.default_dashboard_scope,
      periodMode,
      month,
      reportYear,
      quarter,
      dateFrom,
      dateTo,
      dateBasis,
      dashboardFilters,
    ],
    queryFn: async () =>
      (
        await api.get<SummaryWithApprovals>("/dashboards/summary", {
          timeout: DASHBOARD_ANALYSIS_TIMEOUT_MS,
          params: {
            ...periodParams,
            ...dashboardFilters,
            dashboard_scope: user?.default_dashboard_scope,
            timezone_offset_minutes: -new Date().getTimezoneOffset(),
          },
        })
      ).data,
    staleTime: 120_000,
    refetchInterval: 300_000,
    refetchIntervalInBackground: false,
    enabled:
      periodMode !== "CUSTOM" ||
      Boolean(dateFrom && dateTo && dateFrom <= dateTo),
  });
  const topAgentsPeriod = currentMonthToDate();
  const periodEnd = (year: number, monthIndex: number) => {
    const day = new Date(year, monthIndex + 1, 0);
    return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
  };
  const consumptionDates = periodMode === "CUSTOM"
    ? { from: dateFrom, to: dateTo }
    : periodMode === "MONTH"
      ? { from: `${month}-01`, to: periodEnd(Number(month.slice(0, 4)), Number(month.slice(5, 7)) - 1) }
      : (() => {
          const startMonth = (quarter - 1) * 3;
          return {
            from: `${reportYear}-${String(startMonth + 1).padStart(2, "0")}-01`,
            to: periodEnd(reportYear, startMonth + 2),
          };
        })();
  const consumptionQuery = useQuery({
    queryKey: ["support-consumption", consumptionDates.from, consumptionDates.to, dashboardFilters],
    queryFn: async () => (await api.get<{ dashboards: Record<string, { code: string; value: { key: string; label: string; value: number }[] }[]> }>(
      "/management-dashboards/analytics",
      { params: { date_from: consumptionDates.from, date_to: consumptionDates.to, ...dashboardFilters, timezone_offset_minutes: -new Date().getTimezoneOffset() }, timeout: DASHBOARD_ANALYSIS_TIMEOUT_MS },
    )).data.dashboards.EXECUTIVE_OVERVIEW.filter((item) => ["support_consumption", "customer_workhours"].includes(item.code)),
    enabled: hasPermission("dashboard.executive") && Boolean(consumptionDates.from && consumptionDates.to && consumptionDates.from <= consumptionDates.to),
    staleTime: 120_000,
  });
  const topAgentsQuery = useQuery({
    queryKey: [
      "top-support-agents",
      user?.default_dashboard_scope,
      topAgentsPeriod.dateFrom,
      topAgentsPeriod.dateTo,
    ],
    queryFn: async () =>
      (
        await api.get<TopSupportAgentsResponse>(
          "/dashboards/top-support-agents",
          {
            params: {
              timezone_offset_minutes: -new Date().getTimezoneOffset(),
              limit: 3,
            },
          },
        )
      ).data,
    staleTime: 300_000,
    refetchInterval: 600_000,
  });
  const filterMetadata = useQuery({
    queryKey: ["dashboard-filter-metadata"],
    queryFn: async () =>
      (
        await api.get<DashboardFilterMetadata>("/dashboards/filter-metadata", {
          timeout: DASHBOARD_ANALYSIS_TIMEOUT_MS,
        })
      ).data,
    staleTime: 300_000,
  });
  const dashboardConfig = useQuery({
    queryKey: ["dashboard-config", dashboardType],
    queryFn: async () =>
      (
        await api.get<{ widgets: Widget[] }>("/dashboards/config", {
          params: { dashboard_type: dashboardType },
        })
      ).data,
    staleTime: 300_000,
  });
  const configuredWidgets = (dashboardConfig.data?.widgets ?? []).filter(
    (widget) =>
      !visibleWidgetCodes || visibleWidgetCodes.has(widget.widget_code),
  );
  const onlineEngineers = useQuery({
    queryKey: ["dashboard-online-engineers"],
    queryFn: async () =>
      (
        await api.get<OnlineEngineer[]>("/dashboards/online-engineers", {
          timeout: DASHBOARD_ANALYSIS_TIMEOUT_MS,
        })
      ).data,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    enabled: hasPermission("dashboard.online_engineers.view"),
  });
  const logActivity = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/agent-activities", payload),
    onSuccess: async () => {
      setActivityDialog(false);
      await query.refetch();
    },
  });
  const topSupportAgents = useMemo(
    () => selectTopSupportAgents(topAgentsQuery.data?.agents ?? []),
    [topAgentsQuery.data?.agents],
  );
  useEffect(() => {
    const section = params.get("report");
    if (section)
      window.setTimeout(
        () =>
          document
            .getElementById(`${section}-report`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" }),
        50,
      );
  }, [params]);
  useEffect(() => {
    const winner = topSupportAgents[0];
    if (!winner || winner.user_id !== user?.id || winner.resolved <= 0) return;
    const key = `top-agent-celebrated-${topAgentsQuery.data?.date_from}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "true");
    setCelebrate(true);
    const timer = window.setTimeout(() => setCelebrate(false), 5000);
    return () => window.clearTimeout(timer);
  }, [topAgentsQuery.data?.date_from, topSupportAgents, user?.id]);
  const agentRows = useMemo(
    () =>
      (query.data?.agent_kpis ?? []).filter(
        (row) => agent === "ALL" || row.agent === agent,
      ),
    [agent, query.data],
  );
  const productRows = useMemo(
    () =>
      (query.data?.product_kpis ?? []).filter(
        (row) => product === "ALL" || row.product === product,
      ),
    [product, query.data],
  );
  async function exportTickets() {
    const response = await api.get("/reports/tickets.csv", {
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "tickets.csv";
    link.click();
    URL.revokeObjectURL(url);
  }
  async function exportAgentKpis() {
    setExportError("");
    setExportingHr(true);
    try {
      const response = await api.get<Blob>("/reports/agent-kpis.xlsx", {
        params: periodParams,
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      const label =
        periodMode === "MONTH"
          ? month
          : periodMode === "QUARTER"
            ? `${reportYear}-Q${quarter}`
            : `${dateFrom}-to-${dateTo}`;
      link.href = url;
      link.download = `Millensys-Agent-KPI-${label}.xlsx`;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setExportError(t("employeeDashboard.hrExportFailed"));
    } finally {
      setExportingHr(false);
    }
  }
  function ticketPeriodFilters(): TicketDrilldownFilters {
    let from = dateFrom;
    let to = dateTo;
    if (periodMode === "MONTH") {
      const [year, selectedMonth] = month.split("-").map(Number);
      from = `${month}-01`;
      to = serverDateInput(new Date(year, selectedMonth, 0));
    } else if (periodMode === "QUARTER") {
      const firstMonth = (quarter - 1) * 3;
      from = new Date(Date.UTC(reportYear, firstMonth, 1))
        .toISOString()
        .slice(0, 10);
      to = new Date(Date.UTC(reportYear, firstMonth + 3, 0))
        .toISOString()
        .slice(0, 10);
    }
    const prefix =
      dateBasis === "RESOLUTION"
        ? "resolved"
        : dateBasis === "ASSIGNMENT"
          ? "assigned"
          : "created";
    return {
      [`${prefix}_from`]: from,
      [`${prefix}_to`]: to,
      timezone_offset_minutes: String(-new Date().getTimezoneOffset()),
      ...dashboardFilters,
      ...(user?.default_dashboard_scope === "MY"
        ? { assigned_user_id: String(user.id) }
        : {}),
    };
  }
  function openTickets(filters: TicketDrilldownFilters = {}, newTab = false) {
    const route = `/tickets?${new URLSearchParams({ ...ticketPeriodFilters(), ...filters })}`;
    if (!newTab) return navigate(route);
    const tab = window.open(`/SupportHub${route}`, "_blank");
    if (tab) tab.opener = null;
  }
  function openCard(key: (typeof cards)[number]["key"]) {
    openTickets(dashboardCardDrilldownFilters(key, user?.id), true);
  }
  if (query.isLoading)
    return (
      <Box sx={{ minHeight: 400, display: "grid", placeItems: "center" }}>
        <CircularProgress />
      </Box>
    );
  if (query.isError || !query.data) {
    const denied =
      axios.isAxiosError(query.error) && query.error.response?.status === 403;
    const unavailable =
      axios.isAxiosError(query.error) &&
      (query.error.response?.status ?? 0) >= 500;
    return (
      <Alert severity="error">
        {t(
          denied
            ? "employeeDashboard.denied"
            : unavailable
              ? "employeeDashboard.unavailable"
              : "employeeDashboard.loadFailed",
        )}
      </Alert>
    );
  }
  const data = query.data;
  const repeatedIssueRows = Object.entries(data.top_repeated_issues ?? {});
  const repeatedIssuesPageCount = Math.max(
    1,
    Math.ceil(repeatedIssueRows.length / 10),
  );
  const visibleRepeatedIssues = showAllRepeatedIssues
    ? repeatedIssueRows
    : repeatedIssueRows.slice(
        repeatedIssuesPage * 10,
        repeatedIssuesPage * 10 + 10,
      );
  return (
    <Stack
      spacing={2.5}
      sx={{
        bgcolor: "background.default",
        m: -3,
        p: { xs: 2, md: 3 },
        minHeight: "calc(100vh - 64px)",
      }}
    >
      <InactiveClientsKpi />
      {data.total_tickets === 0 && (
        <Alert severity="info">{t("employeeDashboard.emptyScope")}</Alert>
      )}
      {(hasPermission("dashboard.customize.own") ||
        hasPermission("dashboard.manage_widgets")) && (
        <Stack direction="row" justifyContent="flex-end">
          <DashboardCustomizer dashboardType={dashboardType} />
        </Stack>
      )}
      {dashboardSection === "OVERVIEW" && <Box textAlign="right"><Button size="small" startIcon={<Save />} disabled={!layoutDirty} onClick={() => { localStorage.setItem(layoutKey, JSON.stringify(personalLayout)); setLayoutDirty(false); }}>Save layout</Button></Box>}
      <Paper sx={{ p: 2, borderRadius: 3 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={1}
          mb={1.5}
          alignItems={{ md: "center" }}
        >
          <Box>
            <Typography fontWeight={800}>
              {t("employeeDashboard.filters")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t("employeeDashboard.filtersHint")}
            </Typography>
          </Box>
          <Chip
            size="small"
            label={t("employeeDashboard.active", {
              count: Object.values(dashboardFilters).filter(Boolean).length + 2,
            })}
          />
          <Button
            size="small"
            onClick={() => setFiltersOpen((value) => !value)}
            endIcon={filtersOpen ? <ExpandLess /> : <ExpandMore />}
          >
            {filtersOpen
              ? t("employeeDashboard.collapse")
              : t("employeeDashboard.expand")}
          </Button>
          <Button
            size="small"
            sx={{ marginInlineStart: { md: "auto" } }}
            onClick={() => {
              const currentMonth = currentMonthToDate();
              setDateFrom(currentMonth.dateFrom);
              setDateTo(currentMonth.dateTo);
              setPeriodMode("CUSTOM");
              setDashboardFilters({});
            }}
          >
            {t("employeeDashboard.reset")}
          </Button>
        </Stack>
        <Collapse in={filtersOpen}>
          <Grid container spacing={1}>
            <Grid size={{ xs: 12, sm: 6, lg: 2 }}>
              <TextField
                fullWidth
                size="small"
                type="date"
                label={t("employeeDashboard.fromDate")}
                value={dateFrom}
                onChange={(event) => {
                  setDateFrom(event.target.value);
                  setPeriodMode("CUSTOM");
                }}
                slotProps={{
                  inputLabel: { shrink: true },
                  htmlInput: { max: dateTo },
                }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, lg: 2 }}>
              <TextField
                fullWidth
                size="small"
                type="date"
                label={t("employeeDashboard.toDate")}
                value={dateTo}
                onChange={(event) => {
                  setDateTo(event.target.value);
                  setPeriodMode("CUSTOM");
                }}
                slotProps={{
                  inputLabel: { shrink: true },
                  htmlInput: { min: dateFrom },
                }}
              />
            </Grid>
            {[
              ["country_id", "Country"],
              ["zone", "Zone"],
              ["client_id", "Client"],
              ["location_id", "Location"],
              ["product_id", "Product"],
              ["team_id", "Team"],
              ["engineer_id", "Engineer"],
            ].map(([name, label]) => (
              <Grid key={name} size={{ xs: 12, sm: 6, lg: 1.3 }}>
                <TextField
                  fullWidth
                  select
                  size="small"
                  label={label}
                  value={dashboardFilters[name] ?? ""}
                  onChange={(event) =>
                    setDashboardFilters((current) => ({
                      ...current,
                      [name]: event.target.value,
                      ...(name === "client_id" ? { location_id: "" } : {}),
                    }))
                  }
                >
                  <MenuItem value="">{t("employeeDashboard.all")}</MenuItem>
                  {name === "zone"
                    ? (filterMetadata.data?.zones ?? []).map((value) => (
                        <MenuItem key={value} value={value}>
                          {value}
                        </MenuItem>
                      ))
                    : (
                        (filterMetadata.data?.[
                          `${name.replace("_id", "")}s` as keyof DashboardFilterMetadata
                        ] as DashboardFilterOption[] | undefined) ?? []
                      )
                        .filter(
                          (item) =>
                            name !== "location_id" ||
                            !dashboardFilters.client_id ||
                            item.client_id ===
                              Number(dashboardFilters.client_id),
                        )
                        .map((item) => (
                          <MenuItem key={item.id} value={item.id}>
                            {item.name}
                          </MenuItem>
                        ))}
                </TextField>
              </Grid>
            ))}
          </Grid>
        </Collapse>
        {dateFrom > dateTo && (
          <Alert severity="warning" sx={{ mt: 1 }}>
            {t("employeeDashboard.invalidDates")}
          </Alert>
        )}
      </Paper>
      {dashboardSection === "OVERVIEW" &&
        hasPermission("dashboard.online_engineers.view") && (
          <Paper sx={{ p: 2.5, borderRadius: 3 }}>
            <Stack direction="row" alignItems="center" mb={2}>
              <Box flexGrow={1}>
                <Typography variant="h6" fontWeight={800}>
                  {t("employeeDashboard.onlineEngineers")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("employeeDashboard.onlineHint")}
                </Typography>
              </Box>
              <Chip
                color="success"
                label={t("employeeDashboard.onlineCount", {
                  count: onlineEngineers.data?.length ?? 0,
                })}
              />
            </Stack>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(2,1fr)",
                  lg: "repeat(4,1fr)",
                },
                gap: 1,
              }}
            >
              {onlineEngineers.data?.map((engineer) => (
                <Paper
                  component="button"
                  type="button"
                  variant="outlined"
                  key={engineer.user_id}
                  onClick={() =>
                    navigate(
                      `/tickets?assigned_user_id=${engineer.user_id}&status_code=IN_PROGRESS`,
                    )
                  }
                  sx={{
                    ...dashboardTicketCardSx(
                      engineer.status === "AVAILABLE" ? "#22c55e" : "#f59e0b",
                      true,
                    ),
                    p: 1.25,
                    textAlign: "left",
                    color: "text.primary",
                  }}
                >
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <Box
                      sx={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        bgcolor:
                          engineer.status === "AVAILABLE"
                            ? "success.main"
                            : "warning.main",
                        flexShrink: 0,
                      }}
                    />
                    <Box flexGrow={1}>
                      <Typography fontWeight={800}>
                        {engineer.engineer}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {t("employeeDashboard.online")} ·{" "}
                        {engineer.active_ticket_count
                          ? t("employeeDashboard.inProgress", {
                              count: engineer.active_ticket_count,
                            })
                          : t("employeeDashboard.available")}
                      </Typography>
                    </Box>
                    <Chip
                      size="small"
                      label={engineer.active_ticket_count}
                      color={
                        engineer.active_ticket_count ? "warning" : "success"
                      }
                    />
                  </Stack>
                  {engineer.active_ticket_count > 0 && (
                    <Stack direction="row" gap={0.5} mt={1} flexWrap="wrap">
                      {Object.entries(engineer.tickets_by_priority).map(
                        ([priority, count]) => (
                          <Chip
                            key={priority}
                            size="small"
                            color={
                              priority === "P1"
                                ? "error"
                                : priority === "P2"
                                  ? "warning"
                                  : priority === "P3"
                                    ? "info"
                                    : "default"
                            }
                            label={`${priority}: ${count}`}
                          />
                        ),
                      )}
                    </Stack>
                  )}
                </Paper>
              ))}
            </Box>
            {!onlineEngineers.data?.length && (
              <Typography color="text.secondary">
                {t("employeeDashboard.noHeartbeat")}
              </Typography>
            )}
          </Paper>
        )}
      {celebrate && (
        <Box
          aria-label={t("employeeDashboard.celebration")}
          sx={{
            position: "fixed",
            inset: 0,
            zIndex: 2000,
            pointerEvents: "none",
            overflow: "hidden",
          }}
        >
          <Typography
            sx={{
              position: "absolute",
              top: "18%",
              width: "100%",
              textAlign: "center",
              fontSize: { xs: 30, md: 48 },
              fontWeight: 900,
              color: "#f59e0b",
              textShadow: "0 2px 8px white",
              animation: "winnerPop 1s ease-out",
            }}
          >
            {t("employeeDashboard.topEngineer")}
          </Typography>
          {Array.from({ length: 36 }, (_, index) => (
            <Box
              key={index}
              sx={{
                position: "absolute",
                left: `${(index * 37) % 100}%`,
                top: -20,
                width: 10,
                height: 16,
                bgcolor: [
                  "#ef4444",
                  "#3b82f6",
                  "#f59e0b",
                  "#22c55e",
                  "#a855f7",
                ][index % 5],
                animation: `confettiFall ${2 + (index % 3)}s linear ${(index % 8) * 0.1}s forwards`,
                transform: `rotate(${index * 29}deg)`,
                "@keyframes confettiFall": {
                  to: {
                    transform: `translateY(110vh) rotate(${720 + index * 29}deg)`,
                    opacity: 0.5,
                  },
                },
                "@keyframes winnerPop": {
                  from: { transform: "scale(.4)", opacity: 0 },
                  to: { transform: "scale(1)", opacity: 1 },
                },
              }}
            />
          ))}
        </Box>
      )}
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          borderRadius: 3,
          background: "linear-gradient(120deg, #0f3970, #0b7285)",
          color: "white",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          alignItems={{ md: "center" }}
          gap={2}
        >
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h4" fontWeight={800}>
              {t("employeeDashboard.supportIntelligence")}
            </Typography>
            <Typography sx={{ opacity: 0.82 }}>
              {t("employeeDashboard.supportSubtitle")}
            </Typography>
          </Box>
          <Chip
            label={t("employeeDashboard.updated", {
              time: new Date(query.dataUpdatedAt).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              }),
            })}
            sx={{ color: "white", bgcolor: "rgba(255,255,255,.15)" }}
          />
          <Button
            color="inherit"
            startIcon={<Refresh />}
            onClick={() => query.refetch()}
          >
            {t("employeeDashboard.refresh")}
          </Button>
          <Button color="inherit" onClick={() => navigate("/tickets")}>
            {t("employeeDashboard.ticketQueue")}
          </Button>
          {hasPermission("report.export") && (
            <Button
              variant="contained"
              color="inherit"
              sx={{ color: "#0f3970" }}
              onClick={exportTickets}
            >
              {t("employeeDashboard.export")}
            </Button>
          )}
        </Stack>
      </Paper>
      <Paper sx={{ px: 1, borderRadius: 3 }}>
        <Tabs
          value={dashboardSection}
          onChange={(_, value) => setDashboardSection(value)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab value="OVERVIEW" label={t("employeeDashboard.overview")} />
          <Tab value="DETAILS" label={t("employeeDashboard.details")} />
        </Tabs>
      </Paper>
      {dashboardSection === "OVERVIEW" &&
        (hasPermission("entitlement_approval.view") ||
          hasPermission("dashboard.manager")) && (
          <Card
            component="button"
            onClick={() =>
              openTickets({
                tab: "approvals",
                entitlement_status: "PENDING_APPROVAL",
              })
            }
            elevation={0}
            sx={{
              ...dashboardTicketCardSx(
                (data as SummaryWithApprovals).pending_approvals
                  ? "#f59e0b"
                  : "#22c55e",
                true,
              ),
              width: { xs: "100%", sm: 300 },
              textAlign: "left",
            }}
          >
            <CardContent>
              <Stack direction="row" alignItems="center">
                <Approval
                  color={
                    (data as SummaryWithApprovals).pending_approvals
                      ? "warning"
                      : "success"
                  }
                />
                <Typography
                  variant="h4"
                  fontWeight={800}
                  sx={{ marginInlineStart: "auto" }}
                >
                  {(data as SummaryWithApprovals).pending_approvals}
                </Typography>
              </Stack>
              <Typography fontWeight={700} mt={1}>
                {t("employeeDashboard.awaitingApproval")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t("employeeDashboard.openApprovalQueue")}
              </Typography>
            </CardContent>
          </Card>
        )}
      {dashboardSection === "OVERVIEW" && (
        <Grid container spacing={2}>
          {cards
            .filter((card) =>
              configuredWidgets.some(
                (widget) => widget.widget_code === card.key,
              ),
            )
            .sort((a, b) => (personalLayout[a.key]?.order ?? cards.indexOf(a)) - (personalLayout[b.key]?.order ?? cards.indexOf(b)))
            .map((card) => (
              <Grid key={card.key} size={{ xs: 12, sm: 6, lg: widgetWidth(card.key, 4) }} onDragOver={event => event.preventDefault()} onDrop={() => moveWidget(card.key, cards.filter(item => configuredWidgets.some(widget => widget.widget_code === item.key)).sort((a, b) => (personalLayout[a.key]?.order ?? cards.indexOf(a)) - (personalLayout[b.key]?.order ?? cards.indexOf(b))).map(item => item.key), Object.fromEntries(cards.map(item => [item.key, 4])))} sx={{ position: "relative" }}>
                {layoutControls(card.key, 4)}
                <Card
                  component="button"
                  onClick={() => openCard(card.key)}
                  elevation={0}
                  sx={{
                    ...dashboardTicketCardSx(card.color, true),
                    width: "100%",
                    textAlign: "left",
                    height: "100%",
                  }}
                >
                  <CardContent>
                    <Stack direction="row" alignItems="center">
                      <Box
                        sx={{
                          display: "grid",
                          placeItems: "center",
                          p: 1,
                          borderRadius: 2,
                          color: card.color,
                          bgcolor: `${card.color}15`,
                        }}
                      >
                        {card.icon}
                      </Box>
                      <TrendingUp
                        sx={{
                          marginInlineStart: "auto",
                          color: "#cbd5e1",
                          fontSize: 18,
                        }}
                      />
                    </Stack>
                    <Typography variant="h4" fontWeight={800} mt={1.5}>
                      {data[card.key]}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t(`employeeDashboard.${card.label}`)} ·{" "}
                      {t("employeeDashboard.viewDetails")}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
        </Grid>
      )}
      {dashboardSection === "OVERVIEW" && (
        <Grid container spacing={2}>
          {configuredWidgets
            .filter(
              (widget) =>
                !cards.some((card) => card.key === widget.widget_code) &&
                !["service_health", "top_support_agents"].includes(
                  widget.widget_code,
                ),
            )
            .sort((a, b) => (personalLayout[a.widget_code]?.order ?? configuredWidgets.indexOf(a)) - (personalLayout[b.widget_code]?.order ?? configuredWidgets.indexOf(b)))
            .map((widget) => (
              <Grid
                key={widget.widget_code}
                size={{ xs: 12, md: widgetWidth(widget.widget_code, Math.max(4, widget.width)) }}
                onDragOver={event => event.preventDefault()}
                onDrop={() => moveWidget(widget.widget_code, configuredWidgets.filter(item => !cards.some(card => card.key === item.widget_code) && !["service_health", "top_support_agents"].includes(item.widget_code)).sort((a, b) => (personalLayout[a.widget_code]?.order ?? configuredWidgets.indexOf(a)) - (personalLayout[b.widget_code]?.order ?? configuredWidgets.indexOf(b))).map(item => item.widget_code), Object.fromEntries(configuredWidgets.map(item => [item.widget_code, Math.max(4, item.width)])))}
                sx={{ position: "relative" }}
              >
                {layoutControls(widget.widget_code, Math.max(4, widget.width))}
                {widget.widget_code.startsWith("service_") ? (
                  <ServiceManagementWidget
                    category={widget.widget_code === "service_incidents" ? "incidents" : widget.widget_code === "service_change_requests" ? "changes" : "problems"}
                    filters={{ ...dashboardFilters, date_from: dateFrom, date_to: dateTo }}
                  />
                ) : widget.widget_code === "client_hours" ? (
                  <ClientHoursWidget dateFrom={consumptionDates.from} dateTo={consumptionDates.to} clientId={dashboardFilters.client_id ? Number(dashboardFilters.client_id) : undefined} />
                ) : widget.widget_code.startsWith("financial_") ? (
                  <FinancialDashboardWidget
                    code={
                      widget.widget_code as Parameters<
                        typeof FinancialDashboardWidget
                      >[0]["code"]
                    }
                  />
                ) : ["support_consumption", "customer_workhours"].includes(widget.widget_code) ? (
                  <CustomerMetricCard title={widget.widget_code === "customer_workhours" ? "Support work hours per customer" : widget.title} period={`${consumptionDates.from} – ${consumptionDates.to} · ${widget.widget_code === "customer_workhours" ? "approved worklogs or completed SLA time" : "tickets created"}`} rows={consumptionQuery.data?.find(item=>item.code===widget.widget_code)?.value??[]} onClient={id=>openTickets({client_id:id})} error={consumptionQuery.isError} loading={consumptionQuery.isLoading} unit={widget.widget_code === "customer_workhours" ? "h" : "tickets"}/>
                ) : widget.widget_code === "projects_by_status" ? (
                  <StatusPie
                    values={data.projects_by_status}
                    title={widget.title}
                    onStatus={() => navigate("/project-handovers")}
                  />
                ) : widget.widget_code === "projects_by_client" ? (
                  <BreakdownPanel
                    title={widget.title}
                    values={data.projects_by_client}
                    color="#7c3aed"
                  />
                ) : widget.widget_type === "DONUT" ? (
                  <StatusPie
                    values={data.by_status}
                    onStatus={(status) => openTickets({ status_code: status })}
                  />
                ) : widget.widget_type === "STACKED_BAR" ? (
                  <PriorityStatus
                    data={data}
                    onOpen={(status, priority) =>
                      openTickets({ status_code: status, priority })
                    }
                  />
                ) : widget.widget_type === "LINE" ? (
                  <TrendChart
                    inflow={data.inflow_last_7_days}
                    closures={data.closures_last_7_days}
                  />
                ) : (
                  <Card
                    component="button"
                    onClick={() => {
                      if (widget.widget_code.startsWith("financial_"))
                        return navigate("/financial");
                      if (widget.widget_code.startsWith("project_"))
                        return navigate("/project-handovers");
                      if (widget.widget_code.startsWith("hr_kpi_"))
                        return navigate("/kpis");
                      if (widget.widget_code === "hr_onboarding_in_progress")
                        return navigate("/onboarding");
                      if (widget.widget_code.startsWith("hr_"))
                        return navigate("/users");
                      const today = serverDateInput();
                      const filters: TicketDrilldownFilters =
                        widget.widget_code === "closed_today"
                          ? {
                              status_code: "CLOSED",
                              resolved_from: today,
                              resolved_to: today,
                            }
                          : widget.widget_code === "created_today"
                            ? { created_from: today, created_to: today }
                            : widget.widget_code === "department_new"
                              ? { routing_status: "NEW" }
                              : widget.widget_code === "department_in_progress"
                                ? { routing_status: "IN_PROGRESS" }
                                : widget.widget_code === "department_returned"
                                  ? { routing_status: "RETURNED" }
                                  : {};
                      openTickets(filters);
                    }}
                    sx={{
                      ...dashboardTicketCardSx("#2563eb", true),
                      width: "100%",
                      textAlign: "left",
                    }}
                  >
                    <CardContent>
                      <Typography variant="h4" fontWeight={800}>
                        {Number(data[widget.query_code as keyof Summary] ?? 0)}
                      </Typography>
                      <Typography color="text.secondary">
                        {widget.title} · {t("employeeDashboard.viewDetails")}
                      </Typography>
                    </CardContent>
                  </Card>
                )}
              </Grid>
            ))}
        </Grid>
      )}
      {dashboardSection === "DETAILS" && (
        <Paper sx={{ p: 2.5, borderRadius: 3 }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ sm: "center" }}
            mb={2}
          >
            <Box flexGrow={1}>
              <Typography variant="h6" fontWeight={800}>
                {t("employeeDashboard.availableEmployees")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t("employeeDashboard.availableEmployeesHint")}
              </Typography>
            </Box>
            <Chip
              color="success"
              label={t("employeeDashboard.availableCount", {
                count: data.available_employees?.length ?? 0,
              })}
            />
          </Stack>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2,1fr)",
                lg: "repeat(4,1fr)",
              },
              gap: 1.25,
            }}
          >
            {data.available_employees?.map((employee) => (
              <Paper
                variant="outlined"
                key={`${employee.user_id}-${employee.starts_at}`}
                sx={{
                  p: 1.5,
                  borderInlineStart: `5px solid ${employee.shift_color}`,
                  borderRadius: 2,
                }}
              >
                <Typography fontWeight={800}>{employee.employee}</Typography>
                <Typography variant="body2">
                  {employee.shift_name}
                  {employee.team ? ` · ${employee.team}` : ""}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("employeeDashboard.until")}{" "}
                  {new Date(employee.ends_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </Typography>
              </Paper>
            ))}
          </Box>
          {!data.available_employees?.length && (
            <Alert severity="info">
              {t("employeeDashboard.noAvailableEmployees")}
            </Alert>
          )}
        </Paper>
      )}
      {(dashboardSection === "DETAILS" || dashboardSection === "OVERVIEW") && (
        <Grid container spacing={2}>
          {dashboardSection === "DETAILS" && (
            <Grid size={{ xs: 12, lg: 8 }}>
              <TrendChart
                inflow={data.inflow_last_7_days}
                closures={data.closures_last_7_days}
              />
            </Grid>
          )}
          {dashboardSection === "OVERVIEW" &&
            configuredWidgets.some(
              (widget) => widget.widget_code === "service_health",
            ) && (
              <Grid size={{ xs: 12 }}>
                <Paper sx={{ p: 2.5, height: "100%", borderRadius: 3 }}>
                  <Typography fontWeight={700}>
                    {t("employeeDashboard.serviceHealth")}
                  </Typography>
                  <Typography
                    variant="h2"
                    fontWeight={800}
                    color={percentColor(data.sla_compliance_percent)}
                    mt={2}
                  >
                    {data.sla_compliance_percent === null
                      ? "—"
                      : `${data.sla_compliance_percent}%`}
                  </Typography>
                  <Typography color="text.secondary">
                    {t("employeeDashboard.slaCompliance")}
                  </Typography>
                  <Stack direction="row" spacing={3} mt={3}>
                    <Box>
                      <Typography variant="h5" fontWeight={700}>
                        {data.average_resolution_hours ?? "—"}
                        {data.average_resolution_hours !== null && "h"}
                      </Typography>
                      <Typography variant="caption">
                        {t("employeeDashboard.avgDedicatedResolution")}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h5" fontWeight={700}>
                        {data.reopen_rate_percent}%
                      </Typography>
                      <Typography variant="caption">
                        {t("employeeDashboard.reopenRate")}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="h5" fontWeight={700}>
                        {data.active_escalations}
                      </Typography>
                      <Typography variant="caption">
                        {t("employeeDashboard.escalations")}
                      </Typography>
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
            )}
        </Grid>
      )}
      {(dashboardSection === "OVERVIEW" || dashboardSection === "DETAILS") &&
        configuredWidgets.some(
          (widget) => widget.widget_code === "top_support_agents",
        ) && (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper
                sx={{
                  p: 2.5,
                  height: "100%",
                  borderRadius: 3,
                  background: (theme) =>
                    theme.palette.mode === "dark"
                      ? "linear-gradient(145deg, #111b2e, #211d16)"
                      : "linear-gradient(145deg, #fff, #fffbeb)",
                }}
              >
                <Typography fontWeight={800} variant="h6">
                  {t("employeeDashboard.topThreeAgents", {
                    period: `${topAgentsPeriod.dateFrom} to ${topAgentsPeriod.dateTo} (Resolution)`,
                  })}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  {t("employeeDashboard.topThreeHint")}
                </Typography>
                <Stack spacing={1.25}>
                  {topSupportAgents.map((row, index) => (
                    <Paper
                      variant="outlined"
                      key={row.agent}
                      sx={{
                        p: 1.5,
                        borderColor: ["#f59e0b", "#94a3b8", "#b45309"][index],
                        bgcolor:
                          index === 0
                            ? (theme) =>
                                theme.palette.mode === "dark"
                                  ? "rgba(245, 158, 11, 0.12)"
                                  : "#fffbeb"
                            : "background.paper",
                      }}
                    >
                      <Stack direction="row" alignItems="center" spacing={2}>
                        <Typography fontSize={28}>
                          {["🥇", "🥈", "🥉"][index]}
                        </Typography>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography fontWeight={800}>{row.agent}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {t("employeeDashboard.agentResult", {
                              resolved: row.resolved,
                              handled: row.assigned,
                            })}
                          </Typography>
                        </Box>
                        <Chip
                          color={index === 0 ? "warning" : "default"}
                          label={`#${index + 1}`}
                        />
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
                {!topSupportAgents.length && (
                  <Typography color="text.secondary">
                    {t("employeeDashboard.noSupportAgents")}
                  </Typography>
                )}
              </Paper>
            </Grid>
          </Grid>
        )}
      {dashboardSection === "DETAILS" && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <BreakdownPanel
              title={t("employeeDashboard.backlogByProduct")}
              values={data.backlog_by_product}
              color="#7c3aed"
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <BreakdownPanel
              title={t("employeeDashboard.backlogByModule")}
              values={data.backlog_by_module}
              color="#0891b2"
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <BreakdownPanel
              title={t("employeeDashboard.backlogAging")}
              values={data.aging_buckets}
              color="#ea580c"
            />
          </Grid>
        </Grid>
      )}
      {dashboardSection === "OVERVIEW" &&
        hasPermission("dashboard.manager") && (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 7 }}>
              <Paper sx={{ p: 2.5, height: "100%", borderRadius: 3 }}>
                <Stack direction="row" alignItems="center" spacing={1} mb={2}>
                  <Insights color="primary" />
                  <Box>
                    <Typography variant="h6" fontWeight={800}>
                      {t("employeeDashboard.repeatedIssues")}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t("employeeDashboard.repeatedIssuesHint")}
                    </Typography>
                  </Box>
                </Stack>
                {repeatedIssueRows.length ? (
                  <>
                    <TableContainer
                      sx={{ maxHeight: showAllRepeatedIssues ? 440 : "none" }}
                    >
                      <Table size="small" stickyHeader={showAllRepeatedIssues}>
                        <TableHead>
                          <TableRow>
                            <TableCell>#</TableCell>
                            <TableCell>
                              {t("employeeDashboard.issue")}
                            </TableCell>
                            <TableCell align="right">
                              {t("employeeDashboard.ticketCount")}
                            </TableCell>
                            <TableCell align="right">
                              {t("employeeDashboard.action")}
                            </TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {visibleRepeatedIssues.map(
                            ([issue, count], index) => (
                              <TableRow hover key={issue}>
                                <TableCell>
                                  {showAllRepeatedIssues
                                    ? index + 1
                                    : repeatedIssuesPage * 10 + index + 1}
                                </TableCell>
                                <TableCell>
                                  <Typography fontWeight={600}>
                                    {issue}
                                  </Typography>
                                </TableCell>
                                <TableCell align="right">
                                  <Chip
                                    size="small"
                                    color="error"
                                    variant="outlined"
                                    label={count}
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  <Button
                                    size="small"
                                    onClick={() =>
                                      openTickets({ search: issue }, true)
                                    }
                                  >
                                    {t("employeeDashboard.openTickets")}
                                  </Button>
                                </TableCell>
                              </TableRow>
                            ),
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                    <Stack
                      direction="row"
                      gap={1}
                      alignItems="center"
                      justifyContent="flex-end"
                      mt={2}
                    >
                      <Button
                        onClick={() => {
                          setShowAllRepeatedIssues((value) => !value);
                          setRepeatedIssuesPage(0);
                        }}
                      >
                        {showAllRepeatedIssues
                          ? t("employeeDashboard.showTen")
                          : t("employeeDashboard.showAll")}
                      </Button>
                      {!showAllRepeatedIssues && (
                        <>
                          <Button
                            disabled={repeatedIssuesPage === 0}
                            onClick={() =>
                              setRepeatedIssuesPage((value) => value - 1)
                            }
                          >
                            {t("employeeDashboard.previous")}
                          </Button>
                          <Typography variant="body2">
                            {t("employeeDashboard.pageOf", {
                              page: Math.min(
                                repeatedIssuesPage + 1,
                                repeatedIssuesPageCount,
                              ),
                              pages: repeatedIssuesPageCount,
                            })}
                          </Typography>
                          <Button
                            disabled={
                              repeatedIssuesPage + 1 >= repeatedIssuesPageCount
                            }
                            onClick={() =>
                              setRepeatedIssuesPage((value) => value + 1)
                            }
                          >
                            {t("employeeDashboard.next")}
                          </Button>
                        </>
                      )}
                    </Stack>
                  </>
                ) : (
                  <Typography color="text.secondary">
                    {t("employeeDashboard.noRepeatedIssues")}
                  </Typography>
                )}
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, lg: 5 }}>
              <Paper
                sx={{
                  p: 2.5,
                  height: "100%",
                  borderRadius: 3,
                  background: (theme) =>
                    theme.palette.mode === "dark"
                      ? "linear-gradient(145deg,#132238,#18251f)"
                      : "linear-gradient(145deg,#eff6ff,#f0fdf4)",
                }}
              >
                <Typography variant="h6" fontWeight={800}>
                  {t("employeeDashboard.managementFocus")}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  {t("employeeDashboard.managementFocusHint")}
                </Typography>
                <Stack spacing={1.25}>
                  <Alert severity={data.breached ? "error" : "success"}>
                    {data.breached
                      ? `${data.breached} SLA breach${data.breached === 1 ? "" : "es"} require action.`
                      : "No active SLA breaches."}
                  </Alert>
                  <Alert severity={data.critical ? "error" : "info"}>
                    {data.critical
                      ? `${data.critical} critical P1 ticket${data.critical === 1 ? "" : "s"} currently open.`
                      : "No critical P1 backlog."}
                  </Alert>
                  <Alert
                    severity={data.expiring_contracts ? "warning" : "success"}
                  >
                    {data.expiring_contracts
                      ? "At least one contract expires in the next 30 days."
                      : "No contracts expire in the next 30 days."}
                  </Alert>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    <Chip
                      label={`Resolution: ${data.average_resolution_hours ?? "—"}${data.average_resolution_hours == null ? "" : "h"}`}
                    />
                    <Chip label={`Reopen rate: ${data.reopen_rate_percent}%`} />
                    <Chip label={`Escalations: ${data.active_escalations}`} />
                  </Stack>
                </Stack>
              </Paper>
            </Grid>
          </Grid>
        )}
      {dashboardSection === "DETAILS" && hasPermission("dashboard.manager") && (
        <>
          <ManagerOverview data={data} />
          {exportError && (
            <Alert severity="error" onClose={() => setExportError("")}>
              {exportError}
            </Alert>
          )}
          {exportingHr && (
            <LinearProgress aria-label={t("employeeDashboard.preparingHr")} />
          )}
          <Paper sx={{ p: 2.5, borderRadius: 3 }}>
            <Typography variant="h6" fontWeight={800}>
              {t("employeeDashboard.afterShiftWork")}
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={2}>
              {t("employeeDashboard.afterShiftHint")}
            </Typography>
            <Stack direction="row" gap={1} flexWrap="wrap">
              {agentRows
                .filter((row) => row.after_shift_work > 0)
                .map((row) => (
                  <Chip
                    key={row.agent}
                    color="secondary"
                    label={`${row.agent}: ${row.after_shift_work} operation${row.after_shift_work === 1 ? "" : "s"} · ${row.after_shift_hours}h`}
                  />
                ))}
              {!agentRows.some((row) => row.after_shift_work > 0) && (
                <Typography color="text.secondary">
                  {t("employeeDashboard.noAfterShiftWork")}
                </Typography>
              )}
            </Stack>
          </Paper>
          <Paper
            id="agents-report"
            sx={{ p: 2.5, borderRadius: 3, scrollMarginTop: 90 }}
          >
            <Stack
              direction={{ xs: "column", sm: "row" }}
              alignItems={{ sm: "center" }}
              mb={2}
              gap={2}
              flexWrap="wrap"
            >
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6" fontWeight={800}>
                  {t("employeeDashboard.agentKpiReport")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("employeeDashboard.agentKpiHint")}
                </Typography>
              </Box>
              <FormControl size="small" sx={{ minWidth: 130 }}>
                <InputLabel>{t("employeeDashboard.period")}</InputLabel>
                <Select
                  value={periodMode}
                  label={t("employeeDashboard.period")}
                  onChange={(event) =>
                    setPeriodMode(
                      event.target.value as "MONTH" | "QUARTER" | "CUSTOM",
                    )
                  }
                >
                  <MenuItem value="MONTH">
                    {t("employeeDashboard.monthly")}
                  </MenuItem>
                  <MenuItem value="QUARTER">
                    {t("employeeDashboard.quarterly")}
                  </MenuItem>
                  <MenuItem value="CUSTOM">
                    {t("employeeDashboard.customDates")}
                  </MenuItem>
                </Select>
              </FormControl>
              {periodMode === "MONTH" && (
                <TextField
                  size="small"
                  type="month"
                  label={t("employeeDashboard.kpiMonth")}
                  value={month}
                  onChange={(event) => setMonth(event.target.value)}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
              )}
              {periodMode === "QUARTER" && (
                <>
                  <TextField
                    size="small"
                    type="number"
                    label={t("employeeDashboard.year")}
                    value={reportYear}
                    onChange={(event) =>
                      setReportYear(Number(event.target.value))
                    }
                    inputProps={{ min: 2020, max: 2100 }}
                    sx={{ width: 110 }}
                  />
                  <FormControl size="small" sx={{ minWidth: 90 }}>
                    <InputLabel>{t("employeeDashboard.quarter")}</InputLabel>
                    <Select
                      value={quarter}
                      label={t("employeeDashboard.quarter")}
                      onChange={(event) =>
                        setQuarter(Number(event.target.value))
                      }
                    >
                      <MenuItem value={1}>Q1</MenuItem>
                      <MenuItem value={2}>Q2</MenuItem>
                      <MenuItem value={3}>Q3</MenuItem>
                      <MenuItem value={4}>Q4</MenuItem>
                    </Select>
                  </FormControl>
                </>
              )}
              {periodMode === "CUSTOM" && (
                <>
                  <TextField
                    size="small"
                    type="date"
                    label={t("employeeDashboard.from")}
                    value={dateFrom}
                    onChange={(event) => setDateFrom(event.target.value)}
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <TextField
                    size="small"
                    type="date"
                    label={t("employeeDashboard.to")}
                    value={dateTo}
                    onChange={(event) => setDateTo(event.target.value)}
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <FormControl size="small" sx={{ minWidth: 160 }}>
                    <InputLabel>{t("employeeDashboard.dateBasis")}</InputLabel>
                    <Select
                      value={dateBasis}
                      label={t("employeeDashboard.dateBasis")}
                      onChange={(event) =>
                        setDateBasis(event.target.value as typeof dateBasis)
                      }
                    >
                      <MenuItem value="CREATION">
                        {t("employeeDashboard.creationDate")}
                      </MenuItem>
                      <MenuItem value="RESOLUTION">
                        {t("employeeDashboard.resolutionDate")}
                      </MenuItem>
                      <MenuItem value="ASSIGNMENT">
                        {t("employeeDashboard.assignmentDate")}
                      </MenuItem>
                    </Select>
                  </FormControl>
                </>
              )}
              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel>{t("employeeDashboard.agent")}</InputLabel>
                <Select
                  value={agent}
                  label={t("employeeDashboard.agent")}
                  onChange={(event) => setAgent(event.target.value)}
                >
                  <MenuItem value="ALL">
                    {t("employeeDashboard.allAgents")}
                  </MenuItem>
                  {(data.agent_kpis ?? []).map((row) => (
                    <MenuItem key={row.agent} value={row.agent}>
                      {row.agent}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              {hasPermission("report.export") && (
                <Button variant="contained" onClick={exportAgentKpis}>
                  {t("employeeDashboard.exportHrExcel")}
                </Button>
              )}
              <Button
                variant="outlined"
                onClick={() => setActivityDialog(true)}
              >
                {t("employeeDashboard.logActivity")}
              </Button>
            </Stack>
            <TableContainer>
              <Table size="small" sx={{ minWidth: 1500 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>{t("employeeDashboard.agent")}</TableCell>
                    <TableCell>
                      {t("employeeDashboard.ticketsByStatusColumn")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.totalHandled")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.escalations")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.responseTime")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.reopened")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.externalActivities")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.trainingSupport")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.tasksAdded")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.knowledgeShared")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.followerAssignments")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.dedicatedClients")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.clientTickets")}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {agentRows.map((row) => (
                    <TableRow hover key={row.agent}>
                      <TableCell>
                        <Typography fontWeight={700}>{row.agent}</Typography>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" gap={0.5} flexWrap="wrap">
                          {Object.entries(row.tickets_by_status ?? {}).map(
                            ([status, count]) => (
                              <Chip
                                key={status}
                                size="small"
                                label={`${status.replaceAll("_", " ")} ${count}`}
                              />
                            ),
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell align="right">{row.assigned}</TableCell>
                      <TableCell align="right">
                        {row.escalation_assignments ?? 0}
                      </TableCell>
                      <TableCell align="right">
                        {row.average_response_hours == null
                          ? "—"
                          : `${row.average_response_hours}h`}
                      </TableCell>
                      <TableCell align="right">
                        {row.reopened_tickets ?? 0}
                      </TableCell>
                      <TableCell align="right">
                        {row.external_activities ?? 0}
                        <Typography variant="caption" display="block">
                          {row.meetings ?? 0} meetings
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {row.training_delivered ?? 0}
                        <Typography variant="caption" display="block">
                          {row.training_attended ?? 0} attended
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {row.tasks_created ?? 0}
                      </TableCell>
                      <TableCell align="right">
                        {row.knowledge_articles ?? 0}
                      </TableCell>
                      <TableCell align="right">
                        {row.follower_assignments ?? 0}
                      </TableCell>
                      <TableCell align="right">
                        {row.dedicated_clients ?? 0}
                      </TableCell>
                      <TableCell align="right">
                        {row.dedicated_client_tickets ?? 0}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
          <Paper
            id="products-report"
            sx={{ p: 2.5, borderRadius: 3, scrollMarginTop: 90 }}
          >
            <Stack
              direction={{ xs: "column", sm: "row" }}
              alignItems={{ sm: "center" }}
              mb={2}
              gap={2}
            >
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6" fontWeight={800}>
                  {t("employeeDashboard.productKpiReport")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("employeeDashboard.productKpiHint")}
                </Typography>
              </Box>
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel>{t("employeeDashboard.product")}</InputLabel>
                <Select
                  value={product}
                  label={t("employeeDashboard.product")}
                  onChange={(event) => setProduct(event.target.value)}
                >
                  <MenuItem value="ALL">
                    {t("employeeDashboard.allProducts")}
                  </MenuItem>
                  {[
                    ...new Set(
                      (data.product_kpis ?? []).map((row) => row.product),
                    ),
                  ].map((value) => (
                    <MenuItem key={value} value={value}>
                      {value}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("employeeDashboard.product")}</TableCell>
                    <TableCell>{t("employeeDashboard.module")}</TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.total")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.open")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.resolved")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.slaBreaches")}
                    </TableCell>
                    <TableCell align="right">
                      {t("employeeDashboard.avgResolution")}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {productRows.map((row) => (
                    <TableRow hover key={`${row.product}-${row.module}`}>
                      <TableCell>
                        <Typography fontWeight={600}>{row.product}</Typography>
                      </TableCell>
                      <TableCell>{row.module}</TableCell>
                      <TableCell align="right">{row.total}</TableCell>
                      <TableCell align="right">{row.open}</TableCell>
                      <TableCell align="right">{row.resolved}</TableCell>
                      <TableCell align="right">
                        <Chip
                          size="small"
                          color={row.breached ? "error" : "success"}
                          label={row.breached}
                        />
                      </TableCell>
                      <TableCell align="right">
                        {row.average_resolution_hours === null
                          ? "—"
                          : `${row.average_resolution_hours}h`}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
          <Grid
            id="sla-report"
            container
            spacing={2}
            sx={{ scrollMarginTop: 90 }}
          >
            <Grid size={{ xs: 12, md: 6 }}>
              <BreakdownPanel
                title={t("employeeDashboard.engineerWorkload")}
                values={data.workload_by_engineer}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <BreakdownPanel
                title={t("employeeDashboard.topCategories")}
                values={data.top_categories}
                color="#0d9488"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <BreakdownPanel
                title={t("employeeDashboard.backlogByClient")}
                values={data.backlog_by_client}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <BreakdownPanel
                title={t("employeeDashboard.backlogByTeam")}
                values={data.backlog_by_team}
                color="#7c3aed"
              />
            </Grid>
          </Grid>
        </>
      )}
      <Dialog
        open={activityDialog}
        onClose={() => setActivityDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            logActivity.mutate({
              user_id: Number(values.user_id),
              activity_type: values.activity_type,
              participation_role: values.participation_role,
              title: String(values.title).trim(),
              duration_minutes: Number(values.duration_minutes),
              occurred_at: new Date(String(values.occurred_at)).toISOString(),
              notes: String(values.notes).trim() || null,
            });
          }}
        >
          <DialogTitle>{t("employeeDashboard.logActivity")}</DialogTitle>
          <DialogContent>
            {logActivity.isError && (
              <Alert severity="error">
                {t("employeeDashboard.activityFailed")}
              </Alert>
            )}
            <TextField
              select
              required
              name="user_id"
              label={t("employeeDashboard.employee")}
              fullWidth
              margin="normal"
              defaultValue={
                hasPermission("dashboard.manager") ? "" : (user?.id ?? "")
              }
            >
              {hasPermission("dashboard.manager") ? (
                (data.agent_kpis ?? [])
                  .filter((row) => row.user_id)
                  .map((row) => (
                    <MenuItem key={row.user_id} value={row.user_id ?? ""}>
                      {row.agent}
                    </MenuItem>
                  ))
              ) : (
                <MenuItem value={user?.id ?? ""}>{user?.full_name}</MenuItem>
              )}
            </TextField>
            <TextField
              select
              required
              name="activity_type"
              label={t("employeeDashboard.activity")}
              fullWidth
              margin="normal"
              defaultValue="TRAINING"
            >
              <MenuItem value="TRAINING">
                {t("employeeDashboard.training")}
              </MenuItem>
              <MenuItem value="MEETING">
                {t("employeeDashboard.meeting")}
              </MenuItem>
            </TextField>
            <TextField
              select
              required
              name="participation_role"
              label={t("employeeDashboard.role")}
              fullWidth
              margin="normal"
              defaultValue="ATTENDEE"
            >
              <MenuItem value="ATTENDEE">
                {t("employeeDashboard.attendee")}
              </MenuItem>
              <MenuItem value="FACILITATOR">
                {t("employeeDashboard.facilitator")}
              </MenuItem>
              <MenuItem value="PRESENTER">
                {t("employeeDashboard.presenter")}
              </MenuItem>
              <MenuItem value="PARTICIPANT">
                {t("employeeDashboard.participant")}
              </MenuItem>
            </TextField>
            <TextField
              required
              name="title"
              label={t("employeeDashboard.subject")}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 3 }}
            />
            <TextField
              required
              type="number"
              name="duration_minutes"
              label={t("employeeDashboard.duration")}
              fullWidth
              margin="normal"
              inputProps={{ min: 1, max: 1440 }}
            />
            <TextField
              required
              type="datetime-local"
              name="occurred_at"
              label={t("employeeDashboard.dateTime")}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              name="notes"
              label={t("employeeDashboard.evidenceNotes")}
              fullWidth
              multiline
              rows={3}
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setActivityDialog(false)}>
              {t("employeeDashboard.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={logActivity.isPending}
            >
              Save activity
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
