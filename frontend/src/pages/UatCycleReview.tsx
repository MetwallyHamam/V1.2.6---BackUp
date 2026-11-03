import { Alert, Box, Button, Chip, CircularProgress, FormControlLabel, Menu, MenuItem, Paper, Stack, Switch, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material'
import { ArrowDownward, ArrowUpward, TableRows, ViewKanban } from '@mui/icons-material'
import { alpha } from '@mui/material/styles'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type ReviewTest = { id: number; display_order: number; snapshot: { code: string; title: string; priority: string; product_id?: number | null; module_id?: number | null; feature_name?: string | null; expected_result?: string }; priority: string; due_date: string | null; workflow_status: string; test_result: string; retest_count: number; linked_ticket_number: string | null; owner_user_id: number | null }
type Metrics = { total: number; completed: number; completion_percent: number; passed: number; failed: number; blocked: number; not_tested: number; overdue: number; pass_rate: number; critical_failures: number; waiting_retest: number; open_defects: number }
type Dashboard = { metrics: Metrics; by_status: Record<string, number>; by_module: Record<string, Record<string, number>>; by_owner: Record<string, Record<string, number>>; failures_by_severity: Record<string, number>; failures_by_category: Record<string, number>; progress_by_date: Record<string, Record<string, number>> }
type SortKey = 'template_order' | 'code' | 'title' | 'priority' | 'status' | 'due_date'
type SavedView = { id: number; name: string; filters: { search: string; status: string; my_tests: boolean; result?: string; priority?: string; due?: string; product_id?: number | null; module_id?: number | null; sort: SortKey | 'code' | 'priority' | 'status'; direction?: 'asc' | 'desc' } }
const columns = [
  { key: 'READY', label: 'Ready', color: '#64748b' }, { key: 'IN_PROGRESS', label: 'In testing', color: '#2563eb' },
  { key: 'NEEDS_INVESTIGATION', label: 'Needs investigation', color: '#dc2626' }, { key: 'WAITING_FIX', label: 'Waiting fix', color: '#9333ea' }, { key: 'READY_FOR_RETEST', label: 'Ready for retest', color: '#0891b2' },
  { key: 'COMPLETED', label: 'Passed', color: '#16a34a' }, { key: 'BLOCKED', label: 'Blocked', color: '#ea580c' },
]
const resultColors: Record<string, string> = { PASS: '#2e7d32', FAIL: '#d32f2f', BLOCKED: '#ed6c02', NOT_TESTED: '#90a4ae' }
const priorityColors: Record<string, string> = { CRITICAL: '#b91c1c', HIGH: '#dc2626', MEDIUM: '#d97706', LOW: '#0284c7' }
const priorityRank: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }
const workflowRank = Object.fromEntries(columns.map((column, index) => [column.key, index]))

export function orderUatTests(tests: ReviewTest[], sort: SortKey, direction: 'asc' | 'desc', sourceOrder: Map<number, number>) {
  const factor = direction === 'asc' ? 1 : -1
  return [...tests].sort((a, b) => {
    let comparison = 0
    if (sort === 'template_order') comparison = (sourceOrder.get(a.id) ?? 0) - (sourceOrder.get(b.id) ?? 0)
    else if (sort === 'priority') comparison = (priorityRank[a.priority] ?? 99) - (priorityRank[b.priority] ?? 99)
    else if (sort === 'status') comparison = (workflowRank[a.workflow_status] ?? 99) - (workflowRank[b.workflow_status] ?? 99)
    else if (sort === 'due_date') comparison = (a.due_date ?? '9999-12-31').localeCompare(b.due_date ?? '9999-12-31')
    else if (sort === 'title') comparison = a.snapshot.title.localeCompare(b.snapshot.title, undefined, { numeric: true })
    else comparison = a.snapshot.code.localeCompare(b.snapshot.code, undefined, { numeric: true })
    return comparison * factor || (sourceOrder.get(a.id) ?? 0) - (sourceOrder.get(b.id) ?? 0)
  })
}

function workflowMeta(status: string) {
  return columns.find((column) => column.key === status) ?? { key: status, label: status.replaceAll('_', ' '), color: '#64748b' }
}

function StatusChip({ status }: { status: string }) {
  const meta = workflowMeta(status)
  return <Chip size="small" label={meta.label} sx={{ bgcolor: alpha(meta.color, 0.13), color: meta.color, border: `1px solid ${alpha(meta.color, 0.28)}`, fontWeight: 800 }} />
}

function ResultChip({ result }: { result: string }) {
  const color = resultColors[result] ?? resultColors.NOT_TESTED
  return <Chip size="small" label={result.replaceAll('_', ' ')} sx={{ bgcolor: alpha(color, 0.13), color, fontWeight: 800 }} />
}

function Breakdown({ title, rows }: { title: string; rows: Record<string, Record<string, number>> }) {
  const entries = Object.entries(rows).sort((a, b) => Object.values(b[1]).reduce((x, y) => x + y, 0) - Object.values(a[1]).reduce((x, y) => x + y, 0))
  return <Paper sx={{ p: 2, flex: '1 1 270px' }}><Typography variant="subtitle1" fontWeight={700}>{title}</Typography>{entries.length === 0 && <Typography color="text.secondary">No tests yet</Typography>}{entries.map(([name, values]) => {
    const total = Object.values(values).reduce((sum, value) => sum + value, 0)
    return <Box key={name} sx={{ mt: 1 }}><Stack direction="row" justifyContent="space-between"><Typography variant="body2">{name}</Typography><Typography variant="body2">{total}</Typography></Stack><Box sx={{ display: 'flex', height: 10, borderRadius: 1, overflow: 'hidden', bgcolor: 'action.hover' }}>{Object.entries(values).map(([result, count]) => count > 0 && <Box key={result} title={`${result}: ${count}`} sx={{ width: `${count * 100 / total}%`, bgcolor: resultColors[result] ?? '#90a4ae' }} />)}</Box></Box>
  })}</Paper>
}

function CountBars({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1])
  const maximum = Math.max(1, ...entries.map(([, value]) => value))
  return <Paper sx={{ p: 2, flex: '1 1 220px' }}><Typography variant="subtitle1" fontWeight={700}>{title}</Typography>{entries.length === 0 && <Typography color="text.secondary">No data yet</Typography>}{entries.map(([name, count]) => <Box key={name} sx={{ mt: 1 }}><Stack direction="row" justifyContent="space-between"><Typography variant="body2">{name.replaceAll('_', ' ')}</Typography><Typography variant="body2">{count}</Typography></Stack><Box sx={{ height: 9, bgcolor: 'action.hover', borderRadius: 1 }}><Box sx={{ height: '100%', width: `${count * 100 / maximum}%`, bgcolor: name === 'CRITICAL' ? 'error.main' : 'primary.main', borderRadius: 1 }} /></Box></Box>)}</Paper>
}

function ProgressTrend({ values }: { values: Record<string, Record<string, number>> }) {
  const days = Object.entries(values).sort((a, b) => a[0].localeCompare(b[0])).slice(-14)
  const maximum = Math.max(1, ...days.map(([, counts]) => (counts.PASS ?? 0) + (counts.FAIL ?? 0) + (counts.BLOCKED ?? 0)))
  return <Paper sx={{ p: 2 }}><Typography variant="subtitle1" fontWeight={700}>Attempts over time</Typography>{days.length === 0 && <Typography color="text.secondary">No attempts yet</Typography>}<Stack direction="row" gap={1} alignItems="flex-end" sx={{ minHeight: 115, overflowX: 'auto' }}>{days.map(([day, counts]) => <Stack key={day} alignItems="center" justifyContent="flex-end" sx={{ width: 48, flexShrink: 0, height: 115 }}><Stack direction="column-reverse" sx={{ width: 26, height: 82, justifyContent: 'flex-start' }}>{(['PASS', 'FAIL', 'BLOCKED'] as const).map((result) => <Box key={result} title={`${day} ${result}: ${counts[result] ?? 0}`} sx={{ height: `${(counts[result] ?? 0) * 82 / maximum}px`, bgcolor: resultColors[result] }} />)}</Stack><Typography variant="caption">{day.slice(5)}</Typography></Stack>)}</Stack><Typography variant="caption" color="text.secondary">Green pass · Red fail · Orange blocked · Retests are included in the day tested.</Typography></Paper>
}

export function UatCycleReview({ cycleId, tests, currentUserId, products, modules, canManage, onSelectTest, onQuickResult }: { cycleId: number; tests: ReviewTest[]; currentUserId: number | null; products: { id: number; name: string }[]; modules: { id: number; product_id: number; name: string }[]; canManage: boolean; onSelectTest: (id: number) => void; onQuickResult: (id: number, result: 'PASS' | 'FAIL' | 'BLOCKED') => void }) {
  const cache = useQueryClient()
  const [mode, setMode] = useState<'board' | 'list'>(() => window.localStorage.getItem('uat-test-layout') === 'list' ? 'list' : 'board')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('ALL')
  const [myTests, setMyTests] = useState(false)
  const [resultFilter, setResultFilter] = useState('ALL')
  const [priorityFilter, setPriorityFilter] = useState('ALL')
  const [dueFilter, setDueFilter] = useState('ALL')
  const [productId, setProductId] = useState<number | ''>('')
  const [moduleId, setModuleId] = useState<number | ''>('')
  const [page, setPage] = useState(0)
  const [sort, setSort] = useState<SortKey>('template_order')
  const [direction, setDirection] = useState<'asc' | 'desc'>('asc')
  const [viewName, setViewName] = useState('')
  const [savedViewId, setSavedViewId] = useState<number | ''>('')
  const [viewError, setViewError] = useState('')
  const [contextMenu, setContextMenu] = useState<{ mouseX: number; mouseY: number; test: ReviewTest } | null>(null)
  const views = useQuery({ queryKey: ['uat-saved-views'], queryFn: async () => (await api.get<SavedView[]>('/uat/saved-views')).data })
  const saveView = useMutation({ mutationFn: async () => api.post('/uat/saved-views', { name: viewName, filters: { search, status, my_tests: myTests, result: resultFilter, priority: priorityFilter, due: dueFilter, product_id: productId || null, module_id: moduleId || null, sort, direction } }), onSuccess: async () => { setViewName(''); setViewError(''); await cache.invalidateQueries({ queryKey: ['uat-saved-views'] }) }, onError: (cause) => setViewError(apiErrorMessage(cause, 'Could not save this view.')) })
  const deleteView = useMutation({ mutationFn: async () => api.delete(`/uat/saved-views/${savedViewId}`), onSuccess: async () => { setSavedViewId(''); setViewError(''); await cache.invalidateQueries({ queryKey: ['uat-saved-views'] }) }, onError: (cause) => setViewError(apiErrorMessage(cause, 'Could not delete this view.')) })
  const moveTest = useMutation({ mutationFn: async ({ testId, workflowStatus }: { testId: number; workflowStatus: string }) => api.put(`/uat/cycle-tests/${testId}/workflow`, { workflow_status: workflowStatus }), onSuccess: async () => { setViewError(''); await cache.invalidateQueries({ queryKey: ['uat-cycles'] }); await cache.invalidateQueries({ queryKey: ['uat-dashboard', cycleId] }) }, onError: (cause) => setViewError(apiErrorMessage(cause, 'This workflow move is not allowed.')) })
  const reorderTests = useMutation({ mutationFn: async (testIds: number[]) => api.put(`/uat/cycles/${cycleId}/test-order`, { test_ids: testIds }), onSuccess: async () => { setSort('template_order'); setDirection('asc'); setViewError(''); await cache.invalidateQueries({ queryKey: ['uat-cycles'] }) }, onError: (cause) => setViewError(apiErrorMessage(cause, 'Could not save the test order.')) })
  const dashboard = useQuery({ queryKey: ['uat-dashboard', cycleId], queryFn: async () => (await api.get<Dashboard>(`/uat/cycles/${cycleId}/dashboard`)).data })
  const sourceOrder = useMemo(() => new Map([...tests].sort((a, b) => a.display_order - b.display_order || a.id - b.id).map((test, index) => [test.id, index])), [tests])
  const filtered = useMemo(() => orderUatTests(tests.filter((test) => {
    const query = search.trim().toLowerCase()
    const today = new Date().toISOString().slice(0, 10)
    return (!query || `${test.snapshot.code} ${test.snapshot.title} ${test.snapshot.feature_name ?? ''} ${test.snapshot.expected_result ?? ''} ${test.linked_ticket_number ?? ''}`.toLowerCase().includes(query))
      && (status === 'ALL' || test.workflow_status === status || (status === 'FAILED' && test.test_result === 'FAIL') || (status === 'OVERDUE' && !!test.due_date && test.due_date < today && test.test_result !== 'PASS'))
      && (resultFilter === 'ALL' || test.test_result === resultFilter)
      && (priorityFilter === 'ALL' || test.priority === priorityFilter)
      && (dueFilter === 'ALL' || (dueFilter === 'OVERDUE' && !!test.due_date && test.due_date < today && test.test_result !== 'PASS') || (dueFilter === 'TODAY' && test.due_date === today) || (dueFilter === 'NO_DUE_DATE' && !test.due_date))
      && (!productId || test.snapshot.product_id === productId)
      && (!moduleId || test.snapshot.module_id === moduleId)
      && (!myTests || test.owner_user_id === currentUserId)
  }), sort, direction, sourceOrder), [tests, search, status, resultFilter, priorityFilter, dueFilter, productId, moduleId, myTests, currentUserId, sort, direction, sourceOrder])
  const clearFilters = () => { setSearch(''); setStatus('ALL'); setResultFilter('ALL'); setPriorityFilter('ALL'); setDueFilter('ALL'); setProductId(''); setModuleId(''); setMyTests(false); setSort('template_order'); setDirection('asc'); setSavedViewId(''); setPage(0) }
  const moveInOrder = (testId: number, offset: -1 | 1) => {
    const ordered = [...tests].sort((a, b) => (sourceOrder.get(a.id) ?? 0) - (sourceOrder.get(b.id) ?? 0))
    const index = ordered.findIndex((test) => test.id === testId)
    const target = index + offset
    if (index < 0 || target < 0 || target >= ordered.length) return
    ;[ordered[index], ordered[target]] = [ordered[target], ordered[index]]
    reorderTests.mutate(ordered.map((test) => test.id))
  }
  const metrics = dashboard.data?.metrics
  const chooseAction = (test: ReviewTest, value: string) => {
    if (value === 'OPEN') onSelectTest(test.id)
    else if (value === 'READY' || value === 'IN_PROGRESS') moveTest.mutate({ testId: test.id, workflowStatus: value })
    else onQuickResult(test.id, value as 'PASS' | 'FAIL' | 'BLOCKED')
  }
  const statusMenu = (test: ReviewTest) => <TextField select size="small" value="" label="Status" onClick={(event) => event.stopPropagation()} onChange={(event) => { event.stopPropagation(); chooseAction(test, event.target.value) }} sx={{ minWidth: 140 }}><MenuItem value="OPEN">Open details</MenuItem><MenuItem value="READY">Ready</MenuItem><MenuItem value="IN_PROGRESS">In testing</MenuItem><MenuItem value="PASS">Pass…</MenuItem><MenuItem value="FAIL">Fail…</MenuItem><MenuItem value="BLOCKED">Blocked…</MenuItem></TextField>
  const metricCards: { label: string; value: string | number; filter?: string }[] = metrics ? [
    { label: 'Total tests', value: metrics.total }, { label: 'Completed', value: metrics.completed },
    { label: 'Completion', value: `${metrics.completion_percent}%` }, { label: 'Passed', value: metrics.passed, filter: 'COMPLETED' },
    { label: 'Failed', value: metrics.failed, filter: 'WAITING_FIX' }, { label: 'Blocked', value: metrics.blocked, filter: 'BLOCKED' },
    { label: 'Not tested', value: metrics.not_tested }, { label: 'Overdue', value: metrics.overdue },
    { label: 'Pass rate', value: `${metrics.pass_rate}%` }, { label: 'Critical failures', value: metrics.critical_failures },
    { label: 'Ready for retest', value: metrics.waiting_retest, filter: 'READY_FOR_RETEST' }, { label: 'Open defects', value: metrics.open_defects },
  ] : []
  return <Stack spacing={2} sx={{ mt: 2 }}>
    {viewError && <Alert severity="error">{viewError}</Alert>}
    <Stack direction={{ xs: 'column', md: 'row' }} gap={1}><TextField select size="small" label="Saved view" value={savedViewId} onChange={(event) => { const id = Number(event.target.value); setSavedViewId(id); const view = views.data?.find((item) => item.id === id); if (view) { setSearch(view.filters.search); setStatus(view.filters.status); setMyTests(view.filters.my_tests); setResultFilter(view.filters.result ?? 'ALL'); setPriorityFilter(view.filters.priority ?? 'ALL'); setDueFilter(view.filters.due ?? 'ALL'); setProductId(view.filters.product_id ?? ''); setModuleId(view.filters.module_id ?? ''); setSort(view.filters.sort === 'code' || view.filters.sort === 'priority' || view.filters.sort === 'status' ? view.filters.sort : view.filters.sort ?? 'template_order'); setDirection(view.filters.direction ?? 'asc'); setPage(0) } }} sx={{ minWidth: 170 }}><MenuItem value="">Choose view</MenuItem>{views.data?.map((view) => <MenuItem key={view.id} value={view.id}>{view.name}</MenuItem>)}</TextField><TextField size="small" label="New view name" value={viewName} onChange={(event) => setViewName(event.target.value)} /><Button disabled={!viewName.trim() || saveView.isPending} onClick={() => saveView.mutate()}>Save filters</Button><Button color="error" disabled={!savedViewId || deleteView.isPending} onClick={() => deleteView.mutate()}>Delete view</Button></Stack>
    {dashboard.isLoading && <CircularProgress size={26} />}{dashboard.isError && <Alert severity="error">Cycle analysis could not be loaded. <Button onClick={() => dashboard.refetch()}>Retry</Button></Alert>}
    <Stack direction="row" flexWrap="wrap" gap={1}>{metricCards.map((card) => <Paper key={card.label} component={card.filter ? 'button' : 'div'} onClick={card.filter ? () => { setStatus(card.filter ?? 'ALL'); setMode('list'); setPage(0) } : undefined} sx={{ p: 1.5, minWidth: 112, flex: '1 1 112px', textAlign: 'left', border: 0, cursor: card.filter ? 'pointer' : 'default', bgcolor: 'background.paper' }}><Typography variant="caption" color="text.secondary">{card.label}</Typography><Typography variant="h6" fontWeight={800}>{card.value}</Typography></Paper>)}</Stack>
    {dashboard.data && <><Stack direction={{ xs: 'column', md: 'row' }} gap={1}><CountBars title="Tests by status" values={dashboard.data.by_status} /><Breakdown title="Results by module" rows={dashboard.data.by_module} /><Breakdown title="Results by owner" rows={dashboard.data.by_owner} /><CountBars title="Failure severity" values={dashboard.data.failures_by_severity} /><CountBars title="Failure category" values={dashboard.data.failures_by_category} /></Stack><ProgressTrend values={dashboard.data.progress_by_date} /></>}
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 3 }}>
      <Stack direction="row" gap={1.25} alignItems="center" flexWrap="wrap">
        <ToggleButtonGroup exclusive size="small" value={mode} onChange={(_, value) => { if (!value) return; setMode(value); window.localStorage.setItem('uat-test-layout', value) }}>
          <ToggleButton value="board"><ViewKanban fontSize="small" sx={{ mr: .75 }} />Board</ToggleButton>
          <ToggleButton value="list"><TableRows fontSize="small" sx={{ mr: .75 }} />List</ToggleButton>
        </ToggleButtonGroup>
        <TextField size="small" label="Search tests or ticket" value={search} onChange={(event) => { setSearch(event.target.value); setPage(0) }} sx={{ minWidth: 240 }} />
        <TextField select size="small" label="Status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(0) }} sx={{ minWidth: 175 }}><MenuItem value="ALL">All statuses</MenuItem>{columns.map((column) => <MenuItem key={column.key} value={column.key}><Box component="span" sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: column.color, display: 'inline-block', mr: 1 }} />{column.label}</MenuItem>)}<MenuItem value="FAILED">Failed result</MenuItem><MenuItem value="OVERDUE">Overdue</MenuItem></TextField>
        <TextField select size="small" label="Result" value={resultFilter} onChange={(event) => { setResultFilter(event.target.value); setPage(0) }} sx={{ minWidth: 145 }}><MenuItem value="ALL">All results</MenuItem>{['NOT_TESTED', 'PASS', 'FAIL', 'BLOCKED'].map((value) => <MenuItem key={value} value={value}>{value.replaceAll('_', ' ')}</MenuItem>)}</TextField>
        <TextField select size="small" label="Priority" value={priorityFilter} onChange={(event) => { setPriorityFilter(event.target.value); setPage(0) }} sx={{ minWidth: 135 }}><MenuItem value="ALL">All priorities</MenuItem>{['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField>
        <TextField select size="small" label="Due" value={dueFilter} onChange={(event) => { setDueFilter(event.target.value); setPage(0) }} sx={{ minWidth: 145 }}><MenuItem value="ALL">Any due date</MenuItem><MenuItem value="OVERDUE">Overdue</MenuItem><MenuItem value="TODAY">Due today</MenuItem><MenuItem value="NO_DUE_DATE">No due date</MenuItem></TextField>
        <TextField select size="small" label="Product" value={productId} onChange={(event) => { setProductId(event.target.value ? Number(event.target.value) : ''); setModuleId(''); setPage(0) }} sx={{ minWidth: 155 }}><MenuItem value="">All products</MenuItem>{products.filter((product) => tests.some((test) => test.snapshot.product_id === product.id)).map((product) => <MenuItem key={product.id} value={product.id}>{product.name}</MenuItem>)}</TextField>
        <TextField select size="small" label="Module" value={moduleId} onChange={(event) => { setModuleId(event.target.value ? Number(event.target.value) : ''); setPage(0) }} sx={{ minWidth: 155 }}><MenuItem value="">All modules</MenuItem>{modules.filter((module) => (!productId || module.product_id === productId) && tests.some((test) => test.snapshot.module_id === module.id)).map((module) => <MenuItem key={module.id} value={module.id}>{module.name}</MenuItem>)}</TextField>
        <TextField select size="small" label="Order by" value={sort} onChange={(event) => { setSort(event.target.value as SortKey); setPage(0) }} sx={{ minWidth: 155 }}><MenuItem value="template_order">Template order</MenuItem><MenuItem value="code">Code</MenuItem><MenuItem value="title">Scenario</MenuItem><MenuItem value="priority">Priority</MenuItem><MenuItem value="status">Status</MenuItem><MenuItem value="due_date">Due date</MenuItem></TextField>
        <TextField select size="small" label="Direction" value={direction} onChange={(event) => { setDirection(event.target.value as 'asc' | 'desc'); setPage(0) }} sx={{ minWidth: 125 }}><MenuItem value="asc">Ascending</MenuItem><MenuItem value="desc">Descending</MenuItem></TextField>
        <FormControlLabel control={<Switch checked={myTests} onChange={(event) => { setMyTests(event.target.checked); setPage(0) }} />} label="My tests" />
        <Button onClick={clearFilters}>Reset</Button>
        <Typography variant="caption" color="text.secondary" sx={{ ml: { md: 'auto' } }}>{filtered.length} of {tests.length} tests</Typography>
      </Stack>
    </Paper>
    {mode === 'board' ? <Box sx={{ display: 'flex', gap: 1.5, overflowX: 'auto', pb: 1.5, alignItems: 'flex-start' }}>
      {columns.map((column) => {
        const laneTests = filtered.filter((test) => test.workflow_status === column.key)
        return <Paper key={column.key} variant="outlined" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); const testId = Number(event.dataTransfer.getData('text/uat-test-id')); if (!testId) return; if (!['READY', 'IN_PROGRESS'].includes(column.key)) { onSelectTest(testId); setViewError('Open the test details to record Pass, Fail, or Blocked. Waiting-for-fix and retest stages follow the linked ticket workflow.'); return } moveTest.mutate({ testId, workflowStatus: column.key }) }} sx={{ minWidth: 270, flex: '1 0 270px', bgcolor: alpha(column.color, .035), borderRadius: 3, overflow: 'hidden', borderColor: alpha(column.color, .25) }}>
          <Stack direction="row" alignItems="center" gap={1} sx={{ px: 1.5, py: 1.25, borderTop: `4px solid ${column.color}`, bgcolor: alpha(column.color, .08) }}><Box sx={{ width: 9, height: 9, borderRadius: '50%', bgcolor: column.color }} /><Typography fontWeight={850} flex={1}>{column.label}</Typography><Chip size="small" label={laneTests.length} sx={{ bgcolor: alpha(column.color, .14), color: column.color, fontWeight: 900 }} /></Stack>
          <Stack spacing={1.25} sx={{ p: 1.25, minHeight: 110 }}>{laneTests.map((test) => <Paper key={test.id} draggable onDragStart={(event) => event.dataTransfer.setData('text/uat-test-id', String(test.id))} onContextMenu={(event) => { event.preventDefault(); setContextMenu({ mouseX: event.clientX + 2, mouseY: event.clientY - 6, test }) }} onClick={() => onSelectTest(test.id)} elevation={0} sx={{ p: 1.5, cursor: 'grab', border: '1px solid', borderColor: 'divider', borderLeft: `4px solid ${column.color}`, borderRadius: 2, transition: 'transform .15s ease, box-shadow .15s ease, border-color .15s ease', '&:hover': { transform: 'translateY(-2px)', boxShadow: 4, borderColor: alpha(column.color, .55) }, '&:active': { cursor: 'grabbing' } }}>
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}><Typography variant="caption" fontWeight={800} color="primary.main">#{(sourceOrder.get(test.id) ?? 0) + 1} · {test.snapshot.code}</Typography><Chip size="small" label={test.priority} sx={{ height: 21, bgcolor: alpha(priorityColors[test.priority] ?? '#64748b', .12), color: priorityColors[test.priority] ?? '#64748b', fontWeight: 800 }} /></Stack>
            <Typography fontWeight={800} sx={{ mt: .75, lineHeight: 1.35 }}>{test.snapshot.title}</Typography>
            <Stack direction="row" gap={.75} flexWrap="wrap" sx={{ mt: 1 }}><ResultChip result={test.test_result} />{test.retest_count > 0 && <Chip size="small" variant="outlined" label={`${test.retest_count} retest${test.retest_count === 1 ? '' : 's'}`} />}</Stack>
            {test.linked_ticket_number && <Typography variant="caption" color="primary.main" fontWeight={700} display="block" sx={{ mt: 1 }}>Ticket · {test.linked_ticket_number}</Typography>}
            <Box sx={{ mt: 1.25 }}>{statusMenu(test)}</Box>
          </Paper>)}</Stack>
        </Paper>
      })}
    </Box> : <><TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden' }}><Table size="small"><TableHead sx={{ bgcolor: 'action.hover' }}><TableRow>{['Order', 'Code', 'Scenario', 'Priority', 'Status', 'Quick action', 'Result', 'Retests', 'Ticket'].map((label) => <TableCell key={label} sx={{ fontWeight: 850, color: 'text.secondary', whiteSpace: 'nowrap' }}>{label}</TableCell>)}</TableRow></TableHead><TableBody>{filtered.slice(page * 20, page * 20 + 20).map((test) => { const meta = workflowMeta(test.workflow_status); const position = sourceOrder.get(test.id) ?? 0; return <TableRow key={test.id} hover onClick={() => onSelectTest(test.id)} onContextMenu={(event) => { event.preventDefault(); setContextMenu({ mouseX: event.clientX + 2, mouseY: event.clientY - 6, test }) }} sx={{ cursor: 'pointer', borderLeft: `4px solid ${meta.color}`, '&:hover': { bgcolor: alpha(meta.color, .055) } }}><TableCell><Stack direction="row" alignItems="center" gap={.25}><Typography variant="body2" fontWeight={850} sx={{ minWidth: 22 }}>{position + 1}</Typography>{canManage && <><Button size="small" aria-label={`Move ${test.snapshot.code} up`} disabled={position === 0 || reorderTests.isPending} onClick={(event) => { event.stopPropagation(); moveInOrder(test.id, -1) }} sx={{ minWidth: 28, p: .25 }}><ArrowUpward fontSize="small" /></Button><Button size="small" aria-label={`Move ${test.snapshot.code} down`} disabled={position === tests.length - 1 || reorderTests.isPending} onClick={(event) => { event.stopPropagation(); moveInOrder(test.id, 1) }} sx={{ minWidth: 28, p: .25 }}><ArrowDownward fontSize="small" /></Button></>}</Stack></TableCell><TableCell><Typography variant="body2" fontWeight={850} color="primary.main">{test.snapshot.code}</Typography></TableCell><TableCell><Typography variant="body2" fontWeight={750}>{test.snapshot.title}</Typography></TableCell><TableCell><Chip size="small" label={test.priority} sx={{ bgcolor: alpha(priorityColors[test.priority] ?? '#64748b', .12), color: priorityColors[test.priority] ?? '#64748b', fontWeight: 800 }} /></TableCell><TableCell><StatusChip status={test.workflow_status} /></TableCell><TableCell>{statusMenu(test)}</TableCell><TableCell><ResultChip result={test.test_result} /></TableCell><TableCell align="center">{test.retest_count}</TableCell><TableCell><Typography variant="body2" color={test.linked_ticket_number ? 'primary.main' : 'text.secondary'} fontWeight={test.linked_ticket_number ? 700 : 400}>{test.linked_ticket_number ?? '—'}</Typography></TableCell></TableRow> })}</TableBody></Table></TableContainer><Stack direction="row" gap={1} alignItems="center" justifyContent="flex-end"><Typography variant="caption" color="text.secondary">{filtered.length} tests</Typography><Button disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button><Typography fontWeight={800}>{page + 1}</Typography><Button disabled={(page + 1) * 20 >= filtered.length} onClick={() => setPage(page + 1)}>Next</Button></Stack></>}
    <Menu open={contextMenu !== null} onClose={() => setContextMenu(null)} anchorReference="anchorPosition" anchorPosition={contextMenu ? { top: contextMenu.mouseY, left: contextMenu.mouseX } : undefined}>{contextMenu && ['OPEN', 'READY', 'IN_PROGRESS', 'PASS', 'FAIL', 'BLOCKED'].map((value) => <MenuItem key={value} onClick={() => { chooseAction(contextMenu.test, value); setContextMenu(null) }}>{value === 'OPEN' ? 'Open test case' : value === 'IN_PROGRESS' ? 'Move to in testing' : value === 'READY' ? 'Move to ready' : `Record ${value.toLowerCase()}…`}</MenuItem>)}</Menu>
  </Stack>
}
