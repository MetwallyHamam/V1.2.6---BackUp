import { Alert, Box, Chip, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

type Tracking = {
  code: string;
  name: string;
  client_name: string;
  status: string;
  planned_start_at: string;
  planned_end_at: string;
  share_expires_at: string;
  approved_software_version?: string;
  summary: { completion_percent: number; planned_minutes: number; actual_minutes: number; total_issues: number; open_issues: number; pending_implementation_phases: number };
  steps: { id: number; title: string; owner_name?: string; status: string; planned_duration_minutes: number; actual_duration_minutes: number; completion_comment?: string }[];
  issues: { id: number; title: string; description: string; issue_type_name?: string; priority: string; status: string; occurrence_stage: string; affects_workflow: boolean; update_needed: boolean; implementation_phase?: string; next_action?: string; resolution_summary?: string; evidence: { id: number; evidence_type: string; label?: string; external_url?: string }[] }[];
  comments: { id: number; author_name?: string; body: string; created_at: string }[];
};

const minutes = (value: number) => value >= 60 ? `${Math.floor(value / 60)}h ${value % 60}m` : `${value}m`;

export function PublicDeploymentTrackingPage() {
  const { token } = useParams();
  const tracking = useQuery({
    queryKey: ["public-deployment-tracking", token],
    enabled: !!token,
    queryFn: async () => (await api.get<Tracking>(`/public/deployment-shares/${token}`)).data,
    refetchInterval: 15_000,
  });
  const data = tracking.data;
  return <Box sx={{ minHeight: "100vh", bgcolor: "#f4f7fa", py: 4, px: 2 }}><Stack spacing={2} sx={{ maxWidth: 1050, mx: "auto" }}>
    <Paper sx={{ p: { xs: 2.5, md: 4 }, color: "white", background: "linear-gradient(135deg,#102a43,#1f6f8b)", borderRadius: 3 }}>
      <Typography variant="overline" sx={{ opacity: .8 }}>MILLENSYS · SUPPORT HUB</Typography>
      <Typography variant="h4" fontWeight={900}>Deployment live tracking</Typography>
      <Typography sx={{ opacity: .85 }}>Automatically refreshes every 15 seconds</Typography>
    </Paper>
    {tracking.isError && <Alert severity="error">This tracking link is unavailable, revoked, or expired.</Alert>}
    {tracking.isLoading && <LinearProgress />}
    {data && <>
      <Paper sx={{ p: 3, borderRadius: 3 }}><Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}><Box><Typography variant="h5" fontWeight={850}>{data.client_name}</Typography><Typography>{data.code} · {data.name}</Typography><Typography color="text.secondary">{new Date(data.planned_start_at).toLocaleString()} → {new Date(data.planned_end_at).toLocaleString()}</Typography></Box><Chip label={data.status.replaceAll("_", " ")} color={data.status === "COMPLETED" ? "success" : data.status === "ACTIVE" ? "primary" : "default"} /></Stack>
      <Typography mt={2} fontWeight={800}>{data.summary.completion_percent}% complete</Typography><LinearProgress variant="determinate" value={data.summary.completion_percent} sx={{ height: 10, borderRadius: 5, mt: 1 }} /><Stack direction="row" gap={1} flexWrap="wrap" mt={2}>{data.approved_software_version && <Chip label={`Approved version ${data.approved_software_version}`} color="success" />}<Chip label={`Planned ${minutes(data.summary.planned_minutes)}`} /><Chip label={`Actual ${minutes(data.summary.actual_minutes)}`} color="info" /><Chip label={`${data.summary.open_issues} open issues`} color={data.summary.open_issues ? "warning" : "success"} /><Chip label={`${data.summary.pending_implementation_phases} pending phases`} /></Stack></Paper>
      <Paper sx={{ p: 3, borderRadius: 3 }}><Typography variant="h6" fontWeight={850} mb={1.5}>Deployment timeline</Typography><Stack spacing={1}>{data.steps.map((step) => <Paper key={step.id} variant="outlined" sx={{ p: 1.5, borderLeft: "4px solid", borderLeftColor: step.status === "COMPLETED" ? "success.main" : step.status === "IN_PROGRESS" ? "primary.main" : step.status === "BLOCKED" ? "error.main" : "grey.400" }}><Stack direction="row" justifyContent="space-between" gap={1}><Box><Typography fontWeight={800}>{step.title}</Typography><Typography variant="body2" color="text.secondary">{step.owner_name ?? "Plan owner"} · Planned {minutes(step.planned_duration_minutes)} · Actual {minutes(step.actual_duration_minutes)}</Typography>{step.completion_comment && <Typography variant="body2" mt={.5}>{step.completion_comment}</Typography>}</Box><Chip size="small" label={step.status.replaceAll("_", " ")} /></Stack></Paper>)}</Stack></Paper>
      {!!data.issues.length && <Paper sx={{ p: 3, borderRadius: 3 }}><Typography variant="h6" fontWeight={850} mb={1.5}>Issues and follow-up</Typography><Stack spacing={1}>{data.issues.map((issue) => <Paper key={issue.id} variant="outlined" sx={{ p: 1.5 }}><Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}><Typography fontWeight={800}>{issue.title}</Typography><Stack direction="row" gap={0.5} flexWrap="wrap"><Chip size="small" variant="outlined" label={issue.issue_type_name || "Issue"} /><Chip size="small" label={`${issue.priority} · ${issue.status.replaceAll("_", " ")}`} /></Stack></Stack><Typography variant="body2" color="text.secondary">{issue.occurrence_stage.replaceAll("_", " ")} · {issue.implementation_phase ?? "General"}</Typography><Stack direction="row" gap={0.5} flexWrap="wrap" my={0.75}><Chip size="small" color={issue.affects_workflow ? "warning" : "default"} label={`Affects workflow: ${issue.affects_workflow ? "Yes" : "No"}`} /><Chip size="small" color={issue.update_needed ? "info" : "default"} label={`Update needed: ${issue.update_needed ? "Yes" : "No"}`} /></Stack><Typography variant="body2">{issue.description}</Typography><Typography variant="body2" color="text.secondary">{issue.resolution_summary ?? issue.next_action ?? "Follow-up in progress"}</Typography>{issue.evidence?.filter((item) => item.evidence_type === "LINK").map((item) => <Typography key={item.id} component="a" href={item.external_url} target="_blank" rel="noreferrer" display="block" variant="body2">{item.label || "Shared evidence"}</Typography>)}</Paper>)}</Stack></Paper>}
      {!!data.comments.length && <Paper sx={{ p: 3, borderRadius: 3 }}><Typography variant="h6" fontWeight={850}>Latest updates</Typography>{data.comments.slice(-10).reverse().map((comment) => <Box key={comment.id} sx={{ mt: 1.5 }}><Typography fontWeight={750}>{comment.author_name ?? "Deployment team"}</Typography><Typography>{comment.body}</Typography><Typography variant="caption" color="text.secondary">{new Date(comment.created_at).toLocaleString()}</Typography></Box>)}</Paper>}
      <Typography variant="caption" textAlign="center" color="text.secondary">Link expires {new Date(data.share_expires_at).toLocaleString()}</Typography>
    </>}
  </Stack></Box>;
}
