import { Alert, Box, Button, Checkbox, FormControlLabel, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, apiErrorMessage } from '../api/client'

type Client = { id: number; code: string; name: string }
type Page = { items: Client[]; total: number; limit: number; offset: number }
type ContractResult = { id: number; client_id: number; linked_client_ids: number[]; is_shared_default: boolean }
type Preview = { matched_count: number; selected_count: number; excluded_count: number; primary_forced: boolean; inactive_count: number }
type Mode = 'EXPLICIT' | 'ALL_MATCHING'
const PAGE_SIZE = 50

export function ContractClientBulkSelector({ contractId, canManage, onApplied }: { contractId: number; canManage: boolean; onApplied: (contract: ContractResult) => void }) {
  const {t,i18n}=useTranslation()
  const locale=i18n.resolvedLanguage==='ar'?'ar-EG':'en-US'
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [mode, setMode] = useState<Mode>('EXPLICIT')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [excludedIds, setExcludedIds] = useState<number[]>([])
  const [linkedSearch, setLinkedSearch] = useState('')
  const [linkedOffset, setLinkedOffset] = useState(0)
  useEffect(() => { const timer = window.setTimeout(() => { setQuery(search.trim()); setOffset(0) }, 300); return () => window.clearTimeout(timer) }, [search])
  const page = useQuery({ queryKey: ['client-search-page', query, offset], queryFn: async () => (await api.get<Page>('/clients/search-page', { params: { search: query || undefined, active_only: false, limit: PAGE_SIZE, offset } })).data })
  const linked = useQuery({ queryKey: ['contract-linked-clients', contractId], queryFn: async () => (await api.get<Client[]>(`/contracts/${contractId}/clients`)).data })
  useEffect(() => { if (linked.data) setSelectedIds(Array.from(new Set(linked.data.map(item => item.id)))) }, [linked.data])
  const intent = mode === 'ALL_MATCHING' ? { mode, search: query || null, excluded_ids: excludedIds, explicit_ids: [] } : { mode, search: null, excluded_ids: [], explicit_ids: selectedIds }
  const preview = useMutation({ mutationFn: async () => (await api.post<Preview>(`/contracts/${contractId}/client-selection/preview`, intent)).data })
  const apply = useMutation({ mutationFn: async () => (await api.post<ContractResult>(`/contracts/${contractId}/client-selection/apply`, intent)).data, onSuccess: contract => { onApplied(contract); linked.refetch(); preview.reset() } })
  const total = page.data?.total ?? 0
  const filteredLinked = useMemo(() => { const term = linkedSearch.trim().toLocaleLowerCase(); return (linked.data ?? []).filter(item => !term || item.name.toLocaleLowerCase().includes(term) || item.code.toLocaleLowerCase().includes(term)) }, [linked.data, linkedSearch])
  const linkedPage = filteredLinked.slice(linkedOffset, linkedOffset + PAGE_SIZE)
  const isSelected = (id: number) => mode === 'ALL_MATCHING' ? !excludedIds.includes(id) : selectedIds.includes(id)
  const toggle = (id: number, checked: boolean) => { if (mode === 'ALL_MATCHING') setExcludedIds(ids => checked ? ids.filter(value => value !== id) : Array.from(new Set([...ids, id]))); else setSelectedIds(ids => checked ? Array.from(new Set([...ids, id])) : ids.filter(value => value !== id)); preview.reset() }
  return <Box>
    <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} mb={2}><Button variant={mode === 'EXPLICIT' ? 'contained' : 'outlined'} onClick={() => { setMode('EXPLICIT'); preview.reset() }}>{t('contractClientSelector.choose')}</Button><Button variant={mode === 'ALL_MATCHING' ? 'contained' : 'outlined'} onClick={() => { setMode('ALL_MATCHING'); setExcludedIds([]); preview.reset() }}>{t('contractClientSelector.allMatching')}</Button></Stack>
    <Stack direction={{ xs: 'column', lg: 'row' }} gap={2}>
      <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 0 }}><Typography fontWeight={800}>{t('contractClientSelector.available')}</Typography><TextField fullWidth size="small" margin="normal" label={t('contractClientSelector.search')} value={search} onChange={event=>setSearch(event.target.value)} helperText={t('contractClientSelector.searchSummary',{total:new Intl.NumberFormat(locale).format(total),range:total?`${new Intl.NumberFormat(locale).format(offset+1)}–${new Intl.NumberFormat(locale).format(Math.min(offset+PAGE_SIZE,total))}`:t('contractClientSelector.zero')})}/>{mode==='ALL_MATCHING'&&<Alert severity="info" sx={{mb:1}}>{t('contractClientSelector.allNotice',{count:new Intl.NumberFormat(locale).format(total)})}</Alert>}{page.data?.items.map(client=><FormControlLabel key={client.id} sx={{display:'flex',m:0}} control={<Checkbox disabled={!canManage} checked={isSelected(client.id)} onChange={event=>toggle(client.id,event.target.checked)}/>} label={<Stack direction="row" gap={1} alignItems="center"><span><span dir="ltr">{client.code}</span> — {client.name}</span></Stack>}/>) }<Stack direction="row" gap={1} mt={1}><Button disabled={offset===0} onClick={()=>setOffset(value=>Math.max(0,value-PAGE_SIZE))}>{t('contractClientSelector.previous')}</Button><Button disabled={offset+PAGE_SIZE>=total} onClick={()=>setOffset(value=>value+PAGE_SIZE)}>{t('contractClientSelector.next')}</Button>{mode==='EXPLICIT'&&<Button disabled={!canManage} onClick={()=>setSelectedIds(ids=>Array.from(new Set([...ids,...(page.data?.items.map(item=>item.id)??[])])))}>{t('contractClientSelector.selectPage')}</Button>}</Stack></Paper>
      <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 0 }}><Typography fontWeight={800}>{t('contractClientSelector.currentlyLinked')}</Typography><TextField fullWidth size="small" margin="normal" label={t('contractClientSelector.searchLinked')} value={linkedSearch} onChange={event=>{setLinkedSearch(event.target.value);setLinkedOffset(0)}} helperText={t('contractClientSelector.linkedSummary',{matching:new Intl.NumberFormat(locale).format(filteredLinked.length),linked:new Intl.NumberFormat(locale).format(linked.data?.length??0)})}/>{linkedPage.map(client=><Stack key={client.id} direction="row" alignItems="center" gap={1} py={0.5}><Box flex={1}><span dir="ltr">{client.code}</span> — {client.name}</Box>{canManage&&mode==='EXPLICIT'?<Button size="small" color="error" onClick={()=>toggle(client.id,false)}>{t('contractClientSelector.remove')}</Button>:null}</Stack>)}<Stack direction="row" gap={1} mt={1}><Button disabled={linkedOffset===0} onClick={()=>setLinkedOffset(value=>Math.max(0,value-PAGE_SIZE))}>{t('contractClientSelector.previous')}</Button><Button disabled={linkedOffset+PAGE_SIZE>=filteredLinked.length} onClick={()=>setLinkedOffset(value=>value+PAGE_SIZE)}>{t('contractClientSelector.next')}</Button>{mode==='EXPLICIT'&&<Button color="error" disabled={!canManage} onClick={()=>setSelectedIds([])}>{t('contractClientSelector.clearSelection')}</Button>}</Stack></Paper>
    </Stack>
    <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} justifyContent="flex-end" mt={2}><Button disabled={!canManage || preview.isPending} onClick={() => preview.mutate()}>{t('contractClientSelector.preview')}</Button><Button variant="contained" disabled={!canManage || apply.isPending} onClick={() => { if (mode !== 'ALL_MATCHING' || window.confirm(t('contractClientSelector.confirmAll',{total:new Intl.NumberFormat(locale).format(total),excluded:new Intl.NumberFormat(locale).format(excludedIds.length)}))) apply.mutate() }}>{t(apply.isPending?'contractClientSelector.applying':'contractClientSelector.apply')}</Button></Stack>
    {preview.data && <Alert severity="info" sx={{ mt: 1 }}>{t('contractClientSelector.previewSummary',{selected:new Intl.NumberFormat(locale).format(preview.data.selected_count),matched:new Intl.NumberFormat(locale).format(preview.data.matched_count),excluded:new Intl.NumberFormat(locale).format(preview.data.excluded_count)})}</Alert>}
    {apply.isSuccess && <Alert severity="success" sx={{ mt: 1 }}>{t('contractClientSelector.applied')}</Alert>}
    {(apply.isError || preview.isError || page.isError || linked.isError) && <Alert severity="error" sx={{ mt: 1 }}>{apiErrorMessage(apply.error || preview.error || page.error || linked.error, t('contractClientSelector.failed'))}</Alert>}
  </Box>
}
