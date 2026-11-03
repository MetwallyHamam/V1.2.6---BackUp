import { AccountTree, Add } from "@mui/icons-material";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { OrganizationHierarchyNode, OrganizationHierarchyViewer } from "../components/OrganizationHierarchyViewer";

type NodeType = "EXECUTIVE" | "MANAGER" | "TEAM" | "TEAM_MEMBER" | "ROLE";
type ChartNode = OrganizationHierarchyNode & { node_type: NodeType; email?: string | null; phone_number?: string | null; sort_order: number; is_active: boolean };
const nodeTypes: Array<{ value: NodeType; label: string }> = [
  { value: "EXECUTIVE", label: "Executive (CEO / CTO / CAO / HR)" }, { value: "MANAGER", label: "Manager" },
  { value: "TEAM", label: "Team" }, { value: "TEAM_MEMBER", label: "Team member" }, { value: "ROLE", label: "Other role" },
];

export function OrganizationHierarchyPage() {
  const { hasPermission } = useAuth(), location = useLocation(), queryClient = useQueryClient();
  const configure = location.pathname.endsWith("/configure") && hasPermission("user.manage");
  const [open, setOpen] = useState(false), [editing, setEditing] = useState<ChartNode | null>(null), [parentId, setParentId] = useState<number | null>(null), [error, setError] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["manual-organization-chart", configure], queryFn: async () => (await api.get<ChartNode[]>("/users/organization-chart", { params: { include_inactive: configure } })).data });
  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => editing ? api.patch(`/users/organization-chart/${editing.id}`, payload) : api.post("/users/organization-chart", payload),
    onSuccess: async () => { setOpen(false); setEditing(null); setError(null); await queryClient.invalidateQueries({ queryKey: ["manual-organization-chart"] }); },
    onError: () => setError("The node could not be saved. Check its parent and required fields."),
  });
  const remove = useMutation({
    mutationFn: async (node: ChartNode) => api.delete(`/users/organization-chart/${node.id}`),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["manual-organization-chart"] }),
    onError: () => setError("Move or remove child nodes before deleting this node."),
  });
  const nodes = useMemo(() => query.data ?? [], [query.data]);
  function show(node?: ChartNode, parent?: ChartNode) { setEditing(node ?? null); setParentId(node?.parent_id ?? parent?.id ?? null); setError(null); setOpen(true); }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget));
    save.mutate({ name: String(data.name).trim(), node_type: data.node_type, title: String(data.title).trim() || null, image_url: String(data.image_url).trim() || null, parent_id: data.parent_id ? Number(data.parent_id) : null, email: String(data.email).trim() || null, phone_number: String(data.phone_number).trim() || null, notes: String(data.notes).trim() || null, sort_order: Number(data.sort_order || 0), is_active: data.is_active === "true" });
  }
  if (query.isError) return <Alert severity="error">The organization hierarchy could not be loaded.</Alert>;
  return <Stack spacing={2}>
    <Paper sx={{ p: 2.5 }}><Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}><Box><Stack direction="row" gap={1} alignItems="center"><AccountTree color="primary" /><Typography variant="h4" fontWeight={900}>Organization Hierarchy</Typography></Stack><Typography color="text.secondary">Explore executives, managers, teams and team members without page-level horizontal scrolling.</Typography></Box>{configure && <Button variant="contained" startIcon={<Add />} onClick={() => show()}>Add root node</Button>}</Stack></Paper>
    {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}
    <Paper sx={{ p: 2 }}><OrganizationHierarchyViewer nodes={nodes} loading={query.isLoading} configure={configure} onAdd={(parent) => show(undefined, parent as ChartNode | undefined)} onEdit={(node) => show(node as ChartNode)} onDelete={(node) => remove.mutate(node as ChartNode)} /></Paper>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm"><form onSubmit={submit}><DialogTitle>{editing ? "Edit hierarchy node" : "Add hierarchy node"}</DialogTitle><DialogContent>
      <TextField required name="name" label="Name / team name" defaultValue={editing?.name ?? ""} fullWidth margin="normal" />
      <TextField required select name="node_type" label="Node type" defaultValue={editing?.node_type ?? "EXECUTIVE"} fullWidth margin="normal">{nodeTypes.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</TextField>
      <TextField name="title" label="Position (CEO, CTO, HR, Manager…)" defaultValue={editing?.title ?? ""} fullWidth margin="normal" />
      <TextField select name="parent_id" label="Reports to / parent" value={parentId ?? ""} onChange={(event) => setParentId(event.target.value === "" ? null : Number(event.target.value))} fullWidth margin="normal"><MenuItem value="">Top level</MenuItem>{nodes.filter((node) => node.id !== editing?.id).map((node) => <MenuItem key={node.id} value={node.id}>{node.title ? `${node.title} — ` : ""}{node.name}</MenuItem>)}</TextField>
      <TextField name="image_url" label="Circular image URL" defaultValue={editing?.image_url ?? ""} fullWidth margin="normal" />
      <Stack direction={{ xs: "column", sm: "row" }} gap={1}><TextField name="email" label="Email (optional)" defaultValue={editing?.email ?? ""} fullWidth margin="normal" /><TextField name="phone_number" label="Phone (optional)" defaultValue={editing?.phone_number ?? ""} fullWidth margin="normal" /></Stack>
      <TextField name="notes" label="Short description" defaultValue={editing?.notes ?? ""} fullWidth margin="normal" />
      <Stack direction="row" gap={1}><TextField name="sort_order" type="number" label="Display order" defaultValue={editing?.sort_order ?? 0} fullWidth margin="normal" /><TextField select name="is_active" label="Status" defaultValue={String(editing?.is_active ?? true)} fullWidth margin="normal"><MenuItem value="true">Active</MenuItem><MenuItem value="false">Inactive</MenuItem></TextField></Stack>
    </DialogContent><DialogActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" variant="contained" disabled={save.isPending}>Save</Button></DialogActions></form></Dialog>
  </Stack>;
}
