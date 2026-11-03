import { Alert, Button, Checkbox, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { MobileMultiAutocomplete } from '../components/MobileMultiAutocomplete'
import { getLocalizedName } from '../i18n/localizedMasterData'

type Option = { id: number; code?: string; name: string; name_ar?: string; product_id?: number }
type ContractScope = { id: number; client_id: number; linked_client_ids: number[]; applies_to_all_clients: boolean }

export function ContractAssignmentWizard({ contract, onContractUpdated, onSaved }: { contract: ContractScope; onContractUpdated: (contract: ContractScope) => void; onSaved: () => Promise<void> }) {
  const {t,i18n}=useTranslation(),language=i18n.resolvedLanguage==='ar'?'ar':'en'
  const [contractAll, setContractAll] = useState(contract.applies_to_all_clients)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [products, setProducts] = useState<Option[]>([])
  const [modules, setModules] = useState<Option[]>([])
  const [services, setServices] = useState<Option[]>([])
  const [allAssignmentClients, setAllAssignmentClients] = useState(true)
  const [assignmentClients, setAssignmentClients] = useState<Option[]>([])
  useEffect(() => { const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300); return () => window.clearTimeout(timer) }, [search])
  useEffect(() => setContractAll(contract.applies_to_all_clients), [contract.applies_to_all_clients])

  const productOptions = useQuery({ queryKey: ['assignment-products'], queryFn: async () => (await api.get<Option[]>('/products')).data })
  const serviceOptions = useQuery({ queryKey: ['assignment-services'], queryFn: async () => (await api.get<Option[]>('/services')).data })
  const linkedClients = useQuery({ queryKey: ['contract-linked-clients', contract.id], queryFn: async () => (await api.get<Option[]>(`/contracts/${contract.id}/clients`)).data })
  const clientSearch = useQuery({ queryKey: ['contract-assignment-client-search', debouncedSearch], queryFn: async () => (await api.get<Option[]>('/clients', { params: { search: debouncedSearch || undefined, active_only: false, limit: 50 } })).data })
  const moduleOptions = useQuery({ queryKey: ['assignment-modules', products.map(item => item.id)], queryFn: async () => { const responses = await Promise.all(products.map(product => api.get<Option[]>(`/products/${product.id}/modules`))); return responses.flatMap(response => response.data) }, enabled: products.length > 0 })
  const clientOptions = useMemo(() => {
    const searchRows = clientSearch.data ?? []
    const eligibleSearch = contractAll ? searchRows : searchRows.filter(client => contract.linked_client_ids.includes(client.id) || client.id === contract.client_id)
    return Array.from(new Map([...(linkedClients.data ?? []), ...assignmentClients, ...eligibleSearch].map(item => [item.id, item])).values())
  }, [assignmentClients, clientSearch.data, contract.client_id, contract.linked_client_ids, contractAll, linkedClients.data])

  const saveScope = useMutation({ mutationFn: async () => (await api.patch<ContractScope>(`/contracts/${contract.id}`, { applies_to_all_clients: contractAll })).data, onSuccess: onContractUpdated })
  const saveAssignments = useMutation({ mutationFn: async () => api.post(`/contracts/${contract.id}/assignments/bulk`, { products: products.map(product => ({ product_id: product.id, module_ids: modules.filter(module => module.product_id === product.id).map(module => module.id) })), service_ids: services.map(service => service.id), applies_to_all_clients: allAssignmentClients, client_ids: assignmentClients.map(client => client.id) }), onSuccess: async () => { setProducts([]); setModules([]); setServices([]); setAssignmentClients([]); await onSaved() } })
  const canSaveAssignments = (products.length > 0 || services.length > 0) && (allAssignmentClients || assignmentClients.length > 0)

  return <Paper variant="outlined" sx={{ p: 2, mb: 3, borderColor: 'primary.main' }}>
    <Typography variant="h6" fontWeight={800}>{t('contractAssignment.title')}</Typography>
    <Typography color="text.secondary">{t('contractAssignment.subtitle')}</Typography>
    {(saveScope.isError || saveAssignments.isError) && <Alert severity="error" sx={{ mt: 2 }}>{t('contractAssignment.saveFailed')}</Alert>}
    <Typography fontWeight={700} mt={2}>{t('contractAssignment.stepClients')}</Typography>
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} alignItems={{ md: 'center' }}>
      <TextField select label={t('contractAssignment.contractApplies')} value={contractAll ? 'ALL' : 'SPECIFIC'} onChange={event => setContractAll(event.target.value === 'ALL')} fullWidth><MenuItem value="ALL">{t('contractAssignment.allCurrentFuture')}</MenuItem><MenuItem value="SPECIFIC">{t('contractAssignment.linkedOnly')}</MenuItem></TextField>
      <Button variant="outlined" disabled={saveScope.isPending || contractAll === contract.applies_to_all_clients} onClick={() => saveScope.mutate()}>{t(saveScope.isPending?'contractAssignment.saving':'contractAssignment.saveScope')}</Button>
    </Stack>
    <Typography fontWeight={700} mt={3}>{t('contractAssignment.stepProducts')}</Typography>
    <MobileMultiAutocomplete options={productOptions.data ?? []} value={products} onChange={(_, value) => { setProducts(value); setModules(current => current.filter(module => value.some(product => product.id === module.product_id))) }} getOptionLabel={item => getLocalizedName(item,language)} isOptionEqualToValue={(a, b) => a.id === b.id} renderInput={params => <TextField {...params} label={t('contractAssignment.products')} placeholder={t('contractAssignment.selectProducts')} margin="normal" />} />
    <MobileMultiAutocomplete options={moduleOptions.data ?? []} value={modules} onChange={(_, value) => setModules(value)} groupBy={item => getLocalizedName(productOptions.data?.find(product => product.id === item.product_id),language)||t('contractAssignment.productGroup')} getOptionLabel={item => getLocalizedName(item,language)} isOptionEqualToValue={(a, b) => a.id === b.id} renderInput={params => <TextField {...params} label={t('contractAssignment.modules')} helperText={t('contractAssignment.modulesHelp')} margin="normal" />} />
    <Typography fontWeight={700} mt={2}>{t('contractAssignment.stepServices')}</Typography>
    <MobileMultiAutocomplete options={serviceOptions.data ?? []} value={services} onChange={(_, value) => setServices(value)} getOptionLabel={item => getLocalizedName(item,language)} isOptionEqualToValue={(a, b) => a.id === b.id} renderInput={params => <TextField {...params} label={t('contractAssignment.services')} placeholder={t('contractAssignment.selectServices')} margin="normal" />} />
    <Typography fontWeight={700} mt={2}>{t('contractAssignment.stepAssignmentClients')}</Typography>
    <TextField select label={t('contractAssignment.itemsApply')} value={allAssignmentClients ? 'ALL' : 'SPECIFIC'} onChange={event => { setAllAssignmentClients(event.target.value === 'ALL'); if (event.target.value === 'ALL') setAssignmentClients([]) }} fullWidth margin="normal"><MenuItem value="ALL">{t('contractAssignment.allCovered')}</MenuItem><MenuItem value="SPECIFIC">{t('contractAssignment.selectedOnly')}</MenuItem></TextField>
    {!allAssignmentClients && <MobileMultiAutocomplete disableCloseOnSelect filterOptions={options => options} options={clientOptions} value={assignmentClients} inputValue={search} onInputChange={(_, value, reason) => { if (reason === 'input' || reason === 'clear') setSearch(value) }} onChange={(_, value) => setAssignmentClients(value)} getOptionLabel={item => item.name} isOptionEqualToValue={(a, b) => a.id === b.id} renderOption={(props, option, state) => <li {...props} key={option.id}><Checkbox checked={state.selected} />{option.name}</li>} renderInput={params => <TextField {...params} label={t('contractAssignment.searchClients')} helperText={t('contractAssignment.searchHelp')} margin="normal" />} />}
    <Stack alignItems="flex-end" mt={2}><Button variant="contained" disabled={!canSaveAssignments || saveAssignments.isPending} onClick={() => saveAssignments.mutate()}>{t(saveAssignments.isPending?'contractAssignment.assigning':'contractAssignment.assign')}</Button></Stack>
  </Paper>
}
