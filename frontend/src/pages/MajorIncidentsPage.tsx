import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { TechnicalText } from "../components/TechnicalText";

type Row = {
  id: number;
  major_incident_number: string;
  primary_ticket_id: number;
  ticket_number: string;
  subject: string;
  client_name?: string | null;
  severity: string;
  status: string;
  commander_name?: string | null;
  current_status_summary: string;
  next_update_at?: string | null;
  declared_at: string;
  affected_ticket_count: number;
  problem_count: number;
};
type MajorSummary = {
  total: number;
  active: number;
  active_sev1: number;
  updates_overdue: number;
  awaiting_pir: number;
};
const statuses = [
  "",
  "DECLARED",
  "RESPONSE_ACTIVE",
  "SERVICE_RESTORED",
  "MONITORING",
  "POST_INCIDENT_REVIEW",
  "CLOSED",
  "CANCELLED",
];
const severities = ["", "SEV1", "SEV2", "SEV3", "SEV4"];
const label = (value: string) => (value ? value.replaceAll("_", " ") : "All");

export function MajorIncidentsPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const rows = useQuery({
    queryKey: ["major-incident-portfolio", search, status, severity],
    queryFn: async () =>
      (
        await api.get<Row[]>("/major-incident-portfolio", {
          params: {
            search: search.trim() || undefined,
            status: status || undefined,
            severity: severity || undefined,
          },
        })
      ).data,
  });
  const summary = useQuery({
    queryKey: ["major-incident-portfolio-summary"],
    queryFn: async () =>
      (await api.get<MajorSummary>("/major-incident-portfolio/summary")).data,
  });
  const data = rows.data ?? [];
  const exportExcel = async () => {
    const response = await api.get("/major-incident-portfolio/export.xlsx", {
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "major_incidents.xlsx";
    link.click();
    URL.revokeObjectURL(url);
  };
  return (
    <Stack gap={2}>
      <Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ sm: "center" }}
          gap={1}
        >
          <Typography variant="h4" sx={{ flexGrow: 1 }}>
            {t("serviceManagement.majorIncidents.title")}
          </Typography>
          <Button variant="outlined" onClick={() => void exportExcel()}>
            {t("serviceManagement.exportExcel")}
          </Button>
        </Stack>
        <Typography color="text.secondary">
          {t("serviceManagement.majorIncidents.subtitle")}
        </Typography>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2,1fr)", md: "repeat(4,1fr)" },
          gap: 1.5,
        }}
      >
        {[
          [t("serviceManagement.total"), summary.data?.total],
          [t("serviceManagement.active"), summary.data?.active],
          [
            t("serviceManagement.majorIncidents.activeSev1"),
            summary.data?.active_sev1,
          ],
          [
            t("serviceManagement.majorIncidents.updatesOverdue"),
            summary.data?.updates_overdue,
          ],
        ].map(([title, value]) => (
          <Paper key={String(title)} variant="outlined" sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">
              {title}
            </Typography>
            <Typography
              variant="h5"
              color={
                title ===
                  t("serviceManagement.majorIncidents.updatesOverdue") &&
                Number(value)
                  ? "error.main"
                  : undefined
              }
            >
              {value}
            </Typography>
          </Paper>
        ))}
      </Box>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} gap={2}>
          <TextField
            fullWidth
            label={t("serviceManagement.majorIncidents.search")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <TextField
            select
            label={t("serviceManagement.status")}
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            sx={{ minWidth: 220 }}
          >
            {statuses.map((item) => (
              <MenuItem key={item || "ALL"} value={item}>
                {item ? label(item) : t("serviceManagement.allStatuses")}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label={t("serviceManagement.severity")}
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
            sx={{ minWidth: 150 }}
          >
            {severities.map((item) => (
              <MenuItem key={item || "ALL"} value={item}>
                {item || t("serviceManagement.allSeverities")}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
      </Paper>
      {rows.isLoading && <CircularProgress />}
      {rows.isError && (
        <Alert severity="error">
          {t("serviceManagement.majorIncidents.loadFailed")}
        </Alert>
      )}
      {!rows.isLoading && !data.length && (
        <Alert severity="info">
          {t("serviceManagement.majorIncidents.noMatches")}
        </Alert>
      )}
      {!!data.length && (
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  {t("serviceManagement.majorIncidents.majorIncident")}
                </TableCell>
                <TableCell>
                  {t("serviceManagement.majorIncidents.clientTicket")}
                </TableCell>
                <TableCell>{t("serviceManagement.severity")}</TableCell>
                <TableCell>{t("serviceManagement.status")}</TableCell>
                <TableCell>
                  {t("serviceManagement.majorIncidents.commander")}
                </TableCell>
                <TableCell>
                  {t("serviceManagement.majorIncidents.scope")}
                </TableCell>
                <TableCell>
                  {t("serviceManagement.majorIncidents.nextUpdate")}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow
                  hover
                  key={row.id}
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate(`/major-incidents/${row.id}`)}
                >
                  <TableCell>
                    <TechnicalText>{row.major_incident_number}</TechnicalText>
                    <Typography variant="body2">
                      {row.current_status_summary}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight={600}>{row.client_name}</Typography>
                    <TechnicalText>{row.ticket_number}</TechnicalText> ·{" "}
                    {row.subject}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={
                        row.severity === "SEV1"
                          ? "error"
                          : row.severity === "SEV2"
                            ? "warning"
                            : "default"
                      }
                      label={row.severity}
                    />
                  </TableCell>
                  <TableCell>{label(row.status)}</TableCell>
                  <TableCell>{row.commander_name}</TableCell>
                  <TableCell>
                    {t("serviceManagement.majorIncidents.scopeCounts", {
                      tickets: row.affected_ticket_count,
                      problems: row.problem_count,
                    })}
                  </TableCell>
                  <TableCell>
                    <Typography
                      color={
                        row.next_update_at &&
                        new Date(row.next_update_at) < new Date()
                          ? "error.main"
                          : undefined
                      }
                    >
                      {row.next_update_at
                        ? new Date(row.next_update_at).toLocaleString(
                            i18n.language,
                          )
                        : "—"}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Stack>
  );
}
