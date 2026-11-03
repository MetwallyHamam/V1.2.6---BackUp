import { PersonOff } from '@mui/icons-material'
import { Button, Paper, Skeleton, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

type Metric = { inactive_clients: number; as_of: string; definition: 'CURRENT_MASTER_STATUS' }

export function InactiveClientsKpi() {
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const allowed = hasPermission('client.view')
  const metric = useQuery({ queryKey: ['client-metrics', 'inactive'], queryFn: async () => (await api.get<Metric>('/clients/metrics/inactive')).data, enabled: allowed, staleTime: 60_000 })
  if (!allowed) return null
  return <Paper variant="outlined" sx={{ px: 1, py: .35, borderColor: 'warning.light', bgcolor: 'warning.50' }}>
    <Stack direction="row" alignItems="center" gap={1} minHeight={30}>
      <PersonOff color="warning" fontSize="small" />
      {metric.isLoading ? <Skeleton width={28} /> : <Typography variant="body2" fontWeight={800}>{metric.data?.inactive_clients ?? 0}</Typography>}
      <Typography variant="body2" color="text.secondary" flex={1}>Inactive clients</Typography>
      <Button size="small" onClick={() => navigate('/clients?account_status=INACTIVE')} aria-label="View inactive clients">View</Button>
    </Stack>
  </Paper>
}
