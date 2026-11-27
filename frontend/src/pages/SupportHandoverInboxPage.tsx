import { Alert, Button, Chip, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Package = {
  project_id: number; project_number: string; project_name: string;
  status: string; readiness_percent: number; submitted_at: string | null;
};

export function SupportHandoverInboxPage() {
  const { hasPermission } = useAuth();
  const query = useQuery({
    queryKey: ["support-handover-inbox"],
    queryFn: async () => (await api.get<Package[]>("/project-handover-inbox")).data,
    refetchOnMount: "always",
  });
  return (
    <Stack spacing={2} sx={{ maxWidth: 1200, mx: "auto" }}>
      <Typography component="h1" variant="h4" fontWeight={800}>Support Handover Inbox</Typography>
      {query.isPending && <LinearProgress aria-label="Loading handovers" />}
      {query.isError && <Alert severity="error">{apiErrorMessage(query.error)}</Alert>}
      {query.isSuccess && !query.data.length && <Alert severity="info">No submitted handovers in your receiving scope.</Alert>}
      {(query.data ?? []).map((item) => (
        <Paper key={item.project_id} variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
          <Stack direction={{ xs: "column", sm: "row" }} alignItems={{ sm: "center" }} gap={1.5}>
            <Stack sx={{ flex: 1 }}>
              <Typography component="h2" fontWeight={750}>{item.project_number} · {item.project_name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {item.readiness_percent}% ready{item.submitted_at && ` · Submitted ${new Date(item.submitted_at).toLocaleDateString()}`}
              </Typography>
            </Stack>
            <Chip size="small" label={item.status.replaceAll("_", " ")} sx={{ alignSelf: "flex-start" }} />
            {hasPermission("project.portfolio.view") && hasPermission("handover.view") && (
              <Button component={Link} to={`/projects/${item.project_id}/handover`}>Open handover</Button>
            )}
          </Stack>
        </Paper>
      ))}
      {query.data?.length === 50 && <Typography variant="caption">Showing the 50 most recently updated handovers.</Typography>}
    </Stack>
  );
}
