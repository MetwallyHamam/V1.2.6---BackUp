import { Alert, Button, FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { getLocalizedName } from '../i18n/localizedMasterData'

export type TicketFormFieldSetting = {
  field_key: string
  label: string
  section: 'PRIMARY' | 'ADDITIONAL'
  display_order: number
  is_visible: boolean
  is_required: boolean
  can_hide: boolean
  can_require: boolean
  can_default: boolean
  default_value?: string
  permission?: string
}

export function TicketFormSettingsPage() {
  const {t,i18n}=useTranslation();const language=i18n.resolvedLanguage==='ar'?'ar':'en'
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['ticket-form-fields'],
    queryFn: async () => (await api.get<TicketFormFieldSetting[]>('/system/ticket-form-fields')).data,
  })
  const preTicketQuery = useQuery({ queryKey: ['pre-ticket-form-fields'], queryFn: async () => (await api.get<TicketFormFieldSetting[]>('/system/pre-ticket-form-fields')).data })
  const ticketTypes = useQuery({ queryKey: ['ticket-types'], queryFn: async () => (await api.get<Array<{ id: number; code: string; name: string; name_ar?:string }>>('/ticket-types')).data })
  const [fields, setFields] = useState<TicketFormFieldSetting[]>([])
  const [preTicketFields, setPreTicketFields] = useState<TicketFormFieldSetting[]>([])
  const [saveError, setSaveError] = useState('')
  useEffect(() => { if (query.data) setFields(query.data) }, [query.data])
  useEffect(() => { if (preTicketQuery.data) setPreTicketFields(preTicketQuery.data) }, [preTicketQuery.data])
  const save = useMutation({
    mutationFn: async () => (await api.put<TicketFormFieldSetting[]>('/system/ticket-form-fields', fields.map((field) => ({ field_key: field.field_key, is_visible: field.is_visible, is_required: field.is_required, default_value: field.can_default ? field.default_value || null : null })))).data,
    onMutate: () => setSaveError(''),
    onError: (caught) => { const response = axios.isAxiosError(caught) ? caught.response?.data as { error?: { message?: string }; detail?: string } | undefined : undefined; setSaveError(response?.error?.message ?? response?.detail ?? t('ticketFormSettingsPage.saveFailed')) },
    onSuccess: async (data) => { setSaveError(''); setFields(data); await queryClient.invalidateQueries({ queryKey: ['ticket-form-fields'] }) },
  })
  const update = (key: string, change: Partial<TicketFormFieldSetting>) => setFields((current) => current.map((field) => {
    if (field.field_key === key) return { ...field, ...change }
    if (change.is_visible === false && ((key === 'product_id' && field.field_key === 'product_module_id') || (key === 'category_id' && field.field_key === 'subcategory_id'))) return { ...field, is_visible: false, is_required: false }
    return field
  }))
  const savePreTicket = useMutation({ mutationFn: async () => (await api.put<TicketFormFieldSetting[]>('/system/pre-ticket-form-fields', preTicketFields.map(field => ({ field_key: field.field_key, is_visible: true, is_required: field.is_required, default_value: null })))).data, onSuccess: async data => { setPreTicketFields(data); await queryClient.invalidateQueries({ queryKey: ['pre-ticket-form-fields'] }) } })

  return <Paper sx={{ p: 3, maxWidth: 1000 }}>
    <Typography variant="h4" gutterBottom>{t('ticketFormSettingsPage.title')}</Typography>
    <Typography color="text.secondary" sx={{ mb: 3 }}>{t('ticketFormSettingsPage.subtitle')}</Typography>
    {save.isError && <Alert severity="error" sx={{ mb: 2 }}>{saveError || t('ticketFormSettingsPage.saveFailed')}</Alert>}
    {save.isSuccess && <Alert severity="success" sx={{ mb: 2 }}>{t('ticketFormSettingsPage.saved')}</Alert>}
    {(['PRIMARY', 'ADDITIONAL'] as const).map((section) => <Stack key={section} spacing={1.25} sx={{ mb: 3 }}>
      <Typography variant="h6">{t(`ticketFormSettingsPage.sections.${section}`)}</Typography>
      {fields.filter((field) => field.section === section).sort((a, b) => a.display_order - b.display_order).map((field) => <Paper key={field.field_key} variant="outlined" sx={{ px: 2, py: 1.25 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} spacing={2}>
          <Typography sx={{ flexGrow: 1 }} fontWeight={600}>{t(`ticketFormSettingsPage.fields.${field.field_key}`,{defaultValue:field.label})}{field.permission && <Typography component="span" variant="caption" color="text.secondary"> · {t('ticketFormSettingsPage.permissionControlled')}</Typography>}</Typography>
          <FormControlLabel control={<Switch checked={field.is_visible} disabled={!field.can_hide || field.is_required} onChange={(event) => update(field.field_key, { is_visible: event.target.checked })} />} label={t('ticketFormSettingsPage.show')} />
          <FormControlLabel control={<Switch checked={field.is_required} disabled={!field.can_require || !field.is_visible} onChange={(event) => update(field.field_key, { is_required: event.target.checked, is_visible: event.target.checked || field.is_visible })} />} label={t('ticketFormSettingsPage.mandatory')} />
          {field.can_default && <TextField select size="small" label={t('ticketFormSettingsPage.defaultValue')} value={field.default_value ?? ''} onChange={(event) => update(field.field_key, { default_value: event.target.value })} sx={{ minWidth: 220 }}><MenuItem value="">{t('ticketFormSettingsPage.noDefault')}</MenuItem>{ticketTypes.data?.map((item) => <MenuItem key={item.id} value={item.code}>{getLocalizedName(item,language)}</MenuItem>)}</TextField>}
        </Stack>
      </Paper>)}
    </Stack>)}
    <Stack spacing={1.25} sx={{ mb: 3 }}>
      <Typography variant="h5">{t('preTickets.formSettings')}</Typography>
      <Typography color="text.secondary">{t('preTickets.formSettingsHelp')}</Typography>
      {savePreTicket.isSuccess && <Alert severity="success">{t('ticketFormSettingsPage.saved')}</Alert>}
      {preTicketFields.map(field => <Paper key={field.field_key} variant="outlined" sx={{ px: 2, py: 1.25 }}><Stack direction={{xs:'column',sm:'row'}} alignItems={{sm:'center'}} spacing={2}><Typography sx={{flexGrow:1}} fontWeight={600}>{field.label}</Typography><FormControlLabel control={<Switch checked disabled />} label={t('ticketFormSettingsPage.show')} /><FormControlLabel control={<Switch checked={field.is_required} onChange={event=>setPreTicketFields(current=>current.map(item=>item.field_key===field.field_key?{...item,is_required:event.target.checked}:item))} />} label={t('ticketFormSettingsPage.mandatory')} /></Stack></Paper>)}
      <Stack direction="row" justifyContent="flex-end"><Button variant="contained" disabled={savePreTicket.isPending || !preTicketFields.length} onClick={()=>savePreTicket.mutate()}>{t(savePreTicket.isPending?'ticketFormSettingsPage.saving':'ticketFormSettingsPage.save')}</Button></Stack>
    </Stack>
    <Stack direction="row" justifyContent="flex-end"><Button variant="contained" disabled={save.isPending || !fields.length} onClick={() => save.mutate()}>{t(save.isPending?'ticketFormSettingsPage.saving':'ticketFormSettingsPage.save')}</Button></Stack>
  </Paper>
}
