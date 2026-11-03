import { AttachFile, DirectionsCar } from '@mui/icons-material'
import { Alert, Box, Button, Chip, CircularProgress, Paper, Stack, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../api/client'

type Visit = { id: number; client_code?: string; client_name?: string; status: string; window_start: string; window_end: string; notes?: string; assignments: Array<{ starts_at: string; ends_at: string }> }

export function MyFieldVisitsPage() {
  const cache = useQueryClient()
  const visits = useQuery({ queryKey: ['my-field-visits'], queryFn: async () => (await api.get<Visit[]>('/visits/field-request/mine')).data })
  const upload = useMutation({ mutationFn: async ({ id, file }: { id: number; file: File }) => { const form = new FormData(); form.append('upload', file); return api.post(`/visits/occurrences/${id}/documents`, form, { headers: { 'Content-Type': 'multipart/form-data' } }) }, onSuccess: async () => cache.invalidateQueries({ queryKey: ['my-field-visits'] }) })
  if (visits.isLoading) return <Box sx={{ minHeight: '40vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
  return <Stack spacing={2}>
    <Box><Typography variant="h4" fontWeight={900}>My field visits</Typography><Typography color="text.secondary">Your requested, approved, and completed outdoor visits</Typography></Box>
    {visits.isError && <Alert severity="error">{apiErrorMessage(visits.error)}</Alert>}
    {upload.isError && <Alert severity="error">{apiErrorMessage(upload.error)}</Alert>}
    {!visits.data?.length && <Alert severity="info">You have no field visits yet. Use Quick actions to request one.</Alert>}
    {visits.data?.map(visit => { const assignment = visit.assignments[0]; return <Paper key={visit.id} variant="outlined" sx={{ p: 2, borderLeft: `5px solid ${visit.status === 'PENDING_APPROVAL' ? '#f59e0b' : '#00a88f'}` }}><Stack direction={{ xs: 'column', sm: 'row' }} gap={1.5} alignItems={{ sm: 'center' }}><DirectionsCar color="primary" /><Box flex={1}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={850}>Visit #{visit.id} · {visit.client_code} — {visit.client_name}</Typography><Chip size="small" color={visit.status === 'PENDING_APPROVAL' ? 'warning' : 'success'} label={visit.status.replaceAll('_', ' ')} /></Stack><Typography variant="body2">Date from: {new Date(assignment?.starts_at ?? visit.window_start).toLocaleString()}</Typography><Typography variant="body2">Date to: {new Date(assignment?.ends_at ?? visit.window_end).toLocaleString()}</Typography>{visit.notes && <Typography variant="body2" color="text.secondary">{visit.notes}</Typography>}</Box><Button component="label" startIcon={<AttachFile />} disabled={upload.isPending}>Attach document<input hidden type="file" accept="image/*,.pdf,.doc,.docx" onChange={event => { const file = event.target.files?.[0]; if (file) upload.mutate({ id: visit.id, file }); event.target.value = '' }} /></Button></Stack></Paper> })}
  </Stack>
}
