import { ServiceManagementWidget } from "../components/ServiceManagementCards";
import {
  AccountTree,
  AssignmentInd,
  ConfirmationNumber,
  ErrorOutline,
  Groups,
  HourglassBottom,
  PlayCircleOutline,
  Refresh,
  Schedule,
  WorkHistory,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import {
  HomePlanner,
  InactiveClientsGrid,
  OperationPanels,
  TicketApprovals,
} from "../components/HomeOperations";
import { ClientHoursWidget } from "../components/ClientHoursWidget";
import {
  PersonalDashboardGrid,
  type DashboardTile,
} from "../components/PersonalDashboardGrid";
import { useAuth } from "../auth/AuthContext";
import { selectTopSupportAgents } from "../utils/dashboardAgents";

type Snapshot = {
  generated_at: string;
  today: string;
  cache_seconds: number;
  capabilities: { internal_operations: boolean };
  tickets: {
    total: number;
    open: number;
    in_progress: number;
    unassigned: number;
    needs_attention: number;
    created_today: number;
    pending_approval: number;
    pending: number;
  };
  operations: {
    online_engineers: number;
    active_shifts: number;
    active_operations: number;
    blocked_operations: number;
  };
  checklists: { completed: number; needs_attention: number };
  attention: Array<{
    id: number;
    ticket_number?: string;
    subject: string;
    priority: string;
    status: string;
    client: string;
    assigned: boolean;
    due_at?: string;
    last_activity_at: string;
  }>;
  status_mix: Array<{ label: string; value: number }>;
  priority_mix: Array<{ label: string; value: number }>;
  ticket_trend: Array<{ date: string; created: number }>;
};

type TopAgents = {
  agents: Array<{
    user_id: number | null;
    agent: string;
    assigned: number;
    resolved: number;
    breached: number;
  }>;
};
type OnlineEngineer = {
  user_id: number;
  engineer: string;
  department?: string;
  status: "AVAILABLE" | "WORKING_ON_TICKET";
  active_ticket_count: number;
};
function MixChart({
  title,
  rows,
  filter,
}: {
  title: string;
  rows: Array<{ label: string; value: number }>;
  filter: "status_code" | "priority";
}) {
  const colors = [
    "#2979ff",
    "#00a88f",
    "#f59e0b",
    "#8b5cf6",
    "#ef4444",
    "#64748b",
  ];
  const sorted = [...rows].sort((a, b) => b.value - a.value);
  const total = sorted.reduce((sum, row) => sum + row.value, 0);
  let progress = 0;
  const gradient = sorted
    .map((row, index) => {
      const start = progress;
      progress += (row.value / Math.max(total, 1)) * 100;
      return `${colors[index % colors.length]} ${start}% ${progress}%`;
    })
    .join(", ");
  return (
    <Paper sx={{ p: 2.5, height: "100%" }}>
      <Typography variant="h6" fontWeight={800} mb={2}>
        {title}
      </Typography>
      {total === 0 ? (
        <Typography color="text.secondary">No tickets in this view.</Typography>
      ) : (
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems="center"
          gap={2}
        >
          <Box
            sx={{
              width: 150,
              height: 150,
              flexShrink: 0,
              borderRadius: "50%",
              background: `conic-gradient(${gradient})`,
              display: "grid",
              placeItems: "center",
            }}
          >
            <Box
              sx={{
                width: 92,
                height: 92,
                borderRadius: "50%",
                bgcolor: "background.paper",
                display: "grid",
                placeItems: "center",
              }}
            >
              <Typography variant="h5" fontWeight={900}>
                {total}
              </Typography>
            </Box>
          </Box>
          <Stack spacing={0.6} flex={1} width="100%">
            {sorted.map((row, index) => (
              <Stack
                key={row.label}
                component={Link}
                to={`/tickets?${filter}=${encodeURIComponent(row.label)}`}
                direction="row"
                gap={1}
                alignItems="center"
                sx={{
                  color: "inherit",
                  textDecoration: "none",
                  "&:hover": { color: "primary.main" },
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
                <Typography variant="body2" flex={1}>
                  {row.label.replaceAll("_", " ")}
                </Typography>
                <Typography fontWeight={800}>{row.value}</Typography>
              </Stack>
            ))}
          </Stack>
        </Stack>
      )}
    </Paper>
  );
}

function TicketTrend({
  rows,
}: {
  rows: Array<{ date: string; created: number }>;
}) {
  const maximum = Math.max(1, ...rows.map((row) => row.created));
  return (
    <Paper sx={{ p: 2.5, height: "100%" }}>
      <Typography variant="h6" fontWeight={800}>
        Tickets created · last 7 days
      </Typography>
      <Stack
        direction="row"
        alignItems="flex-end"
        gap={1}
        sx={{ height: 185, mt: 2 }}
      >
        {rows.map((row) => (
          <Stack
            key={row.date}
            flex={1}
            height="100%"
            justifyContent="flex-end"
            alignItems="center"
            gap={0.5}
          >
            <Typography variant="caption" fontWeight={800}>
              {row.created}
            </Typography>
            <Box
              sx={{
                width: "100%",
                maxWidth: 48,
                height: `${Math.max(3, (row.created / maximum) * 130)}px`,
                bgcolor: "primary.main",
                borderRadius: "5px 5px 0 0",
              }}
            />
            <Typography variant="caption" color="text.secondary">
              {row.date.slice(5)}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}

const cards = [
  {
    key: "open",
    label: "Open tickets",
    icon: <ConfirmationNumber />,
    color: "#2979ff",
    query: "open_only=true",
  },
  {
    key: "pending_approval",
    label: "Waiting for approval",
    icon: <HourglassBottom />,
    color: "#d97706",
    query: "entitlement_status=PENDING_APPROVAL",
  },
  {
    key: "pending",
    label: "Pending tickets",
    icon: <Schedule />,
    color: "#9333ea",
    query: "status_code=PENDING_CLIENT%2CPENDING_INTERNAL%2CPENDING_VENDOR",
  },
  {
    key: "in_progress",
    label: "In progress",
    icon: <PlayCircleOutline />,
    color: "#00a88f",
    query: "status_code=IN_PROGRESS",
  },
  {
    key: "unassigned",
    label: "Unassigned",
    icon: <AssignmentInd />,
    color: "#f59e0b",
    query: "unassigned_only=true",
  },
  {
    key: "needs_attention",
    label: "Need attention",
    icon: <ErrorOutline />,
    color: "#ef4444",
    query: "needs_attention=true",
  },
  {
    key: "created_today",
    label: "Created today",
    icon: <Schedule />,
    color: "#8b5cf6",
    query: "",
  },
] as const;

export function HomePage() {
  const { user, hasPermission } = useAuth();
  const snapshot = useQuery({
    queryKey: ["operational-home"],
    queryFn: async () => (await api.get<Snapshot>("/home/snapshot")).data,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });
  const topAgents = useQuery({
    queryKey: ["home-top-support-agents"],
    queryFn: async () =>
      (
        await api.get<TopAgents>("/dashboards/top-support-agents", {
          params: { limit: 3 },
        })
      ).data,
    enabled:
      hasPermission("dashboard.agent") || hasPermission("dashboard.manager"),
    staleTime: 300_000,
  });
  const canViewOnlineEngineers = hasPermission(
    "dashboard.online_engineers.view",
  );
  const onlineEngineers = useQuery({
    queryKey: ["support-now-online-engineers"],
    queryFn: async () =>
      (await api.get<OnlineEngineer[]>("/dashboards/online-engineers")).data,
    enabled: canViewOnlineEngineers,
    staleTime: 10_000,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
  if (snapshot.isLoading)
    return (
      <Box sx={{ minHeight: "45vh", display: "grid", placeItems: "center" }}>
        <CircularProgress />
      </Box>
    );
  if (!snapshot.data)
    return (
      <Alert severity="error">
        The operational snapshot could not be loaded.
      </Alert>
    );

  const data = snapshot.data;
  const operations = [
    {
      label: "Online engineers",
      value: data.operations.online_engineers,
      icon: <Groups />,
      color: "#2979ff",
    },
    {
      label: "Active shifts",
      value: data.operations.active_shifts,
      icon: <Schedule />,
      color: "#00a88f",
      to: "/internal-operations?section=calendar",
    },
    {
      label: "Active operations",
      value: data.operations.active_operations,
      icon: <WorkHistory />,
      color: "#8b5cf6",
      to: "/internal-operations",
    },
    {
      label: "Blocked operations",
      value: data.operations.blocked_operations,
      icon: <ErrorOutline />,
      color: data.operations.blocked_operations ? "#ef4444" : "#64748b",
      to: "/internal-operations",
    },
  ];
  const rankedAgents = selectTopSupportAgents(topAgents.data?.agents ?? []);
  const tiles: DashboardTile[] = [
    ...cards.map((card) => ({
      code: card.key,
      width: 4,
      content: (
        <Paper
          component={Link}
          to={`/tickets?${card.key === "created_today" ? `created_from=${data.today}&created_to=${data.today}` : card.query}`}
          sx={{
            p: 2,
            pl: 2.25,
            display: "block",
            height: "100%",
            color: "inherit",
            textDecoration: "none",
            position: "relative",
            overflow: "hidden",
            border: `1px solid ${alpha(card.color, 0.24)}`,
            transition: "transform .18s ease, box-shadow .18s ease",
            "&::before": {
              content: '""',
              position: "absolute",
              inset: "0 auto 0 0",
              width: 5,
              bgcolor: card.color,
            },
            "&:hover": {
              transform: "translateY(-3px)",
              boxShadow: `0 10px 24px ${alpha(card.color, 0.14)}`,
            },
          }}
        >
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
          >
            <Box>
              <Typography variant="h4" fontWeight={900}>
                {data.tickets[card.key].toLocaleString()}
              </Typography>
              <Typography
                color="text.secondary"
                variant="body2"
                fontWeight={600}
              >
                {card.label}
              </Typography>
            </Box>
            <Box
              sx={{
                width: 42,
                height: 42,
                display: "grid",
                placeItems: "center",
                color: card.color,
                bgcolor: alpha(card.color, 0.1),
                borderRadius: 2,
              }}
            >
              {card.icon}
            </Box>
          </Stack>
        </Paper>
      ),
    })),
    {
      code: "completed_checklists", width: 4,
      content: <Paper component={Link} to="/service-checklists?view=monitor&filter=COMPLETED" sx={{p:2,height:"100%",display:"block",color:"inherit",textDecoration:"none",border:"2px solid #2E7D32",borderInlineStart:"7px solid #2E7D32","&:hover":{boxShadow:5,transform:"translateY(-2px)"}}}><Typography variant="h4" fontWeight={900}>{(data.checklists?.completed ?? 0).toLocaleString()}</Typography><Typography color="text.secondary" variant="body2" fontWeight={600}>Completed checklists · last 7 days</Typography></Paper>,
    },
    {
      code: "attention_checklists", width: 4,
      content: <Paper component={Link} to="/service-checklists?view=monitor&filter=ATTENTION" sx={{p:2,height:"100%",display:"block",color:"inherit",textDecoration:"none",border:"2px solid #D32F2F",borderInlineStart:"7px solid #D32F2F","&:hover":{boxShadow:5,transform:"translateY(-2px)"}}}><Typography variant="h4" fontWeight={900}>{(data.checklists?.needs_attention ?? 0).toLocaleString()}</Typography><Typography color="text.secondary" variant="body2" fontWeight={600}>Checklists needing attention</Typography></Paper>,
    },
    { code: "client_hours", width: 12, content: <ClientHoursWidget /> },
    { code: "service_incidents", width: 4, content: <ServiceManagementWidget category="incidents" /> },
    { code: "service_change_requests", width: 4, content: <ServiceManagementWidget category="changes" /> },
    { code: "service_problems", width: 4, content: <ServiceManagementWidget category="problems" /> },
    {
      code: "top_agents",
      width: 6,
      content: (
        <Paper sx={{ p: 2.5, height: "100%" }}>
          <Typography variant="h6" fontWeight={800}>
            Top 3 agents
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Resolved tickets this month
          </Typography>
          <Stack spacing={1.5} mt={2}>
            {rankedAgents.map((agent, index) => (
              <Stack
                key={agent.agent}
                direction="row"
                gap={1.5}
                alignItems="center"
              >
                <Typography fontSize={26}>
                  {["🥇", "🥈", "🥉"][index]}
                </Typography>
                <Typography flex={1} fontWeight={700}>
                  {agent.agent}
                </Typography>
                <Chip label={`${agent.resolved} resolved`} size="small" />
              </Stack>
            ))}
            {!rankedAgents.length && (
              <Typography color="text.secondary">
                No resolved tickets this month.
              </Typography>
            )}
          </Stack>
        </Paper>
      ),
    },
    {
      code: "status_mix",
      width: 6,
      content: (
        <MixChart
          title="Ticket status mix"
          rows={data.status_mix ?? []}
          filter="status_code"
        />
      ),
    },
    {
      code: "priority_mix",
      width: 6,
      content: (
        <MixChart
          title="Ticket priority mix"
          rows={data.priority_mix ?? []}
          filter="priority"
        />
      ),
    },
    {
      code: "ticket_trend",
      width: 6,
      content: <TicketTrend rows={data.ticket_trend ?? []} />,
    },
    { code: "planner", width: 12, content: <HomePlanner today={data.today} /> },
    { code: "inactive_clients", width: 12, content: <InactiveClientsGrid /> },
    { code: "approvals", width: 12, content: <TicketApprovals /> },
    { code: "operation_panels", width: 12, content: <OperationPanels /> },
  ];

  return (
    <Stack spacing={2.25}>
      <Paper
        sx={(theme) => ({
          position: "relative",
          overflow: "hidden",
          p: { xs: 2.5, md: 3.5 },
          color: theme.palette.primary.contrastText,
          background: `linear-gradient(125deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 58%, ${theme.palette.secondary.main} 125%)`,
          border: `1px solid ${alpha(theme.palette.primary.contrastText, 0.14)}`,
          "&::after": {
            content: '""',
            position: "absolute",
            width: 280,
            height: 280,
            borderRadius: "50%",
            right: -70,
            top: -150,
            background: alpha(theme.palette.primary.contrastText, 0.08),
          },
        })}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ md: "center" }}
          gap={2.5}
          sx={{ position: "relative", zIndex: 1 }}
        >
          <Box>
            <Stack direction="row" alignItems="center" spacing={1} mb={1}>
              <Chip
                size="small"
                label="LIVE OPERATIONS"
                sx={{
                  color: "#fff",
                  bgcolor: alpha("#fff", 0.14),
                  fontWeight: 800,
                  letterSpacing: 0.8,
                  "&::before": {
                    content: '""',
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    bgcolor: "#55e6a5",
                    ml: 1.2,
                    boxShadow: "0 0 0 4px rgba(85,230,165,.15)",
                  },
                }}
              />
              <Typography variant="caption" sx={{ color: alpha("#fff", 0.72) }}>
                {new Date(data.today).toLocaleDateString(undefined, {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                })}
              </Typography>
            </Stack>
            <Typography variant="h4" fontWeight={900} letterSpacing={-0.7}>
              Support Operations
            </Typography>
            <Typography sx={{ color: alpha("#fff", 0.76), mt: 0.5 }}>
              A clear view of what is happening and what needs action now.
            </Typography>
            {canViewOnlineEngineers && (
              <Box mt={1.5} maxWidth={{ xs: "100%", md: 760 }}>
                <Stack direction="row" alignItems="center" gap={0.75} mb={0.6}>
                  <Groups sx={{ fontSize: 16 }} />
                  <Typography
                    variant="caption"
                    fontWeight={850}
                    letterSpacing={0.35}
                  >
                    ONLINE ENGINEERS
                  </Typography>
                  <Chip
                    size="small"
                    label={onlineEngineers.data?.length ?? 0}
                    sx={{
                      height: 20,
                      color: "inherit",
                      bgcolor: alpha("#fff", 0.14),
                      fontWeight: 850,
                    }}
                  />
                </Stack>
                <Stack
                  direction="row"
                  gap={0.75}
                  sx={{ overflowX: "auto", pb: 0.35, scrollbarWidth: "thin" }}
                >
                  {onlineEngineers.data?.map((engineer) => (
                    <Paper
                      key={engineer.user_id}
                      component={Link}
                      to={`/tickets?assigned_user_id=${engineer.user_id}&open_only=true`}
                      variant="outlined"
                      sx={{
                        minWidth: 150,
                        maxWidth: 190,
                        px: 1,
                        py: 0.55,
                        color: "inherit",
                        bgcolor: alpha("#fff", 0.1),
                        borderColor: alpha("#fff", 0.2),
                        textDecoration: "none",
                        borderRadius: 1.5,
                        "&:hover": { bgcolor: alpha("#fff", 0.18) },
                      }}
                    >
                      <Stack direction="row" alignItems="center" gap={0.75}>
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            bgcolor:
                              engineer.status === "AVAILABLE"
                                ? "#55e6a5"
                                : "warning.light",
                            boxShadow: `0 0 0 3px ${alpha("#fff", 0.1)}`,
                            flexShrink: 0,
                          }}
                        />
                        <Box minWidth={0}>
                          <Typography
                            variant="caption"
                            fontWeight={850}
                            display="block"
                            noWrap
                          >
                            {engineer.engineer}
                          </Typography>
                          <Typography
                            variant="caption"
                            display="block"
                            noWrap
                            sx={{ color: alpha("#fff", 0.72), fontSize: 10.5 }}
                          >
                            {engineer.status === "AVAILABLE"
                              ? engineer.department || "Available"
                              : `${engineer.active_ticket_count} active ticket${engineer.active_ticket_count === 1 ? "" : "s"}`}
                          </Typography>
                        </Box>
                      </Stack>
                    </Paper>
                  ))}
                  {!onlineEngineers.isLoading &&
                    !onlineEngineers.data?.length && (
                      <Typography
                        variant="caption"
                        sx={{ color: alpha("#fff", 0.72) }}
                      >
                        No engineers are online now.
                      </Typography>
                    )}
                </Stack>
              </Box>
            )}
          </Box>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Box textAlign="right">
              <Typography variant="h4" fontWeight={900}>
                {data.tickets.total.toLocaleString()}
              </Typography>
              <Typography variant="caption" sx={{ color: alpha("#fff", 0.72) }}>
                VISIBLE TICKETS
              </Typography>
            </Box>
            <Button
              component={Link}
              to="/organization"
              variant="contained"
              startIcon={<AccountTree />}
              sx={{
                bgcolor: "#fff",
                color: "primary.dark",
                boxShadow: "0 8px 22px rgba(0,0,0,.12)",
                "&:hover": { bgcolor: alpha("#fff", 0.9) },
              }}
            >
              Our Organization
            </Button>
            <Button
              variant="contained"
              startIcon={<Refresh />}
              disabled={snapshot.isFetching}
              onClick={() => snapshot.refetch()}
              sx={{
                bgcolor: alpha("#fff", 0.14),
                color: "#fff",
                boxShadow: "none",
                "&:hover": { bgcolor: alpha("#fff", 0.23), boxShadow: "none" },
              }}
            >
              {snapshot.isFetching ? "Updating" : "Refresh"}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <PersonalDashboardGrid
        tiles={tiles}
        storageKey={`supporthub-dashboard-layout-${user?.id ?? "anonymous"}-SUPPORT_NOW`}
      />
      {data.capabilities.internal_operations && (
        <Box>
          <Typography variant="h6" fontWeight={850} mb={1.25}>
            Live operations
          </Typography>
          <Grid container spacing={1.5}>
            {operations.map((item) => (
              <Grid key={item.label} size={{ xs: 6, md: 3 }}>
                <Paper
                  component={item.to ? Link : "div"}
                  to={item.to}
                  sx={{
                    p: 2,
                    height: "100%",
                    color: "inherit",
                    textDecoration: "none",
                    border: `1px solid ${alpha(item.color, 0.22)}`,
                    borderBottom: `4px solid ${item.color}`,
                  }}
                >
                  <Stack direction="row" alignItems="center" spacing={1.5}>
                    <Box
                      sx={{
                        color: item.color,
                        bgcolor: alpha(item.color, 0.1),
                        borderRadius: 1.5,
                        p: 0.8,
                        display: "grid",
                      }}
                    >
                      {item.icon}
                    </Box>
                    <Box>
                      <Typography variant="h5" fontWeight={900} lineHeight={1}>
                        {item.value}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        mt={0.5}
                      >
                        {item.label}
                      </Typography>
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Stack>
  );
}
