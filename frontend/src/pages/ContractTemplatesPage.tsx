import { Add, ContentCopy, Star } from "@mui/icons-material";
import {
  Alert,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getLocalizedName } from "../i18n/localizedMasterData";

type Catalog = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  is_active?: boolean;
};
type Coverage = {
  product_id?: number;
  product_module_id?: number;
  service_id?: number;
  is_covered: boolean;
  notes?: string;
};
type Template = {
  id: number;
  code: string;
  name: string;
  description?: string;
  template_type: string;
  contract_type_id?: number;
  calendar_id: number;
  sla_policy_id?: number;
  default_duration_months: number;
  has_sla: boolean;
  ticket_catalog_visibility: string;
  require_product_on_ticket: boolean;
  require_module_on_ticket: boolean;
  require_service_on_ticket: boolean;
  coverage_validation_level: "CONTRACT" | "PRODUCT" | "PRODUCT_MODULE" | "FULL";
  expiry_grace_days: number;
  approval_group_id?: number;
  support_summary?: string;
  exclusions?: string;
  included_request_limit?: number;
  default_billing_frequency?: string;
  default_payment_terms_days?: number;
  is_default: boolean;
  is_active: boolean;
  version: number;
  coverages: Coverage[];
};

export function ContractTemplatesPage({
  embedded = false,
}: {
  embedded?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const { hasPermission } = useAuth(),
    qc = useQueryClient(),
    [open, setOpen] = useState(false),
    [editing, setEditing] = useState<Template | null>(null),
    [coverage, setCoverage] = useState<Coverage[]>([]),
    [error, setError] = useState(""),
    [dirty, setDirty] = useState(false);
  const rows = useQuery({
    queryKey: ["contract-templates"],
    queryFn: async () =>
      (await api.get<Template[]>("/contract-templates")).data,
  });
  const calendars = useQuery({
    queryKey: ["business-calendars"],
    queryFn: async () => (await api.get<Catalog[]>("/business-calendars")).data,
  });
  const types = useQuery({
    queryKey: ["contract-types"],
    queryFn: async () =>
      (
        await api.get<Catalog[]>("/contract-types", {
          params: { active_only: true },
        })
      ).data,
  });
  const templateTypes = useQuery({
    queryKey: ["contract-template-types"],
    queryFn: async () =>
      (
        await api.get<Catalog[]>("/contract-template-types", {
          params: { active_only: true },
        })
      ).data,
  });
  const policies = useQuery({
    queryKey: ["sla-policies"],
    queryFn: async () => (await api.get<Catalog[]>("/sla-policies")).data,
  });
  const approvalGroups = useQuery({
    queryKey: ["entitlement-approval-groups"],
    queryFn: async () =>
      (await api.get<Catalog[]>("/entitlement-approvals/groups")).data,
    enabled: hasPermission("entitlement_approval.manage") && open,
  });
  const products = useQuery({
    queryKey: ["products", i18n.language],
    queryFn: async () =>
      (await api.get<Catalog[]>("/products")).data.map((x) => ({
        ...x,
        name: getLocalizedName(x, i18n.language),
      })),
  });
  const services = useQuery({
    queryKey: ["services", i18n.language],
    queryFn: async () =>
      (await api.get<Catalog[]>("/services")).data.map((x) => ({
        ...x,
        name: getLocalizedName(x, i18n.language),
      })),
  });
  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editing
        ? api.patch(`/contract-templates/${editing.id}`, payload)
        : api.post("/contract-templates", payload),
    onSuccess: async () => {
      setDirty(false);
      setOpen(false);
      setEditing(null);
      setCoverage([]);
      setError("");
      await qc.invalidateQueries({ queryKey: ["contract-templates"] });
    },
    onError: () => setError("saveFailed"),
  });
  const makeDefault = useMutation({
    mutationFn: async (id: number) =>
      api.post(`/contract-templates/${id}/make-default`),
    onSuccess: async () =>
      qc.invalidateQueries({ queryKey: ["contract-templates"] }),
  });
  const clone = useMutation({
    mutationFn: async (row: Template) =>
      api.post(`/contract-templates/${row.id}/clone`, null, {
        params: { name: `${row.name} ${t("contractTemplates.copySuffix")}` },
      }),
    onSuccess: async () =>
      qc.invalidateQueries({ queryKey: ["contract-templates"] }),
  });
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function show(row?: Template) {
    setEditing(row ?? null);
    setCoverage(row?.coverages ?? []);
    setError("");
    setDirty(false);
    setOpen(true);
  }
  function close() {
    if (dirty && !window.confirm(t("contractTemplates.discard"))) return;
    setDirty(false);
    setOpen(false);
    setEditing(null);
    setCoverage([]);
    setError("");
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const v = Object.fromEntries(new FormData(event.currentTarget));
    save.mutate({
      code: editing?.code ?? null,
      name: v.name,
      description: v.description || null,
      template_type: v.template_type,
      contract_type_id: v.contract_type_id ? Number(v.contract_type_id) : null,
      calendar_id: Number(v.calendar_id),
      sla_policy_id: v.sla_policy_id ? Number(v.sla_policy_id) : null,
      default_duration_months: Number(v.default_duration_months),
      has_sla: v.has_sla === "on",
      ticket_catalog_visibility: "CONTRACT_ONLY",
      require_product_on_ticket: v.require_product_on_ticket === "on",
      require_module_on_ticket: v.require_module_on_ticket === "on",
      require_service_on_ticket: v.require_service_on_ticket === "on",
      coverage_validation_level: v.coverage_validation_level || "PRODUCT",
      expiry_grace_days: Number(v.expiry_grace_days || 0),
      approval_group_id: hasPermission("entitlement_approval.manage")
        ? v.approval_group_id ? Number(v.approval_group_id) : null
        : editing?.approval_group_id ?? null,
      support_summary: v.support_summary || null,
      exclusions: v.exclusions || null,
      included_request_limit: v.included_request_limit
        ? Number(v.included_request_limit)
        : null,
      default_billing_frequency: v.default_billing_frequency || null,
      default_payment_terms_days: v.default_payment_terms_days
        ? Number(v.default_payment_terms_days)
        : null,
      is_default: v.is_default === "on",
      is_active: v.is_active === "on",
      coverages: coverage,
    });
  }
  return (
    <Stack spacing={2}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <div style={{ flex: 1 }}>
          <Typography variant={embedded ? "h5" : "h4"}>
            {t("contractTemplates.title")}
          </Typography>
          <Typography color="text.secondary">
            {t("contractTemplates.subtitle")}
          </Typography>
        </div>
        {hasPermission("contract.template.manage") && (
          <Button
            startIcon={<Add />}
            variant="contained"
            onClick={() => show()}
          >
            {t("contractTemplates.create")}
          </Button>
        )}
      </Stack>
      {rows.isError && (
        <Alert severity="error">{t("contractTemplates.loadFailed")}</Alert>
      )}
      <Stack spacing={1}>
        {rows.data?.map((row) => (
          <Paper
            key={row.id}
            variant="outlined"
            sx={{
              p: 2,
              borderInlineStart: 5,
              borderColor: row.is_default ? "warning.main" : "primary.main",
            }}
          >
            <Stack
              direction={{ xs: "column", md: "row" }}
              gap={1}
              alignItems={{ md: "center" }}
            >
              <div style={{ flex: 1 }}>
                <Typography fontWeight={900}>
                  <span dir="ltr">{row.code}</span> — {row.name}
                  {row.is_default ? ` · ${t("contractTemplates.default")}` : ""}
                </Typography>
                <Typography variant="body2">
                  {t("contractTemplates.summary", {
                    type: row.template_type,
                    months: new Intl.NumberFormat(locale).format(
                      row.default_duration_months,
                    ),
                    version: new Intl.NumberFormat(locale).format(row.version),
                    count: row.coverages.length,
                  })}
                </Typography>
              </div>
              {hasPermission("contract.template.manage") && (
                <>
                  <Button onClick={() => show(row)}>
                    {t("contractTemplates.edit")}
                  </Button>
                  <Button
                    startIcon={<ContentCopy />}
                    onClick={() => clone.mutate(row)}
                  >
                    {t("contractTemplates.clone")}
                  </Button>
                  {!row.is_default && (
                    <Button
                      startIcon={<Star />}
                      onClick={() => makeDefault.mutate(row.id)}
                    >
                      {t("contractTemplates.makeDefault")}
                    </Button>
                  )}
                </>
              )}
            </Stack>
          </Paper>
        ))}
      </Stack>
      <Dialog open={open} onClose={close} fullWidth maxWidth="md">
        <form onSubmit={submit} onChange={() => setDirty(true)}>
          <DialogTitle>
            {t(
              editing
                ? "contractTemplates.editTitle"
                : "contractTemplates.createTitle",
            )}
          </DialogTitle>
          <DialogContent>
            {error && (
              <Alert severity="error">{t(`contractTemplates.${error}`)}</Alert>
            )}
            <Stack spacing={1.5} mt={1}>
              {editing && (
                <TextField
                  label={t("contractTemplates.templateCode")}
                  value={editing.code}
                  disabled
                  helperText={t("contractTemplates.generated")}
                  inputProps={{ dir: "ltr" }}
                />
              )}
              <TextField
                required
                name="name"
                label={t("contractTemplates.templateName")}
                defaultValue={editing?.name ?? ""}
                fullWidth
              />
              <TextField
                name="description"
                label={t("contractTemplates.description")}
                defaultValue={editing?.description ?? ""}
              />
              <TextField
                select
                required
                name="template_type"
                label={t("contractTemplates.templateType")}
                defaultValue={
                  editing?.template_type ?? templateTypes.data?.[0]?.code ?? ""
                }
              >
                {templateTypes.data?.map((x) => (
                  <MenuItem key={x.id} value={x.code}>
                    {x.name}
                  </MenuItem>
                ))}
              </TextField>
              <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                <TextField
                  select
                  required
                  name="calendar_id"
                  label={t("contractTemplates.businessCalendar")}
                  defaultValue={editing?.calendar_id ?? ""}
                  fullWidth
                >
                  {calendars.data?.map((x) => (
                    <MenuItem key={x.id} value={x.id}>
                      {x.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  name="contract_type_id"
                  label={t("contractTemplates.contractType")}
                  defaultValue={editing?.contract_type_id ?? ""}
                  fullWidth
                >
                  <MenuItem value="">
                    {t("contractTemplates.systemDefault")}
                  </MenuItem>
                  {types.data?.map((x) => (
                    <MenuItem key={x.id} value={x.id}>
                      {x.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  type="number"
                  required
                  name="default_duration_months"
                  label={t("contractTemplates.durationMonths")}
                  defaultValue={editing?.default_duration_months ?? 12}
                  inputProps={{ min: 1, max: 120 }}
                />
              </Stack>
              <TextField
                select
                name="sla_policy_id"
                label={t("contractTemplates.defaultSla")}
                defaultValue={editing?.sla_policy_id ?? ""}
              >
                <MenuItem value="">{t("contractTemplates.noPolicy")}</MenuItem>
                {policies.data?.map((x) => (
                  <MenuItem key={x.id} value={x.id}>
                    {x.name}
                  </MenuItem>
                ))}
              </TextField>
              <Stack direction={{ xs: "column", sm: "row" }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      name="has_sla"
                      defaultChecked={editing?.has_sla ?? true}
                    />
                  }
                  label={t("contractTemplates.hasSla")}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      name="is_default"
                      defaultChecked={editing?.is_default}
                    />
                  }
                  label={t("contractTemplates.defaultTemplate")}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      name="is_active"
                      defaultChecked={editing?.is_active ?? true}
                    />
                  }
                  label={t("contractTemplates.active")}
                />
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                <TextField select name="coverage_validation_level" label={t("contractsPage.coverageValidationLevel")} defaultValue={editing?.coverage_validation_level??"PRODUCT"} fullWidth>
                  <MenuItem value="CONTRACT">{t("contractsPage.validationContract")}</MenuItem>
                  <MenuItem value="PRODUCT">{t("contractsPage.validationProduct")}</MenuItem>
                  <MenuItem value="PRODUCT_MODULE">{t("contractsPage.validationProductModule")}</MenuItem>
                  <MenuItem value="FULL">{t("contractsPage.validationFull")}</MenuItem>
                </TextField>
                <TextField type="number" name="expiry_grace_days" label={t("contractsPage.expiryGraceDays")} defaultValue={editing?.expiry_grace_days??0} inputProps={{min:0,max:3650}} fullWidth/>
                {hasPermission("entitlement_approval.manage")&&<TextField select name="approval_group_id" label={t("contractsPage.approvalGroup")} defaultValue={editing?.approval_group_id??""} fullWidth><MenuItem value="">{t("contractsPage.supportManagersDefault")}</MenuItem>{approvalGroups.data?.map(group=><MenuItem key={group.id} value={group.id}>{group.name}</MenuItem>)}</TextField>}
              </Stack>
              <Alert severity="info">{t("contractsPage.approvalFirstHelp")}</Alert>
              <Stack direction={{ xs: "column", sm: "row" }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      name="require_product_on_ticket"
                      defaultChecked={
                        editing?.require_product_on_ticket ?? true
                      }
                    />
                  }
                  label={t("contractsPage.requireProductOnTicket")}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      name="require_module_on_ticket"
                      defaultChecked={
                        editing?.require_module_on_ticket ?? false
                      }
                    />
                  }
                  label={t("contractsPage.requireModuleOnTicket")}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      name="require_service_on_ticket"
                      defaultChecked={
                        editing?.require_service_on_ticket ?? false
                      }
                    />
                  }
                  label={t("contractsPage.requireServiceOnTicket")}
                />
              </Stack>
              <TextField
                name="support_summary"
                label={t("contractTemplates.supportSummary")}
                multiline
                rows={2}
                defaultValue={editing?.support_summary ?? ""}
              />
              <TextField
                name="exclusions"
                label={t("contractTemplates.exclusions")}
                multiline
                rows={2}
                defaultValue={editing?.exclusions ?? ""}
              />
              <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                <TextField
                  type="number"
                  name="included_request_limit"
                  label={t("contractTemplates.includedRequests")}
                  defaultValue={editing?.included_request_limit ?? ""}
                />
                <TextField
                  select
                  name="default_billing_frequency"
                  label={t("contractTemplates.billingFrequency")}
                  defaultValue={editing?.default_billing_frequency ?? ""}
                >
                  <MenuItem value="">{t("contractTemplates.notSet")}</MenuItem>
                  {["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"].map(
                    (x) => (
                      <MenuItem key={x} value={x}>
                        {t(`contractTemplates.billing.${x}`)}
                      </MenuItem>
                    ),
                  )}
                </TextField>
                <TextField
                  type="number"
                  name="default_payment_terms_days"
                  label={t("contractTemplates.paymentTerms")}
                  defaultValue={editing?.default_payment_terms_days ?? ""}
                />
              </Stack>
              <Typography variant="h6">
                {t("contractTemplates.coverage")}
              </Typography>
              {coverage.map((row, i) => (
                <Stack key={i} direction={{ xs: "column", md: "row" }} gap={1}>
                  <TextField
                    select
                    label={t("contractTemplates.product")}
                    value={row.product_id ?? ""}
                    onChange={(e) => {
                      setDirty(true);
                      setCoverage((v) =>
                        v.map((x, n) =>
                          n === i
                            ? {
                                ...x,
                                product_id: Number(e.target.value) || undefined,
                                product_module_id: undefined,
                              }
                            : x,
                        ),
                      );
                    }}
                    fullWidth
                  >
                    <MenuItem value="">
                      {t("contractTemplates.anyProduct")}
                    </MenuItem>
                    {products.data?.map((x) => (
                      <MenuItem key={x.id} value={x.id}>
                        {x.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    label={t("contractTemplates.service")}
                    value={row.service_id ?? ""}
                    onChange={(e) => {
                      setDirty(true);
                      setCoverage((v) =>
                        v.map((x, n) =>
                          n === i
                            ? {
                                ...x,
                                service_id: Number(e.target.value) || undefined,
                              }
                            : x,
                        ),
                      );
                    }}
                    fullWidth
                  >
                    <MenuItem value="">
                      {t("contractTemplates.anyService")}
                    </MenuItem>
                    {services.data?.map((x) => (
                      <MenuItem key={x.id} value={x.id}>
                        {x.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Button
                    color="error"
                    onClick={() => {
                      setDirty(true);
                      setCoverage((v) => v.filter((_, n) => n !== i));
                    }}
                  >
                    {t("contractTemplates.remove")}
                  </Button>
                </Stack>
              ))}
              <Button
                onClick={() => {
                  setDirty(true);
                  setCoverage((v) => [...v, { is_covered: true }]);
                }}
              >
                {t("contractTemplates.addCoverage")}
              </Button>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={close}>{t("contractTemplates.cancel")}</Button>
            <Button type="submit" variant="contained" disabled={save.isPending}>
              {t("contractTemplates.save")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Stack>
  );
}
