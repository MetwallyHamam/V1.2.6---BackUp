import { Alert, Box, LinearProgress, Paper, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'

type Tracking = { code: string; title: string; release_version: string; status: string; due_date: string | null; expires_at: string; total: number; passed: number; failed: number; blocked: number; completion_percent: number; client_total: number; client_passed: number }

export function PublicUatTrackingPage() {
  const { token } = useParams()
  const tracking = useQuery({ queryKey: ['uat-public-tracking', token], enabled: !!token, queryFn: async () => (await api.get<Tracking>(`/public/uat-shares/${token}`)).data, refetchInterval: 60_000 })
  return <Box sx={{ maxWidth: 850, mx: 'auto', p: 3 }}><Stack spacing={2}><Typography variant="h4" fontWeight={800}>UAT live tracking</Typography>{tracking.isError && <Alert severity="error">This tracking link is unavailable or has expired.</Alert>}{tracking.data && <><Paper sx={{ p: 3 }}><Typography variant="h5">{tracking.data.code} · {tracking.data.title}</Typography><Typography>Release {tracking.data.release_version} · {tracking.data.status.replaceAll('_', ' ')}</Typography><Typography variant="body2" color="text.secondary">Due {tracking.data.due_date ?? 'Not set'} · Link expires {new Date(tracking.data.expires_at).toLocaleString()}</Typography></Paper><Paper sx={{ p: 3 }}><Typography variant="h6">Progress: {tracking.data.completion_percent}%</Typography><LinearProgress variant="determinate" value={tracking.data.completion_percent} sx={{ my: 1, height: 10, borderRadius: 2 }} /><Stack direction="row" flexWrap="wrap" gap={3}><Typography>{tracking.data.passed}/{tracking.data.total} passed</Typography><Typography>{tracking.data.failed} failed</Typography><Typography>{tracking.data.blocked} blocked</Typography><Typography>Client tests: {tracking.data.client_passed}/{tracking.data.client_total} passed</Typography></Stack></Paper></>}</Stack></Box>
}
