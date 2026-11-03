import {
  Alert,
  Button,
  Chip,
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
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TechnicalText } from "./TechnicalText";

type LinkedProblem = {
  id: number;
  problem_number: string;
  title: string;
  status: string;
  priority: string;
  link_type: string;
};
type ProblemOption = LinkedProblem & { version: number };
const label = (value: string) => value.replaceAll("_", " ");

export function ProblemPanel({ ticketId }: { ticketId: number }) {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"link" | "create">("link");
  const [error, setError] = useState("");
  const linked = useQuery({
    queryKey: ["ticket-problems", ticketId],
    queryFn: async () =>
      (await api.get<LinkedProblem[]>(`/tickets/${ticketId}/problems`)).data,
  });
  const options = useQuery({
    queryKey: ["problem-link-options"],
    queryFn: async () => (await api.get<ProblemOption[]>("/problems")).data,
    enabled: open && mode === "link",
  });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["ticket-problems", ticketId],
      }),
      queryClient.invalidateQueries({ queryKey: ["problem-portfolio"] }),
    ]);
  };
  const create = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post("/problems", payload),
    onSuccess: async () => {
      setOpen(false);
      setError("");
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const link = useMutation({
    mutationFn: ({
      problemId,
      version,
      linkType,
    }: {
      problemId: number;
      version: number;
      linkType: string;
    }) =>
      api.post(`/problems/${problemId}/tickets`, {
        ticket_id: ticketId,
        link_type: linkType,
        version,
      }),
    onSuccess: async () => {
      setOpen(false);
      setError("");
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  if (linked.isError)
    return <Alert severity="error">Linked Problems could not be loaded.</Alert>;
  const canCreate = hasPermission("problem.create");
  const canLink = hasPermission("problem.link_ticket");
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (mode === "create") {
      create.mutate({
        title: String(data.get("title")),
        description: String(data.get("description")),
        priority: String(data.get("priority")),
        source_ticket_id: ticketId,
      });
      return;
    }
    const problemId = Number(data.get("problem_id"));
    const selected = options.data?.find((item) => item.id === problemId);
    if (selected)
      link.mutate({
        problemId,
        version: selected.version,
        linkType: String(data.get("link_type")),
      });
  };
  return (
    <Paper
      variant="outlined"
      sx={{ p: 2.5, my: 2, borderColor: "warning.main" }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Problem Management
        </Typography>
        {(canCreate || canLink) && (
          <Button onClick={() => setOpen(true)}>Link or create Problem</Button>
        )}
      </Stack>
      {linked.data?.length === 0 && (
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          This ticket is not linked to a Problem.
        </Typography>
      )}
      {linked.data?.map((item) => (
        <Stack
          key={`${item.id}-${item.link_type}`}
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          alignItems={{ sm: "center" }}
          sx={{ mt: 1.5 }}
        >
          <Button onClick={() => navigate(`/problems/${item.id}`)}>
            <TechnicalText>{item.problem_number}</TechnicalText>&nbsp;·{" "}
            {item.title}
          </Button>
          <Chip size="small" variant="outlined" label={label(item.status)} />
          <Chip size="small" label={label(item.link_type)} />
        </Stack>
      ))}
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <form onSubmit={submit}>
          <DialogTitle>
            {mode === "create"
              ? "Create Problem from ticket"
              : "Link existing Problem"}
          </DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              {canCreate && canLink && (
                <TextField
                  select
                  label="Action"
                  value={mode}
                  onChange={(event) =>
                    setMode(event.target.value as "link" | "create")
                  }
                >
                  <MenuItem value="link">Link existing Problem</MenuItem>
                  <MenuItem value="create">Create new Problem</MenuItem>
                </TextField>
              )}
              {mode === "link" && canLink ? (
                <>
                  <TextField
                    select
                    name="problem_id"
                    label="Problem"
                    required
                    defaultValue=""
                  >
                    {options.data
                      ?.filter(
                        (item) =>
                          !linked.data?.some(
                            (linkedItem) => linkedItem.id === item.id,
                          ),
                      )
                      .map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          <TechnicalText>{item.problem_number}</TechnicalText> ·{" "}
                          {item.title}
                        </MenuItem>
                      ))}
                  </TextField>
                  <TextField
                    select
                    name="link_type"
                    label="Relationship"
                    defaultValue="AFFECTED_INCIDENT"
                  >
                    <MenuItem value="AFFECTED_INCIDENT">
                      Affected incident
                    </MenuItem>
                    <MenuItem value="EVIDENCE">Evidence</MenuItem>
                    <MenuItem value="RELATED">Related</MenuItem>
                  </TextField>
                </>
              ) : (
                <>
                  <TextField name="title" label="Problem title" required />
                  <TextField
                    name="description"
                    label="Investigation description"
                    required
                    multiline
                    minRows={3}
                  />
                  <TextField
                    select
                    name="priority"
                    label="Priority"
                    defaultValue="MEDIUM"
                  >
                    {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => (
                      <MenuItem key={item} value={item}>
                        {item}
                      </MenuItem>
                    ))}
                  </TextField>
                </>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {mode === "create" ? "Create" : "Link"}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Paper>
  );
}
