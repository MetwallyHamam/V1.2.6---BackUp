import { Button, MenuItem, Paper, Stack, Tab, Tabs, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useDeferredValue, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { MobileMultiAutocomplete } from '../components/MobileMultiAutocomplete'
import { useAuth } from '../auth/AuthContext'
import { VisitBulkPanel } from './VisitBulkPanel'
import { VisitPlannerPanel } from './VisitPlannerPanel'
import { serverDateInput } from '../utils/serverTime'

type Client = { id: number; code: string; name: string; ticket_count: number }
type Summary = { visits: number; scheduled: number; completed: number; pending: number; entitled: number; remaining: number }

export function VisitOperationsPage() {
  const { hasPermission } = useAuth()
  const { t, i18n } = useTranslation()
  const today = new Date()
  const [tab, setTab] = useState<'QUARTER' | 'NORMAL'>('QUARTER')
  const [year, setYear] = useState(today.getFullYear())
  const [quarter, setQuarter] = useState(Math.floor(today.getMonth() / 3) + 1)
  const [month, setMonth] = useState(0)
  const [selectedClients, setSelectedClients] = useState<Client[]>([])
  const [clientSearch, setClientSearch] = useState('')
  const [clientLimit, setClientLimit] = useState(20)
  const deferredSearch = useDeferredValue(clientSearch)
  const range = useMemo(() => {
    const startMonth = month ? month - 1 : (quarter - 1) * 3
    return { start: new Date(year, startMonth, 1), end: new Date(year, month ? month : startMonth + 3, 0, 23, 59, 59) }
  }, [year, quarter, month])
  const sourceType = tab === 'QUARTER' ? 'CONTRACT_RECURRING' : 'AD_HOC,INTERNAL_OPERATION'
  const clientIds = selectedClients.map(client => client.id)
  const clientIdsParam = clientIds.join(',') || undefined
  const clients = useQuery({
    queryKey: ['visit-operation-clients', deferredSearch, clientLimit],
    queryFn: async () => (await api.get<Client[]>('/clients/ticket-options', { params: { search: deferredSearch || undefined, limit: clientLimit } })).data,
  })
  const summary = useQuery({
    queryKey: ['visit-summary', tab, year, quarter, month, clientIdsParam],
    queryFn: async () => (await api.get<Summary>('/visits/summary-cards', { params: { date_from: serverDateInput(range.start), date_to: serverDateInput(range.end), client_ids: clientIdsParam, include_subclients: false, source_type: sourceType } })).data,
  })
  const options = [...selectedClients, ...(clients.data ?? [])].filter((client, index, rows) => rows.findIndex(row => row.id === client.id) === index)

  return <Stack spacing={2}>
    <Paper sx={{ p: 2 }}>
      <Typography variant="h4" fontWeight={900}>{t('visitOperations.title')}</Typography>
      <Typography color="text.secondary">{t('visitOperations.subtitle')}</Typography>
      <Tabs value={tab} onChange={(_, value) => setTab(value)}><Tab value="QUARTER" label={t('visitOperations.quarterVisits')} /><Tab value="NORMAL" label={t('visitOperations.normalVisits')} /></Tabs>
      <Stack direction={{ xs: 'column', md: 'row' }} gap={1} mt={2} alignItems={{ md: 'center' }}>
        <MobileMultiAutocomplete
          filterOptions={values => values} options={options} value={selectedClients} inputValue={clientSearch}
          onInputChange={(_, value, reason) => { if (reason !== 'reset') { setClientSearch(value); setClientLimit(20) } }}
          onChange={(_, value) => setSelectedClients(value)} getOptionLabel={client => `${client.code} — ${client.name}`}
          isOptionEqualToValue={(left, right) => left.id === right.id} loading={clients.isFetching} noOptionsText={t('visitOperations.noMatchingClients')}
          sx={{ minWidth: { md: 380 }, flex: 1 }}
          renderOption={(props, client) => <li {...props} key={client.id}><span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{client.code}</span>&nbsp;— {client.name} · {t('visitOperations.ticketCount', { count: client.ticket_count })}</li>}
          renderInput={params => <TextField {...params} label={t('visitOperations.clients')} placeholder={t('visitOperations.clientPlaceholder')} helperText={t('visitOperations.clientHint')} />}
        />
        {(clients.data?.length ?? 0) >= clientLimit && <Button variant="outlined" onClick={() => setClientLimit(value => Math.min(200, value + 20))}>{t('visitOperations.viewMore')}</Button>}
        <TextField type="number" label={t('visitOperations.year')} value={year} onChange={event => setYear(Number(event.target.value))} />
        <TextField select label={t('visitOperations.quarter')} value={quarter} onChange={event => { setQuarter(Number(event.target.value)); setMonth(0) }} disabled={Boolean(month)}>{[1, 2, 3, 4].map(value => <MenuItem key={value} value={value}>{t('visitOperations.quarterValue', { value })}</MenuItem>)}</TextField>
        <TextField select label={t('visitOperations.monthOptional')} value={month} onChange={event => setMonth(Number(event.target.value))}><MenuItem value={0}>{t('visitOperations.wholeQuarter')}</MenuItem>{Array.from({ length: 12 }, (_, index) => <MenuItem key={index + 1} value={index + 1}>{new Date(2000, index).toLocaleString(i18n.resolvedLanguage === 'ar' ? 'ar-EG' : 'en-US', { month: 'long' })}</MenuItem>)}</TextField>
      </Stack>
    </Paper>
    <Stack direction={{ xs: 'column', md: 'row' }} gap={1}>{Object.entries(summary.data ?? {}).map(([key, value]) => <Paper key={key} variant="outlined" sx={{ p: 2, flex: 1 }}><Typography variant="overline">{t(`visitOperations.summary.${key}`)}</Typography><Typography variant="h4">{value.toLocaleString(i18n.resolvedLanguage === 'ar' ? 'ar-EG' : 'en-US')}</Typography></Paper>)}</Stack>
    {tab === 'NORMAL' && hasPermission('visit.schedule') && <Paper sx={{ p: 2 }}><VisitBulkPanel /></Paper>}
    <VisitPlannerPanel rangeStart={range.start} rangeEnd={range.end} sourceType={sourceType} clientIds={clientIds.length ? clientIds : undefined} canSchedule={hasPermission('visit.schedule')} canComplete={hasPermission('visit.occurrence.complete')} />
  </Stack>
}
