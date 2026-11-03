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
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Approval = {
  id: number;
  approval_stage: string;
  cycle_number: number;
  approver_user_id: number;
  approver_name?: string | null;
  decision: string;
  comment?: string | null;
  requested_at: string;
  decided_at?: string | null;
  version: number;
};
type Candidate = { id: number; full_name: string; username: string };

export function ChangeRequestApprovalsPanel({
  ticketId,
  changeVersion,
  requestDialogOpen,
  onRequestDialogOpenChange,
}: {
  ticketId: number;
  changeVersion: number;
  requestDialogOpen?: boolean;
  onRequestDialogOpenChange?: (open: boolean) => void;
}) {
  const { hasPermission, user } = useAuth();
  const queryClient = useQueryClient();
  const [internalRequestOpen, setInternalRequestOpen] = useState(false);
  const requestOpen = requestDialogOpen ?? internalRequestOpen;
  const setRequestOpen = (open: boolean) => {
    setInternalRequestOpen(open);
    onRequestDialogOpenChange?.(open);
  };
  const [decision, setDecision] = useState<{
    approval: Approval;
    value: "APPROVED" | "REJECTED";
  } | null>(null);
  const [error, setError] = useState("");
  const approvals = useQuery({
    queryKey: ["change-request-approvals", ticketId],
    queryFn: async () =>
      (
        await api.get<Approval[]>(
          `/tickets/${ticketId}/change-request/approvals`,
        )
      ).data,
  });
  const candidates = useQuery({
    queryKey: ["change-request-approval-candidates", ticketId],
    queryFn: async () =>
      (
        await api.get<Candidate[]>(
          `/tickets/${ticketId}/change-request/approval-candidates`,
        )
      ).data,
    enabled: requestOpen && hasPermission("change_request.assess"),
  });
  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: ["change-request-approvals", ticketId],
    });
  const requestApproval = useMutation({
    mutationFn: (payload: {
      approval_stage: string;
      approver_user_id: number;
      version: number;
    }) => api.post(`/tickets/${ticketId}/change-request/approvals`, payload),
    onSuccess: async () => {
      setError("");
      setRequestOpen(false);
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const decide = useMutation({
    mutationFn: (payload: {
      approval: Approval;
      value: string;
      comment: string;
    }) =>
      api.post(`/change-request-approvals/${payload.approval.id}/decision`, {
        decision: payload.value,
        comment: payload.comment,
        version: payload.approval.version,
      }),
    onSuccess: async () => {
      setError("");
      setDecision(null);
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    requestApproval.mutate({
      approval_stage: String(data.get("approval_stage")),
      approver_user_id: Number(data.get("approver_user_id")),
      version: changeVersion,
    });
  }
  function submitDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!decision) return;
    decide.mutate({
      approval: decision.approval,
      value: decision.value,
      comment: String(
        new FormData(event.currentTarget).get("comment") ?? "",
      ).trim(),
    });
  }
  const pending = approvals.data?.some((item) => item.decision === "PENDING");
  return (
    <>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack direction="row" gap={1} alignItems="center">
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Approvals
          </Typography>
          {hasPermission("change_request.assess") && !pending && (
            <Button
              onClick={() => {
                setError("");
                setRequestOpen(true);
              }}
            >
              Request approval
            </Button>
          )}
        </Stack>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
        {!approvals.data?.length && (
          <Typography color="text.secondary" sx={{ mt: 2 }}>
            No approval cycles have been requested.
          </Typography>
        )}
        <Stack gap={1.5} sx={{ mt: 2 }}>
          {approvals.data?.map((item) => (
            <Paper key={item.id} variant="outlined" sx={{ p: 2 }}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                gap={1}
                alignItems={{ sm: "center" }}
              >
                <Typography fontWeight={700} sx={{ flexGrow: 1 }}>
                  Cycle {item.cycle_number} ·{" "}
                  {item.approval_stage.replaceAll("_", " ")}
                </Typography>
                <Chip
                  size="small"
                  color={
                    item.decision === "APPROVED"
                      ? "success"
                      : item.decision === "REJECTED"
                        ? "error"
                        : "warning"
                  }
                  label={item.decision}
                />
              </Stack>
              <Typography variant="body2">
                Approver:{" "}
                {item.approver_name || `User ${item.approver_user_id}`}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Requested {new Date(item.requested_at).toLocaleString()}
                {item.decided_at
                  ? ` · Decided ${new Date(item.decided_at).toLocaleString()}`
                  : ""}
              </Typography>
              {item.comment && (
                <Typography sx={{ mt: 1, whiteSpace: "pre-wrap" }}>
                  {item.comment}
                </Typography>
              )}
              {item.decision === "PENDING" &&
                item.approver_user_id === user?.id &&
                hasPermission("change_request.approve") && (
                  <Stack direction="row" gap={1} sx={{ mt: 1 }}>
                    <Button
                      size="small"
                      color="success"
                      onClick={() =>
                        setDecision({ approval: item, value: "APPROVED" })
                      }
                    >
                      Approve
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={() =>
                        setDecision({ approval: item, value: "REJECTED" })
                      }
                    >
                      Reject
                    </Button>
                  </Stack>
                )}
            </Paper>
          ))}
        </Stack>
      </Paper>
      <Dialog
        open={requestOpen}
        onClose={() => setRequestOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <form onSubmit={submitRequest}>
          <DialogTitle>Request Change approval</DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField
                name="approval_stage"
                label="Approval stage"
                defaultValue="MANAGER"
                required
              />
              <TextField
                select
                name="approver_user_id"
                label="Approver"
                defaultValue=""
                required
              >
                {candidates.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.full_name} ({item.username})
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setRequestOpen(false)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={requestApproval.isPending}
            >
              Request
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Dialog
        open={Boolean(decision)}
        onClose={() => setDecision(null)}
        fullWidth
        maxWidth="sm"
      >
        <form onSubmit={submitDecision}>
          <DialogTitle>
            {decision?.value === "APPROVED" ? "Approve" : "Reject"} Change
            Request
          </DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField
                name="comment"
                label="Decision comment"
                required
                multiline
                minRows={3}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDecision(null)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              color={decision?.value === "REJECTED" ? "error" : "success"}
              disabled={decide.isPending}
            >
              Confirm
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
}
