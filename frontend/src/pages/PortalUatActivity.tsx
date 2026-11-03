import { Alert, Button, Paper, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'

type Event = { kind: 'TEST_RESULT' | 'COMMENT' | 'SIGNOFF'; test_code: string | null; actor: string; detail: string; at: string }

export function PortalUatActivity({ cycleId }: { cycleId: number }) {
  const [open, setOpen] = useState(false)
  const activity = useQuery({ queryKey: ['portal-uat-activity', cycleId], enabled: open,
    queryFn: async () => (await api.get<Event[]>(`/portal/uat/cycles/${cycleId}/activity`)).data })
  return <Stack spacing={1} sx={{ mt: 2 }}>
    <Button size="small" onClick={() => setOpen(!open)} sx={{ alignSelf: 'flex-start' }}>{open ? 'Hide client activity' : 'Show client activity'}</Button>
    {open && <Paper variant="outlined" sx={{ p: 1.5 }}>
      {activity.isError && <Alert severity="error">Could not load client activity.</Alert>}
      {activity.isLoading && <Typography variant="body2">Loading activity…</Typography>}
      {activity.data?.length === 0 && <Typography variant="body2">No client activity yet.</Typography>}
      {activity.data?.map((event, index) => <Typography key={`${event.kind}-${event.at}-${index}`} variant="body2" sx={{ my: 0.5 }}>
        {new Date(event.at).toLocaleString()} · {event.actor} · {event.test_code ? `${event.test_code} · ` : ''}{event.kind.replaceAll('_', ' ')}: {event.detail}
      </Typography>)}
    </Paper>}
  </Stack>
}
