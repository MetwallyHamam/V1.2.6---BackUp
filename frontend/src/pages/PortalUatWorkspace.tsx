import { TableRows, ViewKanban } from '@mui/icons-material'
import { alpha, lighten } from '@mui/material/styles'
import { Box, Chip, Menu, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material'
import { useMemo, useState } from 'react'

export type PortalWorkspaceTest = {
  id: number
  snapshot: { code: string; title: string; priority?: string }
  client_test_result: string
  client_workflow_status: string
  client_attempt_count: number
  linked_ticket: { id: number; ticket_number: string } | null
  assigned_to_me: boolean
}

type PortalWorkspaceCycle = {
  allow_client_testing: boolean
  allow_client_pass: boolean
  allow_client_fail: boolean
  allow_client_blocked: boolean
  client_signoff_current: boolean
}

const lanes = [
  { key: 'READY', label: 'Ready', color: '#64748b' },
  { key: 'IN_PROGRESS', label: 'In testing', color: '#2563eb' },
  { key: 'NEEDS_INVESTIGATION', label: 'Needs investigation', color: '#dc2626' },
  { key: 'WAITING_FIX', label: 'Waiting fix', color: '#9333ea' },
  { key: 'READY_FOR_RETEST', label: 'Ready for retest', color: '#0891b2' },
  { key: 'COMPLETED', label: 'Passed', color: '#16a34a' },
  { key: 'BLOCKED', label: 'Blocked', color: '#ea580c' },
]
const resultColors: Record<string, string> = { PASS: '#16a34a', FAIL: '#dc2626', BLOCKED: '#ea580c', NOT_TESTED: '#64748b' }
const priorityColors: Record<string, string> = { CRITICAL: '#b91c1c', HIGH: '#dc2626', MEDIUM: '#d97706', LOW: '#0284c7' }

function laneMeta(status: string) {
  return lanes.find((lane) => lane.key === status) ?? { key: status, label: status.replaceAll('_', ' '), color: '#64748b' }
}

function savedLayout(): 'board' | 'list' {
  try {
    return typeof window.localStorage?.getItem === 'function' && window.localStorage.getItem('portal-uat-layout') === 'list' ? 'list' : 'board'
  } catch {
    return 'board'
  }
}

function saveLayout(value: 'board' | 'list') {
  try {
    if (typeof window.localStorage?.setItem === 'function') window.localStorage.setItem('portal-uat-layout', value)
  } catch {
    // Storage can be disabled by managed-browser policy; the workspace must still function.
  }
}

function ColorChip({ label, color }: { label: string; color: string }) {
  return <Chip size="small" label={label.replaceAll('_', ' ')} sx={(theme) => {
    const foreground = theme.palette.mode === 'dark' ? lighten(color, .38) : color
    return { bgcolor: alpha(color, theme.palette.mode === 'dark' ? .24 : .13), color: foreground, border: `1px solid ${alpha(foreground, .48)}`, fontWeight: 800 }
  }} />
}

export function PortalUatWorkspace({ cycle, tests, selectedId, moving, onMove, onOpen }: {
  cycle: PortalWorkspaceCycle
  tests: PortalWorkspaceTest[]
  selectedId: number | null
  moving: boolean
  onMove: (testId: number, workflowStatus: 'READY' | 'IN_PROGRESS') => void
  onOpen: (test: PortalWorkspaceTest, result?: 'PASS' | 'FAIL' | 'BLOCKED') => void
}) {
  const [mode, setMode] = useState<'board' | 'list'>(savedLayout)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('ALL')
  const [context, setContext] = useState<{ mouseX: number; mouseY: number; test: PortalWorkspaceTest } | null>(null)
  const [dragged, setDragged] = useState<PortalWorkspaceTest | null>(null)
  const [dropLane, setDropLane] = useState<string | null>(null)
  const filtered = useMemo(() => tests.filter((test) => {
    const query = search.trim().toLowerCase()
    return (!query || `${test.snapshot.code} ${test.snapshot.title} ${test.linked_ticket?.ticket_number ?? ''}`.toLowerCase().includes(query)) && (status === 'ALL' || test.client_workflow_status === status || (status === 'FAIL' && test.client_test_result === 'FAIL'))
  }), [tests, search, status])
  const canRecord = (test: PortalWorkspaceTest, result: 'PASS' | 'FAIL' | 'BLOCKED') => test.assigned_to_me && cycle.allow_client_testing && !cycle.client_signoff_current && cycle[`allow_client_${result.toLowerCase()}` as 'allow_client_pass']
  const canDrag = (test: PortalWorkspaceTest) => test.assigned_to_me && cycle.allow_client_testing && !cycle.client_signoff_current && ['READY', 'IN_PROGRESS', 'READY_FOR_RETEST'].includes(test.client_workflow_status)
  const drop = (lane: string) => {
    const test = dragged
    setDragged(null)
    setDropLane(null)
    if (!test || test.client_workflow_status === lane) return
    if (lane === 'READY' || lane === 'IN_PROGRESS') onMove(test.id, lane)
    else if (lane === 'COMPLETED' && canRecord(test, 'PASS')) onOpen(test, 'PASS')
    else if (lane === 'NEEDS_INVESTIGATION' && canRecord(test, 'FAIL')) onOpen(test, 'FAIL')
    else if (lane === 'BLOCKED' && canRecord(test, 'BLOCKED')) onOpen(test, 'BLOCKED')
  }
  const action = (test: PortalWorkspaceTest, value: string) => {
    if (value === 'READY' || value === 'IN_PROGRESS') onMove(test.id, value)
    else onOpen(test, value === 'OPEN' ? undefined : value as 'PASS' | 'FAIL' | 'BLOCKED')
  }
  const statusActions = (test: PortalWorkspaceTest) => {
    if (!canDrag(test)) return []
    if (test.client_workflow_status === 'IN_PROGRESS') return [{ value: 'READY', label: 'Move to ready' }]
    return [{ value: 'IN_PROGRESS', label: test.client_workflow_status === 'READY_FOR_RETEST' ? 'Start retest' : 'Start testing' }]
  }
  const actionMenu = (test: PortalWorkspaceTest) => <TextField select size="small" value="" label="Actions" disabled={moving} onClick={(event) => event.stopPropagation()} onMouseDown={(event) => event.stopPropagation()} onChange={(event) => { event.stopPropagation(); action(test, event.target.value) }} sx={{ minWidth: 145 }} SelectProps={{ displayEmpty: true }}><MenuItem value="OPEN">Open test</MenuItem>{statusActions(test).map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}{canRecord(test, 'PASS') && <MenuItem value="PASS">Record pass…</MenuItem>}{canRecord(test, 'FAIL') && <MenuItem value="FAIL">Record fail…</MenuItem>}{canRecord(test, 'BLOCKED') && <MenuItem value="BLOCKED">Record blocked…</MenuItem>}</TextField>

  return <Stack spacing={1.5} sx={{ mt: 2 }}>
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 3 }}><Stack direction={{ xs: 'column', md: 'row' }} gap={1.25} alignItems={{ md: 'center' }}>
      <ToggleButtonGroup exclusive size="small" value={mode} onChange={(_, value: 'board' | 'list' | null) => { if (!value) return; setMode(value); saveLayout(value) }}><ToggleButton value="board"><ViewKanban fontSize="small" sx={{ mr: .75 }} />Board</ToggleButton><ToggleButton value="list"><TableRows fontSize="small" sx={{ mr: .75 }} />List</ToggleButton></ToggleButtonGroup>
      <TextField size="small" label="Search scenarios or tickets" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ minWidth: 245 }} />
      <TextField select size="small" label="Status" value={status} onChange={(event) => setStatus(event.target.value)} sx={{ minWidth: 180 }}><MenuItem value="ALL">All statuses</MenuItem>{lanes.map((lane) => <MenuItem key={lane.key} value={lane.key}><Box component="span" sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: lane.color, display: 'inline-block', mr: 1 }} />{lane.label}</MenuItem>)}<MenuItem value="FAIL">Failed result</MenuItem></TextField>
      <Chip label={`${filtered.length} test${filtered.length === 1 ? '' : 's'}`} sx={{ ml: { md: 'auto' }, fontWeight: 800 }} />
    </Stack></Paper>
    {mode === 'board' ? <Box sx={{ display: 'flex', gap: 1.5, overflowX: 'auto', pb: 1.5, alignItems: 'flex-start' }}>{lanes.map((lane) => {
      const laneTests = filtered.filter((test) => test.client_workflow_status === lane.key)
      return <Paper key={lane.key} variant="outlined" onDragOver={(event) => { if (!dragged) return; event.preventDefault(); event.dataTransfer.dropEffect = 'move'; setDropLane(lane.key) }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDropLane(null) }} onDrop={(event) => { event.preventDefault(); drop(lane.key) }} sx={(theme) => ({ minWidth: 270, flex: '1 0 270px', bgcolor: dropLane === lane.key ? alpha(lane.color, theme.palette.mode === 'dark' ? .28 : .13) : theme.palette.mode === 'dark' ? alpha(lane.color, .12) : alpha(lane.color, .035), borderRadius: 3, overflow: 'hidden', borderColor: dropLane === lane.key ? lighten(lane.color, theme.palette.mode === 'dark' ? .25 : 0) : alpha(lane.color, theme.palette.mode === 'dark' ? .55 : .25), outline: dropLane === lane.key ? `2px dashed ${lighten(lane.color, theme.palette.mode === 'dark' ? .25 : 0)}` : 'none', outlineOffset: -4 })}><Stack direction="row" alignItems="center" gap={1} sx={(theme) => ({ px: 1.5, py: 1.25, borderTop: `4px solid ${lane.color}`, bgcolor: alpha(lane.color, theme.palette.mode === 'dark' ? .22 : .08) })}><Box sx={{ width: 9, height: 9, borderRadius: '50%', bgcolor: lane.color }} /><Typography fontWeight={850} flex={1}>{lane.label}</Typography><Chip size="small" label={laneTests.length} sx={(theme) => ({ bgcolor: alpha(lane.color, theme.palette.mode === 'dark' ? .3 : .14), color: theme.palette.mode === 'dark' ? lighten(lane.color, .42) : lane.color, border: '1px solid', borderColor: alpha(lane.color, theme.palette.mode === 'dark' ? .6 : .25), fontWeight: 900 })} /></Stack><Stack spacing={1.25} sx={{ p: 1.25, minHeight: 105 }}>{laneTests.map((test) => <Paper key={test.id} elevation={0} draggable={canDrag(test) && !moving} onDragStart={(event) => { event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('text/plain', String(test.id)); setDragged(test) }} onDragEnd={() => { setDragged(null); setDropLane(null) }} onClick={() => onOpen(test)} onContextMenu={(event) => { event.preventDefault(); setContext({ mouseX: event.clientX + 2, mouseY: event.clientY - 6, test }) }} aria-label={`${test.snapshot.code} UAT test card${canDrag(test) ? '; drag to change status' : ''}`} sx={(theme) => ({ p: 1.5, bgcolor: theme.palette.mode === 'dark' ? alpha(theme.palette.background.paper, .96) : 'background.paper', color: 'text.primary', cursor: canDrag(test) ? 'grab' : 'pointer', opacity: dragged?.id === test.id ? .55 : 1, border: '1px solid', borderColor: selectedId === test.id ? (theme.palette.mode === 'dark' ? lighten(lane.color, .25) : lane.color) : 'divider', borderLeft: `4px solid ${lane.color}`, borderRadius: 2, transition: 'transform .15s ease, box-shadow .15s ease', '&:hover': { transform: 'translateY(-2px)', borderColor: theme.palette.mode === 'dark' ? alpha(lighten(lane.color, .3), .8) : lane.color, boxShadow: theme.shadows[4] }, '&:active': { cursor: canDrag(test) ? 'grabbing' : 'pointer' } })}><Stack direction="row" justifyContent="space-between" gap={1}><Typography variant="caption" fontWeight={850} color="primary.main">{test.snapshot.code}</Typography>{test.snapshot.priority && <ColorChip label={test.snapshot.priority} color={priorityColors[test.snapshot.priority] ?? '#64748b'} />}</Stack><Typography fontWeight={800} sx={{ mt: .75, lineHeight: 1.35 }}>{test.snapshot.title}</Typography><Stack direction="row" gap={.75} flexWrap="wrap" sx={{ mt: 1 }}><ColorChip label={test.client_test_result} color={resultColors[test.client_test_result] ?? resultColors.NOT_TESTED} />{test.client_attempt_count > 0 && <Chip size="small" variant="outlined" label={`${test.client_attempt_count} attempt${test.client_attempt_count === 1 ? '' : 's'}`} />}</Stack>{test.linked_ticket && <Typography variant="caption" color="primary.main" fontWeight={750} display="block" sx={{ mt: 1 }}>Ticket · {test.linked_ticket.ticket_number}</Typography>}<Box sx={{ mt: 1.25 }}>{actionMenu(test)}</Box></Paper>)}</Stack></Paper>
    })}</Box> : <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden' }}><Table size="small"><TableHead sx={{ bgcolor: 'action.hover' }}><TableRow>{['Test', 'Scenario', 'Status', 'Result', 'Attempts', 'Ticket', 'Action'].map((label) => <TableCell key={label} sx={{ fontWeight: 850, color: 'text.secondary', whiteSpace: 'nowrap' }}>{label}</TableCell>)}</TableRow></TableHead><TableBody>{filtered.map((test) => { const lane = laneMeta(test.client_workflow_status); return <TableRow key={test.id} hover selected={selectedId === test.id} onClick={() => onOpen(test)} onContextMenu={(event) => { event.preventDefault(); setContext({ mouseX: event.clientX + 2, mouseY: event.clientY - 6, test }) }} sx={{ cursor: 'pointer', borderLeft: `4px solid ${lane.color}`, '&:hover': { bgcolor: alpha(lane.color, .055) } }}><TableCell><Typography variant="body2" fontWeight={850} color="primary.main">{test.snapshot.code}</Typography></TableCell><TableCell><Typography variant="body2" fontWeight={750}>{test.snapshot.title}</Typography></TableCell><TableCell><ColorChip label={lane.label} color={lane.color} /></TableCell><TableCell><ColorChip label={test.client_test_result} color={resultColors[test.client_test_result] ?? resultColors.NOT_TESTED} /></TableCell><TableCell align="center">{test.client_attempt_count}</TableCell><TableCell>{test.linked_ticket?.ticket_number ?? '—'}</TableCell><TableCell>{actionMenu(test)}</TableCell></TableRow> })}</TableBody></Table></TableContainer>}
    <Menu open={context !== null} onClose={() => setContext(null)} anchorReference="anchorPosition" anchorPosition={context ? { top: context.mouseY, left: context.mouseX } : undefined}>{context ? [<MenuItem key="OPEN" onClick={() => { action(context.test, 'OPEN'); setContext(null) }}>Open test case</MenuItem>, ...statusActions(context.test).map((item) => <MenuItem key={item.value} onClick={() => { action(context.test, item.value); setContext(null) }}>{item.label}</MenuItem>), ...(['PASS', 'FAIL', 'BLOCKED'] as const).filter((value) => canRecord(context.test, value)).map((value) => <MenuItem key={value} onClick={() => { action(context.test, value); setContext(null) }}>Record {value.toLowerCase()}…</MenuItem>)] : null}</Menu>
  </Stack>
}
