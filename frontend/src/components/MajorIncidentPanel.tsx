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

type MajorIncident = {
  id: number;
  primary_ticket_id: number;
  major_incident_number: string;
  severity: string;
  status: string;
  business_impact: string;
  current_status_summary: string;
};
export function MajorIncidentPanel({ ticketId }: { ticketId: number }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, hasPermission } = useAuth();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const incidents = useQuery({
    queryKey: ["ticket-major-incident", ticketId],
    queryFn: async () =>
      (await api.get<MajorIncident[]>("/major-incidents")).data.find(
        (item) => item.primary_ticket_id === ticketId,
      ) ?? null,
  });
  const declare = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<MajorIncident>(`/tickets/${ticketId}/major-incident`, payload),
    onSuccess: async (response) => {
      setOpen(false);
      setError("");
      await queryClient.invalidateQueries({
        queryKey: ["ticket-major-incident", ticketId],
      });
      navigate(`/major-incidents/${response.data.id}`);
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  if (incidents.isLoading) return null;
  const row = incidents.data;
  return (
    <Paper
      variant="outlined"
      sx={{ p: 2.5, my: 2, borderColor: row ? "error.main" : "warning.main" }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Major Incident
        </Typography>
        {row ? (
          <>
            <TechnicalText>{row.major_incident_number}</TechnicalText>
            <Chip
              size="small"
              color={row.severity === "SEV1" ? "error" : "warning"}
              label={row.severity}
            />
            <Chip
              size="small"
              variant="outlined"
              label={row.status.replaceAll("_", " ")}
            />
            <Button onClick={() => navigate(`/major-incidents/${row.id}`)}>
              Open commander workspace
            </Button>
          </>
        ) : hasPermission("major_incident.declare") ? (
          <Button
            variant="contained"
            color="warning"
            onClick={() => setOpen(true)}
          >
            Declare Major Incident
          </Button>
        ) : (
          <Typography color="text.secondary">
            Not declared as a Major Incident.
          </Typography>
        )}
      </Stack>
      {row && (
        <Typography sx={{ mt: 1 }}>{row.current_status_summary}</Typography>
      )}
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <form
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            declare.mutate({
              severity: String(data.get("severity")),
              incident_commander_user_id: user?.id,
              business_impact: String(data.get("business_impact")),
              affected_users: String(data.get("affected_users") || "") || null,
              current_status_summary: String(
                data.get("current_status_summary"),
              ),
              next_update_at: String(data.get("next_update_at") || "") || null,
            });
          }}
        >
          <DialogTitle>Declare Major Incident</DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              <Alert severity="warning">
                This keeps the current Incident ticket and adds Major-Incident
                coordination around it.
              </Alert>
              <TextField
                select
                name="severity"
                label="Severity"
                defaultValue="SEV1"
              >
                <MenuItem value="SEV1">SEV1</MenuItem>
                <MenuItem value="SEV2">SEV2</MenuItem>
                <MenuItem value="SEV3">SEV3</MenuItem>
                <MenuItem value="SEV4">SEV4</MenuItem>
              </TextField>
              <TextField
                name="business_impact"
                label="Business impact"
                required
                multiline
                minRows={2}
              />
              <TextField name="affected_users" label="Affected users" />
              <TextField
                name="current_status_summary"
                label="Current status summary"
                required
                multiline
                minRows={2}
              />
              <TextField
                name="next_update_at"
                label="Next update"
                type="datetime-local"
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              color="warning"
              disabled={!user || declare.isPending}
            >
              Declare
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Paper>
  );
}
