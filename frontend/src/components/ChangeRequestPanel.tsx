import { Alert, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useNavigate } from "react-router-dom";

type ChangeRequest = {
  id: number;
  ticket_id: number;
  request_kind: string;
  purpose: string;
  detailed_description: string;
  business_impact: string;
  expected_result: string;
  change_status: string;
  version: number;
};

export function ChangeRequestPanel({ ticketId }: { ticketId: number }) {
  const navigate = useNavigate();
  const change = useQuery({
    queryKey: ["change-request", ticketId],
    queryFn: async () =>
      (await api.get<ChangeRequest>(`/tickets/${ticketId}/change-request`))
        .data,
    retry: false,
  });

  if (change.isLoading)
    return (
      <Typography color="text.secondary">
        Loading Change Request details…
      </Typography>
    );
  if (change.isError)
    return (
      <Alert
        severity="info"
        sx={{ my: 2 }}
        action={
          <Button
            onClick={() => navigate(`/tickets/${ticketId}/change-request`)}
          >
            Open workspace
          </Button>
        }
      >
        This Change Request ticket does not yet have structured change details.
      </Alert>
    );

  const row = change.data;
  if (!row) return null;
  return (
    <Paper
      variant="outlined"
      sx={{ p: 2.5, my: 2, borderColor: "primary.main" }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        alignItems={{ sm: "center" }}
      >
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Change Request
        </Typography>
        <Chip
          label={row.change_status.replaceAll("_", " ")}
          color="primary"
          variant="outlined"
        />
        <Chip label={row.request_kind.replaceAll("_", " ")} size="small" />
        <Button onClick={() => navigate(`/tickets/${ticketId}/change-request`)}>
          Open workspace
        </Button>
      </Stack>
      <Stack gap={1.5} sx={{ mt: 2 }}>
        <section>
          <Typography variant="caption" color="text.secondary">
            Purpose
          </Typography>
          <Typography sx={{ whiteSpace: "pre-wrap" }}>{row.purpose}</Typography>
        </section>
        <section>
          <Typography variant="caption" color="text.secondary">
            Detailed description
          </Typography>
          <Typography sx={{ whiteSpace: "pre-wrap" }}>
            {row.detailed_description}
          </Typography>
        </section>
        <section>
          <Typography variant="caption" color="text.secondary">
            Business impact
          </Typography>
          <Typography sx={{ whiteSpace: "pre-wrap" }}>
            {row.business_impact}
          </Typography>
        </section>
        <section>
          <Typography variant="caption" color="text.secondary">
            Expected result
          </Typography>
          <Typography sx={{ whiteSpace: "pre-wrap" }}>
            {row.expected_result}
          </Typography>
        </section>
      </Stack>
    </Paper>
  );
}
