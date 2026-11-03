import { Autocomplete, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, TextField } from '@mui/material'
import { useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type Person = { id: number; name: string; user_type: string; client_ids?: number[]; department?: string | null }
type Cycle = {
  id: number; client_id: number; release_version: string; status: string; coordinator_user_id: number;
  engineer_user_ids: number[]; coordinator_user_ids: number[]; client_tester_user_ids: number[];
  start_date: string | null; due_date: string | null; description?: string | null;
  portal_settings: { portal_visible: boolean; allow_client_testing: boolean; allow_client_pass: boolean; allow_client_fail: boolean; allow_client_blocked: boolean; allow_client_comments: boolean; allow_client_attachments: boolean; allow_client_create_ticket_from_failure: boolean; allow_client_view_linked_ticket: boolean; allow_client_signoff: boolean; client_approver_user_id: number | null; client_coordinator_user_id: number | null };
}

export function UatCycleEditor({ cycle, users, onSaved }: { cycle: Cycle; users: Person[]; onSaved: () => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState(() => ({
    release_version: cycle.release_version, coordinator_user_id: cycle.coordinator_user_id,
    engineer_user_ids: cycle.engineer_user_ids, coordinator_user_ids: cycle.coordinator_user_ids,
    client_tester_user_ids: cycle.client_tester_user_ids, start_date: cycle.start_date, due_date: cycle.due_date,
    description: cycle.description ?? '', ...cycle.portal_settings,
  }))
  const employees = users.filter((person) => person.user_type === 'EMPLOYEE')
  const supportUsers = employees.filter((person) => person.department?.toLowerCase().includes('support'))
  const clientUsers = users.filter((person) => person.user_type === 'CLIENT_PORTAL' && person.client_ids?.includes(cycle.client_id))
  const save = async () => {
    setBusy(true); setError('')
    try { await api.put(`/uat/cycles/${cycle.id}`, draft); await onSaved(); setOpen(false) }
    catch (cause) { setError(apiErrorMessage(cause, 'Could not update the UAT.')) }
    finally { setBusy(false) }
  }
  return <>
    <Button variant="outlined" onClick={() => setOpen(true)}>Edit UAT</Button>
    <Dialog open={open} onClose={() => !busy && setOpen(false)} fullWidth maxWidth="md">
      <DialogTitle>Edit UAT</DialogTitle>
      <DialogContent><Stack spacing={1.5} sx={{ pt: 1 }}>
        {error && <TextField value={error} error slotProps={{ input: { readOnly: true } }} />}
        <Stack direction={{ xs: 'column', sm: 'row' }} gap={1.5}><TextField required fullWidth label="Release Version" value={draft.release_version} onChange={(event) => setDraft({ ...draft, release_version: event.target.value })} /><TextField required select fullWidth label="UAT Owner" value={draft.coordinator_user_id} onChange={(event) => setDraft({ ...draft, coordinator_user_id: Number(event.target.value) })}>{employees.map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField></Stack>
        <Autocomplete multiple options={employees} value={employees.filter((person) => draft.engineer_user_ids.includes(person.id))} getOptionLabel={(person) => person.name} isOptionEqualToValue={(a, b) => a.id === b.id} onChange={(_, value) => setDraft({ ...draft, engineer_user_ids: value.map((person) => person.id) })} renderInput={(params) => <TextField {...params} label="Internal engineers" helperText="Internal test ownership is distributed across these engineers; the UAT owner is used when empty." />} />
        <Autocomplete multiple options={clientUsers} value={clientUsers.filter((person) => draft.client_tester_user_ids.includes(person.id))} getOptionLabel={(person) => person.name} isOptionEqualToValue={(a, b) => a.id === b.id} onChange={(_, value) => setDraft({ ...draft, client_tester_user_ids: value.map((person) => person.id) })} renderInput={(params) => <TextField {...params} label="Client engineers" helperText="Portal tests are redistributed across these client contacts." />} />
        <Autocomplete multiple options={supportUsers} value={supportUsers.filter((person) => draft.coordinator_user_ids.includes(person.id))} getOptionLabel={(person) => person.name} isOptionEqualToValue={(a, b) => a.id === b.id} onChange={(_, value) => setDraft({ ...draft, coordinator_user_ids: value.map((person) => person.id) })} renderInput={(params) => <TextField {...params} label="UAT coordinators" helperText="Only Support-department users are available." />} />
        <Stack direction={{ xs: 'column', sm: 'row' }} gap={1.5}><TextField fullWidth type="date" label="Start Date" InputLabelProps={{ shrink: true }} value={draft.start_date ?? ''} onChange={(event) => setDraft({ ...draft, start_date: event.target.value || null })} /><TextField fullWidth type="date" label="Due Date" InputLabelProps={{ shrink: true }} value={draft.due_date ?? ''} onChange={(event) => setDraft({ ...draft, due_date: event.target.value || null })} /></Stack>
        <TextField multiline minRows={2} label="Description" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} />
        <Stack direction={{ xs: 'column', sm: 'row' }} gap={1.5}><TextField fullWidth select label="Client coordinator" value={draft.client_coordinator_user_id ?? ''} onChange={(event) => setDraft({ ...draft, client_coordinator_user_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">Unassigned</MenuItem>{clientUsers.map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField><TextField fullWidth select label="Client sign-off approver" value={draft.client_approver_user_id ?? ''} onChange={(event) => setDraft({ ...draft, client_approver_user_id: event.target.value ? Number(event.target.value) : null, allow_client_signoff: Boolean(event.target.value) })}><MenuItem value="">Unassigned</MenuItem>{clientUsers.map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField></Stack>
        <Stack direction="row" flexWrap="wrap" gap={.5}>
          <FormControlLabel control={<Checkbox checked={draft.portal_visible} onChange={(event) => setDraft({ ...draft, portal_visible: event.target.checked })} />} label="Visible in client portal" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_testing} onChange={(event) => setDraft({ ...draft, allow_client_testing: event.target.checked })} />} label="Client testing" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_pass} onChange={(event) => setDraft({ ...draft, allow_client_pass: event.target.checked })} />} label="Allow pass" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_fail} onChange={(event) => setDraft({ ...draft, allow_client_fail: event.target.checked })} />} label="Allow fail" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_blocked} onChange={(event) => setDraft({ ...draft, allow_client_blocked: event.target.checked })} />} label="Allow blocked" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_comments} onChange={(event) => setDraft({ ...draft, allow_client_comments: event.target.checked })} />} label="Comments" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_attachments} onChange={(event) => setDraft({ ...draft, allow_client_attachments: event.target.checked })} />} label="Attachments" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_create_ticket_from_failure} onChange={(event) => setDraft({ ...draft, allow_client_create_ticket_from_failure: event.target.checked })} />} label="Client defect tickets" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_view_linked_ticket} onChange={(event) => setDraft({ ...draft, allow_client_view_linked_ticket: event.target.checked })} />} label="View linked tickets" />
          <FormControlLabel control={<Checkbox checked={draft.allow_client_signoff} disabled={!draft.client_approver_user_id} onChange={(event) => setDraft({ ...draft, allow_client_signoff: event.target.checked })} />} label="Client sign-off" />
        </Stack>
      </Stack></DialogContent>
      <DialogActions><Button onClick={() => setOpen(false)} disabled={busy}>Cancel</Button><Button variant="contained" onClick={save} disabled={busy || !draft.release_version.trim() || !draft.coordinator_user_id}>{busy ? 'Saving…' : 'Save changes'}</Button></DialogActions>
    </Dialog>
  </>
}
