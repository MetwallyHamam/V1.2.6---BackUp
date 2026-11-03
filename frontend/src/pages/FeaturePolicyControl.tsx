import { Add, Delete } from "@mui/icons-material";
import {
  Alert,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { FormEvent, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { api } from "../api/client";
import { getLocalizedName } from "../i18n/localizedMasterData";

type Feature = {
  key: string;
  name: string;
  category: string;
  description: string;
  default_mode: string;
  supported_scopes: string[];
};
type Policy = {
  id: number;
  feature_key: string;
  scope_key: string;
  mode: "OFF" | "SHADOW" | "ENFORCED";
  effective_from: string;
  effective_until?: string;
  version: number;
};
type Effective = {
  mode: "OFF" | "SHADOW" | "ENFORCED";
  source_scope_key: string;
  policy_version: number;
};
type Catalog = { id: number; name: string; name_ar?: string };
type Contract = {
  id: number;
  name: string;
  contract_number: string;
  client_id: number;
};
type TicketType = {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
};
const modeColor = {
  OFF: "default",
  SHADOW: "warning",
  ENFORCED: "success",
} as const;
const impactUrgencyValues = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export function FeaturePolicyControl({ initialFeatureKey }: { initialFeatureKey?: string }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState(initialFeatureKey ?? "");
  const [editor, setEditor] = useState(false);
  const [removing, setRemoving] = useState<Policy | null>(null);
  const [previewClient, setPreviewClient] = useState("");
  const [previewContract, setPreviewContract] = useState("");
  const [previewProduct, setPreviewProduct] = useState("");
  const [previewService, setPreviewService] = useState("");
  const features = useQuery({
    queryKey: ["feature-policies"],
    queryFn: async () =>
      (await api.get<Feature[]>("/system/feature-policies")).data,
  });
  const featureKey = selected || features.data?.[0]?.key || "";
  const feature = features.data?.find((x) => x.key === featureKey);
  const policies = useQuery({
    queryKey: ["feature-policies", featureKey, "rules"],
    queryFn: async () =>
      (
        await api.get<Policy[]>(
          `/system/feature-policies/${featureKey}/policies`,
        )
      ).data,
    enabled: Boolean(featureKey),
  });
  const clients = useQuery({
    queryKey: ["feature-policy-clients"],
    queryFn: async () =>
      (await api.get<Catalog[]>("/clients/ticket-options")).data,
  });
  const contracts = useQuery({
    queryKey: ["feature-policy-contracts"],
    queryFn: async () => (await api.get<Contract[]>("/contracts")).data,
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
  const ticketTypes = useQuery({
    queryKey: ["ticket-types"],
    queryFn: async () => (await api.get<TicketType[]>("/ticket-types")).data,
  });
  const preview = useQuery({
    queryKey: [
      "feature-policy-preview",
      featureKey,
      previewClient,
      previewContract,
      previewProduct,
      previewService,
    ],
    queryFn: async () =>
      (
        await api.get<Effective>(
          `/system/feature-policies/${featureKey}/effective`,
          {
            params: {
              client_id: previewClient || undefined,
              contract_id: previewContract || undefined,
              product_id: previewProduct || undefined,
              service_id: previewService || undefined,
            },
          },
        )
      ).data,
    enabled: Boolean(featureKey),
  });
  async function invalidate() {
    await queryClient.invalidateQueries({
      queryKey: ["feature-policies", featureKey],
    });
    await queryClient.invalidateQueries({
      queryKey: ["feature-policy-preview", featureKey],
    });
  }
  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.put(`/system/feature-policies/${featureKey}/policies`, payload),
    onSuccess: async () => {
      setEditor(false);
      await invalidate();
    },
  });
  const remove = useMutation({
    mutationFn: async ({ item, reason }: { item: Policy; reason: string }) =>
      api.delete(
        `/system/feature-policies/${item.feature_key}/policies/${item.id}`,
        { params: { reason } },
      ),
    onSuccess: async () => {
      setRemoving(null);
      await invalidate();
    },
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const configuration =
      featureKey === "engineer_pre_ticket"
        ? {
            ticket_type_id: Number(data.get("pre_ticket_type_id")),
            priority_mapping: Object.fromEntries(
              ["P1", "P2", "P3", "P4"].map((priority) => [
                priority,
                {
                  impact: data.get(`pre_ticket_${priority}_impact`),
                  urgency: data.get(`pre_ticket_${priority}_urgency`),
                },
              ]),
            ),
          }
        : {};
    save.mutate({
      scope_type: data.get("scope_type"),
      client_id: data.get("client_id") ? Number(data.get("client_id")) : null,
      contract_id: data.get("contract_id")
        ? Number(data.get("contract_id"))
        : null,
      product_id: data.get("product_id")
        ? Number(data.get("product_id"))
        : null,
      service_id: data.get("service_id")
        ? Number(data.get("service_id"))
        : null,
      mode: data.get("mode"),
      effective_until: data.get("effective_until")
        ? new Date(String(data.get("effective_until"))).toISOString()
        : null,
      configuration,
      reason: data.get("reason"),
    });
  }
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5">{t("featurePolicy.title")}</Typography>
      <Typography color="text.secondary">
        {t("featurePolicy.subtitle")}
      </Typography>
      <Alert severity="info" sx={{ my: 2 }}>
        <Trans
          i18nKey="featurePolicy.modeHelp"
          components={{ off: <b />, shadow: <b />, enforced: <b /> }}
        />
      </Alert>
      {features.isError && (
        <Alert severity="error">{t("featurePolicy.loadFailed")}</Alert>
      )}
      {features.data && (
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            select
            label={t("featurePolicy.feature")}
            value={featureKey}
            onChange={(e) => setSelected(e.target.value)}
            sx={{ minWidth: 320 }}
          >
            {features.data.map((x) => (
              <MenuItem key={x.key} value={x.key}>
                {x.category} — {x.name}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setEditor(true)}
          >
            {t("featurePolicy.add")}
          </Button>
        </Stack>
      )}
      {feature && (
        <Paper variant="outlined" sx={{ p: 2, my: 2 }}>
          <Typography fontWeight={800}>{feature.name}</Typography>
          <Typography color="text.secondary">{feature.description}</Typography>
          <Typography variant="caption">
            {t("featurePolicy.featureMeta", {
              scopes: feature.supported_scopes.join(", "),
              fallback: feature.default_mode,
            })}
          </Typography>
        </Paper>
      )}
      <Typography variant="h6">{t("featurePolicy.configured")}</Typography>
      {!policies.isLoading && !policies.data?.length && (
        <Typography color="text.secondary">
          {t("featurePolicy.none")}
        </Typography>
      )}
      {!!policies.data?.length && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("featurePolicy.scope")}</TableCell>
              <TableCell>{t("featurePolicy.mode")}</TableCell>
              <TableCell>{t("featurePolicy.period")}</TableCell>
              <TableCell>{t("featurePolicy.version")}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {policies.data.map((x) => (
              <TableRow key={x.id}>
                <TableCell sx={{ direction: "ltr" }}>{x.scope_key}</TableCell>
                <TableCell>
                  <Chip size="small" color={modeColor[x.mode]} label={x.mode} />
                </TableCell>
                <TableCell>
                  {new Date(x.effective_from).toLocaleString(locale)} →{" "}
                  {x.effective_until
                    ? new Date(x.effective_until).toLocaleString(locale)
                    : t("featurePolicy.noExpiry")}
                </TableCell>
                <TableCell>{x.version.toLocaleString(locale)}</TableCell>
                <TableCell>
                  <Button
                    size="small"
                    color="error"
                    startIcon={<Delete />}
                    onClick={() => setRemoving(x)}
                  >
                    {t("featurePolicy.remove")}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
        <Typography variant="h6">{t("featurePolicy.preview")}</Typography>
        <Typography variant="body2" color="text.secondary" mb={1}>
          {t("featurePolicy.previewHelp")}
        </Typography>
        <Stack direction={{ xs: "column", lg: "row" }} gap={1}>
          <SelectCatalog
            label={t("featurePolicy.client")}
            value={previewClient}
            setValue={(value) => {
              setPreviewClient(value);
              setPreviewContract("");
            }}
            items={clients.data}
          />
          <TextField
            select
            size="small"
            label={t("featurePolicy.contract")}
            value={previewContract}
            onChange={(e) => setPreviewContract(e.target.value)}
            sx={{ minWidth: 210 }}
          >
            <MenuItem value="">{t("featurePolicy.any")}</MenuItem>
            {contracts.data
              ?.filter(
                (x) => !previewClient || x.client_id === Number(previewClient),
              )
              .map((x) => (
                <MenuItem key={x.id} value={x.id}>
                  <span dir="ltr">{x.contract_number}</span> — {x.name}
                </MenuItem>
              ))}
          </TextField>
          <SelectCatalog
            label={t("featurePolicy.product")}
            value={previewProduct}
            setValue={setPreviewProduct}
            items={products.data}
          />
          <SelectCatalog
            label={t("featurePolicy.service")}
            value={previewService}
            setValue={setPreviewService}
            items={services.data}
          />
        </Stack>
        {preview.data && (
          <Alert
            severity={
              preview.data.mode === "ENFORCED"
                ? "success"
                : preview.data.mode === "SHADOW"
                  ? "warning"
                  : "info"
            }
            sx={{ mt: 2 }}
          >
            {t("featurePolicy.effective", {
              mode: preview.data.mode,
              source: preview.data.source_scope_key,
              version: preview.data.policy_version.toLocaleString(locale),
            })}
          </Alert>
        )}
      </Paper>
      <Dialog
        open={editor}
        onClose={() => setEditor(false)}
        fullWidth
        maxWidth="sm"
      >
        <form onSubmit={submit}>
          <DialogTitle>
            {t("featurePolicy.addTitle", { name: feature?.name })}
          </DialogTitle>
          <DialogContent>
            <TextField
              select
              required
              name="scope_type"
              label={t("featurePolicy.scope")}
              defaultValue="SYSTEM"
              fullWidth
              margin="normal"
            >
              {feature?.supported_scopes.map((x) => (
                <MenuItem key={x} value={x}>
                  {x.replace("_", " / ")}
                </MenuItem>
              ))}
            </TextField>
            <Typography variant="caption" color="text.secondary">
              {t("featurePolicy.scopeHelp")}
            </Typography>
            {featureKey === "engineer_pre_ticket" && (
              <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
                <Typography fontWeight={700}>
                  {t("preTickets.fastCreateProfile")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("preTickets.fastCreateHelp")}
                </Typography>
                <TextField
                  select
              name="pre_ticket_type_id"
                  label={t("preTickets.defaultTicketType")}
                  defaultValue=""
                  fullWidth
                  margin="normal"
                >
                  <MenuItem value="">
                    {t("preTickets.selectTicketType")}
                  </MenuItem>
                  {ticketTypes.data
                    ?.filter((item) => item.is_active)
                    .map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        {item.code} — {item.name}
                      </MenuItem>
                    ))}
                </TextField>
                {["P1", "P2", "P3", "P4"].map((priority) => (
                  <Stack key={priority} direction="row" gap={1} sx={{ mb: 1 }}>
                    <Typography sx={{ width: 28, pt: 1 }}>
                      {priority}
                    </Typography>
                    <TextField
                      select
                    name={`pre_ticket_${priority}_impact`}
                    label={t('tickets.fields.impact')}
                      defaultValue="MEDIUM"
                      fullWidth
                    >
                      {impactUrgencyValues.map((value) => (
                        <MenuItem key={value} value={value}>
                          {value}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      select
                    name={`pre_ticket_${priority}_urgency`}
                    label={t('tickets.fields.urgency')}
                      defaultValue="MEDIUM"
                      fullWidth
                    >
                      {impactUrgencyValues.map((value) => (
                        <MenuItem key={value} value={value}>
                          {value}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Stack>
                ))}
              </Paper>
            )}
            <FormCatalog
              name="client_id"
              label={t("featurePolicy.client")}
              items={clients.data}
            />
            <TextField
              select
              name="contract_id"
              label={t("featurePolicy.contract")}
              defaultValue=""
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("featurePolicy.notScoped")}</MenuItem>
              {contracts.data?.map((x) => (
                <MenuItem key={x.id} value={x.id}>
                  <span dir="ltr">{x.contract_number}</span> — {x.name}
                </MenuItem>
              ))}
            </TextField>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <FormCatalog
                name="product_id"
                label={t("featurePolicy.product")}
                items={products.data}
              />
              <FormCatalog
                name="service_id"
                label={t("featurePolicy.service")}
                items={services.data}
              />
            </Stack>
            <TextField
              select
              required
              name="mode"
              label={t("featurePolicy.operatingMode")}
              defaultValue="OFF"
              fullWidth
              margin="normal"
            >
              {(["OFF", "SHADOW", "ENFORCED"] as const).map((mode) => (
                <MenuItem key={mode} value={mode}>
                  {t(`featurePolicy.modes.${mode}`)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              type="datetime-local"
              name="effective_until"
              label={t("featurePolicy.expiry")}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              required
              name="reason"
              label={t("featurePolicy.reason")}
              multiline
              rows={2}
              inputProps={{ minLength: 5, maxLength: 500 }}
              fullWidth
              margin="normal"
            />
            {save.isError && (
              <Alert severity="error">{t("featurePolicy.saveFailed")}</Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditor(false)}>
              {t("featurePolicy.cancel")}
            </Button>
            <Button type="submit" variant="contained" disabled={save.isPending}>
              {t("featurePolicy.save")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Dialog
        open={Boolean(removing)}
        onClose={() => setRemoving(null)}
        fullWidth
        maxWidth="xs"
      >
        <RemoveForm
          pending={remove.isPending}
          onSubmit={(reason) =>
            removing && remove.mutate({ item: removing, reason })
          }
        />
      </Dialog>
    </Paper>
  );
}

function SelectCatalog({
  label,
  value,
  setValue,
  items,
}: {
  label: string;
  value: string;
  setValue: (value: string) => void;
  items?: Catalog[];
}) {
  const { t } = useTranslation();
  return (
    <TextField
      select
      size="small"
      label={label}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      sx={{ minWidth: 180 }}
    >
      <MenuItem value="">{t("featurePolicy.any")}</MenuItem>
      {items?.map((x) => (
        <MenuItem key={x.id} value={x.id}>
          {x.name}
        </MenuItem>
      ))}
    </TextField>
  );
}
function FormCatalog({
  name,
  label,
  items,
}: {
  name: string;
  label: string;
  items?: Catalog[];
}) {
  const { t } = useTranslation();
  return (
    <TextField
      select
      name={name}
      label={label}
      defaultValue=""
      fullWidth
      margin="normal"
    >
      <MenuItem value="">{t("featurePolicy.notScoped")}</MenuItem>
      {items?.map((x) => (
        <MenuItem key={x.id} value={x.id}>
          {x.name}
        </MenuItem>
      ))}
    </TextField>
  );
}
function RemoveForm({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (reason: string) => void;
}) {
  const { t } = useTranslation();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(String(new FormData(event.currentTarget).get("reason") || ""));
  }
  return (
    <form onSubmit={submit}>
      <DialogTitle>{t("featurePolicy.removeTitle")}</DialogTitle>
      <DialogContent>
        <Alert severity="warning">{t("featurePolicy.removeWarning")}</Alert>
        <TextField
          required
          name="reason"
          label={t("featurePolicy.removalReason")}
          inputProps={{ minLength: 5, maxLength: 500 }}
          fullWidth
          multiline
          rows={2}
          margin="normal"
        />
      </DialogContent>
      <DialogActions>
        <Button
          type="submit"
          color="error"
          variant="contained"
          disabled={pending}
        >
          {t("featurePolicy.removeOverride")}
        </Button>
      </DialogActions>
    </form>
  );
}
