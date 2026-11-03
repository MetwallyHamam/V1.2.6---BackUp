import { DeleteOutline, EditOutlined } from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  Divider,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, apiErrorMessage } from "../api/client";
import { getLocalizedName } from "../i18n/localizedMasterData";

type Catalog = { id: number; name: string; name_ar?: string };
type Target = {
  id: number;
  product_id?: number;
  product_module_id?: number;
  service_id?: number;
  priority: string;
  first_response_minutes: number;
  resolution_minutes: number;
  warning_percent: number;
  is_fallback: boolean;
  effective_from?: string;
  effective_until?: string;
  context_key: string;
  version: number;
};
type Coverage = {
  id: number;
  product_id?: number;
  product_module_id?: number;
  service_id?: number;
  is_covered: boolean;
};
const priorities = ["P1", "P2", "P3", "P4"];
const localInput = (value?: string) => (value ? value.slice(0, 16) : "");

export function ProductScopedSlaEditor({
  contractId,
  targets,
  products,
  services,
  canManage,
}: {
  contractId: number;
  targets: Target[];
  products: Catalog[];
  services: Catalog[];
  canManage: boolean;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const queryClient = useQueryClient();
  const [productId, setProductId] = useState("");
  const [editing, setEditing] = useState<Target | null>(null);
  const [coverageIds, setCoverageIds] = useState<number[]>([]);
  const [selectedPriorities, setSelectedPriorities] =
    useState<string[]>(priorities);
  const modules = useQuery({
    queryKey: ["sla-target-modules", productId, i18n.language],
    enabled: Boolean(productId),
    queryFn: async () =>
      (await api.get<Catalog[]>(`/products/${productId}/modules`)).data.map(
        (item) => ({ ...item, name: getLocalizedName(item, i18n.language) }),
      ),
  });
  const coverage = useQuery({
    queryKey: ["contract-coverage", contractId],
    queryFn: async () =>
      (await api.get<Coverage[]>(`/contracts/${contractId}/coverage`)).data,
  });
  const refresh = async () =>
    queryClient.invalidateQueries({ queryKey: ["contract-sla", contractId] });
  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/contracts/${contractId}/sla/targets`, payload),
    onSuccess: async () => {
      setEditing(null);
      setProductId("");
      await refresh();
    },
  });
  const bulkSave = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/contracts/${contractId}/sla/targets/bulk`, payload),
    onSuccess: async () => {
      setCoverageIds([]);
      await refresh();
    },
  });
  const remove = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/contracts/${contractId}/sla/targets/${id}`),
    onSuccess: refresh,
  });
  const label = (items: Catalog[], id?: number) =>
    id
      ? getLocalizedName(
          items.find((item) => item.id === id) ?? { id, name: `#${id}` },
          i18n.language,
        )
      : t("productScopedSla.any");
  const coverageLabel = (row: Coverage) =>
    [
      row.product_id ? label(products, row.product_id) : null,
      row.product_module_id ? `Module #${row.product_module_id}` : null,
      row.service_id ? label(services, row.service_id) : null,
    ]
      .filter(Boolean)
      .join(" · ") || "Contract default";
  const tier = (target: Target) =>
    t(
      `productScopedSla.tiers.${target.product_id && target.product_module_id && target.service_id ? "1" : target.product_id && target.service_id ? "2" : target.product_id ? "3" : target.service_id ? "4" : "5"}`,
    );
  const activeCoverage = (coverage.data ?? []).filter((row) => row.is_covered);
  function edit(target: Target) {
    setEditing(target);
    setProductId(target.product_id ? String(target.product_id) : "");
  }
  function targetPayload(data: FormData) {
    const productId =
        editing?.product_id ??
        (data.get("product_id") ? Number(data.get("product_id")) : null),
      serviceId =
        editing?.service_id ??
        (data.get("service_id") ? Number(data.get("service_id")) : null);
    return {
      product_id: productId,
      product_module_id:
        editing?.product_module_id ??
        (data.get("product_module_id")
          ? Number(data.get("product_module_id"))
          : null),
      service_id: serviceId,
      priority: editing?.priority ?? String(data.get("priority") || "P3"),
      first_response_minutes: Number(data.get("first_response_minutes")),
      resolution_minutes: Number(data.get("resolution_minutes")),
      warning_percent: Number(data.get("warning_percent")),
      is_fallback: !productId && !serviceId,
      effective_from: data.get("effective_from")
        ? new Date(String(data.get("effective_from"))).toISOString()
        : null,
      effective_until: data.get("effective_until")
        ? new Date(String(data.get("effective_until"))).toISOString()
        : null,
    };
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    save.mutate(targetPayload(new FormData(event.currentTarget)));
  }
  function submitBulk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    bulkSave.mutate({
      coverage_ids: coverageIds,
      priorities: selectedPriorities,
      first_response_minutes: Number(data.get("first_response_minutes")),
      resolution_minutes: Number(data.get("resolution_minutes")),
      warning_percent: Number(data.get("warning_percent")),
      effective_from: data.get("effective_from")
        ? new Date(String(data.get("effective_from"))).toISOString()
        : null,
      effective_until: data.get("effective_until")
        ? new Date(String(data.get("effective_until"))).toISOString()
        : null,
    });
  }
  return (
    <Box>
      <Alert severity="info" sx={{ mb: 2 }}>
        SLA changes apply prospectively. Existing ticket SLA snapshots and audit
        history remain unchanged.
      </Alert>
      <Stack spacing={1}>
        {targets.map((target) => (
          <Paper key={target.id} variant="outlined" sx={{ p: 2 }}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              gap={1.5}
              alignItems={{ md: "center" }}
            >
              <Stack direction="row" gap={1}>
                <Chip label={target.priority} color="primary" />
                <Chip label={tier(target)} variant="outlined" />
              </Stack>
              <Box flex={1}>
                <Typography fontWeight={700}>
                  {label(products, target.product_id)} ·{" "}
                  {target.product_module_id
                    ? `Module #${target.product_module_id}`
                    : t("productScopedSla.anyModule")}{" "}
                  · {label(services, target.service_id)}
                </Typography>
                <Typography variant="body2">
                  Response{" "}
                  {Intl.NumberFormat(locale).format(
                    target.first_response_minutes,
                  )}{" "}
                  min · Resolution{" "}
                  {Intl.NumberFormat(locale).format(target.resolution_minutes)}{" "}
                  min · Warning {target.warning_percent}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Version {target.version} ·{" "}
                  {target.effective_from
                    ? new Date(target.effective_from).toLocaleString(locale)
                    : "Effective immediately"}
                  {target.effective_until
                    ? ` → ${new Date(target.effective_until).toLocaleString(locale)}`
                    : " · No end date"}
                </Typography>
              </Box>
              {canManage && (
                <Stack direction="row">
                  <Button
                    startIcon={<EditOutlined />}
                    onClick={() => edit(target)}
                  >
                    Edit
                  </Button>
                  <Button
                    color="error"
                    startIcon={<DeleteOutline />}
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(target.id)}
                  >
                    Remove
                  </Button>
                </Stack>
              )}
            </Stack>
          </Paper>
        ))}
      </Stack>
      {canManage && !editing && (
        <Paper
          component="form"
          onSubmit={submitBulk}
          variant="outlined"
          sx={{ p: 2, mt: 2 }}
        >
          <Typography variant="h6" fontWeight={800}>
            Bulk SLA setup
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Select existing contract coverage and priorities once. Matching
            targets are created or updated together.
          </Typography>
          <Divider sx={{ my: 2 }} />
          {activeCoverage.length === 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Assign products, modules or services in the Coverage tab first.
            </Alert>
          )}
          <Autocomplete
            multiple
            disableCloseOnSelect
            options={activeCoverage}
            value={activeCoverage.filter((row) => coverageIds.includes(row.id))}
            getOptionLabel={coverageLabel}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            onChange={(_, rows) => setCoverageIds(rows.map((row) => row.id))}
            renderOption={(props, option, { selected }) => (
              <li {...props} key={option.id}>
                <Checkbox checked={selected} />
                {coverageLabel(option)}
              </li>
            )}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Assigned contract coverage"
                helperText={`${coverageIds.length} coverage scope(s) selected`}
              />
            )}
          />
          <Autocomplete
            multiple
            disableCloseOnSelect
            options={priorities}
            value={selectedPriorities}
            onChange={(_, values) => setSelectedPriorities(values)}
            sx={{ mt: 1 }}
            renderOption={(props, option, { selected }) => (
              <li {...props} key={option}>
                <Checkbox checked={selected} />
                {option}
              </li>
            )}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Priorities"
                helperText={`${selectedPriorities.length} selected`}
              />
            )}
          />
          <Typography fontWeight={700} mt={2} mb={1}>
            Commitments
          </Typography>
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              required
              type="number"
              name="first_response_minutes"
              label={t("productScopedSla.respond")}
              inputProps={{ min: 1 }}
            />
            <TextField
              required
              type="number"
              name="resolution_minutes"
              label={t("productScopedSla.resolve")}
              inputProps={{ min: 1 }}
            />
            <TextField
              required
              type="number"
              name="warning_percent"
              label={t("productScopedSla.warn")}
              defaultValue={75}
              inputProps={{ min: 1, max: 99 }}
            />
            <TextField
              type="datetime-local"
              name="effective_from"
              label={t("productScopedSla.effectiveFrom")}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              type="datetime-local"
              name="effective_until"
              label={t("productScopedSla.effectiveUntil")}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Stack>
          {bulkSave.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {apiErrorMessage(bulkSave.error)}
            </Alert>
          )}
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ sm: "center" }}
            mt={2}
            gap={1}
          >
            <Typography color="text.secondary">
              Up to {coverageIds.length * selectedPriorities.length} targets
              will be created or updated.
            </Typography>
            <Button
              type="submit"
              variant="contained"
              disabled={
                !coverageIds.length ||
                !selectedPriorities.length ||
                bulkSave.isPending
              }
            >
              Apply SLA targets
            </Button>
          </Stack>
        </Paper>
      )}
      {canManage && editing && (
        <Paper
          component="form"
          key={editing.id}
          onSubmit={submit}
          variant="outlined"
          sx={{ p: 2, mt: 2, borderColor: "primary.main" }}
        >
          <Stack direction="row" alignItems="center">
            <Box flex={1}>
              <Typography variant="h6" fontWeight={800}>
                Edit SLA target
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Update commitments without changing this target's scope.
              </Typography>
            </Box>
            <Button
              onClick={() => {
                setEditing(null);
                setProductId("");
              }}
            >
              Cancel edit
            </Button>
          </Stack>
          <Divider sx={{ my: 2 }} />
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              select
              name="product_id"
              label={t("productScopedSla.product")}
              value={productId}
              disabled
              fullWidth
            >
              <MenuItem value="">
                {t("productScopedSla.contractDefault")}
              </MenuItem>
              {products.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {getLocalizedName(item, i18n.language)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="product_module_id"
              label={t("productScopedSla.module")}
              defaultValue={editing.product_module_id ?? ""}
              disabled
              fullWidth
            >
              <MenuItem value="">{t("productScopedSla.anyModule")}</MenuItem>
              {modules.data?.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="service_id"
              label={t("productScopedSla.service")}
              defaultValue={editing.service_id ?? ""}
              disabled
              fullWidth
            >
              <MenuItem value="">{t("productScopedSla.anyService")}</MenuItem>
              {services.map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {getLocalizedName(item, i18n.language)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="priority"
              label={t("productScopedSla.priority")}
              defaultValue={editing.priority}
              disabled
            >
              {priorities.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
          <Typography fontWeight={700} mt={2} mb={1}>
            Commitments
          </Typography>
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              required
              type="number"
              name="first_response_minutes"
              label={t("productScopedSla.respond")}
              defaultValue={editing.first_response_minutes}
              inputProps={{ min: 1 }}
            />
            <TextField
              required
              type="number"
              name="resolution_minutes"
              label={t("productScopedSla.resolve")}
              defaultValue={editing.resolution_minutes}
              inputProps={{ min: 1 }}
            />
            <TextField
              required
              type="number"
              name="warning_percent"
              label={t("productScopedSla.warn")}
              defaultValue={editing.warning_percent}
              inputProps={{ min: 1, max: 99 }}
            />
            <TextField
              type="datetime-local"
              name="effective_from"
              label={t("productScopedSla.effectiveFrom")}
              defaultValue={localInput(editing.effective_from)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              type="datetime-local"
              name="effective_until"
              label={t("productScopedSla.effectiveUntil")}
              defaultValue={localInput(editing.effective_until)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Stack>
          {save.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {apiErrorMessage(save.error)}
            </Alert>
          )}
          <Stack alignItems="flex-end" mt={2}>
            <Button type="submit" variant="contained" disabled={save.isPending}>
              Save SLA changes
            </Button>
          </Stack>
        </Paper>
      )}
    </Box>
  );
}
