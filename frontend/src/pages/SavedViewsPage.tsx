import { ContentCopy, Delete, OpenInNew, Star, StarBorder } from "@mui/icons-material";
import { Alert, Box, Button, Chip, IconButton, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography, useMediaQuery, useTheme } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { DataListToolbar } from "../components/DataListToolbar";

type View = { id: number; owner_user_id: number; name: string; scope: string; team_id?: number; department_id?: number; filter_json: string; columns_json?: string; sort_json?: string; has_layout: boolean; is_default: boolean };
type Team = { id: number; name: string };
type WorkspaceItem = { id: string; label: string; path: string; item_type: "saved_view" };
type Workspace = { favorites: WorkspaceItem[]; recent: WorkspaceItem[]; hidden_widgets: string[] };

export function SavedViewsPage() {
  const { t } = useTranslation();
  const { user, hasPermission } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const mobile = useMediaQuery(useTheme().breakpoints.down("sm"));
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState("ALL");
  const query = useQuery({ queryKey: ["saved-views"], queryFn: async () => (await api.get<View[]>("/saved-views")).data });
  const workspace = useQuery({ queryKey: ["my-workspace"], queryFn: async () => (await api.get<Workspace>("/tickets/my-workspace")).data });
  const teams = useQuery({ queryKey: ["support-teams"], queryFn: async () => (await api.get<Team[]>("/support-teams")).data });
  const remove = useMutation({ mutationFn: async (id: number) => api.delete(`/saved-views/${id}`), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["saved-views"] }) });
  const makeDefault = useMutation({ mutationFn: async (id: number) => api.patch(`/saved-views/${id}/default`), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["saved-views"] }) });
  const addDepartmentQueues = useMutation({ mutationFn: async () => api.post("/saved-views/department-defaults"), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["saved-views"] }) });
  const duplicateName = (view: View) => { const base = `${view.name} (${t("savedViewsPage.copy", { defaultValue: "Copy" })})`; const names = new Set((query.data ?? []).map((item) => item.name)); if (!names.has(base)) return base; let suffix = 2; while (names.has(`${base} ${suffix}`)) suffix += 1; return `${base} ${suffix}`; };
  const duplicate = useMutation({ mutationFn: async (view: View) => api.post("/saved-views", { name: duplicateName(view), scope: "PRIVATE", filters: JSON.parse(view.filter_json), columns: JSON.parse(view.columns_json || "[]"), sort: JSON.parse(view.sort_json || "[]"), has_layout: view.has_layout, is_default: false }), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["saved-views"] }) });
  const saveWorkspace = useMutation({ mutationFn: async (favorites: WorkspaceItem[]) => (await api.put<Workspace>("/tickets/my-workspace", { favorites, hidden_widgets: workspace.data?.hidden_widgets ?? [] })).data, onSuccess: (data) => queryClient.setQueryData(["my-workspace"], data) });
  const filtered = useMemo(() => (query.data ?? []).filter((view) => view.name.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()) && (scope === "ALL" || view.scope === scope)), [query.data, scope, search]);
  const openView = (view: View) => navigate(`/tickets?${new URLSearchParams(JSON.parse(view.filter_json) as Record<string, string>).toString()}`);
  const scopeLabel = (view: View) => view.scope === "TEAM" ? t("savedViewsPage.team", { name: teams.data?.find((team) => team.id === view.team_id)?.name ?? `#${view.team_id}` }) : t(`savedViewsPage.scopes.${view.scope}`, { defaultValue: view.scope });
  const filtersLabel = (view: View) => Object.entries(JSON.parse(view.filter_json) as Record<string, string>).map(([key, value]) => t("savedViewsPage.filter", { key: t(`savedViewsPage.filterKeys.${key}`, { defaultValue: key.replaceAll("_", " ") }), value })).join(", ") || t("savedViewsPage.noFilters");
  const canDelete = (view: View) => view.owner_user_id === user?.id || (view.scope === "GLOBAL" && hasPermission("configuration.manage"));
  const favoriteItem = (view: View): WorkspaceItem => ({ id: `saved_view:${view.id}`, label: view.name, path: `/tickets?saved_view_id=${view.id}`, item_type: "saved_view" });
  const isFavorite = (view: View) => Boolean(workspace.data?.favorites.some((item) => item.id === `saved_view:${view.id}`));
  const toggleFavorite = (view: View) => { const item = favoriteItem(view); const current = workspace.data?.favorites ?? []; saveWorkspace.mutate(isFavorite(view) ? current.filter((favorite) => favorite.id !== item.id) : [...current, item]); };

  const actions = (view: View) => <Stack direction="row" justifyContent="flex-end">
    <Button size="small" startIcon={<OpenInNew />} onClick={() => openView(view)}>{t("savedViewsPage.open")}</Button>
    <IconButton size="small" aria-label={t("savedViewsPage.favorite", { name: view.name, defaultValue: `Favorite ${view.name}` })} color={isFavorite(view) ? "warning" : "default"} onClick={() => toggleFavorite(view)}>{isFavorite(view) ? <Star /> : <StarBorder />}</IconButton>
    <IconButton size="small" aria-label={t("savedViewsPage.duplicate", { name: view.name, defaultValue: `Duplicate ${view.name}` })} onClick={() => duplicate.mutate(view)}><ContentCopy /></IconButton>
    {canDelete(view) && <IconButton size="small" aria-label={t("savedViewsPage.delete", { name: view.name })} color="error" onClick={() => remove.mutate(view.id)}><Delete /></IconButton>}
  </Stack>;

  return <Paper sx={{ p: { xs: 1.5, sm: 3 }, minWidth: 0, overflow: "hidden" }}>
    <Typography variant="h4" gutterBottom>{t("savedViewsPage.title")}</Typography>
    <Typography color="text.secondary" mb={2}>{t("savedViewsPage.subtitle")}</Typography>
    <DataListToolbar search={search} onSearchChange={setSearch} searchLabel={t("savedViewsPage.search", { defaultValue: "Search saved views" })} filterValue={scope} onFilterChange={setScope} filterLabel={t("savedViewsPage.scopeFilter", { defaultValue: "Scope" })} filterOptions={["ALL", "PRIVATE", "TEAM", "DEPARTMENT", "GLOBAL"].map((value) => ({ value, label: value === "ALL" ? t("savedViewsPage.allScopes", { defaultValue: "All scopes" }) : t(`savedViewsPage.scopes.${value}`, { defaultValue: value === "PRIVATE" ? "Personal" : value.charAt(0) + value.slice(1).toLowerCase() }) }))} activeFilterCount={(scope === "ALL" ? 0 : 1) + (search.trim() ? 1 : 0)} onClear={() => { setSearch(""); setScope("ALL"); }} clearLabel={t("savedViewsPage.clearFilters", { defaultValue: "Clear filters" })} actions={user?.user_type === "EMPLOYEE" ? <Button variant="outlined" disabled={addDepartmentQueues.isPending} onClick={() => addDepartmentQueues.mutate()}>{t(addDepartmentQueues.isPending ? "savedViewsPage.adding" : "savedViewsPage.addQueues")}</Button> : undefined} />
    {query.isError && <Alert severity="error">{t("savedViewsPage.loadFailed")}</Alert>}
    {remove.isError && <Alert severity="error" sx={{ mb: 2 }}>{t("savedViewsPage.removeFailed")}</Alert>}
    {!query.isLoading && query.data?.length === 0 && <Alert severity="info">{t("savedViewsPage.empty")}</Alert>}
    {!query.isLoading && !!query.data?.length && filtered.length === 0 && <Alert severity="info">{t("savedViewsPage.noMatches", { defaultValue: "No views match these filters." })}</Alert>}
    {!mobile && filtered.length > 0 && <Box role="region" aria-label={t("savedViewsPage.region")} tabIndex={0} sx={{ overflowX: "auto", maxWidth: "100%", WebkitOverflowScrolling: "touch" }}>
      <Table sx={{ minWidth: 720 }}><TableHead><TableRow>{(["name", "scope", "filters", "default", "actions"] as const).map((column) => <TableCell key={column} align={column === "actions" ? "right" : "left"}>{t(`savedViewsPage.columns.${column}`)}</TableCell>)}</TableRow></TableHead>
      <TableBody>{filtered.map((view) => <TableRow key={view.id} hover><TableCell><Typography fontWeight={700}>{view.name}</Typography></TableCell><TableCell>{scopeLabel(view)}</TableCell><TableCell sx={{ minWidth: 220, overflowWrap: "anywhere" }}>{filtersLabel(view)}</TableCell><TableCell>{view.is_default ? <Chip size="small" color="primary" label={t("savedViewsPage.yes")} /> : view.owner_user_id === user?.id ? <Button size="small" onClick={() => makeDefault.mutate(view.id)}>{t("savedViewsPage.makeDefault")}</Button> : "—"}</TableCell><TableCell align="right">{actions(view)}</TableCell></TableRow>)}</TableBody></Table>
    </Box>}
    {mobile && <Stack gap={1.25}>{filtered.map((view) => <Paper key={view.id} variant="outlined" sx={{ p: 1.5 }}><Stack direction="row" justifyContent="space-between" gap={1}><Box><Typography fontWeight={800}>{view.name}</Typography><Typography variant="caption" color="text.secondary">{scopeLabel(view)}</Typography></Box>{view.is_default && <Chip size="small" color="primary" label={t("savedViewsPage.yes")} />}</Stack><Typography variant="body2" color="text.secondary" sx={{ my: 1, overflowWrap: "anywhere" }}>{filtersLabel(view)}</Typography><Stack direction="row" justifyContent="space-between" alignItems="center">{!view.is_default && view.owner_user_id === user?.id ? <Button size="small" onClick={() => makeDefault.mutate(view.id)}>{t("savedViewsPage.makeDefault")}</Button> : <span />}{actions(view)}</Stack></Paper>)}</Stack>}
  </Paper>;
}
