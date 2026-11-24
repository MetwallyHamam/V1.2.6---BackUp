import {
  AccountTree,
  Add,
  Apartment,
  Business,
  ChevronRight,
  Groups,
  Link as LinkIcon,
  Policy,
  Refresh,
  Store,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Account = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  organization_count: number;
};
type Organization = {
  id: number;
  account_id: number;
  code: string;
  name: string;
  legal_name: string | null;
  is_active: boolean;
  client_count: number;
};
type Client = {
  id: number;
  code: string;
  name: string;
  organization_id: number | null;
  is_active: boolean;
};
type Branch = { id: number; client_id: number; code: string; name: string; is_active: boolean };
type Department = { id: number; code: string; name: string; is_active: boolean };
type Scope = { type: "ORGANIZATION" | "CLIENT" | "BRANCH"; id: number; name: string };
type EffectiveAssignment = {
  department_id: number;
  department_name: string;
  relationship: string;
  access_profile: string;
  source_type: string;
  source_id: number;
  inherited: boolean;
  visibility_only: boolean;
  effective_from: string | null;
  effective_until: string | null;
  reason: string | null;
};
type PolicyResponse = {
  scope_type: string;
  scope_id: number;
  mode: "INHERIT" | "EXTEND" | "OVERRIDE";
  effective_at: string;
  assignments: EffectiveAssignment[];
  direct_assignments: EffectiveAssignment[];
};
type AssignmentDraft = {
  department_id: string;
  relationship: string;
  access_profile: string;
  effective_from: string;
  effective_until: string;
  reason: string;
};
type Impact = {
  affected_client_count: number;
  affected_branch_count: number;
  added_department_ids: number[];
  retained_visibility_department_ids: number[];
};

const blankAssignment = (): AssignmentDraft => ({
  department_id: "",
  relationship: "SHARED_OPERATOR",
  access_profile: "CUSTOMER_VIEWER",
  effective_from: "",
  effective_until: "",
  reason: "",
});

const toLocalDateTime = (value: string | null) =>
  value ? value.slice(0, 16) : "";

export function clientsForOrganization(items: Client[], organizationId: number | null) {
  return items.filter((item) => item.organization_id === organizationId);
}

export function buildDepartmentPolicyPayload(
  mode: PolicyResponse["mode"],
  changeReason: string,
  assignments: AssignmentDraft[],
) {
  return {
    mode,
    change_reason: changeReason,
    assignments: assignments.map((item) => ({
      department_id: Number(item.department_id),
      relationship: item.relationship,
      access_profile: item.access_profile,
      effective_from: item.effective_from || null,
      effective_until: item.effective_until || null,
      reason: item.reason || null,
    })),
  };
}

export function CustomerStructurePage() {
  const { t } = useTranslation();
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const canManage =
    hasPermission("customer_structure.policy.manage") || hasPermission("client.manage");
  const [accountId, setAccountId] = useState<number | null>(null);
  const [organizationId, setOrganizationId] = useState<number | null>(null);
  const [clientId, setClientId] = useState<number | null>(null);
  const [accountDialog, setAccountDialog] = useState(false);
  const [organizationDialog, setOrganizationDialog] = useState(false);
  const [linkDialog, setLinkDialog] = useState(false);
  const [clientsToLink, setClientsToLink] = useState<number[]>([]);
  const [clientSearch, setClientSearch] = useState("");
  const [bulkReason, setBulkReason] = useState("");
  const [policyScope, setPolicyScope] = useState<Scope | null>(null);
  const [mode, setMode] = useState<PolicyResponse["mode"]>("INHERIT");
  const [assignments, setAssignments] = useState<AssignmentDraft[]>([]);
  const [changeReason, setChangeReason] = useState("");
  const [impact, setImpact] = useState<Impact | null>(null);
  const [notice, setNotice] = useState("");

  const accounts = useQuery({
    queryKey: ["customer-structure", "accounts"],
    queryFn: async () => (await api.get<Account[]>("/accounts", { params: { active_only: false } })).data,
  });
  const organizations = useQuery({
    queryKey: ["customer-structure", "organizations", accountId],
    queryFn: async () =>
      (await api.get<Organization[]>("/organizations", { params: { account_id: accountId, active_only: false } })).data,
    enabled: accountId !== null,
  });
  const clients = useQuery({
    queryKey: ["customer-structure", "clients"],
    queryFn: async () => {
      const result: Client[] = [];
      for (let offset = 0; ; offset += 200) {
        const page = (
          await api.get<Client[]>("/clients", {
            params: { active_only: false, limit: 200, offset },
          })
        ).data;
        result.push(...page);
        if (page.length < 200) return result;
      }
    },
  });
  const branches = useQuery({
    queryKey: ["customer-structure", "branches", clientId],
    queryFn: async () => (await api.get<Branch[]>(`/clients/${clientId}/branches`)).data,
    enabled: clientId !== null,
  });
  const departments = useQuery({
    queryKey: ["departments", "active"],
    queryFn: async () =>
      (await api.get<Department[]>("/departments", { params: { active_only: true } })).data,
  });
  const policy = useQuery({
    queryKey: ["customer-structure", "policy", policyScope?.type, policyScope?.id],
    queryFn: async () =>
      (
        await api.get<PolicyResponse>(
          `/customer-structure/${policyScope!.type.toLowerCase()}/${policyScope!.id}/department-policy`,
        )
      ).data,
    enabled: policyScope !== null,
  });

  useEffect(() => {
    if (accountId === null && accounts.data?.length) setAccountId(accounts.data[0].id);
  }, [accountId, accounts.data]);
  useEffect(() => {
    if (!organizations.data?.some((item) => item.id === organizationId)) {
      setOrganizationId(organizations.data?.[0]?.id ?? null);
      setClientId(null);
    }
  }, [organizationId, organizations.data]);
  useEffect(() => {
    if (!policy.data) return;
    setMode(policy.data.mode);
    setAssignments(
      policy.data.direct_assignments.map((item) => ({
        department_id: String(item.department_id),
        relationship: item.relationship,
        access_profile: item.access_profile,
        effective_from: toLocalDateTime(item.effective_from),
        effective_until: toLocalDateTime(item.effective_until),
        reason: item.reason ?? "",
      })),
    );
    setChangeReason("");
    setImpact(null);
  }, [policy.data]);

  const selectedAccount = accounts.data?.find((item) => item.id === accountId);
  const selectedOrganization = organizations.data?.find((item) => item.id === organizationId);
  const organizationClients = useMemo(
    () => clientsForOrganization(clients.data ?? [], organizationId),
    [clients.data, organizationId],
  );
  const assignableClients = useMemo(
    () => (clients.data ?? []).filter((item) => item.organization_id !== organizationId),
    [clients.data, organizationId],
  );
  const filteredAssignableClients = useMemo(
    () => {
      const term = clientSearch.trim().toLocaleLowerCase();
      return term
        ? assignableClients.filter((item) =>
            `${item.code} ${item.name}`.toLocaleLowerCase().includes(term),
          )
        : assignableClients;
    },
    [assignableClients, clientSearch],
  );

  const invalidateStructure = async () => {
    await queryClient.invalidateQueries({ queryKey: ["customer-structure"] });
  };
  const createAccount = useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await api.post<Account>("/accounts", body)).data,
    onSuccess: async (item) => {
      await invalidateStructure();
      setAccountId(item.id);
      setAccountDialog(false);
      setNotice(t("customerStructure.accountCreated"));
    },
  });
  const createOrganization = useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await api.post<Organization>("/organizations", body)).data,
    onSuccess: async (item) => {
      await invalidateStructure();
      setOrganizationId(item.id);
      setOrganizationDialog(false);
      setNotice(t("customerStructure.organizationCreated"));
    },
  });
  const linkClients = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ updated_count: number }>(
          `/organizations/${organizationId}/clients/bulk-assign`,
          { client_ids: clientsToLink, reason: bulkReason.trim() },
        )
      ).data,
    onSuccess: async (result) => {
      await invalidateStructure();
      setClientId(clientsToLink.length === 1 ? clientsToLink[0] : null);
      setClientsToLink([]);
      setClientSearch("");
      setBulkReason("");
      setLinkDialog(false);
      setNotice(t("customerStructure.clientsLinked", { count: result.updated_count }));
    },
  });
  const closeLinkDialog = () => {
    if (linkClients.isPending) return;
    setLinkDialog(false);
    setClientsToLink([]);
    setClientSearch("");
    setBulkReason("");
  };

  const policyPayload = () =>
    buildDepartmentPolicyPayload(mode, changeReason, assignments);
  const previewPolicy = useMutation({
    mutationFn: async () =>
      (
        await api.post<Impact>(
          `/customer-structure/${policyScope!.type.toLowerCase()}/${policyScope!.id}/department-policy/impact-preview`,
          policyPayload(),
        )
      ).data,
    onSuccess: setImpact,
  });
  const savePolicy = useMutation({
    mutationFn: async () =>
      (
        await api.put<PolicyResponse>(
          `/customer-structure/${policyScope!.type.toLowerCase()}/${policyScope!.id}/department-policy`,
          policyPayload(),
        )
      ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["customer-structure", "policy"] });
      setNotice(t("customerStructure.policySaved"));
      setImpact(null);
    },
  });

  const openPolicy = (scope: Scope) => setPolicyScope(scope);
  const updateAssignment = (index: number, patch: Partial<AssignmentDraft>) =>
    setAssignments((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));

  if (accounts.isLoading || clients.isLoading) return <CircularProgress />;
  if (accounts.isError || clients.isError) return <Alert severity="error">{t("customerStructure.loadFailed")}</Alert>;

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 3, background: "linear-gradient(125deg, rgba(25,118,210,.10), rgba(0,150,136,.06))" }}>
        <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}>
          <Box>
            <Stack direction="row" spacing={1} alignItems="center">
              <AccountTree color="primary" />
              <Typography variant="h5" fontWeight={800}>{t("customerStructure.title")}</Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ mt: 0.5 }}>{t("customerStructure.subtitle")}</Typography>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={t("customerStructure.accountCount", { count: accounts.data?.length ?? 0 })} />
            <Chip label={t("customerStructure.organizationCount", { count: organizations.data?.length ?? 0 })} />
            <Chip label={t("customerStructure.clientCount", { count: organizationClients.length })} />
            <Tooltip title={t("customerStructure.refresh")}><IconButton onClick={() => invalidateStructure()}><Refresh /></IconButton></Tooltip>
          </Stack>
        </Stack>
      </Paper>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(230px,.72fr) minmax(260px,.86fr) minmax(360px,1.42fr)" }, gap: 2, alignItems: "start" }}>
        <StructureColumn title={t("customerStructure.accounts")} icon={<Business />} action={canManage && <Button size="small" startIcon={<Add />} onClick={() => setAccountDialog(true)}>{t("common.add", { defaultValue: "Add" })}</Button>}>
          <List disablePadding>
            {accounts.data?.map((item) => <ListItemButton key={item.id} selected={item.id === accountId} onClick={() => setAccountId(item.id)} sx={{ borderRadius: 2, mb: .5 }}><ListItemIcon sx={{ minWidth: 36 }}><Business fontSize="small" /></ListItemIcon><ListItemText primary={item.name} secondary={`${item.code} · ${item.organization_count} ${t("customerStructure.organizationsLower")}`} /><ChevronRight fontSize="small" /></ListItemButton>)}
          </List>
        </StructureColumn>

        <StructureColumn title={t("customerStructure.organizations")} icon={<Apartment />} action={canManage && accountId && <Button size="small" startIcon={<Add />} onClick={() => setOrganizationDialog(true)}>{t("common.add", { defaultValue: "Add" })}</Button>}>
          {selectedAccount && <Typography variant="caption" color="text.secondary" sx={{ display: "block", px: 1, pb: 1 }}>{selectedAccount.name}</Typography>}
          <List disablePadding>
            {organizations.data?.map((item) => <ListItemButton key={item.id} selected={item.id === organizationId} onClick={() => { setOrganizationId(item.id); setClientId(null); }} sx={{ borderRadius: 2, mb: .5 }}><ListItemIcon sx={{ minWidth: 36 }}><Apartment fontSize="small" /></ListItemIcon><ListItemText primary={item.name} secondary={`${item.code} · ${item.client_count} ${t("customerStructure.clientsLower")}`} /><Tooltip title={t("customerStructure.managePolicy")}><IconButton size="small" onClick={(event) => { event.stopPropagation(); openPolicy({ type: "ORGANIZATION", id: item.id, name: item.name }); }}><Policy fontSize="small" /></IconButton></Tooltip></ListItemButton>)}
            {!organizations.data?.length && <EmptyState text={t("customerStructure.noOrganizations")} />}
          </List>
        </StructureColumn>

        <StructureColumn title={t("customerStructure.clientsAndBranches")} icon={<Groups />} action={canManage && organizationId && <Button size="small" startIcon={<LinkIcon />} onClick={() => setLinkDialog(true)}>{t("customerStructure.bulkAssignClients")}</Button>}>
          {selectedOrganization && <Stack direction="row" spacing={1} alignItems="center" sx={{ px: 1, pb: 1 }}><Typography variant="body2" fontWeight={700}>{selectedOrganization.name}</Typography><Chip size="small" variant="outlined" label={`${selectedAccount?.name ?? ""} / ${selectedOrganization.code}`} /></Stack>}
          <List disablePadding>
            {organizationClients.map((item) => <Box key={item.id}><ListItemButton selected={item.id === clientId} onClick={() => setClientId(item.id)} sx={{ borderRadius: 2 }}><ListItemIcon sx={{ minWidth: 36 }}><Groups fontSize="small" /></ListItemIcon><ListItemText primary={item.name} secondary={item.code} /><Tooltip title={t("customerStructure.managePolicy")}><IconButton size="small" onClick={(event) => { event.stopPropagation(); openPolicy({ type: "CLIENT", id: item.id, name: item.name }); }}><Policy fontSize="small" /></IconButton></Tooltip></ListItemButton>{item.id === clientId && <Box sx={{ ml: 4.5, pl: 1.5, borderLeft: 2, borderColor: "divider" }}>{branches.isLoading ? <CircularProgress size={20} /> : branches.data?.length ? branches.data.map((branch) => <Stack key={branch.id} direction="row" alignItems="center" sx={{ py: .5 }}><Store fontSize="small" color="action" /><Box sx={{ ml: 1, minWidth: 0, flex: 1 }}><Typography variant="body2" noWrap>{branch.name}</Typography><Typography variant="caption" color="text.secondary">{branch.code}</Typography></Box><Tooltip title={t("customerStructure.managePolicy")}><IconButton size="small" onClick={() => openPolicy({ type: "BRANCH", id: branch.id, name: branch.name })}><Policy fontSize="small" /></IconButton></Tooltip></Stack>) : <Typography variant="caption" color="text.secondary">{t("customerStructure.noBranches")}</Typography>}</Box>}</Box>)}
            {!organizationClients.length && <EmptyState text={t("customerStructure.noClients")} />}
          </List>
        </StructureColumn>
      </Box>

      <CreateDialog open={accountDialog} title={t("customerStructure.newAccount")} pending={createAccount.isPending} error={createAccount.error} onClose={() => setAccountDialog(false)} onSubmit={(data) => createAccount.mutate(data)} />
      <CreateDialog open={organizationDialog} title={t("customerStructure.newOrganization")} pending={createOrganization.isPending} error={createOrganization.error} onClose={() => setOrganizationDialog(false)} onSubmit={(data) => createOrganization.mutate({ ...data, account_id: accountId })} legalName />
      <Dialog open={linkDialog} onClose={closeLinkDialog} fullWidth maxWidth="sm">
        <DialogTitle>{t("customerStructure.bulkAssignTitle", { organization: selectedOrganization?.name })}</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mt: 1 }}>{t("customerStructure.bulkAssignHelp")}</Alert>
          <TextField fullWidth margin="normal" label={t("customerStructure.searchClients")} value={clientSearch} onChange={(event) => setClientSearch(event.target.value)} />
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="body2" fontWeight={700}>{t("customerStructure.selectedClients", { count: clientsToLink.length })}</Typography>
            <Button size="small" onClick={() => setClientsToLink(filteredAssignableClients.map((item) => item.id))} disabled={!filteredAssignableClients.length}>{t("customerStructure.selectVisible")}</Button>
          </Stack>
          <Paper variant="outlined" sx={{ maxHeight: 300, overflow: "auto", p: 0.5 }}>
            {filteredAssignableClients.map((item) => (
              <ListItemButton key={item.id} dense onClick={() => setClientsToLink((current) => current.includes(item.id) ? current.filter((id) => id !== item.id) : [...current, item.id])}>
                <Checkbox edge="start" checked={clientsToLink.includes(item.id)} tabIndex={-1} />
                <ListItemText primary={item.name} secondary={`${item.code} · ${item.organization_id === null ? t("customerStructure.unassigned") : t("customerStructure.reassignment")}`} />
              </ListItemButton>
            ))}
            {!filteredAssignableClients.length && <EmptyState text={t("customerStructure.noAssignableClients")} />}
          </Paper>
          <TextField fullWidth required multiline minRows={2} margin="normal" label={t("customerStructure.bulkAssignmentReason")} value={bulkReason} onChange={(event) => setBulkReason(event.target.value)} helperText={t("customerStructure.bulkAssignmentReasonHelp")} />
          {linkClients.isError && <Alert severity="error">{apiErrorMessage(linkClients.error, t("customerStructure.bulkAssignFailed"))}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeLinkDialog}>{t("common.cancel", { defaultValue: "Cancel" })}</Button>
          <Button variant="contained" disabled={!clientsToLink.length || bulkReason.trim().length < 5 || linkClients.isPending} onClick={() => linkClients.mutate()}>{t("customerStructure.assignSelected", { count: clientsToLink.length })}</Button>
        </DialogActions>
      </Dialog>

      <Drawer anchor="right" open={policyScope !== null} onClose={() => setPolicyScope(null)} PaperProps={{ sx: { width: { xs: "100%", sm: 560 }, p: 2.5 } }}>
        <Stack spacing={2}>
          <Box><Typography variant="overline" color="primary">{policyScope?.type}</Typography><Typography variant="h6" fontWeight={800}>{policyScope?.name}</Typography><Typography color="text.secondary" variant="body2">{t("customerStructure.policyHelp")}</Typography></Box>
          {policy.isLoading && <CircularProgress />}
          {policy.isError && <Alert severity="error">{apiErrorMessage(policy.error, t("customerStructure.policyLoadFailed"))}</Alert>}
          {policy.data && <>
            <TextField select label={t("customerStructure.policyMode")} value={mode} onChange={(event) => { setMode(event.target.value as PolicyResponse["mode"]); setImpact(null); }} disabled={!canManage}><MenuItem value="INHERIT">{t("customerStructure.inherit")}</MenuItem><MenuItem value="EXTEND">{t("customerStructure.extend")}</MenuItem><MenuItem value="OVERRIDE">{t("customerStructure.override")}</MenuItem></TextField>
            {mode === "OVERRIDE" && <Alert severity="info">{t("customerStructure.overrideSafety")}</Alert>}
            <Box><Typography fontWeight={800} gutterBottom>{t("customerStructure.effectiveAccess")}</Typography><Stack spacing={1}>{policy.data.assignments.map((item) => <Paper key={`${item.department_id}-${item.source_type}`} variant="outlined" sx={{ p: 1.25, borderRadius: 2 }}><Stack direction="row" justifyContent="space-between" gap={1}><Box><Typography variant="body2" fontWeight={700}>{item.department_name}</Typography><Typography variant="caption" color="text.secondary">{item.relationship.replaceAll("_", " ")} · {item.access_profile.replaceAll("_", " ")}</Typography></Box><Stack direction="row" spacing={.5}><Chip size="small" label={item.source_type} variant="outlined" />{item.inherited && <Chip size="small" label={t("customerStructure.inherited")} />}{item.visibility_only && <Chip size="small" color="info" label={t("customerStructure.viewOnly")} />}</Stack></Stack></Paper>)}</Stack>{!policy.data.assignments.length && <Typography variant="body2" color="text.secondary">{t("customerStructure.noEffectiveAccess")}</Typography>}</Box>
            {canManage && <><Divider /><Stack direction="row" justifyContent="space-between" alignItems="center"><Typography fontWeight={800}>{t("customerStructure.directAssignments")}</Typography><Button size="small" startIcon={<Add />} onClick={() => setAssignments((current) => [...current, blankAssignment()])}>{t("customerStructure.addDepartment")}</Button></Stack>{assignments.map((item, index) => <Paper key={index} variant="outlined" sx={{ p: 1.5, borderRadius: 2 }}><Stack spacing={1.25}><TextField select size="small" label={t("customerStructure.department")} value={item.department_id} onChange={(event) => updateAssignment(index, { department_id: event.target.value })}>{departments.data?.map((department) => <MenuItem key={department.id} value={department.id}>{department.name} ({department.code})</MenuItem>)}</TextField><Stack direction={{ xs: "column", sm: "row" }} spacing={1}><TextField select fullWidth size="small" label={t("customerStructure.relationship")} value={item.relationship} onChange={(event) => updateAssignment(index, { relationship: event.target.value })}>{["PRIMARY_OWNER", "SHARED_OPERATOR", "VIEWER", "TEMPORARY_OPERATOR"].map((value) => <MenuItem key={value} value={value}>{value.replaceAll("_", " ")}</MenuItem>)}</TextField><TextField select fullWidth size="small" label={t("customerStructure.accessProfile")} value={item.access_profile} onChange={(event) => updateAssignment(index, { access_profile: event.target.value })}>{["CUSTOMER_VIEWER", "PROJECT_OPERATOR", "IMPLEMENTATION_OPERATOR", "SUPPORT_OPERATOR", "CUSTOMER_MANAGER", "PORTFOLIO_MANAGER"].map((value) => <MenuItem key={value} value={value}>{value.replaceAll("_", " ")}</MenuItem>)}</TextField></Stack><Stack direction={{ xs: "column", sm: "row" }} spacing={1}><TextField fullWidth size="small" type="datetime-local" label={t("customerStructure.starts")} InputLabelProps={{ shrink: true }} value={item.effective_from} onChange={(event) => updateAssignment(index, { effective_from: event.target.value })} /><TextField fullWidth size="small" type="datetime-local" label={t("customerStructure.ends")} InputLabelProps={{ shrink: true }} value={item.effective_until} onChange={(event) => updateAssignment(index, { effective_until: event.target.value })} /></Stack><TextField size="small" label={t("customerStructure.assignmentReason")} value={item.reason} onChange={(event) => updateAssignment(index, { reason: event.target.value })} /><Button color="error" size="small" onClick={() => setAssignments((current) => current.filter((_, itemIndex) => itemIndex !== index))}>{t("common.remove", { defaultValue: "Remove" })}</Button></Stack></Paper>)}<TextField label={t("customerStructure.changeReason")} required multiline minRows={2} value={changeReason} onChange={(event) => setChangeReason(event.target.value)} />{impact && <Alert severity="info">{t("customerStructure.impactSummary", { clients: impact.affected_client_count, branches: impact.affected_branch_count, added: impact.added_department_ids.length, retained: impact.retained_visibility_department_ids.length })}</Alert>}{(previewPolicy.isError || savePolicy.isError) && <Alert severity="error">{apiErrorMessage(previewPolicy.error ?? savePolicy.error)}</Alert>}<Stack direction="row" spacing={1} justifyContent="flex-end"><Button onClick={() => setPolicyScope(null)}>{t("common.cancel", { defaultValue: "Cancel" })}</Button><Button variant="outlined" disabled={changeReason.trim().length < 5 || assignments.some((item) => !item.department_id) || previewPolicy.isPending} onClick={() => previewPolicy.mutate()}>{t("customerStructure.previewImpact")}</Button><Button variant="contained" disabled={!impact || changeReason.trim().length < 5 || savePolicy.isPending} onClick={() => savePolicy.mutate()}>{t("customerStructure.savePolicy")}</Button></Stack></>}
          </>}
        </Stack>
      </Drawer>
      <Snackbar open={Boolean(notice)} autoHideDuration={3500} onClose={() => setNotice("")} message={notice} />
    </Stack>
  );
}

function StructureColumn({ title, icon, action, children }: { title: string; icon: React.ReactNode; action?: React.ReactNode; children: React.ReactNode }) {
  return <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 3, minHeight: 260 }}><Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}><Stack direction="row" spacing={1} alignItems="center">{icon}<Typography fontWeight={800}>{title}</Typography></Stack>{action}</Stack><Divider sx={{ mb: 1 }} />{children}</Paper>;
}

function EmptyState({ text }: { text: string }) {
  return <Box sx={{ py: 4, px: 2, textAlign: "center" }}><Typography variant="body2" color="text.secondary">{text}</Typography></Box>;
}

function CreateDialog({ open, title, pending, error, onClose, onSubmit, legalName = false }: { open: boolean; title: string; pending: boolean; error: unknown; onClose: () => void; onSubmit: (data: Record<string, unknown>) => void; legalName?: boolean }) {
  const { t } = useTranslation();
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    onSubmit({ ...data, code: String(data.code).trim().toUpperCase(), name: String(data.name).trim(), legal_name: legalName ? String(data.legal_name || "").trim() || null : undefined });
  };
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm"><Box component="form" onSubmit={submit}><DialogTitle>{title}</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><TextField name="code" label={t("customerStructure.code")} required inputProps={{ pattern: "[A-Za-z0-9_-]+" }} /><TextField name="name" label={t("customerStructure.name")} required />{legalName && <TextField name="legal_name" label={t("customerStructure.legalName")} />}<TextField name="description" label={t("customerStructure.description")} multiline minRows={2} />{Boolean(error) && <Alert severity="error">{apiErrorMessage(error)}</Alert>}</Stack></DialogContent><DialogActions><Button onClick={onClose}>{t("common.cancel", { defaultValue: "Cancel" })}</Button><Button type="submit" variant="contained" disabled={pending}>{t("common.save", { defaultValue: "Save" })}</Button></DialogActions></Box></Dialog>;
}
