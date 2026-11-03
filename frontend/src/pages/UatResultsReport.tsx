import { Alert, Button, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../api/client'
import { useState } from 'react'

type Result = { test_id: number; code: string; title: string; priority: string; internal_owner: string; internal_result: string; internal_status: string; internal_attempts: number; client_tester: string; client_result: string; client_status: string; client_attempts: number; linked_ticket: string }
type Report = { code: string; title: string; tests: Result[]; by_priority: Record<string, number>; by_feature: Record<string, number>; summary: { total: number; internal_passed: number; internal_failed: number; internal_blocked: number; internal_unexecuted: number; internal_retests: number; client_assigned: number; client_passed: number; client_failed: number; client_blocked: number; client_unexecuted: number; client_retests: number; linked_defects: number } }

export function UatResultsReport({ cycleId }: { cycleId: number }) {
  const [error, setError] = useState('')
  const report = useQuery({ queryKey: ['uat-results-report', cycleId], queryFn: async () => (await api.get<Report>(`/uat/cycles/${cycleId}/results-report`)).data })
  const download = async (format: 'xlsx' | 'pdf') => {
    setError('')
    try {
      const response = await api.get(`/uat/cycles/${cycleId}/results-report.${format}`, { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `uat-cycle-${cycleId}-results.${format}`
      link.click()
      URL.revokeObjectURL(url)
    } catch (cause) { setError(apiErrorMessage(cause, 'Could not export the results.')) }
  }
  return <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
    <Stack direction="row" justifyContent="space-between" alignItems="center"><Typography variant="h6">Combined results report</Typography><Stack direction="row"><Button onClick={() => download('xlsx')}>Export Excel</Button><Button onClick={() => download('pdf')}>Export PDF</Button></Stack></Stack>
    {error && <Alert severity="error">{error}</Alert>}
    {report.isError && <Alert severity="error">Could not load the results report.</Alert>}
    {report.data && <><Typography variant="body2" sx={{ mb: 1 }}>Tests: {report.data.summary.total} · Internal pass/fail/blocked/unexecuted: {report.data.summary.internal_passed}/{report.data.summary.internal_failed}/{report.data.summary.internal_blocked}/{report.data.summary.internal_unexecuted} · Client assigned: {report.data.summary.client_assigned} · Client pass/fail/blocked/unexecuted: {report.data.summary.client_passed}/{report.data.summary.client_failed}/{report.data.summary.client_blocked}/{report.data.summary.client_unexecuted} · Linked defects: {report.data.summary.linked_defects} · Retests (internal/client): {report.data.summary.internal_retests}/{report.data.summary.client_retests}</Typography>
      <Typography variant="body2" sx={{ mb: 1 }}>By priority: {Object.entries(report.data.by_priority).map(([key, count]) => `${key} ${count}`).join(' · ') || '—'} · By feature: {Object.entries(report.data.by_feature).map(([key, count]) => `${key} ${count}`).join(' · ') || '—'}</Typography>
      <div style={{ overflowX: 'auto' }}><Table size="small"><TableHead><TableRow>{['Test', 'Priority', 'Internal owner', 'Internal result', 'Client tester', 'Client result', 'Ticket'].map((label) => <TableCell key={label}>{label}</TableCell>)}</TableRow></TableHead><TableBody>{report.data.tests.map((test) => <TableRow key={test.test_id}><TableCell>{test.code} · {test.title}</TableCell><TableCell>{test.priority}</TableCell><TableCell>{test.internal_owner || '—'}</TableCell><TableCell>{test.internal_result} · {test.internal_status}</TableCell><TableCell>{test.client_tester || '—'}</TableCell><TableCell>{test.client_result} · {test.client_status}</TableCell><TableCell>{test.linked_ticket || '—'}</TableCell></TableRow>)}</TableBody></Table></div>
    </>}
  </Paper>
}
