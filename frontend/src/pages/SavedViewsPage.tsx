import { Delete, OpenInNew } from '@mui/icons-material'
import { Alert, Box, Button, IconButton, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

type View = { id: number; owner_user_id: number; name: string; scope: string; team_id?: number; filter_json: string; is_default: boolean }
type Team = { id: number; name: string }

export function SavedViewsPage() {
  const {t}=useTranslation()
  const { user, hasPermission } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['saved-views'], queryFn: async () => (await api.get<View[]>('/saved-views')).data })
  const teams = useQuery({ queryKey: ['support-teams'], queryFn: async () => (await api.get<Team[]>('/support-teams')).data })
  const remove = useMutation({
    mutationFn: async (id: number) => api.delete(`/saved-views/${id}`),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['saved-views'] }),
  })
  const makeDefault = useMutation({ mutationFn: async (id: number) => api.patch(`/saved-views/${id}/default`), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['saved-views'] }) })
  const addDepartmentQueues = useMutation({mutationFn:async()=>api.post('/saved-views/department-defaults'),onSuccess:async()=>queryClient.invalidateQueries({queryKey:['saved-views']})})
  const openView = (view: View) => {
    const filters = JSON.parse(view.filter_json) as Record<string, string>
    navigate(`/tickets?${new URLSearchParams(filters).toString()}`)
  }
  return <Paper sx={{ p: { xs: 1.5, sm: 3 }, minWidth: 0, overflow: 'hidden' }}>
    <Typography variant="h4" gutterBottom>{t('savedViewsPage.title')}</Typography>
    <Typography color="text.secondary" mb={2}>{t('savedViewsPage.subtitle')}</Typography>
    {user?.user_type==='EMPLOYEE'&&<Button variant="outlined" fullWidth={false} sx={{mb:2}} disabled={addDepartmentQueues.isPending} onClick={()=>addDepartmentQueues.mutate()}>{t(addDepartmentQueues.isPending?'savedViewsPage.adding':'savedViewsPage.addQueues')}</Button>}
    {query.isError && <Alert severity="error">{t('savedViewsPage.loadFailed')}</Alert>}
    {remove.isError && <Alert severity="error" sx={{ mb: 2 }}>{t('savedViewsPage.removeFailed')}</Alert>}
    {query.data?.length === 0 && <Alert severity="info">{t('savedViewsPage.empty')}</Alert>}
    {!!query.data?.length && <Box role="region" aria-label={t('savedViewsPage.region')} tabIndex={0} sx={{ overflowX: 'auto', maxWidth: '100%', WebkitOverflowScrolling: 'touch' }}><Table sx={{ minWidth: 720 }}><TableHead><TableRow>{(['name','scope','filters','default','actions'] as const).map(column=><TableCell key={column} align={column==='actions'?'right':'left'}>{t(`savedViewsPage.columns.${column}`)}</TableCell>)}</TableRow></TableHead><TableBody>{query.data.map((view) => { const owned = view.owner_user_id === user?.id; const canDelete = owned || (view.scope === 'GLOBAL' && hasPermission('configuration.manage')); return <TableRow key={view.id}><TableCell>{view.name}</TableCell><TableCell>{view.scope === 'TEAM' ? t('savedViewsPage.team',{name:teams.data?.find(team => team.id === view.team_id)?.name ?? `#${view.team_id}`}) : t(`savedViewsPage.scopes.${view.scope}`,{defaultValue:view.scope})}</TableCell><TableCell sx={{ minWidth: 220, overflowWrap: 'anywhere' }}>{Object.entries(JSON.parse(view.filter_json) as Record<string, string>).map(([key, value]) => t('savedViewsPage.filter',{key:t(`savedViewsPage.filterKeys.${key}`,{defaultValue:key.replaceAll('_',' ')}),value})).join(', ') || t('savedViewsPage.noFilters')}</TableCell><TableCell>{view.is_default ? t('savedViewsPage.yes') : owned ? <Button size="small" onClick={() => makeDefault.mutate(view.id)}>{t('savedViewsPage.makeDefault')}</Button> : '—'}</TableCell><TableCell align="right"><Stack direction="row" justifyContent="flex-end"><Button size="small" startIcon={<OpenInNew />} onClick={() => openView(view)}>{t('savedViewsPage.open')}</Button>{canDelete && <IconButton aria-label={t('savedViewsPage.delete',{name:view.name})} color="error" onClick={() => remove.mutate(view.id)}><Delete /></IconButton>}</Stack></TableCell></TableRow>})}</TableBody></Table></Box>}
  </Paper>
}
