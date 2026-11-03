import { serverDateInput } from "../utils/serverTime";
import { Add, Brush, ExpandMore } from "@mui/icons-material";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { TechnicalText } from "../components/TechnicalText";
import { getLocalizedName } from "../i18n/localizedMasterData";

type Strategy =
  "MANUAL" | "FIXED" | "ROTATION" | "AUTO_BALANCE" | "KEEP_EXISTING";
type ShiftType = { id: number; name: string; name_ar?: string; default_start_time: string; default_end_time: string; default_required_headcount: number };
type Rotation = { id: number; name: string; is_active: boolean };
type Employee = { id: number; full_name: string };
type Slot = {
  slot_key: string;
  starts_at: string;
  shift_type_name: string;
  required_headcount: number;
  assigned_user_names: string[];
  unassigned_positions: number;
  coverage_status: string;
};
type Preview = {
  preview_hash: string;
  required_positions: number;
  assignable_positions: number;
  unassigned_positions: number;
  coverage_percent: number;
  workload_balance_percent: number;
  slots: Slot[];
};
type Request = {
  rows: {
    weekday: number;
    shift_type_id: number;
    start_time: string;
    end_time: string;
    required_headcount: number;
    assignment_strategy: Strategy;
    rotation_id: number | null;
    work_location: string;
  }[];
  recurrence: {
    frequency: "SPECIFIC_DATES";
    date_from: string;
    date_to: string;
    specific_dates: string[];
  };
  timezone: string;
  assignment_strategy: Strategy;
  rotation_id: number | null;
  fixed_user_ids: number[];
};
const today = () => serverDateInput();

export function ShiftPaintMode({ onApplied, initialDate, defaultExpanded = false }: { onApplied?: () => void; initialDate?: string; defaultExpanded?: boolean }) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage?.startsWith("ar") ? "ar" : "en";
  const locale = i18n.resolvedLanguage?.startsWith("ar") ? "ar-EG" : "en-US";
  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(locale, {
      weekday: "short",
      month: "short",
      day: "numeric",
    }).format(new Date(`${value}T12:00:00`));
  const formatDateTime = (value: string) =>
    new Intl.DateTimeFormat(locale, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  const formatNumber = (value: number) =>
    new Intl.NumberFormat(locale).format(value);
  const queryClient = useQueryClient();
  const [shiftTypeId, setShiftTypeId] = useState(""),
    [startTime, setStartTime] = useState("09:00"),
    [endTime, setEndTime] = useState("17:00"),
    [headcount, setHeadcount] = useState(1),
    [strategy, setStrategy] = useState<Strategy>("AUTO_BALANCE"),
    [rotationId, setRotationId] = useState(""),
    [fixedIds, setFixedIds] = useState<number[]>([]),
    [paintDate, setPaintDate] = useState(today()),
    [dates, setDates] = useState<string[]>([]),
    [snapshot, setSnapshot] = useState<Request | null>(null),
    [notice, setNotice] = useState("");
  const types = useQuery({
      queryKey: ["shift-types", language],
      queryFn: async () =>
        (await api.get<ShiftType[]>("/shift-types")).data.map((type) => ({
          ...type,
          name: getLocalizedName(type, language),
        })),
    }),
    rotations = useQuery({
      queryKey: ["assignment-rotations"],
      queryFn: async () =>
        (await api.get<Rotation[]>("/assignment-rotations")).data,
    }),
    employees = useQuery({
      queryKey: ["shift-template-users"],
      queryFn: async () => (await api.get<Employee[]>("/shift-employees")).data,
    });
  useEffect(() => {
    if (initialDate) {
      setPaintDate(initialDate);
      setDates([initialDate]);
    }
  }, [initialDate]);
  const request = useMemo<Request | null>(() => {
    if (!dates.length || !shiftTypeId) return null;
    const weekdays = [
      ...new Set(
        dates.map((date) => (new Date(`${date}T12:00:00`).getDay() + 6) % 7),
      ),
    ];
    return {
      rows: weekdays.map((weekday) => ({
        weekday,
        shift_type_id: Number(shiftTypeId),
        start_time: startTime,
        end_time: endTime,
        required_headcount: headcount,
        assignment_strategy: strategy,
        rotation_id: rotationId ? Number(rotationId) : null,
        work_location: "OFFICE",
      })),
      recurrence: {
        frequency: "SPECIFIC_DATES",
        date_from: dates[0],
        date_to: dates[dates.length - 1],
        specific_dates: dates,
      },
      timezone: "Africa/Cairo",
      assignment_strategy: strategy,
      rotation_id: rotationId ? Number(rotationId) : null,
      fixed_user_ids: fixedIds,
    };
  }, [
    dates,
    shiftTypeId,
    startTime,
    endTime,
    headcount,
    strategy,
    rotationId,
    fixedIds,
  ]);
  const preview = useMutation({
    mutationFn: async (payload: Request) =>
      (await api.post<Preview>("/shifts/generator/preview", payload)).data,
    onSuccess: (_, payload) => setSnapshot(payload),
  });
  const apply = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ batch_id: number; created_shifts: number }>(
          "/shifts/generator/apply",
          { request: snapshot, preview_hash: preview.data?.preview_hash },
        )
      ).data,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["shift-calendar"] });
      setNotice(
        t("shiftPaint.generated", {
          batch: result.batch_id,
          count: result.created_shifts,
        }),
      );
      preview.reset();
      setSnapshot(null);
      setDates([]);
      onApplied?.();
    },
  });
  const changed = Boolean(
      snapshot &&
      request &&
      JSON.stringify(snapshot) !== JSON.stringify(request),
    ),
    valid = Boolean(
      request &&
      (!(strategy === "FIXED" || strategy === "MANUAL") || fixedIds.length) &&
      (strategy !== "ROTATION" || rotationId),
    );
  function addDate() {
    if (paintDate && !dates.includes(paintDate)) {
      setDates((current) => [...current, paintDate].sort());
      preview.reset();
    }
  }
  return (
    <Accordion defaultExpanded={defaultExpanded}>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Stack direction="row" gap={1} alignItems="center">
          <Brush color="primary" />
          <Box>
            <Typography fontWeight={900}>{t("shiftPaint.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("shiftPaint.help")}
            </Typography>
          </Box>
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.5}>
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              select
              label={t("shiftPaint.shiftType")}
              value={shiftTypeId}
              onChange={(event) => {
                const selected = types.data?.find((row) => row.id === Number(event.target.value));
                setShiftTypeId(event.target.value);
                if (selected) {
                  setStartTime(selected.default_start_time.slice(0, 5));
                  setEndTime(selected.default_end_time.slice(0, 5));
                  setHeadcount(selected.default_required_headcount);
                }
                preview.reset();
              }}
              fullWidth
            >
              {types.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              type="time"
              label={t("shiftPaint.starts")}
              value={startTime}
              onChange={(event) => setStartTime(event.target.value)}
              slotProps={{
                inputLabel: { shrink: true },
                htmlInput: { dir: "ltr" },
              }}
            />
            <TextField
              type="time"
              label={t("shiftPaint.ends")}
              value={endTime}
              onChange={(event) => setEndTime(event.target.value)}
              slotProps={{
                inputLabel: { shrink: true },
                htmlInput: { dir: "ltr" },
              }}
            />
            <TextField
              type="number"
              label={t("shiftPaint.required")}
              value={headcount}
              onChange={(event) => setHeadcount(Number(event.target.value))}
              inputProps={{ min: 1, max: 100 }}
            />
            <TextField
              select
              label={t("shiftPaint.assignment")}
              value={strategy}
              onChange={(event) => setStrategy(event.target.value as Strategy)}
              sx={{ minWidth: 190 }}
            >
              {(
                [
                  "MANUAL",
                  "FIXED",
                  "ROTATION",
                  "AUTO_BALANCE",
                  "KEEP_EXISTING",
                ] as Strategy[]
              ).map((value) => (
                <MenuItem key={value} value={value}>
                  {t(`shiftPaint.strategies.${value}`)}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
          {strategy === "ROTATION" && (
            <TextField
              select
              label={t("shiftPaint.rotation")}
              value={rotationId}
              onChange={(event) => setRotationId(event.target.value)}
              fullWidth
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
          {(strategy === "FIXED" || strategy === "MANUAL") && (
            <TextField
              select
              label={t("shiftPaint.engineers")}
              value={fixedIds}
              onChange={(event) => {
                const value = event.target.value;
                setFixedIds(
                  typeof value === "string"
                    ? value.split(",").map(Number)
                    : value,
                );
              }}
              slotProps={{ select: { multiple: true } }}
              fullWidth
            >
              {employees.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.full_name}
                </MenuItem>
              ))}
            </TextField>
          )}
          <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
            <TextField
              type="date"
              label={t("shiftPaint.calendarDate")}
              value={paintDate}
              onChange={(event) => setPaintDate(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Button startIcon={<Add />} onClick={addDate}>
              {t("shiftPaint.paintDate")}
            </Button>
          </Stack>
          <Stack direction="row" gap={0.75} flexWrap="wrap">
            {dates.map((date) => (
              <Chip
                key={date}
                label={formatDate(date)}
                onDelete={() => {
                  setDates((current) =>
                    current.filter((value) => value !== date),
                  );
                  preview.reset();
                }}
              />
            ))}
            {!dates.length && (
              <Alert severity="info" sx={{ width: "100%" }}>
                {t("shiftPaint.emptyDates")}
              </Alert>
            )}
          </Stack>
          <Button
            variant="outlined"
            disabled={!valid || preview.isPending}
            onClick={() => request && preview.mutate(request)}
          >
            {t("shiftPaint.preview")}
          </Button>
          {preview.data && (
            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Stack direction="row" gap={0.75} flexWrap="wrap">
                <Chip
                  label={t("shiftPaint.coverage", {
                    value: formatNumber(preview.data.coverage_percent),
                  })}
                  color={
                    preview.data.unassigned_positions ? "warning" : "success"
                  }
                />
                <Chip
                  label={t("shiftPaint.assigned", {
                    assigned: formatNumber(preview.data.assignable_positions),
                    required: formatNumber(preview.data.required_positions),
                  })}
                />
                <Chip
                  label={t("shiftPaint.balance", {
                    value: formatNumber(preview.data.workload_balance_percent),
                  })}
                />
              </Stack>
              {preview.data.slots.map((slot) => (
                <Typography key={slot.slot_key} variant="body2" mt={0.75}>
                  <TechnicalText component="b">
                    {formatDateTime(slot.starts_at)}
                  </TechnicalText>{" "}
                  ·{" "}
                  {slot.assigned_user_names.join("، ") ||
                    t("shiftPaint.unassigned")}{" "}
                  ·{" "}
                  {t(`shiftPaint.coverageStatuses.${slot.coverage_status}`, {
                    defaultValue: slot.coverage_status.replaceAll("_", " "),
                  })}
                </Typography>
              ))}
              {changed && (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  {t("shiftPaint.changed")}
                </Alert>
              )}
              <Button
                variant="contained"
                color="success"
                sx={{ mt: 1 }}
                disabled={changed || apply.isPending}
                onClick={() => apply.mutate()}
              >
                {t("shiftPaint.generate")}
              </Button>
            </Paper>
          )}
          {(preview.isError || apply.isError) && (
            <Alert severity="error">{t("shiftPaint.error")}</Alert>
          )}
        </Stack>
        <Snackbar
          open={Boolean(notice)}
          autoHideDuration={5000}
          onClose={() => setNotice("")}
          message={notice}
        />
      </AccordionDetails>
    </Accordion>
  );
}
