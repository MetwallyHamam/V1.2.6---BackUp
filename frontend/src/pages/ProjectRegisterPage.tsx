import { Alert, Button, Chip, LinearProgress, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { Project } from "./ProjectWorkspacePage";

type Entry = {
  id: number; kind: "RISK" | "CHANGE"; title: string; impact: string; due_date: string;
  owner_user_id: number; status: string; decision_reason?: string; revision_id?: number;
};
type Decision = "MITIGATED" | "APPROVED" | "REJECTED";

export function ProjectRegisterPage() {
  const project = useOutletContext<Project>();
  const { user, hasPermission } = useAuth();
  const client = useQueryClient();
  const key = ["project-register", project.id];
  const url = `/projects/${project.id}/register`;
  const register = useQuery({ queryKey: key, queryFn: async () => (await api.get<Entry[]>(url)).data });
  const [kind, setKind] = useState<Entry["kind"]>("RISK");
  const [title, setTitle] = useState("");
  const [impact, setImpact] = useState("");
  const [due, setDue] = useState("");
  const [selected, setSelected] = useState<Entry | null>(null);
  const [reason, setReason] = useState("");
  const [revision, setRevision] = useState("");
  const create = useMutation({
    mutationFn: () => api.post(url, { kind, title: title.trim(), impact: impact.trim(), due_date: due }),
    onSuccess: async () => {
      setTitle(""); setImpact(""); setDue("");
      await client.invalidateQueries({ queryKey: key });
    },
  });
  const decide = useMutation({
    mutationFn: ({ id, status }: { id: number; status: Decision }) => api.post(`${url}/${id}/decision`, {
      status, reason: reason.trim(), expected_version: project.row_version,
      revision_id: status === "APPROVED" && revision ? Number(revision) : null,
    }),
    onSuccess: async () => {
      setSelected(null);
      await Promise.all([
        client.invalidateQueries({ queryKey: key }),
        client.invalidateQueries({ queryKey: ["project", project.id] }),
      ]);
    },
  });
  const reviewer = hasPermission("project.manage");
  const canCreate = !["COMPLETED", "CANCELLED"].includes(project.status) && (
    reviewer || (hasPermission("project.manage.assigned") && user?.id === project.project_manager_user_id)
  );
  const error = register.error ?? create.error ?? decide.error;
  return (
    <Stack spacing={2}>
      <Typography component="h2" variant="h6">Risks and changes</Typography>
      {error && <Alert severity="error">{apiErrorMessage(error)}</Alert>}
      {register.isPending && <LinearProgress aria-label="Loading project register" />}
      {canCreate && (
        <Paper component="form" variant="outlined" sx={{ p: 2 }}
          onSubmit={(event) => { event.preventDefault(); create.mutate(); }}>
          <Stack gap={1.5}>
            <TextField select label="Type" value={kind} onChange={(event) => setKind(event.target.value as Entry["kind"])}>
              <MenuItem value="RISK">Risk</MenuItem><MenuItem value="CHANGE">Change request</MenuItem>
            </TextField>
            <TextField label="Title" required value={title} onChange={(event) => setTitle(event.target.value)} slotProps={{ htmlInput: { maxLength: 200 } }} />
            <TextField label="Impact" required multiline value={impact} onChange={(event) => setImpact(event.target.value)} slotProps={{ htmlInput: { maxLength: 2000 } }} />
            <TextField label="Due date" type="date" required value={due} onChange={(event) => setDue(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
            <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}
              disabled={create.isPending || !title.trim() || !impact.trim() || !due}>Add register entry</Button>
          </Stack>
        </Paper>
      )}
      {register.isSuccess && !register.data.length && <Typography>No risks or changes recorded.</Typography>}
      {(register.data ?? []).map((entry) => (
        <Paper key={entry.id} variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1}>
            <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
              <Typography component="h3" variant="subtitle1">{entry.title}</Typography>
              <Chip size="small" label={entry.kind === "RISK" ? "Risk" : "Change request"} />
              <Chip size="small" label={entry.status} />
            </Stack>
            <Typography variant="body2">#{entry.id} · Owner #{entry.owner_user_id} · Due {entry.due_date}</Typography>
            <Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{entry.impact}</Typography>
            {entry.decision_reason && <Typography variant="body2">{entry.decision_reason}</Typography>}
            {entry.revision_id && (
              <Button component={Link} to={`../revisions?revision=${entry.revision_id}`} sx={{ alignSelf: "flex-start" }}>
                Schedule revision #{entry.revision_id}
              </Button>
            )}
            {reviewer && entry.status === "OPEN" && (entry.kind === "RISK" || entry.owner_user_id !== user?.id) && (
              <Button sx={{ alignSelf: "flex-start" }} onClick={() => { setSelected(entry); setReason(""); setRevision(""); }}>Record decision</Button>
            )}
            {selected?.id === entry.id && (
              <Stack spacing={1}>
                <TextField label="Decision reason" value={reason} onChange={(event) => setReason(event.target.value)} slotProps={{ htmlInput: { maxLength: 500 } }} />
                {entry.kind === "CHANGE" && <TextField label="Schedule revision ID" type="number" value={revision} onChange={(event) => setRevision(event.target.value)} />}
                <Stack direction="row" gap={1}>
                  {(entry.kind === "RISK" ? ["MITIGATED"] as const : ["APPROVED", "REJECTED"] as const).map((status) => (
                    <Button key={status} disabled={decide.isPending || !reason.trim()}
                      onClick={() => decide.mutate({ id: entry.id, status })}>{status}</Button>
                  ))}
                  <Button onClick={() => setSelected(null)}>Cancel</Button>
                </Stack>
              </Stack>
            )}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}
