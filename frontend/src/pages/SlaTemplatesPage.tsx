import { Add, AutoAwesome, Delete, Save } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Option = { id: number; name: string };
type Target = {
  id: number;
  product_id: number | null;
  service_id: number | null;
  priority: string;
  first_response_minutes: number;
  resolution_minutes: number;
  warning_percent: number;
  effective_from: string | null;
  effective_until: string | null;
  is_fallback: boolean;
};
type Policy = {
  id: number;
  code: string;
  name: string;
  calendar_id: number;
  is_active: boolean;
  include_escalation_time: boolean;
  targets: Target[];
};
type Version = { id: number; version: number; status: string };
type Usage = { contracts: number; templates: number; ticket_clocks: number };
const localDateTime = (value: string | null) =>
  value ? value.slice(0, 16) : "";
const normalizeCode = (value: string) =>
  value
    .toUpperCase()
    .trim()
    .replace(/[^A-Z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "");

export function SlaTemplatesPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("contract.manage");
  const cache = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editingTarget, setEditingTarget] = useState<Target | null>(null);
  const [targetFormKey, setTargetFormKey] = useState(0);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [calendarId, setCalendarId] = useState("");
  const [active, setActive] = useState(true);
  const [includeEscalation, setIncludeEscalation] = useState(true);
  const policies = useQuery({
    queryKey: ["sla-policies"],
    queryFn: async () => (await api.get<Policy[]>("/sla-policies")).data,
  });
  const calendars = useQuery({
    queryKey: ["business-calendars"],
    queryFn: async () => (await api.get<Option[]>("/business-calendars")).data,
  });
  const products = useQuery({
    queryKey: ["products"],
    queryFn: async () => (await api.get<Option[]>("/products")).data,
  });
  const services = useQuery({
    queryKey: ["services"],
    queryFn: async () => (await api.get<Option[]>("/services")).data,
  });
  const selected = policies.data?.find((item) => item.id === selectedId);
  const versions = useQuery({
    queryKey: ["sla-policy-versions", selectedId],
    enabled: Boolean(selectedId),
    queryFn: async () =>
      (await api.get<Version[]>(`/sla-policies/${selectedId}/versions`)).data,
  });
  const usage = useQuery({
    queryKey: ["sla-policy-usage", selectedId],
    enabled: Boolean(selectedId),
    queryFn: async () =>
      (await api.get<Usage>(`/sla-policies/${selectedId}/usage`)).data,
  });
  useEffect(() => {
    if (!selected) return;
    setName(selected.name);
    setCode(selected.code);
    setCalendarId(String(selected.calendar_id));
    setActive(selected.is_active);
    setIncludeEscalation(selected.include_escalation_time);
    setEditingTarget(null);
  }, [selected]);
  const refresh = async () => {
    await cache.invalidateQueries({ queryKey: ["sla-policies"] });
    await cache.invalidateQueries({
      queryKey: ["sla-policy-versions", selectedId],
    });
    await cache.invalidateQueries({
      queryKey: ["sla-policy-usage", selectedId],
    });
  };
  const savePolicy = useMutation({
    mutationFn: async () =>
      selectedId
        ? (
            await api.put<Policy>(`/sla-policies/${selectedId}`, {
              code,
              name: name.trim(),
              calendar_id: Number(calendarId),
              is_active: active,
              include_escalation_time: includeEscalation,
            })
          ).data
        : (
            await api.post<Policy>("/sla-policies", {
              code: code.trim() || null,
              name: name.trim(),
              calendar_id: Number(calendarId),
              is_active: active,
              include_escalation_time: includeEscalation,
            })
          ).data,
    onSuccess: async (policy) => {
      setSelectedId(policy.id);
      await refresh();
    },
  });
  const createPreset = useMutation({
    mutationFn: async () =>
      (
        await api.post<Policy>("/sla-policies/presets/l1-l4", {
          name: "Standard Support SLA — L1 to L4",
          calendar_id: Number(calendarId),
          is_active: true,
          include_escalation_time: true,
        })
      ).data,
    onSuccess: async (policy) => {
      setSelectedId(policy.id);
      await refresh();
    },
  });
  const saveTarget = useMutation({
    mutationFn: async (event: FormEvent<HTMLFormElement>) => {
      const values = new FormData(event.currentTarget);
      return api.post(`/sla-policies/${selectedId}/targets`, {
        product_id: editingTarget
          ? editingTarget.product_id
          : values.get("product_id")
            ? Number(values.get("product_id"))
            : null,
        service_id: editingTarget
          ? editingTarget.service_id
          : values.get("service_id")
            ? Number(values.get("service_id"))
            : null,
        priority: editingTarget?.priority ?? values.get("priority"),
        first_response_minutes: Number(values.get("first_response_minutes")),
        resolution_minutes: Number(values.get("resolution_minutes")),
        warning_percent: Number(values.get("warning_percent")),
        effective_from: values.get("effective_from") || null,
        effective_until: values.get("effective_until") || null,
      });
    },
    onSuccess: async () => {
      setEditingTarget(null);
      setTargetFormKey((value) => value + 1);
      await refresh();
    },
  });
  const removeTarget = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/sla-policies/${selectedId}/targets/${id}`),
    onSuccess: refresh,
  });
  const publish = useMutation({
    mutationFn: async () => api.post(`/sla-policies/${selectedId}/publish`),
    onSuccess: refresh,
  });
  const removePolicy = useMutation({
    mutationFn: async () => api.delete(`/sla-policies/${selectedId}`),
    onSuccess: async () => {
      setSelectedId(null);
      setName("");
      setCode("");
      await refresh();
    },
  });
  const error =
    savePolicy.error ||
    createPreset.error ||
    saveTarget.error ||
    removeTarget.error ||
    publish.error ||
    removePolicy.error;
  const newPolicy = () => {
    setSelectedId(null);
    setName("");
    setCode("");
    setCalendarId("");
    setActive(true);
    setIncludeEscalation(true);
    setEditingTarget(null);
  };

  return (
    <Stack spacing={2}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ sm: "center" }}
        gap={1}
      >
        <Box flex={1}>
          <Typography variant="h5" fontWeight={800}>
            Reusable SLA templates
          </Typography>
          <Typography color="text.secondary">
            Manage shared SLA policies here. A contract can link an active
            template and make its own scoped copy when edited.
          </Typography>
        </Box>
        {canManage && (
          <Button startIcon={<Add />} variant="outlined" onClick={newPolicy}>
            New SLA template
          </Button>
        )}
      </Stack>
      {policies.isError && (
        <Alert severity="error">
          Could not load SLA templates: {apiErrorMessage(policies.error)}
        </Alert>
      )}
      {error && <Alert severity="error">{apiErrorMessage(error)}</Alert>}
      <Stack
        direction={{ xs: "column", md: "row" }}
        gap={2}
        alignItems="flex-start"
      >
        <Paper
          variant="outlined"
          sx={{ p: 2, width: { xs: "100%", md: 300 }, flexShrink: 0 }}
        >
          <Typography fontWeight={800} mb={1}>
            Templates
          </Typography>
          {!policies.data?.length && (
            <Typography color="text.secondary">
              No reusable SLA templates yet.
            </Typography>
          )}
          {policies.data?.map((policy) => (
            <Button
              key={policy.id}
              fullWidth
              onClick={() => setSelectedId(policy.id)}
              variant={selectedId === policy.id ? "contained" : "text"}
              sx={{
                justifyContent: "space-between",
                mb: 0.5,
                textAlign: "left",
              }}
            >
              {policy.name}
              <Chip
                size="small"
                label={policy.is_active ? "Active" : "Inactive"}
                color={policy.is_active ? "success" : "default"}
              />
            </Button>
          ))}
        </Paper>
        <Paper
          component="form"
          variant="outlined"
          onSubmit={(event) => {
            event.preventDefault();
            if (
              !selected ||
              !usage.data?.contracts ||
              window.confirm(
                `This SLA is linked to ${usage.data.contracts} contract(s). Publish these changes for those contracts?`,
              )
            )
              savePolicy.mutate();
          }}
          sx={{ p: 2, flex: 1, minWidth: 0 }}
        >
          <Typography variant="h6" fontWeight={800} mb={2}>
            {selected ? `Edit ${selected.name}` : "Create SLA template"}
          </Typography>
          {selected && usage.data && (
            <Alert
              severity={
                usage.data.contracts || usage.data.templates
                  ? "warning"
                  : "info"
              }
              sx={{ mb: 2 }}
            >
              Used by {usage.data.contracts} contracts, {usage.data.templates}{" "}
              contract templates, and {usage.data.ticket_clocks} ticket SLA
              clocks. Active changes publish immediately.
            </Alert>
          )}
          <Stack spacing={2}>
            <TextField
              required
              label="Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={!canManage}
            />
            <TextField
              label="Code"
              value={code}
              onChange={(event) => setCode(normalizeCode(event.target.value))}
              error={Boolean(code && !/^[A-Z0-9_-]{2,80}$/.test(code))}
              helperText={
                selected
                  ? "Stable code used by imports and integrations."
                  : "Optional. Only A-Z, 0-9, underscore and hyphen are allowed; invalid characters are corrected automatically."
              }
              disabled={!canManage || Boolean(selected)}
            />
            <TextField
              required
              select
              label="Business calendar"
              value={calendarId}
              onChange={(event) => setCalendarId(event.target.value)}
              disabled={!canManage}
            >
              <MenuItem value="">Choose a calendar</MenuItem>
              {calendars.data?.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
            </TextField>
            <FormControlLabel
              control={
                <Checkbox
                  checked={active}
                  onChange={(event) => setActive(event.target.checked)}
                  disabled={!canManage}
                />
              }
              label="Active and available for contracts"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={includeEscalation}
                  onChange={(event) =>
                    setIncludeEscalation(event.target.checked)
                  }
                  disabled={!canManage}
                />
              }
              label="Include escalation time"
            />
            {canManage && (
              <Stack direction="row" gap={1} flexWrap="wrap">
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={<Save />}
                  disabled={
                    savePolicy.isPending ||
                    !calendarId ||
                    !name.trim() ||
                    Boolean(code && !/^[A-Z0-9_-]{2,80}$/.test(code))
                  }
                >
                  {selected ? "Save template" : "Create template"}
                </Button>
                {!selected && (
                  <Button
                    type="button"
                    variant="outlined"
                    startIcon={<AutoAwesome />}
                    disabled={!calendarId || createPreset.isPending}
                    onClick={() => createPreset.mutate()}
                  >
                    Create standard L1–L4 template
                  </Button>
                )}
                {selected && (
                  <Button
                    color="error"
                    startIcon={<Delete />}
                    onClick={() => {
                      if (window.confirm("Delete this unused SLA template?"))
                        removePolicy.mutate();
                    }}
                    disabled={removePolicy.isPending}
                  >
                    Delete
                  </Button>
                )}
              </Stack>
            )}
            {!selected && (
              <Alert severity="info">
                The standard preset creates P1 15/60 minutes, P2 30/180 minutes,
                P3 60 minutes/10 business days, and P4 4 hours/30 business days
                using the selected calendar.
              </Alert>
            )}
          </Stack>
        </Paper>
      </Stack>
      {selected && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ sm: "center" }}
            gap={1}
            mb={2}
          >
            <Box flex={1}>
              <Typography variant="h6" fontWeight={800}>
                Priority targets
              </Typography>
              <Typography color="text.secondary">
                Leave Product empty to apply a target to all products. Dates are
                optional.
              </Typography>
            </Box>
            {canManage && (
              <Button
                onClick={() => {
                  setEditingTarget(null);
                  setTargetFormKey((value) => value + 1);
                }}
              >
                New target
              </Button>
            )}
          </Stack>
          {selected.targets.length === 0 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Add at least one target, then publish the SLA template.
            </Alert>
          )}
          <Stack spacing={1} mb={2}>
            {selected.targets.map((target) => (
              <Paper key={target.id} variant="outlined" sx={{ p: 1.5 }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  gap={1}
                  alignItems={{ sm: "center" }}
                >
                  <Chip label={target.priority} color="primary" />
                  <Box flex={1}>
                    <Typography fontWeight={700}>
                      {products.data?.find(
                        (item) => item.id === target.product_id,
                      )?.name ?? "All products"}{" "}
                      ·{" "}
                      {services.data?.find(
                        (item) => item.id === target.service_id,
                      )?.name ?? "All services"}
                    </Typography>
                    <Typography variant="body2">
                      Response {target.first_response_minutes} min · Resolution{" "}
                      {target.resolution_minutes} min · Warning{" "}
                      {target.warning_percent}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {target.effective_from?.slice(0, 10) ?? "Any start"} →{" "}
                      {target.effective_until?.slice(0, 10) ?? "No end"}
                    </Typography>
                  </Box>
                  {canManage && (
                    <>
                      <Button onClick={() => setEditingTarget(target)}>
                        Edit
                      </Button>
                      <Button
                        color="error"
                        onClick={() => {
                          if (window.confirm("Remove this SLA target?"))
                            removeTarget.mutate(target.id);
                        }}
                      >
                        Delete
                      </Button>
                    </>
                  )}
                </Stack>
              </Paper>
            ))}
          </Stack>
          {canManage && (
            <Box
              key={`${editingTarget?.id ?? "new"}-${targetFormKey}`}
              component="form"
              onSubmit={(event) => {
                event.preventDefault();
                if (
                  !usage.data?.contracts ||
                  window.confirm(
                    `Publish this target change for ${usage.data.contracts} linked contract(s)?`,
                  )
                )
                  saveTarget.mutate(event);
              }}
            >
              <Typography fontWeight={800} mb={1}>
                {editingTarget ? "Edit target" : "Add target"}
              </Typography>
              <Stack
                direction={{ xs: "column", md: "row" }}
                gap={1}
                flexWrap="wrap"
              >
                <TextField
                  select
                  name="product_id"
                  label="Product"
                  defaultValue={editingTarget?.product_id ?? ""}
                  sx={{ minWidth: 180 }}
                  disabled={Boolean(editingTarget)}
                >
                  <MenuItem value="">All products</MenuItem>
                  {products.data?.map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  name="service_id"
                  label="Service"
                  defaultValue={editingTarget?.service_id ?? ""}
                  sx={{ minWidth: 180 }}
                  disabled={Boolean(editingTarget)}
                >
                  <MenuItem value="">All services</MenuItem>
                  {services.data?.map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  name="priority"
                  label="Priority"
                  defaultValue={editingTarget?.priority ?? "P3"}
                  disabled={Boolean(editingTarget)}
                >
                  {["P1", "P2", "P3", "P4"].map((priority) => (
                    <MenuItem key={priority} value={priority}>
                      {priority}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  required
                  type="number"
                  name="first_response_minutes"
                  label="Response minutes"
                  defaultValue={editingTarget?.first_response_minutes ?? ""}
                  inputProps={{ min: 1 }}
                />
                <TextField
                  required
                  type="number"
                  name="resolution_minutes"
                  label="Resolution minutes"
                  defaultValue={editingTarget?.resolution_minutes ?? ""}
                  inputProps={{ min: 1 }}
                />
                <TextField
                  required
                  type="number"
                  name="warning_percent"
                  label="Warning %"
                  defaultValue={editingTarget?.warning_percent ?? 75}
                  inputProps={{ min: 1, max: 99 }}
                />
                <TextField
                  type="datetime-local"
                  name="effective_from"
                  label="Effective from"
                  defaultValue={localDateTime(
                    editingTarget?.effective_from ?? null,
                  )}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <TextField
                  type="datetime-local"
                  name="effective_until"
                  label="Effective until"
                  defaultValue={localDateTime(
                    editingTarget?.effective_until ?? null,
                  )}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={saveTarget.isPending}
                >
                  Save target
                </Button>
              </Stack>
            </Box>
          )}
          {canManage && (
            <Stack direction="row" alignItems="center" gap={1} mt={2}>
              <Button
                variant="outlined"
                onClick={() => publish.mutate()}
                disabled={publish.isPending || !selected.targets.length}
              >
                Publish changes
              </Button>
              <Typography variant="body2" color="text.secondary">
                Active templates publish automatically when targets or settings
                change. To change a target’s product, service, or priority, add
                the new target and then remove the old one. Latest version:{" "}
                {versions.data?.[0]
                  ? `${versions.data[0].version} (${versions.data[0].status})`
                  : "None"}
              </Typography>
            </Stack>
          )}
        </Paper>
      )}
    </Stack>
  );
}
