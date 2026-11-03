import {
  Add,
  ArrowDownward,
  ArrowUpward,
  ContentCopy,
  Edit,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";

type Widget = {
  widget_code: string;
  title: string;
  description: string;
  widget_type: "KPI_CARD" | "DONUT" | "STACKED_BAR" | "LINE";
  query_code: string;
  default_width: number;
  required_permissions: string[];
};
type ConfigWidget = {
  widget_code: string;
  title: string;
  widget_type: Widget["widget_type"];
  query_code: string;
  position: number;
  width: number;
  refresh_seconds: number;
  config: Record<string, unknown>;
};
type Template = {
  id: number;
  code?: string;
  name: string;
  description?: string;
  destination: "EXECUTIVE" | "TOP_MANAGEMENT";
  version: number;
  is_active: boolean;
  widgets: ConfigWidget[];
};
type Assignment = {
  id: number;
  dashboard_id: number;
  dashboard_type: "EXECUTIVE" | "TOP_MANAGEMENT";
  profile_id?: number;
  department_id?: number;
  user_id?: number;
  priority: number;
  effective_from?: string;
  effective_until?: string;
  is_active: boolean;
  version: number;
};
type AssignmentImpact = { assignment_id: number; affected_user_count: number };
type EffectiveDashboard = {
  user_id?: number;
  user_name?: string;
  profile_id?: number;
  department_id?: number;
  permission_codes: string[];
  source: string;
  name: string;
  template_code?: string;
  template_version: number;
  assignment_id?: number;
  resolution_explanation?: string;
  widgets: ConfigWidget[];
};
type Option = { id: number; name?: string; full_name?: string; code?: string };
type DashboardProfile = Option & {
  profile_type: string;
  effective_dashboard_source: string;
  effective_dashboard_name?: string;
};

export function DashboardAdminPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [templateOpen, setTemplateOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const [draftWidgets, setDraftWidgets] = useState<ConfigWidget[]>([]);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [adminArea, setAdminArea] = useState<"DESIGNER" | "CATALOG">("DESIGNER");
  const [targetType, setTargetType] = useState("PROFILE");
  const [adminDestination, setAdminDestination] = useState<"EXECUTIVE" | "TOP_MANAGEMENT">("EXECUTIVE");
  const [previewUserId, setPreviewUserId] = useState("");
  const [previewProfileId, setPreviewProfileId] = useState("");
  const [previewDepartmentId, setPreviewDepartmentId] = useState("");
  const [error, setError] = useState("");
  const templates = useQuery({
    queryKey: ["dashboard-admin-templates"],
    queryFn: async () =>
      (await api.get<Template[]>("/dashboards/admin/templates")).data,
  });
  const assignments = useQuery({
    queryKey: ["dashboard-admin-assignments"],
    queryFn: async () =>
      (await api.get<Assignment[]>("/dashboards/admin/assignments")).data,
  });
  const assignmentImpact = useQuery({
    queryKey: ["dashboard-admin-assignment-impact"],
    queryFn: async () =>
      (await api.get<AssignmentImpact[]>("/dashboards/admin/assignment-impact")).data,
  });
  const catalog = useQuery({
    queryKey: ["dashboard-widget-catalog"],
    queryFn: async () =>
      (await api.get<Widget[]>("/dashboards/widget-catalog")).data,
  });
  const profiles = useQuery({
    queryKey: ["profiles", "dashboard-admin"],
    queryFn: async () => (await api.get<DashboardProfile[]>("/profiles")).data,
  });
  const departments = useQuery({
    queryKey: ["departments", "dashboard-admin"],
    queryFn: async () => (await api.get<Option[]>("/departments")).data,
  });
  const users = useQuery({
    queryKey: ["users", "dashboard-admin"],
    queryFn: async () => (await api.get<Option[]>("/users")).data,
  });
  const preview = useQuery({
    queryKey: ["dashboard-admin-preview", previewUserId, adminDestination],
    queryFn: async () =>
      (
        await api.get<EffectiveDashboard>("/dashboards/admin/preview", {
          params: { user_id: Number(previewUserId), dashboard_type: adminDestination },
        })
      ).data,
    enabled: Boolean(previewUserId),
  });
  const scenarioPreview = useQuery({
    queryKey: ["dashboard-admin-scenario-preview", previewProfileId, previewDepartmentId, adminDestination],
    queryFn: async () =>
      (
        await api.get<EffectiveDashboard>("/dashboards/admin/scenario-preview", {
          params: {
            profile_id: previewProfileId || undefined,
            department_id: previewDepartmentId || undefined,
            dashboard_type: adminDestination,
          },
        })
      ).data,
    enabled: Boolean(previewProfileId || previewDepartmentId),
  });
  const message = (caught: unknown) =>
    axios.isAxiosError(caught)
      ? (caught.response?.data?.error?.message ?? t("dashboardAdmin.failed"))
      : t("dashboardAdmin.failed");
  const refresh = async () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["dashboard-admin-templates"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["dashboard-admin-assignments"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["dashboard-admin-assignment-impact"],
      }),
    ]);
  const createTemplate = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/dashboards/admin/templates", payload),
    onSuccess: async () => {
      setTemplateOpen(false);
      setDraftWidgets([]);
      setCatalogSearch("");
      setError("");
      await refresh();
    },
    onError: (caught) => setError(message(caught)),
  });
  const updateTemplate = useMutation({
    mutationFn: async ({
      item,
      changes,
    }: {
      item: Template;
      changes: Record<string, unknown>;
    }) =>
      api.patch(`/dashboards/admin/templates/${item.id}`, {
        expected_version: item.version,
        ...changes,
      }),
    onSuccess: async () => {
      setTemplateOpen(false);
      setEditingTemplate(null);
      setDraftWidgets([]);
      setCatalogSearch("");
      await refresh();
    },
    onError: (caught) => setError(message(caught)),
  });
  const cloneTemplate = useMutation({
    mutationFn: async (item: Template) =>
      api.post(`/dashboards/admin/templates/${item.id}/clone`, null, {
        params: {
          code: `${item.code}_COPY_${Date.now()}`,
          name: `${item.name} Copy`,
        },
      }),
    onSuccess: refresh,
    onError: (caught) => setError(message(caught)),
  });
  const createAssignment = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/dashboards/admin/assignments", payload),
    onSuccess: async () => {
      setAssignmentOpen(false);
      setError("");
      await refresh();
    },
    onError: (caught) => setError(message(caught)),
  });
  const updateAssignment = useMutation({
    mutationFn: async (item: Assignment) =>
      api.patch(`/dashboards/admin/assignments/${item.id}`, {
        expected_version: item.version,
        is_active: !item.is_active,
      }),
    onSuccess: refresh,
    onError: (caught) => setError(message(caught)),
  });
  function submitTemplate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const widgets = draftWidgets.map((widget, position) => ({
      ...widget,
      position,
    }));
    const changes = {
      name: String(values.name).trim(),
      description: values.description || null,
      widgets,
    };
    if (editingTemplate) {
      updateTemplate.mutate({ item: editingTemplate, changes });
    } else {
      createTemplate.mutate({
        code: String(values.code).trim().toUpperCase(),
        destination: String(values.destination),
        ...changes,
      });
    }
  }
  function addWidget(item: Widget) {
    setDraftWidgets((current) => [
      ...current,
      {
        widget_code: item.widget_code,
        title: item.title,
        widget_type: item.widget_type,
        query_code: item.query_code,
        position: current.length,
        width: item.default_width,
        refresh_seconds: 60,
        config: {},
      },
    ]);
  }
  function patchWidget(code: string, changes: Partial<ConfigWidget>) {
    setDraftWidgets((current) =>
      current.map((widget) =>
        widget.widget_code === code ? { ...widget, ...changes } : widget,
      ),
    );
  }
  function moveWidget(index: number, offset: number) {
    setDraftWidgets((current) => {
      const target = index + offset;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }
  function openTemplateEditor(item?: Template) {
    setEditingTemplate(item ?? null);
    setDraftWidgets(item?.widgets.map((widget) => ({ ...widget })) ?? []);
    setCatalogSearch("");
    setTemplateOpen(true);
  }
  function submitAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const targetId = values.target_id ? Number(values.target_id) : null;
    createAssignment.mutate({
      dashboard_id: Number(values.dashboard_id),
      dashboard_type: adminDestination,
      profile_id:
        targetType === "PROFILE" || targetType === "PROFILE_DEPARTMENT"
          ? Number(values.profile_id)
          : null,
      department_id:
        targetType === "DEPARTMENT" || targetType === "PROFILE_DEPARTMENT"
          ? Number(values.department_id)
          : null,
      user_id: targetType === "USER" ? targetId : null,
      priority: Number(values.priority || 0),
      effective_from: values.effective_from
        ? new Date(String(values.effective_from)).toISOString()
        : null,
      effective_until: values.effective_until
        ? new Date(String(values.effective_until)).toISOString()
        : null,
    });
  }
  const templateName = (id: number) =>
    templates.data?.find((item) => item.id === id)?.name ?? `#${id}`;
  const target = (item: Assignment) =>
    item.user_id
      ? `${t("dashboardAdmin.user")} #${item.user_id}`
      : item.profile_id && item.department_id
        ? `${t("dashboardAdmin.profile")} #${item.profile_id} + ${t("dashboardAdmin.department")} #${item.department_id}`
        : item.profile_id
          ? `${t("dashboardAdmin.profile")} #${item.profile_id}`
          : item.department_id
            ? `${t("dashboardAdmin.department")} #${item.department_id}`
            : t("dashboardAdmin.system");
  const impactCount = (assignmentId: number) =>
    assignmentImpact.data?.find((item) => item.assignment_id === assignmentId)
      ?.affected_user_count ?? 0;
  const widgetDiagnostics = (data: EffectiveDashboard) => {
    const assignment = assignments.data?.find((item) => item.id === data.assignment_id);
    const template = templates.data?.find((item) => item.id === assignment?.dashboard_id);
    const visibleCodes = new Set(data.widgets.map((widget) => widget.widget_code));
    const permissionCodes = new Set(data.permission_codes);
    return (template?.widgets ?? []).map((widget) => {
      const required = catalog.data?.find((item) => item.widget_code === widget.widget_code)?.required_permissions ?? [];
      const permitted = required.every((permission) => permissionCodes.has(permission));
      return {
        ...widget,
        required,
        status: visibleCodes.has(widget.widget_code)
          ? "VISIBLE"
          : permitted
            ? "USER_HIDDEN"
            : "PERMISSION_BLOCKED",
      };
    });
  };
  const previewPanel = (data: EffectiveDashboard) => (
    <Stack spacing={1} mt={2}>
      <Stack direction="row" gap={1} flexWrap="wrap">
        <Chip label={data.name} color="primary" />
        <Chip label={`${t("dashboardAdmin.source")}: ${data.source}`} />
        <Chip label={`${t("dashboardAdmin.version")}: ${data.template_version}`} />
        <Chip label={`${t("dashboardAdmin.widgets")}: ${data.widgets.length}`} />
      </Stack>
      <Typography color="text.secondary">
        {data.resolution_explanation ?? t("dashboardAdmin.legacyResolution")}
      </Typography>
      <Typography variant="body2">
        {data.widgets.map((widget) => widget.title).join(" · ") ||
          t("dashboardAdmin.noAuthorizedWidgets")}
      </Typography>
      {data.assignment_id && <Stack spacing={0.75} mt={1}>
        {widgetDiagnostics(data).map((widget) => <Paper key={widget.widget_code} variant="outlined" sx={{ p: 1 }}>
          <Stack direction={{ xs: "column", sm: "row" }} gap={0.5} alignItems={{ sm: "center" }}>
            <Box flex={1} minWidth={0}>
              <Typography variant="body2" fontWeight={700}>{widget.title}</Typography>
              {widget.required.length > 0 && <Typography variant="caption" color="text.secondary">{t("dashboardAdmin.requiredPermissions", { defaultValue: "Requires" })}: {widget.required.join(", ")}</Typography>}
            </Box>
            <Chip size="small" color={widget.status === "VISIBLE" ? "success" : widget.status === "PERMISSION_BLOCKED" ? "error" : "warning"} label={t(`dashboardAdmin.widgetStatuses.${widget.status}`, { defaultValue: widget.status.replaceAll("_", " ") })} />
          </Stack>
        </Paper>)}
      </Stack>}
    </Stack>
  );
  if (adminArea === "CATALOG") {
    const usageCount = (code: string) => templates.data?.reduce((count, template) => count + template.widgets.filter((widget) => widget.widget_code === code).length, 0) ?? 0;
    const visibleCatalog = (catalog.data ?? []).filter((widget) => `${widget.title} ${widget.widget_code} ${widget.description}`.toLowerCase().includes(catalogSearch.trim().toLowerCase()));
    return <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}><Box flex={1}><Typography variant="h4" fontWeight={900}>Widget Catalog</Typography><Typography color="text.secondary">Reusable widget library and assignment usage.</Typography></Box><Button variant="outlined" onClick={() => setAdminArea("DESIGNER")}>Dashboard Designer</Button></Stack>
      <TextField value={catalogSearch} onChange={(event) => setCatalogSearch(event.target.value)} label="Search widgets by name or code" fullWidth />
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(250px,1fr))", gap: 2 }}>
        {visibleCatalog.map((widget) => <Paper key={widget.widget_code} variant="outlined" sx={{ p: 2 }}><Stack spacing={1} height="100%"><Typography fontWeight={800}>{widget.title}</Typography><Chip size="small" label={widget.widget_type.replaceAll("_", " ")} sx={{ alignSelf: "flex-start" }} /><Typography variant="body2" color="text.secondary" flex={1}>{widget.description}</Typography><Typography variant="caption" color={usageCount(widget.widget_code) ? "primary.main" : "warning.main"}>{usageCount(widget.widget_code) ? `Used in ${usageCount(widget.widget_code)} dashboard${usageCount(widget.widget_code) === 1 ? "" : "s"}` : "Unassigned"}</Typography><Button size="small" onClick={() => { setAdminArea("DESIGNER"); setCatalogSearch(widget.widget_code); }}>Assign</Button></Stack></Paper>)}
      </Box>
    </Stack>;
  }
  return (
    <Stack spacing={2}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Box flex={1}>
          <Typography variant="h4" fontWeight={900}>
            {t("dashboardAdmin.title")}
          </Typography>
          <Typography color="text.secondary">
            {t("dashboardAdmin.subtitle")}
          </Typography>
        </Box>
        <Button variant="outlined" onClick={() => setAdminArea("CATALOG")}>Widget Catalog</Button>
        <Button
          startIcon={<Add />}
          variant="outlined"
          onClick={() => setAssignmentOpen(true)}
        >
          {t("dashboardAdmin.addAssignment")}
        </Button>
        <Button
          startIcon={<Add />}
          variant="contained"
          onClick={() => openTemplateEditor()}
        >
          {t("dashboardAdmin.addTemplate")}
        </Button>
      </Stack>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography fontWeight={800} mb={1}>{t("dashboardAdmin.dashboardType")}</Typography>
        <TextField
          select
          value={adminDestination}
          onChange={(event) => setAdminDestination(event.target.value as "EXECUTIVE" | "TOP_MANAGEMENT")}
          fullWidth
          size="small"
        >
          <MenuItem value="EXECUTIVE">{t("dashboardAdmin.dashboardTypes.EXECUTIVE")}</MenuItem>
          <MenuItem value="TOP_MANAGEMENT">{t("dashboardAdmin.dashboardTypes.TOP_MANAGEMENT")}</MenuItem>
        </TextField>
      </Paper>
      {error && <Alert severity="error">{error}</Alert>}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" fontWeight={800} mb={1}>
          {t("dashboardAdmin.preview")}
        </Typography>
        <TextField
          select
          value={previewUserId}
          onChange={(event) => setPreviewUserId(event.target.value)}
          label={t("dashboardAdmin.previewUser")}
          fullWidth
          size="small"
        >
          {users.data?.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.full_name ?? item.name}
            </MenuItem>
          ))}
        </TextField>
        {preview.isError && (
          <Alert severity="error" sx={{ mt: 1 }}>
            {t("dashboardAdmin.previewFailed")}
          </Alert>
        )}
        {preview.data && (
          <Stack spacing={1}>
            {previewPanel(preview.data)}
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("dashboardAdmin.effectivePermissions")}
              </Typography>
              <Stack direction="row" gap={0.5} flexWrap="wrap" mt={0.5}>
                {preview.data.permission_codes.map((code) => (
                  <Chip key={code} label={code} size="small" variant="outlined" />
                ))}
              </Stack>
            </Box>
          </Stack>
        )}
        <Typography variant="subtitle2" mt={3} mb={1}>
          {t("dashboardAdmin.scenarioPreview")}
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField select value={previewProfileId} onChange={(event) => setPreviewProfileId(event.target.value)} label={t("dashboardAdmin.profile")} fullWidth size="small">
            <MenuItem value="">—</MenuItem>
            {profiles.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField select value={previewDepartmentId} onChange={(event) => setPreviewDepartmentId(event.target.value)} label={t("dashboardAdmin.department")} fullWidth size="small">
            <MenuItem value="">—</MenuItem>
            {departments.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
        </Stack>
        {scenarioPreview.isError && <Alert severity="error" sx={{ mt: 1 }}>{t("dashboardAdmin.previewFailed")}</Alert>}
        {scenarioPreview.data && previewPanel(scenarioPreview.data)}
      </Paper>
      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Typography variant="h6" fontWeight={800} p={2}>
          {t("dashboardAdmin.templates")}
        </Typography>
        <Table size="small" sx={{ minWidth: 760 }}>
          <TableHead>
            <TableRow>
              <TableCell>{t("dashboardAdmin.code")}</TableCell>
              <TableCell>{t("dashboardAdmin.name")}</TableCell>
              <TableCell>{t("dashboardAdmin.widgets")}</TableCell>
              <TableCell>{t("dashboardAdmin.version")}</TableCell>
              <TableCell>{t("dashboardAdmin.status")}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {templates.data?.filter((item) => item.destination === adminDestination).map((item) => (
              <TableRow key={item.id}>
                <TableCell dir="ltr">{item.code}</TableCell>
                <TableCell>{item.name}</TableCell>
                <TableCell>{item.widgets.length}</TableCell>
                <TableCell>{item.version}</TableCell>
                  <TableCell>
                  <Chip
                    size="small"
                    color={item.is_active ? "success" : "default"}
                    label={t(
                      item.is_active
                        ? "dashboardAdmin.active"
                        : "dashboardAdmin.inactive",
                    )}
                  />
                  </TableCell>
                  <TableCell align="right">
                  <Button
                    size="small"
                    startIcon={<Edit />}
                    onClick={() => openTemplateEditor(item)}
                  >
                    {t("dashboardAdmin.edit")}
                  </Button>
                  <Button
                    size="small"
                    startIcon={<ContentCopy />}
                    onClick={() => cloneTemplate.mutate(item)}
                  >
                    {t("dashboardAdmin.clone")}
                  </Button>
                  <Button
                    size="small"
                    color={item.is_active ? "error" : "success"}
                    onClick={() =>
                      updateTemplate.mutate({
                        item,
                        changes: { is_active: !item.is_active },
                      })
                    }
                  >
                    {t(
                      item.is_active
                        ? "dashboardAdmin.deactivate"
                        : "dashboardAdmin.activate",
                    )}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Typography variant="h6" fontWeight={800} p={2}>
          {t("dashboardAdmin.assignments")}
        </Typography>
        <Table size="small" sx={{ minWidth: 980 }}>
          <TableHead>
            <TableRow>
              <TableCell>{t("dashboardAdmin.template")}</TableCell>
              <TableCell>{t("dashboardAdmin.dashboardType")}</TableCell>
              <TableCell>{t("dashboardAdmin.target")}</TableCell>
              <TableCell>{t("dashboardAdmin.priority")}</TableCell>
              <TableCell>{t("dashboardAdmin.period")}</TableCell>
              <TableCell>{t("dashboardAdmin.status")}</TableCell>
              <TableCell>{t("dashboardAdmin.affectedUsers")}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {assignments.data?.filter((item) => item.dashboard_type === adminDestination).map((item) => (
              <TableRow key={item.id}>
                <TableCell>{templateName(item.dashboard_id)}</TableCell>
                <TableCell>{t(`dashboardAdmin.dashboardTypes.${item.dashboard_type}`)}</TableCell>
                <TableCell>{target(item)}</TableCell>
                <TableCell>{item.priority}</TableCell>
                <TableCell>
                  {item.effective_from ?? "—"} → {item.effective_until ?? "—"}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    color={item.is_active ? "success" : "default"}
                    label={t(
                      item.is_active
                        ? "dashboardAdmin.active"
                        : "dashboardAdmin.inactive",
                    )}
                  />
                </TableCell>
                <TableCell>{impactCount(item.id)}</TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    color={item.is_active ? "error" : "success"}
                    onClick={() => updateAssignment.mutate(item)}
                  >
                    {t(
                      item.is_active
                        ? "dashboardAdmin.deactivate"
                        : "dashboardAdmin.activate",
                    )}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <Dialog
        open={templateOpen}
        onClose={() => {
          setTemplateOpen(false);
          setEditingTemplate(null);
        }}
        fullWidth
        maxWidth="md"
      >
        <Box component="form" onSubmit={submitTemplate}>
          <DialogTitle>
            {t(
              editingTemplate
                ? "dashboardAdmin.editTemplate"
                : "dashboardAdmin.addTemplate",
            )}
          </DialogTitle>
          <DialogContent>
        <TextField
              required
              name="code"
              label={t("dashboardAdmin.code")}
              fullWidth
              margin="normal"
              inputProps={{ pattern: "[A-Za-z0-9_]+" }}
              defaultValue={editingTemplate?.code ?? ""}
              disabled={Boolean(editingTemplate)}
            />
            <TextField
              required
              name="name"
              label={t("dashboardAdmin.name")}
              fullWidth
              margin="normal"
              defaultValue={editingTemplate?.name ?? ""}
            />
            <TextField
              name="description"
              label={t("dashboardAdmin.description")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              defaultValue={editingTemplate?.description ?? ""}
            />
            <TextField
              required
              select
              name="destination"
              label={t("dashboardAdmin.dashboardType")}
              fullWidth
              margin="normal"
              defaultValue={editingTemplate?.destination ?? adminDestination}
              disabled={Boolean(editingTemplate)}
            >
              <MenuItem value="EXECUTIVE">{t("dashboardAdmin.dashboardTypes.EXECUTIVE")}</MenuItem>
              <MenuItem value="TOP_MANAGEMENT">{t("dashboardAdmin.dashboardTypes.TOP_MANAGEMENT")}</MenuItem>
            </TextField>
            <Typography fontWeight={800} mt={1}>
              {t("dashboardAdmin.widgets")}
            </Typography>
            <TextField
              value={catalogSearch}
              onChange={(event) => setCatalogSearch(event.target.value)}
              label={t("dashboardAdmin.searchCatalog")}
              fullWidth
              size="small"
              margin="normal"
            />
            {catalog.data
              ?.filter((item) => {
                const needle = catalogSearch.trim().toLocaleLowerCase();
                return (
                  !needle ||
                  `${item.title} ${item.description} ${item.widget_code}`
                    .toLocaleLowerCase()
                    .includes(needle)
                );
              })
              .map((item) => (
              <FormControlLabel
                key={item.widget_code}
                control={
                  <Checkbox
                    checked={draftWidgets.some(
                      (widget) => widget.widget_code === item.widget_code,
                    )}
                    onChange={(_, checked) =>
                      checked
                        ? addWidget(item)
                        : setDraftWidgets((current) =>
                            current.filter(
                              (widget) =>
                                widget.widget_code !== item.widget_code,
                            ),
                          )
                    }
                  />
                }
                label={<Box><Typography variant="body2">{item.title} — {item.description}</Typography>{item.required_permissions.length > 0 && <Typography variant="caption" color="text.secondary">{t("dashboardAdmin.requiredPermissions", { defaultValue: "Requires" })}: {item.required_permissions.join(", ")}</Typography>}</Box>}
              />
              ))}
            <Stack spacing={1} mt={2}>
              {draftWidgets.map((widget, index) => (
                <Paper key={widget.widget_code} variant="outlined" sx={{ p: 1 }}>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    gap={1}
                    alignItems={{ md: "center" }}
                  >
                    <Typography fontWeight={700} flex={1}>
                      {index + 1}. {widget.title}
                    </Typography>
                    <Button
                      size="small"
                      aria-label={t("dashboardAdmin.moveUp")}
                      disabled={index === 0}
                      onClick={() => moveWidget(index, -1)}
                    >
                      <ArrowUpward fontSize="small" />
                    </Button>
                    <Button
                      size="small"
                      aria-label={t("dashboardAdmin.moveDown")}
                      disabled={index === draftWidgets.length - 1}
                      onClick={() => moveWidget(index, 1)}
                    >
                      <ArrowDownward fontSize="small" />
                    </Button>
                    <TextField
                      select
                      size="small"
                      label={t("dashboardAdmin.width")}
                      value={widget.width}
                      onChange={(event) =>
                        patchWidget(widget.widget_code, {
                          width: Number(event.target.value),
                        })
                      }
                      sx={{ minWidth: 110 }}
                    >
                      {[2, 3, 4, 6, 8, 12].map((width) => (
                        <MenuItem key={width} value={width}>
                          {width}/12
                        </MenuItem>
                      ))}
        </TextField>
                    <TextField
                      size="small"
                      type="number"
                      label={t("dashboardAdmin.refreshSeconds")}
                      value={widget.refresh_seconds}
                      inputProps={{ min: 15, max: 3600 }}
                      onChange={(event) =>
                        patchWidget(widget.widget_code, {
                          refresh_seconds: Math.min(
                            3600,
                            Math.max(15, Number(event.target.value)),
                          ),
                        })
                      }
                      sx={{ width: 160 }}
                    />
                  </Stack>
                </Paper>
              ))}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setTemplateOpen(false);
                setEditingTemplate(null);
              }}
            >
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createTemplate.isPending || updateTemplate.isPending}
            >
              {t("common.actions.save")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={assignmentOpen}
        onClose={() => setAssignmentOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitAssignment}>
          <DialogTitle>{t("dashboardAdmin.addAssignment")}</DialogTitle>
          <DialogContent>
            <Alert severity="info" sx={{ mt: 1 }}>{t(`dashboardAdmin.dashboardTypes.${adminDestination}`)}</Alert>
            <TextField
              required
              select
              name="dashboard_id"
              label={t("dashboardAdmin.template")}
              fullWidth
              margin="normal"
              defaultValue=""
            >
              {templates.data
                ?.filter((item) => item.is_active && item.destination === adminDestination)
                .map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              select
              label={t("dashboardAdmin.targetType")}
              value={targetType}
              onChange={(event) => setTargetType(event.target.value)}
              fullWidth
              margin="normal"
            >
              {[
                "USER",
                "PROFILE",
                "DEPARTMENT",
                "PROFILE_DEPARTMENT",
                "SYSTEM",
              ].map((value) => (
                <MenuItem key={value} value={value}>
                  {t(`dashboardAdmin.targetTypes.${value}`)}
                </MenuItem>
              ))}
            </TextField>
            {targetType === "USER" && (
              <TextField
                required
                select
                name="target_id"
                label={t("dashboardAdmin.user")}
                fullWidth
                margin="normal"
                defaultValue=""
              >
                {users.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.full_name ?? item.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {(targetType === "PROFILE" ||
              targetType === "PROFILE_DEPARTMENT") && (
              <TextField
                required
                select
                name="profile_id"
                label={t("dashboardAdmin.profile")}
                fullWidth
                margin="normal"
                defaultValue=""
              >
                {profiles.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {(targetType === "DEPARTMENT" ||
              targetType === "PROFILE_DEPARTMENT") && (
              <TextField
                required
                select
                name="department_id"
                label={t("dashboardAdmin.department")}
                fullWidth
                margin="normal"
                defaultValue=""
              >
                {departments.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
            <TextField
              name="priority"
              type="number"
              defaultValue={0}
              label={t("dashboardAdmin.priority")}
              fullWidth
              margin="normal"
            />
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                name="effective_from"
                type="datetime-local"
                label={t("dashboardAdmin.from")}
                fullWidth
                margin="normal"
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                name="effective_until"
                type="datetime-local"
                label={t("dashboardAdmin.until")}
                fullWidth
                margin="normal"
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAssignmentOpen(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createAssignment.isPending}
            >
              {t("common.actions.save")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
