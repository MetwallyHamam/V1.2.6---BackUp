import { Add, ContentCopy, Edit, ExpandMore } from "@mui/icons-material";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
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
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

type Profile = {
  id: number;
  name: string;
  code: string;
  description?: string;
  profile_type: string;
  is_system: boolean;
  is_active: boolean;
  risk_level: string;
  default_dashboard_code?: string;
};
type Permission = {
  id: number;
  code: string;
  module: string;
  description: string;
  is_high_risk: boolean;
};

function PermissionPicker({
  permissions,
  granted,
  onChange,
}: {
  permissions: Permission[];
  granted: Permission[];
  onChange: (permissions: Permission[]) => void;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const grantedIds = new Set(granted.map((item) => item.id));
  const query = search.trim().toLowerCase();
  const available = permissions
    .filter((item) => !grantedIds.has(item.id))
    .filter(
      (item) =>
        !query ||
        `${item.code} ${item.module} ${item.description}`
          .toLowerCase()
          .includes(query),
    )
    .sort(
      (left, right) =>
        left.module.localeCompare(right.module) ||
        left.code.localeCompare(right.code),
    );
  const selected = new Set(selectedIds);
  const visibleIds = available.map((item) => item.id);
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selected.has(id));
  const addSelected = () => {
    const additions = permissions.filter(
      (item) => selected.has(item.id) && !grantedIds.has(item.id),
    );
    onChange([...granted, ...additions]);
    setSelectedIds([]);
  };
  return (
    <Stack spacing={1.5} sx={{ mt: 2 }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ sm: "center" }}
        gap={1}
      >
        <Typography variant="h6" sx={{ flex: 1 }}>
          {t("profilesPage.picker.granted", {
            count: granted.length.toLocaleString(locale),
          })}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t("profilesPage.picker.removeBeforeSave")}
        </Typography>
      </Stack>
      <Paper variant="outlined" sx={{ maxHeight: 230, overflowY: "auto" }}>
        {granted.length === 0 && (
          <Typography color="text.secondary" sx={{ p: 2 }}>
            {t("profilesPage.picker.noneGranted")}
          </Typography>
        )}
        {[...granted]
          .sort(
            (left, right) =>
              left.module.localeCompare(right.module) ||
              left.code.localeCompare(right.code),
          )
          .map((item) => (
            <Stack
              key={item.id}
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              alignItems={{ sm: "center" }}
              sx={{
                px: 1.5,
                py: 1,
                borderBottom: 1,
                borderColor: "divider",
                "&:last-child": { borderBottom: 0 },
              }}
            >
              <Stack sx={{ flex: 1, minWidth: 0 }}>
                <Typography fontWeight={700} dir="ltr">
                  {item.code}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.description}
                </Typography>
              </Stack>
              {item.is_high_risk && (
                <Chip
                  size="small"
                  color="error"
                  label={t("profilesPage.picker.highRisk")}
                />
              )}
              <Button
                size="small"
                color="error"
                onClick={() =>
                  onChange(granted.filter((right) => right.id !== item.id))
                }
              >
                {t("profilesPage.picker.remove")}
              </Button>
            </Stack>
          ))}
      </Paper>
      <Typography variant="h6">{t("profilesPage.picker.addRights")}</Typography>
      <TextField
        size="small"
        label={t("profilesPage.picker.search")}
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        fullWidth
      />
      <Stack direction="row" gap={1} alignItems="center">
        <Button
          size="small"
          disabled={!visibleIds.length}
          onClick={() =>
            setSelectedIds((current) =>
              allVisibleSelected
                ? current.filter((id) => !visibleIds.includes(id))
                : Array.from(new Set([...current, ...visibleIds])),
            )
          }
        >
          {t(
            allVisibleSelected
              ? "profilesPage.picker.clearVisible"
              : "profilesPage.picker.selectVisible",
          )}
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
          {t("profilesPage.picker.selection", {
            selected: selectedIds.length.toLocaleString(locale),
            available: available.length.toLocaleString(locale),
          })}
        </Typography>
        <Button
          variant="contained"
          size="small"
          disabled={!selectedIds.length}
          onClick={addSelected}
        >
          {t("profilesPage.picker.addSelected")}
        </Button>
      </Stack>
      <Paper variant="outlined" sx={{ maxHeight: 320, overflowY: "auto" }}>
        {available.length === 0 && (
          <Typography color="text.secondary" sx={{ p: 2 }}>
            {t(
              query
                ? "profilesPage.picker.noMatches"
                : "profilesPage.picker.allGranted",
            )}
          </Typography>
        )}
        {available.map((item) => (
          <Stack
            component="label"
            key={item.id}
            direction="row"
            gap={1}
            alignItems="center"
            sx={{
              px: 1.25,
              py: 0.75,
              cursor: "pointer",
              "&:hover": { bgcolor: "action.hover" },
            }}
          >
            <Checkbox
              checked={selected.has(item.id)}
              onChange={(event) =>
                setSelectedIds((current) =>
                  event.target.checked
                    ? [...current, item.id]
                    : current.filter((id) => id !== item.id),
                )
              }
            />
            <Stack sx={{ flex: 1, minWidth: 0 }}>
              <Typography fontWeight={700} dir="ltr">
                {item.code}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {item.description}
              </Typography>
              <Typography variant="caption" color="text.secondary" dir="ltr">
                {item.module}
              </Typography>
            </Stack>
            {item.is_high_risk && (
              <Chip
                size="small"
                color="error"
                label={t("profilesPage.picker.highRisk")}
              />
            )}
          </Stack>
        ))}
      </Paper>
    </Stack>
  );
}

export function ProfilesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Profile | null>(null);
  const [cloning, setCloning] = useState<Profile | null>(null);
  const [createPermissions, setCreatePermissions] = useState<Permission[]>([]);
  const [editPermissions, setEditPermissions] = useState<Permission[]>([]);
  const query = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await api.get<Profile[]>("/profiles")).data,
  });
  const permissions = useQuery({
    queryKey: ["permissions"],
    queryFn: async () => (await api.get<Permission[]>("/permissions")).data,
  });
  const assigned = useQuery({
    queryKey: ["profile-permissions", editing?.id],
    queryFn: async () =>
      (await api.get<Permission[]>(`/profiles/${editing?.id}/permissions`))
        .data,
    enabled: Boolean(editing),
  });
  useEffect(() => {
    if (assigned.data) setEditPermissions(assigned.data);
  }, [assigned.data]);
  const message = (requestError: unknown, fallback: string) =>
    axios.isAxiosError(requestError)
      ? (requestError.response?.data?.error?.message ?? fallback)
      : fallback;
  const create = useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      api.post("/profiles", data),
    onSuccess: async () => {
      setCreateOpen(false);
      setCreatePermissions([]);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
    onError: (requestError) =>
      setError(message(requestError, t("profilesPage.errors.create"))),
  });
  const save = useMutation({
    mutationFn: async ({
      profileId,
      details,
      permissionIds,
      reason,
    }: {
      profileId: number;
      details: Record<string, unknown>;
      permissionIds: number[];
      reason: string;
    }) => {
      await api.patch(`/profiles/${profileId}`, details);
      return api.put(`/profiles/${profileId}/permissions`, {
        permission_ids: permissionIds,
        reason,
      });
    },
    onSuccess: async () => {
      setEditing(null);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
    onError: (requestError) =>
      setError(message(requestError, t("profilesPage.errors.update"))),
  });
  const clone = useMutation({
    mutationFn: async ({
      sourceId,
      name,
    }: {
      sourceId: number;
      name: string;
    }) => api.post(`/profiles/${sourceId}/clone`, null, { params: { name } }),
    onSuccess: async () => {
      setCloning(null);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
    onError: (requestError) =>
      setError(message(requestError, t("profilesPage.errors.clone"))),
  });
  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    create.mutate({
      name: values.name,
      description: values.description || null,
      profile_type: values.profile_type,
      default_dashboard_code: values.default_dashboard_code,
      permission_ids: createPermissions.map((item) => item.id),
    });
  }
  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    save.mutate({
      profileId: editing.id,
      details: {
        name: values.name,
        description: values.description || null,
        is_active: values.is_active === "true",
        default_dashboard_code: values.default_dashboard_code,
      },
      permissionIds: editPermissions.map((item) => item.id),
      reason: String(values.reason),
    });
  }
  function submitClone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cloning) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    clone.mutate({ sourceId: cloning.id, name: String(values.name).trim() });
  }
  if (query.isLoading) return <CircularProgress />;
  if (query.isError)
    return <Alert severity="error">{t("profilesPage.loadFailed")}</Alert>;
  return (
    <Paper sx={{ p: { xs: 1.5, sm: 3 }, minWidth: 0, overflow: "hidden" }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Typography variant="h4" sx={{ flexGrow: 1 }}>
          {t("profilesPage.title")}
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setCreateOpen(true)}
        >
          {t("profilesPage.createProfile")}
        </Button>
      </Stack>
      {error && (
        <Alert severity="error" sx={{ my: 2 }}>
          {error}
        </Alert>
      )}
      <Accordion
        defaultExpanded={false}
        disableGutters
        sx={{
          mt: 2,
          border: 1,
          borderColor: "divider",
          boxShadow: "none",
          "&:before": { display: "none" },
        }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box>
            <Typography variant="h6">
              {t("profilesPage.dashboardQueries")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("profilesPage.dashboardMovedHelp", {
                defaultValue:
                  "Dashboard query configuration is managed centrally in Dashboard Administration.",
              })}
            </Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            gap={1}
            alignItems={{ sm: "center" }}
          >
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
              {t("profilesPage.dashboardAdminHelp", {
                defaultValue:
                  "Open the central dashboard configuration page for profile defaults, templates, and assignments.",
              })}
            </Typography>
            <Button
              variant="outlined"
              onClick={() => navigate("/dashboard-admin")}
            >
              {t("profilesPage.openDashboardAdmin", {
                defaultValue: "Open Dashboard Administration",
              })}
            </Button>
          </Stack>
        </AccordionDetails>
      </Accordion>
      <Box
        role="region"
        aria-label={t("profilesPage.regionLabel")}
        tabIndex={0}
        sx={{
          mt: 2,
          maxWidth: "100%",
          overflowX: "auto",
          WebkitOverflowScrolling: "touch",
        }}
      >
        <Table sx={{ minWidth: 780 }}>
          <TableHead>
            <TableRow>
              <TableCell>{t("profilesPage.columns.name")}</TableCell>
              <TableCell>{t("profilesPage.columns.code")}</TableCell>
              <TableCell>{t("profilesPage.columns.type")}</TableCell>
              <TableCell>{t("profilesPage.columns.risk")}</TableCell>
              <TableCell>{t("profilesPage.columns.status")}</TableCell>
              <TableCell>{t("profilesPage.columns.managed")}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {query.data?.map((profile) => (
              <TableRow key={profile.id}>
                <TableCell>{profile.name}</TableCell>
                <TableCell sx={{ overflowWrap: "anywhere", direction: "ltr" }}>
                  {profile.code}
                </TableCell>
                <TableCell>
                  {t(`profilesPage.types.${profile.profile_type}`, {
                    defaultValue: profile.profile_type,
                  })}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={t(`profilesPage.risks.${profile.risk_level}`, {
                      defaultValue: profile.risk_level,
                    })}
                    color={
                      profile.risk_level === "CRITICAL" ? "error" : "default"
                    }
                  />
                </TableCell>
                <TableCell>
                  {t(
                    profile.is_active
                      ? "profilesPage.active"
                      : "profilesPage.inactive",
                  )}
                </TableCell>
                <TableCell>
                  {t(
                    profile.is_system
                      ? "profilesPage.system"
                      : "profilesPage.custom",
                  )}
                </TableCell>
                <TableCell>
                  <Stack direction="row">
                    <Button
                      size="small"
                      startIcon={<Edit />}
                      onClick={() => {
                        setEditPermissions([]);
                        setEditing(profile);
                      }}
                    >
                      {t("profilesPage.manage")}
                    </Button>
                    <Button
                      size="small"
                      startIcon={<ContentCopy />}
                      onClick={() => setCloning(profile)}
                    >
                      {t("profilesPage.clone")}
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        fullWidth
        maxWidth="lg"
      >
        <form onSubmit={submitCreate}>
          <DialogTitle>{t("profilesPage.createProfile")}</DialogTitle>
          <DialogContent sx={{ maxHeight: "75vh" }}>
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("profilesPage.generatedCode")}
            </Alert>
            <TextField
              required
              name="name"
              label={t("profilesPage.name")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="description"
              label={t("profilesPage.description")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <TextField
              required
              select
              name="profile_type"
              label={t("profilesPage.profileType")}
              defaultValue="EMPLOYEE"
              fullWidth
              margin="normal"
            >
              {["EMPLOYEE", "CLIENT_PORTAL", "ADMINISTRATOR", "API_INTEGRATION"].map((type) => (
                <MenuItem key={type} value={type}>
                  {t(`profilesPage.types.${type}`)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              required
              select
              name="default_dashboard_code"
              label={t("profilesPage.defaultLanding")}
              defaultValue="home"
              fullWidth
              margin="normal"
            >
              {[
                "home",
                "dashboard",
                "top-management",
                "ticket-create",
                "tickets",
                "saved-views",
                "clients",
                "knowledge",
                "portal",
              ].map((code) => (
                <MenuItem key={code} value={code}>
                  {t(`profilesPage.landing.${code}`)}
                </MenuItem>
              ))}
            </TextField>
            <PermissionPicker
              permissions={permissions.data ?? []}
              granted={createPermissions}
              onChange={setCreatePermissions}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateOpen(false)}>
              {t("profilesPage.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={create.isPending}
            >
              {t("profilesPage.create")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Dialog
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        fullWidth
        maxWidth="lg"
      >
        <form key={editing?.id} onSubmit={submitEdit}>
          <DialogTitle>
            {t("profilesPage.manageTitle", { code: editing?.code })}
          </DialogTitle>
          <DialogContent sx={{ maxHeight: "75vh" }}>
            {assigned.isLoading && <CircularProgress size={24} />}
            <TextField
              required
              name="name"
              label={t("profilesPage.name")}
              defaultValue={editing?.name}
              fullWidth
              margin="normal"
            />
            <TextField
              name="description"
              label={t("profilesPage.description")}
              defaultValue={editing?.description ?? ""}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <FormControlLabel
              control={
                <Switch
                  name="is_active"
                  value="true"
                  defaultChecked={editing?.is_active}
                />
              }
              label={t("profilesPage.activeProfile")}
            />
            <TextField
              required
              select
              name="default_dashboard_code"
              label={t("profilesPage.defaultLanding")}
              defaultValue={
                editing?.default_dashboard_code === "agent"
                  ? "dashboard"
                  : (editing?.default_dashboard_code ?? "home")
              }
              fullWidth
              margin="normal"
            >
              {[
                "home",
                "dashboard",
                "top-management",
                "ticket-create",
                "tickets",
                "saved-views",
                "clients",
                "knowledge",
              ].map((code) => (
                <MenuItem key={code} value={code}>
                  {t(`profilesPage.landing.${code}`)}
                </MenuItem>
              ))}
              {editing?.profile_type === "CLIENT_PORTAL" && (
                <MenuItem value="portal">
                  {t("profilesPage.landing.portal")}
                </MenuItem>
              )}
            </TextField>
            <PermissionPicker
              permissions={permissions.data ?? []}
              granted={editPermissions}
              onChange={setEditPermissions}
            />
            <TextField
              required
              name="reason"
              label={t("profilesPage.changeReason")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              inputProps={{ minLength: 5 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditing(null)}>
              {t("profilesPage.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={save.isPending || assigned.isLoading}
            >
              {t("profilesPage.saveProfile")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Dialog
        open={Boolean(cloning)}
        onClose={() => setCloning(null)}
        fullWidth
        maxWidth="sm"
      >
        <form onSubmit={submitClone}>
          <DialogTitle>
            {t("profilesPage.cloneTitle", { name: cloning?.name })}
          </DialogTitle>
          <DialogContent>
            <Typography color="text.secondary">
              {t("profilesPage.cloneHelp")}
            </Typography>
            <TextField
              required
              name="name"
              label={t("profilesPage.newName")}
              fullWidth
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCloning(null)}>
              {t("profilesPage.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={clone.isPending}
            >
              {t("profilesPage.clone")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Paper>
  );
}
