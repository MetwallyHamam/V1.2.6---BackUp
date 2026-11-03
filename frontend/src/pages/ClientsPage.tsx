import { Add, Assessment, Business, DeleteOutline, Edit, NoteAdd, Refresh, Search, VpnKey } from '@mui/icons-material'
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Link,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Typography,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { FormEvent, useEffect, useState } from 'react'
import { Link as RouterLink, useLocation, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { MobileMultiAutocomplete } from '../components/MobileMultiAutocomplete'
import { useAuth } from '../auth/AuthContext'
import { InactiveClientsKpi } from '../components/InactiveClientsKpi'
import { getLocalizedName } from '../i18n/localizedMasterData'
import { serverDateInput } from '../utils/serverTime'

type Client = {
  id: number
  code: string
  name: string
  status_id: number
  parent_client_id?: number | null
  timezone: string
  country?: string
  zone?: string
  phone_number?: string
  email?: string
  is_active: boolean
  owner_department_id?: number | null
  shared_department_ids: number[]
}
type Catalog = { id: number; code: string; name: string; name_ar?: string; is_active: boolean }
type ClientPage = { items: Client[]; total: number; limit: number; offset: number }
type Country = {id:number;code:string;name:string;name_ar?:string;default_timezone?:string;is_active:boolean}
type City = {id:number;country_id:number;code:string;name:string;name_ar?:string;is_active:boolean}
type Department = { id: number; code: string; name: string; name_ar?: string; is_active: boolean }
type ContractTemplate = { id: number; name: string; template_type: string; version: number; default_duration_months: number; is_default: boolean; is_active: boolean }
type AccessDraft = { access_type: string; label: string; server_or_address: string; username: string; password: string; notes: string }
const blankAccess = (): AccessDraft => ({ access_type: 'SERVER', label: '', server_or_address: '', username: '', password: '', notes: '' })

export function clientListSearchParams(search:string,accountStatus:string,statusId:string,page:number,countryId=''):URLSearchParams {
  const params=new URLSearchParams()
  if(search)params.set('search',search)
  if(accountStatus!=='ACTIVE')params.set('account_status',accountStatus)
  if(statusId)params.set('status_id',statusId)
  if(countryId)params.set('country_id',countryId)
  if(page>0)params.set('page',String(page+1))
  return params
}

export function ClientsPage() {
  const { i18n, t } = useTranslation()
  const language = i18n.resolvedLanguage === 'ar' ? 'ar' : 'en'
  const queryClient = useQueryClient()
  const { hasPermission } = useAuth()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState(()=>searchParams.get('search')??'')
  const [accountStatus, setAccountStatus] = useState<'ACTIVE' | 'INACTIVE' | 'ALL'>(() => searchParams.get('account_status') === 'INACTIVE' ? 'INACTIVE' : searchParams.get('account_status') === 'ALL' ? 'ALL' : 'ACTIVE')
  const [clientStatusId, setClientStatusId] = useState(()=>searchParams.get('status_id')??'')
  const [countryId] = useState(()=>searchParams.get('country_id')??'')
  const [page, setPage] = useState(()=>Math.max(0,(Number(searchParams.get('page'))||1)-1))
  const [dialogOpen, setDialogOpen] = useState(false)
  const [countryOpen, setCountryOpen] = useState(false)
  const [cityOpen,setCityOpen]=useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [accesses, setAccesses] = useState<AccessDraft[]>([])
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null)
  const [selectedCity,setSelectedCity]=useState<City|null>(null)
  const [createContract, setCreateContract] = useState(true)
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [contractClient, setContractClient] = useState<Client | null>(null)
  const [ownerDepartmentId, setOwnerDepartmentId] = useState('')
  const [sharedDepartments, setSharedDepartments] = useState<Department[]>([])
  const clients = useQuery({
    queryKey: ['clients-page', search, accountStatus, clientStatusId, countryId, page],
    queryFn: async () =>
      (await api.get<ClientPage>('/clients/search-page', { params: { search: search || undefined, account_status: accountStatus, active_only: false, status_id: clientStatusId || undefined, country_id: countryId || undefined, limit: 20, offset: page * 20 } })).data,
  })
  const parentClients = useQuery({ queryKey: ['clients', 'parent-options'], queryFn: async () => (await api.get<Client[]>('/clients', { params: { active_only: false, limit: 200 } })).data, enabled: dialogOpen })
  const statuses = useQuery({
    queryKey: ['client-statuses'],
    queryFn: async () => (await api.get<Catalog[]>('/client-statuses')).data,
  })
  const countries = useQuery({
    queryKey: ['countries'],
    queryFn: async () => (await api.get<Country[]>('/countries')).data,
  })
  const cities=useQuery({queryKey:['cities'],queryFn:async()=>(await api.get<City[]>('/cities')).data})
  const departments = useQuery({ queryKey: ['departments'], queryFn: async () => (await api.get<Department[]>('/departments', { params: { active_only: true } })).data })
  const contractTemplates = useQuery({ queryKey: ['contract-templates'], queryFn: async () => (await api.get<ContractTemplate[]>('/contract-templates', { params: { active_only: true } })).data, enabled: dialogOpen || Boolean(contractClient) })
  useEffect(()=>{
    const next=clientListSearchParams(search,accountStatus,clientStatusId,page,countryId)
    if(next.toString()!==searchParams.toString())setSearchParams(next,{replace:true})
  },[accountStatus,clientStatusId,countryId,page,search,searchParams,setSearchParams])
  useEffect(() => {
    if (!selectedTemplateId && contractTemplates.data?.length) {
      setSelectedTemplateId(String(contractTemplates.data.find(item => item.is_default)?.id ?? contractTemplates.data[0].id))
    }
  }, [contractTemplates.data, selectedTemplateId])
  const create = useMutation({
    mutationFn: async ({ onboarding, access, location }: { onboarding: Record<string, unknown>; access: AccessDraft[]; location: Record<string, unknown> | null }) => {
      const created = (await api.post<{ client_id: number; client_code: string; contract_id: number | null }>('/clients/onboard', onboarding)).data
      if (location) await api.post(`/clients/${created.client_id}/locations`, { ...location, code: `${created.client_code}-${String(location.city_code)}`.slice(0, 50), city_code: undefined })
      await Promise.all(access.map(item => api.post(`/clients/${created.client_id}/access`, {
        ...item,
        server_or_address: item.server_or_address.trim() || null,
        username: item.username.trim() || null,
        password: item.password || null,
        notes: item.notes.trim() || null,
        is_active: true,
      })))
      return created
    },
    onSuccess: async () => {
      setDialogOpen(false)
      setAccesses([])
      setOwnerDepartmentId('')
      setSharedDepartments([])
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      await queryClient.invalidateQueries({ queryKey: ['clients-page'] })
    },
  })
  const createCountry = useMutation({ mutationFn: async (payload: Record<string, unknown>) => (await api.post<Country>('/countries', payload)).data, onSuccess: async (country) => { const cityRows=(await api.get<City[]>('/cities',{params:{country_id:country.id}})).data;setCountryOpen(false);setSelectedCountry(country);setSelectedCity(cityRows[0]??null);await queryClient.invalidateQueries({ queryKey: ['countries'] });await queryClient.invalidateQueries({queryKey:['cities']});await queryClient.invalidateQueries({ queryKey: ['management-metadata'] }) } })
  const createCity=useMutation({mutationFn:async(payload:{name:string;name_ar:string})=>(await api.post<City>('/cities',{country_id:selectedCountry?.id,...payload,is_active:true})).data,onSuccess:async city=>{setCityOpen(false);setSelectedCity(city);await queryClient.invalidateQueries({queryKey:['cities']})}})
  const remove = useMutation({
    mutationFn: async (client: Client) => api.delete(`/clients/${client.id}`),
    onSuccess: async () => { setDeleteError(''); await queryClient.invalidateQueries({ queryKey: ['clients'] }); await queryClient.invalidateQueries({ queryKey: ['clients-page'] }) },
    onError: () => setDeleteError(t('clients.deleteFailed')),
  })
  const createExistingContract = useMutation({
    mutationFn: async (payload: { clientId: number; body: Record<string, unknown> }) => (await api.post(`/clients/${payload.clientId}/contracts/from-template`, payload.body)).data,
    onSuccess: async () => { setContractClient(null); await queryClient.invalidateQueries({ queryKey: ['contracts'] }) },
  })

  function confirmDelete(client: Client) {
    const warning = t('clients.deleteConfirm', { code: client.code, name: client.name })
    if (window.confirm(warning)) remove.mutate(client)
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    const client = {
      code: null,
      name: String(data.name).trim(),
      timezone: String(data.timezone).trim(),
      country_id: selectedCountry?.id ?? null,
      city_id:selectedCity?.id ?? null,
      country: selectedCountry?.name ?? null,
      zone: selectedCity?.name ?? null,
      email: String(data.email).trim() || null,
      phone_number: String(data.phone_number).trim() || null,
      address: String(data.address).trim() || null,
      status_id: Number(data.status_id),
      owner_department_id: Number(data.owner_department_id),
      shared_department_ids: sharedDepartments.map(department => department.id).filter(id => id !== Number(data.owner_department_id)),
      parent_client_id: data.parent_client_id ? Number(data.parent_client_id) : null,
      is_active: true,
    }
    const template = contractTemplates.data?.find(item => item.id === Number(selectedTemplateId))
    create.mutate({ onboarding: {
      client,
      contact: null,
      contract: createContract && template ? {
        template_id: template.id,
        expected_template_version: template.version,
        acceptance_date: String(data.acceptance_date),
        start_date: String(data.acceptance_date),
        duration_months: Number(data.duration_months || template.default_duration_months),
        name: String(data.name).trim(),
        idempotency_key: crypto.randomUUID(),
        change_overrides: {},
      } : null,
      source: new URLSearchParams(window.location.search).get('source') === 'DELIVERY_PROJECT' ? 'DELIVERY_PROJECT' : 'CLIENT_SETUP',
    }, location: selectedCountry && selectedCity ? {
      country_id: selectedCountry.id,
      city_code: selectedCity.code,
      name: selectedCity.name,
      zone: selectedCity.name,
      address: String(data.address).trim() || null,
      timezone: String(data.timezone).trim() || null,
      is_active: true,
    } : null, access: accesses.filter(item => item.label.trim()) })
  }
  function submitCountry(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data=Object.fromEntries(new FormData(event.currentTarget)); createCountry.mutate({name:String(data.name).trim(),name_ar:String(data.name_ar).trim(),city_name:String(data.city_name).trim(),city_name_ar:String(data.city_name_ar).trim(),default_timezone:String(data.default_timezone).trim()||null,is_active:true}) }
  function submitCity(event:FormEvent<HTMLFormElement>){event.preventDefault();const data=Object.fromEntries(new FormData(event.currentTarget));createCity.mutate({name:String(data.name).trim(),name_ar:String(data.name_ar).trim()})}

  const createError = (() => {
    if (!create.error || !axios.isAxiosError(create.error)) return null
    const body = create.error.response?.data as {
      error?: { message?: string; details?: { fields?: Array<{ msg?: string }> } }
    } | undefined
    return body?.error?.details?.fields?.[0]?.msg ?? body?.error?.message ?? t('clients.saveFailed')
  })()

  return (
    <Paper sx={{ p: { xs: 1.5, sm: 3 }, maxWidth: '100%', overflow: 'hidden' }}>
      <InactiveClientsKpi />
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'stretch', md: 'center' }} mb={3}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4">{t('clients.title')}</Typography>
          <Typography color="text.secondary">{t('clients.subtitle')}</Typography>
        </Box>
        <TextField
          size="small"
          label={t('clients.search')}
          value={search}
          onChange={(event) => { setSearch(event.target.value); setPage(0) }}
          slotProps={{ input: { startAdornment: <Search sx={{ mr: 1 }} /> } }}
          sx={{ width: { xs: '100%', md: 220 } }}
        />
        <TextField select size="small" label={t('clients.accountStatus')} value={accountStatus} onChange={(event) => { setAccountStatus(event.target.value as 'ACTIVE' | 'INACTIVE' | 'ALL'); setPage(0) }} sx={{ width: { xs: '100%', md: 155 } }}>
          <MenuItem value="ACTIVE">{t('clients.active')}</MenuItem>
          <MenuItem value="INACTIVE">{t('clients.inactive')}</MenuItem>
          <MenuItem value="ALL">{t('clients.allAccounts')}</MenuItem>
        </TextField>
        <TextField select size="small" label={t('clients.clientStatus')} value={clientStatusId} onChange={(event) => { setClientStatusId(event.target.value); setPage(0) }} sx={{ width: { xs: '100%', md: 155 } }}>
          <MenuItem value="">{t('clients.allStatuses')}</MenuItem>
          {statuses.data?.map((status) => <MenuItem key={status.id} value={status.id}>{getLocalizedName(status, language)}</MenuItem>)}
        </TextField>
        <IconButton onClick={() => clients.refetch()} aria-label={t('clients.refresh')}>
          <Refresh />
        </IconButton>
        {hasPermission('client.manage') && (
          <Stack direction={{ xs: 'column', sm: 'row' }} gap={1}><Button fullWidth variant="outlined" onClick={() => setCountryOpen(true)}>{t('clients.countryMaster')}</Button><Button fullWidth variant="contained" startIcon={<Add />} onClick={() => setDialogOpen(true)}>{t('clients.addClient')}</Button></Stack>
        )}
      </Stack>

      {clients.isLoading && <CircularProgress aria-label={t('clients.loading')} />}
      {deleteError && <Alert severity="error" sx={{ mb: 2 }}>{deleteError}</Alert>}
      {clients.isError && <Alert severity="error">{t('clients.loadFailed')}</Alert>}
      {clients.data?.items.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Business sx={{ fontSize: 56, color: 'text.disabled' }} />
          <Typography variant="h6">{t('clients.noClients')}</Typography>
          <Typography color="text.secondary">{t('clients.emptyHint')}</Typography>
        </Box>
      )}
      {!!clients.data?.items.length && (
        <TableContainer sx={{ width: '100%', overflowX: 'auto' }}><Table sx={{ minWidth: 900 }}>
          <TableHead>
            <TableRow>
              <TableCell>{t('clients.code')}</TableCell><TableCell>{t('clients.client')}</TableCell>
              <TableCell>{t('clients.status')}</TableCell><TableCell>{t('clients.timezone')}</TableCell>
              <TableCell>{t('clients.contact')}</TableCell><TableCell>{t('clients.account')}</TableCell><TableCell>{t('clients.actions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {clients.data.items.map((client) => (
              <TableRow hover key={client.id}>
                <TableCell><strong>{client.code}</strong></TableCell>
                <TableCell><Link component={RouterLink} to={`/clients/${client.id}/edit`} state={{clientsList:`${location.pathname}${location.search}`}} underline="hover" fontWeight={700}>{client.name}</Link></TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  {getLocalizedName(statuses.data?.find((status) => status.id === client.status_id), language) || '—'}
                </TableCell>
                <TableCell><span dir="ltr" style={{unicodeBidi:'isolate'}}>{client.timezone}</span></TableCell>
                <TableCell><span dir="ltr" style={{unicodeBidi:'isolate'}}>{client.email ?? client.phone_number ?? '—'}</span></TableCell>
                <TableCell>
                  <Chip size="small" color={client.is_active ? 'success' : 'default'} label={client.is_active ? t('clients.active') : t('clients.inactive')} />
                </TableCell>
                <TableCell><Stack direction="row" flexWrap="wrap" gap={.25}>
                  {hasPermission('client.profile.view') && <IconButton component={RouterLink} to={`/clients/${client.id}/profile`} state={{clientsList:`${location.pathname}${location.search}`}} aria-label={t('clients.profileFor', { name: client.name })} title={t('clients.openProfile')} color="primary"><Assessment /></IconButton>}
                  {hasPermission('client_access.view') && <IconButton component={RouterLink} to={`/clients/${client.id}/edit`} state={{clientsList:`${location.pathname}${location.search}`}} aria-label={t('clients.accessFor', { name: client.name })} title={t('clients.clientAccess')} color="primary"><VpnKey /></IconButton>}
                  {hasPermission('contract.template.apply') && <IconButton onClick={() => setContractClient(client)} aria-label={t('clients.contractFor', { name: client.name })} title={t('clients.contractFromTemplate')}><NoteAdd /></IconButton>}
                  {hasPermission('client.manage') && <IconButton component={RouterLink} to={`/clients/${client.id}/edit`} state={{clientsList:`${location.pathname}${location.search}`}} aria-label={t('clients.editName', { name: client.name })} title={t('clients.editClient')}><Edit /></IconButton>}
                  {hasPermission('client.delete') && <IconButton color="error" disabled={remove.isPending} aria-label={t('clients.deleteName', { name: client.name })} title={t('clients.deleteClient')} onClick={() => confirmDelete(client)}><DeleteOutline /></IconButton>}
                </Stack></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table></TableContainer>
      )}
      {clients.data && <TablePagination component="div" count={clients.data.total} page={page} onPageChange={(_, nextPage) => setPage(nextPage)} rowsPerPage={20} rowsPerPageOptions={[20]} labelRowsPerPage={t('clients.perPage')} sx={{ overflowX: 'auto', '.MuiTablePagination-toolbar': { px: { xs: 0, sm: 2 } } }} />}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={submit}>
          <DialogTitle>{t('clients.addClient')}</DialogTitle>
          <DialogContent>
            {create.isError && <Alert severity="error" sx={{ mb: 2 }}>{createError}</Alert>}
            <Alert severity="info" sx={{ mt: 1 }}>{t('clients.codeAutomatic')}</Alert>
            <TextField name="name" label={t('clients.clientName')} required fullWidth margin="normal" />
            <TextField name="owner_department_id" label={t('clients.ownerDepartment')} select required fullWidth margin="normal" value={ownerDepartmentId} onChange={event => { setOwnerDepartmentId(event.target.value); setSharedDepartments(current => current.filter(department => department.id !== Number(event.target.value))) }}>
              {departments.data?.map(department => <MenuItem key={department.id} value={department.id}>{getLocalizedName(department, language)}</MenuItem>)}
            </TextField>
            <MobileMultiAutocomplete options={(departments.data ?? []).filter(department => department.id !== Number(ownerDepartmentId))} value={sharedDepartments} onChange={(_, value) => setSharedDepartments(value)} getOptionLabel={department => getLocalizedName(department, language)} isOptionEqualToValue={(option, value) => option.id === value.id} renderInput={params => <TextField {...params} label={t('clients.sharedDepartments')} margin="normal" helperText={t('clients.sharedHint')} />} />
            <TextField name="parent_client_id" label={t('clients.parentOptional')} select fullWidth margin="normal" defaultValue=""><MenuItem value="">{t('clients.rootClient')}</MenuItem>{parentClients.data?.map(item=><MenuItem key={item.id} value={item.id}>{item.name} ({item.code})</MenuItem>)}</TextField>
            <TextField name="status_id" label={t('clients.status')} select required fullWidth margin="normal" defaultValue="">
              {statuses.data?.map((status) => <MenuItem key={status.id} value={status.id}>{getLocalizedName(status, language)}</MenuItem>)}
            </TextField>
            <TextField name="timezone" label={t('clients.timezone')} required fullWidth margin="normal" defaultValue="Africa/Cairo" inputProps={{dir:'ltr'}} />
            <Stack direction={{xs:'column',sm:'row'}} spacing={1}>
              <Autocomplete
                fullWidth
                options={countries.data ?? []}
                value={selectedCountry}
                onChange={(_, value) => {setSelectedCountry(value);setSelectedCity(null)}}
                getOptionLabel={(option) => `${getLocalizedName(option, language)} (${option.code})`}
                renderInput={(params) => <TextField {...params} label={t('clients.countryOptional')} margin="normal" />}
              />
              <Autocomplete fullWidth disabled={!selectedCountry} options={(cities.data??[]).filter(city=>city.country_id===selectedCountry?.id)} value={selectedCity} onChange={(_,value)=>setSelectedCity(value)} getOptionLabel={option=>getLocalizedName(option, language)} renderInput={params=><TextField {...params} label={t('clients.cityOptional')} margin="normal"/>}/>
            </Stack>
            <Button size="small" onClick={()=>setCountryOpen(true)}>{t('clients.missingLocation')}</Button>
            {selectedCountry&&<Button size="small" onClick={()=>setCityOpen(true)}>{t('clients.addCityTo', { country: getLocalizedName(selectedCountry, language) })}</Button>}
            <TextField name="email" label={t('clients.supportEmail')} type="email" fullWidth margin="normal" inputProps={{dir:'ltr'}} />
            <TextField name="phone_number" label={t('clients.phone')} fullWidth margin="normal" inputProps={{dir:'ltr'}} />
            <TextField name="address" label={t('clients.address')} fullWidth multiline rows={2} margin="normal" />
            <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
              <FormControlLabel control={<Checkbox checked={createContract} onChange={event => setCreateContract(event.target.checked)} />} label={t('clients.createContract')} />
              {createContract && <>
                <TextField select required fullWidth margin="normal" label={t('clients.contractTemplate')} value={selectedTemplateId} onChange={event => setSelectedTemplateId(event.target.value)}>
                  {contractTemplates.data?.map(template => <MenuItem key={template.id} value={template.id}>{template.name}{template.is_default ? ` (${t('clients.default')})` : ''}</MenuItem>)}
                </TextField>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                  <TextField name="acceptance_date" type="date" required label={t('clients.acceptanceDate')} defaultValue={serverDateInput()} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
                  <TextField name="duration_months" type="number" required label={t('clients.durationMonths')} defaultValue={contractTemplates.data?.find(item => item.id === Number(selectedTemplateId))?.default_duration_months ?? 12} inputProps={{ min: 1, max: 120 }} fullWidth />
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{t('clients.contractNameHint')}</Typography>
              </>}
            </Paper>
            <Stack direction="row" alignItems="center" sx={{ mt: 2 }}>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>{t('clients.accessCredentials')}</Typography>
              <Button startIcon={<Add />} onClick={() => setAccesses(current => [...current, blankAccess()])}>{t('clients.addAccess')}</Button>
            </Stack>
            <Typography variant="body2" color="text.secondary">{t('clients.accessHint')}</Typography>
            {accesses.map((access, index) => <Paper variant="outlined" sx={{ p: 2, mt: 2 }} key={index}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ xs: 'stretch', sm: 'center' }}>
                <TextField select label={t('clients.accessType')} value={access.access_type} onChange={event => setAccesses(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, access_type: event.target.value } : item))} sx={{ minWidth: 160 }}><MenuItem value="SERVER">{t('clients.server')}</MenuItem><MenuItem value="VPN">VPN</MenuItem><MenuItem value="ANYDESK">AnyDesk</MenuItem><MenuItem value="SYSTEM_ADMIN">{t('clients.systemAdmin')}</MenuItem><MenuItem value="OTHER">{t('clients.other')}</MenuItem></TextField>
                <TextField required label={t('clients.label')} value={access.label} onChange={event => setAccesses(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item))} fullWidth />
                <IconButton aria-label={t('clients.removeAccess')} color="error" onClick={() => setAccesses(current => current.filter((_, itemIndex) => itemIndex !== index))}><DeleteOutline /></IconButton>
              </Stack>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ mt: 1 }}><TextField label={t('clients.serverAddress')} value={access.server_or_address} onChange={event => setAccesses(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, server_or_address: event.target.value } : item))} fullWidth /><TextField label={t('clients.username')} value={access.username} autoComplete="off" onChange={event => setAccesses(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, username: event.target.value } : item))} fullWidth /></Stack>
              <TextField label={t('clients.password')} type="password" value={access.password} autoComplete="new-password" onChange={event => setAccesses(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, password: event.target.value } : item))} fullWidth margin="normal" />
              <TextField label={t('clients.internalNotes')} value={access.notes} onChange={event => setAccesses(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, notes: event.target.value } : item))} fullWidth multiline rows={2} />
            </Paper>)}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => { setDialogOpen(false); setAccesses([]); setSelectedCountry(null); setOwnerDepartmentId(''); setSharedDepartments([]) }}>{t('clients.cancel')}</Button>
            <Button type="submit" variant="contained" disabled={create.isPending}>{t('clients.saveClient')}</Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog open={Boolean(contractClient)} onClose={() => setContractClient(null)} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={event => {
          event.preventDefault()
          const data = Object.fromEntries(new FormData(event.currentTarget))
          const template = contractTemplates.data?.find(item => item.id === Number(data.template_id))
          if (!contractClient || !template) return
          createExistingContract.mutate({ clientId: contractClient.id, body: { template_id: template.id, expected_template_version: template.version, acceptance_date: data.acceptance_date, start_date: data.acceptance_date, duration_months: Number(data.duration_months), name: String(data.name).trim() || contractClient.name, change_overrides: {}, idempotency_key: crypto.randomUUID() } })
        }}>
          <DialogTitle>{t('clients.anotherContract', { name: contractClient?.name })}</DialogTitle>
          <DialogContent>
            {createExistingContract.isError && <Alert severity="error" sx={{ mb: 2 }}>{t('clients.contractFailed')}</Alert>}
            <TextField name="template_id" select required fullWidth margin="normal" label={t('clients.contractTemplate')} value={selectedTemplateId} onChange={event => setSelectedTemplateId(event.target.value)}>
              {contractTemplates.data?.map(template => <MenuItem key={template.id} value={template.id}>{template.name}{template.is_default ? ` (${t('clients.default')})` : ''}</MenuItem>)}
            </TextField>
            <TextField name="name" label={t('clients.contractName')} fullWidth margin="normal" defaultValue={contractClient?.name ?? ''} />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
              <TextField name="acceptance_date" type="date" required label={t('clients.acceptanceDate')} defaultValue={serverDateInput()} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
              <TextField name="duration_months" type="number" required label={t('clients.durationMonths')} defaultValue={contractTemplates.data?.find(item => item.id === Number(selectedTemplateId))?.default_duration_months ?? 12} inputProps={{ min: 1, max: 120 }} fullWidth />
            </Stack>
            <Alert severity="info" sx={{ mt: 2 }}>{t('clients.separateContract')}</Alert>
          </DialogContent>
          <DialogActions><Button onClick={() => setContractClient(null)}>{t('clients.cancel')}</Button><Button type="submit" variant="contained" disabled={createExistingContract.isPending}>{t('clients.createContractAction')}</Button></DialogActions>
        </Box>
      </Dialog>
      <Dialog open={countryOpen} onClose={()=>setCountryOpen(false)} fullWidth maxWidth="xs"><Box component="form" onSubmit={submitCountry}><DialogTitle>{t('clients.addCountryCity')}</DialogTitle><DialogContent>{createCountry.isError&&<Alert severity="error">{t('clients.locationExists')}</Alert>}<TextField required name="name" label={t('clients.countryNameEn')} fullWidth margin="normal" helperText={t('clients.countryCodeAutomatic')} inputProps={{dir:'ltr'}}/><TextField required name="name_ar" label={t('clients.countryNameAr')} fullWidth margin="normal" inputProps={{dir:'rtl'}}/><TextField required name="city_name" label={t('clients.cityNameEn')} fullWidth margin="normal" helperText={t('clients.cityExample')} inputProps={{dir:'ltr'}}/><TextField required name="city_name_ar" label={t('clients.cityNameAr')} fullWidth margin="normal" inputProps={{dir:'rtl'}}/><TextField name="default_timezone" label={t('clients.defaultTimezone')} fullWidth margin="normal" inputProps={{dir:'ltr'}}/></DialogContent><DialogActions><Button onClick={()=>setCountryOpen(false)}>{t('clients.cancel')}</Button><Button type="submit" variant="contained" disabled={createCountry.isPending}>{t('clients.saveSelect')}</Button></DialogActions></Box></Dialog>
      <Dialog open={cityOpen} onClose={()=>setCityOpen(false)} fullWidth maxWidth="xs"><Box component="form" onSubmit={submitCity}><DialogTitle>{t('clients.addCityTitle', { country: getLocalizedName(selectedCountry, language) })}</DialogTitle><DialogContent>{createCity.isError&&<Alert severity="error">{t('clients.cityExists')}</Alert>}<TextField required name="name" label={t('clients.cityNameEn')} fullWidth margin="normal" helperText={t('clients.cityCodeAutomatic')} inputProps={{dir:'ltr'}}/><TextField required name="name_ar" label={t('clients.cityNameAr')} fullWidth margin="normal" inputProps={{dir:'rtl'}}/></DialogContent><DialogActions><Button onClick={()=>setCityOpen(false)}>{t('clients.cancel')}</Button><Button type="submit" variant="contained" disabled={createCity.isPending||!selectedCountry}>{t('clients.saveSelect')}</Button></DialogActions></Box></Dialog>
    </Paper>
  )
}
