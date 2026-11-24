import { Alert, Box, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

type PublicAssignment = {
  id: number; title: string; status: string; priority: string; progress_percent: number;
  due_at?: string | null; updated_at: string;
};

export function PublicWorkAssignmentPage() {
  const { token } = useParams();
  const assignment = useQuery({
    queryKey: ["public-work-assignment", token], enabled: Boolean(token), refetchInterval: 30_000,
    queryFn: async () => (await api.get<PublicAssignment>(`/public/work-assignments/${token}`)).data,
  });
  if (assignment.isLoading) return <LinearProgress />;
  if (assignment.isError || !assignment.data) return <Alert severity="error">This live task link is invalid or expired.</Alert>;
  const item = assignment.data;
  return <Box sx={{ maxWidth: 760, mx: "auto", p: { xs: 2, md: 5 } }}><Paper variant="outlined" sx={{ p: { xs: 2, md: 4 }, borderRadius: 4 }}><Stack spacing={2}><Typography variant="overline">Live work update · #{item.id}</Typography><Typography variant="h3" fontWeight={850}>{item.title}</Typography><Typography variant="h6">{item.status.replaceAll("_", " ")} · {item.priority}</Typography><Box><Typography variant="body2" color="text.secondary">Progress</Typography><Typography variant="h2" fontWeight={900}>{item.progress_percent}%</Typography></Box>{item.due_at && <Typography>Due: {new Date(item.due_at).toLocaleString()}</Typography>}<Typography variant="caption" color="text.secondary">Last updated {new Date(item.updated_at).toLocaleString()} · This page refreshes automatically.</Typography></Stack></Paper></Box>;
}
