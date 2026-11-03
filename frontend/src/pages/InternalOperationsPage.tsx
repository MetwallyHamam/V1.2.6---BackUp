import {
  AttachFile,
  Add,
  Download,
  Groups,
  Schedule,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { serverDateTimeInput } from "../utils/serverTime";
import { OperationTemplatesPanel } from "./OperationTemplatesPanel";
import { OperationTypesPanel } from "./OperationTypesPanel";
import { SmartOperationBuilder } from "./SmartOperationBuilder";

type Person = {
  id: number;
  full_name: string;
  department?: string;
  job_title?: string;
};
type ClientOption = { id: number; code: string; name: string };
type OperationComment = {
  id: number;
  author_name: string;
  comment_type: string;
  body: string;
  created_at: string;
};
type OperationDocument = {
  id: number;
  original_filename: string;
  size_bytes: number;
  uploaded_by_name: string;
  created_at: string;
};
type Operation = {
  id: number;
  title: string;
  operation_type: string;
  status: string;
  starts_at: string;
  ends_at: string;
  location?: string;
  client_id?: number;
  client_code?: string;
  client_name?: string;
  description?: string;
  created_by_name: string;
  assignees: Person[];
  comments: OperationComment[];
  documents: OperationDocument[];
};
type OperationType = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  color: string;
  supports_client: boolean;
};

const typeLabels: Record<string, string> = {
  WORK_FROM_HOME: "Work from home",
  OUTDOOR_VISIT: "Outdoor / field visit",
  MEETING: "Meeting",
  DEMO: "Client / sales demo",
  AFTER_SHIFT: "After-shift work",
};
const statusColors: Record<
  string,
  "default" | "info" | "warning" | "success" | "error"
> = {
  SCHEDULED: "info",
  IN_PROGRESS: "warning",
  COMPLETED: "success",
  CANCELLED: "error",
};
const dateInput = (value: Date) => serverDateTimeInput(value);
const todayInput = () => dateInput(new Date()).slice(0, 10);

export function InternalOperationsPage({
  initialCreateType,
  initialCreateDate,
  dialogOnly = false,
  onCreated,
  onClose,
}: {
  initialCreateType?: string;
  initialCreateDate?: string;
  dialogOnly?: boolean;
  onCreated?: () => void | Promise<void>;
  onClose?: () => void;
} = {}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const localDate = (value: string) =>
    new Date(value).toLocaleString(locale, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  const typeLabel = (value: string) =>
    t(`internalOperations.types.${value}`, {
      defaultValue:
        operationTypes.data?.find((row) => row.code === value)?.name ??
        typeLabels[value] ??
        value,
    });
  const statusLabel = (value: string) =>
    t(`internalOperations.status.${value}`, {
      defaultValue: value.replaceAll("_", " "),
    });
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canCreate =
    hasPermission("internal_operation.create") ||
    hasPermission("internal_operation.manage");
  const canManageTemplates =
    hasPermission("internal_operation.template.manage") ||
    hasPermission("internal_operation.type.manage") ||
    hasPermission("internal_operation.manage");
  const canTransition = hasPermission("internal_operation.transition");
  const canComment = hasPermission("internal_operation.comment");
  const canUpload = hasPermission("internal_operation.document.upload");
  const canDownload = hasPermission("internal_operation.document.download");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(dialogOnly);
  const [generatorOpen, setGeneratorOpen] = useState(false);
  const [workspace, setWorkspace] = useState<"OPERATIONS" | "TEMPLATES">(
    "OPERATIONS",
  );
  const [operationType, setOperationType] = useState("OUTDOOR_VISIT"),
    [operationTitle, setOperationTitle] = useState(typeLabels.OUTDOOR_VISIT);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState(
    () => searchParams.get("status") ?? "",
  );
  const [dateFrom, setDateFrom] = useState(
    () => searchParams.get("date_from") ?? todayInput(),
  );
  const [dateTo, setDateTo] = useState(
    () => searchParams.get("date_to") ?? todayInput(),
  );
  const [commentType, setCommentType] = useState("COMMENT");
  const [commentBody, setCommentBody] = useState("");
  const clientFilter = searchParams.get("client_id") ?? "";
  const requestedDate = initialCreateDate ?? searchParams.get("date");
  const requestedStart = requestedDate
    ? new Date(`${requestedDate}T09:00:00`)
    : new Date();
  const operations = useQuery({
    queryKey: [
      "internal-operations",
      typeFilter,
      statusFilter,
      dateFrom,
      dateTo,
      clientFilter,
    ],
    queryFn: async () =>
      (
        await api.get<Operation[]>("/internal-operations", {
          params: {
            operation_type: typeFilter || undefined,
            status: statusFilter || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
            client_id: clientFilter || undefined,
          },
        })
      ).data,
  });
  const engineers = useQuery({
    queryKey: ["internal-operation-engineers"],
    queryFn: async () =>
      (await api.get<Person[]>("/internal-operations/engineers")).data,
  });
  const clients = useQuery({
    queryKey: ["internal-operation-clients"],
    queryFn: async () =>
      (await api.get<ClientOption[]>("/internal-operations/clients")).data,
  });
  const operationTypes = useQuery({
    queryKey: ["internal-operation-types", i18n.language],
    queryFn: async () =>
      (await api.get<OperationType[]>("/internal-operations/types")).data.map(
        (row) => ({ ...row, name: getLocalizedName(row, i18n.language) }),
      ),
  });
  const detail = useQuery({
    queryKey: ["internal-operation", selectedId],
    queryFn: async () =>
      (await api.get<Operation>(`/internal-operations/${selectedId}`)).data,
    enabled: selectedId !== null,
  });
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["internal-operations"] });
    await queryClient.invalidateQueries({
      queryKey: ["internal-operation", selectedId],
    });
  };
  const create = useMutation({
    mutationFn: async (payload: object) =>
      (await api.post<Operation>("/internal-operations", payload)).data,
    onSuccess: async (row) => {
      setCreateOpen(false);
      await onCreated?.();
      onClose?.();
      setSelectedId(row.id);
      await refresh();
    },
  });
  const updateStatus = useMutation({
    mutationFn: async (status: string) =>
      api.patch(`/internal-operations/${selectedId}`, { status }),
    onSuccess: refresh,
  });
  const addComment = useMutation({
    mutationFn: async () =>
      api.post(`/internal-operations/${selectedId}/comments`, {
        comment_type: commentType,
        body: commentBody,
      }),
    onSuccess: async () => {
      setCommentBody("");
      await refresh();
    },
  });
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("upload", file);
      return api.post(`/internal-operations/${selectedId}/documents`, form);
    },
    onSuccess: refresh,
  });
  const submitCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      title: operationTitle,
      operation_type: operationType,
      starts_at: new Date(String(form.get("starts_at"))).toISOString(),
      ends_at: new Date(String(form.get("ends_at"))).toISOString(),
      location: form.get("location") || null,
      client_id: form.get("client_id") ? Number(form.get("client_id")) : null,
      description: form.get("description") || null,
      assignee_user_ids: form.getAll("assignee_user_ids").map(Number),
    });
  };
  const download = async (document: OperationDocument) => {
    const response = await api.get(
      `/internal-operations/${selectedId}/documents/${document.id}/download`,
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(response.data);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = document.original_filename;
    link.click();
    URL.revokeObjectURL(url);
  };
  const row = detail.data;
  useEffect(() => {
    if (
      (dialogOnly || searchParams.get("create") === "operation") &&
      canCreate
    ) {
      const requestedType = initialCreateType ?? searchParams.get("type");
      const selected =
        operationTypes.data?.find((row) => row.code === requestedType) ??
        operationTypes.data?.[0];
      if (selected) {
        setOperationType(selected.code);
        setOperationTitle(selected.name);
      }
      setCreateOpen(true);
    }
    if (
      searchParams.get("create") === "generate" &&
      hasPermission("internal_operation.manage")
    )
      setGeneratorOpen(true);
  }, [
    searchParams,
    canCreate,
    hasPermission,
    operationTypes.data,
    dialogOnly,
    initialCreateType,
  ]);
  const closeCreate = () => {
    setCreateOpen(false);
    onClose?.();
  };
  const createDialog = (
    <Dialog open={createOpen} onClose={closeCreate} fullWidth maxWidth="md">
      <form onSubmit={submitCreate}>
        <DialogTitle>{t("internalOperations.createTitle")}</DialogTitle>
        <DialogContent>
          <TextField
            required
            label={t("internalOperations.titleField")}
            value={operationTitle}
            onChange={(event) => setOperationTitle(event.target.value)}
            helperText={t("internalOperations.titleHint")}
            fullWidth
            margin="normal"
          />
          <TextField
            required
            select
            label={t("internalOperations.operationType")}
            value={operationType}
            onChange={(event) => {
              const code = event.target.value;
              setOperationType(code);
              setOperationTitle(
                operationTypes.data?.find((row) => row.code === code)?.name ??
                  typeLabel(code),
              );
            }}
            fullWidth
            margin="normal"
          >
            {operationTypes.data?.map((type) => (
              <MenuItem key={type.id} value={type.code}>
                {typeLabel(type.code)}
              </MenuItem>
            ))}
          </TextField>
          <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
            <TextField
              required
              name="starts_at"
              type="datetime-local"
              label={t("internalOperations.starts")}
              defaultValue={dateInput(requestedStart)}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              required
              name="ends_at"
              type="datetime-local"
              label={t("internalOperations.ends")}
              defaultValue={dateInput(
                new Date(requestedStart.getTime() + 60 * 60_000),
              )}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Stack>
          <TextField
            select
            required
            name="assignee_user_ids"
            label={t("internalOperations.engineers")}
            fullWidth
            margin="normal"
            slotProps={{ select: { multiple: true, defaultValue: [] } }}
          >
            {engineers.data?.map((person) => (
              <MenuItem key={person.id} value={person.id}>
                {person.full_name} —{" "}
                {person.job_title ??
                  person.department ??
                  t("internalOperations.engineer")}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            name="client_id"
            label={t("internalOperations.linkedClient")}
            defaultValue=""
            fullWidth
            margin="normal"
          >
            <MenuItem value="">{t("internalOperations.noClient")}</MenuItem>
            {clients.data?.map((client) => (
              <MenuItem key={client.id} value={client.id}>
                <span dir="ltr">{client.code}</span>&nbsp;— {client.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            name="location"
            label={t("internalOperations.locationField")}
            fullWidth
            margin="normal"
          />
          <TextField
            name="description"
            label={t("internalOperations.descriptionField")}
            fullWidth
            multiline
            rows={4}
            margin="normal"
          />
          {create.isError && (
            <Alert severity="error">
              {t("internalOperations.createFailed")}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeCreate}>{t("common.actions.cancel")}</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={create.isPending || !operationTitle.trim()}
          >
            {t("internalOperations.createAssign")}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
  if (dialogOnly) return createDialog;
  const header = (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        background: "linear-gradient(120deg, #4527a0, #7b1fa2)",
        color: "white",
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ sm: "center" }}
        gap={2}
      >
        <Box flexGrow={1}>
          <Typography variant="h4" fontWeight={800}>
            {t("internalOperations.title")}
          </Typography>
          <Typography sx={{ opacity: 0.82 }}>
            {t("internalOperations.subtitle")}
          </Typography>
        </Box>
        {hasPermission("internal_operation.manage") &&
          workspace === "OPERATIONS" && (
            <Button
              color="inherit"
              variant="outlined"
              onClick={() => setGeneratorOpen(true)}
            >
              {t("internalOperations.generate")}
            </Button>
          )}
        {canManageTemplates && (
          <Button
            color="inherit"
            variant="outlined"
            onClick={() =>
              setWorkspace(
                workspace === "OPERATIONS" ? "TEMPLATES" : "OPERATIONS",
              )
            }
          >
            {t(
              workspace === "OPERATIONS"
                ? "internalOperations.templates"
                : "internalOperations.back",
            )}
          </Button>
        )}
        {canCreate && workspace === "OPERATIONS" && (
          <Button
            variant="contained"
            color="inherit"
            sx={{ color: "#4527a0" }}
            startIcon={<Add />}
            onClick={() => {
              const first = operationTypes.data?.[0];
              setOperationType(first?.code ?? "OUTDOOR_VISIT");
              setOperationTitle(first?.name ?? typeLabels.OUTDOOR_VISIT);
              setCreateOpen(true);
            }}
          >
            {t("internalOperations.quick")}
          </Button>
        )}
      </Stack>
    </Paper>
  );
  if (workspace === "TEMPLATES")
    return (
      <Stack spacing={3}>
        {header}
        <OperationTypesPanel />
        <OperationTemplatesPanel />
      </Stack>
    );

  return (
    <Stack spacing={3}>
      {header}
      <Dialog
        open={generatorOpen}
        onClose={() => setGeneratorOpen(false)}
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle>{t("internalOperations.generate")}</DialogTitle>
        <DialogContent dividers>
          <SmartOperationBuilder
            onApplied={() => {
              void refresh();
              setGeneratorOpen(false);
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGeneratorOpen(false)}>
            {t("common.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>{t("internalOperations.operationType")}</InputLabel>
            <Select
              value={typeFilter}
              label={t("internalOperations.operationType")}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <MenuItem value="">{t("internalOperations.allTypes")}</MenuItem>
              {Object.keys(typeLabels).map((value) => (
                <MenuItem key={value} value={value}>
                  {typeLabel(value)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>{t("internalOperations.statusLabel")}</InputLabel>
            <Select
              value={statusFilter}
              label={t("internalOperations.statusLabel")}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="">
                {t("internalOperations.allStatuses")}
              </MenuItem>
              {["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"].map(
                (value) => (
                  <MenuItem key={value} value={value}>
                    {statusLabel(value)}
                  </MenuItem>
                ),
              )}
            </Select>
          </FormControl>
          <TextField
            size="small"
            type="date"
            label={t("common.from")}
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            size="small"
            type="date"
            label={t("common.to")}
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Stack>
      </Paper>
      {operations.isError && (
        <Alert severity="error">{t("internalOperations.loadFailed")}</Alert>
      )}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: "repeat(2, 1fr)",
            xl: "repeat(3, 1fr)",
          },
          gap: 2,
        }}
      >
        {operations.data?.map((item) => (
          <Card key={item.id} variant="outlined">
            <CardActionArea
              sx={{ p: 2, height: "100%", alignItems: "start" }}
              onClick={() => setSelectedId(item.id)}
            >
              <Stack direction="row" justifyContent="space-between" gap={1}>
                <Chip size="small" label={typeLabel(item.operation_type)} />
                <Chip
                  size="small"
                  color={statusColors[item.status]}
                  label={statusLabel(item.status)}
                />
              </Stack>
              <Typography variant="h6" fontWeight={700} mt={1.5}>
                {item.title}
              </Typography>
              <Stack direction="row" gap={1} alignItems="center" mt={1}>
                <Schedule fontSize="small" color="action" />
                <Typography variant="body2">
                  {localDate(item.starts_at)}
                </Typography>
              </Stack>
              <Stack direction="row" gap={1} alignItems="center" mt={0.5}>
                <Groups fontSize="small" color="action" />
                <Typography variant="body2">
                  {item.assignees.map((x) => x.full_name).join(", ")}
                </Typography>
              </Stack>
              {item.location && (
                <Typography variant="body2" color="text.secondary" mt={1}>
                  {item.location}
                </Typography>
              )}
            </CardActionArea>
          </Card>
        ))}
      </Box>
      {operations.data?.length === 0 && (
        <Alert severity="info">{t("internalOperations.empty")}</Alert>
      )}

      <Dialog
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {row?.title ?? t("internalOperations.details")}
        </DialogTitle>
        <DialogContent dividers>
          {detail.isLoading ? (
            <Typography>{t("common.loading")}</Typography>
          ) : (
            row && (
              <Stack spacing={2}>
                <Stack direction="row" gap={1} flexWrap="wrap">
                  <Chip label={typeLabel(row.operation_type)} />
                  <Chip
                    color={statusColors[row.status]}
                    label={statusLabel(row.status)}
                  />
                </Stack>
                <Typography>
                  <b>{t("internalOperations.schedule")}:</b>{" "}
                  {localDate(row.starts_at)} — {localDate(row.ends_at)}
                </Typography>
                {row.location && (
                  <Typography>
                    <b>{t("internalOperations.location")}:</b> {row.location}
                  </Typography>
                )}
                {row.client_name && (
                  <Typography>
                    <b>{t("internalOperations.client")}:</b> {row.client_name}
                  </Typography>
                )}
                <Typography>
                  <b>{t("internalOperations.assignedEngineers")}:</b>{" "}
                  {row.assignees.map((x) => x.full_name).join(", ")}
                </Typography>
                {row.description && (
                  <Typography sx={{ whiteSpace: "pre-wrap" }}>
                    {row.description}
                  </Typography>
                )}
                {canTransition && (
                  <Stack direction="row" gap={1}>
                    {row.status === "SCHEDULED" && (
                      <Button
                        variant="outlined"
                        onClick={() => updateStatus.mutate("IN_PROGRESS")}
                      >
                        {t("internalOperations.startWork")}
                      </Button>
                    )}
                    {row.status !== "COMPLETED" &&
                      row.status !== "CANCELLED" && (
                        <Button
                          variant="contained"
                          color="success"
                          onClick={() => updateStatus.mutate("COMPLETED")}
                        >
                          {t("internalOperations.complete")}
                        </Button>
                      )}
                  </Stack>
                )}
                <Divider />
                <Typography variant="h6">
                  {t("internalOperations.summaries")}
                </Typography>
                {row.comments.map((comment) => (
                  <Paper key={comment.id} variant="outlined" sx={{ p: 1.5 }}>
                    <Stack direction="row" justifyContent="space-between">
                      <Chip
                        size="small"
                        label={t(
                          `internalOperations.commentTypes.${comment.comment_type}`,
                          {
                            defaultValue: comment.comment_type.replaceAll(
                              "_",
                              " ",
                            ),
                          },
                        )}
                      />
                      <Typography variant="caption">
                        {comment.author_name} · {localDate(comment.created_at)}
                      </Typography>
                    </Stack>
                    <Typography mt={1} sx={{ whiteSpace: "pre-wrap" }}>
                      {comment.body}
                    </Typography>
                  </Paper>
                ))}
                {canComment && (
                  <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                    <FormControl size="small" sx={{ minWidth: 170 }}>
                      <InputLabel>
                        {t("internalOperations.entryType")}
                      </InputLabel>
                      <Select
                        value={commentType}
                        label={t("internalOperations.entryType")}
                        onChange={(e) => setCommentType(e.target.value)}
                      >
                        {["COMMENT", "MOM", "MEETING_SUMMARY"].map((value) => (
                          <MenuItem key={value} value={value}>
                            {t(`internalOperations.commentTypes.${value}`)}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <TextField
                      fullWidth
                      size="small"
                      multiline
                      minRows={2}
                      label={t("internalOperations.commentField")}
                      value={commentBody}
                      onChange={(e) => setCommentBody(e.target.value)}
                    />
                    <Button
                      variant="contained"
                      disabled={
                        commentBody.trim().length < 2 || addComment.isPending
                      }
                      onClick={() => addComment.mutate()}
                    >
                      {t("common.actions.add", { defaultValue: "Add" })}
                    </Button>
                  </Stack>
                )}
                <Divider />
                <Typography variant="h6">
                  {t("internalOperations.documents")}
                </Typography>
                {row.documents.map((document) => (
                  <Stack
                    key={document.id}
                    direction="row"
                    alignItems="center"
                    gap={1}
                  >
                    <AttachFile color="action" />
                    <Box flexGrow={1}>
                      <Typography dir="ltr" sx={{ unicodeBidi: "isolate" }}>
                        {document.original_filename}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {document.uploaded_by_name} ·{" "}
                        {new Intl.NumberFormat(locale, {
                          maximumFractionDigits: 1,
                        }).format(document.size_bytes / 1024)}{" "}
                        KB
                      </Typography>
                    </Box>
                    {canDownload && (
                      <Button
                        startIcon={<Download />}
                        onClick={() => download(document)}
                      >
                        {t("internalOperations.download")}
                      </Button>
                    )}
                  </Stack>
                ))}
                {canUpload && (
                  <Button
                    component="label"
                    variant="outlined"
                    startIcon={<AttachFile />}
                    disabled={upload.isPending}
                  >
                    {t("internalOperations.attach")}
                    <input
                      hidden
                      type="file"
                      accept=".pdf,.docx,.xlsx,.txt,.csv,.png,.jpg,.jpeg"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) upload.mutate(file);
                        event.target.value = "";
                      }}
                    />
                  </Button>
                )}
              </Stack>
            )
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedId(null)}>
            {t("common.actions.close")}
          </Button>
        </DialogActions>
      </Dialog>

      {createDialog}
    </Stack>
  );
}
