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

type ProblemRow = {
  id: number;
  problem_number: string;
  title: string;
  status: string;
  priority: string;
  owner_name?: string | null;
  target_resolution_date?: string | null;
  linked_ticket_count: number;
  open_task_count: number;
  overdue_task_count: number;
  updated_at: string;
};
type ProblemSummary = {
  total: number;
  active: number;
  known_errors: number;
  overdue: number;
  unassigned: number;
};

const statuses = [
  "",
  "NEW",
  "INVESTIGATING",
  "ROOT_CAUSE_IDENTIFIED",
  "KNOWN_ERROR",
  "FIX_PROPOSED",
  "FIX_IMPLEMENTED",
  "MONITORING",
  "CLOSED",
  "CANCELLED",
];
const priorities = ["", "LOW", "MEDIUM", "HIGH", "CRITICAL"];
const label = (value: string) => (value ? value.replaceAll("_", " ") : "All");

export function ProblemsPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const rows = useQuery({
    queryKey: ["problem-portfolio", search, status, priority],
    queryFn: async () =>
      (
        await api.get<ProblemRow[]>("/problem-portfolio", {
          params: {
            search: search.trim() || undefined,
            status: status || undefined,
            priority: priority || undefined,
          },
        })
      ).data,
  });
  const summary = useQuery({
    queryKey: ["problem-portfolio-summary"],
    queryFn: async () =>
      (await api.get<ProblemSummary>("/problem-portfolio/summary")).data,
  });
  const data = rows.data ?? [];
  const exportExcel = async () => {
    const response = await api.get("/problem-portfolio/export.xlsx", {
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "problems.xlsx";
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
            {t("serviceManagement.problems.title")}
          </Typography>
          <Button variant="outlined" onClick={() => void exportExcel()}>
            {t("serviceManagement.exportExcel")}
          </Button>
        </Stack>
        <Typography color="text.secondary">
          {t("serviceManagement.problems.subtitle")}
        </Typography>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(4, 1fr)" },
          gap: 1.5,
        }}
      >
        {[
          [t("serviceManagement.total"), summary.data?.total],
          [t("serviceManagement.active"), summary.data?.active],
          [
            t("serviceManagement.problems.knownErrors"),
            summary.data?.known_errors,
          ],
          [t("serviceManagement.problems.overdueTasks"), summary.data?.overdue],
        ].map(([title, value]) => (
          <Paper key={String(title)} variant="outlined" sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">
              {title}
            </Typography>
            <Typography
              variant="h5"
              color={
                title === t("serviceManagement.problems.overdueTasks") &&
                Number(value) > 0
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
            label={t("serviceManagement.problems.search")}
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
            label={t("serviceManagement.priority")}
            value={priority}
            onChange={(event) => setPriority(event.target.value)}
            sx={{ minWidth: 170 }}
          >
            {priorities.map((item) => (
              <MenuItem key={item || "ALL"} value={item}>
                {item ? label(item) : t("serviceManagement.allPriorities")}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
      </Paper>
      {rows.isLoading && <CircularProgress />}
      {rows.isError && (
        <Alert severity="error">
          {t("serviceManagement.problems.loadFailed")}
        </Alert>
      )}
      {!rows.isLoading && data.length === 0 && (
        <Alert severity="info">
          {t("serviceManagement.problems.noMatches")}
        </Alert>
      )}
      {data.length > 0 && (
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("serviceManagement.problems.problem")}</TableCell>
                <TableCell>{t("serviceManagement.status")}</TableCell>
                <TableCell>{t("serviceManagement.priority")}</TableCell>
                <TableCell>{t("serviceManagement.problems.owner")}</TableCell>
                <TableCell>{t("serviceManagement.problems.tickets")}</TableCell>
                <TableCell>
                  {t("serviceManagement.problems.openTasks")}
                </TableCell>
                <TableCell>{t("serviceManagement.problems.target")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow
                  hover
                  key={row.id}
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate(`/problems/${row.id}`)}
                >
                  <TableCell>
                    <TechnicalText>{row.problem_number}</TechnicalText>
                    <Typography variant="body2" fontWeight={600}>
                      {row.title}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      variant="outlined"
                      label={label(row.status)}
                    />
                  </TableCell>
                  <TableCell>{label(row.priority)}</TableCell>
                  <TableCell>
                    {row.owner_name ||
                      t("serviceManagement.problems.unassigned")}
                  </TableCell>
                  <TableCell>{row.linked_ticket_count}</TableCell>
                  <TableCell>
                    <Typography
                      color={row.overdue_task_count ? "error.main" : undefined}
                    >
                      {row.open_task_count}
                      {row.overdue_task_count
                        ? ` (${t("serviceManagement.problems.overdueCount", { count: row.overdue_task_count })})`
                        : ""}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {row.target_resolution_date
                      ? new Date(row.target_resolution_date).toLocaleDateString(
                          i18n.language,
                        )
                      : "—"}
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
