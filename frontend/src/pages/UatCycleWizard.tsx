import { Alert, Autocomplete, Button, Checkbox, FormControlLabel, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMemo, useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type Template = { id: number; name: string; current_version: number; test_case_ids: number[]; client_ids: number[]; scope_type: string; client_id: number | null; product_id: number | null; is_active: boolean }
type Person = { id: number; name: string; user_type: string; client_ids?: number[]; department?: string | null }
type Metadata = { clients: { id: number; name: string }[]; contracts: { id: number; client_id: number; name: string }[]; products: { id: number; name: string }[]; users: Person[] }
type Draft = {
  client_id: number; contract_id: number | null; release_version: string; coordinator_user_id: number;
  engineer_user_ids: number[]; coordinator_user_ids: number[]; client_tester_user_ids: number[]; template_ids: number[]; test_case_ids: number[];
  start_date: string | null; due_date: string | null; portal_visible: boolean; allow_client_testing: boolean;
  allow_client_pass: boolean; allow_client_fail: boolean; allow_client_blocked: boolean; allow_client_comments: boolean;
  allow_client_attachments: boolean; allow_client_create_ticket_from_failure: boolean; allow_client_view_linked_ticket: boolean;
  allow_client_signoff: boolean; client_approver_user_id: number | null; client_coordinator_user_id: number | null;
}
const emptyDraft = (currentUserId: number): Draft => ({
  client_id: 0, contract_id: null, release_version: '', coordinator_user_id: currentUserId,
  engineer_user_ids: [], coordinator_user_ids: [], client_tester_user_ids: [], template_ids: [], test_case_ids: [], start_date: null, due_date: null,
  portal_visible: true, allow_client_testing: true, allow_client_pass: true, allow_client_fail: true,
  allow_client_blocked: true, allow_client_comments: true, allow_client_attachments: true,
  allow_client_create_ticket_from_failure: true, allow_client_view_linked_ticket: true,
  allow_client_signoff: false, client_approver_user_id: null, client_coordinator_user_id: null,
})

export function UatCycleWizard({ templates, metadata, currentUserId, onCreated }: { templates: Template[]; metadata: Metadata; currentUserId: number; onCreated: (id: number) => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState<Draft>(emptyDraft(currentUserId))
  const employees = metadata.users.filter((person) => person.user_type === 'EMPLOYEE')
  const supportUsers = employees.filter((person) => person.department?.toLowerCase().includes('support'))
  const portalUsers = metadata.users.filter((person) => person.user_type === 'CLIENT_PORTAL' && person.client_ids?.includes(draft.client_id))
  const available = useMemo(() => templates.filter((item) => item.is_active && (
    (item.scope_type === 'GLOBAL' && (!item.client_ids.length || item.client_ids.includes(draft.client_id)))
    || (item.scope_type !== 'GLOBAL' && (item.client_id === draft.client_id || item.client_ids.includes(draft.client_id)))
  )), [templates, draft.client_id])
  const selected = available.filter((item) => draft.template_ids.includes(item.id))
  const clientName = metadata.clients.find((item) => item.id === draft.client_id)?.name ?? ''
  const generatedName = clientName && selected.length ? `${clientName} - ${selected.map((item) => item.name).join(' + ')}` : ''
  const testCount = new Set(selected.flatMap((item) => item.test_case_ids)).size
  const valid = Boolean(draft.client_id && draft.template_ids.length && draft.release_version.trim() && draft.coordinator_user_id && draft.client_tester_user_ids.length && draft.coordinator_user_ids.length)
  const create = async () => {
    setBusy(true); setError('')
    try {
      const response = await api.post<{ id: number }>('/uat/cycles', draft)
      await api.post(`/uat/cycles/${response.data.id}/activate`)
      await onCreated(response.data.id)
      setOpen(false); setDraft(emptyDraft(currentUserId))
    } catch (cause) { setError(apiErrorMessage(cause, 'Could not create the UAT.')) }
    finally { setBusy(false) }
  }
  if (!open) return <Button variant="contained" sx={{ alignSelf: 'flex-start' }} onClick={() => setOpen(true)}>Create New UAT</Button>
  return <Paper sx={{ p: { xs: 2, md: 2.5 } }}><Stack spacing={2}>
    <Stack direction="row" justifyContent="space-between" alignItems="center"><div><Typography variant="h6" fontWeight={800}>Create New UAT</Typography><Typography variant="body2" color="text.secondary">Select the client, templates and delivery team, then create and launch.</Typography></div><Button onClick={() => setOpen(false)}>Close</Button></Stack>
    {error && <Alert severity="error">{error}</Alert>}
    <Stack direction={{ xs: 'column', md: 'row' }} gap={1.5}>
      <TextField fullWidth select required label="Client" value={draft.client_id || ''} onChange={(event) => setDraft({ ...draft, client_id: Number(event.target.value), contract_id: null, template_ids: [], client_tester_user_ids: [], client_approver_user_id: null, client_coordinator_user_id: null, allow_client_signoff: false })}>{metadata.clients.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField fullWidth select label="Contract" value={draft.contract_id ?? ''} onChange={(event) => setDraft({ ...draft, contract_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">No contract</MenuItem>{metadata.contracts.filter((item) => item.client_id === draft.client_id).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField fullWidth required label="Release Version" value={draft.release_version} onChange={(event) => setDraft({ ...draft, release_version: event.target.value })} />
    </Stack>
    <Autocomplete multiple options={available} value={selected} getOptionLabel={(item) => `${item.name} · v${item.current_version} · ${item.test_case_ids.length} tests`} isOptionEqualToValue={(left, right) => left.id === right.id} onChange={(_, value) => setDraft({ ...draft, template_ids: value.map((item) => item.id) })} renderInput={(params) => <TextField {...params} required label="Templates" helperText={draft.client_id ? 'Select one or more templates. Each template keeps its own product.' : 'Select a client first.'} />} disabled={!draft.client_id} />
    {draft.client_id && !available.length && <Alert severity="warning">No active templates are available for this client. Create or assign a template from Setup.</Alert>}
    <Stack direction={{ xs: 'column', md: 'row' }} gap={1.5}>
      <TextField fullWidth label="UAT Name" value={generatedName} slotProps={{ input: { readOnly: true } }} helperText="Generated from the client and selected template names" />
      <TextField fullWidth label="UAT Code" value="Generated when created" slotProps={{ input: { readOnly: true } }} />
    </Stack>
    <TextField select required label="UAT Owner" value={draft.coordinator_user_id || ''} onChange={(event) => setDraft({ ...draft, coordinator_user_id: Number(event.target.value) })}>{employees.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
    <Autocomplete multiple options={employees} value={employees.filter((person) => draft.engineer_user_ids.includes(person.id))} getOptionLabel={(person) => person.name} isOptionEqualToValue={(left, right) => left.id === right.id} onChange={(_, value) => setDraft({ ...draft, engineer_user_ids: value.map((person) => person.id) })} renderInput={(params) => <TextField {...params} label="Internal engineers" helperText="Optional. Internal test ownership is distributed across them; otherwise the UAT owner is used." />} />
    <Autocomplete multiple options={portalUsers} value={portalUsers.filter((person) => draft.client_tester_user_ids.includes(person.id))} getOptionLabel={(person) => person.name} isOptionEqualToValue={(left, right) => left.id === right.id} onChange={(_, value) => setDraft({ ...draft, client_tester_user_ids: value.map((person) => person.id) })} renderInput={(params) => <TextField {...params} required label="Client engineers" helperText={draft.client_id ? 'Tests are distributed across these client portal contacts.' : 'Select a client first.'} />} disabled={!draft.client_id} />
    <Autocomplete multiple options={supportUsers} value={supportUsers.filter((person) => draft.coordinator_user_ids.includes(person.id))} getOptionLabel={(person) => `${person.name} · ${person.department ?? 'Support'}`} isOptionEqualToValue={(left, right) => left.id === right.id} onChange={(_, value) => setDraft({ ...draft, coordinator_user_ids: value.map((person) => person.id) })} renderInput={(params) => <TextField {...params} required label="UAT Coordinators" helperText="Only active users in the Support department are available." />} />
    <Stack direction={{ xs: 'column', md: 'row' }} gap={1.5}><TextField fullWidth type="date" label="Start Date" InputLabelProps={{ shrink: true }} value={draft.start_date ?? ''} onChange={(event) => setDraft({ ...draft, start_date: event.target.value || null })} /><TextField fullWidth type="date" label="Due Date" InputLabelProps={{ shrink: true }} value={draft.due_date ?? ''} onChange={(event) => setDraft({ ...draft, due_date: event.target.value || null })} /></Stack>
    <Paper variant="outlined" sx={{ p: 1.5 }}><Typography fontWeight={750}>Client participation</Typography><Stack direction={{ xs: 'column', md: 'row' }} gap={1.5} mt={1}><TextField fullWidth select label="Client coordinator" value={draft.client_coordinator_user_id ?? ''} onChange={(event) => setDraft({ ...draft, client_coordinator_user_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">Unassigned</MenuItem>{portalUsers.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField fullWidth select label="Client sign-off approver" value={draft.client_approver_user_id ?? ''} onChange={(event) => setDraft({ ...draft, client_approver_user_id: event.target.value ? Number(event.target.value) : null, allow_client_signoff: Boolean(event.target.value) })}><MenuItem value="">Configure later</MenuItem>{portalUsers.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField></Stack><FormControlLabel control={<Checkbox checked={draft.portal_visible} onChange={(event) => setDraft({ ...draft, portal_visible: event.target.checked, allow_client_testing: event.target.checked })} />} label="Publish to the client portal immediately" /></Paper>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1}><Typography color="text.secondary">{selected.length} template(s) · {testCount} unique tests</Typography><Stack direction="row" gap={1}><Button onClick={() => setOpen(false)}>Cancel</Button><Button variant="contained" disabled={!valid || busy} onClick={create}>{busy ? 'Creating…' : 'Create and Launch UAT'}</Button></Stack></Stack>
  </Stack></Paper>
}
