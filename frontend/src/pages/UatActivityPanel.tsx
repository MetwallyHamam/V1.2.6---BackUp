import { Alert, Paper, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../api/client'

type Event = { id: number; action: string; entity_type: string; entity_id: string; actor_name: string; created_at: string }

export function UatActivityPanel({ cycleId }: { cycleId: number }) {
  const activity = useQuery({ queryKey: ['uat-activity', cycleId], queryFn: async () => (await api.get<Event[]>(`/uat/cycles/${cycleId}/activity`)).data, refetchInterval: 60_000 })
  return <Paper sx={{ p: 2 }}><Typography variant="h6">Recent UAT activity</Typography>{activity.isError && <Alert severity="error">{apiErrorMessage(activity.error, 'Could not load UAT activity.')}</Alert>}<Stack spacing={1} sx={{ mt: 1, maxHeight: 300, overflowY: 'auto' }}>{activity.data?.map((event) => <Typography key={event.id} variant="body2">{new Date(event.created_at).toLocaleString()} · {event.actor_name} · {event.action.replaceAll('.', ' ').replaceAll('_', ' ')}</Typography>)}{!activity.data?.length && <Typography variant="body2" color="text.secondary">No activity yet.</Typography>}</Stack></Paper>
}
