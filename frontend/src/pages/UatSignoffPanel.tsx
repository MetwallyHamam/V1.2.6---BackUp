import { Alert, Box, Button, Chip, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { api, apiErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'

type Summary = { total: number; passed: number; failed: number; blocked: number; not_tested: number; mandatory_incomplete: number; open_defects: number; pass_rate: number; completion_percent: number }
type Request = { id: number; request_number: number; status: string; requested_by_user_id: number; requested_at: string; request_comment: string | null; summary_snapshot: Summary; decided_by_user_id: number | null; decided_at: string | null; decision_comment: string | null; acceptance_notes: string | null }
type Signoff = { status: string; current_summary: Summary; history: Request[] }

export function UatSignoffPanel({ cycleId, cycleStatus, userNames }: { cycleId: number; cycleStatus: string; userNames: Record<number, string> }) {
  const { hasPermission, user } = useAuth()
  const cache = useQueryClient()
  const [requestComment, setRequestComment] = useState('')
  const [decisionComment, setDecisionComment] = useState('')
  const [acceptanceNotes, setAcceptanceNotes] = useState('')
  const [error, setError] = useState('')
  const signoff = useQuery({ queryKey: ['uat-signoff', cycleId], queryFn: async () => (await api.get<Signoff>(`/uat/cycles/${cycleId}/signoff`)).data })
  const action = useMutation({ mutationFn: async (value: { path: string; body: object }) => api.post(`/uat/cycles/${cycleId}/signoff/${value.path}`, value.body), onSuccess: async () => { setError(''); setRequestComment(''); setDecisionComment(''); setAcceptanceNotes(''); await Promise.all([cache.invalidateQueries({ queryKey: ['uat-signoff', cycleId] }), cache.invalidateQueries({ queryKey: ['uat-cycles'] }), cache.invalidateQueries({ queryKey: ['uat-dashboard', cycleId] })]) }, onError: (cause) => setError(apiErrorMessage(cause, 'The sign-off action failed.')) })
  const summary = signoff.data?.current_summary
  const pending = signoff.data?.history.find((row) => row.status === 'PENDING')
  const ready = summary && summary.total > 0 && summary.mandatory_incomplete === 0 && summary.failed === 0 && summary.blocked === 0 && summary.open_defects === 0
  const canDecide = pending && pending.requested_by_user_id !== user?.id
  const metrics: { label: string; value: number | string }[] = summary ? [
    { label: 'Total tests', value: summary.total }, { label: 'Passed', value: summary.passed },
    { label: 'Failed', value: summary.failed }, { label: 'Blocked', value: summary.blocked },
    { label: 'Not tested', value: summary.not_tested }, { label: 'Mandatory incomplete', value: summary.mandatory_incomplete },
    { label: 'Open tickets', value: summary.open_defects }, { label: 'Pass rate', value: `${summary.pass_rate}%` },
    { label: 'Completion', value: `${summary.completion_percent}%` },
  ] : []
  return <Stack spacing={2}>
    {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
    {signoff.isLoading && <Typography>Loading sign-off…</Typography>}
    <Paper sx={{ p: 2 }}><Stack direction="row" justifyContent="space-between"><Box><Typography variant="h6">Cycle sign-off</Typography><Typography color="text.secondary">Current status: {signoff.data?.status.replaceAll('_', ' ') ?? '—'}</Typography></Box><Chip label={cycleStatus} /></Stack><Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 2 }}>{metrics.map((item) => <Paper key={item.label} variant="outlined" sx={{ p: 1.5, minWidth: 120, flex: '1 1 120px' }}><Typography variant="caption" color="text.secondary">{item.label}</Typography><Typography fontWeight={800}>{item.value}</Typography></Paper>)}</Stack></Paper>
    {cycleStatus === 'ACTIVE' && !pending && hasPermission('uat.signoff.request') && <Paper component="form" sx={{ p: 2 }} onSubmit={(event: FormEvent) => { event.preventDefault(); action.mutate({ path: 'request', body: { comment: requestComment } }) }}><Typography variant="subtitle1" fontWeight={700}>Request sign-off</Typography>{!ready && <Alert severity="warning" sx={{ my: 1 }}>Complete mandatory tests and resolve failed or blocked tests and open defects before requesting sign-off.</Alert>}<TextField fullWidth multiline label="Message to approver" value={requestComment} onChange={(event) => setRequestComment(event.target.value)} sx={{ my: 1 }} /><Button type="submit" variant="contained" disabled={!ready || action.isPending}>Request sign-off</Button></Paper>}
    {pending && <Paper sx={{ p: 2 }}><Typography variant="subtitle1" fontWeight={700}>Request #{pending.request_number} awaiting decision</Typography><Typography variant="body2">Requested by {userNames[pending.requested_by_user_id] ?? `User #${pending.requested_by_user_id}`} on {new Date(pending.requested_at).toLocaleString()}</Typography>{pending.request_comment && <Typography sx={{ mt: 1 }}>{pending.request_comment}</Typography>}{canDecide && (hasPermission('uat.signoff.approve') || hasPermission('uat.signoff.reject')) && <Stack spacing={1} sx={{ mt: 2 }}><TextField multiline label="Decision comment" value={decisionComment} onChange={(event) => setDecisionComment(event.target.value)} /><TextField multiline label="Acceptance notes" value={acceptanceNotes} onChange={(event) => setAcceptanceNotes(event.target.value)} /><Stack direction="row" gap={1}>{hasPermission('uat.signoff.approve') && <Button variant="contained" disabled={action.isPending} onClick={() => action.mutate({ path: 'approve', body: { comment: decisionComment, acceptance_notes: acceptanceNotes } })}>Approve</Button>}{hasPermission('uat.signoff.reject') && <Button color="error" variant="outlined" disabled={action.isPending || !decisionComment.trim()} onClick={() => action.mutate({ path: 'reject', body: { comment: decisionComment } })}>Reject with comment</Button>}</Stack></Stack>}</Paper>}
    <Typography variant="h6">Decision history</Typography>{signoff.data?.history.length === 0 && <Typography color="text.secondary">No requests yet.</Typography>}{signoff.data?.history.map((row) => <Paper key={row.id} variant="outlined" sx={{ p: 2 }}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={700}>Request #{row.request_number}</Typography><Chip label={row.status} color={row.status === 'APPROVED' ? 'success' : row.status === 'REJECTED' ? 'error' : 'warning'} /></Stack><Typography variant="body2">Requested by {userNames[row.requested_by_user_id] ?? `User #${row.requested_by_user_id}`} · {new Date(row.requested_at).toLocaleString()}</Typography>{row.request_comment && <Typography variant="body2">Request: {row.request_comment}</Typography>}{row.decided_at && <Typography variant="body2">Decided by {userNames[row.decided_by_user_id ?? 0] ?? `User #${row.decided_by_user_id}`} · {new Date(row.decided_at).toLocaleString()}</Typography>}{row.decision_comment && <Typography variant="body2">Decision: {row.decision_comment}</Typography>}{row.acceptance_notes && <Typography variant="body2">Acceptance notes: {row.acceptance_notes}</Typography>}</Paper>)}
  </Stack>
}
