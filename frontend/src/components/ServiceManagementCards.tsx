import { AccountTree, BugReport, PublishedWithChanges } from "@mui/icons-material";
import { Alert, Button, Card, CardActionArea, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, List, ListItemButton, ListItemText, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export type ServiceManagementCategory = "incidents" | "changes" | "problems";
type Metric = { count: number; records: Array<{ id: number; number: string; title: string; route: string }> };
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
  const [open, setOpen] = useState(false);
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
        {portal && category === "problems" && <Alert severity="info">{arabic ? "طلباتك المرتبطة بتحقيقات المشكلات. عدد المشكلات يحسب كل تحقيق مرة واحدة." : "Your requests linked to Problem investigations. The widget counts each investigation once."}</Alert>}
        {!metric?.records.length && <Typography color="text.secondary">{arabic ? "لا توجد سجلات في الفترة المحددة." : "No records in the selected period."}</Typography>}
        <List>{metric?.records.map((row) => <ListItemButton key={row.id} onClick={() => { setOpen(false); navigate(row.route); }}>
          <ListItemText primary={row.number} secondary={row.title} />
        </ListItemButton>)}</List>
        {(metric?.count ?? 0) > 100 && <Typography variant="caption">{arabic ? "تُعرض أحدث 100 سجل." : "Showing the latest 100 records."}</Typography>}
      </DialogContent>
      <DialogActions><Button onClick={() => setOpen(false)}>{arabic ? "إغلاق" : "Close"}</Button></DialogActions>
    </Dialog>
  </>;
}
