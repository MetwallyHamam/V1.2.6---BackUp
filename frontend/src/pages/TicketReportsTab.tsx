import {
  Add,
  AutoAwesome,
  ContentCopy,
  DeleteOutline,
  Download,
  Edit,
  Link,
  Publish,
  Refresh,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";

type Report = {
  id: number;
  report_number: string;
  ticket_id: number;
  ticket_number: string;
  client: string;
  report_type: "TICKET" | "INCIDENT";
  expected_report_type: "TICKET" | "INCIDENT";
  template_mismatch: boolean;
  status: string;
  title: string;
  data: Record<string, unknown>;
  published_version?: number;
  updated_at: string;
};
type ShareLink = {
  id: number;
  recipient_name?: string;
  recipient_email?: string;
  expires_at: string;
  revoked_at?: string;
  allow_download: boolean;
};
type ReportField = [string, string];
type ReportFieldGroup = { title: string; description: string; fields: ReportField[] };
const ticketFieldGroups: ReportFieldGroup[] = [
  { title: "Request details", description: "The client request and the reported condition.", fields: [["subject", "Subject"], ["description", "Request description"]] },
  { title: "Resolution and outcome", description: "What was done, the final result and client acceptance.", fields: [["resolution_summary", "Resolution summary"], ["customer_confirmation", "Customer confirmation"]] },
  { title: "References", description: "Optional client-safe notes and supporting references.", fields: [["additional_notes", "Additional notes"], ["attachments_references", "Attachments and references"]] },
];
const incidentFieldGroups: ReportFieldGroup[] = [
  { title: "Executive conclusion", description: "A concise management summary of the incident, impact, recovery and prevention.", fields: [["executive_summary", "Executive summary"]] },
  { title: "Incident ownership and detection", description: "Accountability and the confirmed detection and restoration timestamps.", fields: [["incident_owner", "Incident owner"], ["technical_lead", "Technical lead"], ["detection_time", "Detection time"], ["restoration_time", "Service restoration time"]] },
  { title: "Business and safety impact", description: "Operational scope, affected users, safety and security consequences.", fields: [["business_impact", "Business and operational impact"], ["affected_users", "Affected users"], ["patient_safety", "Patient safety impact"], ["security_incident", "Security impact"]] },
  { title: "Detection, response and evidence", description: "How the incident was detected, managed and technically verified.", fields: [["detection_and_response", "Detection and response"], ["technical_evidence", "Technical evidence"]] },
  { title: "Root cause and recovery", description: "Confirmed cause, contributing conditions, recovery and permanent remediation.", fields: [["root_cause", "Root cause"], ["contributing_factors", "Contributing factors"], ["resolution_summary", "Resolution and recovery"], ["permanent_fix", "Permanent fix"]] },
  { title: "Communication and closure", description: "Client communication, formal approval and supporting references.", fields: [["client_communications", "Client communications"], ["closure_approval", "Closure approval"], ["attachments_references", "Attachments and references"]] },
];

type StructuredRow = Record<string, unknown> & {
  id?: string;
  source?: string;
  included?: boolean;
};

const fieldHelp: Record<string, string> = {
  executive_summary: "A concise client-ready conclusion: what happened, impact, recovery and prevention.",
  customer_confirmation: "Who confirmed the outcome, through which channel, and when.",
  root_cause: "Use confirmed facts only. If investigation is open, state that clearly.",
  closure_approval: "Record the accountable approver and the closure basis.",
};

function RowEditor({
  title,
  description,
  rows,
  columns,
  addLabel,
  onChange,
}: {
  title: string;
  description: string;
  rows: StructuredRow[];
  columns: { key: string; label: string; type?: string; flex?: number }[];
  addLabel: string;
  onChange: (rows: StructuredRow[]) => void;
}) {
  const update = (index: number, key: string, value: unknown) =>
    onChange(rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  return (
    <Paper variant="outlined" sx={{ p: { xs: 1.5, sm: 2 }, borderRadius: 3 }}>
      <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }} mb={1.5}>
        <Box flex={1}>
          <Typography fontWeight={850}>{title}</Typography>
          <Typography variant="body2" color="text.secondary">{description}</Typography>
        </Box>
        <Button startIcon={<Add />} variant="outlined" onClick={() => onChange([...rows, { id: `manual-${crypto.randomUUID()}`, source: "MANUAL", included: true, ...Object.fromEntries(columns.map((column) => [column.key, ""])) }])}>
          {addLabel}
        </Button>
      </Stack>
      <Stack spacing={1.25}>
        {rows.map((row, index) => (
          <Paper key={String(row.id ?? index)} variant="outlined" sx={{ p: 1.25, bgcolor: row.source === "SYSTEM" ? "action.hover" : "background.paper" }}>
            <Stack direction="row" alignItems="center" gap={1} mb={1}>
              <Chip size="small" label={row.source === "SYSTEM" ? "From ticket" : "Manual"} color={row.source === "SYSTEM" ? "info" : "default"} />
              <FormControlLabel sx={{ ml: "auto", mr: 0 }} control={<Switch size="small" checked={row.included !== false} onChange={(e) => update(index, "included", e.target.checked)} />} label="Include" />
              {row.source !== "SYSTEM" && <Button color="error" size="small" startIcon={<DeleteOutline />} onClick={() => onChange(rows.filter((_, i) => i !== index))}>Remove</Button>}
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} gap={1}>
              {columns.map((column) => <TextField key={column.key} size="small" type={column.type} label={column.label} value={String(row[column.key] ?? "")} onChange={(e) => update(index, column.key, e.target.value)} multiline={column.key === "event" || column.key === "action"} minRows={column.key === "event" || column.key === "action" ? 2 : undefined} sx={{ flex: column.flex ?? 1 }} InputLabelProps={column.type === "datetime-local" || column.type === "date" ? { shrink: true } : undefined} />)}
            </Stack>
          </Paper>
        ))}
        {!rows.length && <Alert severity="info">No events are available yet. Add the first report event.</Alert>}
      </Stack>
    </Paper>
  );
}

function downloadBlob(path: string, name: string) {
  api.get(path, { responseType: "blob" }).then((response) => {
    const url = URL.createObjectURL(response.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}

export function TicketReportsTab() {
  const cache = useQueryClient(),
    [searchParams, setSearchParams] = useSearchParams(),
    [search, setSearch] = useState(""),
    [type, setType] = useState(""),
    [status, setStatus] = useState(""),
    [editing, setEditing] = useState<Report | null>(null),
    [share, setShare] = useState<Report | null>(null),
    [shareUrl, setShareUrl] = useState(""),
    [days, setDays] = useState(7),
    [recipient, setRecipient] = useState(""),
    [email, setEmail] = useState(""),
    [allowDownload, setAllowDownload] = useState(true),
    [promptOpen, setPromptOpen] = useState(false),
    [error, setError] = useState("");
  const reports = useQuery({
    queryKey: ["ticket-reports", search, type, status],
    queryFn: async () =>
      (
        await api.get<Report[]>("/ticket-reports", {
          params: {
            search: search || undefined,
            report_type: type || undefined,
            report_status: status || undefined,
          },
        })
      ).data,
  });
  const links = useQuery({
    queryKey: ["ticket-report-share-links", share?.id],
    enabled: !!share,
    queryFn: async () =>
      (await api.get<ShareLink[]>(`/ticket-reports/${share?.id}/share-links`))
        .data,
  });
  const save = useMutation({
    mutationFn: async (row: Report) =>
      (
        await api.patch<Report>(`/ticket-reports/${row.id}`, {
          title: row.title,
          data: row.data,
        })
      ).data,
    onSuccess: async () => {
      closeEditor();
      await cache.invalidateQueries({ queryKey: ["ticket-reports"] });
    },
    onError: (e) => setError(apiErrorMessage(e, "Could not save the report.")),
  });
  const publish = useMutation({
    mutationFn: async (row: Report) =>
      (await api.post<Report>(`/ticket-reports/${row.id}/publish`)).data,
    onSuccess: async () =>
      cache.invalidateQueries({ queryKey: ["ticket-reports"] }),
    onError: (e) =>
      setError(apiErrorMessage(e, "Could not publish the report.")),
  });
  const createShare = useMutation({
    mutationFn: async () => {
      if (!share) return;
      return (
        await api.post<{ url: string }>(
          `/ticket-reports/${share.id}/share-links`,
          {
            expires_in_days: days,
            recipient_name: recipient || null,
            recipient_email: email || null,
            allow_download: allowDownload,
          },
        )
      ).data;
    },
    onSuccess: async (r) => {
      setShareUrl(r?.url ?? "");
      await links.refetch();
    },
    onError: (e) =>
      setError(apiErrorMessage(e, "Could not create the share link.")),
  });
  const revokeShare = useMutation({
    mutationFn: async (linkId: number) =>
      api.post(`/ticket-reports/${share?.id}/share-links/${linkId}/revoke`),
    onSuccess: async () => links.refetch(),
    onError: (e) =>
      setError(apiErrorMessage(e, "Could not revoke the share link.")),
  });
  const fieldGroups =
    editing?.report_type === "INCIDENT" ? incidentFieldGroups : ticketFieldGroups;
  const fields = fieldGroups.flatMap((group) => group.fields);
  useEffect(() => {
    const reportId = Number(searchParams.get("report_id"));
    if (!reportId || !reports.data || editing) return;
    const report = reports.data.find((item) => item.id === reportId);
    if (report) setEditing(structuredClone(report));
  }, [editing, reports.data, searchParams]);
  const closeEditor = () => {
    setEditing(null);
    const next = new URLSearchParams(searchParams);
    next.delete("report_id");
    setSearchParams(next, { replace: true });
  };
  const reportKind = editing?.report_type === "INCIDENT" ? "incident" : "ticket service";
  const reportSpecificInstructions = editing?.report_type === "INCIDENT"
    ? `For the incident report:
- Write an executive conclusion covering what happened, business impact, duration, restoration and prevention.
- Derive the detection and response narrative from the chronological ticket events and work performed.
- Build the root-cause assessment only from the description, actions, results, resolution and recorded evidence. Clearly label a conclusion as "Assessment:" when it is inferred rather than explicitly confirmed.
- Explain contributing factors only when they are supported by the record.
- Distinguish the immediate recovery action from the permanent fix.
- Summarize patient-safety and security impact from their recorded flags and supporting facts.
- After the form fields, suggest useful missing INCIDENT TIMELINE rows and CORRECTIVE AND PREVENTIVE ACTION rows. Do not repeat existing rows.`
    : `For the ticket service report:
- Rewrite the request as a concise client-ready description.
- Summarize the approved worklogs and ticket events in chronological order.
- Explain the resolution, observable outcome and customer confirmation separately.
- Keep the report operational and concise; do not add incident-analysis language unless it exists in the ticket.`;
  const aiPrompt = editing
    ? `You are a senior service-management report writer preparing a professional ${reportKind} report for a client.

OBJECTIVE
Complete every report field as fully as possible by analyzing and combining the supplied ticket facts, description, classification, lifecycle dates, SLA values, worklogs, events, actions, results and resolution. Improve spelling, grammar and clarity. Convert short engineer notes into concise professional language without changing their meaning.

EVIDENCE AND INFERENCE RULES
1. Treat the supplied ticket data as the only source of truth.
2. Reuse facts across the record to complete fields that are currently empty. Do not return "missing" when an answer can reasonably be derived from recorded information.
3. You may make a conservative professional inference when it follows directly from recorded facts. Prefix that text with "Assessment:" so the engineer can review it.
4. Never invent a person, timestamp, client confirmation, technical command, affected-user count, outage duration, root cause, evidence, SLA result or completed action.
5. When no supported answer or safe inference exists, write: "Not recorded in the ticket – engineer confirmation required."
6. Correct obvious spelling and wording errors while preserving product names, ticket numbers and technical meaning.
7. Use client-safe language. Exclude credentials, access information, private notes, personal contact details, commercial information and unsupported blame.
8. Do not mention AI, these instructions or the source data format in the drafted report.

${reportSpecificInstructions}

OUTPUT FORMAT
- Return plain text only; do not return JSON or Markdown tables.
- Use each exact heading below, followed by copy-ready text for that field.
- Complete every heading and keep each field separate.
- Do not combine or rename headings.

REPORT FIELDS
${fields.map(([, label]) => label.toUpperCase()).join("\n")}

TICKET DATA
${JSON.stringify(editing.data, null, 2)}

At the end, add ENGINEER CONFIRMATION REQUIRED and list only material statements that could not be established or safely inferred. Do not list fields completed from evidence.`
    : "";
  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={1}
          alignItems={{ md: "center" }}
        >
          <Box flex={1}>
            <Typography variant="h5" fontWeight={900}>
              Ticket Reports
            </Typography>
            <Typography color="text.secondary">
              Saved drafts, published versions, exports and secure client links
            </Typography>
          </Box>
          <TextField
            size="small"
            label="Search report, ticket or client"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <TextField
            select
            size="small"
            label="Type"
            value={type}
            onChange={(e) => setType(e.target.value)}
            sx={{ minWidth: 145 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="TICKET">Ticket</MenuItem>
            <MenuItem value="INCIDENT">Incident</MenuItem>
          </TextField>
          <TextField
            select
            size="small"
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            sx={{ minWidth: 145 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="DRAFT">Draft</MenuItem>
            <MenuItem value="PUBLISHED">Published</MenuItem>
          </TextField>
          <Button startIcon={<Refresh />} onClick={() => reports.refetch()}>
            Refresh
          </Button>
        </Stack>
      </Paper>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <Paper variant="outlined" sx={{ p: 2, flex: 1, borderRadius: 3, borderTop: "4px solid", borderTopColor: "primary.main" }}>
          <Typography variant="overline" color="primary.main" fontWeight={900}>Ticket report</Typography>
          <Typography fontWeight={850}>Routine client service record</Typography>
          <Typography variant="body2" color="text.secondary">Request, approved work performed, resolution, customer confirmation and SLA result.</Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2, flex: 1, borderRadius: 3, borderTop: "4px solid", borderTopColor: "warning.main" }}>
          <Typography variant="overline" color="warning.dark" fontWeight={900}>Incident report</Typography>
          <Typography fontWeight={850}>Formal operational incident record</Typography>
          <Typography variant="body2" color="text.secondary">Impact, timeline, root cause, recovery, preventive actions and closure approval.</Typography>
        </Paper>
      </Stack>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      {reports.isLoading ? (
        <CircularProgress />
      ) : reports.isError ? (
        <Alert severity="error">Reports could not be loaded.</Alert>
      ) : !reports.data?.length ? (
        <Alert severity="info">
          No saved reports match the selected filters.
        </Alert>
      ) : (
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                {[
                  "Report",
                  "Ticket",
                  "Client",
                  "Type",
                  "Status",
                  "Version",
                  "Updated",
                  "Actions",
                ].map((x) => (
                  <TableCell key={x}>{x}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {reports.data.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>
                    <b>{row.report_number}</b>
                    <Typography variant="caption" display="block">
                      {row.title}
                    </Typography>
                  </TableCell>
                  <TableCell>{row.ticket_number}</TableCell>
                  <TableCell>{row.client}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={row.template_mismatch ? `${row.report_type} · Wrong template` : row.report_type}
                      color={row.template_mismatch ? "error" : row.report_type === "INCIDENT" ? "warning" : "primary"}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={row.status}
                      color={row.status === "PUBLISHED" ? "success" : "default"}
                    />
                  </TableCell>
                  <TableCell>{row.published_version ?? "—"}</TableCell>
                  <TableCell>
                    {new Date(row.updated_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" gap={0.5} flexWrap="wrap">
                      <Button
                        size="small"
                        startIcon={<Edit />}
                        onClick={() => setEditing(structuredClone(row))}
                      >
                        Edit
                      </Button>
                      <Button
                        size="small"
                        startIcon={<Publish />}
                        disabled={row.template_mismatch}
                        onClick={() => publish.mutate(row)}
                      >
                        Publish
                      </Button>
                      {row.published_version && (
                        <>
                          <Button
                            size="small"
                            startIcon={<Download />}
                            onClick={() =>
                              downloadBlob(
                                `/ticket-reports/${row.id}/export.docx`,
                                `${row.report_number}.docx`,
                              )
                            }
                          >
                            Word
                          </Button>
                          <Button
                            size="small"
                            onClick={() =>
                              downloadBlob(
                                `/ticket-reports/${row.id}/export.pdf`,
                                `${row.report_number}.pdf`,
                              )
                            }
                          >
                            PDF
                          </Button>
                          <Button
                            size="small"
                            startIcon={<Link />}
                            onClick={() => {
                              setShare(row);
                              setShareUrl("");
                            }}
                          >
                            Share
                          </Button>
                        </>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
      <Dialog
        open={!!editing}
        onClose={closeEditor}
        fullWidth
        maxWidth="lg"
        fullScreen={false}
        PaperProps={{ sx: { borderRadius: { xs: 0, sm: 3 }, minHeight: { sm: "82vh" } } }}
      >
        <DialogTitle sx={{ bgcolor: "#071d49", color: "white", py: 2.5 }}>
          <Typography variant="overline" sx={{ opacity: .75 }}>{editing?.report_number}</Typography>
          <Typography variant="h5" fontWeight={900}>Prepare {editing?.report_type === "INCIDENT" ? "Incident" : "Ticket Service"} Report</Typography>
        </DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2, borderRadius: 2 }}>
            Imported ticket facts remain unchanged. Your edits and manual rows belong only to this report draft; empty optional sections are omitted from the export.
          </Alert>
          {editing && (
            <Stack spacing={2}>
              {editing.template_mismatch && (
                <Alert severity="error">
                  This legacy report uses the wrong template for its ticket. It cannot be published again. Close it and prepare a new {editing.expected_report_type === "INCIDENT" ? "standard Incident Report" : "Ticket Service Report"} from the ticket menu.
                </Alert>
              )}
              <TextField
                label="Report title"
                value={editing.title}
                onChange={(e) =>
                  setEditing({ ...editing, title: e.target.value })
                }
              />
              <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>
                <Box flex={1}>
                  <Typography fontWeight={850}>Human-written report content</Typography>
                  <Typography variant="body2" color="text.secondary">Review all suggested text before publishing.</Typography>
                </Box>
                <Button startIcon={<AutoAwesome />} variant="outlined" onClick={() => setPromptOpen(true)}>Generate AI prefill prompt</Button>
              </Stack>
              <Divider />
              {fieldGroups.map((group) => (
                <Paper key={group.title} variant="outlined" sx={{ p: { xs: 1.5, sm: 2 }, borderRadius: 3 }}>
                  <Typography variant="h6" fontWeight={900}>{group.title}</Typography>
                  <Typography variant="body2" color="text.secondary" mb={2}>{group.description}</Typography>
                  <Stack spacing={1.5}>
                    {group.fields.map(([key, label]) => (
                      <TextField
                        key={key}
                        label={label}
                        multiline
                        minRows={key === "description" || key.includes("summary") || key.includes("impact") ? 3 : 2}
                        value={String(editing.data[key] ?? "")}
                        onChange={(e) => setEditing({ ...editing, data: { ...editing.data, [key]: e.target.value } })}
                        helperText={fieldHelp[key]}
                      />
                    ))}
                  </Stack>
                </Paper>
              ))}
              {editing.report_type === "TICKET" ? (
                <RowEditor title="Work performed and ticket events" description="Approved worklogs are imported automatically. Add any client-safe event that was not recorded as a worklog." addLabel="Add ticket event" rows={(editing.data.work_performed as StructuredRow[] | undefined) ?? []} columns={[{ key: "time", label: "Date and time", type: "datetime-local", flex: 1.2 }, { key: "engineer", label: "Engineer / owner" }, { key: "action", label: "Action or event", flex: 2.2 }, { key: "result", label: "Result" }]} onChange={(rows) => setEditing({ ...editing, data: { ...editing.data, work_performed: rows } })} />
              ) : (
                <>
                  <RowEditor title="Incident timeline" description="System events are imported from ticket history. Add missing events manually or exclude irrelevant entries." addLabel="Add timeline row" rows={(editing.data.timeline as StructuredRow[] | undefined) ?? []} columns={[{ key: "time", label: "Date and time", type: "datetime-local", flex: 1.2 }, { key: "event", label: "Event", flex: 2.5 }, { key: "owner", label: "Owner / source" }]} onChange={(rows) => setEditing({ ...editing, data: { ...editing.data, timeline: rows } })} />
                  <RowEditor title="Corrective and preventive actions" description="Track each committed action with accountable ownership and status." addLabel="Add action" rows={(editing.data.corrective_actions as StructuredRow[] | undefined) ?? []} columns={[{ key: "action", label: "Action", flex: 2.5 }, { key: "owner", label: "Owner" }, { key: "due_date", label: "Due date", type: "date" }, { key: "status", label: "Status" }]} onChange={(rows) => setEditing({ ...editing, data: { ...editing.data, corrective_actions: rows } })} />
                </>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeEditor}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!editing || save.isPending}
            onClick={() => editing && save.mutate(editing)}
          >
            Save draft
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={promptOpen} onClose={() => setPromptOpen(false)} fullWidth maxWidth="md" PaperProps={{ sx: { borderRadius: 3 } }}>
        <DialogTitle><Typography variant="h6" fontWeight={900}>External AI prefill prompt</Typography><Typography variant="body2" color="text.secondary">The AI will draft every report field from the available ticket evidence. Review all returned text before placing it in the report.</Typography></DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>External AI services may retain submitted content. Follow your organization’s data-handling policy and remove anything sensitive.</Alert>
          <TextField fullWidth multiline minRows={18} value={aiPrompt} InputProps={{ readOnly: true }} />
        </DialogContent>
        <DialogActions><Button onClick={() => setPromptOpen(false)}>Close</Button><Button variant="contained" startIcon={<ContentCopy />} onClick={() => navigator.clipboard.writeText(aiPrompt)}>Copy prompt</Button></DialogActions>
      </Dialog>
      <Dialog
        open={!!share}
        onClose={() => setShare(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Share published PDF</DialogTitle>
        <DialogContent>
          <Stack spacing={2} mt={1}>
            <TextField
              type="number"
              label="Link expires after days"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            />
            <TextField
              label="Recipient name"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
            />
            <TextField
              label="Recipient email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={allowDownload}
                  onChange={(e) => setAllowDownload(e.target.checked)}
                />
              }
              label="Allow PDF download"
            />
            {shareUrl && (
              <Alert
                severity="success"
                action={
                  <Button
                    startIcon={<ContentCopy />}
                    onClick={() => navigator.clipboard.writeText(shareUrl)}
                  >
                    Copy
                  </Button>
                }
              >
                <Typography sx={{ overflowWrap: "anywhere" }}>
                  {shareUrl}
                </Typography>
              </Alert>
            )}
            {!!links.data?.length && (
              <Box>
                <Typography fontWeight={800} mb={1}>
                  Link history
                </Typography>
                <Stack spacing={1}>
                  {links.data.map((item) => (
                    <Paper key={item.id} variant="outlined" sx={{ p: 1.5 }}>
                      <Stack
                        direction={{ xs: "column", sm: "row" }}
                        gap={1}
                        alignItems={{ sm: "center" }}
                      >
                        <Box flex={1}>
                          <Typography fontWeight={700}>
                            {item.recipient_name || "Unnamed recipient"}
                          </Typography>
                          <Typography variant="caption" display="block">
                            {item.recipient_email || "No email recorded"} ·
                            expires {new Date(item.expires_at).toLocaleString()}
                          </Typography>
                        </Box>
                        <Chip
                          size="small"
                          label={item.revoked_at ? "Revoked" : "Active"}
                          color={item.revoked_at ? "default" : "success"}
                        />
                        {!item.revoked_at && (
                          <Button
                            size="small"
                            color="error"
                            onClick={() => revokeShare.mutate(item.id)}
                          >
                            Revoke
                          </Button>
                        )}
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              </Box>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShare(null)}>Close</Button>
          <Button
            variant="contained"
            disabled={createShare.isPending}
            onClick={() => createShare.mutate()}
          >
            Create secure link
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
