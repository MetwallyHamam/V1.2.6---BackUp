import {
  Add,
  Autorenew,
  NotificationsActive,
  Pause,
  PlayArrow,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Option = { id: number; name?: string; full_name?: string };
type Template = {
  id: number;
  name: string;
  publication_status: string;
  schedule_mode: string;
};
type Schedule = {
  id: number;
  name: string;
  template_id: number;
  client_id: number;
  assigned_user_id: number | null;
  starts_at: string;
  next_generate_at: string;
  interval_days: number;
  duration_minutes: number;
  timezone: string;
  is_active: boolean;
  is_paused: boolean;
  version: number;
};
type Report = {
  total: number;
  scheduled: number;
  in_progress: number;
  blocked: number;
  overdue: number;
  completed: number;
  cancelled: number;
  on_time_completed: number;
  late_completed: number;
  client_responsible_items: number;
  evidence_gaps: number;
};

export function ServiceChecklistSchedulePanel({
  templates,
}: {
  templates: Template[];
}) {
  const { hasPermission, user } = useAuth();
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [customDays, setCustomDays] = useState<Record<number, string>>({});
  const canManage = hasPermission("service_checklist.schedule.manage"),
    canReport = hasPermission("service_checklist.report.view");
  const canViewSchedules =
    canManage ||
    hasPermission("service_checklist.view_own") ||
    hasPermission("service_checklist.view_team") ||
    hasPermission("service_checklist.view_all");
  const schedules = useQuery({
    queryKey: ["service-checklist-schedules"],
    queryFn: async () =>
      (
        await api.get<Schedule[]>("/service-checklists/schedules", {
          params: canManage ? undefined : { scope: "mine" },
        })
      ).data,
    enabled: canViewSchedules,
  });
  const report = useQuery({
    queryKey: ["service-checklist-report"],
    queryFn: async () =>
      (await api.get<Report>("/service-checklists/reports/summary")).data,
    enabled: canReport,
  });
  const clients = useQuery({
    queryKey: ["clients", "checklist-schedules"],
    queryFn: async () =>
      (await api.get<Option[]>("/clients", { params: { limit: 200 } })).data,
    enabled: open,
  });
  const users = useQuery({
    queryKey: ["service-checklist-assignees"],
    queryFn: async () =>
      (await api.get<Option[]>("/service-checklists/assignees")).data,
    enabled: open,
  });
  const refresh = async () => {
    await cache.invalidateQueries({
      queryKey: ["service-checklist-schedules"],
    });
    await cache.invalidateQueries({
      queryKey: ["service-checklist-occurrences"],
    });
    await cache.invalidateQueries({ queryKey: ["service-checklist-report"] });
  };
  const mutate = useMutation({
    mutationFn: async ({ url, body }: { url: string; body?: object }) =>
      api.post(url, body),
    onSuccess: refresh,
    onError: (cause) =>
      setError(apiErrorMessage(cause, "The schedule action failed.")),
  });
  const metrics: [keyof Report, string][] = [
    ["total", "All"],
    ["scheduled", "Scheduled"],
    ["in_progress", "In progress"],
    ["blocked", "Blocked"],
    ["overdue", "Overdue"],
    ["completed", "Completed"],
    ["on_time_completed", "On time"],
    ["client_responsible_items", "Client responsibility"],
    ["evidence_gaps", "Evidence gaps"],
  ];
  return (
    <Stack spacing={2}>
      {canReport && (
        <Grid container spacing={1.25}>
          {metrics.map(([key, label]) => (
            <Grid key={key} size={{ xs: 6, md: 3, lg: 2 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h4" fontWeight={900}>
                    {report.data?.[key] ?? "—"}
                  </Typography>
                  <Typography color="text.secondary">{label}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
      {canViewSchedules && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            gap={1}
            alignItems={{ md: "center" }}
          >
            <Box flex={1}>
              <Typography variant="h6" fontWeight={850}>
                Recurring schedules
              </Typography>
              <Typography variant="body2" color="text.secondary">
                A 30-day generation horizon creates each occurrence and
                Scheduled Service ticket once.
              </Typography>
            </Box>
            {canManage && (
              <>
                <Button
                  startIcon={<Autorenew />}
                  onClick={() =>
                    mutate.mutate({
                      url: "/service-checklists/schedule-generation/run",
                    })
                  }
                >
                  Generate horizon
                </Button>
                <Button
                  startIcon={<NotificationsActive />}
                  onClick={() =>
                    mutate.mutate({
                      url: "/service-checklists/occurrences/process-reminders",
                    })
                  }
                >
                  Process reminders
                </Button>
                <Button
                  startIcon={<Add />}
                  variant="contained"
                  onClick={() => setOpen(true)}
                >
                  New schedule
                </Button>
              </>
            )}
          </Stack>
          {error && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {error}
            </Alert>
          )}
          <Stack mt={2} spacing={1}>
            {schedules.data?.map((row) => (
              <Paper key={row.id} variant="outlined" sx={{ p: 1.5 }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  gap={1}
                  alignItems={{ sm: "center" }}
                >
                  <Box flex={1}>
                    <Typography fontWeight={800}>{row.name}</Typography>
                    <Typography variant="caption">
                      Every {row.interval_days} days · Next{" "}
                      {new Date(row.next_generate_at).toLocaleString()} ·{" "}
                      {row.timezone}
                    </Typography>
                  </Box>
                  <TextField
                    select
                    size="small"
                    label="Frequency"
                    value={
                      [1, 7, 30].includes(row.interval_days)
                        ? row.interval_days
                        : "custom"
                    }
                    sx={{ minWidth: 140 }}
                    onChange={(event) => {
                      if (event.target.value === "custom") {
                        setCustomDays((current) => ({
                          ...current,
                          [row.id]: String(row.interval_days),
                        }));
                        return;
                      }
                      mutate.mutate({
                        url: `/service-checklists/schedules/${row.id}/cadence`,
                        body: {
                          version: row.version,
                          interval_days: Number(event.target.value),
                        },
                      });
                    }}
                  >
                    <MenuItem value={1}>Daily</MenuItem>
                    <MenuItem value={7}>Weekly</MenuItem>
                    <MenuItem value={30}>Monthly</MenuItem>
                    <MenuItem value="custom">Specific days</MenuItem>
                  </TextField>
                  {(customDays[row.id] !== undefined ||
                    ![1, 7, 30].includes(row.interval_days)) && (
                    <Stack direction="row" gap={0.5}>
                      <TextField
                        size="small"
                        type="number"
                        label="Every days"
                        value={customDays[row.id] ?? String(row.interval_days)}
                        inputProps={{ min: 1, max: 366 }}
                        sx={{ width: 115 }}
                        onChange={(event) =>
                          setCustomDays((current) => ({
                            ...current,
                            [row.id]: event.target.value,
                          }))
                        }
                      />
                      <Button
                        size="small"
                        disabled={
                          Number(customDays[row.id] ?? row.interval_days) < 1 ||
                          Number(customDays[row.id] ?? row.interval_days) > 366
                        }
                        onClick={() =>
                          mutate.mutate({
                            url: `/service-checklists/schedules/${row.id}/cadence`,
                            body: {
                              version: row.version,
                              interval_days: Number(
                                customDays[row.id] ?? row.interval_days,
                              ),
                            },
                          })
                        }
                      >
                        Apply
                      </Button>
                    </Stack>
                  )}
                  <Button
                    startIcon={row.is_paused ? <PlayArrow /> : <Pause />}
                    onClick={() =>
                      mutate.mutate({
                        url: `/service-checklists/schedules/${row.id}/state`,
                        body: { version: row.version, paused: !row.is_paused },
                      })
                    }
                  >
                    {row.is_paused ? "Resume" : "Pause"}
                  </Button>
                </Stack>
              </Paper>
            ))}
          </Stack>
        </Paper>
      )}
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            mutate.mutate({
              url: "/service-checklists/schedules",
              body: {
                name: values.get("name"),
                template_id: Number(values.get("template_id")),
                client_id: Number(values.get("client_id")),
                assigned_user_id: values.get("assigned_user_id")
                  ? Number(values.get("assigned_user_id"))
                  : null,
                starts_at: values.get("starts_at"),
                interval_days: Number(values.get("interval_days")),
                duration_minutes: Number(values.get("duration_minutes")),
                timezone: values.get("timezone"),
              },
            });
            setOpen(false);
          }}
        >
          <DialogTitle>New recurring checklist schedule</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              <TextField required name="name" label="Schedule name" />
              <TextField
                required
                select
                name="template_id"
                label="Published scheduled template"
              >
                {templates
                  .filter(
                    (row) =>
                      row.publication_status === "PUBLISHED" &&
                      row.schedule_mode === "SCHEDULED",
                  )
                  .map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {row.name}
                    </MenuItem>
                  ))}
              </TextField>
              <TextField required select name="client_id" label="Client">
                {clients.data?.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="assigned_user_id"
                label="Engineer"
                defaultValue={user?.id ?? ""}
              >
                <MenuItem value="">Assign to me automatically</MenuItem>
                {users.data?.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.full_name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                required
                name="starts_at"
                label="First occurrence"
                type="datetime-local"
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <Stack direction="row" gap={2}>
                <TextField
                  required
                  fullWidth
                  name="interval_days"
                  label="Repeat every days"
                  type="number"
                  defaultValue={7}
                />
                <TextField
                  required
                  fullWidth
                  name="duration_minutes"
                  label="Due after minutes"
                  type="number"
                  defaultValue={480}
                />
              </Stack>
              <TextField
                required
                name="timezone"
                label="Timezone"
                defaultValue="Africa/Cairo"
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Activate schedule
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
