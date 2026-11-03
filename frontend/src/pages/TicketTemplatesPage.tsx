import { Alert, Box, Button, Checkbox, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api, apiErrorMessage } from "../api/client";

type TicketTemplate = {
  id: number; name: string; keywords: string; source_ticket_id?: number; ticket_type_id: number;
  client_id?: number; product_id?: number; product_module_id?: number; environment_id?: number;
  service_id?: number; category_id?: number; subcategory_id?: number; subject: string; description: string;
  priority: string; impact: string; urgency: string; assigned_team?: string; portal_visible: boolean;
  is_active: boolean; version: number;
};

export function TicketTemplatesPage() {
  const cache = useQueryClient();
  const [editing, setEditing] = useState<TicketTemplate | null>(null);
  const [error, setError] = useState("");
  const templates = useQuery({ queryKey: ["ticket-templates", "manage"], queryFn: async () => (await api.get<TicketTemplate[]>("/tickets/templates/manage")).data });
  const save = useMutation({
    mutationFn: async ({ template, form }: { template: TicketTemplate; form: HTMLFormElement }) => {
      const values = new FormData(form);
      return api.patch(`/tickets/templates/${template.id}`, {
        ...template,
        name: String(values.get("name") ?? "").trim(), keywords: String(values.get("keywords") ?? "").trim(),
        subject: String(values.get("subject") ?? "").trim(), description: String(values.get("description") ?? "").trim(),
        priority: values.get("priority"), impact: values.get("impact"), urgency: values.get("urgency"),
        portal_visible: values.get("portal_visible") === "on", is_active: values.get("is_active") === "on",
        expected_version: template.version,
      });
    },
    onSuccess: async () => { setEditing(null); setError(""); await cache.invalidateQueries({ queryKey: ["ticket-templates"] }); },
    onError: (cause) => setError(apiErrorMessage(cause, "The template could not be updated.")),
  });
  const remove = useMutation({
    mutationFn: async (template: TicketTemplate) => api.delete(`/tickets/templates/${template.id}`, { params: { expected_version: template.version } }),
    onSuccess: async () => cache.invalidateQueries({ queryKey: ["ticket-templates"] }),
    onError: (cause) => setError(apiErrorMessage(cause, "The template could not be deleted.")),
  });
  return <Paper sx={{ p: { xs: 2, md: 3 } }}>
    <Typography variant="h4">Ticket templates</Typography>
    <Typography color="text.secondary" sx={{ mb: 2 }}>Edit reusable ticket content, portal visibility, and availability. Deleted templates are retained in audit history and disabled.</Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {templates.isError && <Alert severity="error">Ticket templates could not be loaded.</Alert>}
    <Stack spacing={1.25}>
      {templates.data?.map((template) => <Paper key={template.id} variant="outlined" sx={{ p: 2, opacity: template.is_active ? 1 : 0.62 }}>
        <Stack direction={{ xs: "column", sm: "row" }} gap={2} alignItems={{ sm: "center" }}>
          <Box sx={{ flex: 1 }}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={800}>{template.name}</Typography><Chip size="small" label={template.is_active ? "Active" : "Deleted"} color={template.is_active ? "success" : "default"}/>{template.portal_visible && <Chip size="small" label="Client Portal" color="info"/>}</Stack><Typography>{template.subject}</Typography><Typography variant="caption" color="text.secondary">Keywords: {template.keywords || "—"} · Version {template.version}</Typography></Box>
          <Button variant="outlined" onClick={() => { setError(""); setEditing(template); }}>Edit</Button>
          {template.is_active && <Button color="error" disabled={remove.isPending} onClick={() => { if (window.confirm(`Delete template “${template.name}”?`)) remove.mutate(template); }}>Delete</Button>}
        </Stack>
      </Paper>)}
      {templates.data?.length === 0 && <Typography color="text.secondary">No ticket templates have been created.</Typography>}
    </Stack>
    <Dialog open={Boolean(editing)} onClose={() => !save.isPending && setEditing(null)} fullWidth maxWidth="md">
      {editing && <Box component="form" onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); save.mutate({ template: editing, form: event.currentTarget }); }}>
        <DialogTitle>Edit ticket template</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField required name="name" label="Template name" defaultValue={editing.name} inputProps={{ minLength: 2, maxLength: 200 }}/>
          <TextField name="keywords" label="Search keywords" defaultValue={editing.keywords} multiline minRows={2}/>
          <TextField required name="subject" label="Ticket subject" defaultValue={editing.subject} inputProps={{ minLength: 5, maxLength: 300 }}/>
          <TextField required name="description" label="Ticket description" defaultValue={editing.description} multiline minRows={5} inputProps={{ minLength: 10 }}/>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>{(["priority", "impact", "urgency"] as const).map((field) => <TextField key={field} select fullWidth name={field} label={field[0].toUpperCase() + field.slice(1)} defaultValue={editing[field]}>{(field === "priority" ? ["P1", "P2", "P3", "P4"] : ["LOW", "MEDIUM", "HIGH", "CRITICAL"]).map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField>)}</Stack>
          <FormControlLabel control={<Checkbox name="portal_visible" defaultChecked={editing.portal_visible}/>} label="Available in Client Portal"/>
          <FormControlLabel control={<Checkbox name="is_active" defaultChecked={editing.is_active}/>} label="Active"/>
        </Stack></DialogContent><DialogActions><Button onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" variant="contained" disabled={save.isPending}>Save template</Button></DialogActions>
      </Box>}
    </Dialog>
  </Paper>;
}
