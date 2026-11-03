import {
  Add,
  ChevronLeft,
  ChevronRight,
  ContentCopy,
  Delete,
  DeleteSweep,
  Edit,
  ExpandMore,
  Groups,
  HomeWork,
  Today,
} from "@mui/icons-material";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  ButtonGroup,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ShiftPaintMode } from "./ShiftPaintMode";
import { InternalOperationsPage } from "./InternalOperationsPage";
import { QuickShiftDialog } from "./QuickShiftDialog";
import { SmartScheduleBuilder } from "./SmartScheduleBuilder";
import { WeeklyPlannerDialog } from "./WeeklyPlannerDialog";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { serverDateInput, serverDateTimeInput } from "../utils/serverTime";

type Shift = {
  id: number;
  shift_type_id: number;
  user_id: number;
  employee_name: string;
  shift_name: string;
  shift_color: string;
  team?: string;
  on_call_role?: string;
  work_location: "OFFICE" | "WORK_FROM_HOME" | "HYBRID";
  starts_at: string;
  ends_at: string;
  notes?: string;
  status: string;
  presence_status?: "ACTIVE" | "IDLE" | "OFFLINE" | null;
  last_seen_at?: string | null;
};
type ShiftType = {
  id: number;
  name: string;
  name_ar?: string;
  color: string;
  is_on_call: boolean;
  default_start_time: string;
  default_end_time: string;
  default_required_headcount: number;
  crosses_midnight: boolean;
};
type User = { id: number; full_name: string; department?: string };
type Operation = {
  id: number;
  title: string;
  operation_type: string;
  status: string;
  starts_at: string;
  ends_at: string;
  assignees: { id: number; full_name: string }[];
};
type Visit = {
  id: number;
  status: string;
  client_name?: string;
  window_start: string;
  window_end: string;
  assignments: {
    user_id: number;
    user_name?: string;
    starts_at: string;
    ends_at: string;
  }[];
};
type CoverageSlot = {
  id: number;
  shift_type_id: number;
  shift_type_name: string;
  department_id: number | null;
  team: string | null;
  starts_at: string;
  ends_at: string;
  timezone: string;
  required_headcount: number;
  notes: string | null;
  assigned_headcount: number;
  coverage_percent: number;
  coverage_status: "FULL" | "UNDERSTAFFED" | "UNASSIGNED" | "OVERSTAFFED";
  assigned_user_names: string[];
};
type Rotation = { id: number; name: string; is_active: boolean };
type CopyRequest = {
  source_week_start: string;
  target_week_starts: string[];
  assignment_mode: "KEEP_ENGINEERS" | "ROTATE_ENGINEERS" | "AUTO_BALANCE";
  rotation_id: number | null;
  skip_conflicts: boolean;
};
type CopyPreview = {
  preview_hash: string;
  source_count: number;
  target_week_count: number;
  ready: number;
  conflicts: number;
  unassigned: number;
  items: {
    source_shift_id: number;
    starts_at: string;
    assigned_user_name: string | null;
    status: string;
    reason: string;
  }[];
};
type ViewMode = "DAY" | "WEEK" | "MONTH" | "EMPLOYEE";

const dayKey = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
const startOfWeek = (date: Date) => {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  result.setDate(result.getDate() - ((result.getDay() + 6) % 7));
  return result;
};
const addDays = (date: Date, days: number) => {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
};
const localInput = (value: string) => serverDateTimeInput(value);

export function ShiftsPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const shiftStatus = (value: string) =>
    t(`shiftsPage.statuses.${value}`, {
      defaultValue: value.replaceAll("_", " "),
    });
  const coverageStatus = (value: string) =>
    t(`shiftsPage.coverageStatuses.${value}`, {
      defaultValue: value.replaceAll("_", " "),
    });
  const [searchParams] = useSearchParams();
  const { hasPermission, user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [quickDate, setQuickDate] = useState(dayKey(new Date()));
  const [quickTypeId, setQuickTypeId] = useState<number | undefined>();
  const [quickTeam, setQuickTeam] = useState<string | null>(null);
  const [editing, setEditing] = useState<Shift | null>(null);
  const [error, setError] = useState("");
  const [view, setView] = useState<ViewMode>(() =>
    typeof window !== "undefined" &&
    window.matchMedia?.("(max-width: 600px)").matches
      ? "EMPLOYEE"
      : "WEEK",
  );
  const [focus, setFocus] = useState(new Date());
  const [employeeId, setEmployeeId] = useState("");
  const [coverageDate, setCoverageDate] = useState<Date | null>(null);
  const [coverageCreateOpen, setCoverageCreateOpen] = useState(false);
  const [coverageBulkOpen, setCoverageBulkOpen] = useState(false);
  const [coverageSelectionMode, setCoverageSelectionMode] = useState(false);
  const [selectedCoverageDays, setSelectedCoverageDays] = useState<string[]>(
    [],
  );
  const [generatorOpen, setGeneratorOpen] = useState(false);
  const [weeklyPlannerOpen, setWeeklyPlannerOpen] = useState(false);
  const [duplicateOpen, setDuplicateOpen] = useState(false);
  const [copyMode, setCopyMode] = useState<"NEXT" | "SELECTED" | "MULTIPLE">(
    "NEXT",
  );
  const [copyAssignment, setCopyAssignment] =
    useState<CopyRequest["assignment_mode"]>("KEEP_ENGINEERS");
  const [copyRotation, setCopyRotation] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [doubleClickDate, setDoubleClickDate] = useState<string | null>(null);
  const [paintDialogOpen, setPaintDialogOpen] = useState(false);
  const [operationDialogOpen, setOperationDialogOpen] = useState(false);
  const [selectedOperation, setSelectedOperation] = useState<Operation | null>(
    null,
  );
  const [bulkUser, setBulkUser] = useState("");
  const [bulkMonth, setBulkMonth] = useState(serverDateInput().slice(0, 7));
  const [bulkType, setBulkType] = useState("");
  const [bulkStatus, setBulkStatus] = useState("");
  const [calendarFilter, setCalendarFilter] = useState<
    "ALL" | "SHIFTS" | "OPERATIONS" | "VISITS"
  >("ALL");
  const weekStart = startOfWeek(focus);
  const monthGridStart = startOfWeek(
    new Date(focus.getFullYear(), focus.getMonth(), 1),
  );
  const rangeStart =
    view === "DAY"
      ? new Date(new Date(focus).setHours(0, 0, 0, 0))
      : view === "MONTH"
        ? monthGridStart
        : weekStart;
  const rangeEnd = addDays(
    rangeStart,
    view === "DAY" ? 1 : view === "MONTH" ? 42 : 7,
  );
  const canViewShifts = hasPermission("shift.view");
  const canViewOperations =
    hasPermission("internal_operation.calendar.view") ||
    hasPermission("internal_operation.view");
  const canViewVisits = hasPermission("visit.entitlement.view");
  const shifts = useQuery({
    queryKey: [
      "shift-calendar",
      dayKey(rangeStart),
      dayKey(rangeEnd),
      view === "EMPLOYEE" ? employeeId : "",
    ],
    queryFn: async () =>
      (
        await api.get<Shift[]>("/shift-calendar", {
          params: {
            ends_after: rangeStart.toISOString(),
            starts_before: rangeEnd.toISOString(),
            user_id: view === "EMPLOYEE" && employeeId ? employeeId : undefined,
          },
        })
      ).data,
    enabled: canViewShifts,
    refetchInterval: hasPermission("shift.presence.view")
      ? 60_000
      : false,
  });
  const types = useQuery({
    queryKey: ["shift-types", language],
    queryFn: async () =>
      (await api.get<ShiftType[]>("/shift-types")).data.map((type) => ({
        ...type,
        name: getLocalizedName(type, language),
      })),
    enabled: canViewShifts,
  });
  const users = useQuery({
    queryKey: ["shift-employees"],
    queryFn: async () => (await api.get<User[]>("/shift-employees")).data,
    enabled:
      hasPermission("shift.view") ||
      hasPermission("shift.create") ||
      hasPermission("shift.assign_employee") ||
      hasPermission("shift.manage"),
  });
  const rotations = useQuery({
    queryKey: ["assignment-rotations"],
    queryFn: async () =>
      (await api.get<Rotation[]>("/assignment-rotations")).data,
    enabled: hasPermission("shift.manage"),
  });
  const operations = useQuery({
    queryKey: [
      "workforce-calendar-operations",
      dayKey(rangeStart),
      dayKey(rangeEnd),
    ],
    queryFn: async () =>
      (
        await api.get<Operation[]>("/internal-operations", {
          params: { date_from: dayKey(rangeStart), date_to: dayKey(rangeEnd) },
        })
      ).data,
    enabled: canViewOperations,
  });
  const visits = useQuery({
    queryKey: [
      "workforce-calendar-visits",
      rangeStart.toISOString(),
      rangeEnd.toISOString(),
    ],
    queryFn: async () =>
      (
        await api.get<Visit[]>("/visits/planner", {
          params: {
            ends_after: rangeStart.toISOString(),
            starts_before: rangeEnd.toISOString(),
          },
        })
      ).data,
    enabled: canViewVisits,
  });
  const coverage = useQuery({
    queryKey: [
      "shift-coverage-slots",
      rangeStart.toISOString(),
      rangeEnd.toISOString(),
    ],
    queryFn: async () =>
      (
        await api.get<CoverageSlot[]>("/shift-coverage-slots", {
          params: {
            ends_after: rangeStart.toISOString(),
            starts_before: rangeEnd.toISOString(),
          },
        })
      ).data,
    enabled: canViewShifts,
  });
  const message = (requestError: unknown) =>
    axios.isAxiosError(requestError)
      ? (requestError.response?.data?.error?.message ??
        t("shiftsPage.saveFailed"))
      : t("shiftsPage.saveFailed");
  const refreshPlanner = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["shift-calendar"] }),
      queryClient.invalidateQueries({
        queryKey: ["workforce-calendar-operations"],
      }),
      queryClient.invalidateQueries({ queryKey: ["shift-coverage-slots"] }),
      queryClient.invalidateQueries({ queryKey: ["shift-coverage-summary"] }),
    ]);
  };
  const saved = async () => {
    setOpen(false);
    setEditing(null);
    setError("");
    await refreshPlanner();
  };
  const update = useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      api.patch<Shift>(`/shifts/${editing?.id}`, data),
    onSuccess: saved,
    onError: (requestError) => setError(message(requestError)),
  });
  const remove = useMutation({
    mutationFn: async (item: Shift) => api.delete(`/shifts/${item.id}`),
    onSuccess: saved,
    onError: (requestError) => setError(message(requestError)),
  });
  const status = useMutation({
    mutationFn: async ({ item, value }: { item: Shift; value: string }) =>
      api.post(`/shifts/${item.id}/status`, {
        status: value,
        reason: `Shift ${value.toLowerCase()} from calendar`,
      }),
    onSuccess: saved,
    onError: (requestError) => setError(message(requestError)),
  });
  const copyPreview = useMutation({
    mutationFn: async (payload: CopyRequest) =>
      (await api.post<CopyPreview>("/shifts/duplicate-week/preview", payload))
        .data,
  });
  const duplicate = useMutation({
    mutationFn: async () =>
      api.post<{ created: number; skipped: number }>("/shifts/duplicate-week", {
        ...copyPreview.variables,
        preview_hash: copyPreview.data?.preview_hash,
      }),
    onSuccess: async (response) => {
      setDuplicateOpen(false);
      copyPreview.reset();
      setNotice(
        t("shiftsPage.copySuccess", {
          created: response.data.created,
          skipped: response.data.skipped,
        }),
      );
      await queryClient.invalidateQueries({ queryKey: ["shift-calendar"] });
    },
    onError: (requestError) => setError(message(requestError)),
  });
  type BulkPreview = {
    matched: number;
    protected: number;
    deletable: number;
    shift_ids: number[];
  };
  type BulkFilter = {
    user_id: number;
    starts_at: string;
    ends_at: string;
    shift_type_id?: number;
    status?: string;
  };
  const bulkFilter = (): BulkFilter => {
    const start = new Date(`${bulkMonth}-01T00:00:00`),
      end = new Date(start.getFullYear(), start.getMonth() + 1, 1);
    return {
      user_id: Number(bulkUser),
      starts_at: start.toISOString(),
      ends_at: end.toISOString(),
      shift_type_id: bulkType ? Number(bulkType) : undefined,
      status: bulkStatus || undefined,
    };
  };
  const previewBulk = useMutation({
    mutationFn: async () =>
      (await api.post<BulkPreview>("/shifts/bulk-delete/preview", bulkFilter()))
        .data,
  });
  const deleteBulk = useMutation({
    mutationFn: async (reason: string) =>
      api.post<{ deleted: number; protected: number }>("/shifts/bulk-delete", {
        ...bulkFilter(),
        expected_count: previewBulk.data?.deletable ?? 0,
        reason,
      }),
    onSuccess: async (response) => {
      setBulkOpen(false);
      previewBulk.reset();
      setNotice(
        t("shiftsPage.bulkDeleteSuccess", {
          deleted: response.data.deleted,
          protected: response.data.protected,
        }),
      );
      await queryClient.invalidateQueries({ queryKey: ["shift-calendar"] });
    },
    onError: (requestError) => setError(message(requestError)),
  });
  const createCoverage = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post<CoverageSlot>("/shift-coverage-slots", payload)).data,
    onSuccess: async () => {
      setCoverageCreateOpen(false);
      setNotice(t("shiftsPage.coverageCreated"));
      await refreshPlanner();
    },
    onError: (requestError) => setError(message(requestError)),
  });
  const deleteCoverage = useMutation({
    mutationFn: async (slot: CoverageSlot) =>
      api.delete(`/shift-coverage-slots/${slot.id}`),
    onSuccess: async () => {
      setCoverageDate(null);
      setNotice(t("shiftsPage.coverageDeleted"));
      await refreshPlanner();
    },
    onError: (requestError) => setError(message(requestError)),
  });
  const bulkDeleteCoverage = useMutation({
    mutationFn: async (reason: string) =>
      api.post<{ deleted: number }>("/shift-coverage-slots/bulk-delete", {
        slot_ids: (coverage.data ?? [])
          .filter((slot) =>
            selectedCoverageDays.includes(dayKey(new Date(slot.starts_at))),
          )
          .map((slot) => slot.id),
        reason,
      }),
    onSuccess: async (response) => {
      setCoverageBulkOpen(false);
      setCoverageSelectionMode(false);
      setSelectedCoverageDays([]);
      setNotice(
        t("shiftsPage.coverageBulkDeleted", { count: response.data.deleted }),
      );
      await refreshPlanner();
    },
    onError: (requestError) => setError(message(requestError)),
  });
  const days =
    view === "DAY"
      ? [rangeStart]
      : Array.from({ length: view === "MONTH" ? 42 : 7 }, (_, index) =>
          addDays(rangeStart, index),
        );
  const move = (direction: number) =>
    setFocus((current) =>
      view === "MONTH"
        ? new Date(current.getFullYear(), current.getMonth() + direction, 1)
        : addDays(current, direction * (view === "DAY" ? 1 : 7)),
    );
  const copyRequest = (targetDate: string, count: number): CopyRequest => {
    const first =
      copyMode === "NEXT"
        ? addDays(weekStart, 7)
        : startOfWeek(new Date(`${targetDate}T12:00:00`));
    const targets = Array.from(
      {
        length: copyMode === "MULTIPLE" ? Math.max(1, Math.min(count, 12)) : 1,
      },
      (_, index) => addDays(first, index * 7).toISOString(),
    );
    return {
      source_week_start: weekStart.toISOString(),
      target_week_starts: targets,
      assignment_mode: copyAssignment,
      rotation_id:
        copyAssignment === "ROTATE_ENGINEERS" ? Number(copyRotation) : null,
      skip_conflicts: true,
    };
  };
  const canEdit = (item: Shift) =>
    hasPermission("shift.edit.all") ||
    (hasPermission("shift.edit.own") && item.user_id === user?.id) ||
    hasPermission("shift.edit.team") ||
    hasPermission("shift.manage");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const payload = {
      ...data,
      shift_type_id: Number(data.shift_type_id),
      user_id: Number(data.user_id),
      starts_at: new Date(String(data.starts_at)).toISOString(),
      ends_at: new Date(String(data.ends_at)).toISOString(),
      work_location: data.work_location || "OFFICE",
      notes: data.notes || null,
      team: data.team || null,
      on_call_role: data.on_call_role || null,
      overlap_override_reason: data.overlap_override_reason || null,
    };
    update.mutate({ ...payload, change_reason: data.change_reason });
  }
  const canManageShiftMasters = hasPermission("shift.manage");
  useEffect(() => {
    if (
      searchParams.get("create") === "shift" &&
      (hasPermission("shift.create") || canManageShiftMasters)
    ) {
      setQuickDate(dayKey(focus));
      setOpen(true);
    }
    if (searchParams.get("create") === "generate" && canManageShiftMasters)
      setGeneratorOpen(true);
  }, [searchParams, hasPermission, canManageShiftMasters, focus]);
  const openQuick = (date: Date) => {
    setQuickDate(dayKey(date));
    setQuickTypeId(undefined);
    setQuickTeam(null);
    setError("");
    setOpen(true);
  };
  const assignCoverage = (slot: CoverageSlot) => {
    setCoverageDate(null);
    setQuickDate(dayKey(new Date(slot.starts_at)));
    setQuickTypeId(slot.shift_type_id);
    setQuickTeam(slot.team);
    setError("");
    setOpen(true);
  };
  const toggleCoverageDay = (key: string) =>
    setSelectedCoverageDays((current) =>
      current.includes(key)
        ? current.filter((value) => value !== key)
        : [...current, key],
    );
  const workspaceHeader = (
    <Paper
      sx={{
        p: 2.5,
        background: "linear-gradient(120deg,#123b67,#6a1b9a)",
        color: "white",
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ md: "center" }}
        gap={1.5}
      >
        <Box flexGrow={1}>
          <Typography variant="h4" fontWeight={800}>
            {t("shiftsPage.title")}
          </Typography>
          <Typography sx={{ opacity: 0.82 }}>
            {t("shiftsPage.subtitle")}
          </Typography>
        </Box>
        {(hasPermission("shift.create") || canManageShiftMasters) && (
          <Button
            variant="contained"
            color="inherit"
            sx={{ color: "#123b67" }}
            startIcon={<Add />}
            onClick={() => openQuick(focus)}
          >
            {t("shiftsPage.create")}
          </Button>
        )}
      </Stack>
    </Paper>
  );
  const shiftCard = (item: Shift) => (
    <Paper
      key={item.id}
      variant="outlined"
      sx={{
        p: 1,
        mb: 0.75,
        borderLeft: `5px solid ${item.shift_color}`,
        bgcolor: `${item.shift_color}10`,
      }}
    >
      <Stack direction="row" gap={0.5}>
        <Box flexGrow={1}>
          <Typography fontWeight={800} variant="body2">
            {item.employee_name}
          </Typography>
          <Typography variant="caption" display="block">
            {item.shift_name} ·{" "}
            {new Date(item.starts_at).toLocaleTimeString(
              i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
              { hour: "2-digit", minute: "2-digit" },
            )}
            –
            {new Date(item.ends_at).toLocaleTimeString(
              i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
              { hour: "2-digit", minute: "2-digit" },
            )}
          </Typography>
        </Box>
        {canEdit(item) && (
          <Button
            size="small"
            aria-label={t("shiftsPage.editShift")}
            onClick={() => {
              setError("");
              setEditing(item);
            }}
          >
            <Edit fontSize="small" />
          </Button>
        )}
      </Stack>
      <Stack direction="row" gap={0.5} mt={0.5} flexWrap="wrap">
        <Chip size="small" label={shiftStatus(item.status)} />
        {item.presence_status &&
          Date.now() >= new Date(item.starts_at).getTime() &&
          Date.now() <= new Date(item.ends_at).getTime() && (
            <Chip
              size="small"
              variant={item.presence_status === "OFFLINE" ? "outlined" : "filled"}
              color={
                item.presence_status === "ACTIVE"
                  ? "success"
                  : item.presence_status === "IDLE"
                    ? "warning"
                    : "default"
              }
              label={t(`shiftsPage.presence.${item.presence_status}`)}
              title={
                item.last_seen_at
                  ? t("shiftsPage.lastActivity", {
                      time: new Date(item.last_seen_at).toLocaleString(
                        i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                      ),
                    })
                  : t("shiftsPage.noRecentActivity")
              }
            />
          )}
        {item.work_location !== "OFFICE" && (
          <Chip
            size="small"
            icon={<HomeWork />}
            color="info"
            label={
              item.work_location === "WORK_FROM_HOME"
                ? t("shiftsPage.wfh")
                : t("shiftsPage.hybrid")
            }
          />
        )}
        {(item.team || item.on_call_role) && (
          <Chip size="small" label={item.on_call_role ?? item.team} />
        )}
      </Stack>
    </Paper>
  );
  const operationCard = (item: Operation) => (
    <Paper
      key={`operation-${item.id}`}
      data-calendar-card
      role="button"
      tabIndex={0}
      variant="outlined"
      onDoubleClick={(event) => {
        event.stopPropagation();
        setSelectedOperation(item);
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          setSelectedOperation(item);
        }
      }}
      sx={{
        p: 1,
        mb: 0.75,
        borderLeft: "5px solid #7b1fa2",
        bgcolor: "#7b1fa210",
        cursor: "pointer",
        "&:hover": { boxShadow: 2 },
      }}
    >
      <Typography fontWeight={800} variant="body2">
        {item.title}
      </Typography>
      <Typography variant="caption">
        {item.operation_type.replaceAll("_", " ")} ·{" "}
        {new Date(item.starts_at).toLocaleTimeString(
          i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
          { hour: "2-digit", minute: "2-digit" },
        )}
        –
        {new Date(item.ends_at).toLocaleTimeString(
          i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
          { hour: "2-digit", minute: "2-digit" },
        )}
      </Typography>
      <Stack direction="row" gap={0.5} alignItems="center" mt={0.5}>
        <Groups sx={{ fontSize: 16 }} color="action" />
        <Typography
          variant="caption"
          display="block"
          fontWeight={700}
          color={
            (item.assignees?.length ?? 0) ? "text.primary" : "warning.main"
          }
        >
          {(item.assignees?.length ?? 0)
            ? item.assignees.map((row) => row.full_name).join(", ")
            : t("internalOperations.unassigned", {
                defaultValue: "Unassigned",
              })}
        </Typography>
      </Stack>
    </Paper>
  );
  const visitCard = (item: Visit) => (
    <Paper
      key={`visit-${item.id}`}
      variant="outlined"
      sx={{
        p: 1,
        mb: 0.75,
        borderLeft: "5px solid #ef6c00",
        bgcolor: "#ef6c0010",
      }}
    >
      <Typography fontWeight={800} variant="body2">
        {t("shiftsPage.fieldVisit")} ·{" "}
        {item.client_name ?? t("shiftsPage.visitNumber", { id: item.id })}
      </Typography>
      <Typography variant="caption">
        {item.assignments
          .map(
            (row) =>
              row.user_name ??
              t("shiftsPage.engineerNumber", { id: row.user_id }),
          )
          .join(", ")}
      </Typography>
    </Paper>
  );
  return (
    <Stack spacing={2}>
      {workspaceHeader}
      {canManageShiftMasters && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography fontWeight={800}>
              {t("shiftsPage.moreTools")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1} mb={1}>
              <Button
                startIcon={<ContentCopy />}
                onClick={() => setWeeklyPlannerOpen(true)}
              >
                Weekly Planner
              </Button>
              <Button
                startIcon={<ContentCopy />}
                onClick={() => setGeneratorOpen(true)}
              >
                {t("shiftsPage.generateShifts")}
              </Button>
              <Button
                startIcon={<ContentCopy />}
                onClick={() => setDuplicateOpen(true)}
              >
                {t("shiftsPage.copyWeek")}
              </Button>
              {hasPermission("shift.delete") && (
                <Button
                  color="error"
                  startIcon={<DeleteSweep />}
                  onClick={() => setBulkOpen(true)}
                >
                  {t("shiftsPage.bulkDelete")}
                </Button>
              )}
            </Stack>
            <ShiftPaintMode />
          </AccordionDetails>
        </Accordion>
      )}
      <Paper sx={{ p: 2 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          alignItems={{ md: "center" }}
          gap={1.5}
        >
          <ButtonGroup>
            <Button
              variant={view === "DAY" ? "contained" : "outlined"}
              onClick={() => setView("DAY")}
            >
              {t("shiftsPage.day")}
            </Button>
            <Button
              variant={view === "WEEK" ? "contained" : "outlined"}
              onClick={() => setView("WEEK")}
            >
              {t("shiftsPage.week")}
            </Button>
            <Button
              variant={view === "MONTH" ? "contained" : "outlined"}
              onClick={() => setView("MONTH")}
            >
              {t("shiftsPage.month")}
            </Button>
            <Button
              variant={view === "EMPLOYEE" ? "contained" : "outlined"}
              onClick={() => setView("EMPLOYEE")}
            >
              {t("shiftsPage.agenda")}
            </Button>
          </ButtonGroup>
          <ButtonGroup>
            <Button
              aria-label={t("shiftsPage.previousPeriod")}
              onClick={() => move(-1)}
            >
              <ChevronLeft />
            </Button>
            <Button startIcon={<Today />} onClick={() => setFocus(new Date())}>
              {t("shiftsPage.today")}
            </Button>
            <Button
              aria-label={t("shiftsPage.nextPeriod")}
              onClick={() => move(1)}
            >
              <ChevronRight />
            </Button>
          </ButtonGroup>
          {view === "EMPLOYEE" && (
            <TextField
              select
              size="small"
              label={t("shiftsPage.engineer")}
              value={employeeId}
              onChange={(event) => setEmployeeId(event.target.value)}
              sx={{ minWidth: 220 }}
            >
              <MenuItem value="">{t("shiftsPage.allEngineers")}</MenuItem>
              {users.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.full_name}
                </MenuItem>
              ))}
            </TextField>
          )}
          <Typography fontWeight={700} sx={{ ml: { md: "auto" } }}>
            {view === "DAY"
              ? focus.toLocaleDateString(
                  i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                  { dateStyle: "full" },
                )
              : view === "MONTH"
                ? focus.toLocaleDateString(
                    i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                    { month: "long", year: "numeric" },
                  )
                : `${weekStart.toLocaleDateString(i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB")} — ${addDays(weekStart, 6).toLocaleDateString(i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB")}`}
          </Typography>
        </Stack>
      </Paper>
      <Paper sx={{ p: 2 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={1}
          alignItems={{ md: "center" }}
        >
          <Typography fontWeight={900}>
            {t("shiftsPage.calendarContent")}
          </Typography>
          <TextField
            select
            size="small"
            value={calendarFilter}
            onChange={(event) =>
              setCalendarFilter(event.target.value as typeof calendarFilter)
            }
            sx={{ minWidth: 220 }}
          >
            <MenuItem value="ALL">{t("shiftsPage.allSources")}</MenuItem>
            {canViewShifts && (
              <MenuItem value="SHIFTS">{t("shiftsPage.shiftsOnly")}</MenuItem>
            )}
            {canViewOperations && (
              <MenuItem value="OPERATIONS">
                {t("shiftsPage.operationsOnly")}
              </MenuItem>
            )}
            {canViewVisits && (
              <MenuItem value="VISITS">{t("shiftsPage.visitsOnly")}</MenuItem>
            )}
          </TextField>
          {canManageShiftMasters && (
            <>
              <Button
                size="small"
                variant={coverageSelectionMode ? "contained" : "outlined"}
                onClick={() => {
                  setCoverageSelectionMode((value) => !value);
                  setSelectedCoverageDays([]);
                }}
              >
                {t("shiftsPage.selectCoverageDays")}
              </Button>
              {coverageSelectionMode && (
                <Button
                  size="small"
                  color="error"
                  disabled={!selectedCoverageDays.length}
                  onClick={() => setCoverageBulkOpen(true)}
                >
                  {t("shiftsPage.deleteCoverageDays", {
                    count: selectedCoverageDays.length,
                  })}
                </Button>
              )}
            </>
          )}
          <Stack direction="row" gap={1} ml={{ md: "auto" }}>
            {canViewShifts && (
              <Chip
                sx={{ borderLeft: "5px solid #145da0" }}
                label={t("shiftsPage.shift")}
              />
            )}{" "}
            {canViewOperations && (
              <Chip
                sx={{ borderLeft: "5px solid #7b1fa2" }}
                label={t("shiftsPage.internalOperation")}
              />
            )}{" "}
            {canViewVisits && (
              <Chip
                sx={{ borderLeft: "5px solid #ef6c00" }}
                label={t("shiftsPage.fieldVisit")}
              />
            )}
          </Stack>
        </Stack>
      </Paper>
      {(shifts.isError || operations.isError || visits.isError) && (
        <Alert severity="warning">{t("shiftsPage.sourceFailed")}</Alert>
      )}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns:
            view === "DAY"
              ? "1fr"
              : { xs: "1fr", md: "repeat(7,minmax(130px,1fr))" },
          gap: 1,
        }}
      >
        {days.map((day) => {
          const dayStart = new Date(day);
          dayStart.setHours(0, 0, 0, 0);
          const dayEnd = addDays(dayStart, 1);
          const rows = (shifts.data ?? []).filter(
            (item) =>
              new Date(item.starts_at) < dayEnd &&
              new Date(item.ends_at) > dayStart,
          );
          const operationRows = (operations.data ?? []).filter(
            (item) =>
              new Date(item.starts_at) < dayEnd &&
              new Date(item.ends_at) > dayStart,
          );
          const visitRows = (visits.data ?? []).filter((item) =>
            item.assignments.some(
              (row) =>
                new Date(row.starts_at) < dayEnd &&
                new Date(row.ends_at) > dayStart,
            ),
          );
          const coverageRows = (coverage.data ?? []).filter(
              (item) =>
                new Date(item.starts_at) < dayEnd &&
                new Date(item.ends_at) > dayStart,
            ),
            required = coverageRows.reduce(
              (sum, row) => sum + row.required_headcount,
              0,
            ),
            assigned = coverageRows.reduce(
              (sum, row) =>
                sum + Math.min(row.assigned_headcount, row.required_headcount),
              0,
            ),
            coveragePercent = required
              ? Math.round((assigned * 100) / required)
              : 100;
          const count =
            (calendarFilter === "ALL" || calendarFilter === "SHIFTS"
              ? rows.length
              : 0) +
            (calendarFilter === "ALL" || calendarFilter === "OPERATIONS"
              ? operationRows.length
              : 0) +
            (calendarFilter === "ALL" || calendarFilter === "VISITS"
              ? visitRows.length
              : 0);
          const coverageDaySelected = selectedCoverageDays.includes(
            dayKey(day),
          );
          return (
            <Paper
              key={dayKey(day)}
              onDoubleClick={(event) => {
                if (
                  event.target === event.currentTarget ||
                  (event.target as HTMLElement).closest(
                    "[data-calendar-card]",
                  ) === null
                ) {
                  setDoubleClickDate(dayKey(day));
                }
              }}
              sx={{
                minHeight: view === "DAY" ? 400 : view === "MONTH" ? 150 : 260,
                p: 1.25,
                opacity:
                  view === "MONTH" && day.getMonth() !== focus.getMonth()
                    ? 0.55
                    : 1,
                outline: coverageDaySelected ? "2px solid #d32f2f" : undefined,
              }}
            >
              <Stack direction="row" alignItems="center" mb={1}>
                <Typography fontWeight={800} flexGrow={1}>
                  {day.toLocaleDateString(
                    i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                    { weekday: "short", day: "numeric" },
                  )}
                </Typography>
                {canManageShiftMasters &&
                  coverageSelectionMode &&
                  coverageRows.length > 0 && (
                    <Button
                      size="small"
                      color={coverageDaySelected ? "error" : "inherit"}
                      onClick={() => toggleCoverageDay(dayKey(day))}
                    >
                      {coverageDaySelected
                        ? t("shiftsPage.selected")
                        : t("shiftsPage.select")}
                    </Button>
                  )}
              </Stack>
              {canViewShifts && coverageRows.length > 0 && (
                <Paper
                  component="button"
                  type="button"
                  variant="outlined"
                  onClick={() => setCoverageDate(dayStart)}
                  sx={{
                    p: 0.75,
                    mb: 1,
                    width: "100%",
                    textAlign: "left",
                    cursor: "pointer",
                    borderColor:
                      coveragePercent < 100 ? "warning.main" : "success.main",
                    bgcolor:
                      coveragePercent < 100 ? "warning.50" : "success.50",
                  }}
                >
                  <Typography variant="caption" fontWeight={900}>
                    {t("shiftsPage.coverage")} {assigned}/{required} ·{" "}
                    {coveragePercent}%
                  </Typography>
                  <Stack direction="row" gap={0.5} mt={0.5} flexWrap="wrap">
                    {coverageRows.map((slot) => (
                      <Chip
                        key={slot.id}
                        size="small"
                        color={
                          slot.coverage_status === "FULL"
                            ? "success"
                            : slot.coverage_status === "OVERSTAFFED"
                              ? "info"
                              : slot.coverage_status === "UNDERSTAFFED"
                                ? "warning"
                                : "error"
                        }
                        label={`${slot.shift_type_name} ${slot.assigned_headcount}/${slot.required_headcount}`}
                      />
                    ))}
                  </Stack>
                </Paper>
              )}
              {(calendarFilter === "ALL" || calendarFilter === "SHIFTS") &&
                rows.map(shiftCard)}
              {(calendarFilter === "ALL" || calendarFilter === "OPERATIONS") &&
                operationRows.map(operationCard)}
              {(calendarFilter === "ALL" || calendarFilter === "VISITS") &&
                visitRows.map(visitCard)}
              {!count && !coverageRows.length && (
                <Typography variant="caption" color="text.secondary">
                  {t("shiftsPage.noScheduledActivity")}
                </Typography>
              )}
            </Paper>
          );
        })}
      </Box>
      <Dialog
        open={selectedOperation !== null}
        onClose={() => setSelectedOperation(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {selectedOperation?.title ?? t("internalOperations.details")}
        </DialogTitle>
        <DialogContent dividers>
          {selectedOperation && (
            <Stack spacing={2}>
              <Stack direction="row" gap={0.75} flexWrap="wrap">
                <Chip
                  color="secondary"
                  label={selectedOperation.operation_type.replaceAll("_", " ")}
                />
                <Chip label={shiftStatus(selectedOperation.status)} />
              </Stack>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  {t("internalOperations.schedule", {
                    defaultValue: "Schedule",
                  })}
                </Typography>
                <Typography>
                  {new Date(selectedOperation.starts_at).toLocaleString(
                    i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                  )}
                  {" – "}
                  {new Date(selectedOperation.ends_at).toLocaleString(
                    i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                  )}
                </Typography>
              </Box>
              <Box>
                <Stack direction="row" gap={0.75} alignItems="center" mb={1}>
                  <Groups color="primary" />
                  <Typography fontWeight={800}>
                    {t("internalOperations.assignedEngineers", {
                      defaultValue: "Assigned engineers",
                    })}
                  </Typography>
                </Stack>
                <Stack direction="row" gap={0.75} flexWrap="wrap">
                  {(selectedOperation.assignees?.length ?? 0) ? (
                    selectedOperation.assignees.map((engineer) => (
                      <Chip
                        key={engineer.id}
                        label={engineer.full_name}
                        color="primary"
                        variant="outlined"
                      />
                    ))
                  ) : (
                    <Alert severity="warning" sx={{ width: "100%" }}>
                      {t("internalOperations.unassigned", {
                        defaultValue: "No engineers are assigned",
                      })}
                    </Alert>
                  )}
                </Stack>
              </Box>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedOperation(null)}>
            {t("common.actions.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={
          Boolean(doubleClickDate) && !paintDialogOpen && !operationDialogOpen
        }
        onClose={() => setDoubleClickDate(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>
          {t("shiftsPage.calendarActions", {
            defaultValue: "Calendar actions",
          })}{" "}
          · {doubleClickDate}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} mt={1}>
            {(hasPermission("internal_operation.create") ||
              hasPermission("internal_operation.manage")) && (
              <Button
                variant="contained"
                onClick={() => setOperationDialogOpen(true)}
              >
                {t("internalOperations.createTitle")}
              </Button>
            )}
            {(hasPermission("shift.create") || canManageShiftMasters) && (
              <Button
                variant="outlined"
                onClick={() => setPaintDialogOpen(true)}
              >
                {t("shiftPaint.title")}
              </Button>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDoubleClickDate(null)}>
            {t("common.actions.cancel")}
          </Button>
        </DialogActions>
      </Dialog>
      {operationDialogOpen && doubleClickDate && (
        <InternalOperationsPage
          dialogOnly
          initialCreateDate={doubleClickDate}
          onCreated={refreshPlanner}
          onClose={() => {
            setOperationDialogOpen(false);
            setDoubleClickDate(null);
          }}
        />
      )}
      <Dialog
        open={paintDialogOpen}
        onClose={() => {
          setPaintDialogOpen(false);
          setDoubleClickDate(null);
        }}
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle>
          {t("shiftPaint.title")} · {doubleClickDate}
        </DialogTitle>
        <DialogContent dividers>
          {doubleClickDate && (
            <ShiftPaintMode
              initialDate={doubleClickDate}
              defaultExpanded
              onApplied={() => {
                setPaintDialogOpen(false);
                setDoubleClickDate(null);
                void refreshPlanner();
              }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setPaintDialogOpen(false);
              setDoubleClickDate(null);
            }}
          >
            {t("common.actions.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(coverageDate)}
        onClose={() => setCoverageDate(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {t("shiftsPage.coverageDetails")} ·{" "}
          {coverageDate?.toLocaleDateString(
            i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
          )}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={1}>
            {(coverage.data ?? [])
              .filter(
                (slot) =>
                  coverageDate &&
                  new Date(slot.starts_at) < addDays(coverageDate, 1) &&
                  new Date(slot.ends_at) > coverageDate,
              )
              .map((slot) => (
                <Paper
                  key={slot.id}
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    borderLeft: `5px solid ${slot.coverage_status === "FULL" ? "#2e7d32" : slot.coverage_status === "OVERSTAFFED" ? "#0288d1" : slot.coverage_status === "UNDERSTAFFED" ? "#ed6c02" : "#d32f2f"}`,
                  }}
                >
                  <Stack direction="row">
                    <Box flex={1}>
                      <Typography fontWeight={900}>
                        {slot.shift_type_name}
                      </Typography>
                      <Typography variant="body2">
                        {new Date(slot.starts_at).toLocaleTimeString(
                          i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                          { hour: "2-digit", minute: "2-digit" },
                        )}
                        –
                        {new Date(slot.ends_at).toLocaleTimeString(
                          i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                          { hour: "2-digit", minute: "2-digit" },
                        )}
                      </Typography>
                    </Box>
                    <Stack direction="row" gap={0.5} alignItems="center">
                      <Chip
                        label={`${slot.assigned_headcount}/${slot.required_headcount} · ${coverageStatus(slot.coverage_status)}`}
                      />
                      {canManageShiftMasters && (
                        <Button
                          size="small"
                          color="error"
                          disabled={deleteCoverage.isPending}
                          onClick={() => {
                            if (
                              window.confirm(
                                t("shiftsPage.deleteCoverageConfirm"),
                              )
                            ) {
                              deleteCoverage.mutate(slot);
                            }
                          }}
                        >
                          <Delete fontSize="small" />
                        </Button>
                      )}
                    </Stack>
                  </Stack>
                  <Typography variant="body2" color="text.secondary" mt={0.5}>
                    {slot.assigned_user_names.join(", ") ||
                      t("shiftsPage.noAssignedEngineers")}
                  </Typography>
                  {slot.assigned_headcount < slot.required_headcount &&
                    (hasPermission("shift.create") ||
                      canManageShiftMasters) && (
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<Add />}
                        sx={{ mt: 1 }}
                        onClick={() => assignCoverage(slot)}
                      >
                        {t("shiftsPage.assignEngineers", {
                          count:
                            slot.required_headcount - slot.assigned_headcount,
                        })}
                      </Button>
                    )}
                </Paper>
              ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          {canManageShiftMasters && (
            <Button
              startIcon={<Add />}
              onClick={() => setCoverageCreateOpen(true)}
            >
              {t("shiftsPage.createCoverage")}
            </Button>
          )}
          <Button onClick={() => setCoverageDate(null)}>
            {t("shiftsPage.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={coverageCreateOpen}
        onClose={() => setCoverageCreateOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            const date = String(values.date);
            const starts = new Date(`${date}T${String(values.starts_at)}`);
            let ends = new Date(`${date}T${String(values.ends_at)}`);
            if (ends <= starts) ends = addDays(ends, 1);
            createCoverage.mutate({
              shift_type_id: Number(values.shift_type_id),
              starts_at: starts.toISOString(),
              ends_at: ends.toISOString(),
              timezone: "Africa/Cairo",
              required_headcount: Number(values.required_headcount),
              team: String(values.team).trim() || null,
              notes: String(values.notes).trim() || null,
            });
          }}
        >
          <DialogTitle>{t("shiftsPage.createCoverage")}</DialogTitle>
          <DialogContent>
            <Alert severity="info" sx={{ mb: 2 }}>
              {t("shiftsPage.emptyCoverageHint")}
            </Alert>
            <TextField
              required
              select
              fullWidth
              name="shift_type_id"
              label={t("shiftsPage.shiftType")}
              defaultValue={types.data?.[0]?.id ?? ""}
              margin="normal"
            >
              {types.data?.map((type) => (
                <MenuItem key={type.id} value={type.id}>
                  {type.name}
                </MenuItem>
              ))}
            </TextField>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                required
                fullWidth
                name="date"
                type="date"
                label={t("shiftsPage.date")}
                defaultValue={dayKey(coverageDate ?? focus)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                required
                fullWidth
                name="required_headcount"
                type="number"
                label={t("shiftsPage.requiredEngineers")}
                defaultValue={1}
                inputProps={{ min: 1, max: 100 }}
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1} mt={1}>
              <TextField
                required
                fullWidth
                name="starts_at"
                type="time"
                label={t("shiftsPage.starts")}
                defaultValue={types.data?.[0]?.default_start_time ?? "09:00"}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                required
                fullWidth
                name="ends_at"
                type="time"
                label={t("shiftsPage.ends")}
                defaultValue={types.data?.[0]?.default_end_time ?? "17:00"}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
            <TextField
              fullWidth
              name="team"
              label={t("shiftsPage.team")}
              margin="normal"
            />
            <TextField
              fullWidth
              name="notes"
              label={t("shiftsPage.notes")}
              margin="normal"
              multiline
              minRows={2}
            />
            {createCoverage.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {message(createCoverage.error)}
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCoverageCreateOpen(false)}>
              {t("shiftsPage.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createCoverage.isPending}
            >
              {t("shiftsPage.createCoverage")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={coverageBulkOpen}
        onClose={() => setCoverageBulkOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            bulkDeleteCoverage.mutate(
              String(new FormData(event.currentTarget).get("reason") ?? ""),
            );
          }}
        >
          <DialogTitle>
            {t("shiftsPage.deleteCoverageDays", {
              count: selectedCoverageDays.length,
            })}
          </DialogTitle>
          <DialogContent>
            <Alert severity="warning">
              {t("shiftsPage.coverageBulkDeleteHint")}
            </Alert>
            <TextField
              required
              fullWidth
              name="reason"
              label={t("shiftsPage.deletionReason")}
              margin="normal"
              inputProps={{ minLength: 5 }}
            />
            {bulkDeleteCoverage.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {message(bulkDeleteCoverage.error)}
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCoverageBulkOpen(false)}>
              {t("shiftsPage.cancel")}
            </Button>
            <Button
              type="submit"
              color="error"
              variant="contained"
              disabled={bulkDeleteCoverage.isPending}
            >
              {t("shiftsPage.deleteCoverageDays", {
                count: selectedCoverageDays.length,
              })}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={generatorOpen}
        onClose={() => setGeneratorOpen(false)}
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle>{t("shiftsPage.generateShifts")}</DialogTitle>
        <DialogContent dividers>
          <SmartScheduleBuilder onApplied={() => setGeneratorOpen(false)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGeneratorOpen(false)}>
            {t("shiftsPage.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <WeeklyPlannerDialog
        open={weeklyPlannerOpen}
        onClose={() => setWeeklyPlannerOpen(false)}
      />
      <QuickShiftDialog
        key={`${quickDate}-${quickTypeId ?? "new"}-${quickTeam ?? ""}`}
        open={open}
        initialDate={quickDate}
        initialShiftTypeId={quickTypeId}
        initialTeam={quickTeam}
        onClose={() => setOpen(false)}
      />
      <Dialog
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        fullWidth
        maxWidth="sm"
      >
        <form key={editing?.id} onSubmit={submit}>
          <DialogTitle>{t("shiftsPage.editShift")}</DialogTitle>
          <DialogContent>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              select
              required
              name="user_id"
              label={t("shiftsPage.employee")}
              fullWidth
              margin="normal"
              defaultValue={editing?.user_id ?? user?.id ?? ""}
              disabled={
                !hasPermission("shift.assign_employee") &&
                !hasPermission("shift.manage")
              }
            >
              {users.data?.map((x) => (
                <MenuItem key={x.id} value={x.id}>
                  {x.full_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              required
              name="shift_type_id"
              label={t("shiftsPage.shiftType")}
              fullWidth
              margin="normal"
              defaultValue={editing?.shift_type_id ?? ""}
            >
              {types.data?.map((x) => (
                <MenuItem key={x.id} value={x.id}>
                  {x.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              required
              name="work_location"
              label={t("shiftsPage.workLocation")}
              fullWidth
              margin="normal"
              defaultValue={editing?.work_location ?? "OFFICE"}
            >
              <MenuItem value="OFFICE">{t("shiftsPage.office")}</MenuItem>
              <MenuItem value="WORK_FROM_HOME">
                {t("shiftsPage.workFromHome")}
              </MenuItem>
              <MenuItem value="HYBRID">{t("shiftsPage.hybrid")}</MenuItem>
            </TextField>
            <TextField
              type="datetime-local"
              required
              name="starts_at"
              label={t("shiftsPage.starts")}
              defaultValue={editing ? localInput(editing.starts_at) : ""}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              type="datetime-local"
              required
              name="ends_at"
              label={t("shiftsPage.ends")}
              defaultValue={editing ? localInput(editing.ends_at) : ""}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              name="team"
              label={t("shiftsPage.team")}
              defaultValue={editing?.team ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              select
              name="on_call_role"
              label={t("shiftsPage.onCallRole")}
              fullWidth
              margin="normal"
              defaultValue={editing?.on_call_role ?? ""}
            >
              <MenuItem value="">{t("shiftsPage.none")}</MenuItem>
              <MenuItem value="PRIMARY">{t("shiftsPage.primary")}</MenuItem>
              <MenuItem value="BACKUP">{t("shiftsPage.backup")}</MenuItem>
            </TextField>
            <TextField
              name="notes"
              label={t("shiftsPage.notes")}
              defaultValue={editing?.notes ?? ""}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <TextField
              name="overlap_override_reason"
              label={t("shiftsPage.overlapReason")}
              fullWidth
              margin="normal"
            />
            <TextField
              required
              name="change_reason"
              label={t("shiftsPage.changeReason")}
              inputProps={{ minLength: 5 }}
              fullWidth
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            {hasPermission("shift.delete") && (
              <Button
                color="error"
                startIcon={<Delete />}
                disabled={remove.isPending}
                onClick={() => setDeleteOpen(true)}
              >
                {remove.isPending
                  ? t("shiftsPage.deleting")
                  : t("shiftsPage.deleteShift")}
              </Button>
            )}
            {(hasPermission("shift.publish") ||
              hasPermission("shift.manage")) &&
              editing?.status === "DRAFT" && (
                <Button
                  onClick={() =>
                    editing &&
                    status.mutate({ item: editing, value: "PUBLISHED" })
                  }
                >
                  {t("shiftsPage.publish")}
                </Button>
              )}
            {hasPermission("shift.approve") &&
              editing?.status === "PUBLISHED" && (
                <Button
                  onClick={() =>
                    editing &&
                    status.mutate({ item: editing, value: "APPROVED" })
                  }
                >
                  {t("shiftsPage.approve")}
                </Button>
              )}
            <Button onClick={() => setEditing(null)}>
              {t("shiftsPage.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={update.isPending || remove.isPending}
            >
              {t("shiftsPage.save")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)}>
        <DialogTitle>{t("shiftsPage.deleteConfirm")}</DialogTitle>
        <DialogContent>
          <Typography>
            {editing?.employee_name} ·{" "}
            {editing &&
              new Date(editing.starts_at).toLocaleString(
                i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
              )}
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            {t("shiftsPage.deleteWarning")}
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteOpen(false)}>
            {t("shiftsPage.cancel")}
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              if (editing)
                remove.mutate(editing, {
                  onSuccess: () => setDeleteOpen(false),
                });
            }}
          >
            {t("shiftsPage.deleteShift")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={duplicateOpen}
        onClose={() => {
          setDuplicateOpen(false);
          copyPreview.reset();
        }}
        fullWidth
        maxWidth="md"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const v = Object.fromEntries(new FormData(event.currentTarget));
            copyPreview.mutate(
              copyRequest(String(v.target_date), Number(v.week_count || 1)),
            );
          }}
        >
          <DialogTitle>{t("shiftsPage.copyWeek")}</DialogTitle>
          <DialogContent>
            <Typography color="text.secondary">
              {t("shiftsPage.source")}:{" "}
              {weekStart.toLocaleDateString(
                i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
              )}{" "}
              —{" "}
              {addDays(weekStart, 6).toLocaleDateString(
                i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
              )}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                select
                label={t("shiftsPage.copyDestination")}
                value={copyMode}
                onChange={(event) => {
                  setCopyMode(event.target.value as typeof copyMode);
                  copyPreview.reset();
                }}
                fullWidth
                margin="normal"
              >
                <MenuItem value="NEXT">{t("shiftsPage.nextWeek")}</MenuItem>
                <MenuItem value="SELECTED">
                  {t("shiftsPage.selectedWeek")}
                </MenuItem>
                <MenuItem value="MULTIPLE">
                  {t("shiftsPage.multipleWeeks")}
                </MenuItem>
              </TextField>
              {copyMode !== "NEXT" && (
                <TextField
                  required
                  type="date"
                  name="target_date"
                  label={t("shiftsPage.firstTargetWeek")}
                  defaultValue={dayKey(addDays(weekStart, 7))}
                  fullWidth
                  margin="normal"
                  slotProps={{ inputLabel: { shrink: true } }}
                />
              )}{" "}
              {copyMode === "NEXT" && (
                <input
                  type="hidden"
                  name="target_date"
                  value={dayKey(addDays(weekStart, 7))}
                />
              )}{" "}
              {copyMode === "MULTIPLE" && (
                <TextField
                  required
                  type="number"
                  name="week_count"
                  label={t("shiftsPage.numberOfWeeks")}
                  defaultValue={2}
                  inputProps={{ min: 1, max: 12 }}
                  fullWidth
                  margin="normal"
                />
              )}
            </Stack>
            <TextField
              select
              label={t("shiftsPage.assignmentMode")}
              value={copyAssignment}
              onChange={(event) => {
                setCopyAssignment(
                  event.target.value as CopyRequest["assignment_mode"],
                );
                copyPreview.reset();
              }}
              fullWidth
              margin="normal"
            >
              <MenuItem value="KEEP_ENGINEERS">
                {t("shiftsPage.keepEngineers")}
              </MenuItem>
              <MenuItem value="ROTATE_ENGINEERS">
                {t("shiftsPage.rotateEngineers")}
              </MenuItem>
              <MenuItem value="AUTO_BALANCE">
                {t("shiftsPage.autoBalance")}
              </MenuItem>
            </TextField>
            {copyAssignment === "ROTATE_ENGINEERS" && (
              <TextField
                required
                select
                label={t("shiftsPage.assignmentRotation")}
                value={copyRotation}
                onChange={(event) => {
                  setCopyRotation(event.target.value);
                  copyPreview.reset();
                }}
                fullWidth
                margin="normal"
              >
                {rotations.data
                  ?.filter((row) => row.is_active)
                  .map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {row.name}
                    </MenuItem>
                  ))}
              </TextField>
            )}
            <Alert severity="info">{t("shiftsPage.copyHint")}</Alert>
            {copyPreview.data && (
              <Paper variant="outlined" sx={{ p: 1.5, mt: 1.5 }}>
                <Stack direction="row" gap={0.75} flexWrap="wrap">
                  <Chip
                    label={t("shiftsPage.sourceShifts", {
                      count: copyPreview.data.source_count,
                    })}
                  />
                  <Chip
                    label={t("shiftsPage.targetWeeks", {
                      count: copyPreview.data.target_week_count,
                    })}
                  />
                  <Chip
                    color="success"
                    label={t("shiftsPage.ready", {
                      count: copyPreview.data.ready,
                    })}
                  />
                  {copyPreview.data.conflicts > 0 && (
                    <Chip
                      color="warning"
                      label={t("shiftsPage.conflicts", {
                        count: copyPreview.data.conflicts,
                      })}
                    />
                  )}{" "}
                  {copyPreview.data.unassigned > 0 && (
                    <Chip
                      color="error"
                      label={t("shiftsPage.unassignedCount", {
                        count: copyPreview.data.unassigned,
                      })}
                    />
                  )}
                </Stack>
                {copyPreview.data.items
                  .filter((row) => row.status !== "READY")
                  .slice(0, 8)
                  .map((row) => (
                    <Typography
                      key={`${row.source_shift_id}-${row.starts_at}`}
                      variant="body2"
                      mt={0.5}
                    >
                      {new Date(row.starts_at).toLocaleString(
                        i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-GB",
                      )}{" "}
                      · {row.reason}
                    </Typography>
                  ))}
              </Paper>
            )}
            {(copyPreview.isError || duplicate.isError) && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {t("shiftsPage.copyFailed")}
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setDuplicateOpen(false);
                copyPreview.reset();
              }}
            >
              {t("shiftsPage.cancel")}
            </Button>
            <Button
              type="submit"
              variant="outlined"
              disabled={
                (copyAssignment === "ROTATE_ENGINEERS" && !copyRotation) ||
                copyPreview.isPending
              }
            >
              {t("shiftsPage.previewCopy")}
            </Button>
            <Button
              variant="contained"
              disabled={!copyPreview.data || duplicate.isPending}
              onClick={() => duplicate.mutate()}
            >
              {t("shiftsPage.copyDrafts")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={bulkOpen}
        onClose={() => {
          setBulkOpen(false);
          previewBulk.reset();
        }}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const v = Object.fromEntries(new FormData(event.currentTarget));
            deleteBulk.mutate(String(v.reason));
          }}
        >
          <DialogTitle>{t("shiftsPage.bulkDeleteTitle")}</DialogTitle>
          <DialogContent>
            <Alert severity="warning">{t("shiftsPage.bulkDeleteHint")}</Alert>
            <TextField
              select
              required
              label={t("shiftsPage.engineer")}
              value={bulkUser}
              onChange={(event) => {
                setBulkUser(event.target.value);
                previewBulk.reset();
              }}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("shiftsPage.selectEngineer")}</MenuItem>
              {users.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.full_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              required
              type="month"
              label={t("shiftsPage.month")}
              value={bulkMonth}
              onChange={(event) => {
                setBulkMonth(event.target.value);
                previewBulk.reset();
              }}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Stack direction="row" gap={1}>
              <TextField
                select
                label={t("shiftsPage.shiftType")}
                value={bulkType}
                onChange={(event) => {
                  setBulkType(event.target.value);
                  previewBulk.reset();
                }}
                fullWidth
              >
                <MenuItem value="">{t("shiftsPage.allTypes")}</MenuItem>
                {types.data?.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label={t("shiftsPage.status")}
                value={bulkStatus}
                onChange={(event) => {
                  setBulkStatus(event.target.value);
                  previewBulk.reset();
                }}
                fullWidth
              >
                <MenuItem value="">{t("shiftsPage.allStatuses")}</MenuItem>
                {[
                  "DRAFT",
                  "PUBLISHED",
                  "APPROVED",
                  "COMPLETED",
                  "CANCELLED",
                ].map((value) => (
                  <MenuItem key={value} value={value}>
                    {shiftStatus(value)}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Button
              sx={{ mt: 2 }}
              variant="outlined"
              disabled={!bulkUser || previewBulk.isPending}
              onClick={() => previewBulk.mutate()}
            >
              {t("shiftsPage.previewMatching")}
            </Button>
            {previewBulk.data && (
              <Alert
                severity={previewBulk.data.deletable ? "warning" : "info"}
                sx={{ mt: 2 }}
              >
                {t("shiftsPage.bulkSummary", {
                  matched: previewBulk.data.matched,
                  deletable: previewBulk.data.deletable,
                  protected: previewBulk.data.protected,
                })}
              </Alert>
            )}
            {previewBulk.data && previewBulk.data.deletable > 0 && (
              <TextField
                required
                name="reason"
                label={t("shiftsPage.deletionReason")}
                fullWidth
                margin="normal"
                inputProps={{ minLength: 5 }}
              />
            )}
            {(previewBulk.isError || deleteBulk.isError) && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {t("shiftsPage.bulkFailed")}
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setBulkOpen(false);
                previewBulk.reset();
              }}
            >
              {t("shiftsPage.cancel")}
            </Button>
            <Button
              type="submit"
              color="error"
              variant="contained"
              disabled={!previewBulk.data?.deletable || deleteBulk.isPending}
            >
              {t("shiftsPage.deleteCount", {
                count: previewBulk.data?.deletable ?? 0,
              })}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Snackbar
        open={Boolean(notice)}
        autoHideDuration={6000}
        onClose={() => setNotice("")}
        message={notice}
      />
    </Stack>
  );
}
