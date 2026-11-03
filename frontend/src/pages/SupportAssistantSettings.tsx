import {
  Alert,
  Button,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";

export type SupportAssistantSettingsValues = {
  queue_refresh_seconds: number;
  count_refresh_seconds: number;
  unreceived_warning_minutes: number;
  queue_tab_attention_enabled: boolean;
  overdue_card_animation_enabled: boolean;
  mine_show_resolved: boolean;
  mine_show_closed: boolean;
  backlog_default_period:
    "TODAY" | "THIS_WEEK" | "LAST_WEEK" | "THIS_MONTH" | "CUSTOM";
  page_size: number;
  allow_user_overrides: boolean;
  tab_sorting: Record<string, string>;
};
type Response = {
  category: string;
  version: number;
  values: SupportAssistantSettingsValues;
};
const tabs = [
  "queue",
  "mine",
  "backlog",
  "follow-up",
  "sla-risk",
  "pre-tickets",
];
const sorts = [
  "created_at:asc",
  "created_at:desc",
  "updated_at:asc",
  "updated_at:desc",
  "resolved_at:asc",
  "resolved_at:desc",
  "priority:asc",
  "priority:desc",
  "submitted_at:asc",
  "submitted_at:desc",
];

export function SupportAssistantSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const settings = useQuery({
    queryKey: ["site-settings", "support-assistant"],
    queryFn: async () =>
      (await api.get<Response>("/system/site-settings/support-assistant")).data,
  });
  const save = useMutation({
    mutationFn: async (values: SupportAssistantSettingsValues) =>
      api.put("/system/site-settings/support-assistant", {
        ...values,
        expected_version: settings.data?.version,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["site-settings", "support-assistant"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["support-assistant-settings"],
      });
    },
  });
  if (!settings.data) return null;
  const values = settings.data.values;
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    save.mutate({
      queue_refresh_seconds: Number(data.get("queue_refresh_seconds")),
      count_refresh_seconds: Number(data.get("count_refresh_seconds")),
      unreceived_warning_minutes: Number(
        data.get("unreceived_warning_minutes"),
      ),
      queue_tab_attention_enabled:
        data.get("queue_tab_attention_enabled") === "on",
      overdue_card_animation_enabled:
        data.get("overdue_card_animation_enabled") === "on",
      mine_show_resolved: data.get("mine_show_resolved") === "on",
      mine_show_closed: data.get("mine_show_closed") === "on",
      backlog_default_period: String(
        data.get("backlog_default_period"),
      ) as SupportAssistantSettingsValues["backlog_default_period"],
      page_size: Number(data.get("page_size")),
      allow_user_overrides: data.get("allow_user_overrides") === "on",
      tab_sorting: Object.fromEntries(
        tabs.map((tab) => [tab, String(data.get(`sort_${tab}`))]),
      ),
    });
  };
  return (
    <Paper component="form" onSubmit={submit} sx={{ p: 3 }}>
      <Typography variant="h5">
        {t("supportAssistantSettings.title")}
      </Typography>
      <Typography color="text.secondary" mb={2}>
        {t("supportAssistantSettings.help")}
      </Typography>
      {save.isSuccess && (
        <Alert severity="success">{t("supportAssistantSettings.saved")}</Alert>
      )}
      {save.isError && (
        <Alert severity="error">{t("supportAssistantSettings.failed")}</Alert>
      )}
      <Stack spacing={1.5} mt={2}>
        <Stack direction={{ xs: "column", md: "row" }} gap={1}>
          <TextField
            name="queue_refresh_seconds"
            type="number"
            label={t("supportAssistantSettings.queueRefresh")}
            defaultValue={values.queue_refresh_seconds}
            inputProps={{ min: 10, max: 300 }}
            fullWidth
          />
          <TextField
            name="count_refresh_seconds"
            type="number"
            label={t("supportAssistantSettings.countRefresh")}
            defaultValue={values.count_refresh_seconds}
            inputProps={{ min: 10, max: 300 }}
            fullWidth
          />
          <TextField
            name="unreceived_warning_minutes"
            type="number"
            label={t("supportAssistantSettings.warningMinutes")}
            defaultValue={values.unreceived_warning_minutes}
            inputProps={{ min: 1, max: 1440 }}
            fullWidth
          />
          <TextField
            name="page_size"
            type="number"
            label={t("supportAssistantSettings.pageSize")}
            defaultValue={values.page_size}
            inputProps={{ min: 6, max: 50 }}
            fullWidth
          />
        </Stack>
        {(
          [
            ["queue_tab_attention_enabled", "tabAttention"],
            ["overdue_card_animation_enabled", "cardAnimation"],
            ["mine_show_resolved", "mineResolved"],
            ["mine_show_closed", "mineClosed"],
            ["allow_user_overrides", "allowOverrides"],
          ] as const
        ).map(([name, label]) => (
          <FormControlLabel
            key={name}
            control={<Switch name={name} defaultChecked={values[name]} />}
            label={t(`supportAssistantSettings.${label}`)}
          />
        ))}
        <TextField
          select
          name="backlog_default_period"
          label={t("supportAssistantSettings.backlogPeriod")}
          defaultValue={values.backlog_default_period}
        >
          {["TODAY", "THIS_WEEK", "LAST_WEEK", "THIS_MONTH"].map((period) => (
            <MenuItem key={period} value={period}>
              {t(`supportWorkspace.periods.${period}`)}
            </MenuItem>
          ))}
        </TextField>
        <Typography variant="h6">
          {t("supportAssistantSettings.sorting")}
        </Typography>
        <Stack direction={{ xs: "column", md: "row" }} gap={1} flexWrap="wrap">
          {tabs.map((tab) => (
            <TextField
              key={tab}
              select
              name={`sort_${tab}`}
              label={tab}
              defaultValue={values.tab_sorting[tab]}
              sx={{ minWidth: 220, flex: 1 }}
            >
              {sorts
                .filter((option) =>
                  tab === "pre-tickets"
                    ? option.startsWith("submitted_at")
                    : !option.startsWith("submitted_at"),
                )
                .map((option) => (
                  <MenuItem key={option} value={option}>
                    {t(`supportAssistantSettings.sortOptions.${option}`)}
                  </MenuItem>
                ))}
            </TextField>
          ))}
        </Stack>
        <Button type="submit" variant="contained" disabled={save.isPending}>
          {t("supportAssistantSettings.save")}
        </Button>
      </Stack>
    </Paper>
  );
}
