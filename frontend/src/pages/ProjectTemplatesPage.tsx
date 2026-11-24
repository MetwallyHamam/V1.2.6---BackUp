import { Alert, Box, Button, LinearProgress, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";

type Template = { id: number; name: string };
type Version = {
  id: number;
  version_number: number;
  published_at: string | null;
  plan: { product_ids: number[]; module_ids: number[]; phases: { name: string; tasks: { title: string }[] }[] };
};

export function ProjectTemplatesPage() {
  const [selected, setSelected] = useState("");
  const queryClient = useQueryClient();
  const templates = useQuery({
    queryKey: ["project-templates"],
    queryFn: async () => (await api.get<Template[]>("/project-templates")).data,
  });
  const versions = useQuery({
    queryKey: ["project-template-versions", selected],
    queryFn: async () => (await api.get<Version[]>(`/project-templates/${selected}/versions`)).data,
    enabled: Boolean(selected),
  });
  const publish = useMutation({
    mutationFn: async ({ templateId, plan }: { templateId: string; plan: Version["plan"] }) =>
      api.post(`/project-templates/${templateId}/versions`, { plan, publish: true }),
    onSuccess: (_, { templateId }) =>
      queryClient.invalidateQueries({ queryKey: ["project-template-versions", templateId] }),
  });
  const error = templates.error ?? versions.error ?? publish.error;
  return (
    <Stack gap={2} sx={{ p: { xs: 2, md: 3 }, maxWidth: 1200, mx: "auto" }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
        <Typography component="h1" variant="h4">Project Templates</Typography>
        <Button component={Link} to="/projects">Open projects</Button>
      </Stack>
      {error && <Alert severity="error">{apiErrorMessage(error)}</Alert>}
      {(templates.isPending || (selected && versions.isPending)) && <LinearProgress />}
      {templates.data?.length === 0 && (
        <Alert severity="info">To create your first template, open a new project and publish its plan from Review.</Alert>
      )}
      {!!templates.data?.length && <TextField select label="Template" value={selected}
        onChange={(event) => { setSelected(event.target.value); publish.reset(); }}>
        <MenuItem value="">Choose a template</MenuItem>
        {templates.data.map((template) => (
          <MenuItem key={template.id} value={String(template.id)}>{template.name}</MenuItem>
        ))}
      </TextField>}
      {versions.data?.map((version) => (
        <Paper key={version.id} variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" justifyContent="space-between" gap={1}>
            <Box>
              <Typography component="h2" variant="h6">
                Version {version.version_number} · {version.published_at ? "Published" : "Draft"}
              </Typography>
              <Typography color="text.secondary">
                {version.plan.product_ids.length} products · {version.plan.module_ids.length} modules
              </Typography>
            </Box>
            {!version.published_at && (
              <Button disabled={publish.isPending} onClick={() => publish.mutate({
                templateId: selected, plan: version.plan,
              })}>Publish as new version</Button>
            )}
          </Stack>
          {version.plan.phases.map((phase, index) => (
            <Typography key={index} variant="body2" sx={{ mt: 1 }}>
              {phase.name} · {phase.tasks.length} tasks
            </Typography>
          ))}
        </Paper>
      ))}
    </Stack>
  );
}
