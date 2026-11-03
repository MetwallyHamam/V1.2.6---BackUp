import { Alert, Button, FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type Settings = { portal_visible: boolean; allow_client_testing: boolean; allow_client_pass: boolean; allow_client_fail: boolean; allow_client_blocked: boolean; allow_client_view_linked_ticket: boolean; allow_client_signoff: boolean; allow_client_comments: boolean; allow_client_attachments: boolean; allow_client_create_ticket_from_failure: boolean; client_approver_user_id: number | null; client_coordinator_user_id: number | null; client_access_start_at: string | null; client_access_end_at: string | null }
type Cycle = { id: number; client_id: number; status: string; portal_settings: Settings; tests: { id: number; snapshot: { title: string }; client_tester_user_id: number | null; client_test_result: string; client_workflow_status: string }[] }
type User = { id: number; name: string; user_type: string; client_ids: number[] }

export function UatPortalSettings({ cycle, users, canManage, onSaved }: { cycle: Cycle; users: User[]; canManage: boolean; onSaved: () => Promise<void> }) {
  const [settings, setSettings] = useState(cycle.portal_settings)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => setSettings(cycle.portal_settings), [cycle])
  const run = async (work: () => Promise<unknown>) => { setBusy(true); setError(''); try { await work(); await onSaved() } catch (cause) { setError(apiErrorMessage(cause, 'Could not save client UAT access.')) } finally { setBusy(false) } }
  const portalUsers = users.filter((person) => person.user_type === 'CLIENT_PORTAL' && person.client_ids.includes(cycle.client_id))
  return <Stack spacing={2}>
    {error && <Alert severity="error">{error}</Alert>}
    <Paper sx={{ p: 2 }}><Typography variant="h6">Publication and permissions</Typography><Typography variant="body2" color="text.secondary">Only assigned users for this client can see tests. Publishing requires an active cycle.</Typography>
      <Stack direction="row" flexWrap="wrap" gap={1}>
        {(['portal_visible', 'allow_client_testing', 'allow_client_pass', 'allow_client_fail', 'allow_client_blocked', 'allow_client_signoff', 'allow_client_comments', 'allow_client_attachments', 'allow_client_view_linked_ticket', 'allow_client_create_ticket_from_failure'] as const).map((field) => <FormControlLabel key={field} control={<Switch disabled={!canManage} checked={settings[field]} onChange={(event) => setSettings({ ...settings, [field]: event.target.checked })} />} label={field.replaceAll('_', ' ')} />)}
      </Stack>
      <TextField select label="Client approver" sx={{ minWidth: 240, my: 1 }} value={settings.client_approver_user_id ?? ''} disabled={!canManage} onChange={(event) => setSettings({ ...settings, client_approver_user_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">Unassigned</MenuItem>{portalUsers.map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField>
      <TextField select label="Client UAT coordinator" sx={{ minWidth: 240, my: 1, ml: 1 }} value={settings.client_coordinator_user_id ?? ''} disabled={!canManage} onChange={(event) => setSettings({ ...settings, client_coordinator_user_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">Unassigned</MenuItem>{portalUsers.map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField>
      <Stack direction={{ xs: 'column', md: 'row' }} gap={1} sx={{ my: 1 }}><TextField label="Access starts" type="datetime-local" slotProps={{ inputLabel: { shrink: true } }} value={settings.client_access_start_at?.slice(0, 16) ?? ''} onChange={(event) => setSettings({ ...settings, client_access_start_at: event.target.value || null })} disabled={!canManage} /><TextField label="Access ends" type="datetime-local" slotProps={{ inputLabel: { shrink: true } }} value={settings.client_access_end_at?.slice(0, 16) ?? ''} onChange={(event) => setSettings({ ...settings, client_access_end_at: event.target.value || null })} disabled={!canManage} /></Stack>
      {canManage && <Button variant="contained" disabled={busy || (settings.portal_visible && cycle.status === 'DRAFT')} onClick={() => run(() => api.put(`/uat/cycles/${cycle.id}/portal-settings`, settings))}>Save portal settings</Button>}
    </Paper>
    <Paper sx={{ p: 2 }}><Typography variant="h6">Assigned client tests</Typography>{cycle.tests.map((test) => <Stack key={test.id} direction={{ xs: 'column', md: 'row' }} gap={1} alignItems={{ md: 'center' }} sx={{ my: 1 }}><Typography sx={{ flex: 1 }}>{test.snapshot.title} · {test.client_test_result}</Typography><TextField select size="small" label="Client tester" sx={{ minWidth: 220 }} value={test.client_tester_user_id ?? ''} disabled={!canManage || busy || cycle.status === 'COMPLETED'} onChange={(event) => run(() => api.put(`/uat/cycle-tests/${test.id}/client-tester`, { user_id: event.target.value ? Number(event.target.value) : null }))}><MenuItem value="">Unassigned</MenuItem>{portalUsers.map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField>{test.client_workflow_status === 'BLOCKED' && canManage && <Button disabled={busy} onClick={() => run(() => api.post(`/uat/cycle-tests/${test.id}/client-unblock`))}>Unblock</Button>}</Stack>)}</Paper>
  </Stack>
}
