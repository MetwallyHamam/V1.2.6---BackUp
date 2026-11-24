import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  Drawer,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { UatCycleReview } from "./UatCycleReview";
import { UatSignoffPanel } from "./UatSignoffPanel";
import { UatPortalSettings } from "./UatPortalSettings";
import { UatCollaborationPanel } from "./UatCollaborationPanel";
import { UatPortfolioPanel } from "./UatPortfolioPanel";
import { UatSharePanel } from "./UatSharePanel";
import { UatImportPanel } from "./UatImportPanel";
import { UatActivityPanel } from "./UatActivityPanel";
import { UatBulkPanel } from "./UatBulkPanel";
import { UatLibraryActions } from "./UatLibraryActions";
import { UatResultsReport } from "./UatResultsReport";
import { UatChecklistBuilder } from "./UatChecklistBuilder";
import { UatCycleTestPicker } from "./UatCycleTestPicker";
import { UatCycleWizard } from "./UatCycleWizard";
import { UatCycleEditor } from "./UatCycleEditor";
import { DeploymentTracker } from "./DeploymentTracker";

type Step = { action: string; expected_result: string };
type TestCase = {
  id: number;
  code: string;
  title: string;
  product_id: number | null;
  module_id: number | null;
  feature_name: string | null;
  description: string | null;
  expected_result: string;
  preconditions: string | null;
  priority: string;
  is_mandatory: boolean;
  is_active: boolean;
  version: number;
  steps: Step[];
};
type Template = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  product_id: number | null;
  category_id: number | null;
  scope_type: "GLOBAL" | "CLIENT" | "CONTRACT";
  client_id: number | null;
  client_ids: number[];
  contract_id: number | null;
  current_version: number;
  is_active: boolean;
  test_case_ids: number[];
  section_names: Record<number, string>;
};
type CycleTest = {
  id: number;
  test_case_id: number | null;
  display_order: number;
  snapshot: TestCase;
  owner_user_id: number | null;
  client_tester_user_id: number | null;
  client_test_result: string;
  client_workflow_status: string;
  workflow_status: string;
  test_result: string;
  attempt_count: number;
  retest_count: number;
  comment_count: number;
  evidence_count: number;
  due_date: string | null;
  priority: string;
  linked_ticket_id: number | null;
  linked_ticket_number: string | null;
};
type Cycle = {
  id: number;
  code: string;
  title: string;
  client_id: number;
  contract_id: number | null;
  product_id: number | null;
  release_version: string;
  description: string | null;
  start_date: string | null;
  due_date: string | null;
  coordinator_user_id: number;
  engineer_user_ids: number[];
  coordinator_user_ids: number[];
  client_tester_user_ids: number[];
  status: string;
  total_tests: number;
  passed: number;
  failed: number;
  portal_settings: {
    portal_visible: boolean;
    allow_client_testing: boolean;
    allow_client_pass: boolean;
    allow_client_fail: boolean;
    allow_client_blocked: boolean;
    allow_client_view_linked_ticket: boolean;
    allow_client_signoff: boolean;
    allow_client_comments: boolean;
    allow_client_attachments: boolean;
    allow_client_create_ticket_from_failure: boolean;
    client_approver_user_id: number | null;
    client_coordinator_user_id: number | null;
    client_access_start_at: string | null;
    client_access_end_at: string | null;
  };
  tests: CycleTest[];
};
type Metadata = {
  clients: { id: number; name: string }[];
  contracts: { id: number; client_id: number; name: string }[];
  products: { id: number; name: string }[];
  modules: { id: number; product_id: number; name: string }[];
  users: {
    id: number;
    name: string;
    user_type: string;
    client_ids: number[];
    department?: string | null;
  }[];
};
type Progress = {
  id: number;
  feature_area: string;
  backend_status: string;
  frontend_status: string;
  database_status: string;
  testing_status: string;
  overall_status: string;
  notes: string | null;
};
type Attempt = {
  id: number;
  attempt_number: number;
  execution_source: string;
  result: string;
  actual_result: string;
  failure_reason: string | null;
  blocking_reason: string | null;
  severity: string | null;
  linked_ticket_id: number | null;
  comment: string | null;
  tested_at: string;
};
type DefectDraft = {
  subject: string;
  description: string;
  impact: string;
  urgency: string;
  entitlement_override_reason?: string;
};
type ExecutionDraft = { result: "PASS" | "FAIL" | "BLOCKED"; actualResult: string; comment: string; failureReason: string; blockingReason: string; severity: string; failureCategory: string };
const blankCase = () => ({
  code: "",
  title: "",
  product_id: null as number | null,
  module_id: null as number | null,
  feature_name: "",
  description: "",
  expected_result: "",
  preconditions: "",
  priority: "MEDIUM",
  is_mandatory: true,
  steps: [{ action: "", expected_result: "" }],
});
const statuses = [
  "NOT_STARTED",
  "IN_PROGRESS",
  "COMPLETED",
  "BLOCKED",
  "NEEDS_REVIEW",
  "DEFERRED",
];

export function UatPage() {
  const { hasPermission, user } = useAuth();
  const cache = useQueryClient();
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState(0);
  const [setupView, setSetupView] = useState<"templates" | "cases">(
    "templates",
  );
  const [error, setError] = useState("");
  const [caseDraft, setCaseDraft] = useState<
    (ReturnType<typeof blankCase> & { id?: number }) | null
  >(null);
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);
  const [selectedTest, setSelectedTest] = useState<number | null>(null);
  const [result, setResult] = useState<"PASS" | "FAIL" | "BLOCKED">("PASS");
  const [actualResult, setActualResult] = useState("");
  const [comment, setComment] = useState("");
  const [failureReason, setFailureReason] = useState("");
  const [blockingReason, setBlockingReason] = useState("");
  const [severity, setSeverity] = useState("MEDIUM");
  const [failureCategory, setFailureCategory] = useState("Software Bug");
  const [addingToCycle, setAddingToCycle] = useState(false);
  const [cycleAdd, setCycleAdd] = useState({
    template_ids: [] as number[],
    test_case_ids: [] as number[],
  });
  const [adHocDraft, setAdHocDraft] = useState<ReturnType<
    typeof blankCase
  > | null>(null);
  const [defectDraft, setDefectDraft] = useState<DefectDraft | null>(null);
  const [progressDraft, setProgressDraft] = useState<Progress | null>(null);
  const cases = useQuery({
    queryKey: ["uat-cases"],
    queryFn: async () => (await api.get<TestCase[]>("/uat/test-cases")).data,
  });
  const templates = useQuery({
    queryKey: ["uat-templates"],
    queryFn: async () => (await api.get<Template[]>("/uat/templates")).data,
  });
  const cycles = useQuery({
    queryKey: ["uat-cycles"],
    queryFn: async () => (await api.get<Cycle[]>("/uat/cycles")).data,
  });
  const metadata = useQuery({
    queryKey: ["uat-metadata"],
    queryFn: async () => (await api.get<Metadata>("/uat/metadata")).data,
  });
  const progress = useQuery({
    queryKey: ["uat-progress"],
    enabled: hasPermission("uat.progress.view"),
    queryFn: async () =>
      (await api.get<Progress[]>("/uat/implementation-progress")).data,
  });
  const attempts = useQuery({
    queryKey: ["uat-attempts", selectedTest],
    enabled: selectedTest !== null,
    queryFn: async () =>
      (await api.get<Attempt[]>(`/uat/cycle-tests/${selectedTest}/attempts`))
        .data,
  });
  const refresh = async () => {
    await cache.invalidateQueries({ queryKey: ["uat-cases"] });
    await cache.invalidateQueries({ queryKey: ["uat-templates"] });
    await cache.invalidateQueries({ queryKey: ["uat-cycles"] });
    await cache.invalidateQueries({ queryKey: ["uat-dashboard"] });
    await cache.invalidateQueries({ queryKey: ["uat-signoff"] });
    await cache.invalidateQueries({ queryKey: ["uat-attempts"] });
    await cache.invalidateQueries({ queryKey: ["uat-progress"] });
  };
  const action = useMutation({
    mutationFn: async (run: () => Promise<unknown>) => run(),
    onSuccess: async () => {
      setError("");
      await refresh();
    },
    onError: (cause) =>
      setError(apiErrorMessage(cause, "The UAT action failed.")),
  });
  const selected = cycles.data?.find((cycle) => cycle.id === selectedCycle);
  const executionIndex = selected?.tests.findIndex((test) => test.id === selectedTest) ?? -1;
  useEffect(() => {
    if (selectedTest === null) return;
    window.sessionStorage.setItem(`uat-execution-draft:${selectedTest}`, JSON.stringify({ result, actualResult, comment, failureReason, blockingReason, severity, failureCategory }));
  }, [selectedTest, result, actualResult, comment, failureReason, blockingReason, severity, failureCategory]);
  const saveExecutionDraft = () => {
    if (selectedTest === null) return;
    window.sessionStorage.setItem(`uat-execution-draft:${selectedTest}`, JSON.stringify({ result, actualResult, comment, failureReason, blockingReason, severity, failureCategory }));
  };
  const openExecution = (testId: number, quickResult?: "PASS" | "FAIL" | "BLOCKED") => {
    saveExecutionDraft();
    const saved = window.sessionStorage.getItem(`uat-execution-draft:${testId}`);
    let draft: ExecutionDraft | null = null;
    try { draft = saved ? JSON.parse(saved) as ExecutionDraft : null; } catch { window.sessionStorage.removeItem(`uat-execution-draft:${testId}`); }
    setSelectedTest(testId);
    setResult(quickResult ?? draft?.result ?? "PASS");
    setActualResult(draft?.actualResult ?? "");
    setComment(draft?.comment ?? "");
    setFailureReason(draft?.failureReason ?? "");
    setBlockingReason(draft?.blockingReason ?? "");
    setSeverity(draft?.severity ?? "MEDIUM");
    setFailureCategory(draft?.failureCategory ?? "Software Bug");
    setDefectDraft(null);
  };
  useEffect(() => {
    const cycleId = Number(searchParams.get("cycle_id") || 0);
    const testId = Number(searchParams.get("test_id") || 0);
    if (!cycleId || !cycles.data?.some((cycle) => cycle.id === cycleId)) return;
    setSelectedCycle(cycleId);
    setTab(1);
    if (testId && cycles.data.find((cycle) => cycle.id === cycleId)?.tests.some((test) => test.id === testId)) {
      openExecution(testId);
    }
  }, [cycles.data, searchParams]);
  const closeExecution = () => {
    saveExecutionDraft();
    setSelectedTest(null);
  };
  const execute = (event: FormEvent) => {
    event.preventDefault();
    if (selectedTest === null) return;
    action.mutate(() =>
      api.post(`/uat/cycle-tests/${selectedTest}/attempts`, {
        result,
        actual_result: result === "BLOCKED" ? blockingReason : actualResult,
        comment,
        failure_reason: result === "FAIL" ? failureReason : null,
        failure_category: result === "FAIL" ? failureCategory : null,
        blocking_reason: result === "BLOCKED" ? blockingReason : null,
        severity: result === "FAIL" ? severity : null,
      }),
    );
  };
  const loadDefectDraft = async (testId: number) => {
    try {
      const response = await api.get<DefectDraft>(
        `/uat/cycle-tests/${testId}/defect-ticket-draft`,
      );
      setDefectDraft(response.data);
      setError("");
    } catch (cause) {
      setError(apiErrorMessage(cause, "Could not prepare the defect ticket."));
    }
  };
  return (
    <Stack spacing={2.5}>
      <Paper sx={{ p: { xs: 2, md: 3 } }}>
        <Typography variant="h4" fontWeight={800}>
          User Acceptance Testing
        </Typography>
        <Typography color="text.secondary">
          Launch client testing, follow progress, resolve failed scenarios, and
          complete sign-off.
        </Typography>
      </Paper>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      <Tabs
        value={tab}
        onChange={(_, value: number) => setTab(value)}
        variant="scrollable"
        scrollButtons="auto"
      >
        <Tab label="UAT workspace" />
        <Tab label="Setup" />
        <Tab label="Client review" />
        <Tab label="Reports" />
        <Tab label="Deployment" />
        {hasPermission("uat.progress.view") && <Tab label="System status" />}
      </Tabs>
      {tab === 0 && (
        <Stack spacing={2}>
          {hasPermission("uat.cycle.manage") && metadata.data && (
            <UatCycleWizard
              templates={templates.data ?? []}
              metadata={metadata.data}
              currentUserId={user?.id ?? 0}
              onCreated={async (id) => {
                setSelectedCycle(id);
                await refresh();
              }}
            />
          )}
          <TextField
            select
            size="small"
            label="Open UAT cycle"
            value={selectedCycle ?? ""}
            sx={{ maxWidth: 520 }}
            onChange={(event) => {
              setSelectedCycle(Number(event.target.value));
              setSelectedTest(null);
              setCycleAdd({ template_ids: [], test_case_ids: [] });
              setAddingToCycle(false);
            }}
          >
            <MenuItem value="" disabled>
              Select a cycle
            </MenuItem>
            {cycles.data?.map((cycle) => (
              <MenuItem key={cycle.id} value={cycle.id}>
                {cycle.code} · {cycle.title} ·{" "}
                {cycle.status.replaceAll("_", " ")}
              </MenuItem>
            ))}
          </TextField>
          {selected && (
            <Paper sx={{ p: 2 }}>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
              >
                <Box>
                  <Typography variant="h6">
                    {selected.title} · {selected.release_version}
                  </Typography>
                  <Typography>
                    {selected.status} · {selected.passed}/{selected.total_tests}{" "}
                    passed · {selected.failed} failed
                  </Typography>
                </Box>
                {hasPermission("uat.cycle.manage") && (
                  <Stack direction="row" gap={1}>
                    {selected.status !== "COMPLETED" && metadata.data && (
                      <UatCycleEditor
                        cycle={selected}
                        users={metadata.data.users}
                        onSaved={refresh}
                      />
                    )}
                    {selected.status === "DRAFT" && (
                      <Button
                        variant="contained"
                        onClick={() =>
                          action.mutate(() =>
                            api.post(`/uat/cycles/${selected.id}/activate`),
                          )
                        }
                      >
                        Activate
                      </Button>
                    )}
                  </Stack>
                )}
              </Stack>
              {hasPermission("uat.cycle.manage") && (
                <Box sx={{ mt: 1 }}>
                  <Button onClick={() => setAddingToCycle(!addingToCycle)}>
                    {addingToCycle ? "Close add tests" : "Add tests"}
                  </Button>
                </Box>
              )}
              {addingToCycle && hasPermission("uat.cycle.manage") && (
                <Paper
                  component="form"
                  variant="outlined"
                  sx={{ p: 2, mt: 1 }}
                  onSubmit={(event: FormEvent) => {
                    event.preventDefault();
                    action.mutate(() =>
                      api
                        .post(`/uat/cycles/${selected.id}/tests`, {
                          ...cycleAdd,
                          ad_hoc_tests: adHocDraft
                            ? [
                                {
                                  title: adHocDraft.title,
                                  preconditions: adHocDraft.preconditions,
                                  expected_result: adHocDraft.expected_result,
                                  priority: adHocDraft.priority,
                                  steps: adHocDraft.steps,
                                },
                              ]
                            : [],
                        })
                        .then((response) => {
                          setAddingToCycle(false);
                          setCycleAdd({ template_ids: [], test_case_ids: [] });
                          setAdHocDraft(null);
                          return response;
                        }),
                    );
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={700}>
                    Add to this cycle
                  </Typography>
                  <Typography variant="caption">
                    Existing tests are skipped. The current checklist version is
                    copied into the cycle.
                  </Typography>
                  <UatCycleTestPicker
                    cycle={selected}
                    cases={cases.data ?? []}
                    templates={templates.data ?? []}
                    value={cycleAdd}
                    onChange={setCycleAdd}
                  />
                  <Button
                    onClick={() =>
                      setAdHocDraft(adHocDraft ? null : blankCase())
                    }
                  >
                    {adHocDraft
                      ? "Remove ad hoc test"
                      : "Create cycle only test"}
                  </Button>
                  {adHocDraft && (
                    <Stack spacing={1} sx={{ my: 1 }}>
                      <TextField
                        required
                        label="Scenario"
                        value={adHocDraft.title}
                        onChange={(e) =>
                          setAdHocDraft({
                            ...adHocDraft,
                            title: e.target.value,
                          })
                        }
                      />
                      <TextField
                        label="Preconditions"
                        value={adHocDraft.preconditions}
                        onChange={(e) =>
                          setAdHocDraft({
                            ...adHocDraft,
                            preconditions: e.target.value,
                          })
                        }
                      />
                      <TextField
                        required
                        label="Expected result"
                        value={adHocDraft.expected_result}
                        onChange={(e) =>
                          setAdHocDraft({
                            ...adHocDraft,
                            expected_result: e.target.value,
                          })
                        }
                      />
                      {adHocDraft.steps.map((step, index) => (
                        <Stack
                          key={index}
                          direction={{ xs: "column", md: "row" }}
                          gap={1}
                        >
                          <TextField
                            required
                            label={`Step ${index + 1}`}
                            value={step.action}
                            onChange={(e) =>
                              setAdHocDraft({
                                ...adHocDraft,
                                steps: adHocDraft.steps.map((row, position) =>
                                  position === index
                                    ? { ...row, action: e.target.value }
                                    : row,
                                ),
                              })
                            }
                          />
                          <TextField
                            required
                            label="Expected"
                            value={step.expected_result}
                            onChange={(e) =>
                              setAdHocDraft({
                                ...adHocDraft,
                                steps: adHocDraft.steps.map((row, position) =>
                                  position === index
                                    ? {
                                        ...row,
                                        expected_result: e.target.value,
                                      }
                                    : row,
                                ),
                              })
                            }
                          />
                        </Stack>
                      ))}
                      <Button
                        onClick={() =>
                          setAdHocDraft({
                            ...adHocDraft,
                            steps: [
                              ...adHocDraft.steps,
                              { action: "", expected_result: "" },
                            ],
                          })
                        }
                      >
                        Add step
                      </Button>
                    </Stack>
                  )}
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={
                      action.isPending ||
                      (!cycleAdd.template_ids.length &&
                        !cycleAdd.test_case_ids.length &&
                        !adHocDraft)
                    }
                  >
                    Add selected tests
                  </Button>
                </Paper>
              )}
              <UatCycleReview
                cycleId={selected.id}
                tests={selected.tests}
                currentUserId={user?.id ?? null}
                products={metadata.data?.products ?? []}
                modules={metadata.data?.modules ?? []}
                canManage={hasPermission("uat.cycle.manage")}
                onSelectTest={openExecution}
                onQuickResult={(testId, quickResult) => {
                  openExecution(testId, quickResult);
                }}
              />
              <Accordion
                disableGutters
                elevation={0}
                sx={{
                  mt: 2,
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                  "&:before": { display: "none" },
                }}
              >
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box>
                    <Typography fontWeight={750}>More cycle tools</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Bulk assignment, activity history and detailed results
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Stack spacing={2}>
                    {hasPermission("uat.cycle.manage") &&
                      selected.status !== "COMPLETED" && (
                        <UatBulkPanel
                          cycleId={selected.id}
                          tests={selected.tests}
                          users={metadata.data?.users ?? []}
                          onSaved={refresh}
                        />
                      )}
                    <UatActivityPanel cycleId={selected.id} />
                    <UatResultsReport cycleId={selected.id} />
                  </Stack>
                </AccordionDetails>
              </Accordion>
              <Drawer
                anchor="right"
                open={selectedTest !== null}
                onClose={closeExecution}
              >
                <Box sx={{ width: { xs: "100vw", sm: 560 }, p: 2 }}>
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                    sx={{ mb: 1 }}
                  >
                    <Box><Typography variant="h6">Guided test execution</Typography><Typography variant="caption" color="text.secondary">Draft input is kept for this browser session.</Typography></Box>
                    <Button onClick={closeExecution}>Close</Button>
                  </Stack>
                  {selectedTest !== null && executionIndex >= 0 && (
                    <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1} sx={{ mb: 2 }}>
                      <Button disabled={executionIndex === 0} onClick={() => openExecution(selected.tests[executionIndex - 1].id)}>Previous test</Button>
                      <Typography fontWeight={800}>Test {executionIndex + 1} of {selected.tests.length}</Typography>
                      <Button disabled={executionIndex === selected.tests.length - 1} onClick={() => openExecution(selected.tests[executionIndex + 1].id)}>Next test</Button>
                    </Stack>
                  )}
                  <Stack spacing={1}>
                    {selected.tests
                      .filter((test) => test.id === selectedTest)
                      .map((test) => (
                        <Paper key={test.id} variant="outlined" sx={{ p: 1.5 }}>
                          <Stack direction="row" justifyContent="space-between">
                            <Box>
                              <Typography fontWeight={700}>
                                {test.snapshot.code} · {test.snapshot.title}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">Priority {test.priority} · {test.attempt_count} attempts · {test.evidence_count} evidence · {test.comment_count} comments</Typography>
                            </Box>
                            <Stack direction="row" gap={1} alignItems="center">
                              <Chip
                                label={test.workflow_status.replaceAll(
                                  "_",
                                  " ",
                                )}
                                color={
                                  test.test_result === "PASS"
                                    ? "success"
                                    : test.test_result === "FAIL"
                                      ? "error"
                                      : "default"
                                }
                              />
                              <Button
                                onClick={() => {
                                  setSelectedTest(test.id);
                                  setDefectDraft(null);
                                }}
                              >
                                Details
                              </Button>
                            </Stack>
                          </Stack>
                          {selectedTest === test.id && (
                            <Stack spacing={1} sx={{ mt: 2 }}>
                              <Paper variant="outlined" sx={{ p: 1.5 }}>
                                <Typography variant="subtitle2">Preconditions</Typography>
                                <Typography variant="body2" color={test.snapshot.preconditions ? "text.primary" : "text.secondary"}>{test.snapshot.preconditions || "No preconditions specified."}</Typography>
                              </Paper>
                              <Paper variant="outlined" sx={{ p: 1.5 }}>
                                <Typography variant="subtitle2">Test steps</Typography>
                                <Stack component="ol" spacing={1} sx={{ pl: 2.5, mb: 0 }}>{test.snapshot.steps.map((step, index) => <Box component="li" key={`${index}-${step.action}`}><Typography variant="body2" fontWeight={700}>{step.action}</Typography><Typography variant="caption" color="text.secondary">Expected: {step.expected_result}</Typography></Box>)}</Stack>
                              </Paper>
                              <Alert severity="info"><strong>Expected result:</strong> {test.snapshot.expected_result}</Alert>
                              <Typography variant="subtitle2">
                                Attempt history · {test.retest_count} retests
                              </Typography>
                              {attempts.data?.map((attempt) => (
                                <Typography key={attempt.id} variant="body2">
                                  #{attempt.attempt_number} ·{" "}
                                  {attempt.execution_source === "CLIENT_PORTAL"
                                    ? "Client"
                                    : "Internal"}{" "}
                                  · {attempt.result}: {attempt.actual_result}
                                  {attempt.failure_reason &&
                                    ` · ${attempt.failure_reason}`}
                                  {attempt.blocking_reason &&
                                    ` · Blocked: ${attempt.blocking_reason}`}
                                  {attempt.comment && ` · ${attempt.comment}`}
                                </Typography>
                              ))}
                              <UatCollaborationPanel
                                testId={test.id}
                                attempts={attempts.data ?? []}
                                portal={false}
                                canComment={
                                  selected.status === "ACTIVE" &&
                                  hasPermission("uat.test.execute")
                                }
                                canUpload={
                                  selected.status === "ACTIVE" &&
                                  hasPermission("uat.test.execute")
                                }
                              />
                              {test.linked_ticket_id && (
                                <Button
                                  href={`/tickets/${test.linked_ticket_id}`}
                                  sx={{ alignSelf: "flex-start" }}
                                >
                                  Linked ticket: {test.linked_ticket_number}
                                </Button>
                              )}
                              {test.workflow_status === "BLOCKED" &&
                                hasPermission("uat.cycle.manage") && (
                                  <Button
                                    onClick={() =>
                                      action.mutate(() =>
                                        api.post(
                                          `/uat/cycle-tests/${test.id}/unblock`,
                                        ),
                                      )
                                    }
                                    sx={{ alignSelf: "flex-start" }}
                                  >
                                    Unblock test
                                  </Button>
                                )}
                              {selected.status !== "ACTIVE" && <Alert severity="info">Activate this cycle before recording a test result.</Alert>}
                              {test.test_result === "PASS" && <Alert severity="success">This test passed. No further result action is available in this milestone.</Alert>}
                              {test.workflow_status === "BLOCKED" && !hasPermission("uat.cycle.manage") && <Alert severity="warning">A UAT manager must unblock this test before another attempt.</Alert>}
                              {test.workflow_status === "NEEDS_INVESTIGATION" && <Alert severity="warning">The failure must be investigated, linked to a defect, or returned to Ready by a coordinator.</Alert>}
                              {["WAITING_FIX", "FIX_IN_PROGRESS"].includes(test.workflow_status) && test.linked_ticket_id && <Alert severity="info">Retesting becomes available after the linked defect is resolved.</Alert>}
                              {selected.status === "ACTIVE" &&
                                test.test_result !== "PASS" &&
                                !["BLOCKED", "NEEDS_INVESTIGATION"].includes(
                                  test.workflow_status,
                                ) &&
                                (test.workflow_status !== "WAITING_FIX" ||
                                  !test.linked_ticket_id) &&
                                hasPermission("uat.test.execute") && (
                                  <Stack
                                    component="form"
                                    onSubmit={execute}
                                    gap={1}
                                  >
                                    <TextField
                                      select
                                      label="Result"
                                      value={result}
                                      onChange={(e) =>
                                        setResult(
                                          e.target.value as
                                            "PASS" | "FAIL" | "BLOCKED",
                                        )
                                      }
                                    >
                                      <MenuItem value="PASS">PASS</MenuItem>
                                      <MenuItem value="FAIL">FAIL</MenuItem>
                                      <MenuItem value="BLOCKED">
                                        BLOCKED
                                      </MenuItem>
                                    </TextField>
                                    {result !== "BLOCKED" && (
                                      <TextField
                                        required
                                        multiline
                                        label="Actual result"
                                        value={actualResult}
                                        onChange={(e) =>
                                          setActualResult(e.target.value)
                                        }
                                      />
                                    )}
                                    {result === "FAIL" && (
                                      <>
                                        <TextField
                                          required
                                          multiline
                                          label="Failure description"
                                          value={failureReason}
                                          onChange={(e) =>
                                            setFailureReason(e.target.value)
                                          }
                                        />
                                        <TextField
                                          select
                                          label="Severity"
                                          value={severity}
                                          onChange={(e) =>
                                            setSeverity(e.target.value)
                                          }
                                        >
                                          {[
                                            "LOW",
                                            "MEDIUM",
                                            "HIGH",
                                            "CRITICAL",
                                          ].map((value) => (
                                            <MenuItem key={value} value={value}>
                                              {value}
                                            </MenuItem>
                                          ))}
                                        </TextField>
                                        <TextField
                                          select
                                          label="Failure category"
                                          value={failureCategory}
                                          onChange={(e) =>
                                            setFailureCategory(e.target.value)
                                          }
                                        >
                                          {[
                                            "Software Bug",
                                            "Configuration",
                                            "Integration",
                                            "Environment",
                                            "Permission",
                                            "Data",
                                            "Performance",
                                            "Workflow",
                                            "User Misunderstanding",
                                            "Other",
                                          ].map((value) => (
                                            <MenuItem key={value} value={value}>
                                              {value}
                                            </MenuItem>
                                          ))}
                                        </TextField>
                                      </>
                                    )}
                                    {result === "BLOCKED" && (
                                      <TextField
                                        required
                                        multiline
                                        label="Blocking reason"
                                        value={blockingReason}
                                        onChange={(e) =>
                                          setBlockingReason(e.target.value)
                                        }
                                      />
                                    )}
                                    <TextField
                                      required={result === "BLOCKED"}
                                      label="Comment"
                                      value={comment}
                                      onChange={(e) =>
                                        setComment(e.target.value)
                                      }
                                    />
                                    <Button
                                      type="submit"
                                      variant="contained"
                                      disabled={action.isPending}
                                    >
                                      Record result
                                    </Button>
                                  </Stack>
                                )}
                              {test.test_result === "FAIL" &&
                                !test.linked_ticket_id &&
                                hasPermission("ticket.create") && (
                                  <Button
                                    onClick={() => loadDefectDraft(test.id)}
                                    sx={{ alignSelf: "flex-start" }}
                                  >
                                    Create UAT Defect Ticket
                                  </Button>
                                )}
                              {defectDraft &&
                                test.test_result === "FAIL" &&
                                !test.linked_ticket_id && (
                                  <Stack
                                    component="form"
                                    spacing={1}
                                    onSubmit={(event: FormEvent) => {
                                      event.preventDefault();
                                      action.mutate(() =>
                                        api
                                          .post(
                                            `/uat/cycle-tests/${test.id}/defect-ticket`,
                                            defectDraft,
                                          )
                                          .then((response) => {
                                            setDefectDraft(null);
                                            return response;
                                          }),
                                      );
                                    }}
                                  >
                                    <Typography variant="subtitle1">
                                      Review ticket before creation
                                    </Typography>
                                    <TextField
                                      required
                                      label="Subject"
                                      value={defectDraft.subject}
                                      onChange={(e) =>
                                        setDefectDraft({
                                          ...defectDraft,
                                          subject: e.target.value,
                                        })
                                      }
                                    />
                                    <TextField
                                      required
                                      multiline
                                      minRows={8}
                                      label="Description"
                                      value={defectDraft.description}
                                      onChange={(e) =>
                                        setDefectDraft({
                                          ...defectDraft,
                                          description: e.target.value,
                                        })
                                      }
                                    />
                                    {(["impact", "urgency"] as const).map(
                                      (field) => (
                                        <TextField
                                          key={field}
                                          select
                                          label={field}
                                          value={defectDraft[field]}
                                          onChange={(e) =>
                                            setDefectDraft({
                                              ...defectDraft,
                                              [field]: e.target.value,
                                            })
                                          }
                                        >
                                          {[
                                            "LOW",
                                            "MEDIUM",
                                            "HIGH",
                                            "CRITICAL",
                                          ].map((value) => (
                                            <MenuItem key={value} value={value}>
                                              {value}
                                            </MenuItem>
                                          ))}
                                        </TextField>
                                      ),
                                    )}
                                    <TextField
                                      label="Entitlement override reason (if required)"
                                      value={
                                        defectDraft.entitlement_override_reason ??
                                        ""
                                      }
                                      onChange={(e) =>
                                        setDefectDraft({
                                          ...defectDraft,
                                          entitlement_override_reason:
                                            e.target.value,
                                        })
                                      }
                                    />
                                    <Stack direction="row" gap={1}>
                                      <Button
                                        type="submit"
                                        variant="contained"
                                        disabled={action.isPending}
                                      >
                                        Create UAT Defect Ticket
                                      </Button>
                                      <Button
                                        onClick={() => setDefectDraft(null)}
                                      >
                                        Cancel
                                      </Button>
                                    </Stack>
                                  </Stack>
                                )}
                            </Stack>
                          )}
                        </Paper>
                      ))}
                  </Stack>
                </Box>
              </Drawer>
            </Paper>
          )}
        </Stack>
      )}
      {tab === 1 && (
        <Stack spacing={2}>
          <Stack direction="row" gap={1}>
            <Button
              variant={setupView === "templates" ? "contained" : "outlined"}
              onClick={() => setSetupView("templates")}
            >
              Templates
            </Button>
            <Button
              variant={setupView === "cases" ? "contained" : "outlined"}
              onClick={() => setSetupView("cases")}
            >
              Test cases
            </Button>
          </Stack>
          {setupView === "templates" && (
            <>
              {hasPermission("uat.library.manage") && (
                <UatImportPanel kind="checklists" />
              )}
              <UatChecklistBuilder
                cases={cases.data ?? []}
                templates={templates.data ?? []}
                metadata={
                  metadata.data ?? {
                    products: [],
                    modules: [],
                    clients: [],
                    contracts: [],
                  }
                }
                canManage={hasPermission("uat.library.manage")}
                onSaved={refresh}
              />
            </>
          )}
          {setupView === "cases" && (
            <>
              {hasPermission("uat.library.manage") && <UatImportPanel />}
              <Stack spacing={1.5}>
                {hasPermission("uat.library.manage") && (
                  <Button
                    sx={{ alignSelf: "flex-start" }}
                    onClick={() => setCaseDraft(blankCase())}
                  >
                    New test case
                  </Button>
                )}
                {caseDraft && (
                  <Paper
                    component="form"
                    sx={{ p: 2 }}
                    onSubmit={(event: FormEvent) => {
                      event.preventDefault();
                      const payload = {
                        ...caseDraft,
                        steps: caseDraft.steps.filter(
                          (step) => step.action && step.expected_result,
                        ),
                      };
                      action.mutate(() =>
                        caseDraft.id
                          ? api.put(`/uat/test-cases/${caseDraft.id}`, payload)
                          : api.post("/uat/test-cases", payload),
                      );
                      setCaseDraft(null);
                    }}
                  >
                    <Stack spacing={1}>
                      <Typography variant="h6">
                        {caseDraft.id ? "Edit" : "New"} test case
                      </Typography>
                      <TextField
                        required
                        label="Code"
                        value={caseDraft.code}
                        onChange={(e) =>
                          setCaseDraft({ ...caseDraft, code: e.target.value })
                        }
                      />
                      <TextField
                        required
                        label="Title"
                        value={caseDraft.title}
                        onChange={(e) =>
                          setCaseDraft({ ...caseDraft, title: e.target.value })
                        }
                      />
                      <TextField
                        select
                        label="Product"
                        value={caseDraft.product_id ?? ""}
                        onChange={(e) =>
                          setCaseDraft({
                            ...caseDraft,
                            product_id: e.target.value
                              ? Number(e.target.value)
                              : null,
                            module_id: null,
                          })
                        }
                      >
                        <MenuItem value="">None</MenuItem>
                        {metadata.data?.products.map((product) => (
                          <MenuItem key={product.id} value={product.id}>
                            {product.name}
                          </MenuItem>
                        ))}
                      </TextField>
                      <TextField
                        select
                        label="Module"
                        value={caseDraft.module_id ?? ""}
                        onChange={(e) =>
                          setCaseDraft({
                            ...caseDraft,
                            module_id: e.target.value
                              ? Number(e.target.value)
                              : null,
                          })
                        }
                      >
                        <MenuItem value="">None</MenuItem>
                        {metadata.data?.modules
                          .filter(
                            (module) =>
                              !caseDraft.product_id ||
                              module.product_id === caseDraft.product_id,
                          )
                          .map((module) => (
                            <MenuItem key={module.id} value={module.id}>
                              {module.name}
                            </MenuItem>
                          ))}
                      </TextField>
                      <TextField
                        label="Feature"
                        value={caseDraft.feature_name}
                        onChange={(e) =>
                          setCaseDraft({
                            ...caseDraft,
                            feature_name: e.target.value,
                          })
                        }
                      />
                      <TextField
                        multiline
                        label="Description"
                        value={caseDraft.description}
                        onChange={(e) =>
                          setCaseDraft({
                            ...caseDraft,
                            description: e.target.value,
                          })
                        }
                      />
                      <TextField
                        label="Preconditions"
                        value={caseDraft.preconditions}
                        onChange={(e) =>
                          setCaseDraft({
                            ...caseDraft,
                            preconditions: e.target.value,
                          })
                        }
                      />
                      <TextField
                        required
                        label="Expected result"
                        value={caseDraft.expected_result}
                        onChange={(e) =>
                          setCaseDraft({
                            ...caseDraft,
                            expected_result: e.target.value,
                          })
                        }
                      />
                      <TextField
                        select
                        label="Priority"
                        value={caseDraft.priority}
                        onChange={(e) =>
                          setCaseDraft({
                            ...caseDraft,
                            priority: e.target.value,
                          })
                        }
                      >
                        {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(
                          (priority) => (
                            <MenuItem key={priority} value={priority}>
                              {priority}
                            </MenuItem>
                          ),
                        )}
                      </TextField>
                      {caseDraft.steps.map((step, index) => (
                        <Stack
                          key={index}
                          direction={{ xs: "column", md: "row" }}
                          gap={1}
                        >
                          <Button
                            size="small"
                            disabled={caseDraft.steps.length === 1}
                            onClick={() =>
                              setCaseDraft({
                                ...caseDraft,
                                steps: caseDraft.steps.filter(
                                  (_, i) => i !== index,
                                ),
                              })
                            }
                          >
                            Remove
                          </Button>
                          <TextField
                            required
                            fullWidth
                            label={`Step ${index + 1} action`}
                            value={step.action}
                            onChange={(e) =>
                              setCaseDraft({
                                ...caseDraft,
                                steps: caseDraft.steps.map((row, i) =>
                                  i === index
                                    ? { ...row, action: e.target.value }
                                    : row,
                                ),
                              })
                            }
                          />
                          <TextField
                            required
                            fullWidth
                            label="Expected"
                            value={step.expected_result}
                            onChange={(e) =>
                              setCaseDraft({
                                ...caseDraft,
                                steps: caseDraft.steps.map((row, i) =>
                                  i === index
                                    ? {
                                        ...row,
                                        expected_result: e.target.value,
                                      }
                                    : row,
                                ),
                              })
                            }
                          />
                        </Stack>
                      ))}
                      <Button
                        onClick={() =>
                          setCaseDraft({
                            ...caseDraft,
                            steps: [
                              ...caseDraft.steps,
                              { action: "", expected_result: "" },
                            ],
                          })
                        }
                      >
                        Add step
                      </Button>
                      <Stack direction="row" gap={1}>
                        <Button type="submit" variant="contained">
                          Save
                        </Button>
                        <Button onClick={() => setCaseDraft(null)}>
                          Cancel
                        </Button>
                      </Stack>
                    </Stack>
                  </Paper>
                )}
                {cases.data?.map((test) => (
                  <Paper key={test.id} variant="outlined" sx={{ p: 1.5 }}>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      gap={1}
                    >
                      <Box>
                        <Typography fontWeight={700}>
                          {test.code} · {test.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {test.steps.length} steps · {test.priority} ·{" "}
                          {test.is_active ? "Active" : "Archived"}
                        </Typography>
                      </Box>
                      {hasPermission("uat.library.manage") && (
                        <Stack direction="row" gap={1} alignItems="center">
                          {test.is_active && (
                            <Button
                              size="small"
                              onClick={() =>
                                setCaseDraft({
                                  id: test.id,
                                  code: test.code,
                                  title: test.title,
                                  product_id: test.product_id,
                                  module_id: test.module_id,
                                  feature_name: test.feature_name ?? "",
                                  description: test.description ?? "",
                                  expected_result: test.expected_result,
                                  preconditions: test.preconditions ?? "",
                                  priority: test.priority,
                                  is_mandatory: test.is_mandatory,
                                  steps: test.steps,
                                })
                              }
                            >
                              Edit
                            </Button>
                          )}
                          <UatLibraryActions
                            kind="test-cases"
                            item={{
                              id: test.id,
                              code: test.code,
                              name: test.title,
                              is_active: test.is_active,
                            }}
                            onSaved={refresh}
                          />
                        </Stack>
                      )}
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            </>
          )}
        </Stack>
      )}
      {tab === 2 && (
        <Stack spacing={2}>
          <TextField
            select
            size="small"
            label="Client UAT cycle"
            value={selectedCycle ?? ""}
            sx={{ maxWidth: 520 }}
            onChange={(event) => setSelectedCycle(Number(event.target.value))}
          >
            <MenuItem value="" disabled>
              Select a cycle
            </MenuItem>
            {cycles.data?.map((cycle) => (
              <MenuItem key={cycle.id} value={cycle.id}>
                {cycle.code} · {cycle.title}
              </MenuItem>
            ))}
          </TextField>
          {!selected && (
            <Alert severity="info">
              Select a UAT cycle to manage client access, sharing and sign-off.
            </Alert>
          )}
          {selected && (
            <>
              <UatSignoffPanel
                cycleId={selected.id}
                cycleStatus={selected.status}
                userNames={Object.fromEntries(
                  (metadata.data?.users ?? []).map((person) => [
                    person.id,
                    person.name,
                  ]),
                )}
              />
              {hasPermission("uat.cycle.manage") && (
                <UatSharePanel cycleId={selected.id} />
              )}
              <Accordion
                disableGutters
                elevation={0}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                  "&:before": { display: "none" },
                }}
              >
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box>
                    <Typography fontWeight={750}>
                      Portal access and tester assignments
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Advanced publication permissions and per-test client
                      owners
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <UatPortalSettings
                    cycle={selected}
                    users={metadata.data?.users ?? []}
                    canManage={hasPermission("uat.cycle.manage")}
                    onSaved={refresh}
                  />
                </AccordionDetails>
              </Accordion>
            </>
          )}
        </Stack>
      )}
      {tab === 3 && (
        <UatPortfolioPanel
          onOpenCycle={(id) => {
            setSelectedCycle(id);
            setTab(0);
          }}
        />
      )}
      {tab === 4 && <DeploymentTracker />}
      {tab === 5 && hasPermission("uat.progress.view") && (
        <Stack spacing={1}>
          {progress.data?.map((row) => (
            <Paper key={row.id} sx={{ p: 1.5 }}>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
              >
                <Box>
                  <Typography fontWeight={700}>{row.feature_area}</Typography>
                  <Typography variant="body2">
                    Overall: {row.overall_status.replaceAll("_", " ")} ·
                    Backend: {row.backend_status} · Frontend:{" "}
                    {row.frontend_status} · Database: {row.database_status} ·
                    Testing: {row.testing_status}
                  </Typography>
                </Box>
                {hasPermission("uat.progress.manage") && (
                  <Button onClick={() => setProgressDraft(row)}>Update</Button>
                )}
              </Stack>
              {progressDraft?.id === row.id && (
                <Stack
                  component="form"
                  onSubmit={(event: FormEvent) => {
                    event.preventDefault();
                    action.mutate(() =>
                      api.put(
                        `/uat/implementation-progress/${row.id}`,
                        progressDraft,
                      ),
                    );
                    setProgressDraft(null);
                  }}
                  direction={{ xs: "column", md: "row" }}
                  gap={1}
                  sx={{ mt: 1 }}
                >
                  {(
                    [
                      "backend_status",
                      "frontend_status",
                      "database_status",
                      "testing_status",
                      "overall_status",
                    ] as const
                  ).map((field) => (
                    <TextField
                      key={field}
                      select
                      label={field.replace("_status", "")}
                      value={progressDraft[field]}
                      onChange={(e) =>
                        setProgressDraft({
                          ...progressDraft,
                          [field]: e.target.value,
                        })
                      }
                    >
                      {statuses.map((status) => (
                        <MenuItem key={status} value={status}>
                          {status}
                        </MenuItem>
                      ))}
                    </TextField>
                  ))}
                  <Button type="submit" variant="contained">
                    Save
                  </Button>
                </Stack>
              )}
            </Paper>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
