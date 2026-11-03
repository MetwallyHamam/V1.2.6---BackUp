import { Close } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Drawer,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { UatCollaborationPanel } from "./UatCollaborationPanel";
import { PortalUatActivity } from "./PortalUatActivity";
import { PortalUatWorkspace } from "./PortalUatWorkspace";
import { DeploymentTracker } from "./DeploymentTracker";

type Test = {
  id: number;
  snapshot: {
    code: string;
    title: string;
    priority?: string;
    preconditions: string | null;
    expected_result: string;
    steps: { action: string; expected_result: string }[];
  };
  client_test_result: string;
  client_workflow_status: string;
  client_attempt_count: number;
  linked_ticket: { id: number; ticket_number: string } | null;
  has_linked_ticket: boolean;
  assigned_to_me: boolean;
};
type Summary = {
  total: number;
  passed: number;
  failed: number;
  blocked: number;
  not_tested: number;
  completion_percent: number;
  pass_rate: number;
  open_defects: number;
  mandatory_outstanding: number;
};
type ClientSignoff = {
  decision: string;
  decided_at: string;
  comment: string | null;
};
type Cycle = {
  id: number;
  code: string;
  title: string;
  release_version: string;
  status: string;
  role: "TESTER" | "COORDINATOR" | "APPROVER";
  allow_client_testing: boolean;
  allow_client_pass: boolean;
  allow_client_fail: boolean;
  allow_client_blocked: boolean;
  allow_client_signoff: boolean;
  allow_client_request_testing: boolean;
  allow_client_comments: boolean;
  allow_client_attachments: boolean;
  allow_client_create_ticket_from_failure: boolean;
  client_summary: Summary | null;
  client_signoff: ClientSignoff | null;
  client_signoff_current: boolean;
  tests: Test[];
};
type DefectDraft = {
  subject: string;
  description: string;
  impact: string;
  urgency: string;
};
type Attempt = {
  id: number;
  attempt_number: number;
  result: string;
  actual_result: string;
  failure_reason: string | null;
  blocking_reason: string | null;
  comment: string | null;
  tested_at: string;
};

export function PortalUatPage() {
  const cache = useQueryClient();
  const [selected, setSelected] = useState<number | null>(null);
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState<"PASS" | "FAIL" | "BLOCKED">("PASS");
  const [actual, setActual] = useState("");
  const [reason, setReason] = useState("");
  const [comment, setComment] = useState("");
  const [severity, setSeverity] = useState("MEDIUM");
  const [signoffComment, setSignoffComment] = useState("");
  const [defectDraft, setDefectDraft] = useState<DefectDraft | null>(null);
  const cycles = useQuery({
    queryKey: ["portal-uat-cycles"],
    queryFn: async () => (await api.get<Cycle[]>("/portal/uat/cycles")).data,
  });
  const attempts = useQuery({
    queryKey: ["portal-uat-attempts", selected],
    enabled: selected !== null,
    queryFn: async () =>
      (await api.get<Attempt[]>(`/portal/uat/tests/${selected}/attempts`)).data,
  });
  const execute = useMutation({
    mutationFn: async (testId: number) =>
      api.post(`/portal/uat/tests/${testId}/attempts`, {
        result,
        actual_result: actual,
        failure_reason: result === "FAIL" ? reason : null,
        blocking_reason: result === "BLOCKED" ? reason : null,
        severity: result === "FAIL" ? severity : null,
        comment,
      }),
    onSuccess: async () => {
      setError("");
      setActual("");
      setReason("");
      setComment("");
      await cache.invalidateQueries({ queryKey: ["portal-uat-cycles"] });
      await cache.invalidateQueries({
        queryKey: ["portal-uat-attempts", selected],
      });
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "Could not record your UAT result.")),
  });
  const moveWorkflow = useMutation({
    mutationFn: async ({
      testId,
      workflowStatus,
    }: {
      testId: number;
      workflowStatus: "READY" | "IN_PROGRESS";
    }) =>
      api.put(`/portal/uat/tests/${testId}/workflow`, {
        workflow_status: workflowStatus,
      }),
    onSuccess: async () => {
      setError("");
      await cache.invalidateQueries({ queryKey: ["portal-uat-cycles"] });
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "Could not change the UAT test status.")),
  });
  const signoff = useMutation({
    mutationFn: async ({
      cycleId,
      decision,
    }: {
      cycleId: number;
      decision: "APPROVED" | "REJECTED" | "ADDITIONAL_TESTING";
    }) =>
      api.post(`/portal/uat/cycles/${cycleId}/signoff`, {
        decision,
        comment: signoffComment,
      }),
    onSuccess: async () => {
      setError("");
      setSignoffComment("");
      await cache.invalidateQueries({ queryKey: ["portal-uat-cycles"] });
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "Could not record the client decision.")),
  });
  const createDefect = useMutation({
    mutationFn: async (testId: number) =>
      api.post(`/portal/uat/tests/${testId}/defect-ticket`, defectDraft),
    onSuccess: async () => {
      setDefectDraft(null);
      setError("");
      await cache.invalidateQueries({ queryKey: ["portal-uat-cycles"] });
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "Could not create the defect ticket.")),
  });
  const prepareDefect = async (testId: number) => {
    try {
      const response = await api.get<DefectDraft>(
        `/portal/uat/tests/${testId}/defect-ticket-draft`,
      );
      setDefectDraft(response.data);
      setError("");
    } catch (cause) {
      setError(apiErrorMessage(cause, "Could not prepare the defect ticket."));
    }
  };
  const current = cycles.data
    ?.flatMap((cycle) => cycle.tests.map((test) => ({ cycle, test })))
    .find(({ test }) => test.id === selected);
  const visibleCycles =
    tab === 3
      ? []
      : cycles.data?.filter((cycle) =>
          tab === 2
            ? cycle.status === "COMPLETED"
            : tab === 1
              ? cycle.tests.some((test) => test.assigned_to_me)
              : cycle.status === "ACTIVE",
        );
  useEffect(() => {
    if (!current) return;
    const allowed = {
      PASS: current.cycle.allow_client_pass,
      FAIL: current.cycle.allow_client_fail,
      BLOCKED: current.cycle.allow_client_blocked,
    };
    if (!allowed[result])
      setResult(
        (["PASS", "FAIL", "BLOCKED"] as const).find(
          (value) => allowed[value],
        ) ?? "PASS",
      );
  }, [current, result]);
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" fontWeight={800}>
          My UAT tests
        </Typography>
        <Typography color="text.secondary">
          Review assigned tests and record your acceptance results.
        </Typography>
      </Paper>
      <Tabs
        value={tab}
        onChange={(_, value: number) => {
          setTab(value);
          setSelected(null);
        }}
      >
        <Tab label="Active UAT" />
        <Tab label="My tests" />
        <Tab label="Completed UAT" />
        <Tab label="Deployment" />
      </Tabs>
      {tab === 3 && <DeploymentTracker portal />}
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      {cycles.isError && (
        <Alert severity="error">
          {apiErrorMessage(cycles.error, "Could not load UAT cycles.")}
        </Alert>
      )}
      {!cycles.isLoading && !cycles.data?.length && (
        <Alert severity="info">No UAT cycles are available to you.</Alert>
      )}
      {visibleCycles?.map((cycle) => {
        const visibleTests = cycle.tests.filter(
          (test) => tab !== 1 || test.assigned_to_me,
        );
        return (
          <Paper
            key={cycle.id}
            sx={{ p: { xs: 1.5, md: 2.5 }, borderRadius: 3 }}
          >
            <Typography variant="h6" fontWeight={850}>
              {cycle.code} · {cycle.title}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Role: {cycle.role.toLowerCase()} · Release {cycle.release_version}{" "}
              · {cycle.status}
            </Typography>
            {visibleTests.length === 0 ? (
              <Typography variant="body2" sx={{ mt: 1 }}>
                No tests are assigned to you in this cycle.
              </Typography>
            ) : (
              <PortalUatWorkspace
                cycle={cycle}
                tests={visibleTests}
                selectedId={selected}
                moving={moveWorkflow.isPending}
                onMove={(testId, workflowStatus) =>
                  moveWorkflow.mutate({ testId, workflowStatus })
                }
                onOpen={(test, quickResult) => {
                  setSelected(test.id);
                  setDefectDraft(null);
                  if (quickResult) {
                    setResult(quickResult);
                    setReason("");
                    setActual("");
                    setComment("");
                  }
                }}
              />
            )}
            {(cycle.allow_client_signoff ||
              cycle.allow_client_request_testing) &&
              cycle.client_summary && (
                <Stack spacing={1} sx={{ mt: 2 }}>
                  <Typography variant="h6">Client acceptance</Typography>
                  <Typography variant="body2">
                    {cycle.client_summary.passed}/{cycle.client_summary.total}{" "}
                    passed · {cycle.client_summary.failed} failed ·{" "}
                    {cycle.client_summary.blocked} blocked ·{" "}
                    {cycle.client_summary.not_tested} not tested ·{" "}
                    {cycle.client_summary.open_defects} open defects ·{" "}
                    {cycle.client_summary.mandatory_outstanding} mandatory
                    outstanding
                  </Typography>
                  <Typography variant="body2">
                    Completion {cycle.client_summary.completion_percent}% · Pass
                    rate {cycle.client_summary.pass_rate}%
                  </Typography>
                  {cycle.client_signoff && (
                    <Alert
                      severity={
                        cycle.client_signoff.decision === "APPROVED"
                          ? "success"
                          : "info"
                      }
                    >
                      Latest decision:{" "}
                      {cycle.client_signoff.decision.replaceAll("_", " ")} ·{" "}
                      {new Date(
                        cycle.client_signoff.decided_at,
                      ).toLocaleString()}
                      {cycle.client_signoff.comment &&
                        ` · ${cycle.client_signoff.comment}`}
                    </Alert>
                  )}
                  {!cycle.client_signoff_current &&
                    cycle.status === "ACTIVE" && (
                      <>
                        <TextField
                          multiline
                          label="Decision comment"
                          value={signoffComment}
                          onChange={(event) =>
                            setSignoffComment(event.target.value)
                          }
                        />
                        <Stack direction="row" flexWrap="wrap" gap={1}>
                          {cycle.allow_client_signoff && (
                            <Button
                              variant="contained"
                              disabled={
                                signoff.isPending ||
                                cycle.client_summary.total === 0 ||
                                cycle.client_summary.mandatory_outstanding >
                                  0 ||
                                cycle.client_summary.failed > 0 ||
                                cycle.client_summary.blocked > 0 ||
                                cycle.client_summary.open_defects > 0
                              }
                              onClick={() =>
                                signoff.mutate({
                                  cycleId: cycle.id,
                                  decision: "APPROVED",
                                })
                              }
                            >
                              Approve UAT
                            </Button>
                          )}
                          {cycle.allow_client_signoff && (
                            <Button
                              color="error"
                              variant="outlined"
                              disabled={
                                signoff.isPending || !signoffComment.trim()
                              }
                              onClick={() =>
                                signoff.mutate({
                                  cycleId: cycle.id,
                                  decision: "REJECTED",
                                })
                              }
                            >
                              Reject UAT
                            </Button>
                          )}
                          <Button
                            variant="outlined"
                            disabled={
                              signoff.isPending || !signoffComment.trim()
                            }
                            onClick={() =>
                              signoff.mutate({
                                cycleId: cycle.id,
                                decision: "ADDITIONAL_TESTING",
                              })
                            }
                          >
                            Request additional testing
                          </Button>
                        </Stack>
                      </>
                    )}
                </Stack>
              )}
            <PortalUatActivity cycleId={cycle.id} />
          </Paper>
        );
      })}
      <Drawer
        anchor="right"
        open={Boolean(current)}
        onClose={() => setSelected(null)}
        PaperProps={{
          sx: { width: { xs: "100%", sm: 560 }, maxWidth: "100%" },
        }}
      >
        {current && (
          <Box sx={{ p: { xs: 2, sm: 3 } }}>
            <Stack direction="row" alignItems="flex-start" gap={1}>
              <Box flex={1}>
                <Typography
                  variant="overline"
                  color="primary.main"
                  fontWeight={850}
                >
                  {current.test.snapshot.code}
                </Typography>
                <Typography variant="h5" fontWeight={850}>
                  {current.test.snapshot.title}
                </Typography>
              </Box>
              <IconButton
                aria-label="Close test details"
                onClick={() => setSelected(null)}
              >
                <Close />
              </IconButton>
            </Stack>
            {!current.test.assigned_to_me && (
              <Alert severity="info" sx={{ mt: 2 }}>
                This test is assigned to another tester. You can review it, but
                only the assigned tester can change its status or record a
                result.
              </Alert>
            )}
            {current.test.snapshot.preconditions && (
              <Typography sx={{ mt: 2 }}>
                Preconditions: {current.test.snapshot.preconditions}
              </Typography>
            )}
            {current.test.snapshot.steps.map((step, index) => (
              <Typography key={index} variant="body2" sx={{ mt: 0.75 }}>
                {index + 1}. {step.action} → {step.expected_result}
              </Typography>
            ))}
            <Typography sx={{ mt: 1 }}>
              Expected result: {current.test.snapshot.expected_result}
            </Typography>
            <Typography variant="subtitle1" sx={{ mt: 2 }}>
              Your attempt history
            </Typography>
            {!attempts.data?.length && (
              <Typography variant="body2">No attempts recorded.</Typography>
            )}
            {attempts.data?.map((attempt) => (
              <Typography key={attempt.id} variant="body2">
                #{attempt.attempt_number} · {attempt.result} ·{" "}
                {attempt.actual_result}
                {attempt.failure_reason && ` · ${attempt.failure_reason}`}
                {attempt.blocking_reason && ` · ${attempt.blocking_reason}`}
              </Typography>
            ))}
            {current.test.assigned_to_me &&
              current.cycle.allow_client_testing &&
              !current.cycle.client_signoff_current &&
              current.test.client_test_result !== "PASS" &&
              current.test.client_workflow_status !== "BLOCKED" &&
              !(
                current.test.has_linked_ticket &&
                current.test.client_workflow_status === "WAITING_FIX"
              ) && (
                <Stack
                  component="form"
                  spacing={1}
                  sx={{ mt: 2 }}
                  onSubmit={(event: FormEvent) => {
                    event.preventDefault();
                    execute.mutate(current.test.id);
                  }}
                >
                  <TextField
                    select
                    label="Result"
                    value={result}
                    onChange={(event) => {
                      setResult(event.target.value as typeof result);
                      setReason("");
                    }}
                  >
                    {current.cycle.allow_client_pass && (
                      <MenuItem value="PASS">Pass</MenuItem>
                    )}
                    {current.cycle.allow_client_fail && (
                      <MenuItem value="FAIL">Fail</MenuItem>
                    )}
                    {current.cycle.allow_client_blocked && (
                      <MenuItem value="BLOCKED">Blocked</MenuItem>
                    )}
                  </TextField>
                  {result !== "BLOCKED" && (
                    <TextField
                      required
                      multiline
                      label="Actual result"
                      value={actual}
                      onChange={(event) => setActual(event.target.value)}
                    />
                  )}
                  {result !== "PASS" && (
                    <TextField
                      required
                      multiline
                      label={
                        result === "FAIL"
                          ? "Failure description"
                          : "Blocking reason"
                      }
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                    />
                  )}
                  {result === "FAIL" && (
                    <TextField
                      select
                      label="Severity"
                      value={severity}
                      onChange={(event) => setSeverity(event.target.value)}
                    >
                      {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((level) => (
                        <MenuItem key={level} value={level}>
                          {level}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                  <TextField
                    required={result === "BLOCKED"}
                    multiline
                    label="Comment"
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                  />
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={
                      execute.isPending ||
                      !current.cycle[
                        `allow_client_${result.toLowerCase()}` as "allow_client_pass"
                      ]
                    }
                  >
                    Record result
                  </Button>
                </Stack>
              )}
            {current.test.assigned_to_me &&
              current.cycle.allow_client_create_ticket_from_failure &&
              current.test.client_test_result === "FAIL" &&
              !current.test.has_linked_ticket && (
                <Button
                  onClick={() => prepareDefect(current.test.id)}
                  sx={{ alignSelf: "flex-start" }}
                >
                  Review defect ticket
                </Button>
              )}
            {current.test.assigned_to_me &&
              defectDraft &&
              current.test.client_test_result === "FAIL" &&
              !current.test.has_linked_ticket && (
                <Stack spacing={1} sx={{ mt: 1 }}>
                  <Typography variant="h6">
                    Review ticket before creation
                  </Typography>
                  <TextField
                    required
                    label="Subject"
                    value={defectDraft.subject}
                    onChange={(event) =>
                      setDefectDraft({
                        ...defectDraft,
                        subject: event.target.value,
                      })
                    }
                  />
                  <TextField
                    required
                    multiline
                    minRows={6}
                    label="Description"
                    value={defectDraft.description}
                    onChange={(event) =>
                      setDefectDraft({
                        ...defectDraft,
                        description: event.target.value,
                      })
                    }
                  />
                  {(["impact", "urgency"] as const).map((field) => (
                    <TextField
                      key={field}
                      select
                      label={field}
                      value={defectDraft[field]}
                      onChange={(event) =>
                        setDefectDraft({
                          ...defectDraft,
                          [field]: event.target.value,
                        })
                      }
                    >
                      {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
                        <MenuItem key={value} value={value}>
                          {value}
                        </MenuItem>
                      ))}
                    </TextField>
                  ))}
                  <Stack direction="row" gap={1}>
                    <Button
                      variant="contained"
                      disabled={
                        createDefect.isPending ||
                        defectDraft.subject.trim().length < 5 ||
                        defectDraft.description.trim().length < 10
                      }
                      onClick={() => createDefect.mutate(current.test.id)}
                    >
                      Create defect ticket
                    </Button>
                    <Button onClick={() => setDefectDraft(null)}>Cancel</Button>
                  </Stack>
                </Stack>
              )}
            {current.test.linked_ticket && (
              <Button
                href={`/portal/tickets/${current.test.linked_ticket.id}`}
                sx={{ alignSelf: "flex-start" }}
              >
                Linked ticket: {current.test.linked_ticket.ticket_number}
              </Button>
            )}
            {current.test.assigned_to_me && (
              <UatCollaborationPanel
                testId={current.test.id}
                attempts={attempts.data ?? []}
                portal
                canComment={current.cycle.allow_client_comments}
                canUpload={current.cycle.allow_client_attachments}
              />
            )}
            {current.test.has_linked_ticket &&
              current.test.client_workflow_status === "WAITING_FIX" && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  The linked defect ticket must be resolved before you can
                  retest this case.
                </Alert>
              )}
            {current.test.client_workflow_status === "BLOCKED" && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                This test is blocked. Ask your UAT coordinator to unblock it.
              </Alert>
            )}
          </Box>
        )}
      </Drawer>
    </Stack>
  );
}
