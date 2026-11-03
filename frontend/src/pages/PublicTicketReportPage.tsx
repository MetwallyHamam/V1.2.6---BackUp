import { Download } from "@mui/icons-material";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Toolbar,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

type PublicReport = {
  report_number: string;
  report_type: string;
  title: string;
  version: number;
  published_at: string;
  expires_at: string;
  allow_download: boolean;
  meta: Record<string, string>;
  sections: { title: string; layout: string; rows: { label: string; value: string }[] }[];
};
export function PublicTicketReportPage() {
  const { token } = useParams();
  const report = useQuery({
    queryKey: ["public-ticket-report", token],
    enabled: !!token,
    queryFn: async () =>
      (await api.get<PublicReport>(`/public/ticket-reports/${token}`)).data,
  });
  const download = async () => {
    const response = await api.get(
      `/public/ticket-reports/${token}/download.pdf`,
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(response.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.data?.report_number}.pdf`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  if (report.isLoading)
    return (
      <Box minHeight="100vh" display="grid" sx={{ placeItems: "center" }}>
        <CircularProgress />
      </Box>
    );
  if (report.isError || !report.data)
    return (
      <Container maxWidth="sm" sx={{ py: 8 }}>
        <Alert severity="error">
          This report link is invalid, expired or revoked.
        </Alert>
      </Container>
    );
  const r = report.data;
  return (
    <Box minHeight="100vh" bgcolor="#f4f7fa" pb={{ xs: 10, sm: 4 }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: "#071d49" }}>
        <Toolbar sx={{ minHeight: { xs: 64, sm: 76 } }}>
          <Box flex={1}><Typography fontWeight={950} letterSpacing={1.2}>MILLENSYS</Typography><Typography variant="caption" sx={{ color: "#bae6fd" }}>SUPPORT HUB</Typography></Box>
          <Chip label="Secure client report" size="small" sx={{ color: "white", bgcolor: "rgba(255,255,255,.12)" }} />
        </Toolbar>
      </AppBar>
      <Container
        maxWidth="md"
        sx={{ py: { xs: 2, sm: 4 }, px: { xs: 1.5, sm: 3 } }}
      >
        <Paper elevation={0} sx={{ p: { xs: 2, sm: 4.5 }, borderRadius: { xs: 2, sm: 4 }, border: "1px solid", borderColor: "divider", overflow: "hidden" }}>
          <Typography variant="overline">
            {r.report_type} REPORT · {r.report_number}
          </Typography>
          <Typography
            variant="h4"
            component="h1"
            fontWeight={900}
            sx={{
              fontSize: { xs: "1.7rem", sm: "2.3rem" },
              overflowWrap: "anywhere",
            }}
          >
            {r.title}
          </Typography>
          <Typography color="text.secondary" mb={2}>
            Version {r.version} · Published{" "}
            {new Date(r.published_at).toLocaleString()}
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} gap={1.25} mb={4}>
            {[['Client', r.meta.client], ['Ticket', r.meta.ticket_number], ['Priority', r.meta.priority], ['Status', r.meta.status]].map(([label, value]) => <Box key={label} sx={{ flex: 1, bgcolor: "#f2f6f9", borderRadius: 2, p: 1.5, borderTop: "3px solid #0e7490" }}><Typography variant="caption" color="text.secondary" fontWeight={800}>{label.toUpperCase()}</Typography><Typography fontWeight={850} sx={{ overflowWrap: "anywhere" }}>{value || "—"}</Typography></Box>)}
          </Stack>
          <Stack spacing={3.5}>
            {r.sections.map((section) => (
              <Box key={section.title} component="section">
                <Typography variant="h6" fontWeight={900} mb={1.25} color="#071d49" sx={{ borderBottom: "2px solid #d8e1e8", pb: .75 }}>
                  {section.title}
                </Typography>
                {section.layout === "narrative" ? <Stack spacing={1.5}>{section.rows.map((row) => <Box key={row.label}><Typography variant="caption" fontWeight={900} color="#0e7490">{row.label.toUpperCase()}</Typography><Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", lineHeight: 1.7 }}>{row.value}</Typography></Box>)}</Stack> : <Box sx={{ overflowX: "auto" }}>
                  <Table
                    size="small"
                    sx={{
                      minWidth: { xs: 0, sm: 560 },
                      "& td": { verticalAlign: "top", py: 1.25 },
                    }}
                  >
                    {(section.layout === "timeline" || section.layout === "actions" || section.layout === "worklog") && <TableHead><TableRow>{(section.layout === "timeline" ? ["Time", "Event", "Owner"] : section.layout === "actions" ? ["Action", "Owner", "Due", "Status"] : ["Time", "Engineer", "Action", "Result"]).map((header) => <TableCell key={header} sx={{ bgcolor: "#071d49", color: "white", fontWeight: 800 }}>{header}</TableCell>)}</TableRow></TableHead>}
                    <TableBody>
                      {section.rows.map((row) => (
                        <TableRow key={row.label}>
                          <TableCell
                            sx={{
                              fontWeight: 800,
                              width: { xs: "38%", sm: 190 },
                            }}
                          >
                            {row.label}
                          </TableCell>
                          {(section.layout === "timeline" || section.layout === "actions" || section.layout === "worklog") ? row.value.split(" | ").map((value, index) => <TableCell key={index} sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{value}</TableCell>) : <TableCell sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{row.value}</TableCell>}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>}
              </Box>
            ))}
          </Stack>
          <Typography
            variant="caption"
            color="text.secondary"
            display="block"
            mt={3}
          >
            This secure link expires {new Date(r.expires_at).toLocaleString()}.
          </Typography>
        </Paper>
      </Container>
      {r.allow_download && (
        <Box
          sx={{
            position: { xs: "fixed", sm: "static" },
            bottom: 0,
            left: 0,
            right: 0,
            p: { xs: 1.5, sm: 0 },
            bgcolor: { xs: "background.paper", sm: "transparent" },
            boxShadow: { xs: 4, sm: 0 },
            display: "flex",
            justifyContent: "center",
          }}
        >
          <Button
            fullWidth={false}
            sx={{ width: { xs: "100%", sm: "auto" } }}
            size="large"
            variant="contained"
            startIcon={<Download />}
            onClick={download}
          >
            Download PDF
          </Button>
        </Box>
      )}
    </Box>
  );
}
