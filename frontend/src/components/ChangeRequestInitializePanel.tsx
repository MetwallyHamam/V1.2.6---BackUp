import {
  Alert,
  Button,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api, apiErrorMessage } from "../api/client";

export function ChangeRequestInitializePanel({
  ticketId,
}: {
  ticketId: number;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const create = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.put(`/tickets/${ticketId}/change-request`, payload),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({
        queryKey: ["change-request", ticketId],
      });
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    create.mutate({
      request_kind: String(data.get("request_kind")),
      purpose: String(data.get("purpose") ?? "").trim(),
      detailed_description: String(
        data.get("detailed_description") ?? "",
      ).trim(),
      business_impact: String(data.get("business_impact") ?? "").trim(),
      expected_result: String(data.get("expected_result") ?? "").trim(),
      requested_priority: String(data.get("requested_priority")),
      downtime_required: false,
    });
  }
  return (
    <Paper variant="outlined" sx={{ p: 3, maxWidth: 900 }}>
      <Typography variant="h5" gutterBottom>
        Initialize Change Request
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Add the required structured information. Assessment and planning fields
        can be completed afterward.
      </Typography>
      <Stack component="form" onSubmit={submit} gap={2}>
        {error && <Alert severity="error">{error}</Alert>}
        <TextField
          select
          name="request_kind"
          label="Request kind"
          defaultValue="UPDATE_EXISTING_FEATURE"
          required
        >
          <MenuItem value="NEW_FEATURE">New feature</MenuItem>
          <MenuItem value="UPDATE_EXISTING_FEATURE">
            Update existing feature
          </MenuItem>
        </TextField>
        <TextField name="purpose" label="Purpose" required multiline />
        <TextField
          name="detailed_description"
          label="Detailed description"
          required
          multiline
          minRows={3}
        />
        <TextField
          name="business_impact"
          label="Business impact"
          required
          multiline
        />
        <TextField
          name="expected_result"
          label="Expected result"
          required
          multiline
        />
        <TextField
          select
          name="requested_priority"
          label="Requested priority"
          defaultValue="MEDIUM"
        >
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
            <MenuItem key={value} value={value}>
              {value}
            </MenuItem>
          ))}
        </TextField>
        <Button type="submit" variant="contained" disabled={create.isPending}>
          {create.isPending ? "Creating…" : "Create structured details"}
        </Button>
      </Stack>
    </Paper>
  );
}
