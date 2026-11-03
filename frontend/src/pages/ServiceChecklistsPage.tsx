import { Add, DeleteOutline, Publish } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ServiceChecklistSchedulePanel } from "./ServiceChecklistSchedulePanel";
import { ServiceChecklistAssignments } from "./ServiceChecklistAssignments";
import { SimpleChecklistWorkspace } from "./SimpleChecklistWorkspace";

type Responsibility = "MILLENSYS" | "CLIENT" | "SHARED";
type EvidenceType =
  "NONE" | "COMMENT" | "FILE" | "VALUE" | "CONFIRMATION" | "LINK";
type ChecklistItem = {
  id?: number;
  item_code: string;
  title: string;
  instructions: string;
  display_order: number;
  is_required: boolean;
  responsibility: Responsibility;
  evidence_type: EvidenceType;
  evidence_required: boolean;
  expected_duration_minutes: number | null;
};
type ChecklistTemplate = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  schedule_mode: "SCHEDULED" | "CLIENT_MANAGED_UNSCHEDULED";
  version: number;
  publication_status: "DRAFT" | "PUBLISHED" | "RETIRED";
  is_default: boolean;
  is_active: boolean;
  items: ChecklistItem[];
};
type Draft = Omit<
  ChecklistTemplate,
  "id" | "publication_status" | "is_active"
> & { id?: number };

const blankItem = (order: number): ChecklistItem => ({
  item_code: `STEP_${order + 1}`,
  title: "",
  instructions: "",
  display_order: order,
  is_required: true,
  responsibility: "MILLENSYS",
  evidence_type: "NONE",
  evidence_required: false,
  expected_duration_minutes: null,
});
const blankDraft = (): Draft => ({
  code: "",
  name: "",
  description: "",
  schedule_mode: "SCHEDULED",
  is_default: false,
  version: 1,
  items: [blankItem(0)],
});

export function ServiceChecklistsPage() {
  const initialView = new URLSearchParams(window.location.search).get("view");
  const { hasPermission } = useAuth();
  const canManage = hasPermission("service_checklist.template.manage");
  const cache = useQueryClient();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState(
    initialView === "mine" ? 1 : initialView === "configuration" ? 2 : 0,
  );
  const templates = useQuery({
    queryKey: ["service-checklist-templates"],
    queryFn: async () =>
      (await api.get<ChecklistTemplate[]>("/service-checklists/templates"))
        .data,
  });
  const refresh = () =>
    cache.invalidateQueries({ queryKey: ["service-checklist-templates"] });
  const save = useMutation({
    mutationFn: async (value: Draft) =>
      value.id
        ? api.put(`/service-checklists/templates/${value.id}`, value)
        : api.post("/service-checklists/templates", value),
    onSuccess: async () => {
      setDraft(null);
      setError("");
      await refresh();
    },
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The checklist template could not be saved."),
      ),
  });
  const publish = useMutation({
    mutationFn: async (id: number) =>
      api.post(`/service-checklists/templates/${id}/publish`),
    onSuccess: refresh,
    onError: (cause) =>
      setError(
        apiErrorMessage(
          cause,
          "The checklist template could not be published.",
        ),
      ),
  });
  const retire = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/service-checklists/templates/${id}`),
    onSuccess: refresh,
    onError: (cause) =>
      setError(
        apiErrorMessage(cause, "The checklist template could not be retired."),
      ),
  });
  const updateItem = (index: number, change: Partial<ChecklistItem>) =>
    setDraft((current) =>
      current
        ? {
            ...current,
            items: current.items.map((item, position) =>
              position === index ? { ...item, ...change } : item,
            ),
          }
        : current,
    );
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft) return;
    if (
      draft.items.some(
        (item) =>
          ["CLIENT", "SHARED"].includes(item.responsibility) &&
          (!item.evidence_required || item.evidence_type === "NONE"),
      )
    ) {
      setError(
        "Every Client or Shared responsibility item must require a selected evidence type.",
      );
      return;
    }
    save.mutate({
      ...draft,
      items: draft.items.map((item, index) => ({
        ...item,
        display_order: index,
      })),
    });
  };
  return (
    <Stack spacing={2.5}>
      <Paper
        sx={{
          p: { xs: 2, md: 3 },
          background: (theme) =>
            `linear-gradient(135deg, ${theme.palette.background.paper}, ${theme.palette.action.hover})`,
        }}
      >
        <Stack
          direction={{ xs: "column", sm: "row" }}
          gap={2}
          alignItems={{ sm: "center" }}
        >
          <Box sx={{ flex: 1 }}>
            <Typography variant="h4" fontWeight={850}>
              Service Checklists
            </Typography>
            <Typography color="text.secondary">
              Design controlled recurring service procedures, ownership, and
              customer-facing evidence.
            </Typography>
          </Box>
          {canManage && (
            <Button
              startIcon={<Add />}
              variant="contained"
              onClick={() => {
                setError("");
                setDraft(blankDraft());
              }}
            >
              New template
            </Button>
          )}
        </Stack>
      </Paper>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      <Tabs
        value={tab}
        onChange={(_, value) => setTab(value)}
        variant="scrollable"
        allowScrollButtonsMobile
      >
        <Tab label="Checklist Monitor" />
        <Tab label="My Checklists" />
        <Tab label="Configuration" />
      </Tabs>
      {tab === 0 && <SimpleChecklistWorkspace monitor />}
      {tab === 1 && (
        <>
          <SimpleChecklistWorkspace />
          <ServiceChecklistSchedulePanel templates={templates.data ?? []} />
        </>
      )}
      {tab === 2 && (
        <>
          <ServiceChecklistAssignments templates={templates.data ?? []} />
          <ServiceChecklistSchedulePanel templates={templates.data ?? []} />
          <Typography variant="h5" fontWeight={850}>
            Template library
          </Typography>
          {templates.isError && (
            <Alert severity="error">
              Service checklist templates could not be loaded.
            </Alert>
          )}
          <Stack spacing={1.5}>
            {templates.data?.map((template) => (
              <Paper variant="outlined" key={template.id} sx={{ p: 2.25 }}>
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  gap={2}
                  alignItems={{ md: "center" }}
                >
                  <Box sx={{ flex: 1 }}>
                    <Stack
                      direction="row"
                      gap={1}
                      flexWrap="wrap"
                      alignItems="center"
                    >
                      <Typography fontWeight={800}>{template.name}</Typography>
                      <Chip
                        size="small"
                        label={template.publication_status}
                        color={
                          template.publication_status === "PUBLISHED"
                            ? "success"
                            : "default"
                        }
                      />
                      {template.is_default && (
                        <Chip size="small" color="primary" label="DEFAULT" />
                      )}
                      <Chip
                        size="small"
                        variant="outlined"
                        label={
                          template.schedule_mode === "SCHEDULED"
                            ? "Scheduled"
                            : "Client managed · unscheduled"
                        }
                      />
                    </Stack>
                    <Typography variant="body2" color="text.secondary">
                      {template.code} · Version {template.version} ·{" "}
                      {template.items.length} items
                    </Typography>
                  </Box>
                  {canManage && (
                    <Button
                      onClick={() =>
                        setDraft({
                          id: template.id,
                          code: template.code,
                          name: template.name,
                          description: template.description,
                          schedule_mode: template.schedule_mode,
                          is_default: template.is_default,
                          version: template.version,
                          items: template.items,
                        })
                      }
                    >
                      Edit
                    </Button>
                  )}
                  {canManage && template.publication_status === "DRAFT" && (
                    <Button
                      startIcon={<Publish />}
                      onClick={() => publish.mutate(template.id)}
                    >
                      Publish
                    </Button>
                  )}
                  {canManage && (
                    <Button
                      color="error"
                      onClick={() =>
                        window.confirm(`Retire “${template.name}”?`) &&
                        retire.mutate(template.id)
                      }
                    >
                      Retire
                    </Button>
                  )}
                </Stack>
              </Paper>
            ))}
          </Stack>
        </>
      )}
      <Dialog
        open={Boolean(draft)}
        onClose={() => !save.isPending && setDraft(null)}
        fullWidth
        maxWidth="lg"
      >
        <Box component="form" onSubmit={submit}>
          <DialogTitle>
            {draft?.id ? "Edit checklist template" : "New checklist template"}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}
              <Stack direction={{ xs: "column", md: "row" }} gap={2}>
                <TextField
                  required
                  disabled={Boolean(draft?.id)}
                  fullWidth
                  label="Code"
                  value={draft?.code ?? ""}
                  onChange={(e) =>
                    setDraft(
                      (d) => d && { ...d, code: e.target.value.toUpperCase() },
                    )
                  }
                />
                <TextField
                  required
                  fullWidth
                  label="Template name"
                  value={draft?.name ?? ""}
                  onChange={(e) =>
                    setDraft((d) => d && { ...d, name: e.target.value })
                  }
                />
                <TextField
                  select
                  fullWidth
                  label="Scheduling"
                  value={draft?.schedule_mode ?? "SCHEDULED"}
                  onChange={(e) =>
                    setDraft(
                      (d) =>
                        d && {
                          ...d,
                          schedule_mode: e.target
                            .value as Draft["schedule_mode"],
                        },
                    )
                  }
                >
                  <MenuItem value="SCHEDULED">Scheduled by Millensys</MenuItem>
                  <MenuItem value="CLIENT_MANAGED_UNSCHEDULED">
                    Client managed · no scheduling
                  </MenuItem>
                </TextField>
              </Stack>
              <TextField
                multiline
                minRows={2}
                label="Description"
                value={draft?.description ?? ""}
                onChange={(e) =>
                  setDraft((d) => d && { ...d, description: e.target.value })
                }
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={draft?.is_default ?? false}
                    onChange={(e) =>
                      setDraft(
                        (d) => d && { ...d, is_default: e.target.checked },
                      )
                    }
                  />
                }
                label="Default template for new checklist assignments"
              />
              <Typography variant="h6">Checklist items</Typography>
              {draft?.items.map((item, index) => (
                <Paper key={index} variant="outlined" sx={{ p: 2 }}>
                  <Stack spacing={1.5}>
                    <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
                      <TextField
                        required
                        label="Item code"
                        value={item.item_code}
                        onChange={(e) =>
                          updateItem(index, {
                            item_code: e.target.value.toUpperCase(),
                          })
                        }
                        sx={{ flex: 0.65 }}
                      />
                      <TextField
                        required
                        label="Task"
                        value={item.title}
                        onChange={(e) =>
                          updateItem(index, { title: e.target.value })
                        }
                        sx={{ flex: 2 }}
                      />
                      <IconButton
                        aria-label="Remove item"
                        disabled={draft.items.length === 1}
                        onClick={() =>
                          setDraft(
                            (d) =>
                              d && {
                                ...d,
                                items: d.items.filter((_, i) => i !== index),
                              },
                          )
                        }
                      >
                        <DeleteOutline />
                      </IconButton>
                    </Stack>
                    <TextField
                      label="Instructions"
                      value={item.instructions ?? ""}
                      onChange={(e) =>
                        updateItem(index, { instructions: e.target.value })
                      }
                    />
                    <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
                      <TextField
                        select
                        fullWidth
                        label="Responsible party"
                        value={item.responsibility}
                        onChange={(e) => {
                          const responsibility = e.target
                            .value as Responsibility;
                          updateItem(index, {
                            responsibility,
                            evidence_required:
                              responsibility === "MILLENSYS"
                                ? item.evidence_required
                                : true,
                          });
                        }}
                      >
                        <MenuItem value="MILLENSYS">
                          Millensys engineer
                        </MenuItem>
                        <MenuItem value="CLIENT">Client IT</MenuItem>
                        <MenuItem value="SHARED">Shared</MenuItem>
                      </TextField>
                      <TextField
                        select
                        fullWidth
                        label="Evidence type"
                        value={item.evidence_type}
                        onChange={(e) =>
                          updateItem(index, {
                            evidence_type: e.target.value as EvidenceType,
                          })
                        }
                      >
                        {[
                          "NONE",
                          "COMMENT",
                          "FILE",
                          "VALUE",
                          "CONFIRMATION",
                          "LINK",
                        ].map((value) => (
                          <MenuItem key={value} value={value}>
                            {value}
                          </MenuItem>
                        ))}
                      </TextField>
                      <TextField
                        fullWidth
                        type="number"
                        label="Expected minutes"
                        value={item.expected_duration_minutes ?? ""}
                        inputProps={{ min: 1 }}
                        onChange={(e) =>
                          updateItem(index, {
                            expected_duration_minutes: e.target.value
                              ? Number(e.target.value)
                              : null,
                          })
                        }
                      />
                    </Stack>
                    <Stack direction="row" gap={2}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={item.is_required}
                            onChange={(e) =>
                              updateItem(index, {
                                is_required: e.target.checked,
                              })
                            }
                          />
                        }
                        label="Required"
                      />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={item.evidence_required}
                            disabled={item.responsibility !== "MILLENSYS"}
                            onChange={(e) =>
                              updateItem(index, {
                                evidence_required: e.target.checked,
                              })
                            }
                          />
                        }
                        label="Evidence required"
                      />
                    </Stack>
                  </Stack>
                </Paper>
              ))}
              <Button
                startIcon={<Add />}
                onClick={() =>
                  setDraft(
                    (d) =>
                      d && {
                        ...d,
                        items: [...d.items, blankItem(d.items.length)],
                      },
                  )
                }
              >
                Add item
              </Button>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDraft(null)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={save.isPending}>
              Save template
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
