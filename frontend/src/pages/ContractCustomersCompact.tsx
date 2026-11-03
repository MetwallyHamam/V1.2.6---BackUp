import { Groups } from '@mui/icons-material'
import { Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

type Client = { id: number; code: string; name: string }
type Page = { items: Client[]; total: number; limit: number; offset: number }
const PAGE_SIZE = 25

export function ContractCustomersCompact({ contractId, total, preview, allClients }: { contractId: number; total: number; preview: string[]; allClients: boolean }) {
  const {t,i18n}=useTranslation()
  const locale=i18n.resolvedLanguage==='ar'?'ar-EG':'en-US'
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  useEffect(() => { const timer = window.setTimeout(() => { setQuery(search.trim()); setOffset(0) }, 300); return () => window.clearTimeout(timer) }, [search])
  const page = useQuery({ queryKey: ['contract-customers-page', contractId, query, offset], queryFn: async () => (await api.get<Page>(`/contracts/${contractId}/clients/page`, { params: { search: query || undefined, limit: PAGE_SIZE, offset } })).data, enabled: open })
  if (allClients) return <Chip size="small" icon={<Groups />} label={t('contractCustomersCompact.all')} />
  return <>
    <Button size="small" variant="text" startIcon={<Groups />} onClick={event => { event.stopPropagation(); setOpen(true) }} aria-label={t('contractCustomersCompact.viewAria',{count:total})} sx={{ justifyContent: 'flex-start', textTransform: 'none' }}>
      <Stack alignItems="flex-start"><Typography variant="body2" fontWeight={700}>{t('contractCustomersCompact.linked',{count:total})}</Typography><Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 230 }}>{preview.join(', ') || t('contractCustomersCompact.open')}</Typography></Stack>
    </Button>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
      <DialogTitle>{t('contractCustomersCompact.title')}</DialogTitle>
      <DialogContent dividers><TextField autoFocus fullWidth size="small" label={t('contractCustomersCompact.search')} value={search} onChange={event => setSearch(event.target.value)} sx={{ mb: 2 }} />{page.data?.items.map(client => <Stack key={client.id} py={0.75}><Typography fontWeight={700}>{client.name}</Typography><Typography variant="caption" color="text.secondary"><span dir="ltr">{client.code}</span></Typography></Stack>)}{!page.isLoading && !page.data?.items.length && <Typography color="text.secondary">{t('contractCustomersCompact.empty')}</Typography>}<Stack direction="row" gap={1} mt={2}><Button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - PAGE_SIZE))}>{t('contractCustomersCompact.previous')}</Button><Button disabled={offset + PAGE_SIZE >= (page.data?.total ?? 0)} onClick={() => setOffset(value => value + PAGE_SIZE)}>{t('contractCustomersCompact.next')}</Button><Typography variant="caption" color="text.secondary" alignSelf="center">{t('contractCustomersCompact.matching',{count:new Intl.NumberFormat(locale).format(page.data?.total??0)})}</Typography></Stack></DialogContent>
      <DialogActions><Button onClick={() => setOpen(false)}>{t('contractCustomersCompact.close')}</Button></DialogActions>
    </Dialog>
  </>
}
