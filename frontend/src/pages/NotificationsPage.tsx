import { ArrowForward, DeleteOutline, DoneAll, FilterList, NotificationsActive, Settings } from "@mui/icons-material";
import { Alert, Box, Button, Checkbox, Chip, Collapse, Divider, MenuItem, Paper, Slider, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { AttentionCenter } from "../components/AttentionCenter";
import { DataListToolbar } from "../components/DataListToolbar";
import { playNotificationSound } from "../utils/notificationSound";

type Notification = { id: number; notification_type: string; severity: string; title: string; message: string; deep_link?: string; is_read: boolean; created_at: string };
type SavedView = { id: number; name: string; filters_json: string; is_default: boolean };
type Preferences = { sound_enabled: boolean; desktop_enabled: boolean; sound_code: string; volume_percent: number };
type Filters = { date_scope: "TODAY" | "ALL"; date_from: string; date_to: string; is_read: string; severity: string; notification_type: string; search: string };
const todayFilters: Filters = { date_scope: "TODAY", date_from: "", date_to: "", is_read: "", severity: "", notification_type: "", search: "" };

export function NotificationsPage() {
  const { i18n, t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = (location.state as { returnTo?: string } | null)?.returnTo;
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [filters, setFilters] = useState<Filters>(todayFilters);
  const [selected, setSelected] = useState<number[]>([]);
  const [viewName, setViewName] = useState("");
  const [sound, setSound] = useState("CHIME");
  const [volume, setVolume] = useState(70);
  const params = { ...filters, is_read: filters.is_read === "" ? undefined : filters.is_read === "true", date_from: filters.date_from || undefined, date_to: filters.date_to || undefined, notification_type: filters.notification_type || undefined, severity: filters.severity || undefined, search: filters.search || undefined };
  const query = useQuery({ queryKey: ["notifications", filters], queryFn: async () => (await api.get<Notification[]>("/notifications", { params })).data });
  const views = useQuery({ queryKey: ["notification-views"], queryFn: async () => (await api.get<SavedView[]>("/notification-views")).data });
  const preferences = useQuery({ queryKey: ["notification-preferences"], queryFn: async () => (await api.get<Preferences>("/notification-preferences/me")).data });
  useEffect(() => { if (preferences.data) { setSound(preferences.data.sound_code); setVolume(preferences.data.volume_percent); } }, [preferences.data]);
  useEffect(() => { const defaultView = views.data?.find((view) => view.is_default); if (defaultView) setFilters({ ...todayFilters, ...JSON.parse(defaultView.filters_json) }); }, [views.data]);
  useEffect(() => setSelected((current) => current.filter((id) => query.data?.some((item) => item.id === id))), [query.data]);
  const refresh = async () => { await queryClient.invalidateQueries({ queryKey: ["notifications"] }); };
  const read = useMutation({ mutationFn: async (id: number) => api.post(`/notifications/${id}/read`), onSuccess: refresh });
  const dismiss = useMutation({ mutationFn: async (id: number) => api.post(`/notifications/${id}/dismiss`), onSuccess: refresh });
  const bulkRead = useMutation({ mutationFn: async () => api.post("/notifications/bulk-read", { ids: selected }), onSuccess: async () => { setSelected([]); await refresh(); } });
  const bulkDismiss = useMutation({ mutationFn: async () => api.post("/notifications/bulk-dismiss", { ids: selected }), onSuccess: async () => { setSelected([]); await refresh(); } });
  const markAll = useMutation({ mutationFn: async (filtered: boolean) => api.post("/notifications/mark-all-read", null, { params: { ...params, filtered } }), onSuccess: refresh });
  const saveView = useMutation({ mutationFn: async () => api.post("/notification-views", { name: viewName, filters, is_default: false }), onSuccess: async () => { setViewName(""); await queryClient.invalidateQueries({ queryKey: ["notification-views"] }); } });
  const removeView = useMutation({ mutationFn: async (id: number) => api.delete(`/notification-views/${id}`), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["notification-views"] }) });
  const saveSound = useMutation({ mutationFn: async () => api.put("/notification-preferences/me", { sound_enabled: preferences.data?.sound_enabled ?? true, desktop_enabled: preferences.data?.desktop_enabled ?? false, sound_code: sound, volume_percent: volume }), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["notification-preferences"] }) });
  const update = (key: keyof Filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));
  const types = [...new Set((query.data ?? []).map((item) => item.notification_type))];
  const groups = useMemo(() => [
    { key: "CRITICAL", title: t("notifications.urgent", { defaultValue: "Urgent" }), items: (query.data ?? []).filter((item) => item.severity === "CRITICAL") },
    { key: "WARNING", title: t("notifications.actionRequired", { defaultValue: "Action required" }), items: (query.data ?? []).filter((item) => item.severity === "WARNING") },
    { key: "INFO", title: t("notifications.updates", { defaultValue: "Updates" }), items: (query.data ?? []).filter((item) => !["CRITICAL", "WARNING"].includes(item.severity)) },
  ].filter((group) => group.items.length), [query.data, t]);
  const activeFilterCount = Object.entries(filters).filter(([key, value]) => value && !((key === "date_scope") && value === "TODAY")).length;
  const openNotification = (item: Notification) => { if (!item.is_read) read.mutate(item.id); if (item.deep_link) navigate(item.deep_link); };

  return <Stack spacing={2} sx={{ maxWidth: 1100, mx: "auto" }}>
    <Paper sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack direction="row" alignItems="center" gap={1} mb={0.5}><Button size="small" onClick={() => returnTo ? navigate(returnTo) : navigate("/support-workspace")}>{t("common.back")}</Button><Typography variant="h4" sx={{ flexGrow: 1 }}>{t("notifications.title")}</Typography><Button size="small" startIcon={<Settings />} onClick={() => setPreferencesOpen((value) => !value)}>{t("notifications.preferences", { defaultValue: "Preferences" })}</Button></Stack>
      <Typography color="text.secondary" mb={2}>{t("notifications.subtitle")}</Typography>
      <DataListToolbar search={filters.search} onSearchChange={(value) => update("search", value)} searchLabel={t("notifications.search")} filterValue={filters.is_read} onFilterChange={(value) => update("is_read", value)} filterLabel={t("notifications.readStatus")} filterOptions={[{ value: "", label: t("notifications.all") }, { value: "false", label: t("notifications.unread") }, { value: "true", label: t("notifications.read") }]} activeFilterCount={activeFilterCount} onClear={() => setFilters(todayFilters)} clearLabel={t("notifications.resetToday")} actions={<Button startIcon={<FilterList />} onClick={() => setFiltersOpen((value) => !value)}>{filtersOpen ? t("notifications.hideFilters", { defaultValue: "Hide filters" }) : t("notifications.showFilters", { defaultValue: "More filters" })}</Button>} />
      <Collapse in={filtersOpen}><Stack direction={{ xs: "column", md: "row" }} gap={1} flexWrap="wrap"><TextField select size="small" label={t("notifications.period")} value={filters.date_scope} onChange={(event) => update("date_scope", event.target.value)}><MenuItem value="TODAY">{t("notifications.today")}</MenuItem><MenuItem value="ALL">{t("notifications.allDates")}</MenuItem></TextField><TextField size="small" type="date" label={t("notifications.from")} value={filters.date_from} onChange={(event) => update("date_from", event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /><TextField size="small" type="date" label={t("notifications.to")} value={filters.date_to} onChange={(event) => update("date_to", event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /><TextField select size="small" label={t("notifications.severity")} value={filters.severity} onChange={(event) => update("severity", event.target.value)}><MenuItem value="">{t("notifications.all")}</MenuItem>{["INFO", "WARNING", "CRITICAL"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField><TextField select size="small" label={t("notifications.type")} value={filters.notification_type} onChange={(event) => update("notification_type", event.target.value)} sx={{ minWidth: 180 }}><MenuItem value="">{t("notifications.allTypes")}</MenuItem>{types.map((value) => <MenuItem key={value} value={value}>{value.replaceAll("_", " ")}</MenuItem>)}</TextField></Stack><Stack direction="row" gap={1} mt={2} flexWrap="wrap"><Button variant="outlined" onClick={() => markAll.mutate(true)} disabled={markAll.isPending}>{t("notifications.markFiltered")}</Button><Button onClick={() => markAll.mutate(false)} disabled={markAll.isPending}>{t("notifications.markAll")}</Button><TextField size="small" label={t("notifications.viewName")} value={viewName} onChange={(event) => setViewName(event.target.value)} /><Button variant="contained" disabled={viewName.trim().length < 2} onClick={() => saveView.mutate()}>{t("notifications.saveView")}</Button></Stack><Stack direction="row" gap={1} mt={1} flexWrap="wrap">{views.data?.map((view) => <Chip key={view.id} label={view.name} color={view.is_default ? "primary" : "default"} onClick={() => setFilters({ ...todayFilters, ...JSON.parse(view.filters_json) })} onDelete={() => removeView.mutate(view.id)} />)}</Stack></Collapse>
      <Collapse in={preferencesOpen}><Divider sx={{ my: 2 }} /><Typography variant="h6">{t("notifications.soundTitle")}</Typography><Stack direction={{ xs: "column", sm: "row" }} gap={2} alignItems={{ sm: "center" }} mt={1}><TextField select size="small" label={t("notifications.tone")} value={sound} onChange={(event) => setSound(event.target.value)} sx={{ minWidth: 160 }}>{["CHIME", "BELL", "SOFT", "ALERT"].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField><Slider value={volume} onChange={(_, value) => setVolume(value as number)} min={0} max={100} valueLabelDisplay="auto" sx={{ maxWidth: 300 }} /><Button onClick={() => playNotificationSound(sound, volume)}>{t("notifications.play")}</Button><Button variant="contained" onClick={() => saveSound.mutate()}>{t("notifications.saveSound")}</Button></Stack></Collapse>
    </Paper>
    <Paper sx={{ p: 2 }}><Typography variant="h6" fontWeight={850} mb={1}>{t("notifications.attention", { defaultValue: "Needs your attention" })}</Typography><AttentionCenter limit={10} compact /></Paper>
    {selected.length > 0 && <Paper elevation={4} sx={{ position: "sticky", top: 56, zIndex: 4, p: 1.25 }}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={800} sx={{ flexGrow: 1 }}>{t("notifications.selected", { count: selected.length, defaultValue: "{{count}} selected" })}</Typography><Button startIcon={<DoneAll />} disabled={bulkRead.isPending} onClick={() => bulkRead.mutate()}>{t("notifications.markRead")}</Button><Button color="error" startIcon={<DeleteOutline />} disabled={bulkDismiss.isPending} onClick={() => bulkDismiss.mutate()}>{t("notifications.dismiss", { defaultValue: "Dismiss" })}</Button></Stack></Paper>}
    {query.isError && <Alert severity="error">{t("notifications.loadFailed")}</Alert>}
    {!query.isLoading && query.data?.length === 0 && <Alert severity="info">{t("notifications.empty")}</Alert>}
    {groups.map((group) => <Box key={group.key}><Stack direction="row" alignItems="center" gap={1} mb={1}><NotificationsActive color={group.key === "CRITICAL" ? "error" : group.key === "WARNING" ? "warning" : "action"} /><Typography variant="h6" fontWeight={850}>{group.title}</Typography><Chip size="small" label={group.items.length} /></Stack><Stack spacing={1}>{group.items.map((item) => <Paper variant="outlined" key={item.id} sx={{ p: { xs: 1.25, sm: 2 }, bgcolor: item.is_read ? "background.paper" : "action.hover", borderInlineStart: 4, borderInlineStartColor: item.severity === "CRITICAL" ? "error.main" : item.severity === "WARNING" ? "warning.main" : "info.main" }}><Stack direction="row" spacing={1} alignItems="flex-start"><Checkbox size="small" checked={selected.includes(item.id)} onChange={() => setSelected((current) => current.includes(item.id) ? current.filter((id) => id !== item.id) : [...current, item.id])} inputProps={{ "aria-label": t("notifications.select", { title: item.title, defaultValue: `Select ${item.title}` }) }} /><Box sx={{ flexGrow: 1, minWidth: 0 }}><Stack direction={{ xs: "column", sm: "row" }} gap={0.5} alignItems={{ sm: "center" }}><Typography variant="h6" fontWeight={item.is_read ? 650 : 850} sx={{ flexGrow: 1 }}>{item.title}</Typography><Typography variant="caption" color="text.secondary">{new Date(item.created_at).toLocaleString(i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB")}</Typography></Stack><Typography color="text.secondary">{item.message}</Typography><Stack direction="row" spacing={1} mt={1} flexWrap="wrap">{item.deep_link && <Button size="small" variant={item.is_read ? "text" : "contained"} endIcon={<ArrowForward />} onClick={() => openNotification(item)}>{t("notifications.open")}</Button>}{!item.is_read && <Button size="small" onClick={() => read.mutate(item.id)}>{t("notifications.markRead")}</Button>}<Button size="small" color="inherit" onClick={() => dismiss.mutate(item.id)}>{t("notifications.dismiss", { defaultValue: "Dismiss" })}</Button></Stack></Box></Stack></Paper>)}</Stack></Box>)}
  </Stack>;
}
