import { ArrowBack, Edit } from "@mui/icons-material";
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
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TechnicalText } from "../components/TechnicalText";
import { ChangeRequestApprovalsPanel } from "../components/ChangeRequestApprovalsPanel";
import { ChangeRequestHistoryPanel } from "../components/ChangeRequestHistoryPanel";
import { ChangeRequestInitializePanel } from "../components/ChangeRequestInitializePanel";

type TicketSummary = {
  id: number;
  ticket_number: string;
  subject: string;
  client_name?: string;
};
type ChangeRequest = {
  id: number;
  ticket_id: number;
  request_kind: string;
  purpose: string;
  detailed_description: string;
  business_impact: string;
  expected_result: string;
  affected_product_id?: number | null;
  affected_module_id?: number | null;
  assessment_owner_user_id?: number | null;
  required_permissions?: string | null;
  requested_priority: string;
  technical_impact?: string | null;
  security_impact?: string | null;
  data_impact?: string | null;
  downtime_required: boolean;
  risk_level?: string | null;
  estimated_effort?: string | null;
  target_release?: string | null;
  planned_start_at?: string | null;
  planned_end_at?: string | null;
  implementation_plan?: string | null;
  rollback_plan?: string | null;
  test_plan?: string | null;
  deployment_environment?: string | null;
  deployment_requirements?: string | null;
  permissions_readiness: string;
  training_readiness: string;
  documentation_readiness: string;
  implementation_outcome?: string | null;
  actual_implemented_at?: string | null;
  validation_result?: string | null;
  change_status: string;
  version: number;
};
type Approval = {
  id: number;
  approver_user_id: number;
  approver_name?: string | null;
  decision: string;
  version: number;
};

const transitions: Record<string, string[]> = {
  SUBMITTED: ["UNDER_ASSESSMENT", "CANCELLED"],
  UNDER_ASSESSMENT: ["AWAITING_APPROVAL", "CANCELLED"],
  AWAITING_APPROVAL: ["APPROVED", "REJECTED", "UNDER_ASSESSMENT"],
  APPROVED: ["PLANNED", "CANCELLED"],
  PLANNED: ["PENDING_DEPLOYMENT", "CANCELLED"],
  PENDING_DEPLOYMENT: ["IMPLEMENTING", "CANCELLED"],
  IMPLEMENTING: ["VALIDATION", "FAILED", "ROLLED_BACK"],
  VALIDATION: ["PENDING_DEPLOYMENT", "COMPLETED", "FAILED", "ROLLED_BACK"],
  FAILED: ["UNDER_ASSESSMENT", "ROLLED_BACK"],
  REJECTED: ["UNDER_ASSESSMENT"],
  ROLLED_BACK: ["UNDER_ASSESSMENT"],
  COMPLETED: ["UNDER_ASSESSMENT"],
  CANCELLED: ["UNDER_ASSESSMENT"],
};
const transitionPermission: Record<string, string> = {
  UNDER_ASSESSMENT: "change_request.assess",
  AWAITING_APPROVAL: "change_request.assess",
  CANCELLED: "change_request.assess",
  APPROVED: "change_request.approve",
  REJECTED: "change_request.approve",
  PLANNED: "change_request.plan",
  PENDING_DEPLOYMENT: "change_request.plan",
  IMPLEMENTING: "change_request.implement",
  VALIDATION: "change_request.validate",
  COMPLETED: "change_request.complete",
  FAILED: "change_request.implement",
  ROLLED_BACK: "change_request.rollback",
};
const label = (value?: string | null) =>
  value ? value.replaceAll("_", " ") : "—";
const dateTime = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : "—";
const localDateTime = (value?: string | null) =>
  value ? new Date(value).toISOString().slice(0, 16) : "";
const optional = (value: FormDataEntryValue | null) =>
  String(value ?? "").trim() || null;

function Section({ title, value }: { title: string; value?: string | null }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {title}
      </Typography>
      <Typography sx={{ whiteSpace: "pre-wrap" }}>{value || "—"}</Typography>
    </Box>
  );
}

export function ChangeRequestWorkspacePage() {
  const { id } = useParams();
  const ticketId = Number(id);
  const navigate = useNavigate();
  const [workspaceParams, setWorkspaceParams] = useSearchParams();
  const { hasPermission, user } = useAuth();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [approvalRequestOpen, setApprovalRequestOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  const [error, setError] = useState("");
  const ticket = useQuery({
    queryKey: ["ticket", id],
    queryFn: async () => (await api.get<TicketSummary>(`/tickets/${id}`)).data,
    enabled: Number.isFinite(ticketId),
  });
  const change = useQuery({
    queryKey: ["change-request", ticketId],
    queryFn: async () =>
      (await api.get<ChangeRequest>(`/tickets/${ticketId}/change-request`))
        .data,
    enabled: Number.isFinite(ticketId),
    retry: false,
  });
  const approvals = useQuery({
    queryKey: ["change-request-approvals", ticketId],
    queryFn: async () =>
      (await api.get<Approval[]>(`/tickets/${ticketId}/change-request/approvals`)).data,
    enabled: Boolean(change.data),
  });
  const latestApproval = approvals.data?.[0];
  const pendingApproval = approvals.data?.find((item) => item.decision === "PENDING");
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["change-request", ticketId] }),
      queryClient.invalidateQueries({
        queryKey: ["change-request-history", ticketId],
      }),
    ]);
  };
  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (
        await api.put<ChangeRequest>(
          `/tickets/${ticketId}/change-request`,
          payload,
        )
      ).data,
    onSuccess: async () => {
      setError("");
      setEditOpen(false);
      await refresh();
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  const move = useMutation({
    mutationFn: async (payload: {
      transition: { status: string; version: number; reason: string | null };
      details?: Record<string, unknown>;
    }) => {
      let version = payload.transition.version;
      if (payload.details) {
        const saved = (
          await api.put<ChangeRequest>(
            `/tickets/${ticketId}/change-request`,
            payload.details,
          )
        ).data;
        version = saved.version;
      }
      if (
        ["APPROVED", "REJECTED"].includes(payload.transition.status) &&
        pendingApproval
      ) {
        await api.post(`/change-request-approvals/${pendingApproval.id}/decision`, {
          decision: payload.transition.status,
          comment:
            payload.transition.reason ||
            `${payload.transition.status === "APPROVED" ? "Approved" : "Rejected"} from the Change workflow.`,
          version: pendingApproval.version,
        });
      }
      return (
        await api.post<ChangeRequest>(
          `/tickets/${ticketId}/change-request/transition`,
          { ...payload.transition, version },
        )
      ).data;
    },
    onSuccess: async () => {
      setError("");
      setMoveOpen(false);
      await refresh();
      await queryClient.invalidateQueries({ queryKey: ["change-request-approvals", ticketId] });
    },
    onError: (reason) => setError(apiErrorMessage(reason)),
  });
  useEffect(() => {
    const requestedTarget = workspaceParams.get("target");
    const row = change.data;
    if (!requestedTarget || !row) return;
    const permitted = hasPermission(
      transitionPermission[requestedTarget] ?? "change_request.assess",
    );
    if ((transitions[row.change_status] ?? []).includes(requestedTarget) && permitted) {
      setError("");
      setTargetStatus(requestedTarget);
      setMoveOpen(true);
    } else {
      setError("That workflow move is not available from the current Change status.");
    }
    const next = new URLSearchParams(workspaceParams);
    next.delete("target");
    setWorkspaceParams(next, { replace: true });
  }, [change.data, hasPermission, setWorkspaceParams, workspaceParams]);
  if (ticket.isLoading || change.isLoading) return <CircularProgress />;
  if (ticket.isError || !ticket.data)
    return <Alert severity="error">The ticket could not be loaded.</Alert>;
  if (change.isError || !change.data)
    return (
      <Stack gap={2}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate("/change-requests")}
        >
          Back to Change Requests
        </Button>
        <Button onClick={() => navigate(`/tickets/${ticketId}`)}>
          View parent ticket
        </Button>
        <Alert severity="info">
          This ticket does not yet have structured Change Request details.
        </Alert>
        {hasPermission("change_request.create") && (
          <ChangeRequestInitializePanel ticketId={ticketId} />
        )}
      </Stack>
    );
  const row = change.data;
  const availableTransitions = (transitions[row.change_status] ?? []).filter(
    (status) =>
      hasPermission(transitionPermission[status] ?? "change_request.assess"),
  );

  function submitDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    save.mutate({
      request_kind: String(data.get("request_kind")),
      purpose: String(data.get("purpose") ?? "").trim(),
      detailed_description: String(
        data.get("detailed_description") ?? "",
      ).trim(),
      business_impact: String(data.get("business_impact") ?? "").trim(),
      expected_result: String(data.get("expected_result") ?? "").trim(),
      required_permissions: optional(data.get("required_permissions")),
      requested_priority: String(data.get("requested_priority")),
      technical_impact: optional(data.get("technical_impact")),
      security_impact: optional(data.get("security_impact")),
      data_impact: optional(data.get("data_impact")),
      downtime_required: data.get("downtime_required") === "on",
      risk_level: optional(data.get("risk_level")),
      estimated_effort: optional(data.get("estimated_effort")),
      target_release: optional(data.get("target_release")),
      planned_start_at: optional(data.get("planned_start_at")),
      planned_end_at: optional(data.get("planned_end_at")),
      implementation_plan: optional(data.get("implementation_plan")),
      rollback_plan: optional(data.get("rollback_plan")),
      test_plan: optional(data.get("test_plan")),
      deployment_environment: optional(data.get("deployment_environment")),
      deployment_requirements: optional(data.get("deployment_requirements")),
      permissions_readiness: String(data.get("permissions_readiness")),
      training_readiness: String(data.get("training_readiness")),
      documentation_readiness: String(data.get("documentation_readiness")),
      implementation_outcome: optional(data.get("implementation_outcome")),
      actual_implemented_at: optional(data.get("actual_implemented_at")),
      validation_result: optional(data.get("validation_result")),
      version: row.version,
    });
  }
  function submitTransition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const requiresDetailSave = [
      "PLANNED",
      "PENDING_DEPLOYMENT",
      "COMPLETED",
    ].includes(targetStatus);
    const details = requiresDetailSave
      ? {
        request_kind: row.request_kind,
        purpose: row.purpose,
        detailed_description: row.detailed_description,
        business_impact: row.business_impact,
        expected_result: row.expected_result,
        affected_product_id: row.affected_product_id ?? null,
        affected_module_id: row.affected_module_id ?? null,
        required_permissions: row.required_permissions ?? null,
        requested_priority: row.requested_priority,
        assessment_owner_user_id: row.assessment_owner_user_id ?? null,
        technical_impact: row.technical_impact ?? null,
        security_impact: row.security_impact ?? null,
        data_impact: row.data_impact ?? null,
        downtime_required: row.downtime_required,
        risk_level: row.risk_level ?? null,
        estimated_effort: row.estimated_effort ?? null,
        target_release: row.target_release ?? null,
        planned_start_at:
          optional(data.get("planned_start_at")) ?? row.planned_start_at ?? null,
        planned_end_at:
          optional(data.get("planned_end_at")) ?? row.planned_end_at ?? null,
        implementation_plan:
          optional(data.get("implementation_plan")) ?? row.implementation_plan ?? null,
        rollback_plan:
          optional(data.get("rollback_plan")) ?? row.rollback_plan ?? null,
        test_plan: optional(data.get("test_plan")) ?? row.test_plan ?? null,
        deployment_environment:
          optional(data.get("deployment_environment")) ?? row.deployment_environment ?? null,
        deployment_requirements:
          optional(data.get("deployment_requirements")) ?? row.deployment_requirements ?? null,
        permissions_readiness:
          optional(data.get("permissions_readiness")) ?? row.permissions_readiness,
        training_readiness:
          optional(data.get("training_readiness")) ?? row.training_readiness,
        documentation_readiness:
          optional(data.get("documentation_readiness")) ?? row.documentation_readiness,
        implementation_outcome:
          optional(data.get("implementation_outcome")) ?? row.implementation_outcome ?? null,
        actual_implemented_at:
          optional(data.get("actual_implemented_at")) ?? row.actual_implemented_at ?? null,
        validation_result:
          optional(data.get("validation_result")) ?? row.validation_result ?? null,
        version: row.version,
      }
      : undefined;
    move.mutate({
      transition: {
        status: targetStatus,
        version: row.version,
        reason: optional(data.get("reason")),
      },
      details,
    });
  }

  return (
    <Stack gap={3}>
      <Paper sx={{ p: 3, borderLeft: 5, borderLeftColor: "primary.main" }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={1.5}
          alignItems={{ md: "center" }}
        >
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate("/change-requests")}
          >
            Change Requests
          </Button>
          <Button onClick={() => navigate(`/tickets/${ticketId}`)}>
            View parent ticket
          </Button>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="overline">Change Request Workspace</Typography>
            <Typography variant="h4">
              <TechnicalText>{ticket.data.ticket_number}</TechnicalText> ·{" "}
              {ticket.data.subject}
            </Typography>
            <Typography color="text.secondary">
              {ticket.data.client_name || "Client unavailable"}
            </Typography>
          </Box>
          <Chip color="primary" label={label(row.change_status)} />
          <Chip variant="outlined" label={label(row.request_kind)} />
          {hasPermission("change_request.assess") && (
            <Button
              startIcon={<Edit />}
              onClick={() => {
                setError("");
                setEditOpen(true);
              }}
            >
              Edit
            </Button>
          )}
          {!!availableTransitions.length && (
            <Button
              variant="contained"
              onClick={() => {
                setError("");
                setTargetStatus(availableTransitions[0]);
                setMoveOpen(true);
              }}
            >
              Change status
            </Button>
          )}
        </Stack>
      </Paper>
      {error && <Alert severity="error">{error}</Alert>}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "2fr 1fr" },
          gap: 3,
        }}
      >
        <Stack gap={3}>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Request definition
            </Typography>
            <Stack gap={2}>
              <Section title="Purpose" value={row.purpose} />
              <Section
                title="Detailed description"
                value={row.detailed_description}
              />
              <Section title="Business impact" value={row.business_impact} />
              <Section title="Expected result" value={row.expected_result} />
              <Section
                title="Required permissions"
                value={row.required_permissions}
              />
            </Stack>
          </Paper>
          <ChangeRequestApprovalsPanel
            ticketId={ticketId}
            changeVersion={row.version}
            requestDialogOpen={approvalRequestOpen}
            onRequestDialogOpenChange={setApprovalRequestOpen}
          />
          <ChangeRequestHistoryPanel ticketId={ticketId} />
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Impact assessment
            </Typography>
            <Stack gap={2}>
              <Section title="Technical impact" value={row.technical_impact} />
              <Section title="Security impact" value={row.security_impact} />
              <Section title="Data impact" value={row.data_impact} />
            </Stack>
          </Paper>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Implementation and rollback
            </Typography>
            <Stack gap={2}>
              <Section
                title="Implementation plan"
                value={row.implementation_plan}
              />
              <Section title="Rollback plan" value={row.rollback_plan} />
              <Section title="Test plan" value={row.test_plan} />
            </Stack>
          </Paper>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Deployment readiness and validation
            </Typography>
            <Stack gap={2}>
              <Section title="Deployment target" value={label(row.deployment_environment)} />
              <Section title="Deployment requirements" value={row.deployment_requirements} />
              <Section title="Permissions / access" value={label(row.permissions_readiness)} />
              <Section title="Training / communication" value={label(row.training_readiness)} />
              <Section title="Documentation" value={label(row.documentation_readiness)} />
              <Section title="Implementation outcome" value={label(row.implementation_outcome)} />
              <Section title="Actual implementation" value={dateTime(row.actual_implemented_at)} />
              <Section title="Validation result" value={row.validation_result} />
            </Stack>
          </Paper>
        </Stack>
        <Stack gap={3}>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Control summary
            </Typography>
            <Stack gap={1.5}>
              <Section
                title="Requested priority"
                value={label(row.requested_priority)}
              />
              <Section title="Risk level" value={label(row.risk_level)} />
              <Section title="Estimated effort" value={row.estimated_effort} />
              <Section title="Target release" value={row.target_release} />
              <Section
                title="Downtime required"
                value={row.downtime_required ? "Yes" : "No"}
              />
            </Stack>
          </Paper>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Planned window
            </Typography>
            <Stack gap={1.5}>
              <Section title="Start" value={dateTime(row.planned_start_at)} />
              <Section title="End" value={dateTime(row.planned_end_at)} />
            </Stack>
          </Paper>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Workflow
            </Typography>
            <Typography color="text.secondary">
              Lifecycle actions are managed here independently from UAT.
            </Typography>
          </Paper>
        </Stack>
      </Box>

      <Dialog
        open={editOpen}
        onClose={() => setEditOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <Box component="form" onSubmit={submitDetails}>
          <DialogTitle>Edit Change Request</DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField
                select
                name="request_kind"
                label="Request kind"
                defaultValue={row.request_kind}
              >
                <MenuItem value="NEW_FEATURE">New feature</MenuItem>
                <MenuItem value="UPDATE_EXISTING_FEATURE">
                  Update existing feature
                </MenuItem>
              </TextField>
              <TextField
                name="purpose"
                label="Purpose"
                required
                multiline
                defaultValue={row.purpose}
              />
              <TextField
                name="detailed_description"
                label="Detailed description"
                required
                multiline
                minRows={3}
                defaultValue={row.detailed_description}
              />
              <TextField
                name="business_impact"
                label="Business impact"
                required
                multiline
                defaultValue={row.business_impact}
              />
              <TextField
                name="expected_result"
                label="Expected result"
                required
                multiline
                defaultValue={row.expected_result}
              />
              <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
                <TextField
                  select
                  fullWidth
                  name="requested_priority"
                  label="Requested priority"
                  defaultValue={row.requested_priority}
                >
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
                    <MenuItem key={value} value={value}>
                      {value}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  fullWidth
                  name="risk_level"
                  label="Risk level"
                  defaultValue={row.risk_level ?? ""}
                >
                  <MenuItem value="">Not assessed</MenuItem>
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
                    <MenuItem key={value} value={value}>
                      {value}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>
              <TextField
                name="required_permissions"
                label="Required permissions"
                multiline
                defaultValue={row.required_permissions ?? ""}
              />
              <TextField
                name="technical_impact"
                label="Technical impact"
                multiline
                defaultValue={row.technical_impact ?? ""}
              />
              <TextField
                name="security_impact"
                label="Security impact"
                multiline
                defaultValue={row.security_impact ?? ""}
              />
              <TextField
                name="data_impact"
                label="Data impact"
                multiline
                defaultValue={row.data_impact ?? ""}
              />
              <FormControlLabel
                control={
                  <Switch
                    name="downtime_required"
                    defaultChecked={row.downtime_required}
                  />
                }
                label="Downtime required"
              />
              <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
                <TextField
                  fullWidth
                  name="estimated_effort"
                  label="Estimated effort"
                  defaultValue={row.estimated_effort ?? ""}
                />
                <TextField
                  fullWidth
                  name="target_release"
                  label="Target release"
                  defaultValue={row.target_release ?? ""}
                />
              </Stack>
              <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
                <TextField
                  fullWidth
                  type="datetime-local"
                  name="planned_start_at"
                  label="Planned start"
                  slotProps={{ inputLabel: { shrink: true } }}
                  defaultValue={localDateTime(row.planned_start_at)}
                />
                <TextField
                  fullWidth
                  type="datetime-local"
                  name="planned_end_at"
                  label="Planned end"
                  slotProps={{ inputLabel: { shrink: true } }}
                  defaultValue={localDateTime(row.planned_end_at)}
                />
              </Stack>
              <TextField
                name="implementation_plan"
                label="Implementation plan"
                multiline
                minRows={3}
                defaultValue={row.implementation_plan ?? ""}
              />
              <TextField
                name="rollback_plan"
                label="Rollback plan"
                multiline
                minRows={3}
                defaultValue={row.rollback_plan ?? ""}
              />
              <TextField
                name="test_plan"
                label="Test plan"
                multiline
                minRows={3}
                defaultValue={row.test_plan ?? ""}
              />
              <TextField
                select
                name="deployment_environment"
                label="Deployment target"
                defaultValue={row.deployment_environment ?? ""}
                helperText="Use TEST or STAGING before promoting the same Change to PRODUCTION."
              >
                <MenuItem value="">Not selected</MenuItem>
                <MenuItem value="TEST">Test</MenuItem>
                <MenuItem value="STAGING">Staging</MenuItem>
                <MenuItem value="PRODUCTION">Production</MenuItem>
              </TextField>
              <TextField
                name="deployment_requirements"
                label="Deployment requirements"
                multiline
                minRows={3}
                defaultValue={row.deployment_requirements ?? ""}
                helperText="Access, permissions, dependencies, communication, training and operational prerequisites."
              />
              {[
                ["permissions_readiness", "Permissions / access", row.permissions_readiness],
                ["training_readiness", "Training / communication", row.training_readiness],
                ["documentation_readiness", "Documentation / runbook", row.documentation_readiness],
              ].map(([name, fieldLabel, value]) => (
                <TextField key={name} select name={name} label={fieldLabel} defaultValue={value}>
                  <MenuItem value="PENDING">Pending</MenuItem>
                  <MenuItem value="COMPLETED">Completed</MenuItem>
                  <MenuItem value="NOT_REQUIRED">Not required</MenuItem>
                </TextField>
              ))}
              <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
                <TextField
                  select
                  fullWidth
                  name="implementation_outcome"
                  label="Implementation outcome"
                  defaultValue={row.implementation_outcome ?? ""}
                >
                  <MenuItem value="">Not recorded</MenuItem>
                  <MenuItem value="SUCCESSFUL">Successful</MenuItem>
                  <MenuItem value="FAILED">Failed</MenuItem>
                  <MenuItem value="ROLLED_BACK">Rolled back</MenuItem>
                </TextField>
                <TextField
                  fullWidth
                  type="datetime-local"
                  name="actual_implemented_at"
                  label="Actual implementation date"
                  slotProps={{ inputLabel: { shrink: true } }}
                  defaultValue={localDateTime(row.actual_implemented_at)}
                />
              </Stack>
              <TextField
                name="validation_result"
                label="Validation result"
                multiline
                minRows={3}
                defaultValue={row.validation_result ?? ""}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={save.isPending}>
              {save.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitTransition}>
          <DialogTitle>Change Request status</DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField
                select
                label="Next status"
                value={targetStatus}
                onChange={(event) => setTargetStatus(event.target.value)}
              >
                {availableTransitions.map((status) => (
                  <MenuItem key={status} value={status}>
                    {label(status)}
                  </MenuItem>
                ))}
              </TextField>
              {["APPROVED", "REJECTED"].includes(targetStatus) && (
                <Alert
                  action={
                    !pendingApproval &&
                      latestApproval?.decision !== targetStatus &&
                      hasPermission("change_request.assess") ? (
                      <Button
                        color="inherit"
                        size="small"
                        onClick={() => {
                          setMoveOpen(false);
                          setApprovalRequestOpen(true);
                        }}
                      >
                        Request approval
                      </Button>
                    ) : undefined
                  }
                  severity={
                    latestApproval?.decision === targetStatus
                      ? "success"
                      : pendingApproval?.approver_user_id === user?.id
                        ? "info"
                        : "warning"
                  }
                >
                  {latestApproval?.decision === targetStatus
                    ? `The latest approval cycle is already ${targetStatus.toLowerCase()}. Confirm the status change below.`
                    : pendingApproval?.approver_user_id === user?.id
                      ? `You are the selected approver. The ${targetStatus === "APPROVED" ? "Approve" : "Reject"} button will record the immutable decision and update the Change status together.`
                      : pendingApproval
                        ? `Approval is waiting for ${pendingApproval.approver_name || `User ${pendingApproval.approver_user_id}`}. Only that approver can decide it.`
                        : hasPermission("change_request.assess")
                          ? "No pending approval cycle exists. Request one here before approving the Change."
                          : "No pending approval cycle exists. A user with Change assessment permission must request one first."}
                </Alert>
              )}
              {targetStatus === "PLANNED" && (
                <>
                  <Alert severity="info">
                    Planning requires the implementation, rollback and test plans plus a deployment window.
                  </Alert>
                  <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
                    <TextField
                      required
                      fullWidth
                      type="datetime-local"
                      name="planned_start_at"
                      label="Planned start"
                      slotProps={{ inputLabel: { shrink: true } }}
                      defaultValue={localDateTime(row.planned_start_at)}
                    />
                    <TextField
                      required
                      fullWidth
                      type="datetime-local"
                      name="planned_end_at"
                      label="Planned end"
                      slotProps={{ inputLabel: { shrink: true } }}
                      defaultValue={localDateTime(row.planned_end_at)}
                    />
                  </Stack>
                  <TextField required name="implementation_plan" label="Implementation plan" multiline minRows={2} defaultValue={row.implementation_plan ?? ""} />
                  <TextField required name="rollback_plan" label="Rollback plan" multiline minRows={2} defaultValue={row.rollback_plan ?? ""} />
                  <TextField required name="test_plan" label="Test plan" multiline minRows={2} defaultValue={row.test_plan ?? ""} />
                </>
              )}
              {targetStatus === "PENDING_DEPLOYMENT" && (
                <>
                  <Alert severity="info">
                    Select where this deployment will occur. After test validation, return here and select Production for promotion.
                  </Alert>
                  <TextField
                    required
                    select
                    name="deployment_environment"
                    label="Deployment target"
                    defaultValue={row.deployment_environment ?? ""}
                  >
                    <MenuItem value="TEST">Test</MenuItem>
                    <MenuItem value="STAGING">Staging</MenuItem>
                    <MenuItem value="PRODUCTION">Production</MenuItem>
                  </TextField>
                  <TextField
                    name="deployment_requirements"
                    label="Deployment requirements"
                    multiline
                    minRows={3}
                    defaultValue={row.deployment_requirements ?? ""}
                    helperText="Record access, dependencies, permissions, training, communication and documentation prerequisites."
                  />
                  {[
                    ["permissions_readiness", "Permissions / access", row.permissions_readiness],
                    ["training_readiness", "Training / communication", row.training_readiness],
                    ["documentation_readiness", "Documentation / runbook", row.documentation_readiness],
                  ].map(([name, fieldLabel, value]) => (
                    <TextField key={name} select name={name} label={fieldLabel} defaultValue={value}>
                      <MenuItem value="PENDING">Pending</MenuItem>
                      <MenuItem value="COMPLETED">Completed</MenuItem>
                      <MenuItem value="NOT_REQUIRED">Not required</MenuItem>
                    </TextField>
                  ))}
                </>
              )}
              {targetStatus === "COMPLETED" && (
                <>
                  <Alert severity="info">
                    Completion requires all deployment prerequisites to be completed or marked not required, plus implementation and validation evidence.
                  </Alert>
                  <TextField
                    required
                    name="deployment_requirements"
                    label="Deployment requirements summary"
                    multiline
                    minRows={3}
                    defaultValue={row.deployment_requirements ?? ""}
                  />
                  {[
                    ["permissions_readiness", "Permissions / access", row.permissions_readiness],
                    ["training_readiness", "Training / communication", row.training_readiness],
                    ["documentation_readiness", "Documentation / runbook", row.documentation_readiness],
                  ].map(([name, fieldLabel, value]) => (
                    <TextField key={name} required select name={name} label={fieldLabel} defaultValue={value}>
                      <MenuItem value="PENDING" disabled>Pending</MenuItem>
                      <MenuItem value="COMPLETED">Completed</MenuItem>
                      <MenuItem value="NOT_REQUIRED">Not required</MenuItem>
                    </TextField>
                  ))}
                  <TextField
                    required
                    select
                    name="implementation_outcome"
                    label="Implementation outcome"
                    defaultValue={row.implementation_outcome ?? ""}
                  >
                    <MenuItem value="SUCCESSFUL">Successful</MenuItem>
                    <MenuItem value="FAILED">Failed</MenuItem>
                    <MenuItem value="ROLLED_BACK">Rolled back</MenuItem>
                  </TextField>
                  <TextField
                    required
                    type="datetime-local"
                    name="actual_implemented_at"
                    label="Actual implementation date"
                    slotProps={{ inputLabel: { shrink: true } }}
                    defaultValue={localDateTime(row.actual_implemented_at)}
                  />
                  <TextField
                    required
                    name="validation_result"
                    label="Validation result"
                    multiline
                    minRows={3}
                    defaultValue={row.validation_result ?? ""}
                  />
                </>
              )}
              <TextField
                name="reason"
                label="Reason / transition note"
                multiline
                minRows={3}
                required={
                  ["CANCELLED", "FAILED", "ROLLED_BACK"].includes(
                    targetStatus,
                  ) ||
                  ["COMPLETED", "CANCELLED", "FAILED", "ROLLED_BACK"].includes(
                    row.change_status,
                  )
                }
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setMoveOpen(false)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              color={targetStatus === "REJECTED" ? "error" : targetStatus === "APPROVED" ? "success" : "primary"}
              disabled={
                !targetStatus ||
                move.isPending ||
                (["APPROVED", "REJECTED"].includes(targetStatus) &&
                  latestApproval?.decision !== targetStatus &&
                  (!pendingApproval || pendingApproval.approver_user_id !== user?.id))
              }
            >
              {move.isPending
                ? "Updating…"
                : targetStatus === "APPROVED"
                  ? "Approve Change"
                  : targetStatus === "REJECTED"
                    ? "Reject Change"
                    : "Update status"}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
