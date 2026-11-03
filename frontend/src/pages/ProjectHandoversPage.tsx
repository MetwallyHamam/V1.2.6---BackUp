import { Add, Edit } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { QuickCreateClientDialog } from "./QuickCreateClientDialog";
import { serverDateInput } from '../utils/serverTime'

type Option = {
  id: number;
  name: string;
  name_ar?: string;
  full_name?: string;
};
type Line = {
  product_id: string;
  product_module_id: string;
  service_id: string;
  delivery_status: string;
  delivered_version: string;
  delivery_percent: string;
  delivery_date: string;
  notes: string;
};
type PendingPoint = {
  product_id: string;
  product_module_id: string;
  service_id: string;
  description: string;
  status: string;
};
type ScopeCatalog = {
  modules: Array<Option & { product_id: number }>;
  services: Option[];
  templates: Array<Option & { version: number }>;
};
type Handover = {
  id: number;
  project_number: string;
  project_name: string;
  client_id: number;
  client_name: string;
  delivered_by_name: string;
  current_status: string;
  project_manager_user_id?: number;
  project_manager_name?: string;
  project_manager_email?: string;
  project_manager_phone?: string;
  warranty_start_date?: string;
  acceptance_date?: string;
  warranty_months?: number;
  pending_points?: string;
  notes?: string;
  source_template_id?: number;
  source_template_version?: number;
  source_templates: Array<{ template_id: number; template_version: number }>;
  structured_pending_points: Array<{
    product_id: number;
    product_module_id?: number;
    service_id?: number;
    description: string;
    status: string;
  }>;
  recipients: Array<{ user_id: number; name: string; accepted: boolean }>;
  products: Array<{
    product_id: number;
    product: string;
    product_module_id?: number;
    module?: string;
    service_id?: number;
    service?: string;
    delivery_status: string;
    delivered_version?: string;
    delivery_percent?: number;
    delivery_date?: string;
    notes?: string;
  }>;
  comments: Array<{ author: string; body: string }>;
  documents?: Array<{
    id: number;
    original_filename: string;
    size_bytes: number;
    uploaded_by: string;
  }>;
};
const blankLine = (): Line => ({
  product_id: "",
  product_module_id: "",
  service_id: "",
  delivery_status: "PENDING",
  delivered_version: "",
  delivery_percent: "",
  delivery_date: "",
  notes: "",
});
const blankPoint = (): PendingPoint => ({
  product_id: "",
  product_module_id: "",
  service_id: "",
  description: "",
  status: "OPEN",
});

export function ProjectHandoversPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const locale = language === "ar" ? "ar-EG" : "en-GB";
  const statusLabel = (v: string) =>
    t(`projectHandovers.statuses.${v}`, { defaultValue: v });
  const deliveryLabel = (v: string) =>
    t(`projectHandovers.deliveryStatuses.${v}`, { defaultValue: v });
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Handover | null>(null);
  const [selected, setSelected] = useState<Handover | null>(null);
  const [clientDialog, setClientDialog] = useState(false);
  const [clientId, setClientId] = useState<number | null>(null);
  const [recipientIds, setRecipientIds] = useState<number[]>([]);
  const [createdClient, setCreatedClient] = useState<Option | null>(null);
  const [notice, setNotice] = useState<string>("");
  const [lines, setLines] = useState<Line[]>([blankLine()]);
  const [points, setPoints] = useState<PendingPoint[]>([]);
  const [sourceTemplates, setSourceTemplates] = useState<
    Array<{ template_id: number; template_version: number }>
  >([]);
  const [comment, setComment] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const handovers = useQuery({
    queryKey: ["project-handovers"],
    queryFn: async () => (await api.get<Handover[]>("/project-handovers")).data,
  });
  const clientsQuery = useQuery({
    queryKey: ["project-handover-clients"],
    queryFn: async () =>
      (
        await api.get<Option[]>("/project-handovers/options/clients", {
          params: { limit: 200 },
        })
      ).data,
  });
  const clients = [
    ...(clientsQuery.data ?? []).filter((x) => x.id !== createdClient?.id),
    ...(createdClient ? [createdClient] : []),
  ].sort((a, b) => a.name.localeCompare(b.name));
  const products = useQuery({
    queryKey: ["project-handover-products", language],
    queryFn: async () =>
      (await api.get<Option[]>("/project-handovers/options/products")).data.map(
        (x) => ({ ...x, name: getLocalizedName(x, language) }),
      ),
  });
  const engineers = useQuery({
    queryKey: ["handover-engineers"],
    queryFn: async () =>
      (await api.get<Option[]>("/project-handovers/options/engineers")).data,
  });
  const scopeCatalog = useQuery({
    queryKey: ["project-handover-scope-catalog"],
    queryFn: async () =>
      (await api.get<ScopeCatalog>("/project-handovers/options/scope-catalog"))
        .data,
  });
  const create = useMutation({
    mutationFn: async (payload: object) => {
      let row = (await api.post<Handover>("/project-handovers", payload)).data;
      for (const file of files) {
        const form = new FormData();
        form.append("upload", file);
        row = (
          await api.post<Handover>(
            `/project-handovers/${row.id}/documents`,
            form,
          )
        ).data;
      }
      return row;
    },
    onSuccess: async (row) => {
      setOpen(false);
      setSelected(row);
      await qc.invalidateQueries({ queryKey: ["project-handovers"] });
    },
  });
  const update = useMutation({
    mutationFn: async (payload: object) =>
      (await api.patch<Handover>(`/project-handovers/${editing?.id}`, payload))
        .data,
    onSuccess: async (row) => {
      setOpen(false);
      setEditing(null);
      setSelected(row);
      await qc.invalidateQueries({ queryKey: ["project-handovers"] });
    },
  });
  const addComment = useMutation({
    mutationFn: async () =>
      (
        await api.post<Handover>(
          `/project-handovers/${selected?.id}/comments`,
          { body: comment },
        )
      ).data,
    onSuccess: (row) => {
      setSelected(row);
      setComment("");
    },
  });
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("upload", file);
      return (
        await api.post<Handover>(
          `/project-handovers/${selected?.id}/documents`,
          form,
        )
      ).data;
    },
    onSuccess: (row) => setSelected(row),
  });
  const applyTemplates = async (ids: number[]) => {
    if (!ids.length) {
      setSourceTemplates([]);
      setLines([blankLine()]);
      setPoints([]);
      return;
    }
    const scopes = await Promise.all(
      ids.map(async (id) =>
        (
          await api.get<{
            template_id: number;
            template_version: number;
            rows: Array<{
              product_id: number;
              product_module_id?: number;
              service_id?: number;
            }>;
          }>(`/project-handovers/options/templates/${id}/scope`)
        ).data,
      ),
    );
    setSourceTemplates(
      scopes.map((scope) => ({
        template_id: scope.template_id,
        template_version: scope.template_version,
      })),
    );
    const uniqueRows = new Map<string, (typeof scopes)[number]["rows"][number]>();
    scopes.flatMap((scope) => scope.rows).forEach((row) => {
      uniqueRows.set(
        `${row.product_id}:${row.product_module_id ?? ""}:${row.service_id ?? ""}`,
        row,
      );
    });
    setLines(
      [...uniqueRows.values()].map((row) => ({
        ...blankLine(),
        product_id: String(row.product_id),
        product_module_id: row.product_module_id
          ? String(row.product_module_id)
          : "",
        service_id: row.service_id ? String(row.service_id) : "",
      })),
    );
    setPoints([]);
  };
  const startCreate = () => {
    setEditing(null);
    setClientId(null);
    setRecipientIds([]);
    setLines([blankLine()]);
    setPoints([]);
    setSourceTemplates([]);
    setFiles([]);
    setOpen(true);
  };
  const startEdit = (row: Handover) => {
    setEditing(row);
    setClientId(row.client_id);
    setRecipientIds(row.recipients.map((x) => x.user_id));
    setSourceTemplates(
      row.source_templates?.length
        ? row.source_templates
        : row.source_template_id && row.source_template_version
          ? [{ template_id: row.source_template_id, template_version: row.source_template_version }]
          : [],
    );
    setLines(
      row.products.length
        ? row.products.map((x) => ({
            product_id: String(x.product_id),
            product_module_id: x.product_module_id
              ? String(x.product_module_id)
              : "",
            service_id: x.service_id ? String(x.service_id) : "",
            delivery_status: x.delivery_status,
            delivered_version: x.delivered_version ?? "",
            delivery_percent:
              x.delivery_percent == null ? "" : String(x.delivery_percent),
            delivery_date: x.delivery_date ?? "",
            notes: x.notes ?? "",
          }))
        : [blankLine()],
    );
    setPoints(
      row.structured_pending_points.map((x) => ({
        product_id: String(x.product_id),
        product_module_id: x.product_module_id
          ? String(x.product_module_id)
          : "",
        service_id: x.service_id ? String(x.service_id) : "",
        description: x.description,
        status: x.status,
      })),
    );
    setSelected(null);
    setOpen(true);
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      source_template_id: sourceTemplates[0]?.template_id ?? null,
      source_template_version: sourceTemplates[0]?.template_version ?? null,
      source_templates: sourceTemplates,
      project_number: editing ? null : form.get("project_number"),
      project_name: form.get("project_name"),
      client_id: Number(form.get("client_id")),
      recipient_user_ids: recipientIds,
      project_manager_user_id: form.get("project_manager_user_id")
        ? Number(form.get("project_manager_user_id"))
        : null,
      project_manager_name: form.get("project_manager_name") || null,
      project_manager_email: form.get("project_manager_email") || null,
      project_manager_phone: form.get("project_manager_phone") || null,
      warranty_months: form.get("warranty_months")
        ? Number(form.get("warranty_months"))
        : null,
      warranty_start_date: form.get("warranty_start_date") || null,
      acceptance_date: form.get("acceptance_date") || null,
      pending_points: null,
      structured_pending_points: points
        .filter((x) => x.product_id && x.description.trim())
        .map((x) => ({
          ...x,
          product_id: Number(x.product_id),
          product_module_id: x.product_module_id
            ? Number(x.product_module_id)
            : null,
          service_id: x.service_id ? Number(x.service_id) : null,
        })),
      current_status: form.get("current_status"),
      notes: form.get("notes") || null,
      products: lines
        .filter((x) => x.product_id)
        .map((x) => ({
          ...x,
          product_id: Number(x.product_id),
          product_module_id: x.product_module_id
            ? Number(x.product_module_id)
            : null,
          service_id: x.service_id ? Number(x.service_id) : null,
          delivery_date:
            x.delivery_status === "DELIVERED"
              ? x.delivery_date || serverDateInput()
              : null,
          delivery_percent: x.delivery_percent
            ? Number(x.delivery_percent)
            : null,
        })),
    };
    if (editing) update.mutate(payload);
    else create.mutate(payload);
  };
  const canEdit = (row: Handover) =>
    hasPermission("project_handover.edit_pending") &&
    ["DRAFT", "READY", "ON_HOLD"].includes(row.current_status);
  return (
    <Stack spacing={2.5}>
      <QuickCreateClientDialog
        open={clientDialog}
        onClose={() => setClientDialog(false)}
        onCreated={(client, warning) => {
          setClientDialog(false);
          setCreatedClient(client);
          setClientId(client.id);
          setNotice(
            warning ??
              t("projectHandovers.clientCreated", { name: client.name }),
          );
        }}
      />
      <Paper
        sx={{
          p: 2.5,
          background: "linear-gradient(120deg,#006064,#00838f)",
          color: "white",
        }}
      >
        <Stack direction="row" alignItems="center">
          <Box flexGrow={1}>
            <Typography variant="h4" fontWeight={800}>
              {t("projectHandovers.title")}
            </Typography>
            <Typography>{t("projectHandovers.subtitle")}</Typography>
          </Box>
          {hasPermission("project_handover.manage") && (
            <Button
              variant="contained"
              color="inherit"
              sx={{ color: "#006064" }}
              startIcon={<Add />}
              onClick={startCreate}
            >
              {t("projectHandovers.deliverProject")}
            </Button>
          )}
        </Stack>
      </Paper>
      {notice && <Alert onClose={() => setNotice("")}>{notice}</Alert>}
      {handovers.isError && (
        <Alert severity="error">{t("projectHandovers.loadFailed")}</Alert>
      )}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(2,1fr)" },
          gap: 2,
        }}
      >
        {handovers.data?.map((row) => (
          <Paper
            key={row.id}
            variant="outlined"
            sx={{ p: 2, cursor: "pointer" }}
            onClick={() => setSelected(row)}
          >
            <Stack direction="row" justifyContent="space-between">
              <Typography fontWeight={800}>{row.project_number}</Typography>
              <Chip label={statusLabel(row.current_status)} />
            </Stack>
            <Typography variant="h6">{row.project_name}</Typography>
            <Typography>{row.client_name}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("projectHandovers.deliverySummary", {
                deliveredBy: row.delivered_by_name,
                recipients: row.recipients.map((x) => x.name).join(", "),
              })}
            </Typography>
          </Paper>
        ))}
      </Box>
      <Dialog
        open={!!selected}
        onClose={() => setSelected(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {selected?.project_number} — {selected?.project_name}
        </DialogTitle>
        <DialogContent dividers>
          {selected && (
            <Stack spacing={2}>
              <Typography>
                <b>{t("projectHandovers.client")}:</b> {selected.client_name} ·{" "}
                <b>{t("projectHandovers.status")}:</b>{" "}
                {statusLabel(selected.current_status)}
              </Typography>
              <Typography>
                <b>{t("projectHandovers.supportRecipients")}:</b>{" "}
                {selected.recipients.map((x) => x.name).join(", ")}
              </Typography>
              <Typography>
                <b>{t("projectHandovers.warranty")}:</b>{" "}
                {selected.warranty_months ?? "—"} {t("projectHandovers.months")}{" "}
                · <b>{t("projectHandovers.acceptance")}:</b>{" "}
                {selected.acceptance_date
                  ? new Date(selected.acceptance_date).toLocaleDateString(
                      locale,
                    )
                  : "—"}
              </Typography>
              {selected.pending_points && (
                <Alert severity="warning">{selected.pending_points}</Alert>
              )}
              {selected.products.map((x, i) => (
                <Paper key={i} variant="outlined" sx={{ p: 1.5 }}>
                  {x.product}
                  {x.module ? ` / ${x.module}` : ""} —{" "}
                  <Chip size="small" label={deliveryLabel(x.delivery_status)} />{" "}
                  {x.delivery_percent != null && `${x.delivery_percent}%`}
                </Paper>
              ))}
              <Typography variant="h6">
                {t("projectHandovers.deliveryAttachments")}
              </Typography>
              {(selected.documents ?? []).map((doc) => (
                <Stack key={doc.id} direction="row">
                  <Typography sx={{ flexGrow: 1 }}>
                    {doc.original_filename} ·{" "}
                    {(doc.size_bytes / 1024).toFixed(1)} KB
                  </Typography>
                  <Button
                    onClick={async () => {
                      const response = await api.get(
                        `/project-handovers/${selected.id}/documents/${doc.id}/download`,
                        { responseType: "blob" },
                      );
                      const url = URL.createObjectURL(response.data);
                      const anchor = document.createElement("a");
                      anchor.href = url;
                      anchor.download = doc.original_filename;
                      anchor.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    {t("projectHandovers.download")}
                  </Button>
                </Stack>
              ))}
              <Button component="label" variant="outlined">
                {t("projectHandovers.attachDocument")}
                <input
                  hidden
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) upload.mutate(file);
                  }}
                />
              </Button>
              <Typography variant="h6">
                {t("projectHandovers.comments")}
              </Typography>
              {selected.comments.map((x, i) => (
                <Paper key={i} variant="outlined" sx={{ p: 1 }}>
                  <b>{x.author}</b> · {x.body}
                </Paper>
              ))}
              <Stack direction="row">
                <TextField
                  fullWidth
                  label={t("projectHandovers.addComment")}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />
                <Button
                  disabled={comment.trim().length < 2}
                  onClick={() => addComment.mutate()}
                >
                  {t("projectHandovers.add")}
                </Button>
              </Stack>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          {selected && canEdit(selected) && (
            <Button
              startIcon={<Edit />}
              variant="contained"
              onClick={() => startEdit(selected)}
            >
              {t("projectHandovers.editProject", { defaultValue: "Edit project" })}
            </Button>
          )}
          <Button onClick={() => setSelected(null)}>
            {t("projectHandovers.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="lg"
      >
        <form key={editing?.id ?? "new"} onSubmit={submit}>
          <DialogTitle>
            {editing
              ? t("projectHandovers.editProjectTitle", {
                  number: editing.project_number,
                  defaultValue: "Edit project · {{number}}",
                })
              : t("projectHandovers.deliverImplementation")}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={1.5} mt={1}>
              {!editing && (
                <Alert severity="info">
                  {t("projectHandovers.numberAutomatic")}
                </Alert>
              )}
              <TextField
                required
                name="project_name"
                label={t("projectHandovers.projectName")}
                defaultValue={editing?.project_name ?? ""}
                fullWidth
              />
              <Stack direction="row" gap={1}>
                <TextField
                  select
                  required
                  name="client_id"
                  label={t("projectHandovers.client")}
                  value={clientId ?? ""}
                  onChange={(e) => setClientId(Number(e.target.value) || null)}
                  fullWidth
                >
                  {clients.map((x) => (
                    <MenuItem key={x.id} value={x.id}>
                      {x.name}
                    </MenuItem>
                  ))}
                </TextField>
                {hasPermission("project_handover.client.create") && (
                  <Button onClick={() => setClientDialog(true)}>
                    {t("projectHandovers.createClient")}
                  </Button>
                )}
              </Stack>
              <TextField
                select
                name="recipient_user_ids"
                label={t("projectHandovers.deliverToEngineers")}
                value={recipientIds.map(String)}
                onChange={(e) =>
                  setRecipientIds(
                    (typeof e.target.value === "string"
                      ? e.target.value.split(",")
                      : e.target.value
                    ).map(Number),
                  )
                }
                slotProps={{ select: { multiple: true } }}
              >
                {engineers.data?.map((x) => (
                  <MenuItem key={x.id} value={String(x.id)}>
                    {x.full_name}
                  </MenuItem>
                ))}
              </TextField>
              <Stack direction="row" gap={1}>
                <TextField
                  select
                  name="project_manager_user_id"
                  label={t("projectHandovers.projectManagerEmployee")}
                  defaultValue={
                    editing?.project_manager_user_id
                      ? String(editing.project_manager_user_id)
                      : ""
                  }
                  fullWidth
                >
                  <MenuItem value="">
                    {t("projectHandovers.externalDetails")}
                  </MenuItem>
                  {engineers.data?.map((x) => (
                    <MenuItem key={x.id} value={x.id}>
                      {x.full_name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  name="project_manager_name"
                  label={t("projectHandovers.pmName")}
                  defaultValue={editing?.project_manager_name ?? ""}
                />
                <TextField
                  name="project_manager_email"
                  label={t("projectHandovers.pmEmail")}
                  defaultValue={editing?.project_manager_email ?? ""}
                />
                <TextField
                  name="project_manager_phone"
                  label={t("projectHandovers.pmPhone")}
                  defaultValue={editing?.project_manager_phone ?? ""}
                />
              </Stack>
              <Stack direction="row" gap={1}>
                <TextField
                  name="warranty_months"
                  type="number"
                  label={t("projectHandovers.warrantyMonths")}
                  defaultValue={editing?.warranty_months ?? ""}
                />
                <TextField
                  name="warranty_start_date"
                  type="date"
                  label={t("projectHandovers.warrantyStarts")}
                  defaultValue={editing?.warranty_start_date ?? ""}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <TextField
                  name="acceptance_date"
                  type="date"
                  label={t("projectHandovers.acceptanceDate")}
                  defaultValue={editing?.acceptance_date ?? ""}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <TextField
                  select
                  name="current_status"
                  label={t("projectHandovers.currentStatus")}
                  defaultValue={editing?.current_status ?? "DRAFT"}
                >
                  {["DRAFT", "READY", "DELIVERED", "ACCEPTED", "ON_HOLD"].map(
                    (x) => (
                      <MenuItem key={x} value={x}>
                        {statusLabel(x)}
                      </MenuItem>
                    ),
                  )}
                </TextField>
              </Stack>
              <TextField
                select
                label={t("projectHandovers.contractTemplate", { defaultValue: "Contract templates" })}
                value={sourceTemplates.map((item) => String(item.template_id))}
                onChange={(e) => {
                  const value = e.target.value;
                  const ids = (typeof value === "string" ? value.split(",") : value).map(Number);
                  void applyTemplates(ids);
                }}
                helperText={t("projectHandovers.multipleTemplatesHelp", {
                  defaultValue:
                    "Selected templates are merged; duplicate product/module/service rows appear once.",
                })}
                slotProps={{ select: { multiple: true } }}
              >
                {scopeCatalog.data?.templates.map((x) => (
                  <MenuItem key={x.id} value={String(x.id)}>
                    {x.name} · v{x.version}
                  </MenuItem>
                ))}
              </TextField>
              <Typography variant="h6">
                {t("projectHandovers.productsModules", { defaultValue: "Products and modules" })}
              </Typography>
              {lines.map((line, index) => (
                <Stack
                  key={index}
                  direction={{ xs: "column", lg: "row" }}
                  flexWrap="wrap"
                  gap={1}
                  sx={{ p: 1.5, border: 1, borderColor: "divider", borderRadius: 2 }}
                >
                  <TextField
                    select
                    required
                    fullWidth
                    sx={{ minWidth: { lg: 220 }, flex: "2 1 220px" }}
                    label={t("projectHandovers.product", { defaultValue: "Product" })}
                    value={line.product_id}
                    onChange={(e) =>
                      setLines((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, product_id: e.target.value }
                            : x,
                        ),
                      )
                    }
                  >
                    {products.data?.map((x) => (
                      <MenuItem key={x.id} value={x.id}>
                        {x.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    fullWidth
                    sx={{ minWidth: { lg: 220 }, flex: "2 1 220px" }}
                    label={t("projectHandovers.moduleOptional", { defaultValue: "Module (optional)" })}
                    value={line.product_module_id}
                    onChange={(e) =>
                      setLines((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, product_module_id: e.target.value }
                            : x,
                        ),
                      )
                    }
                  >
                    <MenuItem value="">{t("projectHandovers.none", { defaultValue: "None" })}</MenuItem>
                    {scopeCatalog.data?.modules
                      .filter((x) => x.product_id === Number(line.product_id))
                      .map((x) => (
                        <MenuItem key={x.id} value={x.id}>
                          {x.name}
                        </MenuItem>
                      ))}
                  </TextField>
                  <TextField
                    select
                    fullWidth
                    sx={{ minWidth: { lg: 220 }, flex: "2 1 220px" }}
                    label={t("projectHandovers.service", { defaultValue: "Service" })}
                    value={line.service_id}
                    onChange={(e) =>
                      setLines((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, service_id: e.target.value }
                            : x,
                        ),
                      )
                    }
                  >
                    <MenuItem value="">{t("projectHandovers.none", { defaultValue: "None" })}</MenuItem>
                    {scopeCatalog.data?.services.map((x) => (
                      <MenuItem key={x.id} value={x.id}>
                        {x.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    fullWidth
                    sx={{ minWidth: { lg: 170 }, flex: "1 1 170px" }}
                    label={t("projectHandovers.deliveryStatus")}
                    value={line.delivery_status}
                    onChange={(e) =>
                      setLines((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, delivery_status: e.target.value }
                            : x,
                        ),
                      )
                    }
                  >
                    {["DELIVERED", "PENDING", "HOLD"].map((x) => (
                      <MenuItem key={x} value={x}>
                        {deliveryLabel(x)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    fullWidth
                    sx={{ minWidth: { lg: 150 }, flex: "1 1 150px" }}
                    label={t("projectHandovers.version")}
                    value={line.delivered_version}
                    onChange={(e) =>
                      setLines((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, delivered_version: e.target.value }
                            : x,
                        ),
                      )
                    }
                  />
                  <TextField
                    type="date"
                    fullWidth
                    sx={{ minWidth: { lg: 170 }, flex: "1 1 170px" }}
                    label={t("projectHandovers.deliveryDate")}
                    value={line.delivery_date}
                    disabled={line.delivery_status !== "DELIVERED"}
                    slotProps={{ inputLabel: { shrink: true } }}
                    onChange={(e) =>
                      setLines((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, delivery_date: e.target.value }
                            : x,
                        ),
                      )
                    }
                  />
                  <TextField
                    label="%"
                    type="number"
                    fullWidth
                    sx={{ minWidth: { lg: 110 }, flex: "1 1 110px" }}
                    value={line.delivery_percent}
                    onChange={(e) =>
                      setLines((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, delivery_percent: e.target.value }
                            : x,
                        ),
                      )
                    }
                  />
                  <Button
                    color="error"
                    onClick={() =>
                      setLines((v) => v.filter((_, i) => i !== index))
                    }
                  >
                    {t("projectHandovers.remove")}
                  </Button>
                </Stack>
              ))}
              <Button onClick={() => setLines((v) => [...v, blankLine()])}>
                {t("projectHandovers.addProductModule")}
              </Button>
              <Typography variant="h6">
                {t("projectHandovers.structuredPendingPoints", { defaultValue: "Pending points" })}
              </Typography>
              {points.map((point, index) => (
                <Stack key={index} direction={{ xs: "column", md: "row" }} gap={1}>
                  <TextField
                    select
                    fullWidth
                    sx={{ minWidth: { md: 280 }, flex: "1 1 320px" }}
                    label={t("projectHandovers.product", { defaultValue: "Product / module / service" })}
                    value={point.product_id}
                    onChange={(e) => {
                      const row = lines.find(
                        (x) => x.product_id === e.target.value,
                      );
                      setPoints((v) =>
                        v.map((x, i) =>
                          i === index
                            ? {
                                ...x,
                                product_id: e.target.value,
                                product_module_id: row?.product_module_id ?? "",
                                service_id: row?.service_id ?? "",
                              }
                            : x,
                        ),
                      );
                    }}
                  >
                    {lines.map((x, i) => (
                      <MenuItem key={i} value={x.product_id}>
                        {
                          products.data?.find(
                            (p) => p.id === Number(x.product_id),
                          )?.name
                        }{" "}
                        {x.product_module_id
                          ? `/ ${scopeCatalog.data?.modules.find((m) => m.id === Number(x.product_module_id))?.name}`
                          : ""}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    required
                    label={t("projectHandovers.pendingPointDescription", { defaultValue: "Pending point description" })}
                    value={point.description}
                    onChange={(e) =>
                      setPoints((v) =>
                        v.map((x, i) =>
                          i === index
                            ? { ...x, description: e.target.value }
                            : x,
                        ),
                      )
                    }
                    fullWidth
                  />
                  <TextField
                    select
                    fullWidth
                    sx={{ minWidth: { md: 160 }, flex: "0 1 180px" }}
                    label={t("projectHandovers.pendingPointStatus", { defaultValue: "Point status" })}
                    value={point.status}
                    onChange={(e) =>
                      setPoints((v) =>
                        v.map((x, i) =>
                          i === index ? { ...x, status: e.target.value } : x,
                        ),
                      )
                    }
                  >
                    <MenuItem value="OPEN">
                      {t("projectHandovers.open")}
                    </MenuItem>
                    <MenuItem value="RESOLVED">
                      {t("projectHandovers.resolved")}
                    </MenuItem>
                  </TextField>
                  <Button
                    color="error"
                    onClick={() =>
                      setPoints((v) => v.filter((_, i) => i !== index))
                    }
                  >
                    {t("projectHandovers.remove")}
                  </Button>
                </Stack>
              ))}
              <Button onClick={() => setPoints((v) => [...v, blankPoint()])}>
                {t("projectHandovers.addPendingPoint", { defaultValue: "Add pending point" })}
              </Button>
              <TextField
                name="notes"
                label={t("projectHandovers.statusNotes")}
                defaultValue={editing?.notes ?? ""}
                multiline
              />
              {!editing && (
                <Button component="label">
                  {t("projectHandovers.selectDocuments")}
                  <input
                    hidden
                    multiple
                    type="file"
                    onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
                  />
                </Button>
              )}
              {(create.isError || update.isError) && (
                <Alert severity="error">
                  {editing
                    ? t("projectHandovers.updateFailed")
                    : t("projectHandovers.createFailed")}
                </Alert>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>
              {t("projectHandovers.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={create.isPending || update.isPending || !lines.length}
            >
              {editing
                ? t("projectHandovers.saveChanges")
                : t("projectHandovers.deliverProject")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Stack>
  );
}
