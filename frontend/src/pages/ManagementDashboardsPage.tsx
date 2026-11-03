import {
  AspectRatio,
  CloseFullscreen,
  Download,
  DragIndicator,
  ExpandLess,
  ExpandMore,
  Fullscreen,
  Insights,
  Save,
  Settings,
  TrendingDown,
  TrendingUp,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { ServiceManagementWidget } from "../components/ServiceManagementCards";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import worldMap from "@svg-maps/world";
import { api, DASHBOARD_ANALYSIS_TIMEOUT_MS } from "../api/client";
import { FinancialAnalyticsDashboard } from "../components/FinancialAnalyticsDashboard";
import { ClientHoursWidget } from "../components/ClientHoursWidget";
import { InactiveClientsKpi } from "../components/InactiveClientsKpi";
import { ProfessionalCountryMap } from "../components/ProfessionalCountryMap";
import { dashboardTicketCardSx } from "../components/dashboardCardStyles";
import { currentMonthToDate } from "../utils/dateRange";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";

type Option = {
  id: number;
  name: string;
  client_id?: number;
  iso_alpha2?: string;
};
type Metadata = {
  countries: Option[];
  zones: string[];
  clients: Option[];
  locations: Option[];
  products: Option[];
  teams: Option[];
  engineers: Option[];
  departments: Option[];
};
type EvidenceRow = Record<string, unknown>;
type Drilldown = { route: string; params: Record<string, string | number> };
type Widget = {
  code: string;
  title: string;
  value: number | string | null | SeriesRow[];
  drilldown: Drilldown;
  evidence?: EvidenceRow[] | null;
};
type Data = {
  period: {
    start: string;
    end: string;
    comparison: { current: number; previous: number; change_percent: number };
  };
  dashboards: Record<string, Widget[]>;
};
const sections = [
  ["EXECUTIVE_OVERVIEW", "Executive Overview"],
  ["CUSTOMER_SERVICE_SUCCESS", "Customer Service"],
  ["FINANCIAL_ANALYSIS", "Financial"],
] as const;
const financeChartCodes = [
  "summary",
  "trend",
  "clients",
  "aging",
  "status",
] as const;
const palette = [
  "#2563eb",
  "#06b6d4",
  "#8b5cf6",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#64748b",
  "#ec4899",
];
type SeriesRow = {
  key?: string;
  label: string;
  value?: number;
  created?: number;
  resolved?: number;
  latitude?: number | null;
  longitude?: number | null;
  clients?: { id: number; name: string }[];
  health_score?: number;
  health_status?: string;
  tickets?: number;
  open_tickets?: number;
  critical_tickets?: number;
  sla?: number | null;
  satisfaction?: number | null;
  resolution?: number;
  risk_reason?: string;
  route?: string;
};
function Donut({
  rows,
  onOpen,
}: {
  rows: SeriesRow[];
  onOpen: (row?: SeriesRow) => void;
}) {
  const { t } = useTranslation();
  const values = rows.filter((row) => (row.value ?? 0) > 0);
  const total = values.reduce((sum, row) => sum + (row.value ?? 0), 0);
  let cursor = 0;
  const gradient = values
    .map((row, index) => {
      const start = cursor;
      cursor += ((row.value ?? 0) * 100) / Math.max(total, 1);
      return `${palette[index % palette.length]} ${start}% ${cursor}%`;
    })
    .join(",");
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      alignItems="center"
      gap={3}
      mt={2}
    >
      <Box
        onClick={() => onOpen()}
        sx={{
          width: 170,
          height: 170,
          borderRadius: "50%",
          background: total ? `conic-gradient(${gradient})` : "#e2e8f0",
          position: "relative",
          display: "grid",
          placeItems: "center",
          cursor: "pointer",
          "&::after": {
            content: '""',
            position: "absolute",
            inset: 40,
            borderRadius: "50%",
            bgcolor: "background.paper",
          },
        }}
      >
        <Box textAlign="center" zIndex={1}>
          <Typography variant="h4" fontWeight={900}>
            {total}
          </Typography>
          <Typography variant="caption">
            {t("managementDashboard.total")}
          </Typography>
        </Box>
      </Box>
      <Stack spacing={0.6} flex={1}>
        {values.slice(0, 8).map((row, index) => (
          <Stack
            component="button"
            type="button"
            onClick={() => onOpen(row)}
            key={`${row.label}-${index}`}
            direction="row"
            alignItems="center"
            sx={{
              border: 0,
              bgcolor: "transparent",
              color: "text.primary",
              cursor: "pointer",
              p: 0.5,
              borderRadius: 1,
              "&:hover": { bgcolor: "action.hover" },
            }}
          >
            <Box
              width={10}
              height={10}
              borderRadius="50%"
              bgcolor={palette[index % palette.length]}
              mr={1}
            />
            <Typography variant="body2">
              {row.label.replaceAll("_", " ")}
            </Typography>
            <Typography variant="body2" fontWeight={800} ml="auto">
              {row.value ?? 0}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Stack>
  );
}
function LineVisual({ rows }: { rows: SeriesRow[] }) {
  const { t } = useTranslation();
  const max = Math.max(
      ...rows.flatMap((row) => [row.created ?? 0, row.resolved ?? 0]),
      1,
    ),
    x = (index: number) => (index * 100) / Math.max(rows.length - 1, 1),
    y = (row: SeriesRow, key: "created" | "resolved") =>
      88 - ((row[key] ?? 0) * 72) / max,
    points = (key: "created" | "resolved") =>
      rows.map((row, index) => `${x(index)},${y(row, key)}`).join(" ");
  if (!rows.length || rows.every((row) => !(row.created || row.resolved)))
    return (
      <Alert severity="info" sx={{ mt: 2 }}>
        {t("managementDashboard.noTrend")}
      </Alert>
    );
  return (
    <Box mt={2}>
      <Stack direction="row" gap={1} justifyContent="flex-end">
        <Chip
          size="small"
          color="primary"
          label={t("managementDashboard.created")}
        />
        <Chip
          size="small"
          color="success"
          label={t("managementDashboard.resolved")}
        />
      </Stack>
      <Box height={190}>
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          width="100%"
          height="155"
        >
          <line x1="0" y1="88" x2="100" y2="88" stroke="#94a3b8" />
          <polyline
            points={points("created")}
            fill="none"
            stroke="#2563eb"
            strokeWidth="2.5"
            vectorEffect="non-scaling-stroke"
          />
          <polyline
            points={points("resolved")}
            fill="none"
            stroke="#22c55e"
            strokeWidth="2.5"
            vectorEffect="non-scaling-stroke"
          />
          {rows.map((row, index) => (
            <g key={row.label}>
              <circle
                cx={x(index)}
                cy={y(row, "created")}
                r="1.8"
                fill="#2563eb"
              />
              <circle
                cx={x(index)}
                cy={y(row, "resolved")}
                r="1.8"
                fill="#22c55e"
              />
            </g>
          ))}
        </svg>
        <Stack direction="row" justifyContent="space-between">
          {rows
            .filter(
              (_, index) =>
                index === 0 ||
                index === rows.length - 1 ||
                index % Math.max(1, Math.ceil(rows.length / 6)) === 0,
            )
            .map((row) => (
              <Typography
                key={row.label}
                variant="caption"
                color="text.secondary"
              >
                {row.label}
              </Typography>
            ))}
        </Stack>
      </Box>
    </Box>
  );
}
function Bars({
  rows,
  onOpen,
}: {
  rows: SeriesRow[];
  onOpen: (row: SeriesRow) => void;
}) {
  const max = Math.max(...rows.map((row) => row.value ?? 0), 1);
  return (
    <Stack spacing={1.4} mt={2}>
      {rows.slice(0, 12).map((row, index) => (
        <Box
          component="button"
          type="button"
          onClick={() => onOpen(row)}
          key={`${row.label}-${index}`}
          sx={{
            border: 0,
            bgcolor: "transparent",
            color: "text.primary",
            textAlign: "left",
            cursor: "pointer",
            p: 0,
          }}
        >
          <Stack direction="row">
            <Typography variant="body2">
              {row.label.replaceAll("_", " ")}
            </Typography>
            <Typography variant="body2" ml="auto" fontWeight={800}>
              {row.value ?? 0}
            </Typography>
          </Stack>
          <Box
            height={11}
            bgcolor="action.hover"
            borderRadius={8}
            mt={0.5}
            overflow="hidden"
          >
            <Box
              height="100%"
              width={`${((row.value ?? 0) * 100) / max}%`}
              bgcolor={palette[index % palette.length]}
              borderRadius={8}
            />
          </Box>
        </Box>
      ))}
    </Stack>
  );
}
function VisualWidget({
  widget,
  onOpen,
}: {
  widget: Widget;
  onOpen: (row?: SeriesRow) => void;
}) {
  const { t } = useTranslation();
  const rows = Array.isArray(widget.value) ? widget.value : [];
  const isTrend = rows.some(
    (row) => row.created !== undefined || row.resolved !== undefined,
  );
  const isDonut = [
    "status_mix",
    "priority_mix",
    "products",
    "countries",
    "zones",
  ].includes(widget.code);
  return (
    <Card sx={{ ...dashboardTicketCardSx("#2563eb"), height: "100%" }}>
      <CardContent>
        <Stack direction="row" alignItems="center">
          <Box>
            <Typography fontWeight={800}>{widget.title}</Typography>
            <Typography variant="caption" color="text.secondary">
              {t("managementDashboard.interactive")}
            </Typography>
          </Box>
          <Insights color="primary" sx={{ ml: "auto" }} />
        </Stack>
        {isTrend ? (
          <LineVisual rows={rows} />
        ) : isDonut ? (
          <Donut rows={rows} onOpen={onOpen} />
        ) : (
          <Bars rows={rows} onOpen={onOpen} />
        )}
      </CardContent>
    </Card>
  );
}
function CustomerWidget({
  widget,
  onOpen,
}: {
  widget: Widget;
  onOpen: (row?: SeriesRow) => void;
}) {
  const { t } = useTranslation();
  const [client, setClient] = useState("");
  const rows = Array.isArray(widget.value) ? widget.value : [];
  const shown = client ? rows.filter((row) => row.key === client) : rows;
  return (
    <Stack spacing={1}>
      <TextField
        select
        size="small"
        label={t("managementDashboard.clientName")}
        value={client}
        onChange={(event) => setClient(event.target.value)}
      >
        <MenuItem value="">{t("managementDashboard.allClients")}</MenuItem>
        {rows.map((row) => (
          <MenuItem key={row.key} value={row.key}>
            {row.label}
          </MenuItem>
        ))}
      </TextField>
      <VisualWidget widget={{ ...widget, value: shown }} onOpen={onOpen} />
    </Stack>
  );
}
export const LegacyCountryMap = memo(function LegacyCountryMap({
  rows,
  onOpen,
}: {
  rows: SeriesRow[];
  onOpen: (row?: SeriesRow) => void;
}) {
  const { t } = useTranslation();
  const theme = useTheme(),
    dark = theme.palette.mode === "dark";
  const maximum = Math.max(...rows.map((row) => row.value ?? 0), 1);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const tooltipNameRef = useRef<HTMLSpanElement>(null);
  const tooltipCountRef = useRef<HTMLSpanElement>(null);
  const rowByCountry = useMemo(
    () => new Map(rows.map((row) => [(row.key ?? "").toLowerCase(), row])),
    [rows],
  );
  const mapColors = dark
    ? {
        ocean: "#18334a",
        oceanEdge: "#102538",
        grid: "rgba(255,255,255,.045)",
        land: "#465565",
        border: "#657485",
      }
    : {
        ocean: "#b9dff1",
        oceanEdge: "#a8d4e9",
        grid: "rgba(255,255,255,.16)",
        land: "#f3efe8",
        border: "#a8b3bd",
      };
  const scale = dark
    ? ["#93c5fd", "#60a5fa", "#3b82f6", "#1d4ed8"]
    : ["#dbeafe", "#93c5fd", "#3b82f6", "#1d4ed8"];
  const baseCountries = useMemo(
    () =>
      worldMap.locations.map(
        (location: { id: string; name: string; path: string }) => (
          <path
            key={location.id}
            id={`world-country-${location.id}`}
            d={location.path}
            fill={mapColors.land}
            stroke={mapColors.border}
            strokeWidth={0.5}
            vectorEffect="non-scaling-stroke"
          />
        ),
      ),
    [mapColors.border, mapColors.land],
  );
  const activeCountries = useMemo<
    Array<{ id: string; name: string; path: string; row: SeriesRow }>
  >(
    () =>
      worldMap.locations
        .map((location: { id: string; name: string; path: string }) => ({
          ...location,
          row: rowByCountry.get(location.id.toLowerCase()),
        }))
        .filter(
          (location: {
            id: string;
            name: string;
            path: string;
            row?: SeriesRow;
          }): location is {
            id: string;
            name: string;
            path: string;
            row: SeriesRow;
          } => Boolean(location.row),
        ),
    [rowByCountry],
  );
  // Kept null so the legacy detail popover is never mounted; country clicks
  // drill down immediately without React hover updates.
  const [hovered] = useState<{
    name: string;
    row?: SeriesRow;
    x: number;
    y: number;
  } | null>(null);
  function showLocation(
    clientX: number,
    clientY: number,
    svg: SVGSVGElement | null,
    name: string,
    count: number,
  ) {
    const tooltip = tooltipRef.current;
    const bounds = svg?.getBoundingClientRect();
    if (!tooltip || !bounds) return;
    if (tooltipNameRef.current) tooltipNameRef.current.textContent = name;
    if (tooltipCountRef.current)
      tooltipCountRef.current.textContent = t(
        "managementDashboard.clientsCount",
        { count },
      );
    tooltip.style.left = `${Math.min(bounds.width - 190, Math.max(10, clientX - bounds.left + 14))}px`;
    tooltip.style.top = `${Math.min(bounds.height - 74, Math.max(10, clientY - bounds.top + 14))}px`;
    tooltip.style.display = "block";
  }
  function hideLocation() {
    if (tooltipRef.current) tooltipRef.current.style.display = "none";
  }
  return (
    <Paper
      sx={{
        ...dashboardTicketCardSx("#4285f4"),
        p: 2.5,
        height: "100%",
        minHeight: 500,
        color: "text.primary",
        background: dark
          ? "linear-gradient(145deg,#101e27 0%,#0a151d 100%)"
          : "linear-gradient(145deg,#fff 0%,#f3fafb 100%)",
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Box>
          <Typography variant="h6" fontWeight={900}>
            {t("managementDashboard.countries")}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("managementDashboard.countriesHint")}
          </Typography>
        </Box>
        <Chip
          color="primary"
          variant="outlined"
          sx={{ ml: { sm: "auto" }, alignSelf: { xs: "flex-start" } }}
          label={t("managementDashboard.markets", { count: rows.length })}
        />
      </Stack>
      <Box
        sx={{
          position: "relative",
          height: { xs: 330, md: 400 },
          mt: 2,
          borderRadius: 3.5,
          overflow: "hidden",
          contain: "layout paint",
          isolation: "isolate",
          background: `linear-gradient(160deg,${mapColors.ocean} 0%,${mapColors.oceanEdge} 100%)`,
          border: `1px solid ${dark ? "rgba(148,163,184,.18)" : "rgba(100,116,139,.16)"}`,
          boxShadow: dark
            ? "inset 0 -32px 70px rgba(0,0,0,.18),0 10px 24px rgba(0,0,0,.16)"
            : "inset 0 -28px 64px rgba(14,116,144,.065),0 10px 24px rgba(15,23,42,.07)",
        }}
      >
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            backgroundImage: `linear-gradient(${mapColors.grid} 1px,transparent 1px),linear-gradient(90deg,${mapColors.grid} 1px,transparent 1px)`,
            backgroundSize: "56px 56px",
            maskImage: "linear-gradient(to bottom,black,transparent 92%)",
          }}
        />
        <svg
          viewBox={worldMap.viewBox}
          width="100%"
          height="100%"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={t("managementDashboard.worldMap")}
          style={{ position: "relative" }}
        >
          <g aria-hidden="true">{baseCountries}</g>
          {activeCountries.map((location) => {
            const row = location.row!,
              count = row.value ?? 0,
              intensity = count / maximum,
              color =
                scale[
                  intensity > 0.75
                    ? 3
                    : intensity > 0.5
                      ? 2
                      : intensity > 0.25
                        ? 1
                        : 0
                ];
            return (
              <path
                key={location.id}
                d={location.path}
                fill={color}
                fillOpacity={dark ? 0.88 : 0.9}
                stroke={dark ? "#f8fafc" : "#ffffff"}
                strokeWidth={1.2}
                vectorEffect="non-scaling-stroke"
                tabIndex={0}
                aria-label={`${location.name}: ${t("managementDashboard.linkedClients", { count })}`}
                onPointerEnter={(event) =>
                  showLocation(
                    event.clientX,
                    event.clientY,
                    event.currentTarget.ownerSVGElement,
                    location.name,
                    count,
                  )
                }
                onPointerMove={(event) =>
                  showLocation(
                    event.clientX,
                    event.clientY,
                    event.currentTarget.ownerSVGElement,
                    location.name,
                    count,
                  )
                }
                onPointerLeave={hideLocation}
                onFocus={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  showLocation(
                    bounds.left + bounds.width / 2,
                    bounds.top + bounds.height / 2,
                    event.currentTarget.ownerSVGElement,
                    location.name,
                    count,
                  );
                }}
                onBlur={hideLocation}
                onClick={() => onOpen(row)}
                style={{ cursor: "pointer", outline: "none" }}
              >
                <title>{`${location.name} · ${t("managementDashboard.clientsCount", { count })}`}</title>
              </path>
            );
          })}
        </svg>
        <Box
          ref={tooltipRef}
          sx={{
            display: "none",
            position: "absolute",
            zIndex: 4,
            width: 180,
            px: 1.5,
            py: 1,
            pointerEvents: "none",
            borderRadius: 2,
            color: "#f8fafc",
            bgcolor: "rgba(15,23,42,.94)",
            border: "1px solid rgba(255,255,255,.18)",
            boxShadow: "0 10px 28px rgba(15,23,42,.28)",
          }}
        >
          <Typography
            component="span"
            ref={tooltipNameRef}
            display="block"
            fontWeight={850}
          />
          <Typography
            component="span"
            ref={tooltipCountRef}
            display="block"
            variant="caption"
            sx={{ color: "#bfdbfe" }}
          />
          <Typography
            component="span"
            display="block"
            variant="caption"
            sx={{ color: "rgba(255,255,255,.62)" }}
          >
            {t("managementDashboard.openData")}
          </Typography>
        </Box>
        {hovered && (
          <Paper
            elevation={8}
            sx={{
              position: "absolute",
              zIndex: 4,
              p: 1.5,
              width: 250,
              maxWidth: "calc(100% - 24px)",
              pointerEvents: "none",
              left: `min(calc(100% - 262px), max(12px, ${hovered.x + 14}px))`,
              top: `min(calc(100% - 190px), max(12px, ${hovered.y + 14}px))`,
              color: "text.primary",
              border: `1px solid ${dark ? "rgba(103,232,249,.3)" : "rgba(14,165,233,.25)"}`,
              borderRadius: 2.25,
              bgcolor: dark ? "#102531" : "#ffffff",
              boxShadow: dark
                ? "0 12px 28px rgba(0,0,0,.42)"
                : "0 12px 28px rgba(15,23,42,.16)",
            }}
          >
            <Typography color="text.primary" fontWeight={900}>
              {hovered.name}
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: dark ? "#67e8f9" : "#0e7490" }}
              fontWeight={800}
            >
              {t("managementDashboard.linkedClients", {
                count: hovered.row?.value ?? 0,
              })}
            </Typography>
            {hovered.row?.clients?.length ? (
              <Stack spacing={0.45} mt={1}>
                {hovered.row.clients.slice(0, 6).map((client) => (
                  <Stack
                    key={client.id}
                    direction="row"
                    alignItems="center"
                    gap={0.75}
                  >
                    <Box
                      width={6}
                      height={6}
                      flex="0 0 auto"
                      borderRadius="50%"
                      sx={{ bgcolor: dark ? "#22d3ee" : "#0891b2" }}
                    />
                    <Typography variant="caption" color="text.primary" noWrap>
                      {client.name}
                    </Typography>
                  </Stack>
                ))}
                {hovered.row.clients.length > 6 && (
                  <Typography variant="caption" color="text.secondary">
                    {t("managementDashboard.moreClients", {
                      count: hovered.row.clients.length - 6,
                    })}
                  </Typography>
                )}
              </Stack>
            ) : (
              <Typography
                display="block"
                variant="caption"
                color="text.secondary"
                mt={0.75}
              >
                {t("managementDashboard.noClientsInArea")}
              </Typography>
            )}
          </Paper>
        )}
      </Box>
      <Stack
        direction="row"
        alignItems="center"
        gap={1.5}
        mt={1.25}
        flexWrap="wrap"
      >
        <Typography variant="caption" fontWeight={800} color="text.secondary">
          {t("managementDashboard.clientDensity", {
            defaultValue: "Client density",
          })}
        </Typography>
        {scale.map((color, index) => (
          <Stack key={color} direction="row" alignItems="center" gap={0.5}>
            <Box width={18} height={8} borderRadius={0.75} bgcolor={color} />
            <Typography variant="caption" color="text.secondary">
              {
                [
                  t("managementDashboard.densityLow", { defaultValue: "Low" }),
                  t("managementDashboard.densityModerate", {
                    defaultValue: "Moderate",
                  }),
                  t("managementDashboard.densityHigh", {
                    defaultValue: "High",
                  }),
                  t("managementDashboard.densityHighest", {
                    defaultValue: "Highest",
                  }),
                ][index]
              }
            </Typography>
          </Stack>
        ))}
      </Stack>
      <Stack direction="row" gap={1} flexWrap="wrap" mt={1.5}>
        {rows.slice(0, 8).map((row) => (
          <Chip
            key={row.label}
            size="small"
            clickable
            onClick={() => onOpen(row)}
            label={`${row.label} · ${t("managementDashboard.clientsCount", { count: row.value ?? 0 })}`}
            sx={{
              color: "text.primary",
              borderLeft: "4px solid #4285f4",
              bgcolor: dark ? "rgba(30,50,65,.9)" : "rgba(255,255,255,.9)",
              "&:hover": {
                bgcolor: dark ? "rgba(71,85,105,.72)" : "rgba(226,232,240,.82)",
              },
            }}
          />
        ))}
      </Stack>
    </Paper>
  );
});
function MetricVisual({
  widget,
  onOpen,
  comparison,
}: {
  widget: Widget;
  onOpen: () => void;
  comparison?: Data["period"]["comparison"];
}) {
  const { t } = useTranslation();
  const raw = Number(widget.value ?? 0);
  const label = widget.value == null ? "—" : String(widget.value);
  const percent = widget.code === "sla" || widget.code === "growth";
  const good =
    widget.code === "critical"
      ? raw === 0
      : widget.code === "growth"
        ? raw >= 0
        : widget.code === "sla"
          ? raw >= 95
          : true;
  const angle = Math.max(
    0,
    Math.min(100, percent ? raw : Math.log10(raw + 1) * 33),
  );
  const delta =
    widget.code === "tickets" ? comparison?.change_percent : undefined;
  const accent = good
    ? "#22c55e"
    : widget.code === "critical"
      ? "#ef4444"
      : "#f59e0b";
  return (
    <Card
      component="button"
      onClick={onOpen}
      sx={{
        ...dashboardTicketCardSx(accent, true),
        width: "100%",
        height: "100%",
        minHeight: 210,
        textAlign: "left",
      }}
    >
      <CardContent>
        <Stack direction="row">
          <Typography color="text.secondary" fontWeight={700}>
            {widget.title}
          </Typography>
          {delta !== undefined && (
            <Chip
              size="small"
              sx={{ ml: "auto" }}
              color={delta >= 0 ? "success" : "warning"}
              icon={delta >= 0 ? <TrendingUp /> : <TrendingDown />}
              label={`${delta}%`}
            />
          )}
        </Stack>
        {percent ? (
          <Box
            sx={{
              width: 145,
              height: 145,
              borderRadius: "50%",
              mx: "auto",
              mt: 1,
              display: "grid",
              placeItems: "center",
              background: `conic-gradient(${good ? "#16a34a" : "#f59e0b"} ${angle}%,#e2e8f0 0)`,
              position: "relative",
              "&::after": {
                content: '""',
                position: "absolute",
                inset: 17,
                borderRadius: "50%",
                bgcolor: "background.paper",
              },
            }}
          >
            <Box zIndex={1} textAlign="center">
              <Typography
                variant="h4"
                fontWeight={900}
                color={good ? "success.main" : "warning.main"}
              >
                {raw}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("managementDashboard.performance")}
              </Typography>
            </Box>
          </Box>
        ) : (
          <Box mt={4}>
            <Stack alignItems="flex-end" direction="row">
              <Typography variant="h3" fontWeight={900}>
                {label}
              </Typography>
              <Typography ml="auto" variant="caption" color="text.secondary">
                {t("managementDashboard.currentPeriod")}
              </Typography>
            </Stack>
            <Box
              height={18}
              bgcolor="action.hover"
              borderRadius={9}
              overflow="hidden"
              mt={2}
            >
              <Box
                height="100%"
                width={`${Math.max(raw > 0 ? 8 : 0, angle)}%`}
                bgcolor={good ? "primary.main" : "error.main"}
                borderRadius={9}
              />
            </Box>
            <Typography variant="caption" color="text.secondary">
              {t("managementDashboard.relativeVolume")}
            </Typography>
          </Box>
        )}
        <Typography
          display="block"
          mt={1}
          variant="caption"
          color="primary.main"
        >
          {t("managementDashboard.openData")}
        </Typography>
      </CardContent>
    </Card>
  );
}
function ClientPortfolio({
  rows,
  navigate,
  dateFrom,
  dateTo,
}: {
  rows: SeriesRow[];
  navigate: (route: string) => void;
  dateFrom: string;
  dateTo: string;
}) {
  const { t } = useTranslation();
  const [search, setSearch] = useState(""),
    [page, setPage] = useState(0),
    [showAll, setShowAll] = useState(false);
  const filtered = rows.filter((row) =>
      row.label.toLowerCase().includes(search.trim().toLowerCase()),
    ),
    pageCount = Math.max(1, Math.ceil(filtered.length / 20)),
    visible = showAll ? filtered : filtered.slice(page * 20, page * 20 + 20);
  return (
    <Paper sx={{ ...dashboardTicketCardSx("#8b5cf6"), p: 2.5 }}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        gap={1}
        mb={2}
        alignItems={{ md: "center" }}
      >
        <Box flexGrow={1}>
          <Typography variant="h6" fontWeight={900}>
            {t("managementDashboard.portfolio")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("managementDashboard.portfolioHint")}
          </Typography>
        </Box>
        <TextField
          size="small"
          label={t("managementDashboard.searchClient")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(0);
          }}
          sx={{ minWidth: { xs: "100%", md: 260 } }}
        />
        <Chip
          color="primary"
          variant="outlined"
          label={t("managementDashboard.clientsCount", {
            count: filtered.length,
          })}
        />
      </Stack>
      <Box sx={{ overflow: "auto", maxHeight: showAll ? 620 : "none" }}>
        <Box
          component="table"
          sx={{
            width: "100%",
            minWidth: 1000,
            borderCollapse: "collapse",
            "th,td": {
              p: 1.2,
              borderBottom: "1px solid",
              borderColor: "divider",
              textAlign: "left",
            },
            th: {
              color: "text.secondary",
              fontSize: 12,
              position: "sticky",
              top: 0,
              bgcolor: "background.paper",
              zIndex: 1,
            },
          }}
        >
          <thead>
            <tr>
              <th>{t("managementDashboard.client")}</th>
              <th>{t("managementDashboard.health")}</th>
              <th>{t("managementDashboard.tickets")}</th>
              <th>{t("managementDashboard.open")}</th>
              <th>{t("managementDashboard.p1Open")}</th>
              <th>{t("managementDashboard.sla")}</th>
              <th>{t("managementDashboard.satisfaction")}</th>
              <th>{t("managementDashboard.resolved")}</th>
              <th>{t("managementDashboard.managementAttention")}</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <Box
                component="tr"
                key={row.key}
                onClick={() =>
                  row.key &&
                  navigate(
                    `/tickets?${new URLSearchParams({ client_id: row.key, open_only: "true", created_from: dateFrom, created_to: dateTo })}`,
                  )
                }
                sx={{
                  cursor: "pointer",
                  "&:hover": { bgcolor: "action.hover" },
                }}
              >
                <td>
                  <Typography color="primary.main" fontWeight={800}>
                    {row.label}
                  </Typography>
                </td>
                <td>
                  <Chip
                    size="small"
                    color={
                      row.health_status === "HEALTHY"
                        ? "success"
                        : row.health_status === "AT_RISK"
                          ? "error"
                          : row.health_status === "INSUFFICIENT_DATA"
                            ? "default"
                            : "warning"
                    }
                    label={`${row.health_score == null ? "—" : row.health_score} · ${(row.health_status ?? "").replaceAll("_", " ")}`}
                  />
                </td>
                <td>{row.tickets ?? 0}</td>
                <td>{row.open_tickets ?? 0}</td>
                <td>{row.critical_tickets ?? 0}</td>
                <td>
                  {row.sla == null
                    ? t("managementDashboard.unavailable")
                    : `${row.sla}%`}
                </td>
                <td>
                  {row.satisfaction == null
                    ? t("managementDashboard.unavailable")
                    : `${row.satisfaction}/5`}
                </td>
                <td>
                  {row.tickets
                    ? `${row.resolution ?? 0}%`
                    : t("managementDashboard.unavailable")}
                </td>
                <td>{row.risk_reason}</td>
              </Box>
            ))}
          </tbody>
        </Box>
      </Box>
      {!filtered.length && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {t("managementDashboard.noClients")}
        </Alert>
      )}
      <Stack
        direction="row"
        gap={1}
        alignItems="center"
        justifyContent="flex-end"
        mt={2}
      >
        <Button
          onClick={() => {
            setShowAll((value) => !value);
            setPage(0);
          }}
        >
          {showAll
            ? t("managementDashboard.showPaged")
            : t("managementDashboard.showAll")}
        </Button>
        {!showAll && (
          <>
            <Button
              disabled={page === 0}
              onClick={() => setPage((value) => value - 1)}
            >
              {t("managementDashboard.previous")}
            </Button>
            <Typography variant="body2">
              {t("managementDashboard.pageOf", {
                page: Math.min(page + 1, pageCount),
                pages: pageCount,
              })}
            </Typography>
            <Button
              disabled={page + 1 >= pageCount}
              onClick={() => setPage((value) => value + 1)}
            >
              {t("managementDashboard.next")}
            </Button>
          </>
        )}
      </Stack>
    </Paper>
  );
}
function EvidenceModal({
  widget,
  onClose,
  navigate,
}: {
  widget: Widget | null;
  onClose: () => void;
  navigate: (route: string) => void;
}) {
  const { t } = useTranslation();
  const rows = widget?.evidence ?? [],
    columns = rows.length
      ? Object.keys(rows[0]).filter((key) => key !== "route")
      : [];
  return (
    <Dialog open={Boolean(widget)} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center">
          <Box flex={1}>
            <Typography variant="h5" fontWeight={900}>
              {t("managementDashboard.evidenceTitle", { title: widget?.title })}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("managementDashboard.evidenceHint")}
            </Typography>
          </Box>
          <Chip
            color="primary"
            label={t("managementDashboard.records", { count: rows.length })}
          />
          <IconButton onClick={onClose}>×</IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent>
        {!rows.length ? (
          <Alert severity="info">{t("managementDashboard.noEvidence")}</Alert>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                {columns.map((column) => (
                  <TableCell
                    key={column}
                    sx={{ textTransform: "capitalize", fontWeight: 800 }}
                  >
                    {column.replaceAll("_", " ")}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row, index) => (
                <TableRow
                  hover
                  key={index}
                  onClick={() => row.route && navigate(String(row.route))}
                  sx={{ cursor: row.route ? "pointer" : "default" }}
                >
                  {columns.map((column) => (
                    <TableCell key={column}>
                      {row[column] == null ? "—" : String(row[column])}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}

type PersonalWidgetLayout = Record<string, { order: number; width: number }>;

export function ManagementDashboardsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [section, setSection] = useState<string>("EXECUTIVE_OVERVIEW");
  const [presentation, setPresentation] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const [hiddenWidgets, setHiddenWidgets] = useState<Record<string, string[]>>(
    () => {
      try {
        return JSON.parse(
          localStorage.getItem("supporthub-top-management-hidden-widgets") ||
            "{}",
        );
      } catch {
        return {};
      }
    },
  );
  const [widgetTabs, setWidgetTabs] = useState<Record<string, string>>(() => {
    try {
      return JSON.parse(
        localStorage.getItem("supporthub-top-management-widget-tabs") || "{}",
      );
    } catch {
      return {};
    }
  });
  const [evidenceWidget, setEvidenceWidget] = useState<Widget | null>(null);
  const [widgetLayout, setWidgetLayout] = useState<PersonalWidgetLayout>({});
  const [layoutDirty, setLayoutDirty] = useState(false);
  const [draggedWidget, setDraggedWidget] = useState<string | null>(null);
  const defaultPeriod = currentMonthToDate();
  const [filters, setFilters] = useState<Record<string, string>>({
    date_from: defaultPeriod.dateFrom,
    date_to: defaultPeriod.dateTo,
  });
  useEffect(
    () =>
      localStorage.setItem(
        "supporthub-top-management-hidden-widgets",
        JSON.stringify(hiddenWidgets),
      ),
    [hiddenWidgets],
  );
  useEffect(
    () =>
      localStorage.setItem(
        "supporthub-top-management-widget-tabs",
        JSON.stringify(widgetTabs),
      ),
    [widgetTabs],
  );
  useEffect(() => {
    if (!user?.id) return;
    try {
      setWidgetLayout(
        JSON.parse(
          localStorage.getItem(
            `supporthub-dashboard-layout-${user.id}-${section}`,
          ) || "{}",
        ),
      );
    } catch {
      setWidgetLayout({});
    }
    setLayoutDirty(false);
  }, [section, user?.id]);
  useEffect(() => {
    if (section === "ASSIGNED_DASHBOARD") setSection("EXECUTIVE_OVERVIEW");
  }, [section]);
  const metadata = useQuery({
    queryKey: ["management-metadata"],
    queryFn: async () =>
      (await api.get<Metadata>("/management-dashboards/metadata")).data,
  });
  const analytics = useQuery({
    queryKey: ["management-analytics", filters],
    queryFn: async () =>
      (
        await api.get<Data>("/management-dashboards/analytics", {
          params: {
            ...Object.fromEntries(
              Object.entries(filters).filter(([, value]) => value),
            ),
            timezone_offset_minutes: -new Date().getTimezoneOffset(),
          },
          timeout: DASHBOARD_ANALYSIS_TIMEOUT_MS,
        })
      ).data,
    staleTime: 120000,
    enabled: Boolean(
      filters.date_from &&
      filters.date_to &&
      filters.date_from <= filters.date_to,
    ),
  });
  function set(name: string, value: string) {
    setFilters((current) => ({
      ...current,
      [name]: value,
      ...(name === "client_id" ? { location_id: "" } : {}),
    }));
  }
  function open(drilldown: Drilldown) {
    const params = new URLSearchParams(
      Object.entries(drilldown.params)
        .filter(([, value]) => value !== null && value !== "")
        .map(([key, value]) => [key, String(value)]),
    );
    navigate(`${drilldown.route}?${params}`);
  }
  function openWidget(widget: Widget, row?: SeriesRow) {
    if (widget.evidence && !row) {
      setEvidenceWidget(widget);
      return;
    }
    const params = { ...widget.drilldown.params };
    if (row) {
      if (widget.code === "status_mix")
        params.status_code = String(row.key ?? row.label);
      if (widget.code === "priority_mix")
        params.priority = String(row.key ?? row.label);
      if (
        (widget.code === "support_consumption" ||
          widget.code === "customer_workhours") &&
        row.key
      )
        params.client_id = row.key;
      if (widget.code === "health_distribution" && row.key) {
        const affected = (
          analytics.data?.dashboards.CUSTOMER_SERVICE_SUCCESS ?? []
        ).find((item) => item.code === "client_health_portfolio");
        const ids = Array.isArray(affected?.value)
          ? affected.value
              .filter(
                (client) => client.health_status === row.key && client.key,
              )
              .map((client) => client.key)
          : [];
        if (ids.length) {
          params.client_id = ids.join(",");
          params.open_only = "true";
        }
      }
      if (widget.code === "products" && row.key === "__NONE__")
        params.without_product = "true";
      else if (widget.code === "products" && row.key)
        params.product_id = row.key;
      if (widget.code === "workload" && row.key) params.engineer_id = row.key;
      if (widget.code === "root_causes" && row.key)
        params.root_cause_id = row.key;
      if (widget.code === "countries") {
        const country = metadata.data?.countries.find(
          (item) =>
            item.iso_alpha2?.toLowerCase() ===
            String(row.key ?? "").toLowerCase(),
        );
        if (country) params.country_id = country.id;
      }
    }
    open({ ...widget.drilldown, params });
  }
  async function exportReport() {
    const response = await api.get("/management-dashboards/export.docx", {
      params: {
        ...Object.fromEntries(
          Object.entries(filters).filter(([, value]) => value),
        ),
        widget_tabs: JSON.stringify(widgetTabs),
        hidden_widgets: JSON.stringify(hiddenWidgets),
      },
      responseType: "blob",
      timeout: DASHBOARD_ANALYSIS_TIMEOUT_MS,
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `top-management-analysis-${filters.date_from}-${filters.date_to}.docx`;
    link.click();
    URL.revokeObjectURL(url);
  }
  const serviceWidgets: Widget[] = [
    {
      code: "service_incidents",
      title: "Incidents",
      value: null,
      drilldown: {
        route: "/tickets",
        params: { ticket_type_code: "INCIDENT" },
      },
    },
    {
      code: "service_change_requests",
      title: "Change Requests",
      value: null,
      drilldown: { route: "/change-requests", params: {} },
    },
    {
      code: "service_problems",
      title: "Problems",
      value: null,
      drilldown: { route: "/problems", params: {} },
    },
  ];
  const sourceWidgets = [
    ...Object.entries(analytics.data?.dashboards ?? {}).flatMap(
      ([source, items]) => items.map((widget) => ({ widget, source })),
    ),
    ...serviceWidgets.map((widget) => ({
      widget,
      source: "EXECUTIVE_OVERVIEW",
    })),
    ...financeChartCodes.map((code) => ({
      widget: {
        code: `finance_chart_${code}`,
        title: t(`financialAnalytics.widgets.${code}`),
        value: null,
        drilldown: { route: "/financial", params: {} },
      } as Widget,
      source: "FINANCIAL_ANALYSIS",
    })),
  ];
  const allWidgets = sourceWidgets
    .filter(
      ({ widget, source }) => (widgetTabs[widget.code] ?? source) === section,
    )
    .map(({ widget }) => widget);
  const hidden = hiddenWidgets[section] ?? [];
  const widgets = allWidgets
    .filter((widget) => !hidden.includes(widget.code))
    .sort(
      (left, right) =>
        (widgetLayout[left.code]?.order ??
          allWidgets.findIndex((item) => item.code === left.code)) -
        (widgetLayout[right.code]?.order ??
          allWidgets.findIndex((item) => item.code === right.code)),
    );
  const widgetChoices = sourceWidgets;
  const comparison = analytics.data?.period.comparison;
  function toggleWidget(code: string, show: boolean) {
    setHiddenWidgets((current) => {
      const sectionHidden = current[section] ?? [];
      return {
        ...current,
        [section]: show
          ? sectionHidden.filter((item) => item !== code)
          : Array.from(new Set([...sectionHidden, code])),
      };
    });
  }
  function widgetWidth(widget: Widget) {
    return (
      widgetLayout[widget.code]?.width ??
      (widget.code === "client_hours" || widget.code === "finance_chart_summary"
        ? 12
        : widget.code === "finance_chart_trend"
          ? 8
          : widget.code.startsWith("finance_chart_")
            ? 6
            : Array.isArray(widget.value)
              ? widget.code === "countries" ||
                widget.code === "client_health_portfolio"
                ? 12
                : 6
              : 4)
    );
  }
  function moveWidget(targetCode: string) {
    if (!draggedWidget || draggedWidget === targetCode) return;
    const codes = widgets.map((item) => item.code);
    const from = codes.indexOf(draggedWidget),
      to = codes.indexOf(targetCode);
    if (from < 0 || to < 0) return;
    codes.splice(to, 0, codes.splice(from, 1)[0]);
    setWidgetLayout((current) =>
      Object.fromEntries(
        codes.map((code, order) => [
          code,
          {
            order,
            width:
              current[code]?.width ??
              widgetWidth(widgets.find((item) => item.code === code)!),
          },
        ]),
      ),
    );
    setDraggedWidget(null);
    setLayoutDirty(true);
  }
  function resizeWidget(widget: Widget) {
    const sizes = [4, 6, 8, 12],
      current = widgetWidth(widget),
      width = sizes[(Math.max(0, sizes.indexOf(current)) + 1) % sizes.length];
    setWidgetLayout((value) => ({
      ...value,
      [widget.code]: {
        order: value[widget.code]?.order ?? widgets.indexOf(widget),
        width,
      },
    }));
    setLayoutDirty(true);
  }
  function saveLayout() {
    if (!user?.id) return;
    localStorage.setItem(
      `supporthub-dashboard-layout-${user.id}-${section}`,
      JSON.stringify(widgetLayout),
    );
    setLayoutDirty(false);
  }
  return (
    <Box
      sx={
        presentation
          ? {
              position: "fixed",
              inset: 0,
              zIndex: 1500,
              bgcolor: "background.default",
              p: 3,
              overflow: "auto",
            }
          : {}
      }
    >
      <Stack spacing={2}>
        <Paper
          sx={{
            p: 2.5,
            background: "linear-gradient(120deg,#071d49,#0e7490)",
            color: "white",
          }}
        >
          <Stack
            direction={{ xs: "column", md: "row" }}
            alignItems={{ md: "center" }}
            gap={2}
          >
            <Box flexGrow={1}>
              <Typography variant="h4" fontWeight={900}>
                {t("managementDashboard.title")}
              </Typography>
              <Typography sx={{ opacity: 0.8 }}>
                {t("managementDashboard.subtitle")}
              </Typography>
            </Box>
            {comparison && (
              <Chip
                color={comparison.change_percent >= 0 ? "success" : "warning"}
                icon={
                  comparison.change_percent >= 0 ? (
                    <TrendingUp />
                  ) : (
                    <TrendingDown />
                  )
                }
                label={t("managementDashboard.comparison", {
                  value: comparison.change_percent,
                })}
              />
            )}
            <Button
              color="inherit"
              startIcon={<Settings />}
              onClick={() => setCustomizeOpen(true)}
              disabled={section === "ASSIGNED_DASHBOARD"}
            >
              {t("managementDashboard.customize")}
            </Button>
            {
              <Button
                color="inherit"
                variant={layoutDirty ? "contained" : "text"}
                startIcon={<Save />}
                disabled={!layoutDirty}
                onClick={saveLayout}
              >
                {t("managementDashboard.saveLayout", {
                  defaultValue: "Save layout",
                })}
              </Button>
            }
            <Button
              color="inherit"
              startIcon={<Download />}
              onClick={exportReport}
            >
              {t("managementDashboard.export")}
            </Button>
            <Button
              color="inherit"
              startIcon={presentation ? <CloseFullscreen /> : <Fullscreen />}
              onClick={() => setPresentation((value) => !value)}
            >
              {presentation
                ? t("managementDashboard.exitPresentation")
                : t("managementDashboard.presentation")}
            </Button>
          </Stack>
        </Paper>
        {!hidden.includes("inactive_clients") &&
          section === "EXECUTIVE_OVERVIEW" && <InactiveClientsKpi />}
        <Paper sx={{ p: 2 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            gap={1}
            alignItems={{ md: "center" }}
          >
            <Box flexGrow={1}>
              <Typography fontWeight={800}>
                {t("managementDashboard.filters")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("managementDashboard.filtersHint")}
              </Typography>
            </Box>
            <Chip
              size="small"
              label={t("managementDashboard.active", {
                count: Object.values(filters).filter(Boolean).length,
              })}
            />
            <Button
              size="small"
              onClick={() => setFiltersOpen((value) => !value)}
              endIcon={filtersOpen ? <ExpandLess /> : <ExpandMore />}
            >
              {filtersOpen
                ? t("managementDashboard.collapse")
                : t("managementDashboard.expand")}
            </Button>
            <Button
              size="small"
              onClick={() => {
                const currentMonth = currentMonthToDate();
                setFilters({
                  date_from: currentMonth.dateFrom,
                  date_to: currentMonth.dateTo,
                });
              }}
            >
              {t("managementDashboard.reset")}
            </Button>
          </Stack>
          <Collapse in={filtersOpen}>
            <Grid container spacing={1} sx={{ mt: 1 }}>
              {[
                "date_from",
                "date_to",
                "department_id",
                "country_id",
                "zone",
                "client_id",
                "location_id",
                "product_id",
                "team_id",
                "engineer_id",
              ]
                .map((name) => [name, t(`managementDashboard.fields.${name}`)])
                .map(([name, label]) => {
                  const isDate = name === "date_from" || name === "date_to";
                  return (
                    <Grid
                      key={name}
                      size={{ xs: 12, sm: 6, lg: isDate ? 2 : 1.3 }}
                    >
                      <TextField
                        fullWidth
                        size="small"
                        select={!isDate}
                        type={isDate ? "date" : undefined}
                        label={label}
                        value={filters[name] ?? ""}
                        onChange={(event) => set(name, event.target.value)}
                        slotProps={
                          isDate
                            ? {
                                inputLabel: { shrink: true },
                                htmlInput: {
                                  max:
                                    name === "date_from"
                                      ? filters.date_to
                                      : undefined,
                                  min:
                                    name === "date_to"
                                      ? filters.date_from
                                      : undefined,
                                },
                              }
                            : undefined
                        }
                      >
                        {!isDate && [
                          <MenuItem key="all" value="">
                            {t("managementDashboard.all")}
                          </MenuItem>,
                          ...(name === "zone"
                            ? (metadata.data?.zones ?? []).map((value) => (
                                <MenuItem key={value} value={value}>
                                  {value}
                                </MenuItem>
                              ))
                            : (
                                (metadata.data?.[
                                  (name.replace("_id", "") +
                                    "s") as keyof Metadata
                                ] as Option[] | undefined) ?? []
                              )
                                .filter(
                                  (item) =>
                                    name !== "location_id" ||
                                    !filters.client_id ||
                                    item.client_id ===
                                      Number(filters.client_id),
                                )
                                .map((item) => (
                                  <MenuItem key={item.id} value={item.id}>
                                    {item.name}
                                  </MenuItem>
                                ))),
                        ]}
                      </TextField>
                    </Grid>
                  );
                })}
            </Grid>
            {filters.date_from > filters.date_to && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                {t("managementDashboard.invalidDates")}
              </Alert>
            )}
          </Collapse>
        </Paper>
        <Tabs
          value={section}
          onChange={(_, value) => setSection(value)}
          variant="scrollable"
          scrollButtons="auto"
        >
          {sections.map(([code]) => (
            <Tab
              key={code}
              value={code}
              label={
                code === "EXECUTIVE_OVERVIEW"
                  ? t("managementDashboard.executive")
                  : code === "CUSTOMER_SERVICE_SUCCESS"
                    ? t("managementDashboard.customerSuccess")
                    : t("managementDashboard.financial")
              }
            />
          ))}
        </Tabs>
        {section === "CUSTOMER_SERVICE_SUCCESS" && (
          <Paper sx={{ p: 2 }}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1.5}
              alignItems={{ sm: "center" }}
            >
              <Box flexGrow={1}>
                <Typography fontWeight={800}>
                  {t("managementDashboard.customerFocus")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("managementDashboard.customerFocusHint")}
                </Typography>
              </Box>
              <TextField
                select
                size="small"
                label={t("managementDashboard.clientName")}
                value={filters.client_id ?? ""}
                onChange={(event) => set("client_id", event.target.value)}
                sx={{ minWidth: { xs: "100%", sm: 320 } }}
              >
                <MenuItem value="">
                  {t("managementDashboard.allClients")}
                </MenuItem>
                {(metadata.data?.clients ?? []).map((client) => (
                  <MenuItem key={client.id} value={client.id}>
                    {client.name}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
          </Paper>
        )}
        {analytics.isLoading ? (
          <Box minHeight={300} display="grid" sx={{ placeItems: "center" }}>
            <CircularProgress />
          </Box>
        ) : analytics.isError ? (
          <Alert
            severity="error"
            action={
              <Button
                color="inherit"
                size="small"
                onClick={() => analytics.refetch()}
              >
                {t("managementDashboard.retry")}
              </Button>
            }
          >
            {t("managementDashboard.loadFailed")}
          </Alert>
        ) : (
          <>
            <Alert severity="info" sx={{ mb: 2 }}>
              {t("managementDashboard.layoutHint", {
                defaultValue:
                  "Drag widgets by the handle, resize them, then select Save layout. This layout is personal to you.",
              })}
            </Alert>
            <Grid container spacing={2}>
              {widgets.map((widget) => (
                <Grid
                  key={widget.code}
                  size={{ xs: 12, md: widgetWidth(widget) }}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => moveWidget(widget.code)}
                >
                  <Box sx={{ height: "100%", position: "relative" }}>
                    <Stack
                      direction="row"
                      gap={0.25}
                      sx={{
                        position: "absolute",
                        zIndex: 5,
                        top: 8,
                        insetInlineEnd: 8,
                        p: 0.25,
                        borderRadius: 1,
                        bgcolor: "background.paper",
                        boxShadow: 2,
                      }}
                    >
                      <IconButton
                        size="small"
                        draggable
                        onDragStart={(event) => {
                          event.stopPropagation();
                          setDraggedWidget(widget.code);
                          event.dataTransfer.effectAllowed = "move";
                        }}
                        onDragEnd={() => setDraggedWidget(null)}
                        aria-label={t("managementDashboard.dragWidget", {
                          defaultValue: "Drag widget",
                        })}
                        title={t("managementDashboard.dragWidget", {
                          defaultValue: "Drag widget",
                        })}
                        sx={{ cursor: "grab" }}
                      >
                        <DragIndicator fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => resizeWidget(widget)}
                        aria-label={t("managementDashboard.resizeWidget", {
                          defaultValue: "Resize widget",
                        })}
                        title={t("managementDashboard.resizeWidget", {
                          defaultValue: "Resize widget",
                        })}
                      >
                        <AspectRatio fontSize="small" />
                      </IconButton>
                    </Stack>
                    {widget.code.startsWith("service_") ? (
                      <ServiceManagementWidget
                        category={
                          widget.code === "service_incidents"
                            ? "incidents"
                            : widget.code === "service_change_requests"
                              ? "changes"
                              : "problems"
                        }
                        filters={filters}
                      />
                    ) : widget.code === "client_hours" ? (
                      <ClientHoursWidget
                        dateFrom={filters.date_from}
                        dateTo={filters.date_to}
                        clientId={
                          filters.client_id
                            ? Number(filters.client_id)
                            : undefined
                        }
                      />
                    ) : widget.code.startsWith("finance_chart_") ? (
                      <FinancialAnalyticsDashboard
                        externalFilters={filters}
                        compact
                        showCustomizer={false}
                        allowedWidgets={[
                          widget.code.replace(
                            "finance_chart_",
                            "",
                          ) as (typeof financeChartCodes)[number],
                        ]}
                        storageKey={`supporthub-management-financial-widgets-${user?.id ?? "anonymous"}`}
                      />
                    ) : Array.isArray(widget.value) ? (
                      widget.code === "countries" ? (
                        <ProfessionalCountryMap
                          rows={widget.value}
                          onOpen={(row) => openWidget(widget, row)}
                        />
                      ) : widget.code === "client_health_portfolio" ? (
                        <ClientPortfolio
                          rows={widget.value}
                          navigate={navigate}
                          dateFrom={filters.date_from}
                          dateTo={filters.date_to}
                        />
                      ) : widget.code === "support_consumption" ||
                        widget.code === "customer_workhours" ? (
                        <CustomerWidget
                          widget={widget}
                          onOpen={(row) => openWidget(widget, row)}
                        />
                      ) : (
                        <VisualWidget
                          widget={widget}
                          onOpen={(row) => openWidget(widget, row)}
                        />
                      )
                    ) : (
                      <MetricVisual
                        widget={widget}
                        onOpen={() => openWidget(widget)}
                        comparison={comparison}
                      />
                    )}
                  </Box>
                </Grid>
              ))}
            </Grid>
          </>
        )}
        <Dialog
          open={customizeOpen}
          onClose={() => setCustomizeOpen(false)}
          fullWidth
          maxWidth="sm"
        >
          <DialogTitle>{t("managementDashboard.customizeTitle")}</DialogTitle>
          <DialogContent>
            <Typography color="text.secondary" mb={1}>
              {t("managementDashboard.customizeHelp")}
            </Typography>
            <Stack>
              {section === "EXECUTIVE_OVERVIEW" && (
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={!hidden.includes("inactive_clients")}
                      onChange={(_, checked) =>
                        toggleWidget("inactive_clients", checked)
                      }
                    />
                  }
                  label={t("managementDashboard.inactiveClientsWidget")}
                />
              )}{" "}
              {widgetChoices.map(({ widget, source }) => (
                <Stack
                  key={widget.code}
                  direction={{ xs: "column", sm: "row" }}
                  alignItems={{ sm: "center" }}
                  gap={1}
                >
                  <FormControlLabel
                    sx={{ flex: 1 }}
                    control={
                      <Checkbox
                        checked={
                          !(
                            hiddenWidgets[widgetTabs[widget.code] ?? source] ??
                            []
                          ).includes(widget.code)
                        }
                        onChange={(_, checked) => {
                          const tab = widgetTabs[widget.code] ?? source;
                          setHiddenWidgets((current) => ({
                            ...current,
                            [tab]: checked
                              ? (current[tab] ?? []).filter(
                                  (code) => code !== widget.code,
                                )
                              : [...(current[tab] ?? []), widget.code],
                          }));
                        }}
                      />
                    }
                    label={widget.title}
                  />
                  <TextField
                    size="small"
                    select
                    label={t("managementDashboard.tab", {
                      defaultValue: "Tab",
                    })}
                    value={widgetTabs[widget.code] ?? source}
                    onChange={(event) =>
                      setWidgetTabs((current) => ({
                        ...current,
                        [widget.code]: event.target.value,
                      }))
                    }
                    sx={{ minWidth: 170 }}
                  >
                    <MenuItem value="EXECUTIVE_OVERVIEW">
                      {t("managementDashboard.executive")}
                    </MenuItem>
                    <MenuItem value="CUSTOMER_SERVICE_SUCCESS">
                      {t("managementDashboard.customerSuccess")}
                    </MenuItem>
                  </TextField>
                </Stack>
              ))}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() =>
                setHiddenWidgets((current) => ({ ...current, [section]: [] }))
              }
            >
              {t("managementDashboard.showAllWidgets")}
            </Button>
            <Button variant="contained" onClick={() => setCustomizeOpen(false)}>
              {t("managementDashboard.done")}
            </Button>
          </DialogActions>
        </Dialog>
        <EvidenceModal
          widget={evidenceWidget}
          onClose={() => setEvidenceWidget(null)}
          navigate={navigate}
        />
      </Stack>
    </Box>
  );
}
