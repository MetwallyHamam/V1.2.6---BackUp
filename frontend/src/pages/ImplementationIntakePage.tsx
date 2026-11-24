import { AssignmentTurnedIn, FactCheck, Refresh } from "@mui/icons-material";
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
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";

type IntakeRequest = {
  id: number;
  project_id: number;
  project_number: string;
  project_name: string;
  project_status: string;
  priority: string;
  requested_department_id: number;
  requested_team_id: number | null;
  requested_start_date: string | null;
  requested_end_date: string | null;
  capability_notes: string | null;
  status: string;
  row_version: number;
  response_notes: string | null;
  created_at: string;
};

type ProjectOptions = {
  teams: Array<{ id: number; name: string; department_id: number }>;
};

type Decision = "ACCEPTED" | "PROPOSED" | "RETURNED" | "REJECTED";

export function filterIntakeRequests(rows: IntakeRequest[], status: string) {
  return status === "ALL" ? rows : rows.filter((row) => row.status === status);
}

function label(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/^./, (character) => character.toUpperCase());
}

function statusColor(status: string): "default" | "info" | "success" | "warning" | "error" {
  if (status === "ACCEPTED") return "success";
  if (status === "PROPOSED") return "info";
  if (status === "RETURNED") return "warning";
  if (status === "REJECTED") return "error";
  return "default";
}

export function ImplementationIntakePage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("PENDING");
  const [selected, setSelected] = useState<IntakeRequest | null>(null);
  const [decision, setDecision] = useState<Decision>("ACCEPTED");
  const [teamId, setTeamId] = useState("");
  const [notes, setNotes] = useState("");

  const inbox = useQuery({
    queryKey: ["implementation-intake"],
    queryFn: async () => (await api.get<IntakeRequest[]>("/projects/assignment-requests/inbox")).data,
  });
  const options = useQuery({
    queryKey: ["project-options", "implementation-intake"],
    queryFn: async () => (await api.get<ProjectOptions>("/projects/options")).data,
  });
  const visible = useMemo(() => filterIntakeRequests(inbox.data ?? [], status), [inbox.data, status]);
  const teams = (options.data?.teams ?? []).filter(
    (team) => team.department_id === selected?.requested_department_id,
  );

  const respond = useMutation({
    mutationFn: async () => {
      if (!selected) return;
      await api.post(`/projects/assignment-requests/${selected.id}/respond`, {
        decision,
        expected_version: selected.row_version,
        requested_team_id: teamId ? Number(teamId) : null,
        response_notes: notes.trim() || null,
      });
    },
    onSuccess: async () => {
      setSelected(null);
      setTeamId("");
      setNotes("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["implementation-intake"] }),
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["project-summary"] }),
      ]);
    },
  });

  const openDecision = (request: IntakeRequest) => {
    setSelected(request);
    setDecision("ACCEPTED");
    setTeamId(request.requested_team_id ? String(request.requested_team_id) : "");
    setNotes(request.response_notes ?? "");
    respond.reset();
  };

  return (
    <Box sx={{ p: { xs: 1.25, md: 2.5 }, maxWidth: 1400, mx: "auto" }}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={1.5} mb={2}>
        <Box>
          <Stack direction="row" alignItems="center" gap={1}>
            <AssignmentTurnedIn color="primary" />
            <Typography variant="h4" fontWeight={850}>Implementation intake</Typography>
          </Stack>
          <Typography color="text.secondary">
            Review projects published to your department, confirm capacity, and route accepted work to a team.
          </Typography>
        </Box>
        <Stack direction="row" gap={1} alignItems="center">
          <Button component={Link} to="/implementation-analytics" variant="outlined" startIcon={<FactCheck />}>
            Performance
          </Button>
          <Button onClick={() => inbox.refetch()} variant="outlined" startIcon={<Refresh />} disabled={inbox.isFetching}>
            Refresh
          </Button>
        </Stack>
      </Stack>

      <Paper variant="outlined" sx={{ p: 1.5, mb: 1.5 }}>
        <Stack direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}>
          <TextField select size="small" label="Request status" value={status} onChange={(event) => setStatus(event.target.value)} sx={{ minWidth: 210 }}>
            {['PENDING', 'PROPOSED', 'ACCEPTED', 'RETURNED', 'REJECTED', 'ALL'].map((value) => <MenuItem key={value} value={value}>{label(value)}</MenuItem>)}
          </TextField>
          <Chip size="small" label={`${visible.length} request${visible.length === 1 ? "" : "s"}`} />
          <Typography variant="caption" color="text.secondary">
            Only requests addressed to your authorized department are shown.
          </Typography>
        </Stack>
      </Paper>

      {inbox.isLoading && <Stack alignItems="center" py={8}><CircularProgress /></Stack>}
      {inbox.isError && <Alert severity="error">{apiErrorMessage(inbox.error)}</Alert>}
      {!inbox.isLoading && !inbox.isError && visible.length === 0 && (
        <Alert severity="info">No {status === "ALL" ? "" : `${label(status).toLowerCase()} `}implementation requests are in your scope.</Alert>
      )}
      <Stack gap={1.25}>
        {visible.map((request) => (
          <Paper key={request.id} variant="outlined" sx={{ p: 1.5 }}>
            <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={1.5}>
              <Box>
                <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
                  <Typography fontWeight={850}>{request.project_number} · {request.project_name}</Typography>
                  <Chip size="small" color={statusColor(request.status)} label={label(request.status)} />
                  <Chip size="small" variant="outlined" label={label(request.priority)} />
                </Stack>
                <Typography variant="body2" color="text.secondary" mt={0.5}>
                  Requested {request.requested_start_date ?? "unscheduled"} → {request.requested_end_date ?? "unscheduled"}
                </Typography>
                {request.capability_notes && <Typography variant="body2" mt={0.75}>{request.capability_notes}</Typography>}
                {request.response_notes && <Alert severity="info" sx={{ mt: 1, py: 0 }}>Response: {request.response_notes}</Alert>}
              </Box>
              <Stack direction={{ xs: "row", md: "column" }} gap={1} minWidth={{ md: 170 }}>
                {(request.status === "PENDING" || request.status === "PROPOSED") && (
                  <Button variant="contained" onClick={() => openDecision(request)}>Review request</Button>
                )}
                <Button component={Link} to={`/projects/${request.project_id}/execution`} variant="outlined">Open project</Button>
              </Stack>
            </Stack>
          </Paper>
        ))}
      </Stack>

      <Dialog open={Boolean(selected)} onClose={() => !respond.isPending && setSelected(null)} fullWidth maxWidth="sm">
        <DialogTitle>Implementation intake decision</DialogTitle>
        <DialogContent>
          <Stack gap={1.5} pt={1}>
            <Alert severity="info">{selected?.project_number} · {selected?.project_name}</Alert>
            <TextField select label="Decision" value={decision} onChange={(event) => setDecision(event.target.value as Decision)}>
              <MenuItem value="ACCEPTED">Accept and open execution</MenuItem>
              <MenuItem value="PROPOSED">Propose capacity or schedule</MenuItem>
              <MenuItem value="RETURNED">Return for clarification</MenuItem>
              <MenuItem value="REJECTED">Reject request</MenuItem>
            </TextField>
            <TextField select label="Implementation team (optional)" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
              <MenuItem value="">Department queue / assign later</MenuItem>
              {teams.map((team) => <MenuItem key={team.id} value={team.id}>{team.name}</MenuItem>)}
            </TextField>
            <TextField multiline minRows={4} label="Response notes" value={notes} onChange={(event) => setNotes(event.target.value)} helperText="Explain capacity proposals, missing information, or rejection reasons." />
            {respond.isError && <Alert severity="error">{apiErrorMessage(respond.error)}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelected(null)} disabled={respond.isPending}>Cancel</Button>
          <Button variant="contained" onClick={() => respond.mutate()} disabled={respond.isPending}>
            {respond.isPending ? "Saving…" : "Submit decision"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
