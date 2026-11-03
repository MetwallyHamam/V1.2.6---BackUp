import {
  Alert,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";

export type Widget = {
  widget_code: string;
  title: string;
  widget_type: "KPI_CARD" | "DONUT" | "STACKED_BAR" | "LINE";
  query_code: string;
  position: number;
  width: number;
  refresh_seconds: number;
  config: Record<string, unknown>;
};
type Config = { source: string; name: string; template_version: number; resolution_explanation?: string; base_template_version?: number; assigned_template_version?: number; template_update_available: boolean; widgets: Widget[]; available_widgets: Widget[]; hidden_widget_codes: string[] };

export function DashboardCustomizer({ dashboardType = "EXECUTIVE" }: { dashboardType?: "EXECUTIVE" | "TOP_MANAGEMENT" }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("My Dashboard");
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const config = useQuery({
    queryKey: ["dashboard-config", dashboardType],
    queryFn: async () => (await api.get<Config>("/dashboards/config", { params: { dashboard_type: dashboardType } })).data,
    enabled: open,
  });
  useEffect(() => {
    if (config.data) {
      setName(config.data.name);
      setWidgets(config.data.widgets);
    }
  }, [config.data]);
  const save = useMutation({
    mutationFn: async () =>
      api.put("/dashboards/config", {
        name,
        widgets: widgets.map((item, position) => ({ ...item, position })),
      }, { params: { dashboard_type: dashboardType } }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["dashboard-config"] });
      setOpen(false);
    },
  });
  const reset = useMutation({
    mutationFn: async () => api.delete("/dashboards/config", { params: { dashboard_type: dashboardType } }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ["dashboard-config"] }),
        client.invalidateQueries({ queryKey: ["dashboard-summary"] }),
      ]);
      setOpen(false);
    },
  });
  function toggle(item: Widget, checked: boolean) {
    setWidgets((current) =>
      checked
        ? [
            ...current,
            {
              widget_code: item.widget_code,
              title: item.title,
              widget_type: item.widget_type,
              query_code: item.query_code,
              position: current.length,
              width: item.width,
              refresh_seconds: 60,
              config: {},
            },
          ]
        : current.filter((widget) => widget.widget_code !== item.widget_code),
    );
  }
  return (
    <>
      <Button variant="outlined" onClick={() => setOpen(true)}>
        {t("dashboardCustomizer.open")}
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>{t("dashboardCustomizer.title")}</DialogTitle>
        <DialogContent>
          {config.data && (
            <Alert severity="info" sx={{ mb: 1 }}>
              {t("dashboardCustomizer.source", { source: config.data.source, version: config.data.template_version })}
              {config.data.resolution_explanation ? ` — ${config.data.resolution_explanation}` : ""}
            </Alert>
          )}
          {config.data?.template_update_available && (
            <Alert severity="warning" sx={{ mb: 1 }}>
              {t("dashboardCustomizer.templateUpdateAvailable", {
                base: config.data.base_template_version,
                assigned: config.data.assigned_template_version,
              })}
            </Alert>
          )}
          {save.isError && (
            <Alert severity="error">
              {t("dashboardCustomizer.saveFailed")}
            </Alert>
          )}
          <Stack spacing={1}>
            {config.data?.available_widgets.map((item) => {
              const widget = widgets.find(
                (value) => value.widget_code === item.widget_code,
              );
              return (
                <Stack
                  key={item.widget_code}
                  direction={{ xs: "column", md: "row" }}
                  alignItems={{ md: "center" }}
                  gap={1}
                  sx={{
                    p: 1,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                  }}
                >
                  <FormControlLabel
                    sx={{ minWidth: 250 }}
                    control={
                      <Checkbox
                        checked={Boolean(widget)}
                        onChange={(_, checked) => toggle(item, checked)}
                      />
                    }
                    label={
                      <>
                        <Typography fontWeight={700}>
                          {t(
                            `dashboardCustomizer.widgets.${item.widget_code}.title`,
                            { defaultValue: item.title },
                          )}
                        </Typography>
                      </>
                    }
                  />
                </Stack>
              );
            })}
          </Stack>
        </DialogContent>
        <DialogActions>
          {Boolean(config.data?.hidden_widget_codes.length) && (
            <Button color="warning" disabled={reset.isPending} onClick={() => reset.mutate()}>
              {t("dashboardCustomizer.resetAssigned")}
            </Button>
          )}
          <Button onClick={() => setOpen(false)}>
            {t("dashboardCustomizer.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={save.isPending}
            onClick={() => save.mutate()}
          >
            {t("dashboardCustomizer.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
