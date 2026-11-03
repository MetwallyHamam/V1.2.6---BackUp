import { Alert, Box, Card, CardContent, MenuItem, Pagination, Stack, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { currentMonthToDate } from '../utils/dateRange'

type ClientHours = { client_id: number; client_name: string; working_hours: number; target_hours: number; saved_hours: number }
type Response = { date_from: string; date_to: string; clients: ClientHours[] }
const CLIENTS_PER_PAGE = 3

export function ClientHoursWidget({ dateFrom, dateTo, clientId }: { dateFrom?: string; dateTo?: string; clientId?: number }) {
  const initial = currentMonthToDate()
  const [from, setFrom] = useState(dateFrom ?? initial.dateFrom)
  const [to, setTo] = useState(dateTo ?? initial.dateTo)
  const [selected, setSelected] = useState('')
  const [requestedPage, setRequestedPage] = useState(1)
  const navigate = useNavigate()
  const { t } = useTranslation()
  const effectiveFrom = dateFrom ?? from
  const effectiveTo = dateTo ?? to
  const hours = useQuery({
    queryKey: ['client-hours', effectiveFrom, effectiveTo, clientId],
    queryFn: async () => (await api.get<Response>('/home/client-hours', { params: { date_from: effectiveFrom, date_to: effectiveTo, client_id: clientId } })).data,
    enabled: Boolean(effectiveFrom && effectiveTo && effectiveFrom <= effectiveTo),
  })
  const rows = hours.data?.clients ?? []
  const shown = selected ? rows.filter(row => String(row.client_id) === selected) : rows
  const pageCount = Math.ceil(shown.length / CLIENTS_PER_PAGE)
  const page = Math.min(requestedPage, Math.max(1, pageCount))
  const pageRows = shown.slice((page - 1) * CLIENTS_PER_PAGE, page * CLIENTS_PER_PAGE)
  useEffect(() => setRequestedPage(1), [effectiveFrom, effectiveTo, clientId, selected])
  const max = Math.max(1, ...shown.map(row => Math.max(row.working_hours, row.target_hours, Math.abs(row.saved_hours))))
  const totals = shown.reduce((sum, row) => ({
    working: sum.working + row.working_hours,
    target: sum.target + row.target_hours,
    saved: sum.saved + row.saved_hours,
  }), { working: 0, target: 0, saved: 0 })
  return <Card variant="outlined"><CardContent>
    <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} alignItems={{ sm: 'center' }} mb={2}>
      <Box flex={1}><Typography variant="h6" fontWeight={800}>{t('clientHours.title')}</Typography><Typography variant="caption" color="text.secondary">{t('clientHours.definition')}</Typography></Box>
      {!dateFrom && <TextField size="small" type="date" label={t('clientHours.from')} value={from} onChange={event => setFrom(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />}
      {!dateTo && <TextField size="small" type="date" label={t('clientHours.to')} value={to} onChange={event => setTo(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />}
      {!clientId && <TextField select size="small" label={t('clientHours.client')} value={selected} onChange={event => setSelected(event.target.value)} sx={{ minWidth: 180 }}><MenuItem value="">{t('clientHours.allClients')}</MenuItem>{rows.map(row => <MenuItem key={row.client_id} value={String(row.client_id)}>{row.client_name}</MenuItem>)}</TextField>}
    </Stack>
    {effectiveFrom > effectiveTo && <Alert severity="warning">{t('clientHours.invalidDates')}</Alert>}
    {hours.isError && <Alert severity="error">{t('clientHours.loadFailed')}</Alert>}
    {hours.isLoading && <Typography color="text.secondary">{t('clientHours.loading')}</Typography>}
    {!hours.isLoading && !hours.isError && rows.length === 0 && <Typography color="text.secondary">{t('clientHours.empty')}</Typography>}
    {rows.length > 0 && <><Stack direction="row" gap={2} flexWrap="wrap" mb={2}><Typography><b>{totals.working.toFixed(1)} h</b> {t('clientHours.working')}</Typography><Typography><b>{totals.target.toFixed(1)} h</b> {t('clientHours.target')}</Typography><Typography color={totals.saved < 0 ? 'error.main' : 'success.main'}><b>{totals.saved.toFixed(1)} h</b> {t('clientHours.saved')}</Typography></Stack><Stack spacing={1.5}>{pageRows.map(row => <Box key={row.client_id} component="button" type="button" onClick={() => navigate(`/clients/${row.client_id}/profile?${new URLSearchParams({ date_from: effectiveFrom, date_to: effectiveTo })}`)} sx={{ border: 0, p: 0, bgcolor: 'transparent', color: 'text.primary', textAlign: 'left', cursor: 'pointer' }}><Stack direction="row" gap={1} justifyContent="space-between"><Typography fontWeight={700}>{row.client_name}</Typography><Typography variant="body2">{t('clientHours.row', { working: row.working_hours, target: row.target_hours, saved: row.saved_hours })}</Typography></Stack>{([[t('clientHours.working'), row.working_hours, 'primary.main'], [t('clientHours.target'), row.target_hours, 'info.main'], [t(row.saved_hours < 0 ? 'clientHours.overrun' : 'clientHours.saved'), Math.abs(row.saved_hours), row.saved_hours < 0 ? 'error.main' : 'success.main']] as const).map(([label, value, color]) => <Stack key={label} direction="row" alignItems="center" gap={1} mt={.35}><Typography variant="caption" sx={{ width: 68 }}>{label}</Typography><Box flex={1} height={6} bgcolor="action.hover" borderRadius={5} overflow="hidden"><Box height="100%" width={`${value / max * 100}%`} bgcolor={color} /></Box></Stack>)}</Box>)}</Stack>{pageCount > 1 && <Stack alignItems="center" mt={2}><Pagination count={pageCount} page={page} onChange={(_, nextPage) => setRequestedPage(nextPage)} color="primary" aria-label={t('clientHours.pages')} /></Stack>}</>}
  </CardContent></Card>
}
