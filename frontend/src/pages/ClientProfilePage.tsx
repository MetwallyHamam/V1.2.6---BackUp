import { serverDateInput } from "../utils/serverTime";
import { ArrowBack, Download, Insights, OpenInNew } from "@mui/icons-material";
import { ClientLifecycleOverview, type ClientLifecycle } from "../components/ClientLifecycleOverview";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
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
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ClientFinanceStatementPanel } from "./ClientFinanceStatementPanel";

type Impact = {
  area: string;
  level: string;
  consequence: string;
  evidence: string;
  action: string;
};
type Drilldowns = {
  metrics: Record<string, string>;
  breakdowns: Record<string, Record<string, string>>;
  business_impacts: Record<string, string>;
  trend: string;
};
type Evidence = {
  title: string;
  definition: string;
  total: number;
  unit: string;
  rows: Array<Record<string, unknown>>;
};
type Profile = {
  client: Record<string, unknown>;
  metrics: Record<string, number | null>;
  breakdowns: Record<string, Record<string, number>>;
  trends: {
    ticket_volume: Array<{ date: string; created: number; resolved: number }>;
  };
  business_impacts: Impact[];
  critical_tickets: Array<{
    id: number;
    number: string;
    subject: string;
    priority: string;
    status: string;
    business_flags: string;
  }>;
  drilldowns: Drilldowns;
  evidence: Record<string, Evidence>;
  lifecycle: ClientLifecycle;
};
const colors = [
  "#1677a6",
  "#00a0a8",
  "#f59e0b",
  "#7c3aed",
  "#dc2626",
  "#16a34a",
];
const rows = (values: Record<string, number> = {}) =>
  Object.entries(values)
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);

function Donut({
  values,
  onClick,
}: {
  values: Record<string, number>;
  onClick: (label: string) => void;
}) {
  const { t } = useTranslation();
  const data = rows(values),
    total = data.reduce((sum, item) => sum + item.value, 0);
  let at = 0;
  const gradient = data
    .map((item, index) => {
      const start = at;
      at += (item.value * 100) / Math.max(total, 1);
      return `${colors[index % colors.length]} ${start}% ${at}%`;
    })
    .join(",");
  return (
    <Stack direction={{ xs: "column", sm: "row" }} gap={2} alignItems="center">
      <Box
        component="button"
        onClick={() => data[0] && onClick(data[0].label)}
        aria-label={t("clientProfile.openPriorityEvidence")}
        sx={{
          width: 170,
          height: 170,
          border: 0,
          cursor: "pointer",
          borderRadius: "50%",
          background: total ? `conic-gradient(${gradient})` : "#e2e8f0",
          display: "grid",
          placeItems: "center",
          position: "relative",
          "&:after": {
            content: '""',
            position: "absolute",
            inset: 38,
            borderRadius: "50%",
            bgcolor: "background.paper",
          },
        }}
      >
        <Box zIndex={1} textAlign="center">
          <Typography variant="h4" fontWeight={900}>
            {total}
          </Typography>
          <Typography variant="caption">
            {t("clientProfile.tickets")}
          </Typography>
        </Box>
      </Box>
      <Stack flex={1} width="100%">
        {data.map((item, index) => (
          <Button
            key={item.label}
            onClick={() => onClick(item.label)}
            sx={{ justifyContent: "flex-start", color: "text.primary" }}
          >
            <Box
              width={10}
              height={10}
              borderRadius="50%"
              bgcolor={colors[index % colors.length]}
              mr={1}
            />
            {item.label}
            <b style={{ marginLeft: "auto" }}>{item.value}</b>
          </Button>
        ))}
      </Stack>
    </Stack>
  );
}
function Bars({
  values,
  onClick,
}: {
  values: Record<string, number>;
  onClick: (label: string) => void;
}) {
  const data = rows(values),
    maximum = Math.max(...data.map((item) => item.value), 1);
  return (
    <Stack spacing={1.2}>
      {data.slice(0, 10).map((item, index) => (
        <Box
          component="button"
          key={item.label}
          onClick={() => onClick(item.label)}
          sx={{
            border: 0,
            bgcolor: "transparent",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <Stack direction="row">
            <Typography variant="body2">{item.label}</Typography>
            <Typography variant="body2" fontWeight={800} ml="auto">
              {item.value}
            </Typography>
          </Stack>
          <Box height={10} borderRadius={5} bgcolor="action.hover">
            <Box
              height="100%"
              width={`${(item.value * 100) / maximum}%`}
              borderRadius={5}
              bgcolor={colors[index % colors.length]}
            />
          </Box>
        </Box>
      ))}
    </Stack>
  );
}
function Trend({
  values,
  onClick,
}: {
  values: Profile["trends"]["ticket_volume"];
  onClick: () => void;
}) {
  const { t } = useTranslation(),
    { id } = useParams(),
    { hasPermission } = useAuth(),
    maximum = Math.max(
      ...values.flatMap((item) => [item.created, item.resolved]),
      1,
    ),
    points = (key: "created" | "resolved") =>
      values
        .map(
          (item, index) =>
            `${(index * 100) / Math.max(values.length - 1, 1)},${90 - (item[key] * 75) / maximum}`,
        )
        .join(" ");
  return (
    <Stack spacing={2}>
      <Box
        component="button"
        onClick={onClick}
        aria-label={t("clientProfile.openTrendEvidence")}
        sx={{
          width: "100%",
          border: 0,
          bgcolor: "transparent",
          cursor: "pointer",
        }}
      >
        <Stack direction="row" justifyContent="flex-end" gap={1}>
          <Chip
            size="small"
            color="primary"
            label={t("clientProfile.created")}
          />
          <Chip
            size="small"
            color="success"
            label={t("clientProfile.resolved")}
          />
        </Stack>
        <svg
          viewBox="0 0 100 100"
          width="100%"
          height="220"
          preserveAspectRatio="none"
        >
          <line x1="0" y1="90" x2="100" y2="90" stroke="#94a3b8" />
          <polyline
            points={points("created")}
            fill="none"
            stroke="#1677a6"
            strokeWidth="3"
            vectorEffect="non-scaling-stroke"
          />
          <polyline
            points={points("resolved")}
            fill="none"
            stroke="#16a34a"
            strokeWidth="3"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </Box>
      {id && hasPermission("finance.view") && (
        <ClientFinanceStatementPanel
          clientId={Number(id)}
          canActivate={hasPermission("client.manage")}
        />
      )}
    </Stack>
  );
}
export function EvidenceDialog({
  evidence,
  onClose,
  navigate,
}: {
  evidence?: Evidence;
  onClose: () => void;
  navigate: (route: string) => void;
}) {
  const { t } = useTranslation();
  const columns = evidence?.rows.length
    ? Object.keys(evidence.rows[0]).filter((key) => key !== "route")
    : [];
  return (
    <Dialog open={Boolean(evidence)} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>
        <Stack direction="row" alignItems="center" gap={1}>
          <Box flex={1}>
            <Typography variant="h5" fontWeight={900}>
              {evidence?.title}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {evidence?.definition}
            </Typography>
          </Box>
          <Chip
            color="primary"
            label={`${evidence?.total ?? 0} ${evidence?.unit ?? ""}`}
          />
          <IconButton onClick={onClose}>×</IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent>
        {!evidence?.rows.length ? (
          <Alert severity="info">{t("clientProfile.noEvidence")}</Alert>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                {columns.map((column) => (
                  <TableCell key={column}>
                    {column.replaceAll("_", " ")}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {evidence.rows.map((row, index) => (
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

export function ClientProfilePage() {
  const { t } = useTranslation(),
    { id } = useParams(),
    navigate = useNavigate(),
    { hasPermission } = useAuth(),
    today = serverDateInput();
  const params = new URLSearchParams(window.location.search);
  const [from, setFrom] = useState(
      params.get("date_from") ?? `${today.slice(0, 8)}01`,
    ),
    [to, setTo] = useState(params.get("date_to") ?? today);
  const profile = useQuery({
    queryKey: ["client-profile", id, from, to],
    queryFn: async () =>
      (
        await api.get<Profile>("/reports/client-profile", {
          params: { client_id: id, date_from: from, date_to: to },
        })
      ).data,
    enabled: Boolean(id),
  });
  const open = (url?: string) => {
    if (url) navigate(url);
  };
  async function exportWord() {
    const response = await api.get("/reports/client-profile.docx", {
      params: { client_id: id, date_from: from, date_to: to },
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Client-Profile-${from}-${to}.docx`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (profile.isLoading) return <CircularProgress />;
  if (profile.isError || !profile.data)
    return <Alert severity="error">{t("clientProfile.loadFailed")}</Alert>;
  const p = profile.data,
    m = p.metrics,
    c = p.client,
    cardKeys = [
      "total_requests",
      "sla_compliance_percent",
      "sla_breached",
      "critical_incidents",
      "saved_business_hours",
      "sla_target_business_hours",
      "services_provided",
      "total_working_hours",
      "completed_checklists",
      "checklists_needing_attention",
    ];
  return (
    <Stack spacing={2}>
      <Paper
        sx={{
          p: 3,
          background: "linear-gradient(120deg,#123b5d,#1677a6)",
          color: "white",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={2}
          alignItems={{ md: "center" }}
        >
          <Box
            flex={1}
            onClick={() => navigate(`/clients/${id}/edit`)}
            sx={{ cursor: "pointer" }}
          >
            <Button color="inherit" startIcon={<ArrowBack />}>
              {t("clientProfile.clientData")}
            </Button>
            <Typography variant="h3" fontWeight={900}>
              {String(c.name)}
            </Typography>
            <Typography sx={{ opacity: 0.82 }}>
              {String(c.code)} ·{" "}
              {String(c.country ?? t("clientProfile.countryMissing"))} ·{" "}
              {String(c.city ?? t("clientProfile.cityMissing"))}
            </Typography>
          </Box>
          <TextField
            size="small"
            type="date"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
            sx={{ bgcolor: "white", borderRadius: 1 }}
          />
          <TextField
            size="small"
            type="date"
            value={to}
            onChange={(event) => setTo(event.target.value)}
            sx={{ bgcolor: "white", borderRadius: 1 }}
          />
          {hasPermission("report.export") && (
            <Button
              color="inherit"
              variant="outlined"
              startIcon={<Download />}
              onClick={exportWord}
            >
              {t("clientProfile.wordReport")}
            </Button>
          )}
        </Stack>
      </Paper>
      <ClientLifecycleOverview lifecycle={p.lifecycle} />
      <Grid container spacing={2}>
        {cardKeys.map((key) => (
          <Grid key={key} size={{ xs: 6, md: 4, lg: 2 }}>
            <Card sx={{ height: "100%" }}>
              <CardActionArea
                sx={{ height: "100%" }}
                onClick={() => open(p.drilldowns.metrics[key])}
              >
                <CardContent>
                  <Insights color="primary" />
                  <Typography variant="h4" fontWeight={900}>
                    {m[key] ?? "—"}
                  </Typography>
                  <Typography color="text.secondary">
                    {t(`clientProfile.metrics.${key}`)}
                  </Typography>
                  <Typography variant="caption" color="primary">
                    {t("clientProfile.openEvidence")}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="h6" fontWeight={800}>
              {t("clientProfile.ticketTrend")}
            </Typography>
            <Trend
              values={p.trends.ticket_volume}
              onClick={() => open(p.drilldowns.trend)}
            />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="h6" fontWeight={800}>
              {t("clientProfile.priorityMix")}
            </Typography>
            <Donut
              values={p.breakdowns.priority}
              onClick={(value) => open(p.drilldowns.breakdowns.priority[value])}
            />
          </Paper>
        </Grid>
        {(
          [
            ["status", t("clientProfile.statusDistribution")],
            ["product", t("clientProfile.products")],
            ["module", t("clientProfile.modules")],
            ["service", t("clientProfile.services")],
          ] as const
        ).map(([key, title]) => (
          <Grid key={key} size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 2.5, height: "100%" }}>
              <Typography variant="h6" fontWeight={800} mb={2}>
                {title}
              </Typography>
              <Bars
                values={p.breakdowns[key]}
                onClick={(value) => open(p.drilldowns.breakdowns[key][value])}
              />
            </Paper>
          </Grid>
        ))}
      </Grid>
      <Paper sx={{ p: 2.5 }}>
        <Typography variant="h5" fontWeight={900} mb={2}>
          {t("clientProfile.businessImpact")}
        </Typography>
        <Grid container spacing={2}>
          {p.business_impacts.map((impact) => (
            <Grid key={impact.area} size={{ xs: 12, md: 6 }}>
              <Card
                variant="outlined"
                sx={{
                  height: "100%",
                  borderLeft: 6,
                  borderLeftColor:
                    impact.level === "CRITICAL"
                      ? "error.main"
                      : impact.level === "HIGH"
                        ? "warning.main"
                        : impact.level === "POSITIVE"
                          ? "success.main"
                          : "info.main",
                }}
              >
                <CardActionArea
                  sx={{ height: "100%" }}
                  onClick={() =>
                    open(p.drilldowns.business_impacts[impact.area])
                  }
                >
                  <CardContent>
                    <Stack direction="row">
                      <Typography fontWeight={900} flex={1}>
                        {impact.area}
                      </Typography>
                      <Chip size="small" label={impact.level} />
                    </Stack>
                    <Typography mt={1}>{impact.consequence}</Typography>
                    <Typography variant="body2" color="text.secondary" mt={1}>
                      <b>{t("clientProfile.evidence")}</b> {impact.evidence}
                    </Typography>
                    <Typography variant="body2" color="primary" mt={1}>
                      <b>{t("clientProfile.action")}</b> {impact.action}
                    </Typography>
                    <Typography variant="caption" color="primary">
                      {t("clientProfile.openEvidence")}
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>
      <Paper sx={{ p: 2.5 }}>
        <Typography variant="h5" fontWeight={900}>
          {t("clientProfile.criticalDetails")}
        </Typography>
        {!p.critical_tickets.length ? (
          <Alert severity="success" sx={{ mt: 2 }}>
            {t("clientProfile.noCritical")}
          </Alert>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("clientProfile.ticket")}</TableCell>
                <TableCell>{t("clientProfile.subject")}</TableCell>
                <TableCell>{t("clientProfile.priority")}</TableCell>
                <TableCell>{t("clientProfile.status")}</TableCell>
                <TableCell>{t("clientProfile.flags")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {p.critical_tickets.map((ticket) => (
                <TableRow
                  hover
                  key={ticket.id}
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>
                    {ticket.number} <OpenInNew fontSize="inherit" />
                  </TableCell>
                  <TableCell>{ticket.subject}</TableCell>
                  <TableCell>{ticket.priority}</TableCell>
                  <TableCell>{ticket.status}</TableCell>
                  <TableCell>{ticket.business_flags}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
}
