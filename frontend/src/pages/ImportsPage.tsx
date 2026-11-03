import { Download, Upload } from '@mui/icons-material'
import { Alert, Box, Button, Card, CardActionArea, CardContent, Checkbox, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, TextField, Typography } from '@mui/material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { ChangeEvent, useEffect, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { api, apiErrorMessage } from '../api/client'

type Job = { id: number; template_type: string; original_filename: string; status: string; total_rows: number; valid_rows: number; invalid_rows: number; inserted_rows: number; created_at: string }
type ItopPreview = { rows:number; missing_clients:string[]; missing_engineers:string[]; missing_callers:string[]; rows_blocked_without_client_creation:number }

const templates = [
  { value: 'MASTER_DATA' }, { value: 'CLIENTS' }, { value: 'BRANCHES' }, { value: 'CONTACTS' },
  { value: 'INSTALLATIONS' }, { value: 'CLIENT_ACCESS' }, { value: 'PRODUCTS_MODULES' }, { value: 'SERVICES' },
  { value: 'SLA_POLICIES' }, { value: 'USERS' }, { value: 'USER_PROFILES' }, { value: 'CONTRACTS' },
  { value: 'CONTRACT_COVERAGE' }, { value: 'PROJECT_HANDOVERS' }, { value: 'SHIFTS' }, { value: 'TICKETS' },
] as const

export function ImportsPage() {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage === 'ar' ? 'ar-EG' : 'en-US'
  const queryClient = useQueryClient()
  const [type, setType] = useState('CLIENTS')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [workspace, setWorkspace] = useState<'standard'|'itop'>('standard')
  const [confirmJob, setConfirmJob] = useState<Job|null>(null)
  const [preview, setPreview] = useState<ItopPreview|null>(null)
  const [createClients, setCreateClients] = useState(true)
  const [createEngineers, setCreateEngineers] = useState(false)
  const [createCallers, setCreateCallers] = useState(true)
  const [confirmationReason, setConfirmationReason] = useState('Approved ITOP ticket migration')
  useEffect(() => {
    if (workspace === 'itop') setType('ITOP_TICKETS')
    else setType(current => current === 'ITOP_TICKETS' ? 'CLIENTS' : current)
  }, [workspace])
  const jobs = useQuery({ queryKey: ['imports'], queryFn: async () => (await api.get<Job[]>('/imports')).data, refetchInterval: query => query.state.data?.some(job => job.status === 'IMPORTING') ? 3000 : false })
  async function download() { setError(''); try { const response = await api.get(`/imports/templates/${type}`, { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${type.toLowerCase()}_import_v1.xlsx`; document.body.appendChild(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); setMessage(t('importsPage.downloaded')) } catch { setError(t('importsPage.downloadFailed')) } }
  async function upload(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; if (!file) return; setError(''); setMessage(''); const data = new FormData(); data.append('workbook', file); try { const result = await api.post<Job>(`/imports/${type}/upload`, data); setMessage(t('importsPage.uploadResult',{valid:result.data.valid_rows.toLocaleString(locale),invalid:result.data.invalid_rows.toLocaleString(locale),next:t(result.data.invalid_rows?'importsPage.fixWorkbook':'importsPage.ready')})); await queryClient.invalidateQueries({ queryKey: ['imports'] }) } catch (caught) { const response = axios.isAxiosError(caught) ? caught.response?.data as { error?: { message?: string }; detail?: string } | undefined : undefined; setError(response?.error?.message ?? response?.detail ?? t('importsPage.uploadFailed')) } event.target.value = '' }
  async function startImport(job:Job, payload:Record<string,unknown>) { try { await api.post(`/imports/${job.id}/confirm`, payload); await queryClient.invalidateQueries({ queryKey: ['imports'] }); setMessage(t('importsPage.started',{filename:job.original_filename})); setConfirmJob(null); setPreview(null) } catch (caught) { setError(apiErrorMessage(caught, t('importsPage.startFailed'))) } }
  async function confirm(job: Job) { if(job.template_type==='ITOP_TICKETS'){try{const result=await api.get<ItopPreview>(`/imports/${job.id}/itop-preview`);setPreview(result.data);setConfirmJob(job)}catch(caught){setError(apiErrorMessage(caught,t('importsPage.startFailed')))}return} const reason = window.prompt(t('importsPage.reasonPrompt')); if (!reason) return; await startImport(job,{reason}) }
  const historyTable=(items:Job[]|undefined)=><Box role="region" aria-label={t('importsPage.history')} tabIndex={0} sx={{ mt: 3, overflowX: 'auto', maxWidth: '100%', WebkitOverflowScrolling: 'touch' }}><Table sx={{ minWidth: 760 }}><TableHead><TableRow>{(['file','dataset','status','rows','valid','errors','action'] as const).map(column=><TableCell key={column}>{t(`importsPage.columns.${column}`)}</TableCell>)}</TableRow></TableHead><TableBody>{items?.map(job => <TableRow key={job.id}><TableCell sx={{ maxWidth: 240, overflowWrap: 'anywhere',direction:'ltr' }}>{job.original_filename}</TableCell><TableCell>{t(`importsPage.templates.${job.template_type}.label`,{defaultValue:job.template_type})}</TableCell><TableCell>{t(`importsPage.statuses.${job.status}`,{defaultValue:job.status})}</TableCell><TableCell>{job.total_rows.toLocaleString(locale)}</TableCell><TableCell>{job.valid_rows.toLocaleString(locale)}</TableCell><TableCell>{job.invalid_rows.toLocaleString(locale)}</TableCell><TableCell>{job.status === 'READY_FOR_CONFIRMATION' && <Button onClick={() => confirm(job)}>{t('importsPage.confirm')}</Button>}</TableCell></TableRow>)}</TableBody></Table></Box>
  if(workspace==='itop') return <Paper sx={{p:{xs:1.5,sm:3}}}><Typography variant="h4">{t('importsPage.title')}</Typography><Tabs value={workspace} onChange={(_,value)=>{setWorkspace(value);if(value==='itop')setType('ITOP_TICKETS')}} sx={{mb:2}}><Tab value="standard" label={t('importsPage.standardTab')}/><Tab value="itop" label={t('importsPage.itopTab')}/></Tabs><Typography variant="h5">{t('importsPage.templates.ITOP_TICKETS.label')}</Typography><Typography color="text.secondary" mb={2}>{t('importsPage.templates.ITOP_TICKETS.help')}</Typography><Alert severity="info" sx={{mb:2}}>{t('importsPage.warnings.ITOP_TICKETS')}</Alert><Button component="label" variant="contained" startIcon={<Upload />}>{t('importsPage.validateItop')}<input hidden type="file" accept=".xlsx" onChange={upload}/></Button>{message&&<Alert severity="success" sx={{mt:2}}>{message}</Alert>}{error&&<Alert severity="error" sx={{mt:2}}>{error}</Alert>}{historyTable(jobs.data?.filter(job=>job.template_type==='ITOP_TICKETS'))}<Dialog open={Boolean(confirmJob)} onClose={()=>setConfirmJob(null)} fullWidth maxWidth="md"><DialogTitle>{t('importsPage.itopConfirmTitle')}</DialogTitle><DialogContent><Alert severity="info" sx={{my:1}}>{t('importsPage.itopPreviewSummary',{rows:preview?.rows??0,clients:preview?.missing_clients.length??0,engineers:preview?.missing_engineers.length??0,callers:preview?.missing_callers.length??0})}</Alert><FormControlLabel control={<Checkbox checked={createClients} onChange={(_,value)=>setCreateClients(value)}/>} label={t('importsPage.createMissingClients')}/><FormControlLabel control={<Checkbox checked={createEngineers} onChange={(_,value)=>setCreateEngineers(value)}/>} label={t('importsPage.createMissingEngineers')}/><FormControlLabel control={<Checkbox checked={createCallers} onChange={(_,value)=>setCreateCallers(value)}/>} label={t('importsPage.createMissingCallers')}/>{!createClients&&Boolean(preview?.rows_blocked_without_client_creation)&&<Alert severity="warning">{t('importsPage.clientRequiredWarning',{count:preview?.rows_blocked_without_client_creation})}</Alert>}<TextField fullWidth required margin="normal" label={t('importsPage.migrationReason')} value={confirmationReason} onChange={event=>setConfirmationReason(event.target.value)}/></DialogContent><DialogActions><Button onClick={()=>setConfirmJob(null)}>{t('serviceManagement.actions.cancel')}</Button><Button variant="contained" disabled={confirmationReason.trim().length<5} onClick={()=>confirmJob&&startImport(confirmJob,{reason:confirmationReason.trim(),create_missing_clients:createClients,create_missing_engineers:createEngineers,create_missing_callers:createCallers})}>{t('importsPage.confirm')}</Button></DialogActions></Dialog></Paper>
  return <Paper sx={{ p: { xs: 1.5, sm: 3 }, minWidth: 0, overflow: 'hidden' }}>
    <Typography variant="h4">{t('importsPage.title')}</Typography>
    <Tabs value={workspace} onChange={(_,value)=>{setWorkspace(value);if(value==='itop')setType('ITOP_TICKETS')}} sx={{mb:2}}><Tab value="standard" label={t('importsPage.standardTab')}/><Tab value="itop" label={t('importsPage.itopTab')}/></Tabs>
    <Typography color="text.secondary" sx={{ mb: 2 }}>{t('importsPage.subtitle')}</Typography>
    <Alert severity="info" sx={{ mb: 3 }}>{t('importsPage.sequenceHelp')}</Alert>
    <Alert severity="success" sx={{ mb: 3 }}><Trans i18nKey="importsPage.masterHelp" components={{strong:<b/>}} /></Alert>
    <Stack sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 1.5, mb: 3 }}>
      {templates.map((item, index) => <Card key={item.value} variant="outlined" sx={{ borderColor: type === item.value ? 'primary.main' : 'divider' }}><CardActionArea onClick={() => { setType(item.value); setMessage(''); setError('') }}><CardContent><Stack direction="row" spacing={1} alignItems="center"><Chip size="small" color={type === item.value ? 'primary' : 'default'} label={(index + 1).toLocaleString(locale)} /><Typography fontWeight={700}>{t(`importsPage.templates.${item.value}.label`)}</Typography></Stack><Typography variant="body2" sx={{ mt: 1 }}>{t(`importsPage.templates.${item.value}.help`)}</Typography><Typography variant="caption" color="text.secondary">{t(`importsPage.templates.${item.value}.parent`)}</Typography></CardContent></CardActionArea></Card>)}
    </Stack>
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'center' }}>
      <TextField select fullWidth label={t('importsPage.currentTask')} value={type} onChange={e => setType(e.target.value)} sx={{ minWidth: { md: 360 } }}>{templates.map((item, index) => <MenuItem key={item.value} value={item.value}>{(index+1).toLocaleString(locale)}. {t(`importsPage.templates.${item.value}.label`)}</MenuItem>)}</TextField>
      <Button startIcon={<Download />} onClick={download}>{t('importsPage.download')}</Button>
      <Button component="label" variant="contained" startIcon={<Upload />}>{t('importsPage.validate')}<input hidden type="file" accept=".xlsx" onChange={upload} /></Button>
    </Stack>
    {(['CLIENT_ACCESS','MASTER_DATA','USERS','TICKETS'] as const).includes(type as 'CLIENT_ACCESS') && <Alert severity={type==='USERS'||type==='CLIENT_ACCESS'?'warning':'info'} sx={{ mt: 2 }}>{t(`importsPage.warnings.${type}`)}</Alert>}
    {jobs.data?.some(job => job.status === 'IMPORTING') && <Alert severity="info" sx={{ mt: 2 }}>{t('importsPage.warnings.running')}</Alert>}
    {jobs.data?.some(job => job.status === 'IMPORT_FAILED') && <Alert severity="error" sx={{ mt: 2 }}>{t('importsPage.warnings.failed')}</Alert>}
    {message && <Alert severity="success" sx={{ mt: 2 }}>{message}</Alert>}{error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    {historyTable(jobs.data)}
  </Paper>
}
