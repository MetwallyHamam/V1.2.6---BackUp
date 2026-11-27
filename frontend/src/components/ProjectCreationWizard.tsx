import { Add, DeleteOutline, ExpandMore, Publish, Save } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  CardActionArea,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Option = { id: number; name: string; account_id?: number; organization_id?: number; product_id?: number; department_id?: number; leader_user_id?: number; member_user_ids?: number[] };
type Options = { accounts: Option[]; organizations: Option[]; clients: Option[]; departments: Option[]; managers: Option[]; products: Option[]; modules: Option[]; teams: Option[] };
type Branch = { id: number; name: string };
type Status = { id: number; name: string; is_active: boolean };
type TaskDraft = { task_number: string; title: string; description?: string | null; predecessor_numbers?: string[]; product_id: string; product_module_id: string; owner_user_id: string; planned_start_at: string; planned_end_at: string; estimate_minutes: string };
type PhaseDraft = { name: string; planned_start_at: string; planned_end_at: string; product_ids: number[]; module_ids: number[]; tasks: TaskDraft[] };
type DocumentDraft = { title: string; document_type: string; reference_url: string; notes: string };

const steps = ["Customer", "Products", "Ownership", "Project", "Phases & tasks", "Documents", "Review"];
const blankTask = (): TaskDraft => ({ task_number: "", title: "", product_id: "", product_module_id: "", owner_user_id: "", planned_start_at: "", planned_end_at: "", estimate_minutes: "0" });
const blankPhase = (): PhaseDraft => ({ name: "", planned_start_at: "", planned_end_at: "", product_ids: [], module_ids: [], tasks: [blankTask()] });
const toggle = (values: number[], id: number) => values.includes(id) ? values.filter((value) => value !== id) : [...values, id];
const iso = (value: string) => new Date(value).toISOString();

type TemplateWindow = { start_offset_minutes: number; duration_minutes: number };
type TemplateTask = TemplateWindow & {
  task_number: string; title: string; description: string | null; product_id: number;
  product_module_id: number | null; estimate_minutes: number; predecessor_numbers: string[];
};
type TemplatePhase = TemplateWindow & { name: string; product_ids: number[]; module_ids: number[]; tasks: TemplateTask[] };
type TemplateVersion = {
  id: number; version_number: number; published_at: string | null;
  plan: { product_ids: number[]; module_ids: number[]; phases: TemplatePhase[] };
};

const localDateTime = (timestamp: number) => {
  const date = new Date(timestamp);
  return new Date(timestamp - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
};

export function ProjectCreationWizard({ open, onClose, onCreated, startingTemplate }: {
  open: boolean; onClose: () => void; onCreated: () => void;
  startingTemplate?: { id: number; versionId: number };
}) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [step, setStep] = useState(0);
  const [expandedProductId, setExpandedProductId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [templateId, setTemplateId] = useState(startingTemplate ? String(startingTemplate.id) : "");
  const [templateVersionId, setTemplateVersionId] = useState(startingTemplate ? String(startingTemplate.versionId) : "");
  const [templateStart, setTemplateStart] = useState("");
  const [appliedTemplate, setAppliedTemplate] = useState("");
  const [sourceVersionId, setSourceVersionId] = useState<number | null>(null);
  const [sourceTemplateId, setSourceTemplateId] = useState<number | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [savedTemplate, setSavedTemplate] = useState("");
  const [form, setForm] = useState({ project_number: "", name: "", description: "", account_id: "", organization_id: "", client_id: "", branch_ids: [] as number[], product_ids: [] as number[], module_ids: [] as number[], owning_department_id: "", requested_department_id: "", requested_team_id: "", project_manager_user_id: "", intake_owner_user_id: "", planned_start_date: "", planned_end_date: "", priority: "NORMAL", capability_notes: "" });
  const [phases, setPhases] = useState<PhaseDraft[]>([blankPhase()]);
  const [documents, setDocuments] = useState<DocumentDraft[]>([]);
  type Checkpoint = {
    step: number;
    form: typeof form;
    phases: PhaseDraft[];
    documents: DocumentDraft[];
    sourceVersionId: number | null;
    sourceTemplateId?: number | null;
    appliedTemplate: string;
  };
  const checkpointKey = ["project-wizard-draft", user?.id] as const;
  const [loadedVersion, setLoadedVersion] = useState<number | null>(null);
  const savedDraft = useQuery({
    queryKey: checkpointKey,
    queryFn: async () => (await api.get<{ version: number; checkpoint: Checkpoint } | null>("/projects/wizard-draft")).data,
    enabled: open && Boolean(user),
    refetchOnMount: "always",
  });
  const checkpoint = savedDraft.data?.checkpoint;
  const [organizationDraft, setOrganizationDraft] = useState({ code: "", name: "" });
  const [clientDraft, setClientDraft] = useState("");
  const [branchDraft, setBranchDraft] = useState("");
  const options = useQuery({ queryKey: ["project-options"], queryFn: async () => (await api.get<Options>("/projects/options")).data, enabled: open });
  const templates = useQuery({
    queryKey: ["project-templates"],
    queryFn: async () => (await api.get<Option[]>("/project-templates")).data,
    enabled: open,
  });
  const versions = useQuery({
    queryKey: ["project-template-versions", templateId],
    queryFn: async () => (await api.get<TemplateVersion[]>(`/project-templates/${templateId}/versions`)).data,
    enabled: open && Boolean(templateId),
  });
  const publishedVersions = (versions.data ?? []).filter((version) => version.published_at);
  const coverage = useQuery({
    queryKey: ["project-wizard-coverage", form.client_id, form.product_ids, form.module_ids],
    enabled: open && step === 6 && Boolean(form.client_id),
    queryFn: async () => (await api.post<{ name: string; kind: string; status: string }[]>(
      "/projects/wizard/coverage", {
        client_id: Number(form.client_id), product_ids: form.product_ids, module_ids: form.module_ids,
      },
    )).data,
  });
  const saveTemplate = useMutation({
    mutationFn: async (revise: boolean) => {
      const earliestPhase = Math.min(...phases.map((phase) => new Date(phase.planned_start_at).getTime()));
      const window = (item: { planned_start_at: string; planned_end_at: string }) => {
        const start = new Date(item.planned_start_at).getTime();
        const end = new Date(item.planned_end_at).getTime();
        return { start_offset_minutes: (start - earliestPhase) / 60_000, duration_minutes: (end - start) / 60_000 };
      };
      await api.post(revise ? `/project-templates/${sourceTemplateId}/versions` : "/project-templates", {
        ...(revise ? {} : { name: templateName.trim() }),
        publish: true,
        plan: {
          product_ids: form.product_ids,
          module_ids: form.module_ids,
          phases: resolvedPhases.map((phase) => ({
            name: phase.name, product_ids: phase.product_ids, module_ids: phase.module_ids,
            ...window(phase),
            tasks: phase.tasks.map((task) => ({
              task_number: task.task_number, title: task.title, description: task.description,
              predecessor_numbers: task.predecessor_numbers,
              product_id: Number(task.product_id),
              product_module_id: task.product_module_id ? Number(task.product_module_id) : null,
              estimate_minutes: Number(task.estimate_minutes),
              ...window(task),
            })),
          })),
        },
      });
    },
    onSuccess: async (_, revise) => {
      setSavedTemplate(revise ? "A new version of the copied template was published." : `Template “${templateName.trim()}” is ready to reuse.`);
      setTemplateName("");
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["project-templates"] });
      if (revise) await queryClient.invalidateQueries({ queryKey: ["project-template-versions", String(sourceTemplateId)] });
    },
    onError: (cause) => setError(apiErrorMessage(cause, "The template could not be saved.")),
  });
  const applyTemplate = () => {
    const version = publishedVersions.find((item) => String(item.id) === templateVersionId);
    const catalog = options.data;
    const start = new Date(templateStart).getTime();
    if (!version || !catalog || !Number.isFinite(start)) return;
    const { plan } = version;
    if (plan.product_ids.some((id) => !catalog.products.some((product) => product.id === id))
      || plan.module_ids.some((id) => !catalog.modules.some((module) =>
        module.id === id && plan.product_ids.includes(module.product_id ?? 0)))) {
      setError("This template includes products or modules unavailable in the project catalog.");
      return;
    }
    const dateAt = (offset: number) => localDateTime(start + offset * 60_000);
    const window = (item: TemplateWindow) => ({
      planned_start_at: dateAt(item.start_offset_minutes),
      planned_end_at: dateAt(item.start_offset_minutes + item.duration_minutes),
    });
    setPhases(plan.phases.map((phase) => ({
      name: phase.name, product_ids: phase.product_ids, module_ids: phase.module_ids,
      ...window(phase),
      tasks: phase.tasks.map((task) => ({
        task_number: task.task_number, title: task.title, description: task.description,
        predecessor_numbers: task.predecessor_numbers,
        product_id: String(task.product_id), product_module_id: String(task.product_module_id ?? "product-level"),
        owner_user_id: "", estimate_minutes: String(task.estimate_minutes), ...window(task),
      })),
    })));
    setForm((current) => ({
      ...current, product_ids: plan.product_ids, module_ids: plan.module_ids,
      planned_start_date: dateAt(0).slice(0, 10),
      planned_end_date: dateAt(Math.max(...plan.phases.map((phase) =>
        phase.start_offset_minutes + phase.duration_minutes))).slice(0, 10),
    }));
    setAppliedTemplate(`${templates.data?.find((item) => String(item.id) === templateId)?.name} · v${version.version_number}`);
    setSourceVersionId(version.id);
    setSourceTemplateId(Number(templateId));
    setError("");
  };
  const statuses = useQuery({ queryKey: ["client-statuses"], queryFn: async () => (await api.get<Status[]>("/client-statuses")).data, enabled: open });
  const branches = useQuery({ queryKey: ["project-wizard-branches", form.client_id], queryFn: async () => (await api.get<Branch[]>(`/clients/${form.client_id}/branches`)).data, enabled: open && Boolean(form.client_id) });
  const organizations = (options.data?.organizations ?? []).filter((item) => String(item.account_id) === String(form.account_id));
  const clients = (options.data?.clients ?? []).filter((item) => String(item.organization_id) === String(form.organization_id));
  const modules = (options.data?.modules ?? []).filter((item) => form.product_ids.includes(item.product_id ?? 0));
  const teams = (options.data?.teams ?? []).filter((item) => String(item.department_id) === String(form.requested_department_id));
  const selectedTeam = teams.find((item) => String(item.id) === String(form.requested_team_id));
  const eligibleUserIds = new Set([...(selectedTeam?.member_user_ids ?? []), ...(selectedTeam?.leader_user_id ? [selectedTeam.leader_user_id] : [])]);
  const engineers = selectedTeam ? (options.data?.managers ?? []).filter((item) => eligibleUserIds.has(item.id)) : options.data?.managers ?? [];
  const reset = () => { setExpandedProductId(null); setStep(0); setError(""); setForm({ project_number: "", name: "", description: "", account_id: "", organization_id: "", client_id: "", branch_ids: [], product_ids: [], module_ids: [], owning_department_id: "", requested_department_id: "", requested_team_id: "", project_manager_user_id: "", intake_owner_user_id: "", planned_start_date: "", planned_end_date: "", priority: "NORMAL", capability_notes: "" }); setPhases([blankPhase()]); setDocuments([]); };
  const close = () => {
    reset();
    setTemplateId("");
    setTemplateVersionId("");
    setTemplateStart("");
    setAppliedTemplate("");
    setSourceVersionId(null);
    setSourceTemplateId(null);
    setTemplateName("");
    setSavedTemplate("");
    setLoadedVersion(null);
    onClose();
  };
  const createOrganization = useMutation({ mutationFn: async () => (await api.post<Option>("/organizations", { ...organizationDraft, account_id: Number(form.account_id) })).data, onSuccess: async (item) => { await queryClient.invalidateQueries({ queryKey: ["project-options"] }); setForm((current) => ({ ...current, organization_id: String(item.id), client_id: "", branch_ids: [] })); setOrganizationDraft({ code: "", name: "" }); } });
  const createClient = useMutation({ mutationFn: async () => (await api.post<Option>("/clients", { name: clientDraft, status_id: statuses.data?.find((item) => item.is_active)?.id ?? statuses.data?.[0]?.id, organization_id: Number(form.organization_id) })).data, onSuccess: async (item) => { await queryClient.invalidateQueries({ queryKey: ["project-options"] }); setForm((current) => ({ ...current, client_id: String(item.id), branch_ids: [] })); setClientDraft(""); } });
  const createBranch = useMutation({
    mutationFn: async ({ clientId, name }: { clientId: string; name: string }) =>
      (await api.post<Branch>(`/clients/${clientId}/branches`, { name })).data,
    onSuccess: async (item, { clientId }) => {
      await queryClient.invalidateQueries({ queryKey: ["project-wizard-branches", clientId] });
      setForm((current) => current.client_id === clientId
        ? { ...current, branch_ids: [...current.branch_ids, item.id] }
        : current);
      setBranchDraft((current) => current.trim() === item.name ? "" : current);
    },
  });
  const taskScope = (phase: PhaseDraft, task: TaskDraft) => {
    const productId = phase.product_ids.includes(Number(task.product_id))
      ? String(task.product_id)
      : phase.product_ids.length === 1 ? String(phase.product_ids[0]) : "";
    const availableModules = modules.filter((item) => item.product_id === Number(productId));
    const phaseModules = availableModules.filter((item) => phase.module_ids.includes(item.id));
    const moduleId = task.product_module_id === "product-level"
      ? ""
      : phaseModules.some((item) => item.id === Number(task.product_module_id))
        ? String(task.product_module_id)
        : phaseModules.length === 1 ? String(phaseModules[0].id) : "";
    return { productId, moduleId, availableModules };
  };
  const resolvedPhases = phases.map((phase) => ({
    ...phase,
    tasks: phase.tasks.map((task) => {
      const { productId, moduleId } = taskScope(phase, task);
      return { ...task, product_id: productId, product_module_id: moduleId };
    }),
  }));
  const templateReady = form.product_ids.length > 0 && resolvedPhases.length > 0
    && resolvedPhases.every((phase) =>
      phase.name.trim() && phase.product_ids.length > 0
      && phase.product_ids.every((id) => form.product_ids.includes(id))
      && phase.module_ids.every((id) => form.module_ids.includes(id))
      && phase.planned_start_at && phase.planned_end_at > phase.planned_start_at
      && phase.tasks.length > 0 && phase.tasks.every((task) =>
        task.title.trim() && task.product_id && task.planned_start_at
        && task.planned_start_at >= phase.planned_start_at
        && task.planned_end_at > task.planned_start_at && task.planned_end_at <= phase.planned_end_at));
  const payload = (publish: boolean) => ({ ...form, source_template_version_id: sourceVersionId, account_id: Number(form.account_id), organization_id: Number(form.organization_id), client_id: Number(form.client_id), owning_department_id: Number(form.owning_department_id), requested_department_id: Number(form.requested_department_id), requested_team_id: form.requested_team_id ? Number(form.requested_team_id) : null, project_manager_user_id: Number(form.project_manager_user_id), intake_owner_user_id: form.intake_owner_user_id ? Number(form.intake_owner_user_id) : null, phases: resolvedPhases.map((phase) => ({ ...phase, planned_start_at: iso(phase.planned_start_at), planned_end_at: iso(phase.planned_end_at), tasks: phase.tasks.map((task) => ({ ...task, product_id: Number(task.product_id), product_module_id: task.product_module_id ? Number(task.product_module_id) : null, owner_user_id: Number(task.owner_user_id), assignee_user_ids: [Number(task.owner_user_id)], planned_start_at: iso(task.planned_start_at), planned_end_at: iso(task.planned_end_at), estimate_minutes: Number(task.estimate_minutes) })) })), documents, publish });
  const submit = useMutation({ mutationFn: async (publish: boolean) => (await api.post("/projects/wizard", {
    ...payload(publish), checkpoint_version: loadedVersion,
  })).data, onSuccess: () => {
    if (loadedVersion !== null) queryClient.setQueryData(checkpointKey, null);
    close();
    onCreated();
  }, onError: (cause) => setError(apiErrorMessage(cause, "The project wizard could not be saved.")) });

  const saveCheckpoint = useMutation({
    mutationFn: async () => {
      const saved: Checkpoint = { step, form, phases, documents, sourceVersionId, sourceTemplateId, appliedTemplate };
      const result = await api.put<{ version: number }>("/projects/wizard-draft", {
        expected_version: loadedVersion ?? 0, checkpoint: saved,
      });
      return { version: result.data.version, checkpoint: saved };
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(checkpointKey, saved);
      close();
    },
    onError: (cause) => setError(apiErrorMessage(cause, "Unable to save the draft.")),
  });

  function resumeCheckpoint() {
    if (!checkpoint || !savedDraft.data) return;
    if (!Number.isInteger(checkpoint.step) || checkpoint.step < 0 || checkpoint.step >= steps.length
      || !checkpoint.form || !Array.isArray(checkpoint.phases) || !Array.isArray(checkpoint.documents)) {
      setError("The saved draft could not be restored.");
      return;
    }
    setForm(checkpoint.form);
    setPhases(checkpoint.phases);
    setDocuments(checkpoint.documents);
    setSourceVersionId(checkpoint.sourceVersionId);
    setSourceTemplateId(checkpoint.sourceTemplateId ?? null);
    setAppliedTemplate(checkpoint.appliedTemplate);
    setStep(checkpoint.step);
    setLoadedVersion(savedDraft.data.version);
    setError("");
  }

  const discardCheckpoint = useMutation({
    mutationFn: (version: number) => api.delete("/projects/wizard-draft", { params: { expected_version: version } }),
    onSuccess: () => { queryClient.setQueryData(checkpointKey, null); setLoadedVersion(null); },
    onError: (cause) => setError(apiErrorMessage(cause, "Unable to discard the draft.")),
  });
  const updatePhase = (index: number, patch: Partial<PhaseDraft>) => setPhases((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  const updateTask = (phaseIndex: number, taskIndex: number, patch: Partial<TaskDraft>) => setPhases((current) => current.map((phase, index) => index === phaseIndex ? { ...phase, tasks: phase.tasks.map((task, inner) => inner === taskIndex ? { ...task, ...patch } : task) } : phase));
  const tasks = resolvedPhases.flatMap((phase) => phase.tasks);
  const numbers = tasks.map((task) => task.task_number.trim().toUpperCase());
  const manualNumbers = numbers.filter(Boolean);
  const taskByNumber = new Map(tasks.map((task, index) => [numbers[index], task] as const).filter(([number]) => number));
  const checks = [
    { ready: Boolean(form.account_id && form.organization_id && form.client_id), help: "Select the account, organization, and client." },
    { ready: form.product_ids.length > 0, help: "Select at least one product for delivery." },
    { ready: Boolean(form.owning_department_id && form.requested_department_id && form.project_manager_user_id && (!form.requested_team_id || form.intake_owner_user_id)),
      help: "Select the owning and delivery departments and project manager. A named team also requires an intake owner." },
    { ready: Boolean(form.name.trim() && form.planned_start_date && form.planned_end_date && form.planned_end_date >= form.planned_start_date),
      help: "Enter a project name and ordered delivery dates." },
    {
      ready: phases.length > 0 && new Set(manualNumbers).size === manualNumbers.length && resolvedPhases.every((phase) =>
        Boolean(phase.name.trim() && phase.planned_start_at && phase.planned_end_at
          && phase.planned_end_at >= phase.planned_start_at && phase.product_ids.length
          && phase.product_ids.every((id) => form.product_ids.includes(id))
          && phase.module_ids.every((id) => form.module_ids.includes(id)) && phase.tasks.length)
        && phase.tasks.every((task) => Boolean(
          task.title.trim() && task.owner_user_id && task.planned_start_at && task.planned_end_at
          && task.planned_start_at >= phase.planned_start_at && task.planned_end_at <= phase.planned_end_at
          && task.planned_end_at >= task.planned_start_at && phase.product_ids.includes(Number(task.product_id))
          && (!task.product_module_id || phase.module_ids.includes(Number(task.product_module_id)))
          && (task.predecessor_numbers ?? []).every((number) => {
            const predecessor = taskByNumber.get(number.trim().toUpperCase());
            return predecessor && predecessor !== task && predecessor.planned_end_at <= task.planned_start_at;
          }),
        ))),
      help: "Check phase dates and scope, unique task numbers, assignees, and predecessor timing.",
    },
    { ready: documents.every((document) => document.title.trim().length >= 2 && document.document_type.trim().length >= 2),
      help: "Complete or remove each document entry. An empty document list is allowed." },
  ];
  const readyToSubmit = checks.every((check) => check.ready);
  const stepValid = step === steps.length - 1 ? readyToSubmit : Boolean(checks[step]?.ready);

  return <Dialog open={open} onClose={close} fullScreen><DialogTitle sx={{ pb: 1 }}><Typography component="span" display="block" variant="h5" fontWeight={900}>New Project Setup</Typography><Typography component="span" display="block" variant="body2" color="text.secondary">Build the complete governed delivery plan, save it privately, or publish it to Implementation intake.</Typography></DialogTitle><Divider/><DialogContent sx={{ p: { xs: 1.5, md: 3 } }}>
    <Stepper activeStep={step} alternativeLabel sx={{ mb: 3 }}>{steps.map((label) => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}</Stepper>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {savedDraft.isError && <Alert severity="warning" sx={{ mb: 2 }}>Saved draft could not be loaded. <Button onClick={() => savedDraft.refetch()}>Retry</Button></Alert>}
    {step === steps.length - 1 && (
      <Paper variant="outlined" sx={{ p: 2, mb: 2, mx: "auto", maxWidth: 1000 }}>
        <Typography component="h2" variant="h6" gutterBottom>Publish readiness</Typography>
        <Stack spacing={1}>
          {checks.map((check, index) => (
            <Stack key={steps[index]} direction={{ xs: "column", sm: "row" }} gap={1} alignItems={{ sm: "center" }}
              sx={{ borderTop: 1, borderColor: "divider", pt: 1 }}>
              <Chip size="small" color={check.ready ? "success" : "warning"} label={check.ready ? "Ready" : "Needs attention"} />
              <Box sx={{ flex: 1 }}>
                <Typography fontWeight={700}>{steps[index]}</Typography>
                {!check.ready && <Typography variant="body2" color="text.secondary">{check.help}</Typography>}
              </Box>
              <Button size="small" onClick={() => setStep(index)} aria-label={`Review ${steps[index]}`}>Review</Button>
            </Stack>
          ))}
        </Stack>
      </Paper>
    )}
    {step === 0 && checkpoint && (
      <Alert severity="info" sx={{ mb: 2 }} action={<Stack direction="row" flexWrap="wrap">
        <Button onClick={resumeCheckpoint}>Resume draft</Button>
        <Button disabled={discardCheckpoint.isPending} onClick={() => {
          if (savedDraft.data) discardCheckpoint.mutate(savedDraft.data.version);
        }}>Discard saved draft</Button>
      </Stack>}>
        An unfinished draft is saved to your account.
      </Alert>
    )}
    {step === 6 && (
      <Paper variant="outlined" sx={{ p: 2, mb: 2, mx: "auto", maxWidth: 1000 }}>
        <Typography variant="h6">Customer contract coverage</Typography>
        <Typography variant="body2" color="text.secondary">
          Check existing coverage before publishing. New deployments can include products outside the current support contract.
        </Typography>
        {coverage.isFetching && <Typography>Checking coverage…</Typography>}
        {coverage.isError && <Alert severity="warning">Customer coverage could not be checked.</Alert>}
        {coverage.data?.map((item, index) => (
          <Typography key={index} variant="body2">
            {item.kind} · {item.name} · {item.status.replaceAll("_", " ")}
          </Typography>
        ))}
      </Paper>
    )}
    {step === 0 && <Paper variant="outlined" sx={{ p: 2, mb: 2, mx: "auto", maxWidth: 900 }}>
      <Stack gap={2}>
        <Typography variant="h6">Project starting point</Typography>
          <TextField select label="Project template" value={templates.data?.some((item) => String(item.id) === templateId) ? templateId : ""} onChange={(event) => {
          setTemplateId(event.target.value);
          setTemplateVersionId("");
        }}>
          <MenuItem value="">Start blank</MenuItem>
          {templates.data?.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.name}</MenuItem>)}
        </TextField>
        {(templates.isError || versions.isError) && <Alert severity="warning">Templates could not be loaded.</Alert>}
        {templateId && <>
          <TextField select label="Published version" value={publishedVersions.some((version) => String(version.id) === templateVersionId) ? templateVersionId : ""}
            onChange={(event) => setTemplateVersionId(event.target.value)}>
            <MenuItem value="">{versions.isPending ? "Loading versions…" : "Select a version"}</MenuItem>
            {publishedVersions.map((version) => <MenuItem key={version.id} value={String(version.id)}>Version {version.version_number}</MenuItem>)}
          </TextField>
          <TextField type="datetime-local" label="Template schedule start" InputLabelProps={{ shrink: true }}
            value={templateStart} onChange={(event) => setTemplateStart(event.target.value)} />
          <Button variant="outlined" disabled={!templateVersionId || !templateStart || !options.data}
            onClick={applyTemplate}>{appliedTemplate ? "Replace copied plan" : "Copy template plan"}</Button>
        </>}
        {appliedTemplate && <Alert severity="info" action={<Button color="inherit" onClick={() => {
          setAppliedTemplate("");
          setSourceVersionId(null);
          setSourceTemplateId(null);
          setTemplateId("");
          setTemplateVersionId("");
          setTemplateStart("");
          setError("");
          setPhases([blankPhase()]);
          setForm((current) => ({
            ...current, product_ids: [], module_ids: [], planned_start_date: "", planned_end_date: "",
          }));
        }}>Clear copied plan</Button>}>
          Copied {appliedTemplate}. Confirm the project’s dates and choose a task engineer for each task.
        </Alert>}
      </Stack>
    </Paper>}
    {step === 0 && <Stack gap={2} maxWidth={900} mx="auto"><Typography variant="h6" fontWeight={800}>Customer scope</Typography><TextField select label="Account" value={form.account_id} onChange={(event) => setForm({ ...form, account_id: String(event.target.value), organization_id: "", client_id: "", branch_ids: [] })}>{options.data?.accounts.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.name}</MenuItem>)}</TextField><TextField select label="Organization" value={form.organization_id} onChange={(event) => setForm({ ...form, organization_id: String(event.target.value), client_id: "", branch_ids: [] })}>{organizations.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.name}</MenuItem>)}</TextField><Paper variant="outlined" sx={{ p: 1.5 }}><Typography fontWeight={700}>Create organization</Typography><Stack direction={{ xs: "column", sm: "row" }} gap={1} mt={1}><TextField label="Code" value={organizationDraft.code} onChange={(event) => setOrganizationDraft({ ...organizationDraft, code: event.target.value })}/><TextField fullWidth label="Name" value={organizationDraft.name} onChange={(event) => setOrganizationDraft({ ...organizationDraft, name: event.target.value })}/><Button disabled={!form.account_id || !organizationDraft.code || !organizationDraft.name || createOrganization.isPending} onClick={() => createOrganization.mutate()}>Create</Button></Stack></Paper><TextField select label="Client" value={form.client_id} onChange={(event) => setForm({ ...form, client_id: String(event.target.value), branch_ids: [] })}>{clients.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.name}</MenuItem>)}</TextField><Paper variant="outlined" sx={{ p: 1.5 }}><Stack direction={{ xs: "column", sm: "row" }} gap={1}><TextField fullWidth label="New client name" value={clientDraft} onChange={(event) => setClientDraft(event.target.value)}/><Button disabled={!form.organization_id || !clientDraft || createClient.isPending} onClick={() => createClient.mutate()}>Add client</Button></Stack></Paper>{form.client_id && <><Typography fontWeight={700}>Branches (optional)</Typography><Stack direction="row" flexWrap="wrap">{branches.data?.map((item) => <FormControlLabel key={item.id} control={<Checkbox checked={form.branch_ids.includes(item.id)} onChange={() => setForm({ ...form, branch_ids: toggle(form.branch_ids, item.id) })}/>} label={item.name}/>)}</Stack><Stack direction={{ xs: "column", sm: "row" }} gap={1}><TextField fullWidth label="New branch name" value={branchDraft} onChange={(event) => setBranchDraft(event.target.value)}/><Button disabled={branchDraft.trim().length < 2 || createBranch.isPending} onClick={() => createBranch.mutate({ clientId: form.client_id, name: branchDraft.trim() })}>Add branch</Button></Stack>{createBranch.isError && createBranch.variables?.clientId === form.client_id && <Alert severity="error">{apiErrorMessage(createBranch.error, "The branch could not be added.")}</Alert>}</>}</Stack>}
    {step === 1 && <Stack gap={2} maxWidth={1000} mx="auto">
      <Typography variant="h6" fontWeight={800}>Products and modules</Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" }, gap: 1.5, alignItems: "start" }}>
        {options.data?.products.map((product) => {
          const productModules = options.data.modules.filter((module) => module.product_id === product.id);
          const moduleIds = productModules.map((module) => module.id);
          const selectedCount = moduleIds.filter((id) => form.module_ids.includes(id)).length;
          const included = form.product_ids.includes(product.id);
          const expanded = expandedProductId === product.id;
          const panelId = `wizard-product-modules-${product.id}`;
          const setProductModules = (ids: number[]) => setForm((current) => ({
            ...current,
            module_ids: [...current.module_ids.filter((id) => !moduleIds.includes(id)), ...ids],
          }));
          return <Paper key={product.id} variant="outlined" sx={{
            position: "relative", overflow: "hidden", borderRadius: 2,
            borderColor: included ? "primary.main" : "divider",
            "&::before": {
              content: '""', position: "absolute", insetBlock: 8, left: 0, width: 4,
              borderRadius: 2, bgcolor: "primary.main", opacity: included ? 0.9 : 0.35,
              filter: "blur(1px)", pointerEvents: "none", zIndex: 1,
            },
          }}>
            <CardActionArea
              aria-expanded={expanded}
              aria-controls={panelId}
              sx={{ px: 2.5, py: 1.75, textAlign: "left", bgcolor: included ? "action.selected" : undefined }}
              onClick={() => {
                setExpandedProductId(expanded ? null : product.id);
                if (!included) setForm((current) => ({
                  ...current,
                  product_ids: [...current.product_ids, product.id],
                  module_ids: [...new Set([...current.module_ids, ...moduleIds])],
                }));
              }}
            >
              <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
                <Box>
                  <Typography fontWeight={800}>{product.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {!included && `${moduleIds.length} ${moduleIds.length === 1 ? "module" : "modules"} available`}
                    {included && (moduleIds.length ? `${selectedCount} of ${moduleIds.length} modules selected` : "Product selected")}
                  </Typography>
                </Box>
                <ExpandMore color="action" sx={{ transform: expanded ? "rotate(180deg)" : undefined }} />
              </Stack>
            </CardActionArea>
            <Box id={panelId} hidden={!expanded}>
              {expanded && <Stack gap={1} px={2.5} py={1.5}>
                {productModules.length > 0 && <>
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    <Button size="small" disabled={selectedCount === moduleIds.length} onClick={() => setProductModules(moduleIds)}>Select all</Button>
                    <Button size="small" disabled={selectedCount === 0} onClick={() => setProductModules([])}>Clear selection</Button>
                  </Stack>
                  <Stack role="group" aria-label={`${product.name} modules`}>
                    {productModules.map((module) => <FormControlLabel key={module.id} label={module.name} control={
                      <Checkbox checked={form.module_ids.includes(module.id)} onChange={() => setForm((current) => ({
                        ...current, module_ids: toggle(current.module_ids, module.id),
                      }))} />
                    } />)}
                  </Stack>
                </>}
                <Button size="small" color="error" sx={{ alignSelf: "flex-start" }} onClick={() => {
                  setExpandedProductId(null);
                  setForm((current) => ({
                    ...current,
                    product_ids: current.product_ids.filter((id) => id !== product.id),
                    module_ids: current.module_ids.filter((id) => !moduleIds.includes(id)),
                  }));
                }}>Remove product</Button>
              </Stack>}
            </Box>
          </Paper>;
        })}
      </Box>
    </Stack>}
    {step === 2 && <Stack gap={2} maxWidth={900} mx="auto"><Typography variant="h6" fontWeight={800}>Ownership and delivery intake</Typography><TextField select label="Project Management department" value={form.owning_department_id} onChange={(event) => setForm({ ...form, owning_department_id: event.target.value })}>{options.data?.departments.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField select label="Project Manager" value={form.project_manager_user_id} onChange={(event) => setForm({ ...form, project_manager_user_id: event.target.value })}>{options.data?.managers.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField select label="Requested delivery department" value={form.requested_department_id} onChange={(event) => setForm({ ...form, requested_department_id: event.target.value, requested_team_id: "", intake_owner_user_id: "" })}>{options.data?.departments.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField select label="Delivery routing" disabled={!form.requested_department_id} value={form.requested_team_id || "department-queue"} onChange={(event) => setForm({ ...form, requested_team_id: event.target.value === "department-queue" ? "" : event.target.value, intake_owner_user_id: "" })}><MenuItem value="department-queue">Department intake queue</MenuItem>{teams.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField select label={form.requested_team_id ? "Intake engineer / team leader" : "Intake engineer (optional)"} value={form.intake_owner_user_id} onChange={(event) => setForm({ ...form, intake_owner_user_id: event.target.value })}>{!form.requested_team_id && <MenuItem value="">No named intake owner</MenuItem>}{engineers.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField multiline minRows={3} label="Capability and resource notes" value={form.capability_notes} onChange={(event) => setForm({ ...form, capability_notes: event.target.value })}/></Stack>}
    {step === 3 && <Stack gap={2} maxWidth={900} mx="auto"><Typography variant="h6" fontWeight={800}>Project identity and schedule</Typography><Stack direction={{ xs: "column", sm: "row" }} gap={1}><TextField fullWidth label="Project number" helperText="Leave blank to assign a year-based serial on save." inputProps={{ maxLength: 50 }} value={form.project_number} onChange={(event) => setForm({ ...form, project_number: event.target.value })}/><TextField fullWidth label="Project name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })}/></Stack><TextField multiline minRows={3} label="Description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })}/><Stack direction={{ xs: "column", sm: "row" }} gap={1}><TextField fullWidth type="date" label="Start date" InputLabelProps={{ shrink: true }} value={form.planned_start_date} onChange={(event) => setForm({ ...form, planned_start_date: event.target.value })}/><TextField fullWidth type="date" label="End date" InputLabelProps={{ shrink: true }} value={form.planned_end_date} onChange={(event) => setForm({ ...form, planned_end_date: event.target.value })}/><TextField select fullWidth label="Priority" value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })}>{["LOW", "NORMAL", "HIGH", "CRITICAL"].map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}</TextField></Stack></Stack>}
    {step === 4 && <Stack gap={2} maxWidth={1200} mx="auto"><Stack direction="row" justifyContent="space-between"><Box><Typography variant="h6" fontWeight={800}>Phases and scheduled tasks</Typography><Typography variant="body2" color="text.secondary">Every task is tied to a phase, product and optional module.</Typography></Box><Button startIcon={<Add/>} onClick={() => setPhases([...phases, blankPhase()])}>Add phase</Button></Stack>{phases.map((phase, phaseIndex) => <Paper key={phaseIndex} variant="outlined" sx={{ p: 2 }}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={900}>Phase {phaseIndex + 1}</Typography>{phases.length > 1 && <Button color="error" startIcon={<DeleteOutline/>} onClick={() => setPhases(phases.filter((_, index) => index !== phaseIndex))}>Remove</Button>}</Stack><Stack gap={1.25} mt={1}><TextField label="Phase name" value={phase.name} onChange={(event) => updatePhase(phaseIndex, { name: event.target.value })}/><Stack direction={{ xs: "column", sm: "row" }} gap={1}><TextField fullWidth type="datetime-local" label="Phase start" InputLabelProps={{ shrink: true }} value={phase.planned_start_at} onChange={(event) => updatePhase(phaseIndex, { planned_start_at: event.target.value })}/><TextField fullWidth type="datetime-local" label="Phase end" InputLabelProps={{ shrink: true }} value={phase.planned_end_at} onChange={(event) => updatePhase(phaseIndex, { planned_end_at: event.target.value })}/></Stack><Typography variant="subtitle2">Phase products and modules</Typography><Stack direction="row" flexWrap="wrap">{options.data?.products.filter((item) => form.product_ids.includes(item.id)).map((item) => <FormControlLabel key={item.id} control={<Checkbox checked={phase.product_ids.includes(item.id)} onChange={() => {
      const productIds = toggle(phase.product_ids, item.id);
      const productModules = modules.filter((module) => module.product_id === item.id).map((module) => module.id);
      updatePhase(phaseIndex, {
        product_ids: productIds,
        module_ids: productIds.includes(item.id)
          ? [...new Set([...phase.module_ids, ...productModules])]
          : phase.module_ids.filter((id) => !productModules.includes(id)),
      });
    }}/>} label={item.name}/>)}</Stack><Stack direction="row" flexWrap="wrap">{modules.filter((item) => phase.product_ids.includes(item.product_id ?? 0)).map((item) => <FormControlLabel key={item.id} control={<Checkbox checked={phase.module_ids.includes(item.id)} onChange={() => updatePhase(phaseIndex, { module_ids: toggle(phase.module_ids, item.id) })}/>} label={item.name}/>)}</Stack><Divider/><Stack direction="row" justifyContent="space-between"><Typography fontWeight={800}>Tasks</Typography><Button size="small" startIcon={<Add/>} onClick={() => updatePhase(phaseIndex, { tasks: [...phase.tasks, blankTask()] })}>Add task</Button></Stack>{phase.tasks.map((task, taskIndex) => { const { productId, moduleId, availableModules } = taskScope(phase, task); return <Paper key={taskIndex} sx={{ p: 1.5, bgcolor: "action.hover" }}><Stack direction="row" justifyContent="space-between"><Typography variant="subtitle2">Task {taskIndex + 1}</Typography>{phase.tasks.length > 1 && <Button size="small" color="error" onClick={() => updatePhase(phaseIndex, { tasks: phase.tasks.filter((_, index) => index !== taskIndex) })}>Remove</Button>}</Stack><Stack gap={1} mt={1}><Stack direction={{ xs: "column", md: "row" }} gap={1}><TextField label="Task number" placeholder="Automatic" InputLabelProps={{ shrink: true }} inputProps={{ maxLength: 50 }} value={task.task_number} onChange={(event) => updateTask(phaseIndex, taskIndex, { task_number: event.target.value })}/><TextField fullWidth label="Task title" value={task.title} onChange={(event) => updateTask(phaseIndex, taskIndex, { title: event.target.value })}/></Stack><TextField fullWidth label="Task description" value={task.description ?? ""} onChange={(event) => updateTask(phaseIndex, taskIndex, { description: event.target.value })}/><Stack direction={{ xs: "column", md: "row" }} gap={1}><TextField select fullWidth label="Product" value={productId} onChange={(event) => updateTask(phaseIndex, taskIndex, { product_id: String(event.target.value), product_module_id: "" })}>{options.data?.products.filter((item) => phase.product_ids.includes(item.id)).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField select fullWidth label="Module (optional)" disabled={!productId} value={moduleId || "product-level"} onChange={(event) => {
      const selected = String(event.target.value);
      const selectedId = Number(selected);
      updatePhase(phaseIndex, {
        module_ids: selected === "product-level" ? phase.module_ids : [...new Set([...phase.module_ids, selectedId])],
        tasks: phase.tasks.map((item, index) => index === taskIndex ? { ...item, product_module_id: selected } : item),
      });
    }}><MenuItem value="product-level">Product-level task</MenuItem>{availableModules.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.name}</MenuItem>)}</TextField><TextField select fullWidth label="Engineer" value={task.owner_user_id} onChange={(event) => updateTask(phaseIndex, taskIndex, { owner_user_id: event.target.value })}>{engineers.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField></Stack><Stack direction={{ xs: "column", md: "row" }} gap={1}><TextField fullWidth type="datetime-local" label="Task start" InputLabelProps={{ shrink: true }} value={task.planned_start_at} onChange={(event) => updateTask(phaseIndex, taskIndex, { planned_start_at: event.target.value })}/><TextField fullWidth type="datetime-local" label="Task end" InputLabelProps={{ shrink: true }} value={task.planned_end_at} onChange={(event) => updateTask(phaseIndex, taskIndex, { planned_end_at: event.target.value })}/><TextField fullWidth type="number" label="Estimate (minutes)" value={task.estimate_minutes} onChange={(event) => updateTask(phaseIndex, taskIndex, { estimate_minutes: event.target.value })}/></Stack></Stack></Paper>; })}</Stack></Paper>)}</Stack>}
    {step === 5 && <Stack gap={2} maxWidth={900} mx="auto"><Stack direction="row" justifyContent="space-between"><Box><Typography variant="h6" fontWeight={800}>Documents and evidence</Typography><Typography variant="body2" color="text.secondary">Add governed document references. Direct binary upload will continue through the secured evidence storage workflow.</Typography></Box><Button startIcon={<Add/>} onClick={() => setDocuments([...documents, { title: "", document_type: "SCOPE", reference_url: "", notes: "" }])}>Add document</Button></Stack>{documents.map((document, index) => <Paper key={index} variant="outlined" sx={{ p: 1.5 }}><Stack gap={1}><Stack direction={{ xs: "column", sm: "row" }} gap={1}><TextField fullWidth label="Title" value={document.title} onChange={(event) => setDocuments(documents.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.target.value } : item))}/><TextField select label="Type" value={document.document_type} onChange={(event) => setDocuments(documents.map((item, itemIndex) => itemIndex === index ? { ...item, document_type: event.target.value } : item))}>{["SCOPE", "PURCHASE_ORDER", "SITE_SURVEY", "TECHNICAL_DESIGN", "PROJECT_PLAN", "MEETING_MINUTES", "OTHER"].map((item) => <MenuItem key={item} value={item}>{item.replaceAll("_", " ")}</MenuItem>)}</TextField></Stack><TextField label="Reference URL or document location" value={document.reference_url} onChange={(event) => setDocuments(documents.map((item, itemIndex) => itemIndex === index ? { ...item, reference_url: event.target.value } : item))}/><TextField multiline label="Notes" value={document.notes} onChange={(event) => setDocuments(documents.map((item, itemIndex) => itemIndex === index ? { ...item, notes: event.target.value } : item))}/><Button color="error" onClick={() => setDocuments(documents.filter((_, itemIndex) => itemIndex !== index))}>Remove</Button></Stack></Paper>)}{!documents.length && <Alert severity="info">Documents are optional for Draft. Required handover evidence remains enforced before Support activation.</Alert>}</Stack>}
    {step === 6 && <Stack gap={2} maxWidth={1000} mx="auto"><Typography variant="h6" fontWeight={800}>Review and publish</Typography><Alert severity="info">Save Draft keeps this project private to authorized Project Management users. Publish creates the Implementation assignment request and exposes the intake to the requested department.</Alert><Paper variant="outlined" sx={{ p: 2 }}><Typography fontWeight={900}>{form.project_number.trim() || "Automatic project number"} · {form.name}</Typography><Typography color="text.secondary">{options.data?.organizations.find((item) => String(item.id) === form.organization_id)?.name} → {options.data?.clients.find((item) => String(item.id) === form.client_id)?.name}</Typography><Stack direction="row" flexWrap="wrap" gap={1} mt={1}><Chip label={`${form.product_ids.length} products`}/><Chip label={`${form.module_ids.length} modules`}/><Chip label={`${phases.length} phases`}/><Chip label={`${phases.reduce((sum, phase) => sum + phase.tasks.length, 0)} tasks`}/><Chip label={`${documents.length} documents`}/></Stack></Paper>{phases.map((phase, index) => <Paper key={index} variant="outlined" sx={{ p: 1.5 }}><Typography fontWeight={800}>{index + 1}. {phase.name}</Typography><Typography variant="body2" color="text.secondary">{phase.planned_start_at} → {phase.planned_end_at} · {phase.tasks.length} tasks</Typography></Paper>)}</Stack>}
  </DialogContent><Divider/><DialogActions sx={{ px: 3, py: 1.5, flexWrap: "wrap" }}><Button onClick={close}>Cancel</Button>{user && <Button startIcon={<Save />} disabled={submit.isPending || saveCheckpoint.isPending || !savedDraft.isSuccess || (Boolean(checkpoint) && loadedVersion === null)} onClick={() => saveCheckpoint.mutate()}>Save and exit</Button>}{step >= 4 && <Button startIcon={<Save />} disabled={submit.isPending} onClick={() => { saveTemplate.reset(); setSavedTemplate(""); setTemplateDialogOpen(true); }}>Save as template</Button>}<Box flex={1}/>{step > 0 && <Button onClick={() => setStep(step - 1)}>Back</Button>}{step < steps.length - 1 ? <Button variant="contained" disabled={!stepValid} onClick={() => setStep(step + 1)}>Next</Button> : <><Button startIcon={<Save/>} disabled={submit.isPending || !readyToSubmit} onClick={() => submit.mutate(false)}>Save Draft</Button><Button variant="contained" startIcon={<Publish/>} disabled={submit.isPending || !stepValid} onClick={() => submit.mutate(true)}>Publish to Implementation</Button></>}</DialogActions>
    <Dialog open={templateDialogOpen} fullWidth maxWidth="sm" onClose={() => !saveTemplate.isPending && setTemplateDialogOpen(false)}>
      <DialogTitle>Save as template</DialogTitle>
      <DialogContent>
        <Stack gap={2} mt={1}>
          <Typography variant="body2" color="text.secondary">
            Save products, modules, phases, and default implementation tasks for use in another project.
          </Typography>
          {!templateReady && <Alert severity="info">Complete your product selection and add named phases and tasks with valid dates.</Alert>}
          {saveTemplate.isError && <Alert severity="error">{apiErrorMessage(saveTemplate.error)}</Alert>}
          {savedTemplate && <Alert severity="success">{savedTemplate}</Alert>}
          <TextField autoFocus fullWidth label="Template name" value={templateName} inputProps={{ maxLength: 200 }}
            onChange={(event) => setTemplateName(event.target.value)} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button disabled={saveTemplate.isPending} onClick={() => setTemplateDialogOpen(false)}>Close</Button>
        {sourceTemplateId !== null && <Button disabled={!templateReady || saveTemplate.isPending || Boolean(savedTemplate)}
          onClick={() => saveTemplate.mutate(true)}>Publish new version</Button>}
        <Button variant="contained" disabled={!templateReady || !templateName.trim() || saveTemplate.isPending || Boolean(savedTemplate)}
          onClick={() => saveTemplate.mutate(false)}>Save template</Button>
      </DialogActions>
    </Dialog>
  </Dialog>;
}
