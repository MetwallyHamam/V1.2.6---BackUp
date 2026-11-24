import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { CheckCircle, SettingsSuggest, WarningAmber } from "@mui/icons-material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import axios from "axios";
import { api } from "../api/client";
import { FeaturePolicyControl } from "./FeaturePolicyControl";
import { OutlookEmailSettings } from "./OutlookEmailSettings";
import { TicketNotificationSettings } from "./TicketNotificationSettings";
import { SupportAssistantSettings } from "./SupportAssistantSettings";
import { InboundIntegrationSettings } from "./InboundIntegrationSettings";

type Status = {
  database: { status: string; name: string; migration: string };
  scheduler: {
    enabled: boolean;
    interval_seconds: number;
    running: boolean;
    run_count: number;
    last_completed_at?: string;
    last_error?: string;
    last_duration_ms?: number;
    last_stage_metrics?: Record<string, Record<string, number>>;
    queue?: {
      pending: number;
      processing: number;
      completed: number;
      due: number;
      next_evaluation_at?: string;
    };
  };
  attachments: {
    storage_path: string;
    file_count: number;
    size_bytes: number;
    free_bytes: number;
  };
  backups: { count: number };
};
type Backup = { filename: string; size_bytes: number; created_at: string };
type StorageConfiguration = {
  attachment_storage_path: string;
  web_config_path: string;
  restart_required: boolean;
};
type SiteSettings = {
  server_timezone: string;
  daylight_saving_enabled: boolean;
  server_datetime?: string;
  default_theme: string;
  default_sound: boolean;
  default_assignee_user_id?: number;
  assign_available_only: boolean;
  assign_online_only: boolean;
  resolution_details_required_on_close: boolean;
  first_response_start_mode: "TICKET_CREATED" | "FIRST_DEDICATED_ASSIGNMENT";
  live_ticket_update_enabled: boolean;
  live_ticket_update_closed_poll_seconds: number;
  satisfaction_manual_enabled: boolean;
  satisfaction_whatsapp_enabled: boolean;
  satisfaction_email_enabled: boolean;
  satisfaction_token_expiry_days: number;
  satisfaction_whatsapp_template: string;
  satisfaction_email_subject: string;
  satisfaction_email_body: string;
  sla_warning_enabled: boolean;
  sla_response_warning_minutes: number[];
  sla_resolution_warning_minutes: number[];
  sla_warning_recipient_emails: string[];
  sla_warning_support_team_ids: number[];
};
type SiteSettingsCategory = {
  category: string;
  version: number;
  values: SiteSettings;
};
type UserOption = { id: number; full_name: string };
type SupportTeamOption = {
  id: number;
  name: string;
  is_active: boolean;
  member_user_ids: number[];
};
type SmtpConfiguration = {
  enabled: boolean;
  host: string;
  port: number;
  username: string;
  password_configured: boolean;
  from_address: string;
  from_name: string;
  use_tls: boolean;
};
type EmailDeliveryStatus = {
  smtp_enabled: boolean;
  frontend_base_url: string;
  allowed_domains_configured: boolean;
  outbox: Record<string, number>;
  deliveries: Record<string, number>;
  recent: Array<{
    recipient: string;
    status: string;
    attempt_count: number;
    last_error?: string;
    requested_at: string;
    sent_at?: string;
  }>;
};
type EmailProcessResult = {
  sent: number;
  retried: number;
  dead: number;
  skipped: number;
};
type LocalAiConfiguration = {
  mode: "LOCAL" | "REMOTE";
  local_folder: string;
  remote_base_url: string;
  intake_instructions: string;
  provider: "OLLAMA" | "OPENAI";
  model: string;
  api_key_configured: boolean;
  base_url: string;
  source: "SITE_SETTING" | "ENVIRONMENT";
};
type ServerFolders = {
  path: string | null;
  parent: string | null;
  directories: string[];
  is_local_ai_folder: boolean;
};

const smtpSaveError = (
  error: unknown,
  restartMessage: string,
  fallback: string,
) => {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.error?.message;
    if (message) return message;
    if (!error.response) return restartMessage;
  }
  return fallback;
};

const formatBytes = (value: number, locale: string) =>
  `${new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value / 1024 / 1024)} MB`;

const categories = [
  "general",
  "sla-contracts",
  "support-assistant",
  "ticket-notifications",
  "ticket-forms",
  "third-party-integrations",
  "attachments-storage",
  "security-access",
  "advanced",
] as const;

export function SystemOperationsPage() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab") ?? "general";
  const tab = categories.some((key) => key === requestedTab)
    ? requestedTab
    : "general";
  const [generalDirty, setGeneralDirty] = useState(false);
  const [integrationTab, setIntegrationTab] = useState<
    "outlook" | "smtp" | "whatsapp" | "local-ai"
  >("outlook");
  const [localAiMode, setLocalAiMode] = useState<"LOCAL" | "REMOTE">("LOCAL");
  const [aiProvider, setAiProvider] = useState<"OLLAMA" | "OPENAI">("OLLAMA");
  const [aiModel, setAiModel] = useState("qwen2.5:3b");
  const [localAiFolder, setLocalAiFolder] = useState("");
  const [browsePath, setBrowsePath] = useState<string | null>(null);
  const [browsingFolders, setBrowsingFolders] = useState(false);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (generalDirty) event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [generalDirty]);
  const status = useQuery({
    queryKey: ["system-status"],
    queryFn: async () => (await api.get<Status>("/system/status")).data,
    refetchInterval: 30_000,
  });
  const backups = useQuery({
    queryKey: ["system-backups"],
    queryFn: async () => (await api.get<Backup[]>("/system/backups")).data,
  });
  const storageConfiguration = useQuery({
    queryKey: ["storage-configuration"],
    queryFn: async () =>
      (await api.get<StorageConfiguration>("/system/configuration/storage"))
        .data,
  });
  const siteSettings = useQuery({
    queryKey: ["site-settings", "general"],
    queryFn: async () =>
      (
        await api.get<SiteSettingsCategory>(
          "/system/site-settings/categories/general",
        )
      ).data,
  });
  const smtp = useQuery({
    queryKey: ["smtp-configuration"],
    queryFn: async () =>
      (await api.get<SmtpConfiguration>("/system/configuration/smtp")).data,
  });
  const localAi = useQuery({
    queryKey: ["local-ai-configuration"],
    queryFn: async () =>
      (await api.get<LocalAiConfiguration>("/system/configuration/local-ai"))
        .data,
  });
  useEffect(() => {
    if (localAi.data) {
      setLocalAiMode(localAi.data.mode);
      setLocalAiFolder(localAi.data.local_folder);
      setAiProvider(localAi.data.provider);
      setAiModel(localAi.data.model);
    }
  }, [localAi.data]);
  const serverFolders = useQuery({
    queryKey: ["local-ai-folders", browsePath],
    queryFn: async () =>
      (
        await api.get<ServerFolders>("/system/configuration/local-ai/folders", {
          params: { path: browsePath || undefined },
        })
      ).data,
    enabled: browsingFolders,
  });
  const emailStatus = useQuery({
    queryKey: ["email-delivery-status"],
    queryFn: async () =>
      (
        await api.get<EmailDeliveryStatus>(
          "/system/configuration/email-delivery-status",
        )
      ).data,
    enabled: tab === "third-party-integrations" && integrationTab === "smtp",
    refetchInterval: 30_000,
  });
  const userOptions = useQuery({
    queryKey: ["users", "site-settings"],
    queryFn: async () => (await api.get<UserOption[]>("/users")).data,
  });
  const supportTeams = useQuery({
    queryKey: ["support-teams", "site-settings"],
    queryFn: async () =>
      (await api.get<SupportTeamOption[]>("/support-teams")).data,
  });
  const saveSiteSettings = useMutation({
    mutationFn: async (data: SiteSettings & { expected_version: number }) =>
      api.put("/system/site-settings/categories/general", data),
    onSuccess: async () => {
      setGeneralDirty(false);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["site-settings", "general"],
        }),
        queryClient.invalidateQueries({ queryKey: ["server-clock"] }),
      ]);
    },
  });
  const saveSmtp = useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      api.put("/system/configuration/smtp", data),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["smtp-configuration"] }),
  });
  const testSmtp = useMutation({
    mutationFn: async () => api.post("/system/configuration/smtp/test"),
  });
  const processEmailQueue = useMutation({
    mutationFn: async () =>
      (await api.post<EmailProcessResult>("/notifications/email/process")).data,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["email-delivery-status"] }),
        queryClient.invalidateQueries({ queryKey: ["system-status"] }),
        queryClient.invalidateQueries({ queryKey: ["contract-notification-deliveries"] }),
      ]);
    },
  });
  const saveLocalAi = useMutation({
    mutationFn: async (data: {
      mode: "LOCAL" | "REMOTE";
      local_folder?: string;
      remote_base_url?: string;
      intake_instructions: string;
      provider: "OLLAMA" | "OPENAI";
      model: string;
      api_key?: string;
    }) => api.put("/system/configuration/local-ai", data),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["local-ai-configuration"] }),
  });
  const testLocalAi = useMutation({
    mutationFn: async () => api.post("/system/configuration/local-ai/test"),
  });
  const saveStorage = useMutation({
    mutationFn: async (attachment_storage_path: string) =>
      (
        await api.put<StorageConfiguration>("/system/configuration/storage", {
          attachment_storage_path,
        })
      ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["storage-configuration"],
      });
      await queryClient.invalidateQueries({ queryKey: ["system-status"] });
    },
  });
  function submitStorage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(
      new FormData(event.currentTarget).get("attachment_storage_path") ?? "",
    ).trim();
    if (value) saveStorage.mutate(value);
  }
  function submitSiteSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (!siteSettings.data) return;
    saveSiteSettings.mutate({
      expected_version: siteSettings.data.version,
      server_timezone: String(data.get("server_timezone")),
      daylight_saving_enabled: data.get("daylight_saving_enabled") === "on",
      default_theme: String(data.get("default_theme")),
      default_sound: data.get("default_sound") === "on",
      default_assignee_user_id: data.get("default_assignee_user_id")
        ? Number(data.get("default_assignee_user_id"))
        : undefined,
      assign_available_only: data.get("assign_available_only") === "on",
      assign_online_only: data.get("assign_online_only") === "on",
      resolution_details_required_on_close:
        data.get("resolution_details_required_on_close") === "on",
      first_response_start_mode:
        siteSettings.data.values.first_response_start_mode,
      live_ticket_update_enabled:
        data.get("live_ticket_update_enabled") === "on",
      live_ticket_update_closed_poll_seconds: Number(
        data.get("live_ticket_update_closed_poll_seconds") ||
          siteSettings.data.values.live_ticket_update_closed_poll_seconds,
      ),
      satisfaction_manual_enabled:
        data.get("satisfaction_manual_enabled") === "on",
      satisfaction_whatsapp_enabled:
        data.get("satisfaction_whatsapp_enabled") === "on",
      satisfaction_email_enabled:
        data.get("satisfaction_email_enabled") === "on",
      satisfaction_token_expiry_days: Number(
        data.get("satisfaction_token_expiry_days"),
      ),
      satisfaction_whatsapp_template: String(
        data.get("satisfaction_whatsapp_template"),
      ),
      satisfaction_email_subject: String(
        data.get("satisfaction_email_subject"),
      ),
      satisfaction_email_body: String(data.get("satisfaction_email_body")),
      sla_warning_enabled: siteSettings.data.values.sla_warning_enabled,
      sla_response_warning_minutes:
        siteSettings.data.values.sla_response_warning_minutes,
      sla_resolution_warning_minutes:
        siteSettings.data.values.sla_resolution_warning_minutes,
      sla_warning_recipient_emails:
        siteSettings.data.values.sla_warning_recipient_emails,
      sla_warning_support_team_ids:
        siteSettings.data.values.sla_warning_support_team_ids,
    });
  }
  function submitSlaSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!siteSettings.data) return;
    const data = new FormData(event.currentTarget);
    const numbers = (name: string) =>
      String(data.get(name) ?? "")
        .split(",")
        .map((value) => Number(value.trim()))
        .filter((value) => Number.isInteger(value) && value > 0);
    const emails = String(data.get("sla_warning_recipient_emails") ?? "")
      .split(/[;,]/)
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);
    saveSiteSettings.mutate({
      ...siteSettings.data.values,
      expected_version: siteSettings.data.version,
      first_response_start_mode: String(
        data.get("first_response_start_mode"),
      ) as SiteSettings["first_response_start_mode"],
      sla_warning_enabled: data.get("sla_warning_enabled") === "on",
      sla_response_warning_minutes: numbers("sla_response_warning_minutes"),
      sla_resolution_warning_minutes: numbers("sla_resolution_warning_minutes"),
      sla_warning_recipient_emails: emails,
      sla_warning_support_team_ids: data
        .getAll("sla_warning_support_team_ids")
        .map(Number)
        .filter((value) => Number.isInteger(value) && value > 0),
    });
  }
  function submitSmtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    saveSmtp.mutate({
      enabled: data.get("enabled") === "on",
      host: data.get("host"),
      port: Number(data.get("port")),
      username: data.get("username") || null,
      password: data.get("password") || null,
      from_address: data.get("from_address"),
      from_name: data.get("from_name"),
      use_tls: data.get("use_tls") === "on",
    });
  }
  function submitLocalAi(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    saveLocalAi.mutate({
      mode: localAiMode,
      local_folder: localAiMode === "LOCAL" ? localAiFolder : undefined,
      remote_base_url:
        localAiMode === "REMOTE"
          ? String(data.get("remote_base_url") ?? "").trim()
          : undefined,
      intake_instructions: String(data.get("intake_instructions") ?? "").trim(),
      provider: aiProvider,
      model: aiModel,
      api_key: String(data.get("api_key") ?? "").trim() || undefined,
    });
  }
  const createBackup = useMutation({
    mutationFn: async () => (await api.post<Backup>("/system/backups")).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["system-backups"] });
      await queryClient.invalidateQueries({ queryKey: ["system-status"] });
    },
  });
  const changeTab = (next: string) => {
    if (generalDirty && !window.confirm(t("systemOperations.discard"))) return;
    setGeneralDirty(false);
    setSearchParams({ tab: next });
  };
  if (status.isLoading)
    return (
      <Paper variant="outlined" sx={{ p: 5, textAlign: "center" }}>
        <CircularProgress size={32} />
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          {t("systemOperations.loading")}
        </Typography>
      </Paper>
    );
  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={2}
          alignItems={{ md: "center" }}
          sx={{ p: { xs: 2, md: 3 } }}
        >
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: 2.5,
              display: "grid",
              placeItems: "center",
              bgcolor: "primary.main",
              color: "primary.contrastText",
              flexShrink: 0,
            }}
          >
            <SettingsSuggest />
          </Box>
          <Box flex={1} minWidth={0}>
            <Typography variant="h4" fontWeight={850}>
              {t("systemOperations.title")}
            </Typography>
            <Typography color="text.secondary">
              {t("systemOperations.subtitle")}
            </Typography>
          </Box>
          <Stack direction="row" gap={1} flexWrap="wrap">
            <Chip
              icon={status.isError ? <WarningAmber /> : <CheckCircle />}
              color={status.isError ? "error" : "success"}
              variant="outlined"
              label={
                status.isError
                  ? t("systemOperations.statusUnavailable")
                  : t("systemOperations.systemOnline")
              }
            />
            {generalDirty && (
              <Chip
                color="warning"
                label={t("systemOperations.unsavedChanges")}
              />
            )}
          </Stack>
        </Stack>
        <Box sx={{ borderTop: 1, borderColor: "divider", bgcolor: "action.hover" }}>
          <Tabs
            value={tab}
            onChange={(_, value: string) => changeTab(value)}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            aria-label={t("systemOperations.categoriesLabel")}
            sx={{
              px: { xs: 0.5, md: 1.5 },
              "& .MuiTab-root": {
                minHeight: 52,
                textTransform: "none",
                fontWeight: 750,
              },
            }}
          >
            {categories.map((key) => (
              <Tab
                key={key}
                value={key}
                label={t(`systemOperations.categories.${key}`)}
              />
            ))}
          </Tabs>
        </Box>
      </Paper>
      {status.isError && (
        <Alert severity="error">{t("systemOperations.statusFailed")}</Alert>
      )}
      {tab === "support-assistant" && <SupportAssistantSettings />}
      {tab === "sla-contracts" && siteSettings.data && (
        <Paper
          component="form"
          key={`sla-${siteSettings.data.version}`}
          onSubmit={submitSlaSettings}
          sx={{ p: 3 }}
        >
          <Typography variant="h5">SLA operational settings</Typography>
          <Typography color="text.secondary" mb={2}>
            These are the existing system-wide timer and warning settings.
            Contract coverage and SLA targets remain in Contract Management.
          </Typography>
          {saveSiteSettings.isSuccess && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {t("systemOperations.general.saved")}
            </Alert>
          )}
          {saveSiteSettings.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {t("systemOperations.general.failed")}
            </Alert>
          )}
          <Stack spacing={1.5}>
            <TextField
              select
              required
              name="first_response_start_mode"
              label={t("firstResponseSettings.title")}
              defaultValue={siteSettings.data.values.first_response_start_mode}
              helperText={t("firstResponseSettings.help")}
            >
              <MenuItem value="TICKET_CREATED">
                {t("firstResponseSettings.created")}
              </MenuItem>
              <MenuItem value="FIRST_DEDICATED_ASSIGNMENT">
                {t("firstResponseSettings.assigned")}
              </MenuItem>
            </TextField>
            <FormControlLabel
              control={
                <Switch
                  name="sla_warning_enabled"
                  defaultChecked={siteSettings.data.values.sla_warning_enabled}
                />
              }
              label={t("systemOperations.general.slaEnabled")}
            />
            <Stack direction={{ xs: "column", md: "row" }} gap={1}>
              <TextField
                name="sla_response_warning_minutes"
                label={t("systemOperations.general.responseMinutes")}
                defaultValue={siteSettings.data.values.sla_response_warning_minutes.join(
                  ", ",
                )}
                helperText={t("systemOperations.general.responseHelp")}
                fullWidth
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="sla_resolution_warning_minutes"
                label={t("systemOperations.general.resolutionMinutes")}
                defaultValue={siteSettings.data.values.sla_resolution_warning_minutes.join(
                  ", ",
                )}
                helperText={t("systemOperations.general.resolutionHelp")}
                fullWidth
                inputProps={{ dir: "ltr" }}
              />
            </Stack>
            <TextField
              name="sla_warning_recipient_emails"
              label={t("systemOperations.general.emails")}
              defaultValue={siteSettings.data.values.sla_warning_recipient_emails.join(
                ", ",
              )}
              helperText={t("systemOperations.general.emailsHelp")}
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              select
              name="sla_warning_support_team_ids"
              label={t("systemOperations.general.teams")}
              defaultValue={siteSettings.data.values.sla_warning_support_team_ids.map(
                String,
              )}
              SelectProps={{ multiple: true }}
              helperText={t("systemOperations.general.teamsHelp")}
            >
              {supportTeams.data
                ?.filter((team) => team.is_active)
                .map((team) => (
                  <MenuItem key={team.id} value={String(team.id)}>
                    {team.name} ·{" "}
                    {t("systemOperations.general.members", {
                      count: team.member_user_ids.length.toLocaleString(locale),
                    })}
                  </MenuItem>
                ))}
            </TextField>
            <Alert severity="info">
              Validation level, grace days and approval groups are configured
              per contract or contract template. SLA calendars and targets are
              configured in Contract Management.
            </Alert>
            <Stack alignItems="flex-end">
              <Button
                type="submit"
                variant="contained"
                disabled={saveSiteSettings.isPending}
              >
                {t("systemOperations.general.save")}
              </Button>
            </Stack>
          </Stack>
        </Paper>
      )}
      {tab === "advanced" && status.data && (
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6">
              {t("systemOperations.database")}
            </Typography>
            <Typography>{status.data.database.name}</Typography>
            <Typography color="text.secondary">
              {t("systemOperations.migration", {
                migration: status.data.database.migration,
                status: status.data.database.status,
              })}
            </Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6">
              {t("systemOperations.scheduler")}
            </Typography>
            <Typography>
              {status.data.scheduler.enabled
                ? t("systemOperations.everySeconds", {
                    count:
                      status.data.scheduler.interval_seconds.toLocaleString(
                        locale,
                      ),
                  })
                : t("systemOperations.disabled")}
            </Typography>
            <Typography color="text.secondary">
              {t("systemOperations.runs", {
                count: status.data.scheduler.run_count.toLocaleString(locale),
                running: status.data.scheduler.running
                  ? t("systemOperations.runningNow")
                  : "",
              })}
            </Typography>
            {status.data.scheduler.last_duration_ms != null && (
              <Typography variant="body2" color="text.secondary">
                {t("systemOperations.schedulerDuration", {
                  duration: Intl.NumberFormat(locale).format(
                    status.data.scheduler.last_duration_ms,
                  ),
                })}
              </Typography>
            )}
            {Object.entries(status.data.scheduler.last_stage_metrics ?? {}).map(
              ([stage, metrics]) => (
                <Typography key={stage} variant="caption" display="block">
                  {t("systemOperations.schedulerStage", {
                    stage: stage.replaceAll("_", " "),
                    duration: Intl.NumberFormat(locale).format(
                      metrics.duration_ms ?? 0,
                    ),
                  })}
                </Typography>
              ),
            )}
            {status.data.scheduler.queue && (
              <Table size="small" sx={{ mt: 1 }} aria-label="SLA escalation work queue">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("systemOperations.queueState", { defaultValue: "Queue state" })}</TableCell>
                    <TableCell align="right">{t("systemOperations.queueCount", { defaultValue: "Count" })}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(["due", "pending", "processing", "completed"] as const).map((key) => (
                    <TableRow key={key}>
                      <TableCell sx={{ textTransform: "capitalize" }}>{key}</TableCell>
                      <TableCell align="right">{status.data!.scheduler.queue![key].toLocaleString(locale)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {status.data.scheduler.queue?.next_evaluation_at && (
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                {t("systemOperations.nextEvaluation", { defaultValue: "Next SLA evaluation" })}: {new Date(status.data.scheduler.queue.next_evaluation_at).toLocaleString(locale)}
              </Typography>
            )}
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6">
              {t("systemOperations.attachments")}
            </Typography>
            <Typography>
              {t("systemOperations.filesSize", {
                count:
                  status.data.attachments.file_count.toLocaleString(locale),
                size: formatBytes(status.data.attachments.size_bytes, locale),
              })}
            </Typography>
            <Typography color="text.secondary">
              {t("systemOperations.free", {
                size: formatBytes(status.data.attachments.free_bytes, locale),
              })}
            </Typography>
            <Typography
              variant="caption"
              display="block"
              sx={{ mt: 1, wordBreak: "break-all", direction: "ltr" }}
            >
              {t("systemOperations.storageRoot", {
                path: status.data.attachments.storage_path,
              })}
            </Typography>
          </Paper>
        </Stack>
      )}
      {tab === "general" && siteSettings.data && (
        <Paper
          component="form"
          key={JSON.stringify(siteSettings.data)}
          onChange={() => setGeneralDirty(true)}
          onSubmit={submitSiteSettings}
          sx={{ p: 3 }}
        >
          <Typography variant="h5">
            {t("systemOperations.general.title")}
          </Typography>
          <Typography color="text.secondary" mb={2}>
            {t("systemOperations.general.subtitle", {
              version: siteSettings.data.version.toLocaleString(locale),
            })}
          </Typography>
          {saveSiteSettings.isSuccess && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {t("systemOperations.general.saved")}
            </Alert>
          )}
          {saveSiteSettings.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {t("systemOperations.general.failed")}
            </Alert>
          )}
          <Stack spacing={1.5}>
            <Typography variant="h6">Server date and time</Typography>
            <TextField
              required
              name="server_timezone"
              label="Server timezone"
              defaultValue={siteSettings.data.values.server_timezone}
              helperText="IANA timezone used for all database timestamps, dashboards, filters and UI dates."
              inputProps={{ dir: "ltr" }}
            />
            <FormControlLabel
              control={
                <Switch
                  name="daylight_saving_enabled"
                  defaultChecked={
                    siteSettings.data.values.daylight_saving_enabled
                  }
                />
              }
              label="Apply daylight-saving changes"
            />
            {siteSettings.data.values.server_datetime && (
              <Alert severity="info">
                Current server time:{" "}
                {new Date(
                  siteSettings.data.values.server_datetime,
                ).toLocaleString(locale, {
                  timeZone: siteSettings.data.values.server_timezone,
                })}
              </Alert>
            )}
            <TextField
              select
              name="default_theme"
              label={t("systemOperations.general.theme")}
              defaultValue={siteSettings.data.values.default_theme}
            >
              {["SYSTEM", "LIGHT", "DARK"].map((theme) => (
                <MenuItem key={theme} value={theme}>
                  {t(`systemOperations.general.themes.${theme}`)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="default_assignee_user_id"
              label={t("systemOperations.general.assignee")}
              defaultValue={
                siteSettings.data.values.default_assignee_user_id ?? ""
              }
            >
              <MenuItem value="">
                {t("systemOperations.general.fallback")}
              </MenuItem>
              {userOptions.data?.map((user) => (
                <MenuItem key={user.id} value={user.id}>
                  {user.full_name}
                </MenuItem>
              ))}
            </TextField>
            <FormControlLabel
              control={
                <Switch
                  name="default_sound"
                  defaultChecked={siteSettings.data.values.default_sound}
                />
              }
              label={t("systemOperations.general.sound")}
            />
            <FormControlLabel
              control={
                <Switch
                  name="assign_available_only"
                  defaultChecked={
                    siteSettings.data.values.assign_available_only
                  }
                />
              }
              label={t("systemOperations.general.available")}
            />
            <FormControlLabel
              control={
                <Switch
                  name="assign_online_only"
                  defaultChecked={siteSettings.data.values.assign_online_only}
                />
              }
              label={t("systemOperations.general.online")}
            />
            <Typography variant="h6" sx={{ pt: 1 }}>
              Ticket resolution workflow
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  name="resolution_details_required_on_close"
                  defaultChecked={
                    siteSettings.data.values.resolution_details_required_on_close
                  }
                />
              }
              label="Require resolution, root cause and service provided only when closing"
            />
            <Alert severity="info">
              When enabled, Resolve changes only the status. Resolved tickets with missing
              closure details remain in Support Now until the engineer completes the details
              and closes the ticket. This rule also applies to board and grid actions.
            </Alert>
            <FormControlLabel
              control={
                <Switch
                  name="live_ticket_update_enabled"
                  defaultChecked={
                    siteSettings.data.values.live_ticket_update_enabled
                  }
                />
              }
              label={t("systemOperations.general.liveLinks")}
            />
            <Typography variant="h6" sx={{ pt: 1 }}>
              {t("systemOperations.general.satisfactionTitle")}
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  name="satisfaction_manual_enabled"
                  defaultChecked={
                    siteSettings.data.values.satisfaction_manual_enabled
                  }
                />
              }
              label={t("systemOperations.general.manual")}
            />
            <FormControlLabel
              control={
                <Switch
                  name="satisfaction_whatsapp_enabled"
                  defaultChecked={
                    siteSettings.data.values.satisfaction_whatsapp_enabled
                  }
                />
              }
              label={t("systemOperations.general.whatsapp")}
            />
            <FormControlLabel
              control={
                <Switch
                  name="satisfaction_email_enabled"
                  defaultChecked={
                    siteSettings.data.values.satisfaction_email_enabled
                  }
                />
              }
              label={t("systemOperations.general.email")}
            />
            <TextField
              name="satisfaction_token_expiry_days"
              type="number"
              label={t("systemOperations.general.expiry")}
              defaultValue={
                siteSettings.data.values.satisfaction_token_expiry_days
              }
              inputProps={{ min: 1, max: 365 }}
            />
            <TextField
              name="satisfaction_whatsapp_template"
              label={t("systemOperations.general.whatsappTemplate")}
              defaultValue={
                siteSettings.data.values.satisfaction_whatsapp_template
              }
              multiline
              rows={4}
              helperText={t("systemOperations.general.templateHelp")}
            />
            <TextField
              name="satisfaction_email_subject"
              label={t("systemOperations.general.emailSubject")}
              defaultValue={siteSettings.data.values.satisfaction_email_subject}
            />
            <TextField
              name="satisfaction_email_body"
              label={t("systemOperations.general.emailBody")}
              defaultValue={siteSettings.data.values.satisfaction_email_body}
              multiline
              rows={5}
              helperText={t("systemOperations.general.templateHelp")}
            />
            <Stack
              direction="row"
              gap={1}
              justifyContent="flex-end"
              sx={{
                position: "sticky",
                bottom: 0,
                zIndex: 2,
                py: 1.5,
                px: 1.5,
                mx: -1.5,
                bgcolor: "background.paper",
                borderTop: 1,
                borderColor: "divider",
              }}
            >
              <Button
                type="submit"
                variant="contained"
                disabled={!generalDirty || saveSiteSettings.isPending}
              >
                {t("systemOperations.general.save")}
              </Button>
              <Button
                type="button"
                disabled={!generalDirty}
                onClick={() => {
                  setGeneralDirty(false);
                  void queryClient.invalidateQueries({
                    queryKey: ["site-settings", "general"],
                  });
                }}
              >
                {t("systemOperations.general.cancel")}
              </Button>
            </Stack>
          </Stack>
        </Paper>
      )}
      {tab === "ticket-notifications" && <TicketNotificationSettings />}
      {tab === "ticket-forms" && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            {t("systemOperations.ticketForms.title")}
          </Typography>
          <Typography color="text.secondary" mb={2}>
            {t("systemOperations.ticketForms.help")}
          </Typography>
          <Button
            component={RouterLink}
            to="/ticket-form-settings"
            variant="contained"
          >
            {t("systemOperations.ticketForms.open")}
          </Button>
        </Paper>
      )}
      {tab === "security-access" && (
        <FeaturePolicyControl
          initialFeatureKey={searchParams.get("feature") ?? undefined}
        />
      )}
      {tab === "third-party-integrations" && (
        <Paper sx={{ px: 2, pt: 1 }}>
          <Typography variant="h5" sx={{ pt: 1 }}>
            {t("systemOperations.thirdParty.title")}
          </Typography>
          <Typography color="text.secondary">
            {t("systemOperations.thirdParty.help")}
          </Typography>
          <Tabs
            value={integrationTab}
            onChange={(_, value) => setIntegrationTab(value)}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab
              value="outlook"
              label={t("systemOperations.thirdParty.outlook")}
            />
            <Tab value="smtp" label={t("systemOperations.thirdParty.smtp")} />
            <Tab
              value="whatsapp"
              label={t("systemOperations.thirdParty.whatsapp")}
            />
            <Tab value="local-ai" label="AI service" />
          </Tabs>
        </Paper>
      )}
      {tab === "third-party-integrations" && integrationTab === "outlook" && (
        <OutlookEmailSettings />
      )}
      {tab === "third-party-integrations" &&
        integrationTab === "smtp" &&
        smtp.data && (
          <Paper component="form" onSubmit={submitSmtp} sx={{ p: 3 }}>
            <Typography variant="h5">
              {t("systemOperations.smtp.title")}
            </Typography>
            <Typography color="text.secondary" mb={2}>
              {t("systemOperations.smtp.help")}
            </Typography>
            {!smtp.data.enabled && (
              <Alert severity="error" sx={{ mb: 1 }}>
                {t("systemOperations.smtp.disabled")}
              </Alert>
            )}
            {saveSmtp.isSuccess && (
              <Alert severity="warning">
                {t("systemOperations.smtp.saved")}
              </Alert>
            )}
            {saveSmtp.isError && (
              <Alert severity="error">
                {smtpSaveError(
                  saveSmtp.error,
                  t("systemOperations.smtp.restartError"),
                  t("systemOperations.smtp.saveError"),
                )}
              </Alert>
            )}
            {testSmtp.isSuccess && (
              <Alert severity="success">
                {t("systemOperations.smtp.testSent")}
              </Alert>
            )}
            {testSmtp.isError && (
              <Alert severity="error">
                {t("systemOperations.smtp.testFailed")}
              </Alert>
            )}
            <Stack spacing={1.5} mt={2}>
              <FormControlLabel
                control={
                  <Switch name="enabled" defaultChecked={smtp.data.enabled} />
                }
                label={t("systemOperations.smtp.enable")}
              />
              <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                <TextField
                  required
                  name="host"
                  label={t("systemOperations.smtp.server")}
                  defaultValue={smtp.data.host}
                  fullWidth
                  inputProps={{ dir: "ltr" }}
                />
                <TextField
                  required
                  name="port"
                  type="number"
                  label={t("systemOperations.smtp.port")}
                  defaultValue={smtp.data.port}
                />
              </Stack>
              <TextField
                name="username"
                label={t("systemOperations.smtp.username")}
                defaultValue={smtp.data.username}
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="password"
                type="password"
                label={t(
                  smtp.data.password_configured
                    ? "systemOperations.smtp.newPassword"
                    : "systemOperations.smtp.password",
                )}
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                required
                name="from_name"
                label={t("systemOperations.smtp.sender")}
                defaultValue={smtp.data.from_name}
                helperText={t("systemOperations.smtp.senderHelp")}
              />
              <TextField
                required
                name="from_address"
                label={t("systemOperations.smtp.from")}
                defaultValue={smtp.data.from_address}
                inputProps={{ dir: "ltr" }}
              />
              <FormControlLabel
                control={
                  <Switch name="use_tls" defaultChecked={smtp.data.use_tls} />
                }
                label={t("systemOperations.smtp.tls")}
              />
              <Stack direction="row" gap={1}>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={saveSmtp.isPending}
                >
                  {t("systemOperations.smtp.save")}
                </Button>
                <Button
                  variant="outlined"
                  disabled={!smtp.data.enabled || testSmtp.isPending}
                  onClick={() => testSmtp.mutate()}
                >
                  {t("systemOperations.smtp.test")}
                </Button>
                <Button
                  variant="outlined"
                  disabled={!smtp.data.enabled || processEmailQueue.isPending}
                  onClick={() => processEmailQueue.mutate()}
                >
                  {processEmailQueue.isPending
                    ? "Processing…"
                    : "Process email queue now"}
                </Button>
              </Stack>
              {processEmailQueue.isSuccess && (
                <Alert severity={processEmailQueue.data.dead ? "warning" : "success"}>
                  Queue processed: {processEmailQueue.data.sent} sent, {processEmailQueue.data.retried} scheduled for retry, {processEmailQueue.data.dead} failed, {processEmailQueue.data.skipped} skipped.
                </Alert>
              )}
              {processEmailQueue.isError && (
                <Alert severity="error">
                  The email queue could not be processed. Review the server error log.
                </Alert>
              )}
            </Stack>
            {emailStatus.data && (
              <Stack mt={3} spacing={1}>
                <Typography variant="h6">
                  {t("systemOperations.smtp.diagnostics")}
                </Typography>
                <Typography color="text.secondary">
                  {t("systemOperations.smtp.resetUrl", {
                    url: emailStatus.data.frontend_base_url,
                    restriction: t(
                      emailStatus.data.allowed_domains_configured
                        ? "systemOperations.smtp.configured"
                        : "systemOperations.smtp.notConfigured",
                    ),
                  })}
                </Typography>
                <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                  <Alert
                    severity={
                      (emailStatus.data.outbox.PENDING ?? 0) +
                        (emailStatus.data.outbox.RETRY ?? 0) >
                      0
                        ? "warning"
                        : "success"
                    }
                  >
                    {t("systemOperations.smtp.queued", {
                      count: (
                        (emailStatus.data.outbox.PENDING ?? 0) +
                        (emailStatus.data.outbox.RETRY ?? 0)
                      ).toLocaleString(locale),
                    })}
                  </Alert>
                  <Alert severity="success">
                    {t("systemOperations.smtp.sent", {
                      count: (
                        emailStatus.data.deliveries.SENT ?? 0
                      ).toLocaleString(locale),
                    })}
                  </Alert>
                  <Alert
                    severity={
                      (emailStatus.data.deliveries.DEAD ?? 0) > 0
                        ? "error"
                        : "info"
                    }
                  >
                    {t("systemOperations.smtp.failed", {
                      count: (
                        emailStatus.data.deliveries.DEAD ?? 0
                      ).toLocaleString(locale),
                    })}
                  </Alert>
                </Stack>
                {emailStatus.data.recent.length > 0 && (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>
                          {t("systemOperations.smtp.recipient")}
                        </TableCell>
                        <TableCell>
                          {t("systemOperations.smtp.status")}
                        </TableCell>
                        <TableCell>
                          {t("systemOperations.smtp.requested")}
                        </TableCell>
                        <TableCell>
                          {t("systemOperations.smtp.diagnostic")}
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {emailStatus.data.recent.map((row, index) => (
                        <TableRow
                          key={`${row.recipient}-${row.requested_at}-${index}`}
                        >
                          <TableCell sx={{ direction: "ltr" }}>
                            {row.recipient}
                          </TableCell>
                          <TableCell>
                            {row.status} (
                            {row.attempt_count.toLocaleString(locale)})
                          </TableCell>
                          <TableCell>
                            {new Date(row.requested_at).toLocaleString(locale)}
                          </TableCell>
                          <TableCell>{row.last_error || "—"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </Stack>
            )}
          </Paper>
        )}
      {tab === "third-party-integrations" &&
        integrationTab === "local-ai" &&
        localAi.data && (
          <Paper component="form" onSubmit={submitLocalAi} sx={{ p: 3 }}>
            <Typography variant="h5">AI service</Typography>
            <Typography color="text.secondary" mb={2}>
              Switch between local Ollama and the OpenAI API while keeping the
              same Support Hub workflow.
            </Typography>
            {saveLocalAi.isSuccess && (
              <Alert severity="warning" sx={{ mb: 1 }}>
                Configuration saved. Restart the AI gateway to apply provider,
                model, or API-key changes.
              </Alert>
            )}
            {saveLocalAi.isError && (
              <Alert severity="error" sx={{ mb: 1 }}>
                The AI configuration could not be saved. Verify the folder,
                model, credentials, or remote URL.
              </Alert>
            )}
            {testLocalAi.isSuccess && (
              <Alert severity="success" sx={{ mb: 1 }}>
                Connection successful.
              </Alert>
            )}
            {testLocalAi.isError && (
              <Alert severity="error" sx={{ mb: 1 }}>
                Connection failed. Verify the gateway, provider, credentials,
                and firewall.
              </Alert>
            )}
            <Stack spacing={1.5}>
              <TextField
                select
                label="Deployment mode"
                value={localAiMode}
                onChange={(event) =>
                  setLocalAiMode(event.target.value as "LOCAL" | "REMOTE")
                }
              >
                <MenuItem value="LOCAL">Local gateway</MenuItem>
                <MenuItem value="REMOTE">Remote gateway</MenuItem>
              </TextField>
              {localAiMode === "LOCAL" ? (
                <>
                  <TextField
                    required
                    label="AI gateway physical folder"
                    value={localAiFolder}
                    onChange={(event) => setLocalAiFolder(event.target.value)}
                    helperText="Server folder containing app\\main.py, run.bat and .env, for example E:\\SupportHub\\Release\\local-ai"
                    inputProps={{ dir: "ltr" }}
                  />
                  <Button
                    type="button"
                    variant="outlined"
                    onClick={() => {
                      setBrowsePath(localAiFolder || null);
                      setBrowsingFolders(true);
                    }}
                  >
                    Browse server folders
                  </Button>
                  {browsingFolders && (
                    <Paper
                      variant="outlined"
                      sx={{ p: 1.5, maxHeight: 300, overflow: "auto" }}
                    >
                      <Stack spacing={0.5}>
                        <Typography
                          variant="caption"
                          sx={{ direction: "ltr", wordBreak: "break-all" }}
                        >
                          {serverFolders.data?.path ?? "Server drives"}
                        </Typography>
                        {serverFolders.data?.parent && (
                          <Button
                            type="button"
                            size="small"
                            onClick={() =>
                              setBrowsePath(serverFolders.data?.parent ?? null)
                            }
                          >
                            Up
                          </Button>
                        )}
                        {serverFolders.data?.directories.map((folder) => (
                          <Button
                            type="button"
                            size="small"
                            key={folder}
                            onClick={() => setBrowsePath(folder)}
                            sx={{
                              justifyContent: "flex-start",
                              direction: "ltr",
                            }}
                          >
                            {folder}
                          </Button>
                        ))}
                        {serverFolders.data?.is_local_ai_folder && (
                          <Button
                            type="button"
                            variant="contained"
                            onClick={() => {
                              setLocalAiFolder(serverFolders.data?.path ?? "");
                              setBrowsingFolders(false);
                            }}
                          >
                            Select this AI gateway folder
                          </Button>
                        )}
                      </Stack>
                    </Paper>
                  )}
                  <TextField
                    select
                    label="AI provider"
                    value={aiProvider}
                    onChange={(event) => {
                      const provider = event.target.value as
                        "OLLAMA" | "OPENAI";
                      setAiProvider(provider);
                      setAiModel(
                        provider === "OPENAI" ? "gpt-6-luna" : "qwen2.5:3b",
                      );
                    }}
                  >
                    <MenuItem value="OLLAMA">Ollama · local/offline</MenuItem>
                    <MenuItem value="OPENAI">OpenAI API · cloud</MenuItem>
                  </TextField>
                  <TextField
                    required
                    label="Model"
                    value={aiModel}
                    onChange={(event) => setAiModel(event.target.value)}
                    helperText={
                      aiProvider === "OPENAI"
                        ? "Recommended: gpt-6-luna"
                        : "Enter an installed Ollama model tag."
                    }
                    inputProps={{ dir: "ltr" }}
                  />
                  {aiProvider === "OPENAI" && (
                    <>
                      <TextField
                        name="api_key"
                        type="password"
                        label={
                          localAi.data.api_key_configured
                            ? "Replace OpenAI API key"
                            : "OpenAI API key"
                        }
                        helperText={
                          localAi.data.api_key_configured
                            ? "A key is configured. Leave blank to keep it."
                            : "The key is written only to the gateway .env file and is never returned."
                        }
                        inputProps={{
                          dir: "ltr",
                          autoComplete: "new-password",
                        }}
                      />
                      <Alert severity="warning">
                        Ticket text is sent to OpenAI when this provider is
                        active. Confirm your organization’s privacy and
                        healthcare-data requirements.
                      </Alert>
                    </>
                  )}
                </>
              ) : (
                <TextField
                  required
                  name="remote_base_url"
                  label="Remote AI gateway URL"
                  defaultValue={
                    localAi.data.remote_base_url || "http://AI-SERVER:8090"
                  }
                  helperText="Provider credentials are managed on the remote gateway."
                  inputProps={{ dir: "ltr" }}
                />
              )}
              <Alert severity="info">
                Effective service URL:{" "}
                {localAiMode === "LOCAL"
                  ? "http://127.0.0.1:8090"
                  : localAi.data.remote_base_url || "Configure the remote URL"}
              </Alert>
              <TextField
                name="intake_instructions"
                label="AI ticket intake instructions"
                defaultValue={localAi.data.intake_instructions}
                multiline
                minRows={5}
                inputProps={{ maxLength: 8000 }}
                helperText="Optional business instructions applied immediately. Protected safety and output rules cannot be overridden."
                placeholder="Example: Translate Arabic reports into professional English. Preserve client and product names. Use PACS, RIS, HIS, DICOM and ERP terminology."
              />
              <Stack direction="row" gap={1}>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={saveLocalAi.isPending}
                >
                  Save
                </Button>
                <Button
                  type="button"
                  variant="outlined"
                  disabled={testLocalAi.isPending}
                  onClick={() => testLocalAi.mutate()}
                >
                  Test connection
                </Button>
              </Stack>
            </Stack>
          </Paper>
        )}
      {tab === "third-party-integrations" && integrationTab === "whatsapp" && (
        <InboundIntegrationSettings />
      )}
      {tab === "attachments-storage" && (
        <Paper component="form" onSubmit={submitStorage} sx={{ p: 3 }}>
          <Typography variant="h5">
            {t("systemOperations.storage.title")}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            {t("systemOperations.storage.help")}
          </Typography>
          {storageConfiguration.isError && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {t("systemOperations.storage.unavailable")}
            </Alert>
          )}
          {saveStorage.isSuccess && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {t("systemOperations.storage.saved")}
            </Alert>
          )}
          {saveStorage.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {t("systemOperations.storage.failed")}
            </Alert>
          )}
          <TextField
            key={
              storageConfiguration.data?.attachment_storage_path ??
              status.data?.attachments.storage_path ??
              "storage"
            }
            name="attachment_storage_path"
            label={t("systemOperations.storage.path")}
            defaultValue={
              storageConfiguration.data?.attachment_storage_path ??
              status.data?.attachments.storage_path ??
              ""
            }
            placeholder="D:\\MillensysSupportHub\\Storage"
            required
            fullWidth
            helperText={
              storageConfiguration.data
                ? t("systemOperations.storage.managed", {
                    path: storageConfiguration.data.web_config_path,
                  })
                : t("systemOperations.storage.pathHelp")
            }
            inputProps={{ dir: "ltr" }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={saveStorage.isPending}
            sx={{ mt: 2 }}
          >
            {t(
              saveStorage.isPending
                ? "systemOperations.storage.saving"
                : "systemOperations.storage.save",
            )}
          </Button>
        </Paper>
      )}
      {tab === "advanced" && (
        <Paper sx={{ p: 3 }}>
          <Button
            variant="contained"
            onClick={() => createBackup.mutate()}
            disabled={createBackup.isPending}
            sx={{ float: "right" }}
          >
            {t(
              createBackup.isPending
                ? "systemOperations.backups.creating"
                : "systemOperations.backups.create",
            )}
          </Button>
          <Typography variant="h5" gutterBottom>
            {t("systemOperations.backups.title")}
          </Typography>
          <Alert severity="info" sx={{ my: 2 }}>
            {t("systemOperations.backups.help")}
          </Alert>
          {createBackup.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {t("systemOperations.backups.failed")}
            </Alert>
          )}
          {createBackup.data && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {t("systemOperations.backups.created", {
                filename: createBackup.data.filename,
              })}
            </Alert>
          )}
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("systemOperations.backups.backup")}</TableCell>
                <TableCell>{t("systemOperations.backups.createdAt")}</TableCell>
                <TableCell align="right">
                  {t("systemOperations.backups.size")}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {backups.data?.map((backup) => (
                <TableRow key={backup.filename}>
                  <TableCell sx={{ direction: "ltr" }}>
                    {backup.filename}
                  </TableCell>
                  <TableCell>
                    {new Date(backup.created_at).toLocaleString(locale)}
                  </TableCell>
                  <TableCell align="right">
                    {formatBytes(backup.size_bytes, locale)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Stack>
  );
}
