import { Box, Chip, Paper, Stack, Typography } from "@mui/material";
import type { Feature, FeatureCollection, Geometry, MultiPolygon, Polygon, Position } from "geojson";
import countries from "i18n-iso-countries";
import englishCountries from "i18n-iso-countries/langs/en.json";
import { useMemo, useState, type MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import world from "geojson-world-map/src/world.js";
import { dashboardTicketCardSx } from "./dashboardCardStyles";

countries.registerLocale(englishCountries);

type CountryRow = { key?: string; label: string; value?: number; clients?: Array<{ id: number; name: string }> };
type CountryProperties = { name?: string };
type MapCountry = { feature: Feature<Geometry, CountryProperties>; row?: CountryRow; path: string };

const MAP_WIDTH = 960;
const MAP_HEIGHT = 430;
const normalize = (value: string) => value.toLowerCase().replaceAll("&", "and").replace(/[^a-z0-9]/g, "");
const aliases: Record<string, string> = {
  unitedstatesofamerica: "unitedstates", russianfederation: "russia", republicofkorea: "southkorea",
  korea: "southkorea", unitedrepublicoftanzania: "tanzania", syrianarabrepublic: "syria",
};

function project([longitude, latitude]: Position): [number, number] {
  return [((longitude + 180) / 360) * MAP_WIDTH, ((90 - latitude) / 180) * MAP_HEIGHT];
}

function ringPath(ring: Position[]): string {
  return ring.map((point, index) => {
    const [x, y] = project(point);
    return `${index ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ") + " Z";
}

function geometryPath(geometry: Geometry): string {
  if (geometry.type === "Polygon") return (geometry as Polygon).coordinates.map(ringPath).join(" ");
  if (geometry.type === "MultiPolygon") return (geometry as MultiPolygon).coordinates.flatMap((polygon) => polygon.map(ringPath)).join(" ");
  return "";
}

function densityColor(value: number, maximum: number): string {
  const ratio = value / Math.max(1, maximum);
  if (ratio >= 0.75) return "#4f46e5";
  if (ratio >= 0.45) return "#60a5fa";
  if (ratio >= 0.2) return "#5eead4";
  return "#99f6e4";
}

export function ProfessionalCountryMap({ rows, onOpen }: { rows: CountryRow[]; onOpen: (row?: CountryRow) => void }) {
  const { t } = useTranslation();
  const [hovered, setHovered] = useState<{ row: CountryRow; x: number; y: number } | null>(null);
  const maximum = Math.max(1, ...rows.map((row) => row.value ?? 0));
  const rowByName = useMemo(() => {
    const result = new Map<string, CountryRow>();
    rows.forEach((row) => { result.set(normalize(row.label), row); if (row.key) result.set(row.key.toLowerCase(), row); });
    return result;
  }, [rows]);
  const mapCountries = useMemo<MapCountry[]>(() => (
    (world as FeatureCollection<Geometry, CountryProperties>).features.map((feature) => {
      const rawName = feature.properties?.name ?? "";
      const normalizedName = normalize(rawName);
      const isoCode = countries.getAlpha2Code(rawName, "en")?.toLowerCase();
      const row = (isoCode ? rowByName.get(isoCode) : undefined) ?? rowByName.get(normalizedName) ?? rowByName.get(aliases[normalizedName] ?? normalizedName);
      return { feature, row, path: geometryPath(feature.geometry) };
    }).filter((country) => country.path)
  ), [rowByName]);

  const showTooltip = (event: MouseEvent<SVGPathElement>, row: CountryRow) => {
    const bounds = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (bounds) setHovered({ row, x: event.clientX - bounds.left, y: event.clientY - bounds.top });
  };
  const colors = ["#99f6e4", "#5eead4", "#60a5fa", "#4f46e5"];

  return <Paper sx={{ ...dashboardTicketCardSx("#2563eb"), p: 2.5, height: "100%", minHeight: 540 }}>
    <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }} mb={1.5}>
      <Box flex={1}><Typography variant="h6" fontWeight={900}>{t("managementDashboard.countries")}</Typography><Typography variant="caption" color="text.secondary">{t("managementDashboard.countriesHint")}</Typography></Box>
      <Chip color="primary" variant="outlined" label={t("managementDashboard.markets", { count: rows.length })} />
    </Stack>
    <Box sx={{ height: 420, position: "relative", borderRadius: 3, overflow: "hidden", border: "1px solid", borderColor: "divider", bgcolor: "#eef3f7" }} onMouseLeave={() => setHovered(null)}>
      <Box component="svg" role="img" aria-label={t("managementDashboard.countries")} viewBox={`0 22 ${MAP_WIDTH} 348`} preserveAspectRatio="xMidYMid meet" sx={{ width: "100%", height: "100%", display: "block" }}>
        {mapCountries.map(({ feature, row, path }, index) => <path
          key={`${feature.properties?.name ?? "country"}-${index}`} d={path}
          fill={row ? densityColor(row.value ?? 0, maximum) : "#ffffff"} stroke={row ? "#39708e" : "#cbd5df"}
          strokeWidth={row ? 1.1 : 0.62} vectorEffect="non-scaling-stroke" cursor={row ? "pointer" : "default"}
          tabIndex={row ? 0 : undefined} aria-label={row ? `${row.label}: ${row.value ?? 0}` : feature.properties?.name}
          onMouseMove={row ? (event) => showTooltip(event, row) : undefined}
          onFocus={row ? () => setHovered({ row, x: MAP_WIDTH / 2, y: 36 }) : undefined} onBlur={row ? () => setHovered(null) : undefined}
          onClick={row ? () => onOpen(row) : undefined}
          onKeyDown={row ? (event) => { if (event.key === "Enter" || event.key === " ") onOpen(row); } : undefined}
          style={{ transition: "fill 140ms ease, opacity 140ms ease", opacity: hovered && hovered.row !== row && row ? 0.72 : 1 }}
        />)}
      </Box>
      {hovered && <Paper elevation={6} sx={{ position: "absolute", left: Math.min(hovered.x + 14, 700), top: Math.max(8, hovered.y - 78), zIndex: 2, p: 1.25, minWidth: 155, pointerEvents: "none", bgcolor: "#172033", color: "#f8fafc", borderRadius: 2 }}>
        <Typography variant="body2" fontWeight={850}>{hovered.row.label}</Typography>
        <Typography variant="body2" color="#99f6e4">{t("managementDashboard.clientsCount", { count: hovered.row.value ?? 0 })}</Typography>
        <Typography variant="caption" color="#cbd5e1">{t("managementDashboard.openData")}</Typography>
      </Paper>}
    </Box>
    <Stack direction="row" alignItems="center" gap={1.5} mt={1.25} flexWrap="wrap">
      <Typography variant="caption" fontWeight={800} color="text.secondary">{t("managementDashboard.clientDensity", { defaultValue: "Client density" })}</Typography>
      {colors.map((color, index) => <Stack key={color} direction="row" alignItems="center" gap={0.5}><Box width={24} height={11} borderRadius={0.75} sx={{ border: "1px solid rgba(15,23,42,.12)", bgcolor: color }} /><Typography variant="caption" color="text.secondary">{["Low", "Moderate", "High", "Highest"][index]}</Typography></Stack>)}
    </Stack>
  </Paper>;
}
