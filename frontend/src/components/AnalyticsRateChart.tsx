import { Box, ButtonBase, Paper, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";

type ChartMetric = {
  code: string;
  name: string;
  status: string;
  unit: string;
  value: number | null;
};

export function AnalyticsRateChart<T extends ChartMetric>({ title, metrics, onOpen }: {
  title: string;
  metrics: T[];
  onOpen: (metric: T) => void;
}) {
  const rates = metrics.filter((metric) => metric.unit === "PERCENT");
  if (!rates.length) return null;
  return (
    <Paper component="section" aria-label={title} variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 3, mb: 2 }}>
      <Typography component="h2" variant="h6" fontWeight={750}>{title}</Typography>
      <Stack direction="row" justifyContent="space-between" sx={{ my: 1.5 }} aria-hidden>
        {[0, 25, 50, 75, 100].map((tick) => (
          <Typography key={tick} variant="caption" color="text.secondary">{tick}%</Typography>
        ))}
      </Stack>
      <Stack gap={1}>
        {rates.map((metric) => {
          const value = metric.status === "READY" && metric.value !== null && Number.isFinite(metric.value) ? metric.value : null;
          const label = value === null ? "No eligible data" : `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
          return (
            <ButtonBase key={metric.code} onClick={() => onOpen(metric)} disabled={metric.status !== "READY"}
              aria-label={`${metric.name}, ${label}, view evidence`}
              sx={{ display: "block", p: 1, textAlign: "start", borderRadius: 2,
                "&:hover": { bgcolor: "action.hover" }, "&.Mui-focusVisible": { outline: "2px solid", outlineColor: "primary.main" } }}>
              <Stack direction="row" justifyContent="space-between" gap={1} alignItems="baseline">
                <Typography variant="body2" fontWeight={700}>{metric.name}</Typography>
                <Typography variant="body2" color={value === null ? "text.secondary" : "primary.main"} fontWeight={750}>{label}</Typography>
              </Stack>
              <Box aria-hidden sx={(theme) => ({
                mt: 0.75, height: 10, borderRadius: 2, bgcolor: "action.hover", overflow: "hidden",
                backgroundImage: `repeating-linear-gradient(to right, transparent 0 calc(25% - 1px), ${alpha(theme.palette.text.primary, 0.15)} calc(25% - 1px) 25%)`,
              })}>
                {value !== null && <Box sx={{ height: "100%", width: `${Math.max(0, Math.min(100, value))}%`, bgcolor: "primary.main", borderRadius: 2 }} />}
              </Box>
            </ButtonBase>
          );
        })}
      </Stack>
    </Paper>
  );
}
