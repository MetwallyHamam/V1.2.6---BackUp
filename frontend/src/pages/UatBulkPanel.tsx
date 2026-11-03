import { Alert, Button, Checkbox, FormControlLabel, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type Test = { id: number; snapshot: { code: string; title: string }; workflow_status: string; priority: string; due_date: string | null }
type User = { id: number; name: string; user_type: string }

export function UatBulkPanel({ cycleId, tests, users, onSaved }: { cycleId: number; tests: Test[]; users: User[]; onSaved: () => Promise<void> }) {
  const [selected, setSelected] = useState<number[]>([])
  const [action, setAction] = useState<'ASSIGN_OWNER' | 'SET_DUE_DATE' | 'SET_PRIORITY' | 'MOVE_READY'>('ASSIGN_OWNER')
  const [owner, setOwner] = useState<number | ''>('')
  const [due, setDue] = useState('')
  const [priority, setPriority] = useState('MEDIUM')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async () => { setBusy(true); setError(''); try { await api.post(`/uat/cycles/${cycleId}/bulk-tests`, { test_ids: selected, action, owner_user_id: action === 'ASSIGN_OWNER' ? owner || null : null, due_date: action === 'SET_DUE_DATE' ? due || null : null, priority: action === 'SET_PRIORITY' ? priority : null }); setSelected([]); await onSaved() } catch (cause) { setError(apiErrorMessage(cause, 'Could not update the selected tests.')) } finally { setBusy(false) } }
  const exportSelected = () => {
    const csvCell = (value: string) => `"${(/^[=+@\-\t\r]/.test(value) ? `'${value}` : value).replaceAll('"', '""')}"`
    const rows = tests.filter((test) => selected.includes(test.id)).map((test) => [test.snapshot.code, test.snapshot.title, test.workflow_status, test.priority, test.due_date ?? ''])
    const csv = [['Code', 'Title', 'Workflow', 'Priority', 'Due date'], ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `uat-cycle-${cycleId}-selected-tests.csv`
    link.click()
    URL.revokeObjectURL(url)
  }
  return <Paper variant="outlined" sx={{ p: 2, mt: 2 }}><Typography variant="h6">Bulk test planning</Typography>{error && <Alert severity="error">{error}</Alert>}<Stack direction="row" gap={1}><Button size="small" onClick={() => setSelected(tests.map((test) => test.id))}>Select all</Button><Button size="small" onClick={() => setSelected([])}>Clear</Button><Button size="small" disabled={!selected.length} onClick={exportSelected}>Export selected CSV</Button></Stack><Stack direction="row" flexWrap="wrap" gap={1}>{tests.map((test) => <FormControlLabel key={test.id} control={<Checkbox checked={selected.includes(test.id)} onChange={(event) => setSelected(event.target.checked ? [...selected, test.id] : selected.filter((id) => id !== test.id))} />} label={`${test.snapshot.code} · ${test.snapshot.title}`} />)}</Stack><Stack direction={{ xs: 'column', md: 'row' }} gap={1} alignItems={{ md: 'center' }}><TextField select label="Action" value={action} onChange={(event) => setAction(event.target.value as typeof action)} sx={{ minWidth: 170 }}><MenuItem value="ASSIGN_OWNER">Assign owner</MenuItem><MenuItem value="SET_DUE_DATE">Set due date</MenuItem><MenuItem value="SET_PRIORITY">Set priority</MenuItem><MenuItem value="MOVE_READY">Move to ready</MenuItem></TextField>{action === 'ASSIGN_OWNER' && <TextField select label="Owner" value={owner} onChange={(event) => setOwner(Number(event.target.value))} sx={{ minWidth: 170 }}>{users.filter((person) => person.user_type === 'EMPLOYEE').map((person) => <MenuItem key={person.id} value={person.id}>{person.name}</MenuItem>)}</TextField>}{action === 'SET_DUE_DATE' && <TextField type="date" label="Due date" slotProps={{ inputLabel: { shrink: true } }} value={due} onChange={(event) => setDue(event.target.value)} />}{action === 'SET_PRIORITY' && <TextField select label="Priority" value={priority} onChange={(event) => setPriority(event.target.value)}>{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField>}<Button variant="contained" disabled={!selected.length || busy || (action === 'ASSIGN_OWNER' && !owner) || (action === 'SET_DUE_DATE' && !due)} onClick={submit}>Apply to {selected.length} tests</Button></Stack></Paper>
}
