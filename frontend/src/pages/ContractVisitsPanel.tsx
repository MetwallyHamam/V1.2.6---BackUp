import { Alert, Button, Checkbox, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, apiErrorMessage } from '../api/client'

type Entitlement = { id:number; client_id:number; client_code?:string; client_name?:string; visit_type_id:number; service_period_start:string; service_period_end:string; allowed_visits:number; recurrence:string; status:string }
type VisitType = { id:number; code:string; name:string; operation_type_code?:string }
type ClientOption = { id:number; code?:string; name:string }
type Summary = { entitled:number; planned:number; scheduled:number; completed:number; remaining:number; unplanned:number; overdue:number }

function EntitlementCard({ item, canGenerate, visitTypeName }: { item:Entitlement; canGenerate:boolean; visitTypeName:string }) {
  const {t,i18n}=useTranslation()
  const locale=i18n.resolvedLanguage==='ar'?'ar-EG':'en-US'
  const queryClient = useQueryClient()
  const totals = useQuery({ queryKey:['visit-entitlement-summary', item.id], queryFn:async() => (await api.get<Summary>(`/visits/entitlements/${item.id}/summary`)).data })
  const generate = useMutation({ mutationFn:async() => api.post(`/visits/entitlements/${item.id}/generate`), onSuccess:async() => queryClient.invalidateQueries({ queryKey:['visit-entitlement-summary', item.id] }) })
  const client = [item.client_code, item.client_name].filter(Boolean).join(' — ') || t('contractVisits.clientNumber',{id:new Intl.NumberFormat(locale).format(item.client_id)})
  return <Paper variant="outlined" sx={{ p:2 }}>
    <Stack direction={{ xs:'column', md:'row' }} gap={1}><Typography fontWeight={800} flex={1}>{t('contractVisits.entitlement',{client,id:new Intl.NumberFormat(locale).format(item.id)})}</Typography><Typography>{t(`contractVisits.statuses.${item.status}`,{defaultValue:item.status.replaceAll('_',' ')})} · {t(`contractVisits.recurrences.${item.recurrence}`,{defaultValue:item.recurrence.replaceAll('_',' ')})}</Typography></Stack>
    <Typography color="text.secondary">{t('contractVisits.period',{type:visitTypeName,start:new Date(item.service_period_start).toLocaleDateString(locale),end:new Date(item.service_period_end).toLocaleDateString(locale)})}</Typography>
    {totals.data && <Typography sx={{ mt:1 }}>{t('contractVisits.totals',Object.fromEntries(Object.entries(totals.data).map(([key,value])=>[key,new Intl.NumberFormat(locale).format(value)])))}</Typography>}
    {canGenerate && <Button size="small" sx={{ mt:1 }} onClick={() => generate.mutate()} disabled={generate.isPending}>{t('contractVisits.generate')}</Button>}
  </Paper>
}

export function ContractVisitsPanel({ contractId, clientIds, canManage }: { contractId:number; clientIds:number[]; canManage:boolean }) {
  const {t,i18n}=useTranslation()
  const locale=i18n.resolvedLanguage==='ar'?'ar-EG':'en-US'
  const queryClient = useQueryClient()
  const [visitTypeId, setVisitTypeId] = useState<number | ''>('')
  const [selectedClientIds, setSelectedClientIds] = useState<number[]>([])
  const [createError, setCreateError] = useState('')
  const entitlements = useQuery({ queryKey:['visit-entitlements', contractId], queryFn:async() => (await api.get<Entitlement[]>('/visits/entitlements', { params:{ contract_id:contractId } })).data })
  const clients = useQuery({ queryKey:['contract-linked-clients', contractId], queryFn:async() => (await api.get<ClientOption[]>(`/contracts/${contractId}/clients`)).data })
  const types = useQuery({ queryKey:['visit-types'], queryFn:async() => (await api.get<VisitType[]>('/visits/types')).data })
  const create = useMutation({ mutationFn:async(payload:Record<string,unknown>) => api.post('/visits/entitlements/bulk', payload), onMutate:() => setCreateError(''), onError:error => setCreateError(apiErrorMessage(error, t('contractVisits.createFailed'))), onSuccess:async() => { setSelectedClientIds([]); await queryClient.invalidateQueries({ queryKey:['visit-entitlements', contractId] }) } })
  const clientOptions:ClientOption[] = clients.data?.length ? clients.data : clientIds.map(id => ({ id, name:t('contractVisits.clientNumber',{id:new Intl.NumberFormat(locale).format(id)}) }))
  const defaultVisitType = types.data?.find(item => item.operation_type_code === 'OUTDOOR_VISIT' || item.code === 'OUTDOOR_VISIT')
  useEffect(() => {
    if (visitTypeId === '' && defaultVisitType) setVisitTypeId(defaultVisitType.id)
  }, [defaultVisitType, visitTypeId])
  function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    create.mutate({ contract_id:contractId, client_ids:selectedClientIds, visit_type_id:data.visit_type_id ? Number(data.visit_type_id) : undefined, service_period_start:data.service_period_start, service_period_end:data.service_period_end, allowed_visits:Number(data.allowed_visits), recurrence:data.recurrence, scheduling_mode:data.scheduling_mode, default_duration_minutes:Number(data.default_duration_minutes), carry_forward_limit:Number(data.carry_forward_limit||0) })
  }
  return <Stack spacing={2}>
    <Alert severity="info">{t('contractVisits.notice')}</Alert>
    {entitlements.data?.map(item => <EntitlementCard key={item.id} item={item} canGenerate={canManage} visitTypeName={types.data?.find(type => type.id === item.visit_type_id)?.name ?? t('contractVisits.typeNumber',{id:new Intl.NumberFormat(locale).format(item.visit_type_id)})} />)}
    {!entitlements.data?.length && <Typography color="text.secondary">{t('contractVisits.empty')}</Typography>}
    {canManage && <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p:2 }}>
      <Typography fontWeight={800}>{t('contractVisits.add')}</Typography>
      {createError && <Alert severity="error" sx={{ mt:1 }}>{createError}</Alert>}
      <TextField select required label={t('contractVisits.exactClient')} value={selectedClientIds} onChange={event => setSelectedClientIds((event.target.value as unknown as number[]).map(Number))} SelectProps={{ multiple:true, renderValue:value => (value as number[]).map(id => clientOptions.find(client => client.id === id)).filter(Boolean).map(client => [client?.code, client?.name].filter(Boolean).join(' — ')).join(', ') }} fullWidth margin="normal">{clientOptions.map(client => <MenuItem key={client.id} value={client.id}><Checkbox checked={selectedClientIds.includes(client.id)} />{[client.code, client.name].filter(Boolean).join(' — ')}</MenuItem>)}</TextField>
      <TextField select required name="visit_type_id" label={t('contractVisits.visitType')} value={visitTypeId} onChange={event => setVisitTypeId(Number(event.target.value))} disabled={types.isLoading || types.isError || !types.data?.length} error={types.isError || (!!types.data && !types.data.length)} helperText={types.isError?t('contractVisits.typesFailed'):!types.data?.length?t('contractVisits.loadingTypes'):defaultVisitType?t('contractVisits.linkedDefault'):t('contractVisits.selectType')} fullWidth margin="normal">{types.data?.map(item => <MenuItem key={item.id} value={item.id}>{item.name}{item.operation_type_code === 'OUTDOOR_VISIT' ? ` — ${t('contractVisits.internalDefault')}` : ''}</MenuItem>)}</TextField>
      <Stack direction={{ xs:'column', md:'row' }} spacing={1}><TextField required type="date" name="service_period_start" label={t('contractVisits.periodStart')} fullWidth margin="normal" slotProps={{ inputLabel:{ shrink:true } }} /><TextField required type="date" name="service_period_end" label={t('contractVisits.periodEnd')} fullWidth margin="normal" slotProps={{ inputLabel:{ shrink:true } }} /></Stack>
      <Stack direction={{ xs:'column', md:'row' }} spacing={1}><TextField required type="number" name="allowed_visits" label={t('contractVisits.allowed')} defaultValue={4} fullWidth margin="normal" /><TextField select required name="recurrence" label={t('contractVisits.recurrence')} defaultValue="QUARTERLY" fullWidth margin="normal">{['MONTHLY','QUARTERLY','SEMIANNUAL','ANNUAL','CUSTOM'].map(value => <MenuItem key={value} value={value}>{t(`contractVisits.recurrences.${value}`)}</MenuItem>)}</TextField><TextField required type="number" name="default_duration_minutes" label={t('contractVisits.duration')} defaultValue={120} fullWidth margin="normal" /></Stack>
      <Stack direction={{ xs:'column', md:'row' }} spacing={1}><TextField select required name="scheduling_mode" label="Scheduling mode" defaultValue="DATE_WINDOW" fullWidth margin="normal"><MenuItem value="DATE_WINDOW">Planned date windows</MenuItem><MenuItem value="EXACT_DATE">Planned exact dates</MenuItem><MenuItem value="ON_DEMAND">On demand / urgent pool</MenuItem></TextField><TextField type="number" name="carry_forward_limit" label="Carry-forward limit" defaultValue={0} inputProps={{min:0,max:1000}} fullWidth margin="normal" /></Stack>
      <Button type="submit" variant="contained" disabled={create.isPending || !selectedClientIds.length}>{t('contractVisits.create')} ({new Intl.NumberFormat(locale).format(selectedClientIds.length)})</Button>
    </Paper>}
  </Stack>
}
