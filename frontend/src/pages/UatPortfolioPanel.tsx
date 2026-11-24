import { Alert, Button, Chip, LinearProgress, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

export type PortfolioMetrics = { completion_percent: number; pass_rate: number; failed: number; critical_failures: number; open_defects: number; blocked: number }
export type PortfolioRow = { id: number; code: string; title: string; client_id: number; client_name: string; release_version: string; environment: string; status: string; coordinator_user_id: number; coordinator_name: string; due_date: string | null; due_state: string; metrics: PortfolioMetrics; client_total: number; client_passed: number; client_signoff: string; internal_signoff: string; attention: string[]; awaiting_client: boolean; ready_for_signoff: boolean; next_action: string; urgency_rank: number }
export type PortfolioFilters = { client: string; status: string; release: string; due: string; coordinator: string; attention: string }

export const EMPTY_PORTFOLIO_FILTERS: PortfolioFilters = { client: '', status: '', release: '', due: '', coordinator: '', attention: '' }

export function filterPortfolio(rows: PortfolioRow[], filters: PortfolioFilters) {
  return rows.filter((row) =>
    (!filters.client || String(row.client_id) === filters.client) &&
    (!filters.status || row.status === filters.status) &&
    (!filters.release || row.release_version === filters.release) &&
    (!filters.due || row.due_state === filters.due) &&
    (!filters.coordinator || String(row.coordinator_user_id) === filters.coordinator) &&
    (!filters.attention || row.attention.includes(filters.attention)))
}

const uniqueOptions = (rows: PortfolioRow[], key: 'client_name' | 'release_version' | 'coordinator_name') =>
  [...new Set(rows.map((row) => row[key]))].sort((a, b) => a.localeCompare(b))

export function UatPortfolioPanel({ onOpenCycle }: { onOpenCycle: (id: number) => void }) {
  const [error, setError] = useState('')
  const [presentation, setPresentation] = useState(false)
  const [filters, setFilters] = useState<PortfolioFilters>(EMPTY_PORTFOLIO_FILTERS)
  const portfolio = useQuery({ queryKey: ['uat-portfolio'], queryFn: async () => (await api.get<PortfolioRow[]>('/uat/portfolio')).data, refetchInterval: 60_000 })
  const download = async () => { try { const response = await api.get<Blob>('/uat/portfolio.csv', { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = 'uat-portfolio.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000) } catch (cause) { setError(apiErrorMessage(cause, 'Could not export the UAT portfolio.')) } }
  const rows = useMemo(() => portfolio.data ?? [], [portfolio.data])
  const visibleRows = useMemo(() => filterPortfolio(rows, filters), [rows, filters])
  const summary = [
    { label: 'Active', value: rows.filter((row) => row.status === 'ACTIVE').length },
    { label: 'Blocked', value: rows.filter((row) => row.status !== 'COMPLETED' && row.metrics.blocked > 0).length },
    { label: 'Awaiting client', value: rows.filter((row) => row.awaiting_client).length },
    { label: 'Ready for sign-off', value: rows.filter((row) => row.ready_for_signoff).length },
    { label: 'Completed', value: rows.filter((row) => row.status === 'COMPLETED').length },
  ]
  const attentionRows = rows.filter((row) => row.attention.length > 0 && row.status !== 'COMPLETED')
  const setFilter = (name: keyof PortfolioFilters, value: string) => setFilters((current) => ({ ...current, [name]: value }))
  const filterFields: { name: keyof PortfolioFilters; label: string; options: { value: string; label: string }[] }[] = [
    { name: 'client', label: 'Client', options: uniqueOptions(rows, 'client_name').map((label) => ({ label, value: String(rows.find((row) => row.client_name === label)?.client_id) })) },
    { name: 'status', label: 'Cycle status', options: [...new Set(rows.map((row) => row.status))].sort().map((value) => ({ value, label: value.replaceAll('_', ' ') })) },
    { name: 'release', label: 'Release', options: uniqueOptions(rows, 'release_version').map((value) => ({ value, label: value })) },
    { name: 'due', label: 'Due state', options: ['OVERDUE', 'DUE_SOON', 'ON_TRACK', 'NO_DUE_DATE'].map((value) => ({ value, label: value.replaceAll('_', ' ') })) },
    { name: 'coordinator', label: 'Coordinator', options: uniqueOptions(rows, 'coordinator_name').map((label) => ({ label, value: String(rows.find((row) => row.coordinator_name === label)?.coordinator_user_id) })) },
    { name: 'attention', label: 'Attention', options: [...new Set(rows.flatMap((row) => row.attention))].sort().map((value) => ({ value, label: value })) },
  ]
  return <Stack spacing={2} sx={presentation ? { position: 'fixed', inset: 0, zIndex: 1500, bgcolor: 'background.default', p: { xs: 2, md: 3 }, overflowY: 'auto' } : undefined}>
    {error && <Alert severity="error">{error}</Alert>}{portfolio.isError && <Alert severity="error">{apiErrorMessage(portfolio.error, 'Could not load the UAT portfolio.')}</Alert>}
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1} alignItems={{ sm: 'center' }}><Typography variant={presentation ? 'h4' : 'h6'}>UAT portfolio · priority work</Typography><Stack direction="row" gap={1} flexWrap="wrap"><Button variant="outlined" onClick={() => setPresentation(!presentation)}>{presentation ? 'Exit presentation' : 'Presentation mode'}</Button><Button variant="outlined" onClick={download}>Export CSV</Button></Stack></Stack>
    <Stack direction="row" gap={1} flexWrap="wrap">{summary.map((item) => <Paper key={item.label} variant="outlined" sx={{ p: 2, minWidth: 145, flex: '1 1 145px' }}><Typography variant="body2" color="text.secondary">{item.label}</Typography><Typography variant="h5" fontWeight={800}>{item.value}</Typography></Paper>)}</Stack>
    <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="h6">Needs attention</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Urgent cycles are ordered by overdue work, untracked failures, blockers, access, assignments, then sign-off.</Typography>{attentionRows.slice(0, 8).map((row) => <Stack key={row.id} direction={{ xs: 'column', md: 'row' }} gap={1} alignItems={{ md: 'center' }} sx={{ py: 0.75 }}><Button onClick={() => onOpenCycle(row.id)} sx={{ justifyContent: 'flex-start', minWidth: 220 }}>{row.code} · {row.client_name}</Button><Stack direction="row" gap={0.5} flexWrap="wrap">{row.attention.map((reason) => <Chip key={reason} size="small" label={reason} color={reason === 'Overdue tests' || reason === 'Failures without tickets' ? 'error' : 'warning'} />)}</Stack></Stack>)}{!attentionRows.length && <Alert severity="success">No active UAT cycles currently need attention.</Alert>}</Paper>
    <Paper variant="outlined" sx={{ p: 2 }}><Stack direction="row" justifyContent="space-between" alignItems="center" gap={1} sx={{ mb: 1 }}><Typography variant="h6">Cycles</Typography>{Object.values(filters).some(Boolean) && <Button size="small" onClick={() => setFilters(EMPTY_PORTFOLIO_FILTERS)}>Clear filters</Button>}</Stack><Stack direction="row" gap={1} flexWrap="wrap">{filterFields.map((field) => <TextField key={field.name} select size="small" label={field.label} value={filters[field.name]} onChange={(event) => setFilter(field.name, event.target.value)} sx={{ minWidth: 160, flex: '1 1 160px' }}><MenuItem value="">All</MenuItem>{field.options.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}</TextField>)}</Stack></Paper>
    <Stack spacing={1.5}>{visibleRows.map((row) => <Paper key={row.id} variant="outlined" sx={{ p: 2, borderLeft: 4, borderLeftColor: row.attention.length ? 'warning.main' : row.status === 'COMPLETED' ? 'success.main' : 'primary.main' }}><Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}><Stack spacing={0.75} sx={{ flex: 1, minWidth: 0 }}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography variant="h6">{row.code} · {row.title}</Typography><Chip size="small" label={row.status.replaceAll('_', ' ')} color={row.status === 'COMPLETED' ? 'success' : 'default'} /></Stack><Typography variant="body2" color="text.secondary">{row.client_name} · Release {row.release_version} · {row.environment} · Coordinator: {row.coordinator_name}</Typography><Stack direction="row" gap={1} flexWrap="wrap"><Typography variant="body2">Due: {row.due_date ?? 'Not set'}</Typography><Typography variant="body2">Open defects: {row.metrics.open_defects}</Typography><Typography variant="body2">Pass rate: {row.metrics.pass_rate}%</Typography></Stack><LinearProgress variant="determinate" value={row.metrics.completion_percent} aria-label={`${row.code} progress ${row.metrics.completion_percent}%`} sx={{ height: 8, borderRadius: 4 }} /><Typography variant="caption" color="text.secondary">{row.metrics.completion_percent}% complete</Typography>{row.attention.length > 0 && <Stack direction="row" gap={0.5} flexWrap="wrap">{row.attention.map((reason) => <Chip key={reason} size="small" variant="outlined" label={reason} color={reason === 'Overdue tests' || reason === 'Failures without tickets' ? 'error' : 'warning'} />)}</Stack>}</Stack><Button variant="contained" onClick={() => onOpenCycle(row.id)} sx={{ alignSelf: { xs: 'stretch', md: 'center' }, whiteSpace: 'nowrap' }}>{row.next_action}</Button></Stack></Paper>)}</Stack>
    {!visibleRows.length && !portfolio.isLoading && <Paper variant="outlined" sx={{ p: 3, textAlign: 'center' }}><Typography variant="h6">No UAT cycles match this view</Typography><Typography color="text.secondary" sx={{ mb: 1 }}>{rows.length ? 'Clear or adjust the filters to see other governed UAT work.' : 'Create a UAT cycle from Setup to begin planning client acceptance testing.'}</Typography>{rows.length > 0 && <Button onClick={() => setFilters(EMPTY_PORTFOLIO_FILTERS)}>Clear filters</Button>}</Paper>}
  </Stack>
}
