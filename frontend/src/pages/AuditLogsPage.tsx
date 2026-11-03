import { Visibility } from '@mui/icons-material'
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { todayInputDate } from '../utils/date'

type AuditLog = { id: number; actor_name: string; entity_type: string; entity_id: string; action: string; reason?: string; correlation_id?: string; old_values_json?: string; new_values_json?: string; created_at: string }

function prettyJson(value: string | undefined, none: string) {
  if (!value) return none
  try { return JSON.stringify(JSON.parse(value), null, 2) } catch { return value }
}

export function AuditLogsPage() {
  const {t,i18n}=useTranslation();const locale=i18n.resolvedLanguage==='ar'?'ar-EG':'en-US'
  const [search, setSearch] = useState('')
  const [entityType, setEntityType] = useState('')
  const [createdFrom, setCreatedFrom] = useState(todayInputDate)
  const [createdTo, setCreatedTo] = useState(todayInputDate)
  const [selected, setSelected] = useState<AuditLog | null>(null)
  const query = useQuery({ queryKey: ['audit-logs', search, entityType, createdFrom, createdTo], queryFn: async () => (await api.get<AuditLog[]>('/audit-logs', { params: { search: search || undefined, entity_type: entityType || undefined, created_from: createdFrom || undefined, created_to: createdTo || undefined, limit: 200 } })).data })
  return <Paper sx={{ p: 3 }}>
    <Typography variant="h4">{t('auditLogsPage.title')}</Typography><Typography color="text.secondary" mb={3}>{t('auditLogsPage.subtitle')}</Typography>
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} mb={3}><TextField size="small" label={t('auditLogsPage.search')} value={search} onChange={(event) => setSearch(event.target.value)} sx={{ minWidth: 300 }} /><TextField size="small" label={t('auditLogsPage.entityType')} value={entityType} onChange={(event) => setEntityType(event.target.value)} inputProps={{dir:'ltr'}} /><TextField size="small" type="date" label={t('auditLogsPage.from')} value={createdFrom} onChange={(event) => setCreatedFrom(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /><TextField size="small" type="date" label={t('auditLogsPage.to')} value={createdTo} onChange={(event) => setCreatedTo(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /></Stack>
    {query.isError && <Alert severity="error">{t('auditLogsPage.loadFailed')}</Alert>}
    {query.data?.length === 0 && <Alert severity="info">{t('auditLogsPage.empty')}</Alert>}
    {!!query.data?.length && <Table><TableHead><TableRow>{(['time','actor','action','entity','reason'] as const).map(column=><TableCell key={column}>{t(`auditLogsPage.columns.${column}`)}</TableCell>)}<TableCell /></TableRow></TableHead><TableBody>{query.data.map((item) => <TableRow key={item.id}><TableCell>{new Date(item.created_at).toLocaleString(locale)}</TableCell><TableCell>{item.actor_name}</TableCell><TableCell sx={{direction:'ltr'}}>{item.action.replaceAll('.', ' ')}</TableCell><TableCell sx={{direction:'ltr'}}>{item.entity_type} #{item.entity_id}</TableCell><TableCell>{item.reason || '—'}</TableCell><TableCell><Button size="small" startIcon={<Visibility />} onClick={() => setSelected(item)}>{t('auditLogsPage.details')}</Button></TableCell></TableRow>)}</TableBody></Table>}
    <Dialog open={Boolean(selected)} onClose={() => setSelected(null)} fullWidth maxWidth="md"><DialogTitle>{t('auditLogsPage.record',{id:selected?.id.toLocaleString(locale)})}</DialogTitle><DialogContent><Typography><strong>{t('auditLogsPage.action')}</strong> <span dir="ltr">{selected?.action}</span></Typography><Typography><strong>{t('auditLogsPage.actor')}</strong> {selected?.actor_name}</Typography><Typography><strong>{t('auditLogsPage.entity')}</strong> <span dir="ltr">{selected?.entity_type} #{selected?.entity_id}</span></Typography><Typography><strong>{t('auditLogsPage.correlation')}</strong> <span dir="ltr">{selected?.correlation_id || t('auditLogsPage.notRecorded')}</span></Typography><Typography variant="h6" mt={2}>{t('auditLogsPage.previous')}</Typography><Paper variant="outlined" component="pre" dir="ltr" sx={{ p: 2, whiteSpace: 'pre-wrap' }}>{prettyJson(selected?.old_values_json,t('auditLogsPage.none'))}</Paper><Typography variant="h6" mt={2}>{t('auditLogsPage.new')}</Typography><Paper variant="outlined" component="pre" dir="ltr" sx={{ p: 2, whiteSpace: 'pre-wrap' }}>{prettyJson(selected?.new_values_json,t('auditLogsPage.none'))}</Paper></DialogContent><DialogActions><Button onClick={() => setSelected(null)}>{t('auditLogsPage.close')}</Button></DialogActions></Dialog>
  </Paper>
}
