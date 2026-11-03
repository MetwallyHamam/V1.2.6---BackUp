import { ErrorOutline, NotificationsActive, Schedule, Settings, Snooze, TaskAlt } from "@mui/icons-material";
import { Alert, Box, Button, Checkbox, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, IconButton, Paper, Stack, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export type AttentionCategory = "CRITICAL" | "ACTION_REQUIRED" | "DUE_SOON" | "WAITING" | "INFORMATION";
export type AttentionItem = { id: string; source: string; category: AttentionCategory; title: string; reason: string; due_at?: string | null; deep_link: string; primary_action: string };
export type AttentionResponse = { generated_at: string; total: number; counts: Record<AttentionCategory, number>; items: AttentionItem[] };
type AttentionPreferences = { enabled_categories: AttentionCategory[]; snoozed_until: Record<string, string> };
const categories: AttentionCategory[] = ["CRITICAL", "ACTION_REQUIRED", "DUE_SOON", "WAITING", "INFORMATION"];

export function useAttention(limit = 30) {
  return useQuery({ queryKey: ["unified-attention", limit], queryFn: async () => (await api.get<AttentionResponse>("/home/attention", { params: { limit } })).data, refetchInterval: 60_000, refetchIntervalInBackground: false });
}

const color = (category: AttentionCategory): "error" | "warning" | "info" | "default" => category === "CRITICAL" ? "error" : category === "ACTION_REQUIRED" ? "warning" : category === "DUE_SOON" ? "info" : "default";
const buttonColor = (category: AttentionCategory): "error" | "warning" | "info" | "inherit" => category === "CRITICAL" ? "error" : category === "ACTION_REQUIRED" ? "warning" : category === "DUE_SOON" ? "info" : "inherit";
const icon = (category: AttentionCategory) => category === "CRITICAL" ? <ErrorOutline color="error" /> : category === "ACTION_REQUIRED" ? <NotificationsActive color="warning" /> : category === "DUE_SOON" ? <Schedule color="info" /> : <TaskAlt color="action" />;

export function AttentionCenter({ limit = 8, compact = false }: { limit?: number; compact?: boolean }) {
  const navigate = useNavigate(), cache = useQueryClient(), query = useAttention(limit);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const preferences = useQuery({ queryKey: ["attention-preferences"], queryFn: async () => (await api.get<AttentionPreferences>("/home/attention/preferences")).data });
  const refresh = async () => { await Promise.all([cache.invalidateQueries({ queryKey: ["unified-attention"] }), cache.invalidateQueries({ queryKey: ["attention-preferences"] })]); };
  const snooze = useMutation({ mutationFn: async (itemId: string) => api.post("/home/attention/snooze", { item_id: itemId, minutes: 60 }), onSuccess: refresh });
  const saveCategories = useMutation({ mutationFn: async (enabled_categories: AttentionCategory[]) => api.put("/home/attention/preferences", { enabled_categories }), onSuccess: refresh });
  const clearSnoozed = useMutation({ mutationFn: async () => api.delete("/home/attention/snoozed"), onSuccess: refresh });
  const toggleCategory = (category: AttentionCategory) => { const current = preferences.data?.enabled_categories ?? categories; const next = current.includes(category) ? current.filter((item) => item !== category) : [...current, category]; if (next.length) saveCategories.mutate(next); };
  if (query.isLoading) return <Box sx={{ minHeight: 120, display: "grid", placeItems: "center" }}><CircularProgress size={28} /></Box>;
  if (query.isError) return <Alert severity="error">Attention items could not be loaded.</Alert>;
  const items = query.data?.items ?? [];
  return <Stack spacing={1}>
    <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">{!compact && (["CRITICAL", "ACTION_REQUIRED", "DUE_SOON"] as AttentionCategory[]).map((category) => <Chip key={category} size="small" color={color(category)} label={`${category.replaceAll("_", " ")} · ${query.data?.counts[category] ?? 0}`} />)}<IconButton size="small" sx={{ ml: "auto" }} aria-label="Attention settings" onClick={() => setSettingsOpen(true)}><Settings fontSize="small" /></IconButton></Stack>
    {!items.length && <Alert severity="success">Nothing currently needs your attention.</Alert>}
    {items.map((item) => <Paper key={item.id} variant="outlined" sx={{ p: compact ? 1.25 : 1.75, borderInlineStart: 4, borderInlineStartColor: `${color(item.category)}.main` }}><Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>{icon(item.category)}<Box flex={1} minWidth={0}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={800} noWrap>{item.title}</Typography><Chip size="small" variant="outlined" label={item.source} /></Stack><Typography variant="body2" color="text.secondary">{item.reason}{item.due_at ? ` · ${new Date(item.due_at).toLocaleString()}` : ""}</Typography></Box><Button size="small" variant={item.category === "CRITICAL" ? "contained" : "text"} color={buttonColor(item.category)} onClick={() => navigate(item.deep_link)}>{item.primary_action}</Button><Button size="small" color="inherit" startIcon={<Snooze />} disabled={snooze.isPending} onClick={() => snooze.mutate(item.id)}>1h</Button></Stack></Paper>)}
    <Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)} fullWidth maxWidth="xs"><DialogTitle>Attention preferences</DialogTitle><DialogContent><Typography variant="body2" color="text.secondary" mb={1}>Choose which categories appear in your attention center.</Typography>{categories.map((category) => <FormControlLabel key={category} control={<Checkbox checked={(preferences.data?.enabled_categories ?? categories).includes(category)} disabled={saveCategories.isPending} onChange={() => toggleCategory(category)} />} label={category.replaceAll("_", " ")} />)}<Button fullWidth variant="outlined" sx={{ mt: 2 }} disabled={!Object.keys(preferences.data?.snoozed_until ?? {}).length || clearSnoozed.isPending} onClick={() => clearSnoozed.mutate()}>Restore all snoozed items ({Object.keys(preferences.data?.snoozed_until ?? {}).length})</Button></DialogContent><DialogActions><Button onClick={() => setSettingsOpen(false)}>Done</Button></DialogActions></Dialog>
  </Stack>;
}
