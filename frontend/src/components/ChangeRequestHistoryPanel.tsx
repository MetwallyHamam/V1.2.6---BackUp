import { Box, Chip, Paper, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

type HistoryItem = {
  id: number;
  from_status: string;
  to_status: string;
  reason?: string | null;
  changed_by_name?: string | null;
  changed_at: string;
};
const label = (value: string) => value.replaceAll("_", " ");

export function ChangeRequestHistoryPanel({ ticketId }: { ticketId: number }) {
  const history = useQuery({
    queryKey: ["change-request-history", ticketId],
    queryFn: async () =>
      (
        await api.get<HistoryItem[]>(
          `/tickets/${ticketId}/change-request/history`,
        )
      ).data,
  });
  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Lifecycle history
      </Typography>
      {!history.data?.length && (
        <Typography color="text.secondary">
          No lifecycle transitions have been recorded.
        </Typography>
      )}
      <Stack gap={2}>
        {history.data?.map((item) => (
          <Box
            key={item.id}
            sx={{ borderInlineStart: 3, borderColor: "divider", ps: 2 }}
          >
            <Stack direction="row" gap={1} flexWrap="wrap" alignItems="center">
              <Chip
                size="small"
                variant="outlined"
                label={label(item.from_status)}
              />
              <Typography aria-hidden>→</Typography>
              <Chip
                size="small"
                color="primary"
                label={label(item.to_status)}
              />
            </Stack>
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              {item.changed_by_name || "System"} ·{" "}
              {new Date(item.changed_at).toLocaleString()}
            </Typography>
            {item.reason && (
              <Typography
                color="text.secondary"
                sx={{ whiteSpace: "pre-wrap" }}
              >
                {item.reason}
              </Typography>
            )}
          </Box>
        ))}
      </Stack>
    </Paper>
  );
}
