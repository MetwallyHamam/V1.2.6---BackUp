import { Add, Delete, GridView, Save, ViewKanban } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  LinearProgress,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Schedule = {
  id: number;
  client_id: number;
  assigned_user_id: number | null;
  version: number;
  client_name: string;
  template_name: string;
  assigned_user_name: string | null;
  next_generate_at: string;
  interval_days: number;
  is_active: boolean;
  is_paused: boolean;
  last_occurrence_id: number | null;
  last_occurrence_number: string | null;
  last_status: string | null;
  last_workflow_status: string | null;
  last_due_at: string | null;
  last_completed_at: string | null;
  last_required_complete: number;
  last_required_total: number;
  last_evidence_gaps: number;
};
type Item = {
  id: number;
  title: string;
  resource_type: string;
  resource_path: string | null;
  check_date: string | null;
  state: string;
  is_required: boolean;
  responsibility: string;
  evidence_type: string;
  evidence_required: boolean;
  evidence_id?: number | null;
  evidence_reference?: string | null;
};
type Occurrence = {
  id: number;
  occurrence_number: string;
  client_name: string;
  template_name: string;
  assigned_user_name: string | null;
  due_at: string;
  status: string;
  workflow_status: string;
  version: number;
  required_complete: number;
  required_total: number;
  service_provided?: string | null;
  completion_summary?: string | null;
  items: Item[] | null;
};
type DraftItem = Item & {
  resource_path: string;
  check_date: string;
  evidence_file?: File | null;
  client_contact?: string;
  result_note?: string;
  create_follow_up_ticket?: boolean;
};
type Filter = "ALL" | "ATTENTION" | "DUE" | "COMPLETED";
type Engineer = { id: number; full_name: string };

const day = 86_400_000;
const overdueDays = (schedule: Schedule) =>
  Math.max(
    0,
    Math.floor(
      (Date.now() -
        new Date(schedule.last_due_at ?? schedule.next_generate_at).getTime()) /
        day,
    ),
  );
const needsAttention = (schedule: Schedule) =>
  !schedule.is_paused &&
  (schedule.last_status === "BLOCKED" ||
    new Date(schedule.last_due_at ?? schedule.next_generate_at).getTime() <
      Date.now() ||
    schedule.last_workflow_status === "NEED_ATTENTION" ||
    schedule.last_evidence_gaps > 0);
const completedThisWeek = (schedule: Schedule) => {
  if (!schedule.last_completed_at) return false;
  return Date.now() - new Date(schedule.last_completed_at).getTime() <= 7 * day;
};
const dueThisWeek = (schedule: Schedule) =>
  !schedule.is_paused &&
  new Date(schedule.last_due_at ?? schedule.next_generate_at).getTime() >=
    Date.now() &&
  new Date(schedule.last_due_at ?? schedule.next_generate_at).getTime() <=
    Date.now() + 7 * day;

type StatusStyle = { label: string; color: string };
const statusStyles = {
  COMPLETED: { label: "Completed", color: "#2E7D32" },
  NEEDS_ATTENTION: { label: "Needs attention", color: "#D32F2F" },
  OVERDUE: { label: "Overdue", color: "#B71C1C" },
  DUE_THIS_WEEK: { label: "Pending · due this week", color: "#ED6C02" },
  UPCOMING: { label: "Upcoming", color: "#1976D2" },
  NOT_STARTED: { label: "Not started", color: "#757575" },
  PAUSED: { label: "Paused", color: "#616161" },
} satisfies Record<string, StatusStyle>;
const scheduleStatusStyle = (schedule: Schedule): StatusStyle => {
  if (schedule.is_paused) return statusStyles.PAUSED;
  if (needsAttention(schedule)) return statusStyles.NEEDS_ATTENTION;
  if (overdueDays(schedule) > 0) return statusStyles.OVERDUE;
  if (dueThisWeek(schedule)) return statusStyles.DUE_THIS_WEEK;
  if (completedThisWeek(schedule)) return statusStyles.COMPLETED;
  if (schedule.last_occurrence_id) return statusStyles.UPCOMING;
  return statusStyles.NOT_STARTED;
};
const eventStatusStyle = (event: Occurrence): StatusStyle => {
  const status = event.workflow_status || event.status;
  if (status === "COMPLETE" || status === "COMPLETED")
    return statusStyles.COMPLETED;
  if (status === "NEED_ATTENTION" || status === "BLOCKED")
    return statusStyles.NEEDS_ATTENTION;
  if (new Date(event.due_at).getTime() < Date.now())
    return statusStyles.OVERDUE;
  if (status === "PENDING" || status === "IN_PROGRESS")
    return statusStyles.DUE_THIS_WEEK;
  return statusStyles.UPCOMING;
};

export function SimpleChecklistWorkspace({ monitor }: { monitor?: boolean }) {
  const initialParams = new URLSearchParams(window.location.search);
  const requestedFilter = initialParams.get("filter") as Filter | null;
  const requestedClientId = Number(initialParams.get("client_id"));
  const { hasPermission } = useAuth();
  const cache = useQueryClient();
  const [filter, setFilter] = useState<Filter>(
    requestedFilter &&
      ["ALL", "ATTENTION", "DUE", "COMPLETED"].includes(requestedFilter)
      ? requestedFilter
      : monitor
        ? "ATTENTION"
        : "ALL",
  );
  const [clientFilter, setClientFilter] = useState<string | null>(null);
  const layoutKey = `supporthub-checklist-layout-${monitor ? "monitor" : "mine"}`;
  const defaultLayout = (() => {
    try { return JSON.parse(window.localStorage.getItem(layoutKey) || window.localStorage.getItem(`${layoutKey}-default`) || "null") as { layout: "GRID" | "LANES"; groupBy: "STATUS" | "ENGINEER" } | null; } catch { return null; }
  })();
  const [layout, setLayout] = useState<"GRID" | "LANES">(defaultLayout?.layout ?? (monitor ? "LANES" : "GRID"));
  const [groupBy, setGroupBy] = useState<"STATUS" | "ENGINEER">(defaultLayout?.groupBy ?? "STATUS");
  const [selected, setSelected] = useState<Occurrence | null>(null);
  const [historySchedule, setHistorySchedule] = useState<Schedule | null>(null);
  const [historyFrom, setHistoryFrom] = useState("");
  const [historyTo, setHistoryTo] = useState("");
  const [transferUserId, setTransferUserId] = useState("");
  const [draftItems, setDraftItems] = useState<DraftItem[]>([]);
  const [serviceProvided, setServiceProvided] = useState("");
  const [clientSummary, setClientSummary] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selectedCards, setSelectedCards] = useState<number[]>([]);
  const [cardMenu, setCardMenu] = useState<{
    schedule: Schedule;
    mouseX: number;
    mouseY: number;
  } | null>(null);
  const schedules = useQuery({
    queryKey: ["service-checklist-schedules", monitor ? "monitor" : "mine"],
    queryFn: async () =>
      (
        await api.get<Schedule[]>("/service-checklists/schedules", {
          params: monitor ? undefined : { scope: "mine" },
        })
      ).data,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: "always",
  });
  const detail = useQuery({
    queryKey: ["service-checklist-event", selected?.id],
    queryFn: async () =>
      (
        await api.get<Occurrence>(
          `/service-checklists/occurrences/${selected!.id}`,
        )
      ).data,
    enabled: Boolean(selected),
  });
  useEffect(() => {
    if (!detail.data?.items || !selected) return;
    const storageKey = `supporthub-checklist-draft-${selected.id}`;
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "null") as {
        items?: DraftItem[];
        serviceProvided?: string;
        clientSummary?: string;
      } | null;
      if (saved?.items?.length) {
        setDraftItems(saved.items.map((item) => ({ ...item, evidence_file: null })));
        setServiceProvided(saved.serviceProvided || `${selected.template_name} completed`);
        setClientSummary(saved.clientSummary || "Checklist completed with no exceptions.");
        return;
      }
    } catch { /* Ignore an invalid local draft. */ }
    setDraftItems(
      detail.data.items.map((item) => ({
        ...item,
        state: ["CLIENT_RESPONSIBILITY", "CLIENT_RESPONSIBLE"].includes(item.state)
          ? "CLIENT_RESPONSIBILITY"
          : item.state === "NEED_ATTENTION"
            ? "NEED_ATTENTION"
            : "COMPLETE",
        resource_path: item.resource_path ?? "",
        check_date: (item.check_date ?? new Date().toISOString()).slice(0, 10),
        client_contact: "",
        result_note: "",
        evidence_file: null,
        create_follow_up_ticket: item.state === "NEED_ATTENTION",
      })),
    );
    setServiceProvided(detail.data.service_provided || `${selected.template_name} completed`);
    setClientSummary(detail.data.completion_summary || "Checklist completed with no exceptions.");
  }, [detail.data, selected]);
  useEffect(() => {
    if (!selected || !draftItems.length) return;
    const serializable = draftItems.map(({ evidence_file, ...item }) => {
      void evidence_file;
      return item;
    });
    localStorage.setItem(
      `supporthub-checklist-draft-${selected.id}`,
      JSON.stringify({ items: serializable, serviceProvided, clientSummary }),
    );
  }, [clientSummary, draftItems, selected, serviceProvided]);
  const history = useQuery({
    queryKey: [
      "service-checklist-history",
      historySchedule?.id,
      historyFrom,
      historyTo,
    ],
    queryFn: async () =>
      (
        await api.get<Occurrence[]>(
          `/service-checklists/schedules/${historySchedule!.id}/history`,
          {
            params: {
              date_from: historyFrom ? `${historyFrom}T00:00:00` : undefined,
              date_to: historyTo ? `${historyTo}T23:59:59` : undefined,
            },
          },
        )
      ).data,
    enabled: Boolean(historySchedule),
  });
  const canTransfer =
    hasPermission("service_checklist.schedule.manage") ||
    hasPermission("service_checklist.reassign");
  const engineers = useQuery({
    queryKey: ["service-checklist-assignees", "history-transfer"],
    queryFn: async () =>
      (await api.get<Engineer[]>("/service-checklists/assignees")).data,
    enabled: Boolean(historySchedule && canTransfer),
  });
  const openEvent = (event: Occurrence) => {
    setError("");
    setDraftItems([]);
    setSelected(event);
  };
  const addEvent = useMutation({
    mutationFn: async (scheduleId: number) =>
      (
        await api.post<Occurrence>(
          `/service-checklists/schedules/${scheduleId}/events`,
        )
      ).data,
    onSuccess: async (event) => {
      openEvent(event);
      await cache.invalidateQueries({
        queryKey: ["service-checklist-schedules"],
      });
    },
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The checklist event could not be opened."),
      ),
  });
  const openLatest = async (schedule: Schedule) => {
    if (!schedule.last_occurrence_id) {
      if (!monitor) addEvent.mutate(schedule.id);
      return;
    }
    try {
      const event = (
        await api.get<Occurrence>(
          `/service-checklists/occurrences/${schedule.last_occurrence_id}`,
        )
      ).data;
      openEvent(event);
    } catch (cause) {
      setError(
        apiErrorMessage(
          cause,
          "The latest checklist event could not be opened.",
        ),
      );
    }
  };
  const openHistory = (schedule: Schedule) => {
    setHistorySchedule(schedule);
    setTransferUserId(String(schedule.assigned_user_id ?? ""));
    setHistoryFrom("");
    setHistoryTo("");
  };
  const save = useMutation({
    mutationFn: async ({ complete }: { complete: boolean }) => {
      if (!selected) return;
      const items = [];
      for (const item of draftItems) {
        let evidenceId: number | null = item.evidence_id ?? null;
        if (item.evidence_file) {
          const upload = new FormData();
          upload.append("upload", item.evidence_file);
          evidenceId = (
            await api.post<{ id: number }>(
              `/service-checklists/occurrences/${selected.id}/evidence`,
              upload,
            )
          ).data.id;
        }
        items.push({
          item_id: item.id,
          choice:
            item.state === "NEED_ATTENTION"
              ? "NEEDS_ATTENTION"
              : item.state === "CLIENT_RESPONSIBILITY"
                ? "CLIENT_ACTION"
                : "DONE",
          resource_path: item.resource_path || null,
          check_date: item.check_date || new Date().toISOString(),
          note: item.result_note || null,
          evidence_reference: item.evidence_file?.name || item.evidence_reference || item.resource_path || item.result_note || null,
          evidence_id: evidenceId,
          client_contact: item.client_contact || null,
          create_follow_up_ticket: Boolean(item.create_follow_up_ticket),
        });
      }
      return (
        await api.post<{ occurrence: Occurrence; follow_up_ticket_numbers: string[] }>(
          `/service-checklists/occurrences/${selected.id}/quick-complete`,
          {
            version: detail.data?.version ?? selected.version,
            items,
            service_provided: serviceProvided,
            completion_summary: clientSummary,
            complete,
          },
        )
      ).data;
    },
    onSuccess: async () => {
      if (selected) localStorage.removeItem(`supporthub-checklist-draft-${selected.id}`);
      setSelected(null);
      setDraftItems([]);
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["service-checklist-schedules"] }),
        cache.invalidateQueries({
          queryKey: ["service-checklist-occurrences"],
        }),
      ]);
    },
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The checklist event could not be saved."),
      ),
  });
  const taskRow = useMutation({
    mutationFn: async ({ item, remove }: { item: DraftItem; remove?: boolean }) => {
      if (!selected || !detail.data) return;
      if (remove) {
        return (
          await api.delete<Occurrence>(
            `/service-checklists/occurrences/${selected.id}/items/${item.id}`,
            { params: { expected_version: detail.data.version } },
          )
        ).data;
      }
      return (
        await api.patch<Occurrence>(
          `/service-checklists/occurrences/${selected.id}/items/${item.id}/details`,
          {
            version: detail.data.version,
            resource_type: item.resource_type,
            title: item.title.trim(),
            resource_path: item.resource_path.trim() || null,
            check_date: item.check_date,
          },
        )
      ).data;
    },
    onSuccess: async (event) => {
      if (!event) return;
      cache.setQueryData(["service-checklist-event", event.id], event);
      setSelected(event);
      localStorage.removeItem(`supporthub-checklist-draft-${event.id}`);
      setDraftItems(
        (event.items ?? []).map((item) => ({
          ...item,
          resource_path: item.resource_path ?? "",
          check_date: (item.check_date ?? new Date().toISOString()).slice(0, 10),
          client_contact: "",
          result_note: "",
          evidence_file: null,
          create_follow_up_ticket: false,
        })),
      );
      await cache.invalidateQueries({
        queryKey: ["service-checklist-event", event.id],
      });
      await cache.invalidateQueries({
        queryKey: ["service-checklist-schedules"],
      });
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "The checklist task could not be changed.")),
  });
  const reminder = useMutation({
    mutationFn: async (scheduleIds: number[]) =>
      (
        await api.post<{ sent: number; deduplicated: number }>(
          "/service-checklists/schedules/bulk-reminders",
          { schedule_ids: scheduleIds },
        )
      ).data,
    onSuccess: (result) => {
      setMessage(
        `${result.sent} reminder(s) sent${result.deduplicated ? `; ${result.deduplicated} already sent today` : ""}.`,
      );
      setSelectedCards([]);
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "The reminders could not be sent.")),
  });
  const transfer = useMutation({
    mutationFn: async () => {
      if (!historySchedule || !transferUserId) return;
      return api.post(
        `/service-checklists/schedules/${historySchedule.id}/reassign`,
        {
          version: historySchedule.version,
          assigned_user_id: Number(transferUserId),
          reason: "Client checklist transferred from checklist history",
        },
      );
    },
    onSuccess: async () => {
      setMessage("The client checklist assignment was transferred.");
      setHistorySchedule(null);
      await cache.invalidateQueries({
        queryKey: ["service-checklist-schedules"],
      });
    },
    onError: (cause) =>
      setError(
        apiErrorMessage(
          cause,
          "The checklist assignment could not be transferred.",
        ),
      ),
  });
  const exportLatest = async (schedule: Schedule) => {
    if (!schedule.last_occurrence_id) {
      setError("This card does not have an event to export yet.");
      return;
    }
    try {
      const response = await api.get(
        `/service-checklists/occurrences/${schedule.last_occurrence_id}/export.xlsx`,
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${schedule.last_occurrence_number || "checklist-event"}-tasks.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setError(
        apiErrorMessage(cause, "The latest event could not be exported."),
      );
    }
  };
  const shareLatest = async (schedule: Schedule) => {
    if (!schedule.last_occurrence_id) {
      setError("This card does not have an event to share yet.");
      return;
    }
    try {
      const result = (
        await api.post<{ url: string }>(
          `/service-checklists/occurrences/${schedule.last_occurrence_id}/share`,
        )
      ).data;
      await navigator.clipboard.writeText(result.url);
      setMessage("The public checklist URL was copied to the clipboard.");
    } catch (cause) {
      setError(
        apiErrorMessage(
          cause,
          "The public checklist URL could not be created.",
        ),
      );
    }
  };

  const rows = schedules.data ?? [];
  const counts = {
    ALL: rows.length,
    ATTENTION: rows.filter(needsAttention).length,
    DUE: rows.filter(dueThisWeek).length,
    COMPLETED: rows.filter((row) => completedThisWeek(row) && !dueThisWeek(row)).length,
  };
  const visible = rows.filter((row) => {
    if (
      Number.isFinite(requestedClientId) &&
      requestedClientId > 0 &&
      row.client_id !== requestedClientId
    )
      return false;
    if (clientFilter && row.client_name !== clientFilter) return false;
    return filter === "ATTENTION"
      ? needsAttention(row)
      : filter === "DUE"
        ? dueThisWeek(row)
        : filter === "COMPLETED"
          ? completedThisWeek(row) && !dueThisWeek(row)
          : true;
  });
  const clientOverview = Array.from(new Set(rows.map((row) => row.client_name)))
    .map((client) => {
      const assignments = rows.filter((row) => row.client_name === client);
      const completed = assignments.filter(completedThisWeek).length;
      const attention = assignments.filter(needsAttention).length;
      return { client, total: assignments.length, completed, attention };
    })
    .sort(
      (a, b) => b.attention - a.attention || a.client.localeCompare(b.client),
    );
  const statusLanes = useMemo(
    () => [
        ["NEEDS ATTENTION", visible.filter(needsAttention)],
        [
          "DUE THIS WEEK",
          visible.filter((row) => !needsAttention(row) && dueThisWeek(row)),
        ],
        [
          "COMPLETED THIS WEEK",
          visible.filter(
            (row) => !needsAttention(row) && !dueThisWeek(row) && completedThisWeek(row),
          ),
        ],
        [
          "UPCOMING",
          visible.filter(
            (row) =>
              !needsAttention(row) &&
              !dueThisWeek(row) &&
              !completedThisWeek(row),
          ),
        ],
      ] as const,
    [visible],
  );
  const lanes = useMemo(() => {
    if (groupBy === "STATUS") return statusLanes;
    return Array.from(new Set(visible.map((row) => row.assigned_user_name || "Unassigned")))
      .sort()
      .map((engineer) => [engineer.toUpperCase(), visible.filter((row) => (row.assigned_user_name || "Unassigned") === engineer)] as const);
  }, [groupBy, statusLanes, visible]);
  const card = (schedule: Schedule) => {
    const visualStatus = scheduleStatusStyle(schedule);
    return (
      <Paper
        key={schedule.id}
        draggable={!monitor}
        onDragStart={(event) => event.dataTransfer.setData("text/checklist-schedule", String(schedule.id))}
        component="article"
        role="button"
        tabIndex={0}
        aria-label={`Open ${schedule.client_name} ${schedule.template_name}`}
        onClick={() => openHistory(schedule)}
        onContextMenu={(event) => {
          event.preventDefault();
          setCardMenu({
            schedule,
            mouseX: event.clientX + 2,
            mouseY: event.clientY - 6,
          });
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openHistory(schedule);
          }
        }}
        variant="outlined"
        sx={{
          p: 2,
          cursor: "pointer",
          border: `2px solid ${visualStatus.color}`,
          borderInlineStart: `7px solid ${visualStatus.color}`,
          transition: "150ms ease",
          "&:hover, &:focus-visible": {
            boxShadow: 5,
            transform: "translateY(-2px)",
          },
        }}
      >
        <Stack
          direction="column"
          alignItems="stretch"
          gap={1}
        >
          <Box minWidth={0} width="100%">
            <Typography
              fontWeight={900}
              sx={{ overflowWrap: "break-word", wordBreak: "normal" }}
            >
              {schedule.client_name}
            </Typography>
            <Typography
              variant="body2"
              sx={{ overflowWrap: "break-word", wordBreak: "normal" }}
            >
              {schedule.template_name}
            </Typography>
          </Box>
          <Stack
            direction="row"
            alignItems="center"
            alignSelf="stretch"
            justifyContent={monitor ? "space-between" : "flex-end"}
          >
            {monitor && (
              <Checkbox
                size="small"
                disabled={!needsAttention(schedule)}
                checked={selectedCards.includes(schedule.id)}
                onClick={(event) => event.stopPropagation()}
                onChange={(event) =>
                  setSelectedCards((current) =>
                    event.target.checked
                      ? [...new Set([...current, schedule.id])]
                      : current.filter((id) => id !== schedule.id),
                  )
                }
                inputProps={{ "aria-label": `Select ${schedule.client_name}` }}
              />
            )}
            <Chip
              size="small"
              label={visualStatus.label.toUpperCase()}
              sx={{
                bgcolor: visualStatus.color,
                color: "#fff",
                fontWeight: 800,
              }}
            />
          </Stack>
        </Stack>
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          mt={1}
        >
          {schedule.assigned_user_name || "Unassigned"} · Last event{" "}
          {schedule.last_occurrence_number || "—"}
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          Last completed:{" "}
          {schedule.last_completed_at
            ? new Date(schedule.last_completed_at).toLocaleString()
            : "Never"}
        </Typography>
        <Typography
          variant="caption"
          color={overdueDays(schedule) ? "error" : "text.secondary"}
          display="block"
        >
          Current due:{" "}
          {new Date(
            schedule.last_due_at ?? schedule.next_generate_at,
          ).toLocaleString()}
          {overdueDays(schedule)
            ? ` · ${overdueDays(schedule)} days overdue`
            : ""}
        </Typography>
        <LinearProgress
          variant="determinate"
          value={
            schedule.last_required_total
              ? (schedule.last_required_complete /
                  schedule.last_required_total) *
                100
              : 0
          }
          sx={{ my: 1 }}
        />
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
        >
          <Typography variant="caption">
            {schedule.last_required_complete}/{schedule.last_required_total}{" "}
            tasks · {schedule.last_evidence_gaps} evidence gaps
          </Typography>
          {!monitor && (
            <Button
              size="small"
              startIcon={<Add />}
              onClick={(event) => {
                event.stopPropagation();
                addEvent.mutate(schedule.id);
              }}
            >
              Add event
            </Button>
          )}
        </Stack>
      </Paper>
    );
  };

  return (
    <Stack spacing={2}>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      {message && (
        <Alert severity="success" onClose={() => setMessage("")}>
          {message}
        </Alert>
      )}
      <Paper
        variant="outlined"
        sx={{ p: 1.25 }}
        aria-label="Checklist status color legend"
      >
        <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
          <Typography variant="body2" fontWeight={850} mr={0.5}>
            Status colors
          </Typography>
          {Object.entries(statusStyles).map(([key, style]) => (
            <Chip
              key={key}
              size="small"
              label={style.label}
              sx={{ bgcolor: style.color, color: "#fff", fontWeight: 750 }}
            />
          ))}
        </Stack>
      </Paper>
      <Stack direction={{ xs: "column", md: "row" }} gap={1}>
        {(
          [
            ["ALL", "Assigned clients"],
            ["COMPLETED", "Completed this week"],
            ["DUE", "Due this week"],
            ["ATTENTION", "Needs attention"],
          ] as const
        ).map(([key, label]) => (
          <Paper
            key={key}
            role="button"
            tabIndex={0}
            onClick={() => setFilter(key)}
            onKeyDown={(event) =>
              (event.key === "Enter" || event.key === " ") && setFilter(key)
            }
            variant="outlined"
            sx={{
              p: 2,
              flex: 1,
              cursor: "pointer",
              borderColor: filter === key ? "primary.main" : undefined,
              "&:hover, &:focus-visible": { boxShadow: 3 },
            }}
          >
            <Typography variant="h4" fontWeight={900}>
              {counts[key]}
            </Typography>
            <Typography color="text.secondary">{label}</Typography>
          </Paper>
        ))}
      </Stack>
      {monitor && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
          >
            <Box>
              <Typography variant="h6" fontWeight={900}>
                Client completion overview
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Completed this week and assignments requiring attention.
              </Typography>
            </Box>
            {clientFilter && (
              <Button onClick={() => setClientFilter(null)}>
                Show all clients
              </Button>
            )}
          </Stack>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "repeat(2,minmax(0,1fr))" },
              gap: 1,
            }}
          >
            {clientOverview.map((row) => (
              <Paper
                key={row.client}
                role="button"
                tabIndex={0}
                onClick={() => setClientFilter(row.client)}
                onKeyDown={(event) =>
                  (event.key === "Enter" || event.key === " ") &&
                  setClientFilter(row.client)
                }
                sx={{
                  p: 1.25,
                  cursor: "pointer",
                  bgcolor:
                    clientFilter === row.client
                      ? "action.selected"
                      : "action.hover",
                  "&:hover, &:focus-visible": { boxShadow: 3 },
                }}
              >
                <Stack direction="row" justifyContent="space-between" gap={1}>
                  <Typography fontWeight={800}>{row.client}</Typography>
                  <Typography
                    variant="caption"
                    color={row.attention ? "error" : "success.main"}
                  >
                    {row.attention} missing / attention
                  </Typography>
                </Stack>
                <LinearProgress
                  color={row.attention ? "warning" : "success"}
                  variant="determinate"
                  value={row.total ? (row.completed / row.total) * 100 : 0}
                  sx={{ my: 0.75 }}
                />
                <Typography variant="caption">
                  {row.completed}/{row.total} completed this week
                </Typography>
              </Paper>
            ))}
          </Box>
        </Paper>
      )}
      {monitor && selectedCards.length > 0 && (
        <Paper
          variant="outlined"
          sx={{ p: 1.25, position: "sticky", top: 8, zIndex: 2 }}
        >
          <Stack direction="row" alignItems="center" gap={1}>
            <Typography flex={1} fontWeight={800}>
              {selectedCards.length} checklist card(s) selected
            </Typography>
            <Button onClick={() => setSelectedCards([])}>Clear</Button>
            <Button
              variant="contained"
              disabled={reminder.isPending}
              onClick={() => reminder.mutate(selectedCards)}
            >
              Send reminders
            </Button>
          </Stack>
        </Paper>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="flex-end" gap={1}>
          <TextField
            select
            size="small"
            label="Group lanes by"
            value={groupBy}
            sx={{ minWidth: 180 }}
            onChange={(event) => {
              setGroupBy(event.target.value as "STATUS" | "ENGINEER");
              setLayout("LANES");
            }}
          >
            <MenuItem value="STATUS">Status</MenuItem>
            <MenuItem value="ENGINEER">Engineer</MenuItem>
          </TextField>
          <Button
            startIcon={<GridView />}
            variant={layout === "GRID" ? "contained" : "outlined"}
            onClick={() => setLayout("GRID")}
          >
            Grid
          </Button>
          <Button
            startIcon={<ViewKanban />}
            variant={layout === "LANES" ? "contained" : "outlined"}
            onClick={() => setLayout("LANES")}
          >
            Lanes
          </Button>
          <Button startIcon={<Save />} onClick={() => {
            window.localStorage.setItem(layoutKey, JSON.stringify({ layout, groupBy }));
            setMessage("Checklist layout saved.");
          }}>Save layout</Button>
          <Button variant="outlined" onClick={() => {
            window.localStorage.setItem(`${layoutKey}-default`, JSON.stringify({ layout, groupBy }));
            window.localStorage.setItem(layoutKey, JSON.stringify({ layout, groupBy }));
            setMessage("This is now your default checklist layout.");
          }}>Set as default</Button>
        </Stack>
      {schedules.isLoading && <LinearProgress />}
      {!visible.length && !schedules.isLoading && (
        <Alert severity="info">No checklist assignments match this view.</Alert>
      )}
      {layout === "LANES" ? (
        <Box
          sx={{
            display: "grid",
            gridAutoFlow: "column",
            gridAutoColumns: { xs: "minmax(280px,86vw)", sm: "320px" },
            gap: 1.5,
            overflowX: "auto",
            alignItems: "stretch",
            pb: 1,
          }}
        >
          {lanes.map(([label, laneRows]) => (
            <Paper
              key={label}
              variant="outlined"
              onDragOver={(event) => {
                if (!monitor && groupBy === "STATUS" && label === "COMPLETED THIS WEEK") event.preventDefault();
              }}
              onDrop={(event) => {
                if (monitor || groupBy !== "STATUS" || label !== "COMPLETED THIS WEEK") return;
                const scheduleId = Number(event.dataTransfer.getData("text/checklist-schedule"));
                if (scheduleId) addEvent.mutate(scheduleId);
              }}
              sx={{
                p: 1.25,
                minHeight: 420,
                bgcolor: "action.hover",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                mb={1}
                sx={{ position: "sticky", top: 0, zIndex: 1 }}
              >
                <Typography fontWeight={900}>{label}</Typography>
                <Chip size="small" label={laneRows.length} />
              </Stack>
              <Stack spacing={1} flex={1}>{laneRows.map(card)}</Stack>
            </Paper>
          ))}
        </Box>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label="Service checklist list">
            <TableHead>
              <TableRow>
                {monitor && <TableCell padding="checkbox" />}
                <TableCell>Client</TableCell>
                <TableCell>Checklist</TableCell>
                <TableCell>Engineer</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Last completed</TableCell>
                <TableCell>Next checklist</TableCell>
                <TableCell align="center">Tasks</TableCell>
                <TableCell align="right">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {visible.map((schedule) => {
                const visualStatus = scheduleStatusStyle(schedule);
                return (
                  <TableRow
                    hover
                    key={schedule.id}
                    tabIndex={0}
                    onClick={() => openHistory(schedule)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        openHistory(schedule);
                      }
                    }}
                    sx={{
                      cursor: "pointer",
                      "& > td:first-of-type": {
                        borderInlineStart: `4px solid ${visualStatus.color}`,
                      },
                    }}
                  >
                    {monitor && (
                      <TableCell padding="checkbox">
                        <Checkbox
                          size="small"
                          disabled={!needsAttention(schedule)}
                          checked={selectedCards.includes(schedule.id)}
                          onClick={(event) => event.stopPropagation()}
                          onChange={(event) =>
                            setSelectedCards((current) =>
                              event.target.checked
                                ? [...new Set([...current, schedule.id])]
                                : current.filter((id) => id !== schedule.id),
                            )
                          }
                          inputProps={{ "aria-label": `Select ${schedule.client_name}` }}
                        />
                      </TableCell>
                    )}
                    <TableCell sx={{ fontWeight: 850, whiteSpace: "nowrap" }}>
                      {schedule.client_name}
                    </TableCell>
                    <TableCell>{schedule.template_name}</TableCell>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      {schedule.assigned_user_name || "Unassigned"}
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={visualStatus.label}
                        sx={{ bgcolor: visualStatus.color, color: "#fff", fontWeight: 750 }}
                      />
                    </TableCell>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      {schedule.last_completed_at
                        ? new Date(schedule.last_completed_at).toLocaleString()
                        : "Never"}
                    </TableCell>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      {new Date(schedule.last_due_at ?? schedule.next_generate_at).toLocaleString()}
                    </TableCell>
                    <TableCell align="center" sx={{ whiteSpace: "nowrap" }}>
                      {schedule.last_required_complete}/{schedule.last_required_total}
                    </TableCell>
                    <TableCell align="right">
                      {!monitor ? (
                        <Button
                          size="small"
                          startIcon={<Add />}
                          onClick={(event) => {
                            event.stopPropagation();
                            addEvent.mutate(schedule.id);
                          }}
                        >
                          Add event
                        </Button>
                      ) : (
                        <Button
                          size="small"
                          onClick={(event) => {
                            event.stopPropagation();
                            openHistory(schedule);
                          }}
                        >
                          Open
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      <Dialog
        open={Boolean(historySchedule)}
        onClose={() => setHistorySchedule(null)}
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle>
          {historySchedule?.client_name} · Checklist history
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} mt={1}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              alignItems={{ sm: "center" }}
            >
              <TextField
                size="small"
                type="date"
                label="Date from"
                value={historyFrom}
                onChange={(event) => setHistoryFrom(event.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                size="small"
                type="date"
                label="Date to"
                value={historyTo}
                onChange={(event) => setHistoryTo(event.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <Button
                onClick={() => {
                  setHistoryFrom("");
                  setHistoryTo("");
                }}
              >
                Clear dates
              </Button>
              <Typography variant="body2" color="text.secondary" flex={1}>
                {history.data?.length ?? 0} event(s)
              </Typography>
            </Stack>
            {canTransfer && (
              <Paper variant="outlined" sx={{ p: 1.5 }}>
                <Typography fontWeight={850} mb={1}>
                  Transfer client checklist
                </Typography>
                <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                  <TextField
                    select
                    size="small"
                    label="Assigned engineer"
                    value={transferUserId}
                    onChange={(event) => setTransferUserId(event.target.value)}
                    sx={{ minWidth: 280 }}
                  >
                    {engineers.data?.map((engineer) => (
                      <MenuItem key={engineer.id} value={engineer.id}>
                        {engineer.full_name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Button
                    variant="outlined"
                    disabled={
                      !transferUserId ||
                      Number(transferUserId) ===
                        historySchedule?.assigned_user_id ||
                      transfer.isPending
                    }
                    onClick={() => transfer.mutate()}
                  >
                    Transfer assignment
                  </Button>
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  The assignment and unfinished events move to the new engineer.
                  Completed event history is preserved.
                </Typography>
              </Paper>
            )}
            {history.isLoading && <LinearProgress />}
            {!history.isLoading && !history.data?.length && (
              <Alert severity="info">
                No checklist events match this date range.
              </Alert>
            )}
            <Stack spacing={1}>
              {history.data?.map((event) => {
                const visualStatus = eventStatusStyle(event);
                return (
                  <Paper
                    key={event.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => openEvent(event)}
                    onKeyDown={(keyEvent) =>
                      (keyEvent.key === "Enter" || keyEvent.key === " ") &&
                      openEvent(event)
                    }
                    variant="outlined"
                    sx={{
                      p: 1.5,
                      cursor: "pointer",
                      border: `2px solid ${visualStatus.color}`,
                      borderInlineStart: `7px solid ${visualStatus.color}`,
                      "&:hover, &:focus-visible": { boxShadow: 3 },
                    }}
                  >
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      gap={1}
                      alignItems={{ sm: "center" }}
                    >
                      <Box flex={1}>
                        <Typography fontWeight={850}>
                          {event.occurrence_number}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {new Date(event.due_at).toLocaleString()} ·{" "}
                          {event.assigned_user_name || "Unassigned"}
                        </Typography>
                      </Box>
                      <Chip
                        label={visualStatus.label}
                        sx={{
                          bgcolor: visualStatus.color,
                          color: "#fff",
                          fontWeight: 800,
                        }}
                      />
                      <Typography variant="body2">
                        {event.required_complete}/{event.required_total} tasks
                      </Typography>
                    </Stack>
                  </Paper>
                );
              })}
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistorySchedule(null)}>Close</Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(selected)}
        onClose={() => !save.isPending && setSelected(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {selected?.client_name} · {selected?.template_name}
        </DialogTitle>
        <DialogContent>
          {detail.isLoading && <LinearProgress />}
          {error && (
            <Alert severity="error" sx={{ mb: 1 }}>
              {error}
            </Alert>
          )}
          {detail.data && (
            <Stack spacing={1.5} mt={1}>
              <Stack direction="row" gap={1} flexWrap="wrap">
                <Chip label={detail.data.occurrence_number} />
                <Chip label={detail.data.status.replaceAll("_", " ")} />
                <Chip
                  label={`Due ${new Date(detail.data.due_at).toLocaleString()}`}
                />
              </Stack>
              {!monitor && (
                <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>
                  <Typography fontWeight={800}>Detailed review</Typography>
                  <Button sx={{ ml: { sm: "auto" } }} onClick={() => setDraftItems((items) => items.map((item) => ({ ...item, state: "COMPLETE" })))}>Mark all as Done</Button>
                </Stack>
              )}
              {(draftItems.length
                ? draftItems
                : (detail.data.items ?? []).map((item) => ({
                    ...item,
                    resource_path: item.resource_path ?? "",
                    check_date: (
                      item.check_date ?? new Date().toISOString()
                    ).slice(0, 10),
                    client_contact: "",
                    result_note: "",
                    evidence_file: null,
                     create_follow_up_ticket: false,
                  }))
              ).map((item) => {
                const source = draftItems.length
                  ? draftItems
                  : (detail.data.items ?? []).map((entry) => ({
                      ...entry,
                      resource_path: entry.resource_path ?? "",
                      check_date: (
                        entry.check_date ?? new Date().toISOString()
                      ).slice(0, 10),
                      client_contact: "",
                      result_note: "",
                      evidence_file: null,
                      create_follow_up_ticket: false,
                    }));
                const update = (change: Partial<DraftItem>) =>
                  setDraftItems(
                    source.map((entry) =>
                      entry.id === item.id ? { ...entry, ...change } : entry,
                    ),
                  );
                return (
                  <Paper key={item.id} variant="outlined" sx={{ p: 1.5 }}>
                    <Stack spacing={1}>
                      <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>
                        <TextField
                          size="small"
                          fullWidth
                          required
                          label="Task"
                          value={item.title}
                          onChange={(event) => update({ title: event.target.value })}
                        />
                        {!monitor && detail.data?.status !== "COMPLETED" && (
                          <>
                            <Button
                              startIcon={<Save />}
                              disabled={taskRow.isPending || item.title.trim().length < 2}
                              onClick={() => taskRow.mutate({ item })}
                            >
                              Save task
                            </Button>
                            <Button
                              color="error"
                              startIcon={<Delete />}
                              disabled={taskRow.isPending}
                              onClick={() => {
                                if (window.confirm(`Delete task “${item.title}”?`))
                                  taskRow.mutate({ item, remove: true });
                              }}
                            >
                              Delete
                            </Button>
                          </>
                        )}
                      </Stack>
                      <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                        <TextField
                          select
                          size="small"
                          label="Result"
                          value={
                            ["COMPLETED", "CLIENT_RESPONSIBLE"].includes(
                              item.state,
                            )
                              ? item.state === "COMPLETED"
                                ? "COMPLETE"
                                : "CLIENT_RESPONSIBILITY"
                              : item.state
                          }
                          onChange={(event) =>
                            update({ state: event.target.value })
                          }
                          sx={{ minWidth: 180 }}
                        >
                          <MenuItem value="COMPLETE">Done</MenuItem>
                          <MenuItem value="NEED_ATTENTION">
                            Needs Attention
                          </MenuItem>
                          <MenuItem value="CLIENT_RESPONSIBILITY">
                            Client Action
                          </MenuItem>
                        </TextField>
                        <TextField
                          size="small"
                          fullWidth
                          label="Path or URL"
                          value={item.resource_path}
                          onChange={(event) =>
                            update({ resource_path: event.target.value })
                          }
                          helperText="The previous event path is reused; change it when needed."
                        />
                        <TextField
                          size="small"
                          type="date"
                          label="Check date"
                          value={item.check_date}
                          onChange={(event) =>
                            update({ check_date: event.target.value })
                          }
                          slotProps={{ inputLabel: { shrink: true } }}
                        />
                      </Stack>
                      {(item.evidence_required ||
                        item.state === "CLIENT_RESPONSIBILITY") && (
                        <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                          {item.evidence_type === "FILE" ||
                          item.state === "CLIENT_RESPONSIBILITY" ? (
                            <Button component="label" variant="outlined">
                              {item.evidence_file?.name ??
                                "Choose evidence file"}
                              <input
                                hidden
                                type="file"
                                onChange={(event) =>
                                  update({
                                    evidence_file:
                                      event.target.files?.[0] ?? null,
                                  })
                                }
                              />
                            </Button>
                          ) : null}
                          {item.state === "CLIENT_RESPONSIBILITY" && (
                            <TextField
                              size="small"
                              required
                              label="Client contact"
                              value={item.client_contact ?? ""}
                              onChange={(event) =>
                                update({ client_contact: event.target.value })
                              }
                            />
                          )}
                          {item.state === "NEED_ATTENTION" && (
                            <FormControlLabel
                              control={<Checkbox checked={Boolean(item.create_follow_up_ticket)} onChange={(event) => update({ create_follow_up_ticket: event.target.checked })} />}
                              label="Create follow-up ticket"
                            />
                          )}
                          <TextField
                            size="small"
                            fullWidth
                            required
                            label={
                              item.state === "CLIENT_RESPONSIBILITY"
                                ? "Handoff note"
                                : "Evidence or result note"
                            }
                            value={item.result_note ?? ""}
                            onChange={(event) =>
                              update({ result_note: event.target.value })
                            }
                          />
                        </Stack>
                      )}
                    </Stack>
                  </Paper>
                );
              })}
              {!monitor && (
                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  <Stack spacing={1.5}>
                    <TextField required label="Service provided" value={serviceProvided} onChange={(event) => setServiceProvided(event.target.value)} />
                    <TextField required multiline minRows={2} label="Client-visible summary" value={clientSummary} onChange={(event) => setClientSummary(event.target.value)} />
                  </Stack>
                </Paper>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setSelected(null);
              setDraftItems([]);
            }}
          >
            Close
          </Button>
          {!monitor && detail.data?.status !== "COMPLETED" && (
            <>
              <Button
                disabled={save.isPending}
                onClick={() => save.mutate({ complete: false })}
              >
                Save Draft
              </Button>
              <Button
                variant="contained"
                disabled={save.isPending}
                onClick={() => save.mutate({ complete: true })}
              >
                Save &amp; Complete Checklist
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>
      <Menu
        open={Boolean(cardMenu)}
        onClose={() => setCardMenu(null)}
        anchorReference="anchorPosition"
        anchorPosition={
          cardMenu ? { top: cardMenu.mouseY, left: cardMenu.mouseX } : undefined
        }
      >
        <MenuItem
          onClick={() => {
            if (cardMenu) void openLatest(cardMenu.schedule);
            setCardMenu(null);
          }}
        >
          Open latest event
        </MenuItem>
        <MenuItem
          disabled={!cardMenu?.schedule.last_occurrence_id}
          onClick={() => {
            if (cardMenu) void exportLatest(cardMenu.schedule);
            setCardMenu(null);
          }}
        >
          Export latest event tasks
        </MenuItem>
        <MenuItem
          disabled={!cardMenu?.schedule.last_occurrence_id}
          onClick={() => {
            if (cardMenu) void shareLatest(cardMenu.schedule);
            setCardMenu(null);
          }}
        >
          Share latest event URL
        </MenuItem>
        {monitor && (
          <MenuItem
            disabled={!cardMenu || !needsAttention(cardMenu.schedule)}
            onClick={() => {
              if (cardMenu) reminder.mutate([cardMenu.schedule.id]);
              setCardMenu(null);
            }}
          >
            Send reminder
          </MenuItem>
        )}
      </Menu>
    </Stack>
  );
}
