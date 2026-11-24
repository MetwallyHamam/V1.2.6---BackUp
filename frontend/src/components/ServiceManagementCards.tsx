import { AccountTree, BugReport, PublishedWithChanges } from "@mui/icons-material";
import { Alert, Button, Card, CardActionArea, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, List, ListItem, ListItemButton, ListItemText, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export type ServiceManagementCategory = "incidents" | "changes" | "problems";
type MetricRecord = { id: number; number: string; title: string; route: string; status_code?: string; version?: number; can_acknowledge?: boolean; can_resolve?: boolean };
type Metric = { count: number; records: MetricRecord[] };
export type ServiceManagementFilters = { date_from?: string; date_to?: string; client_id?: string | number; product_id?: string | number; department_id?: string | number; engineer_id?: string | number; team_id?: string | number; country_id?: string | number; zone?: string; location_id?: string | number };

export const serviceManagementWidgetCodes: Record<ServiceManagementCategory, string> = {
  incidents: "service_incidents",
  changes: "service_change_requests",
  problems: "service_problems",
};

export function ServiceManagementWidget({ category, filters = {}, portal = false }: {
  category: ServiceManagementCategory;
  filters?: ServiceManagementFilters;
  portal?: boolean;
}) {
  const { user } = useAuth();
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [resolving, setResolving] = useState<MetricRecord | null>(null);
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [rootCauseSummary, setRootCauseSummary] = useState("");
  const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined && value !== ""));
  const metrics = useQuery({
    queryKey: ["service-management-dashboard-cards", user?.id, params],
    queryFn: async () => (await api.get<Partial<Record<ServiceManagementCategory, Metric>>>("/service-management/dashboard-cards", { params })).data,
    enabled: !filters.date_from || !filters.date_to || filters.date_from <= filters.date_to,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  const arabic = i18n.resolvedLanguage === "ar";
  const names: Record<ServiceManagementCategory, string> = arabic
    ? { incidents: "الحوادث", changes: "طلبات التغيير", problems: "المشكلات" }
    : { incidents: "Incidents", changes: "Change Requests", problems: "Problems" };
  const icons = { incidents: <BugReport color="error" />, changes: <PublishedWithChanges color="primary" />, problems: <AccountTree color="warning" /> };
  const metric = metrics.data?.[category];
  const transition = useMutation({
    mutationFn: async ({ row, target }: { row: MetricRecord; target: "IN_PROGRESS" | "RESOLVED" }) => api.post(`/tickets/${row.id}/transition`, {
      to_status_code: target,
      version: row.version,
      resolution_summary: target === "RESOLVED" ? resolutionSummary : null,
      root_cause_summary: target === "RESOLVED" ? rootCauseSummary : null,
    }),
    onSuccess: async () => {
      setError(""); setResolving(null); setResolutionSummary(""); setRootCauseSummary("");
      await cache.invalidateQueries({ queryKey: ["service-management-dashboard-cards"] });
    },
    onError: (cause) => setError(apiErrorMessage(cause, "The incident could not be updated.")),
  });
  if (metrics.isError) return <Alert severity="warning">{arabic ? "تعذر تحميل ملخص إدارة الخدمة." : "Service management count could not be loaded."}</Alert>;
  if (!metrics.isLoading && !metric) return null;
  return <>
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardActionArea disabled={!metric} onClick={() => setOpen(true)} sx={{ height: "100%" }}>
        <CardContent>
          {icons[category]}
          <Typography variant="h4" fontWeight={800}>{metric?.count ?? "…"}</Typography>
          <Typography>{names[category]}</Typography>
          <Typography variant="caption" color="text.secondary">{arabic ? "عرض السجلات" : "View records"}</Typography>
        </CardContent>
      </CardActionArea>
    </Card>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
      <DialogTitle>{names[category]} · {metric?.count ?? 0}</DialogTitle>
      <DialogContent>
        {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
        {portal && category === "problems" && <Alert severity="info">{arabic ? "طلباتك المرتبطة بتحقيقات المشكلات. عدد المشكلات يحسب كل تحقيق مرة واحدة." : "Your requests linked to Problem investigations. The widget counts each investigation once."}</Alert>}
        {!metric?.records.length && <Typography color="text.secondary">{arabic ? "لا توجد سجلات في الفترة المحددة." : "No records in the selected period."}</Typography>}
        <List>{metric?.records.map((row) => <ListItem key={row.id} disablePadding divider><Stack direction={{ xs: "column", sm: "row" }} alignItems={{ sm: "center" }} gap={1} width="100%" py={0.5}>
          <ListItemButton onClick={() => { setOpen(false); navigate(row.route); }} sx={{ flex: 1 }}><ListItemText primary={<Stack direction="row" gap={1} alignItems="center"><span>{row.number}</span>{row.status_code && <Chip size="small" label={row.status_code.replaceAll("_", " ")} />}</Stack>} secondary={row.title} /></ListItemButton>
          {!portal && category === "incidents" && <Stack direction="row" gap={1} px={1}>{row.can_acknowledge && <Button size="small" variant="outlined" disabled={transition.isPending} onClick={() => transition.mutate({ row, target: "IN_PROGRESS" })}>Acknowledge</Button>}{row.can_resolve && <Button size="small" variant="contained" color="success" disabled={transition.isPending} onClick={() => { setResolving(row); setError(""); }}>Resolve</Button>}</Stack>}
        </Stack></ListItem>)}</List>
        {(metric?.count ?? 0) > 100 && <Typography variant="caption">{arabic ? "تُعرض أحدث 100 سجل." : "Showing the latest 100 records."}</Typography>}
      </DialogContent>
      <DialogActions><Button onClick={() => setOpen(false)}>{arabic ? "إغلاق" : "Close"}</Button></DialogActions>
    </Dialog>
    <Dialog open={resolving !== null} onClose={() => setResolving(null)} fullWidth maxWidth="sm">
      <DialogTitle>Resolve {resolving?.number}</DialogTitle>
      <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>{error && <Alert severity="error">{error}</Alert>}<TextField required multiline minRows={3} label="Resolution summary" value={resolutionSummary} onChange={(event) => setResolutionSummary(event.target.value)} /><TextField required multiline minRows={3} label="Root cause summary" value={rootCauseSummary} onChange={(event) => setRootCauseSummary(event.target.value)} /></Stack></DialogContent>
      <DialogActions><Button onClick={() => setResolving(null)}>Cancel</Button><Button variant="contained" color="success" disabled={!resolving || resolutionSummary.trim().length < 5 || rootCauseSummary.trim().length < 5 || transition.isPending} onClick={() => resolving && transition.mutate({ row: resolving, target: "RESOLVED" })}>Resolve incident</Button></DialogActions>
    </Dialog>
  </>;
}
