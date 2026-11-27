import { Add, EditOutlined } from "@mui/icons-material";
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { ProjectCreationWizard } from "../components/ProjectCreationWizard";

type Template = { id: number; name: string };
type Task = {
  task_number: string; title: string; description: string | null; product_id: number;
  product_module_id: number | null; start_offset_minutes: number; duration_minutes: number;
  estimate_minutes: number; predecessor_numbers: string[];
};
type TaskDraft = Task & { predecessorText?: string };
type Phase = { name: string; product_ids: number[]; module_ids: number[]; start_offset_minutes: number; duration_minutes: number; tasks: TaskDraft[] };
type Plan = { product_ids: number[]; module_ids: number[]; phases: Phase[] };
type Version = { id: number; template_id: number; version_number: number; published_at: string | null; plan: Plan };
type Catalog = { products: Template[]; modules: (Template & { product_id: number })[] };
const unique = (ids: number[]) => [...new Set(ids)];
const blankTask = (): Task => ({
  task_number: "", title: "", description: null, product_id: 0, product_module_id: null,
  start_offset_minutes: 0, duration_minutes: 60, estimate_minutes: 60, predecessor_numbers: [],
});
const blankPhase = (): Phase => ({ name: "", product_ids: [], module_ids: [], start_offset_minutes: 0, duration_minutes: 480, tasks: [blankTask()] });

function TemplateEditor({ template, version, onClose, onSaved }: {
  template?: Template; version?: Version; onClose: () => void; onSaved: (version: Version) => void;
}) {
  const [name, setName] = useState(template?.name ?? "");
  const [phases, setPhases] = useState(() => version?.plan.phases ?? [blankPhase()]);
  const catalog = useQuery({
    queryKey: ["project-options"],
    queryFn: async () => (await api.get<Catalog>("/projects/options")).data,
  });
  const save = useMutation({
    mutationFn: async (publish: boolean) => {
      const scopedPhases = phases.map((phase) => ({
        ...phase, name: phase.name.trim(),
        tasks: phase.tasks.map(({ predecessorText, ...task }) => ({
          ...task, title: task.title.trim(),
          predecessor_numbers: predecessorText === undefined ? task.predecessor_numbers
            : predecessorText.split(",").map((value) => value.trim()).filter(Boolean),
        })),
        product_ids: unique([...phase.product_ids, ...phase.tasks.map((task) => task.product_id)]),
        module_ids: unique([...phase.module_ids, ...phase.tasks.flatMap((task) => task.product_module_id ? [task.product_module_id] : [])]),
      }));
      const plan = {
        product_ids: unique([...(version?.plan.product_ids ?? []), ...scopedPhases.flatMap((phase) => phase.product_ids)]),
        module_ids: unique([...(version?.plan.module_ids ?? []), ...scopedPhases.flatMap((phase) => phase.module_ids)]),
        phases: scopedPhases,
      };
      const path = template ? `/project-templates/${template.id}/versions` : "/project-templates";
      return (await api.post<Version>(path, { name: name.trim(), plan, publish })).data;
    },
    onSuccess: onSaved,
  });
  const updatePhase = (index: number, changes: Partial<Phase>) =>
    setPhases((current) => current.map((phase, item) => item === index ? { ...phase, ...changes } : phase));
  const valid = name.trim() && Boolean(catalog.data) && phases.every((phase) =>
    phase.name.trim() && phase.duration_minutes > 0 && phase.tasks.every((task) =>
      task.title.trim() && catalog.data?.products.some((product) => product.id === task.product_id)
      && (!task.product_module_id || catalog.data?.modules.some((module) => module.id === task.product_module_id && module.product_id === task.product_id))
      && task.duration_minutes > 0 && task.start_offset_minutes >= phase.start_offset_minutes
      && task.start_offset_minutes + task.duration_minutes <= phase.start_offset_minutes + phase.duration_minutes));
  return <Dialog open fullWidth maxWidth="lg" onClose={() => !save.isPending && onClose()}>
    <DialogTitle>{template ? `Edit template · ${template.name}` : "New project template"}</DialogTitle>
    <DialogContent dividers>
      <Stack gap={2}>
        {(save.isError || catalog.isError) && <Alert severity="error">{apiErrorMessage(save.error ?? catalog.error)}</Alert>}
        {catalog.isPending && <LinearProgress />}
        <TextField label="Template name" value={name} inputProps={{ maxLength: 200 }} onChange={(event) => setName(event.target.value)} />
        <Typography variant="body2" color="text.secondary">
          Phase and task offsets are measured in minutes from the project start. Each task must fit inside its phase.
        </Typography>
        {phases.map((phase, index) => <Paper key={index} variant="outlined" sx={{ p: 2 }}>
          <Stack gap={1.5}>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField fullWidth size="small" label="Phase name" value={phase.name} onChange={(event) => updatePhase(index, { name: event.target.value })} />
              <TextField size="small" type="number" label="Phase start offset" value={phase.start_offset_minutes}
                inputProps={{ min: 0 }} onChange={(event) => updatePhase(index, { start_offset_minutes: Number(event.target.value) })} />
              <TextField size="small" type="number" label="Phase duration" value={phase.duration_minutes}
                inputProps={{ min: 1 }} onChange={(event) => updatePhase(index, { duration_minutes: Number(event.target.value) })} />
              {phases.length > 1 && <Button color="error" onClick={() => setPhases((current) => current.filter((_, item) => item !== index))}>Remove phase</Button>}
            </Stack>
            <Typography variant="subtitle2">Default implementation tasks</Typography>
            {phase.tasks.map((task, taskIndex) => {
              const updateTask = (changes: Partial<TaskDraft>) => updatePhase(index, {
                tasks: phase.tasks.map((item, offset) => offset === taskIndex ? { ...item, ...changes } : item),
              });
              const modules = catalog.data?.modules.filter((module) => module.product_id === task.product_id) ?? [];
              return <Stack gap={1} key={taskIndex} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
                <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                  <TextField fullWidth size="small" label="Task title" value={task.title} onChange={(event) => updateTask({ title: event.target.value })} />
                  <TextField size="small" label="Task number" placeholder="Automatic" InputLabelProps={{ shrink: true }} value={task.task_number}
                    inputProps={{ maxLength: 50 }} onChange={(event) => updateTask({ task_number: event.target.value })} />
                  {phase.tasks.length > 1 && <Button color="error" onClick={() => updatePhase(index, { tasks: phase.tasks.filter((_, offset) => offset !== taskIndex) })}>Remove task</Button>}
                </Stack>
                <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                  <TextField select fullWidth size="small" label="Product" value={catalog.data?.products.some((item) => item.id === task.product_id) ? task.product_id : 0}
                    onChange={(event) => updateTask({ product_id: Number(event.target.value), product_module_id: null })}>
                    <MenuItem value={0} disabled>Select product</MenuItem>
                    {catalog.data?.products.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
                  </TextField>
                  <TextField select fullWidth size="small" label="Module" value={modules.some((item) => item.id === task.product_module_id) ? task.product_module_id : 0}
                    onChange={(event) => updateTask({ product_module_id: Number(event.target.value) || null })}>
                    <MenuItem value={0}>Product-level task</MenuItem>
                    {modules.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
                  </TextField>
                  <TextField size="small" type="number" label="Task start offset" value={task.start_offset_minutes}
                    inputProps={{ min: 0 }} onChange={(event) => updateTask({ start_offset_minutes: Number(event.target.value) })} />
                  <TextField size="small" type="number" label="Task duration" value={task.duration_minutes}
                    inputProps={{ min: 1 }} onChange={(event) => updateTask({ duration_minutes: Number(event.target.value) })} />
                  <TextField size="small" type="number" label="Estimate (minutes)" value={task.estimate_minutes}
                    inputProps={{ min: 0 }} onChange={(event) => updateTask({ estimate_minutes: Number(event.target.value) })} />
                </Stack>
                <TextField size="small" label="Task description" value={task.description ?? ""}
                  onChange={(event) => updateTask({ description: event.target.value || null })} />
                <TextField size="small" label="Predecessor task numbers" value={task.predecessorText ?? task.predecessor_numbers.join(", ")}
                  helperText="Separate manual task numbers with commas."
                  onChange={(event) => updateTask({ predecessorText: event.target.value })} />
              </Stack>;
            })}
            <Button sx={{ alignSelf: "flex-start" }} startIcon={<Add />} onClick={() => updatePhase(index, {
              tasks: [...phase.tasks, { ...blankTask(), start_offset_minutes: phase.start_offset_minutes }],
            })}>Add default task</Button>
          </Stack>
        </Paper>)}
        <Button sx={{ alignSelf: "flex-start" }} startIcon={<Add />} onClick={() => setPhases((current) => {
          const start = Math.max(...current.map((phase) => phase.start_offset_minutes + phase.duration_minutes));
          return [...current, { ...blankPhase(), start_offset_minutes: start, tasks: [{ ...blankTask(), start_offset_minutes: start }] }];
        })}>Add phase</Button>
      </Stack>
    </DialogContent>
    <DialogActions>
      <Button disabled={save.isPending} onClick={onClose}>Cancel</Button>
      <Button disabled={!valid || save.isPending} onClick={() => save.mutate(false)}>Save draft</Button>
      <Button variant="contained" disabled={!valid || save.isPending} onClick={() => save.mutate(true)}>{template ? "Publish new version" : "Publish template"}</Button>
    </DialogActions>
  </Dialog>;
}

export function ProjectTemplatesPage() {
  const [selected, setSelected] = useState("");
  const [editor, setEditor] = useState<{ template?: Template; version?: Version } | null>(null);
  const [reuse, setReuse] = useState<{ id: number; versionId: number } | null>(null);
  const cache = useQueryClient();
  const templates = useQuery({
    queryKey: ["project-templates"], queryFn: async () => (await api.get<Template[]>("/project-templates")).data,
  });
  const versions = useQuery({
    queryKey: ["project-template-versions", selected],
    queryFn: async () => (await api.get<Version[]>(`/project-templates/${selected}/versions`)).data,
    enabled: Boolean(selected),
  });
  const template = templates.data?.find((item) => String(item.id) === selected);
  return <Stack gap={2} sx={{ width: "100%", minWidth: 0 }}>
    <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
      <Typography component="h1" variant="h4" fontWeight={800}>Project Templates</Typography>
      <Stack direction="row" gap={1}>
        <Button component={Link} to="/projects">Open projects</Button>
        <Button variant="contained" startIcon={<Add />} onClick={() => setEditor({})}>New template</Button>
      </Stack>
    </Stack>
    {(templates.isError || versions.isError) && <Alert severity="error">{apiErrorMessage(templates.error ?? versions.error)}</Alert>}
    {(templates.isPending || (selected && versions.isPending)) && <LinearProgress />}
    {templates.data?.length === 0 && <Alert severity="info">Create a template to reuse its phases and implementation tasks across projects.</Alert>}
    {!!templates.data?.length && <TextField select label="Template" value={template ? selected : "none"} onChange={(event) => setSelected(event.target.value === "none" ? "" : event.target.value)}>
      <MenuItem value="none">Choose a template</MenuItem>
      {templates.data.map((item) => <MenuItem key={item.id} value={String(item.id)}>{item.name}</MenuItem>)}
    </TextField>}
    {versions.data?.map((version) => <Paper key={version.id} variant="outlined" sx={{ p: 2 }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
        <Box>
          <Stack direction="row" gap={1} alignItems="center">
            <Typography component="h2" variant="h6">Version {version.version_number}</Typography>
            <Chip size="small" label={version.published_at ? "Published" : "Draft"} color={version.published_at ? "success" : "default"} />
          </Stack>
          <Typography color="text.secondary">{version.plan.product_ids.length} products · {version.plan.module_ids.length} modules</Typography>
        </Box>
        {template && <Stack direction="row" gap={1}>
          <Button startIcon={<EditOutlined />} onClick={() => setEditor({ template, version })}>Edit template</Button>
          {version.published_at && <Button variant="outlined" onClick={() => setReuse({ id: template.id, versionId: version.id })}>Use template</Button>}
        </Stack>}
      </Stack>
      {version.plan.phases.map((phase, index) => <Box key={index} sx={{ mt: 1 }}>
        <Typography variant="body2" fontWeight={700}>{phase.name}</Typography>
        <Typography variant="body2" color="text.secondary">{phase.tasks.map((task) => task.title).join(" · ")}</Typography>
      </Box>)}
    </Paper>)}
    {editor && <TemplateEditor {...editor} onClose={() => setEditor(null)} onSaved={(version) => {
      const templateId = String(version.template_id);
      setSelected(templateId);
      setEditor(null);
      void cache.invalidateQueries({ queryKey: ["project-templates"] });
      void cache.invalidateQueries({ queryKey: ["project-template-versions", templateId] });
    }} />}
    {reuse && <ProjectCreationWizard open startingTemplate={reuse} onClose={() => setReuse(null)} onCreated={() => {
      for (const key of ["projects", "project-summary", "project-portfolio-products"]) void cache.invalidateQueries({ queryKey: [key] });
    }} />}
  </Stack>;
}
