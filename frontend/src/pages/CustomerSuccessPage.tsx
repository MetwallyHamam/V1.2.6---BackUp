import { serverDateInput } from "../utils/serverTime";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Grid,
  MenuItem,
  Paper,
  Stack,
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
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Option = { id: number; name: string };
type Result = {
  policy: {
    risk_model_version: string;
    minimum_rating_sample: number;
    complaint_overdue_days: number;
  };
  summary: Record<string, number | null>;
  satisfaction_results: Array<Record<string, unknown>>;
  complaint_results: Array<Record<string, unknown>>;
};
export function CustomerSuccessPage() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const navigate = useNavigate();
  const { hasPermission } = useAuth(),
    today = serverDateInput();
  const [tab, setTab] = useState(0),
    [filters, setFilters] = useState<Record<string, string>>({
      date_from: `${today.slice(0, 7)}-01`,
      date_to: today,
    });
  const metadata = useQuery({
    queryKey: ["customer-success-metadata"],
    queryFn: async () =>
      (
        await api.get<{
          clients: Option[];
          reasons: Option[];
          products: Option[];
        }>("/customer-success/metadata")
      ).data,
  });
  const results = useQuery({
    queryKey: ["customer-success", filters],
    queryFn: async () =>
      (
        await api.get<Result>("/customer-success/results", {
          params: Object.fromEntries(
            Object.entries(filters).filter(([, v]) => v),
          ),
        })
      ).data,
  });
  const set = (key: string, value: string) =>
    setFilters((current) => ({ ...current, [key]: value }));
  async function exportCsv() {
    const kind = tab === 0 ? "SATISFACTION" : "COMPLAINT",
      response = await api.get("/customer-success/export", {
        params: {
          ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
          kind,
        },
        responseType: "blob",
      }),
      url = URL.createObjectURL(response.data),
      link = document.createElement("a");
    link.href = url;
    link.download = `customer-success-${kind.toLowerCase()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }
  const rows =
    tab === 0
      ? results.data?.satisfaction_results
      : results.data?.complaint_results;
  const format = (key: string, value: unknown) => {
    if (value == null) return "—";
    if (key === "status")
      return t(`complaints.statuses.${String(value)}`, {
        defaultValue: String(value),
      });
    if (key.endsWith("_at")) {
      const date = new Date(String(value));
      if (!Number.isNaN(date.getTime())) return date.toLocaleString(locale);
    }
    if (typeof value === "number")
      return Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(
        value,
      );
    return String(value);
  };
  return (
    <Stack gap={2}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ md: "center" }}
      >
        <Box flexGrow={1}>
          <Typography variant="h4">{t("customerSuccess.title")}</Typography>
          <Typography color="text.secondary">
            {t("customerSuccess.subtitle")}
          </Typography>
        </Box>
        {hasPermission("customer_success.export") && (
          <Button variant="outlined" onClick={exportCsv}>
            {t("customerSuccess.export")}
          </Button>
        )}
      </Stack>
      <Paper sx={{ p: 2, borderLeft: 4, borderLeftColor: "primary.main" }}>
        <Grid container spacing={1}>
          {[
            ["date_from", "from"],
            ["date_to", "to"],
          ].map(([key, label]) => (
            <Grid key={key} size={{ xs: 12, md: 2 }}>
              <TextField
                fullWidth
                size="small"
                type="date"
                label={t(`customerSuccess.${label}`)}
                value={filters[key]}
                onChange={(e) => set(key, e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Grid>
          ))}
          {[
            ["client_id", "client", metadata.data?.clients],
            ["reason_id", "reason", metadata.data?.reasons],
            ["product_id", "product", metadata.data?.products],
          ].map(([key, label, options]) => (
            <Grid key={String(key)} size={{ xs: 12, md: 2 }}>
              <Autocomplete
                size="small"
                options={(options as Option[] | undefined) ?? []}
                value={
                  (options as Option[] | undefined)?.find(
                    (x) => String(x.id) === filters[String(key)],
                  ) ?? null
                }
                onChange={(_, value) =>
                  set(String(key), value ? String(value.id) : "")
                }
                getOptionLabel={(x) => x.name}
                filterOptions={(items, state) =>
                  items.filter((x) =>
                    x.name
                      .toLowerCase()
                      .includes(state.inputValue.toLowerCase()),
                  )
                }
                renderInput={(input) => (
                  <TextField
                    {...input}
                    label={t(`customerSuccess.${label}`)}
                    placeholder={t("customerSuccess.search", {
                      label: t(`customerSuccess.${label}`).toLocaleLowerCase(
                        locale,
                      ),
                    })}
                  />
                )}
              />
            </Grid>
          ))}
          <Grid size={{ xs: 12, md: 2 }}>
            <TextField
              fullWidth
              select
              size="small"
              label={t("customerSuccess.ratingBand")}
              value={filters.rating_band ?? ""}
              onChange={(e) => set("rating_band", e.target.value)}
            >
              <MenuItem value="">{t("customerSuccess.all")}</MenuItem>
              {["LOW", "MEDIUM", "HIGH"].map((band) => (
                <MenuItem key={band} value={band}>
                  {t(`customerSuccess.bands.${band}`)}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>
      </Paper>
      {results.isLoading ? (
        <Box display="grid" minHeight={200} sx={{ placeItems: "center" }}>
          <CircularProgress />
        </Box>
      ) : results.isError ? (
        <Alert severity="error">{t("customerSuccess.loadFailed")}</Alert>
      ) : (
        results.data && (
          <>
            <Grid container spacing={2}>
              {Object.entries(results.data.summary).map(
                ([key, value], index) => (
                  <Grid key={key} size={{ xs: 6, md: 3 }}>
                    <Paper
                      role={key.includes("checklist") ? "button" : undefined}
                      tabIndex={key.includes("checklist") ? 0 : undefined}
                      onClick={key.includes("checklist") ? () => navigate(`/service-checklists?view=monitor&filter=${key === "completed_checklists" ? "COMPLETED" : "ATTENTION"}${filters.client_id ? `&client_id=${filters.client_id}` : ""}`) : undefined}
                      sx={{
                        p: 2,
                        height: "100%",
                        cursor: key.includes("checklist") ? "pointer" : "default",
                        borderLeft: 4,
                        borderLeftColor: key === "completed_checklists" ? "#2E7D32" : key === "checklists_needing_attention" ? "#D32F2F" : ["primary.main", "success.main", "warning.main", "secondary.main"][index % 4],
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {t(`customerSuccess.metrics.${key}`, {
                          defaultValue: key.replaceAll("_", " "),
                        })}
                      </Typography>
                      <Typography variant="h5">
                        {value == null
                          ? t("customerSuccess.unavailable")
                          : Intl.NumberFormat(locale, {
                              maximumFractionDigits: 2,
                            }).format(value)}
                        {key.includes("rate") && value != null ? "%" : ""}
                      </Typography>
                    </Paper>
                  </Grid>
                ),
              )}
            </Grid>
            <Alert severity="info">
              {t("customerSuccess.policy", {
                version: results.data.policy.risk_model_version,
                sample: Intl.NumberFormat(locale).format(
                  results.data.policy.minimum_rating_sample,
                ),
                days: Intl.NumberFormat(locale).format(
                  results.data.policy.complaint_overdue_days,
                ),
              })}
            </Alert>
            <Paper sx={{ borderLeft: 4, borderLeftColor: "secondary.main" }}>
              <Tabs value={tab} onChange={(_, v) => setTab(v)}>
                <Tab label={t("customerSuccess.satisfactionTab")} />
                <Tab label={t("customerSuccess.complaintTab")} />
              </Tabs>
              {!rows?.length ? (
                <Alert severity="info" sx={{ m: 2 }}>
                  {t("customerSuccess.empty")}
                </Alert>
              ) : (
                <Box sx={{ overflow: "auto" }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        {Object.keys(rows[0]).map((key) => (
                          <TableCell key={key}>
                            {t(`customerSuccess.columns.${key}`, {
                              defaultValue: key.replaceAll("_", " "),
                            })}
                          </TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {rows.map((row, index) => (
                        <TableRow key={index}>
                          {Object.entries(row).map(([key, value]) => (
                            <TableCell key={key}>
                              {(key === "ticket_id" ||
                                key === "ticket_number") &&
                              row.ticket_id != null ? (
                                <Button
                                  size="small"
                                  onClick={() =>
                                    navigate(`/tickets/${row.ticket_id}`)
                                  }
                                  sx={{
                                    minWidth: 0,
                                    p: 0,
                                    textTransform: "none",
                                    fontWeight: 700,
                                  }}
                                >
                                  {format(key, value)}
                                </Button>
                              ) : (
                                format(key, value)
                              )}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              )}
            </Paper>
          </>
        )
      )}
    </Stack>
  );
}
