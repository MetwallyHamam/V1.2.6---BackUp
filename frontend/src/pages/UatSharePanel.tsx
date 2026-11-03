import { Alert, Button, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type Link = { id: number; created_at: string; expires_at: string; revoked_at: string | null }

export function UatSharePanel({ cycleId }: { cycleId: number }) {
  const cache = useQueryClient()
  const [hours, setHours] = useState(72)
  const [createdUrl, setCreatedUrl] = useState('')
  const [error, setError] = useState('')
  const links = useQuery({ queryKey: ['uat-share-links', cycleId], queryFn: async () => (await api.get<Link[]>(`/uat/cycles/${cycleId}/share-links`)).data })
  const create = useMutation({ mutationFn: async () => (await api.post<Link & { token: string }>(`/uat/cycles/${cycleId}/share-links`, { expires_in_hours: hours })).data, onSuccess: async (row) => { setCreatedUrl(`${window.location.origin}/uat-share/${row.token}`); setError(''); await cache.invalidateQueries({ queryKey: ['uat-share-links', cycleId] }) }, onError: (cause) => setError(apiErrorMessage(cause, 'Could not create a tracking link.')) })
  const revoke = useMutation({ mutationFn: async (id: number) => api.post(`/uat/cycles/${cycleId}/share-links/${id}/revoke`), onSuccess: async () => { setError(''); await cache.invalidateQueries({ queryKey: ['uat-share-links', cycleId] }) }, onError: (cause) => setError(apiErrorMessage(cause, 'Could not revoke the tracking link.')) })
  return <Paper sx={{ p: 2 }}><Typography variant="h6">Read-only tracking links</Typography><Typography variant="body2" color="text.secondary">Anyone with a link can see aggregate progress until it expires or is revoked. Copy a new link now; it will not be shown again.</Typography>{error && <Alert severity="error">{error}</Alert>}<Stack direction={{ xs: 'column', md: 'row' }} gap={1} sx={{ my: 1 }}><TextField type="number" label="Expires in hours" value={hours} onChange={(event) => setHours(Number(event.target.value))} slotProps={{ htmlInput: { min: 1, max: 720 } }} /><Button variant="contained" disabled={create.isPending || hours < 1 || hours > 720} onClick={() => create.mutate()}>Create link</Button></Stack>{createdUrl && <TextField fullWidth label="New tracking link" value={createdUrl} slotProps={{ input: { readOnly: true } }} onFocus={(event) => event.target.select()} />}{links.data?.map((row) => <Stack key={row.id} direction="row" justifyContent="space-between" alignItems="center" sx={{ mt: 1 }}><Typography variant="body2">Link #{row.id} · Expires {new Date(row.expires_at).toLocaleString()} · {row.revoked_at ? 'Revoked' : 'Active'}</Typography>{!row.revoked_at && <Button color="error" onClick={() => revoke.mutate(row.id)} disabled={revoke.isPending}>Revoke</Button>}</Stack>)}</Paper>
}
