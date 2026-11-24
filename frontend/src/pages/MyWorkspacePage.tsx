import { Add, ArrowForward, AssignmentTurnedIn, Bookmark, CalendarMonth, CheckCircle, DeleteOutline, DirectionsCar, History, PushPin, Refresh, Settings, SupportAgent, ViewList, WorkHistory } from "@mui/icons-material";
import { Alert, Avatar, Box, Button, Card, CardActionArea, CardContent, Checkbox, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, FormControlLabel, Grid, IconButton, LinearProgress, Paper, Stack, Tab, Tabs, Tooltip, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AttentionCenter } from "../components/AttentionCenter";

type WidgetCode = "tasks" | "support" | "shifts" | "visits" | "operations" | "approvals";
type WorkspaceItem = { id: string; label: string; path: string; item_type: "page" | "ticket" | "client" | "saved_view" | "support_tab" | "record"; visited_at?: string | null };
type Workspace = { favorites: WorkspaceItem[]; recent: WorkspaceItem[]; hidden_widgets: WidgetCode[] };
type SupportPreferences = { pinned_ticket_ids: number[]; custom_tabs: Array<{ id: string; name: string }> };
type Shift = { id: number; shift_name: string; shift_color: string; status: string; starts_at: string; ends_at: string; work_location: string; team?: string };
type Visit = { id: number; client_name?: string; status: string; window_start: string; assignments: Array<{ starts_at: string; ends_at: string }> };
type Operation = { id: number; title: string; status: string; starts_at: string; ends_at: string; client_name?: string; assignees: Array<{ id: number }> };
type Approval = { id: number; ticket_id?: number; requested_action: string };
type Assignment = { id: number; title: string; status: string; priority: string; due_at?: string | null; assignees: Array<{ user_id: number }> };

const quickLinks: WorkspaceItem[] = [
  { id: "page:tickets", label: "Tickets", path: "/tickets", item_type: "page" },
  { id: "page:work-assignments", label: "Work Assignments", path: "/work-assignments", item_type: "page" },
  { id: "page:support-assistant", label: "Support Assistant", path: "/support-workspace", item_type: "page" },
  { id: "page:support-now", label: "Support Now", path: "/home", item_type: "page" },
  { id: "page:dashboard", label: "Dashboard", path: "/dashboard", item_type: "page" },
  { id: "page:knowledge", label: "Knowledge", path: "/knowledge", item_type: "page" },
];
const labels: Record<WidgetCode, string> = { tasks: "My assigned tasks", support: "My support work", shifts: "My shifts", visits: "My visits", operations: "My operations", approvals: "My approvals" };
const fmt = (value: string) => new Intl.DateTimeFormat(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" }).format(new Date(value));
const upcoming = (value: string) => new Date(value).getTime() >= Date.now();

export function MyWorkspacePage() {
  const navigate = useNavigate(), cache = useQueryClient();
  const { user, hasPermission } = useAuth();
  const [tab, setTab] = useState(0), [customize, setCustomize] = useState(false);
  const workspace = useQuery({ queryKey: ["my-workspace"], queryFn: async () => (await api.get<Workspace>("/tickets/my-workspace")).data });
  const savedViews = useQuery({ queryKey: ["saved-views"], enabled: hasPermission("ticket.view.all") || hasPermission("ticket.view.team") || hasPermission("ticket.view.own"), queryFn: async () => (await api.get<Array<{ id: number; name: string }>>("/saved-views")).data });
  const support = useQuery({ queryKey: ["support-assistant-preferences"], queryFn: async () => (await api.get<SupportPreferences>("/tickets/support-assistant/preferences")).data });
  const range = useMemo(() => { const start = new Date(); start.setHours(0, 0, 0, 0); const end = new Date(start); end.setDate(end.getDate() + 7); return { start: start.toISOString(), end: end.toISOString() }; }, []);
  const shifts = useQuery({ queryKey: ["workspace-shifts", user?.id], enabled: Boolean(user && hasPermission("shift.view")), queryFn: async () => (await api.get<Shift[]>("/shift-calendar", { params: { user_id: user?.id, ends_after: range.start, starts_before: range.end } })).data.filter((item) => item.status !== "CANCELLED") });
  const visits = useQuery({ queryKey: ["workspace-visits", user?.id], enabled: Boolean(user), queryFn: async () => (await api.get<Visit[]>("/visits/field-request/mine")).data });
  const operations = useQuery({ queryKey: ["workspace-operations", user?.id], enabled: Boolean(user && hasPermission("internal_operation.view")), queryFn: async () => (await api.get<Operation[]>("/internal-operations", { params: { date_from: range.start.slice(0, 10), date_to: range.end.slice(0, 10) } })).data.filter((item) => item.assignees.some((person) => person.id === user?.id) && upcoming(item.ends_at)) });
  const approvals = useQuery({ queryKey: ["workspace-approvals"], enabled: hasPermission("entitlement_approval.decide"), queryFn: async () => (await api.get<Approval[]>("/entitlement-approvals", { params: { status: "PENDING" } })).data });
  const tasks = useQuery({ queryKey: ["workspace-work-assignments", user?.id], enabled: Boolean(user), queryFn: async () => (await api.get<Assignment[]>("/work-assignments", { params: { scope: "MINE", limit: 20 } })).data.filter((item) => !["COMPLETED", "CANCELLED"].includes(item.status)) });
  const ticketCount = async (assistant_module: string) => { const response = await api.get("/tickets", { params: { assistant_module, limit: 1 } }); return Number(response.headers["x-total-count"] ?? response.data.length); };
  const supportCounts = useQuery({ queryKey: ["workspace-support-counts", user?.id], enabled: hasPermission("support_assistant.mine.view"), queryFn: async () => { const [mine, risk, followUp] = await Promise.all([ticketCount("mine"), hasPermission("support_assistant.sla_risk.view") ? ticketCount("sla-risk") : Promise.resolve(null), hasPermission("support_assistant.follow_up.view") ? ticketCount("follow-up") : Promise.resolve(null)]); return { mine, risk, followUp }; }, refetchInterval: 60_000 });
  const save = useMutation({ mutationFn: async (next: Workspace) => (await api.put<Workspace>("/tickets/my-workspace", { favorites: next.favorites, hidden_widgets: next.hidden_widgets })).data, onSuccess: (data) => cache.setQueryData(["my-workspace"], data) });
  const favorites = useMemo(() => (workspace.data?.favorites ?? []).map((item) => item.id === "page:support-now" && item.path === "/support-workspace" ? { ...item, id: "page:support-assistant", label: "Support Assistant" } : item), [workspace.data?.favorites]), hidden = workspace.data?.hidden_widgets ?? [];
  const available = useMemo(() => [...quickLinks, ...(savedViews.data ?? []).map((view) => ({ id: `saved_view:${view.id}`, label: view.name, path: `/tickets?saved_view_id=${view.id}`, item_type: "saved_view" as const })), ...(support.data?.custom_tabs ?? []).map((item) => ({ id: `support_tab:${item.id}`, label: item.name, path: `/support-workspace?custom=${item.id}`, item_type: "support_tab" as const }))].filter((item) => !favorites.some((favorite) => favorite.id === item.id)), [favorites, savedViews.data, support.data]);
  const persist = (nextFavorites = favorites, nextHidden = hidden) => save.mutate({ favorites: nextFavorites, recent: workspace.data?.recent ?? [], hidden_widgets: nextHidden });
  const toggleFavorite = (item: WorkspaceItem) => persist(favorites.some((favorite) => favorite.id === item.id) ? favorites.filter((favorite) => favorite.id !== item.id) : [...favorites, item]);
  const toggleWidget = (code: WidgetCode) => persist(favorites, hidden.includes(code) ? hidden.filter((item) => item !== code) : [...hidden, code]);
  const ItemCard = ({ item, removable = false }: { item: WorkspaceItem; removable?: boolean }) => <Card variant="outlined" sx={{ height: "100%" }}><CardActionArea onClick={() => navigate(item.path)} sx={{ height: "100%" }}><CardContent><Stack direction="row" justifyContent="space-between"><Box minWidth={0}><Chip size="small" label={item.item_type.replace("_", " ")} sx={{ mb: 1 }} /><Typography fontWeight={700}>{item.label}</Typography><Typography variant="body2" color="text.secondary" noWrap>{item.path}</Typography></Box>{removable && <IconButton size="small" onClick={(event) => { event.stopPropagation(); toggleFavorite(item); }}><DeleteOutline /></IconButton>}</Stack></CardContent></CardActionArea></Card>;
  const Widget = ({ code, icon, children, path }: { code: WidgetCode; icon: ReactNode; children: ReactNode; path: string }) => hidden.includes(code) ? null : <Paper variant="outlined" sx={{ p: 2.25, height: "100%", borderRadius: 3 }}><Stack direction="row" alignItems="center" gap={1} mb={1.5}>{icon}<Typography variant="h6" fontWeight={800}>{labels[code]}</Typography><Button size="small" onClick={() => navigate(path)} sx={{ ml: "auto" }}>Open</Button></Stack>{children}</Paper>;
  const schedule = [...(shifts.data ?? []).map((item) => ({ type: "Shift", title: item.shift_name, start: item.starts_at, end: item.ends_at, detail: `${item.work_location}${item.team ? ` · ${item.team}` : ""}`, color: item.shift_color })), ...(visits.data ?? []).flatMap((item) => item.assignments.slice(0, 1).map((assignment) => ({ type: "Visit", title: item.client_name || `Visit #${item.id}`, start: assignment.starts_at, end: assignment.ends_at, detail: item.status.replaceAll("_", " "), color: "#00897b" }))), ...(operations.data ?? []).map((item) => ({ type: "Operation", title: item.title, start: item.starts_at, end: item.ends_at, detail: item.status.replaceAll("_", " "), color: "#6a1b9a" }))].filter((item) => upcoming(item.end)).sort((a, b) => +new Date(a.start) - +new Date(b.start)).slice(0, 8);
  const isRefreshing = [workspace, tasks, supportCounts, shifts, visits, operations, approvals].some((query) => query.isFetching);
  const refresh = () => Promise.all([
    cache.invalidateQueries({ queryKey: ["my-workspace"] }),
    cache.invalidateQueries({ queryKey: ["workspace-work-assignments"] }),
    cache.invalidateQueries({ queryKey: ["workspace-support-counts"] }),
    cache.invalidateQueries({ queryKey: ["workspace-shifts"] }),
    cache.invalidateQueries({ queryKey: ["workspace-visits"] }),
    cache.invalidateQueries({ queryKey: ["workspace-operations"] }),
    cache.invalidateQueries({ queryKey: ["workspace-approvals"] }),
  ]);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const today = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date());
  const metrics = [
    { label: "Active tasks", value: tasks.data?.length, icon: <AssignmentTurnedIn />, color: "#1565c0", path: "/work-assignments" },
    { label: "My tickets", value: supportCounts.data?.mine, icon: <SupportAgent />, color: "#7b1fa2", path: "/tickets" },
    { label: "Upcoming", value: schedule.length, icon: <CalendarMonth />, color: "#00897b", path: "/internal-operations" },
    { label: "Approvals", value: approvals.data?.length, icon: <CheckCircle />, color: "#ed6c02", path: "/tickets?tab=approvals" },
  ];

  return <Stack spacing={3}>
    {(workspace.isLoading || save.isPending) && <LinearProgress />}
    <Paper sx={{ position: "relative", overflow: "hidden", p: { xs: 2.5, md: 3.5 }, borderRadius: 4, color: "common.white", background: "linear-gradient(120deg, #075985 0%, #0f766e 58%, #155e75 100%)" }}>
      <Box sx={{ position: "absolute", width: 260, height: 260, borderRadius: "50%", bgcolor: "rgba(255,255,255,.08)", insetInlineEnd: -70, top: -120 }} />
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ md: "center" }} gap={2} position="relative">
        <Box><Typography variant="overline" sx={{ opacity: .8, letterSpacing: 1.2 }}>{today}</Typography><Typography variant="h4" fontWeight={900}>{greeting}, {user?.full_name?.split(" ")[0] || "there"}</Typography><Typography sx={{ opacity: .86, mt: .5 }}>Your priorities, schedule, and shortcuts in one place.</Typography></Box>
        <Stack direction="row" gap={1} flexWrap="wrap"><Tooltip title="Refresh workspace data"><span><IconButton disabled={isRefreshing} onClick={refresh} sx={{ color: "inherit", border: "1px solid rgba(255,255,255,.35)" }}><Refresh sx={{ animation: isRefreshing ? "spin 1s linear infinite" : "none", "@keyframes spin": { to: { transform: "rotate(360deg)" } } }} /></IconButton></span></Tooltip><Button variant="outlined" color="inherit" startIcon={<Settings />} onClick={() => setCustomize(true)} sx={{ borderColor: "rgba(255,255,255,.45)" }}>Customize</Button></Stack>
      </Stack>
      <Stack direction="row" gap={1} mt={2.5} sx={{ overflowX: "auto", pb: .25, position: "relative" }}>{quickLinks.slice(0, 4).map((item) => <Chip key={item.id} clickable onClick={() => navigate(item.path)} label={item.label} sx={{ flexShrink: 0, color: "common.white", bgcolor: "rgba(255,255,255,.14)", "&:hover": { bgcolor: "rgba(255,255,255,.22)" } }} />)}</Stack>
    </Paper>
    {workspace.isError && <Alert severity="error">Your workspace could not be loaded.</Alert>}
    <Grid container spacing={2}>{metrics.map((metric) => <Grid key={metric.label} size={{ xs: 6, lg: 3 }}><Card variant="outlined" sx={{ height: "100%", borderRadius: 3 }}><CardActionArea onClick={() => navigate(metric.path)} sx={{ height: "100%" }}><CardContent><Stack direction="row" alignItems="center" gap={1.5}><Avatar sx={{ bgcolor: `${metric.color}18`, color: metric.color }}>{metric.icon}</Avatar><Box><Typography variant="h4" lineHeight={1} fontWeight={900}>{metric.value ?? "—"}</Typography><Typography variant="body2" color="text.secondary" mt={.5}>{metric.label}</Typography></Box><ArrowForward fontSize="small" sx={{ marginInlineStart: "auto", color: "text.disabled" }} /></Stack></CardContent></CardActionArea></Card></Grid>)}</Grid>
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, lg: 7 }}><Paper variant="outlined" sx={{ p: 2.25, borderRadius: 3, height: "100%" }}><Stack direction="row" alignItems="center" mb={1.5}><Box><Typography variant="h6" fontWeight={850}>Needs your attention</Typography><Typography variant="body2" color="text.secondary">Items that may require action today</Typography></Box></Stack><Divider sx={{ mb: 1.5 }} /><AttentionCenter limit={6} /></Paper></Grid>
      <Grid size={{ xs: 12, lg: 5 }}><Paper variant="outlined" sx={{ p: 2.25, height: "100%", borderRadius: 3 }}><Stack direction="row" gap={1} mb={2}><CalendarMonth color="primary"/><Box><Typography variant="h6" fontWeight={800}>Upcoming schedule</Typography><Typography variant="body2" color="text.secondary">Next seven days</Typography></Box></Stack>{schedule.length ? <Stack spacing={1}>{schedule.slice(0, 5).map((item, index) => <Stack key={`${item.type}:${item.start}:${index}`} direction="row" gap={1.5} alignItems="center" sx={{ p: 1.25, borderRadius: 2, bgcolor: "action.hover", borderInlineStart: `4px solid ${item.color}` }}><Box minWidth={92}><Typography variant="caption" color="text.secondary">{item.type}</Typography><Typography variant="body2" fontWeight={750}>{fmt(item.start)}</Typography></Box><Box minWidth={0}><Typography fontWeight={750} noWrap>{item.title}</Typography><Typography variant="caption" color="text.secondary" noWrap display="block">{item.detail}</Typography></Box></Stack>)}</Stack> : <Alert severity="info">Nothing is scheduled for the next seven days.</Alert>}</Paper></Grid>
    </Grid>
    <Box><Typography variant="h5" fontWeight={900}>My work</Typography><Typography color="text.secondary">Your assigned work and operational activity</Typography></Box>
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, md: 6 }}><Widget code="tasks" icon={<AssignmentTurnedIn color="primary" />} path="/work-assignments"><Rows rows={(tasks.data ?? []).slice(0, 5).map((item) => ({ id: item.id, title: item.title, detail: `${item.priority} · ${item.status.replaceAll("_", " ")}`, date: item.due_at ?? new Date().toISOString() }))} empty="No active assigned tasks." /></Widget></Grid>
      <Grid size={{ xs: 12, md: 6 }}><Widget code="support" icon={<SupportAgent color="primary" />} path="/support-workspace"><Grid container spacing={1}>{[["Mine", supportCounts.data?.mine], ["SLA risk", supportCounts.data?.risk], ["Follow-up", supportCounts.data?.followUp]].map(([label, value]) => <Grid key={String(label)} size={4}><Box sx={{ p: 1.2, bgcolor: "action.hover", borderRadius: 2 }}><Typography variant="h5" fontWeight={850}>{value ?? "—"}</Typography><Typography variant="caption">{label}</Typography></Box></Grid>)}</Grid></Widget></Grid>
      <Grid size={{ xs: 12, md: 6 }}><Widget code="shifts" icon={<CalendarMonth color="primary" />} path="/internal-operations?tab=shifts"><Rows rows={(shifts.data ?? []).slice(0, 3).map((item) => ({ id: item.id, title: item.shift_name, detail: `${item.work_location} · ${item.status}`, date: item.starts_at }))} empty="No upcoming shifts." /></Widget></Grid>
      <Grid size={{ xs: 12, md: 6 }}><Widget code="visits" icon={<DirectionsCar color="primary" />} path="/field-visits"><Rows rows={(visits.data ?? []).filter((item) => item.assignments.some((a) => upcoming(a.ends_at))).slice(0, 3).map((item) => ({ id: item.id, title: item.client_name || `Visit #${item.id}`, detail: item.status.replaceAll("_", " "), date: item.assignments[0]?.starts_at ?? item.window_start }))} empty="No upcoming visits." /></Widget></Grid>
      <Grid size={{ xs: 12, md: 6 }}><Widget code="operations" icon={<WorkHistory color="primary" />} path="/internal-operations"><Rows rows={(operations.data ?? []).slice(0, 3).map((item) => ({ id: item.id, title: item.title, detail: item.client_name || item.status.replaceAll("_", " "), date: item.starts_at }))} empty="No upcoming operations." /></Widget></Grid>
      <Grid size={{ xs: 12, md: 6 }}><Widget code="approvals" icon={<CheckCircle color="primary" />} path="/tickets?tab=approvals">{approvals.data?.slice(0, 3).map((item) => <Button key={item.id} fullWidth sx={{ justifyContent: "space-between" }} onClick={() => item.ticket_id && navigate(`/tickets/${item.ticket_id}`)}>{item.ticket_id ? `Ticket #${item.ticket_id}` : `Request #${item.id}`}<Chip size="small" label={item.requested_action.replaceAll("_", " ")} /></Button>)}{!approvals.data?.length && <Typography color="text.secondary">No approvals waiting for you.</Typography>}</Widget></Grid>
    </Grid>
    <Box><Typography variant="h5" fontWeight={900}>Shortcuts and history</Typography><Typography color="text.secondary">Continue where you left off or open a saved destination</Typography></Box>
    <Paper variant="outlined" sx={{ borderRadius: 3, overflow: "hidden" }}><Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto"><Tab icon={<Bookmark />} iconPosition="start" label={`Favorites (${favorites.length})`} /><Tab icon={<ViewList />} iconPosition="start" label="Saved views & tabs" /><Tab icon={<PushPin />} iconPosition="start" label={`Pinned tickets (${support.data?.pinned_ticket_ids.length ?? 0})`} /><Tab icon={<History />} iconPosition="start" label="Recent" /></Tabs></Paper>
    {tab === 0 && <Box>{favorites.length ? <Grid container spacing={2}>{favorites.map((item) => <Grid key={item.id} size={{ xs: 12, sm: 6, lg: 4 }}><ItemCard item={item} removable /></Grid>)}</Grid> : <Alert severity="info">Add pages, saved views, or Support Assistant tabs below.</Alert>}<Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Add to workspace</Typography><Grid container spacing={1}>{available.map((item) => <Grid key={item.id} size={{ xs: 12, sm: 6, lg: 4 }}><Button fullWidth variant="outlined" startIcon={<Add />} onClick={() => toggleFavorite(item)} sx={{ justifyContent: "flex-start" }}>{item.label}</Button></Grid>)}</Grid></Box>}
    {tab === 1 && <Grid container spacing={2}>{available.filter((item) => ["saved_view", "support_tab"].includes(item.item_type)).map((item) => <Grid key={item.id} size={{ xs: 12, sm: 6, lg: 4 }}><ItemCard item={item} /></Grid>)}</Grid>}
    {tab === 2 && <Grid container spacing={2}>{(support.data?.pinned_ticket_ids ?? []).map((id) => <Grid key={id} size={{ xs: 12, sm: 6, lg: 4 }}><ItemCard item={{ id: `ticket:${id}`, label: `Ticket #${id}`, path: `/tickets/${id}`, item_type: "ticket" }} /></Grid>)}</Grid>}
    {tab === 3 && <Grid container spacing={2}>{(workspace.data?.recent ?? []).map((item) => <Grid key={`${item.id}:${item.visited_at}`} size={{ xs: 12, sm: 6, lg: 4 }}><ItemCard item={item} /></Grid>)}</Grid>}
    <Dialog open={customize} onClose={() => setCustomize(false)} fullWidth maxWidth="xs"><DialogTitle>Customize My Workspace</DialogTitle><DialogContent><Typography variant="body2" color="text.secondary" mb={1}>Choose the widgets shown on your personal page.</Typography>{(Object.keys(labels) as WidgetCode[]).map((code) => <FormControlLabel key={code} control={<Checkbox checked={!hidden.includes(code)} onChange={() => toggleWidget(code)} />} label={labels[code]} />)}</DialogContent><DialogActions><Button onClick={() => setCustomize(false)}>Done</Button></DialogActions></Dialog>
  </Stack>;
}

function Rows({ rows, empty }: { rows: Array<{ id: number; title: string; detail: string; date: string }>; empty: string }) {
  if (!rows.length) return <Typography color="text.secondary">{empty}</Typography>;
  return <>{rows.map((item) => <Stack key={item.id} direction="row" justifyContent="space-between" gap={1} py={.75}><Box minWidth={0}><Typography fontWeight={700} noWrap>{item.title}</Typography><Typography variant="caption">{item.detail}</Typography></Box><Typography variant="body2" whiteSpace="nowrap">{fmt(item.date)}</Typography></Stack>)}</>;
}
