import {
  Alert,
  Chip,
  Container,
  Link,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

type SharedEvent = {
  client_name: string;
  template_name: string;
  occurrence_number: string;
  workflow_status: string;
  scheduled_at: string;
  due_at: string;
  completed_at: string | null;
  completion_summary: string | null;
  expires_at: string;
  tasks: Array<{
    title: string;
    status: string;
    resource_type: string;
    resource_path: string | null;
    check_date: string | null;
  }>;
};

export function PublicChecklistEventPage() {
  const { token = "" } = useParams();
  const event = useQuery({
    queryKey: ["public-checklist-event", token],
    queryFn: async () =>
      (await api.get<SharedEvent>(`/public/service-checklists/${token}`)).data,
    enabled: Boolean(token),
    retry: false,
  });
  return (
    <Container maxWidth="lg" sx={{ py: 5 }}>
      <Typography variant="h3" fontWeight={900}>Service checklist event</Typography>
      {!token && <Alert severity="warning" sx={{ mt: 2 }}>The checklist share token is missing.</Alert>}
      {event.isError && <Alert severity="error" sx={{ mt: 2 }}>This shared checklist is invalid or has expired.</Alert>}
      {event.data && <Stack spacing={2} mt={3}>
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>
            <Typography variant="h5" fontWeight={900} flex={1}>{event.data.client_name}</Typography>
            <Chip label={event.data.workflow_status.replaceAll("_", " ")} color={event.data.workflow_status === "COMPLETE" ? "success" : "warning"} />
          </Stack>
          <Typography>{event.data.template_name}</Typography>
          <Typography color="text.secondary">{event.data.occurrence_number} · Due {new Date(event.data.due_at).toLocaleString()}</Typography>
          {event.data.completed_at && <Typography color="text.secondary">Completed {new Date(event.data.completed_at).toLocaleString()}</Typography>}
          {event.data.completion_summary && <Typography mt={2}>{event.data.completion_summary}</Typography>}
        </Paper>
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table>
            <TableHead><TableRow><TableCell>Task</TableCell><TableCell>Status</TableCell><TableCell>Type</TableCell><TableCell>Path or URL</TableCell><TableCell>Check date</TableCell></TableRow></TableHead>
            <TableBody>{event.data.tasks.map((task, index) => <TableRow key={`${task.title}-${index}`}>
              <TableCell>{task.title}</TableCell>
              <TableCell><Chip size="small" label={task.status.replaceAll("_", " ")} color={["COMPLETE", "COMPLETED"].includes(task.status) ? "success" : task.status === "NEED_ATTENTION" ? "error" : "default"} /></TableCell>
              <TableCell>{task.resource_type.replaceAll("_", " ")}</TableCell>
              <TableCell>{task.resource_path ? /^https?:\/\//i.test(task.resource_path) ? <Link href={task.resource_path} target="_blank" rel="noreferrer">{task.resource_path}</Link> : task.resource_path : "—"}</TableCell>
              <TableCell>{task.check_date ? new Date(task.check_date).toLocaleDateString() : "—"}</TableCell>
            </TableRow>)}</TableBody>
          </Table>
        </Paper>
        <Typography variant="caption" color="text.secondary">This read-only link expires {new Date(event.data.expires_at).toLocaleString()}.</Typography>
      </Stack>}
    </Container>
  );
}
