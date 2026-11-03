import { AccessTime, Business, CheckCircle, Description, PriorityHigh, Sync } from '@mui/icons-material'
import { Alert, Box, Button, Chip, CircularProgress, Divider, Paper, Rating, Stack, Step, StepLabel, Stepper, TextField, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

type SatisfactionState = 'AVAILABLE' | 'SUBMITTED' | 'UNAVAILABLE' | 'EXPIRED'
type LiveUpdate = {
  ticket_number: string; client_name?: string; subject: string; description: string
  status?: string; status_code?: string; priority: string; created_at: string; updated_at: string
  closed_poll_seconds: number; resolved_at?: string; closed_at?: string; resolution_seconds: number
  status_flow: Array<{ code: string; name: string; reached_at: string; description?: string }>
  escalation?: { state: 'ACTIVE' | 'HISTORICAL'; occurred_at: string; description: string }
  satisfaction: { state: SatisfactionState; ticket_rating?:number; service_rating?:number; engineer_rating?:number; comments?:string|null }
  comments: Array<{ id: number; body: string; created_at: string }>
}

export function liveUpdatePollInterval(data?: Pick<LiveUpdate, 'status_code' | 'closed_poll_seconds'>) {
  return data?.status_code === 'CLOSED' ? Math.max(60, data.closed_poll_seconds) * 1_000 : 30_000
}

export function liveUpdateTimelineOrientation(narrow: boolean): 'vertical' | 'horizontal' {
  return narrow ? 'vertical' : 'horizontal'
}

function duration(seconds: number, complete: boolean, t: (key: string, options?: Record<string, unknown>) => string) {
  const minutes = Math.max(0, Math.floor(seconds / 60)); const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60); const remainder = minutes % 60
  const value = [days && t('time.daysShort', { count: days }), hours && t('time.hoursShort', { count: hours }), t('time.minutesShort', { count: remainder })].filter(Boolean).join(' ')
  return complete ? t('liveTicket.solvedIn', { value }) : t('liveTicket.elapsed', { value })
}

function InlineSatisfaction({ token, satisfaction, onSubmitted }: { token: string; satisfaction: LiveUpdate['satisfaction']; onSubmitted: () => void }) {
  const { t } = useTranslation()
  const [ticketRating,setTicketRating]=useState(0); const [service, setService] = useState(0); const [engineer, setEngineer] = useState(0); const [comments, setComments] = useState('')
  const submit = useMutation({ mutationFn: async () => api.post('/public/ticket-updates/satisfaction', { ticket_rating:ticketRating, service_rating: service, engineer_rating: engineer, comments: comments.trim() || null }, { params: { token } }), onSuccess: onSubmitted })
  const state=satisfaction.state
  if (state === 'SUBMITTED') return <Paper variant="outlined" sx={{p:2}}><Alert severity="success" sx={{mb:2}}>{t('satisfaction.readOnlyResult')}</Alert><Stack direction={{xs:'column',sm:'row'}} gap={3}><Box><Typography>{t('satisfaction.ticketRating')}</Typography><Rating readOnly value={satisfaction.ticket_rating??0}/></Box><Box><Typography>{t('satisfaction.service')}</Typography><Rating readOnly value={satisfaction.service_rating??0}/></Box><Box><Typography>{t('satisfaction.engineer')}</Typography><Rating readOnly value={satisfaction.engineer_rating??0}/></Box></Stack>{satisfaction.comments&&<Typography mt={2}>{satisfaction.comments}</Typography>}</Paper>
  if (state === 'EXPIRED') return <Alert severity="info">{t('liveTicket.feedbackExpired')}</Alert>
  if (state !== 'AVAILABLE') return null
  return <Paper component="section" aria-labelledby="inline-satisfaction-title" elevation={0} sx={{ p: { xs: 2, sm: 3 }, borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
    <Typography id="inline-satisfaction-title" variant="h6" fontWeight={750}>{t('liveTicket.rateExperience')}</Typography>
    <Typography color="text.secondary" sx={{ mb: 2 }}>{t('liveTicket.feedbackNotice')}</Typography>
    <Stack spacing={2.5}>
      <Box><Typography fontWeight={700}>{t('satisfaction.ticketRating')}</Typography><Rating aria-label={t('satisfaction.ticketRating')} size="large" value={ticketRating} onChange={(_, value) => setTicketRating(value ?? 0)} /></Box>
      <Box><Typography fontWeight={700}>{t('liveTicket.serviceSatisfaction')}</Typography><Rating aria-label={t('liveTicket.serviceSatisfaction')} size="large" value={service} onChange={(_, value) => setService(value ?? 0)} /></Box>
      <Box><Typography fontWeight={700}>{t('liveTicket.engineerRating')}</Typography><Rating aria-label={t('liveTicket.engineerRating')} size="large" value={engineer} onChange={(_, value) => setEngineer(value ?? 0)} /></Box>
      <TextField label={t('liveTicket.optionalComments')} multiline minRows={3} value={comments} inputProps={{ maxLength: 2000 }} helperText={`${comments.length}/2000`} onChange={event => setComments(event.target.value)} />
      {submit.isError && <Alert severity="error">{t('liveTicket.feedbackFailed')}</Alert>}
      <Button variant="contained" sx={{ alignSelf: { sm: 'flex-start' } }} disabled={ticketRating < 1 || service < 1 || engineer < 1 || submit.isPending} onClick={() => submit.mutate()}>{submit.isPending ? t('liveTicket.submitting') : t('liveTicket.submitFeedback')}</Button>
    </Stack>
  </Paper>
}

export function TicketLiveUpdatePage() {
  const { t, i18n } = useTranslation()
  const [params] = useSearchParams(); const token = params.get('token') ?? ''; const theme = useTheme(); const narrow = useMediaQuery(theme.breakpoints.down('sm'))
  const update = useQuery({ queryKey: ['public-ticket-update', token], queryFn: async () => (await api.get<LiveUpdate>('/public/ticket-updates', { params: { token } })).data, enabled: Boolean(token), retry: false, refetchInterval: query => liveUpdatePollInterval(query.state.data), refetchIntervalInBackground: false, refetchOnWindowFocus: 'always', refetchOnReconnect: 'always' })
  if (!token || update.isError) return <Box minHeight="100vh" display="grid" sx={{ placeItems: 'center', p: 2 }}><Alert severity="error">{t('liveTicket.invalidLink')}</Alert></Box>
  if (update.isLoading || !update.data) return <Box minHeight="100vh" display="grid" sx={{ placeItems: 'center' }}><CircularProgress aria-label={t('liveTicket.loading')} /></Box>
  const data = update.data; const steps = [...data.status_flow]
  if (data.status && steps.at(-1)?.code !== data.status_code) steps.push({ code: data.status_code ?? 'CURRENT', name: data.status, reached_at: data.updated_at })
  const complete = Boolean(data.resolved_at || data.closed_at)
  return <Box sx={{ minHeight: '100vh', bgcolor: '#f3f6fb', py: { xs: 1, sm: 2, md: 6 }, px: { xs: 1, sm: 2 }, overflowX: 'hidden' }}><Stack maxWidth={980} mx="auto" spacing={2.5} minWidth={0}>
    <Paper elevation={0} sx={{ overflow: 'hidden', borderRadius: { xs: 2, sm: 4 }, border: '1px solid', borderColor: 'divider' }}>
      <Box sx={{ p: { xs: 2, md: 4 }, color: 'white', background: 'linear-gradient(135deg, #173b67 0%, #1976d2 100%)' }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2} minWidth={0}>
        <Box minWidth={0}><Typography variant="overline" sx={{ opacity: .8 }}>{t('liveTicket.title')}</Typography><Typography variant={narrow ? 'h4' : 'h3'} fontWeight={800} dir="ltr" sx={{ unicodeBidi:'isolate', overflowWrap: 'anywhere' }}>{data.ticket_number}</Typography><Typography variant={narrow ? 'subtitle1' : 'h6'} sx={{ opacity: .9, mt: .5, overflowWrap: 'anywhere' }}>{data.subject}</Typography></Box>
        <Stack direction="row" gap={1} alignItems="flex-start" flexWrap="wrap"><Chip label={data.status_code ? t(`ticketStatus.${data.status_code}`, { defaultValue: data.status ?? t('liveTicket.unknownStatus') }) : data.status ?? t('liveTicket.unknownStatus')} sx={{ bgcolor: 'white', color: 'primary.main', fontWeight: 700 }} /><Chip label={t(`priority.${data.priority}`, { defaultValue: data.priority })} variant="outlined" sx={{ color: 'white', borderColor: 'rgba(255,255,255,.65)' }} /></Stack>
      </Stack></Box>
      <Box sx={{ p: { xs: 2, md: 4 } }}>
        <Stack direction={{ xs: 'column', md: 'row' }} gap={2}>
          <Paper variant="outlined" sx={{ p: 2, flex: 1, borderRadius: 3 }}><Stack direction="row" gap={1.5}><Business color="primary" /><Box minWidth={0}><Typography variant="caption" color="text.secondary">{t('tickets.client')}</Typography><Typography fontWeight={700} sx={{ overflowWrap: 'anywhere' }}>{data.client_name ?? t('liveTicket.clientUnavailable')}</Typography></Box></Stack></Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1, borderRadius: 3 }}><Stack direction="row" gap={1.5}>{complete ? <CheckCircle color="success" /> : <AccessTime color="primary" />}<Box><Typography variant="caption" color="text.secondary">{t('liveTicket.resolutionTime')}</Typography><Typography fontWeight={700}>{duration(data.resolution_seconds, complete, t)}</Typography></Box></Stack></Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1, borderRadius: 3 }}><Stack direction="row" gap={1.5}><Sync color="primary" /><Box><Typography variant="caption" color="text.secondary">{t('liveTicket.lastUpdated')}</Typography><Typography fontWeight={700}>{new Date(data.updated_at).toLocaleString(i18n.language)}</Typography></Box></Stack></Paper>
        </Stack>
        {data.escalation && <Alert icon={<PriorityHigh />} severity={data.escalation.state === 'ACTIVE' ? 'warning' : 'info'} sx={{ mt: 2 }}><Typography fontWeight={750}>{data.escalation.state === 'ACTIVE' ? 'Escalated' : 'Previously escalated'}</Typography>{data.escalation.description} {new Date(data.escalation.occurred_at).toLocaleString()}</Alert>}
        <Typography variant="h6" fontWeight={750} sx={{ mt: 4, mb: 2 }}>{t('liveTicket.statusFlow')}</Typography>
        <Stepper orientation={liveUpdateTimelineOrientation(narrow)} activeStep={Math.max(steps.length - 1, 0)} alternativeLabel={!narrow} sx={{ maxWidth: '100%', '& .MuiStepConnector-line': { borderWidth: narrow ? '0 0 0 3px' : '3px 0 0', borderRadius: 2 }, '& .MuiStepLabel-labelContainer': { minWidth: 0 }, '& .MuiStepLabel-label': { overflowWrap: 'anywhere' } }}>
          {steps.map((step, index) => <Step key={`${step.code}-${step.reached_at}-${index}`} completed><StepLabel optional={<Stack><Typography variant="caption">{new Date(step.reached_at).toLocaleString()}</Typography>{step.description && <Typography variant="caption" color="text.secondary">{step.description}</Typography>}</Stack>}>{step.name}</StepLabel></Step>)}
        </Stepper>
        <Divider sx={{ my: 4 }} /><Stack direction="row" gap={1} alignItems="center"><Description color="primary" /><Typography variant="h6" fontWeight={750}>{t('liveTicket.ticketDetails')}</Typography></Stack>
        <Typography variant="subtitle1" fontWeight={700} sx={{ mt: 2, overflowWrap: 'anywhere' }}>{data.subject}</Typography><Typography color="text.secondary" sx={{ whiteSpace: 'pre-wrap', mt: .5, overflowWrap: 'anywhere' }}>{data.description}</Typography><Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>{t('liveTicket.created', { date: new Date(data.created_at).toLocaleString(i18n.language) })}</Typography>
      </Box>
    </Paper>
    <Paper elevation={0} sx={{ p: { xs: 2, md: 4 }, borderRadius: { xs: 2, sm: 4 }, border: '1px solid', borderColor: 'divider' }}><Typography variant="h6" fontWeight={750}>{t('liveTicket.publicUpdates')}</Typography>
      {!data.comments.length && <Alert severity="info" sx={{ mt: 2 }}>{t('liveTicket.noPublicUpdates')}</Alert>}
      <Stack spacing={1.5} sx={{ mt: 2 }}>{data.comments.map(comment => <Paper key={comment.id} variant="outlined" sx={{ p: 2, borderRadius: 3, borderLeft: '4px solid', borderLeftColor: 'primary.main' }}><Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{comment.body}</Typography><Typography variant="caption" color="text.secondary">{new Date(comment.created_at).toLocaleString()}</Typography></Paper>)}</Stack>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 3 }}>{data.status_code === 'CLOSED' ? t('liveTicket.closedRefresh', { count: Math.round(data.closed_poll_seconds / 60) }) : t('liveTicket.liveRefresh')}</Typography>
    </Paper>
    <InlineSatisfaction token={token} satisfaction={data.satisfaction} onSubmitted={() => void update.refetch()} />
  </Stack></Box>
}
