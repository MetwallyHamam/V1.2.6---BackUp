import { Alert, Button, Paper, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type Evidence = { id: number; cycle_test_id: number; original_filename: string; size_bytes: number; visibility: string }

export function UatTicketEvidencePanel({ ticketId }: { ticketId: number }) {
  const [error, setError] = useState('')
  const evidence = useQuery({ queryKey: ['ticket-uat-evidence', ticketId], queryFn: async () => (await api.get<Evidence[]>(`/tickets/${ticketId}/uat-evidence`)).data })
  const download = async (item: Evidence) => { try { const response = await api.get<Blob>(`/tickets/${ticketId}/uat-evidence/${item.id}/download`, { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = item.original_filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000) } catch (cause) { setError(apiErrorMessage(cause, 'Could not download UAT evidence.')) } }
  if (!evidence.data?.length && !evidence.isError) return null
  return <Paper sx={{ p: 2, mt: 2 }}><Typography variant="h6">Linked UAT evidence</Typography>{error && <Alert severity="error">{error}</Alert>}{evidence.isError && <Alert severity="error">{apiErrorMessage(evidence.error, 'Could not load linked UAT evidence.')}</Alert>}<Stack spacing={0.5}>{evidence.data?.map((item) => <Button key={item.id} onClick={() => download(item)} sx={{ alignSelf: 'flex-start' }}>Test #{item.cycle_test_id} · {item.original_filename} ({Math.ceil(item.size_bytes / 1024)} KB)</Button>)}</Stack></Paper>
}
