import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Avatar, Button, Checkbox, FormControlLabel, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import axios from 'axios'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { api } from '../api/client'
import { getLocalizedName } from '../i18n/localizedMasterData'

type Profile = { id: number; name: string; description?: string; risk_level: string; profile_type:string }
type Client = { id: number; name: string }
type Branch = { id: number; name: string }
type Employee = { id: number; full_name: string; username: string; job_title?: string; user_type: string; is_active: boolean }
type Department = { id: number; code: string; name: string; name_ar?:string|null; is_active: boolean }
const jobTitles = ['Fresh Technical Support', 'Technical Support', 'Junior Technical Support', 'Senior Technical Support', 'Team Leader', 'Manager'] as const
const schema = z.object({
  full_name: z.string().min(2), username: z.string().min(3), email: z.string().email(), support_notification_email: z.string().email().optional().or(z.literal('')),
  password: z.string().min(12), phone_number: z.string().optional(),
  department_id: z.coerce.number().optional(), job_title: z.union([z.enum(jobTitles), z.literal('')]).optional(), hire_date: z.string().optional(), primary_profile_id: z.coerce.number().positive(),
  reports_to_user_id: z.coerce.number().optional(),
  user_type: z.enum(['EMPLOYEE', 'CLIENT_PORTAL', 'API_USER']), client_id: z.coerce.number().optional(),
  client_scope_mode: z.enum(['CLIENT_ONLY','CLIENT_AND_DIRECT_CHILDREN','CLIENT_AND_ALL_DESCENDANTS']),
  branch_id: z.coerce.number().optional(), is_active: z.boolean(), participates_in_shifts:z.boolean(), participates_in_operations:z.boolean(), require_password_change: z.boolean(),
})
type Form = z.infer<typeof schema>

export function CreateUserPage() {
  const {t,i18n}=useTranslation();const language=i18n.resolvedLanguage==='ar'?'ar':'en'
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const [profilePicture,setProfilePicture]=useState<File|null>(null)
  const [profilePreview,setProfilePreview]=useState('')
  const profiles = useQuery({ queryKey: ['profiles'], queryFn: async () => (await api.get<Profile[]>('/profiles')).data })
  const clients = useQuery({ queryKey: ['clients'], queryFn: async () => (await api.get<Client[]>('/clients')).data })
  const employees = useQuery({ queryKey: ['users', 'manager-options'], queryFn: async () => (await api.get<Employee[]>('/users?limit=200')).data })
  const departments = useQuery({ queryKey: ['departments'], queryFn: async () => (await api.get<Department[]>('/departments')).data })
  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { user_type: 'EMPLOYEE', client_scope_mode:'CLIENT_ONLY', is_active: true, participates_in_shifts:true, participates_in_operations:true, require_password_change: true } })
  const userType = watch('user_type')
  const clientId = Number(watch('client_id'))
  const branches = useQuery({ queryKey: ['branches', clientId], queryFn: async () => (await api.get<Branch[]>(`/clients/${clientId}/branches`)).data, enabled: userType === 'CLIENT_PORTAL' && clientId > 0 })
  const selected = profiles.data?.find(p => p.id === Number(watch('primary_profile_id')))
  const submit = async (data: Form) => {
    setServerError('')
    try { const response=await api.post('/users', { ...data, profile_picture_url:null, department_id: data.department_id || null, phone_number: data.phone_number?.trim() || null, job_title: data.job_title?.trim() || null, hire_date: data.hire_date || null, reports_to_user_id: data.user_type === 'EMPLOYEE' && data.reports_to_user_id ? data.reports_to_user_id : null, additional_profile_ids: [], client_scope_ids: data.user_type !== 'EMPLOYEE' && data.client_id ? [data.client_id] : [], client_scope_modes:data.user_type!=='EMPLOYEE'&&data.client_id?{[data.client_id]:data.client_scope_mode}:{}, branch_scope_ids: data.user_type === 'CLIENT_PORTAL' && data.branch_id ? [data.branch_id] : [], require_password_change:data.user_type==='API_USER'?false:data.require_password_change, participates_in_shifts:data.user_type==='EMPLOYEE'&&data.participates_in_shifts, participates_in_operations:data.user_type==='EMPLOYEE'&&data.participates_in_operations, administrator_reason: selected?.risk_level === 'CRITICAL' ? 'Approved user creation' : null });if(profilePicture){const form=new FormData();form.append('upload',profilePicture);await api.post(`/users/${response.data.id}/profile-picture`,form)} navigate('/users') }
    catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        const detail = requestError.response?.data?.error?.message
        const validation = requestError.response?.data?.detail?.[0]?.msg
        setServerError(detail ?? validation ?? t('createUser.failed'))
      } else setServerError(t('createUser.failed'))
    }
  }
  return <Paper component="form" onSubmit={handleSubmit(submit)} sx={{ p: 3, maxWidth: 900 }}>
    <Typography variant="h4" gutterBottom>{t('createUser.title')}</Typography>{serverError && <Alert severity="error">{serverError}</Alert>}
    <TextField select label={t('createUser.userType')} fullWidth margin="normal" {...register('user_type')}>
      <MenuItem value="EMPLOYEE">{t('createUser.types.EMPLOYEE')}</MenuItem><MenuItem value="CLIENT_PORTAL">{t('createUser.types.CLIENT_PORTAL')}</MenuItem><MenuItem value="API_USER">API User</MenuItem>
    </TextField>
    {(['full_name','username','email','support_notification_email','phone_number'] as const).map(name => <TextField key={name} label={t(`createUser.fields.${name}`)} fullWidth margin="normal" {...register(name)} error={!!errors[name]} inputProps={name==='username'||name.includes('email')||name==='phone_number'?{dir:'ltr'}:undefined} />)}
    {userType === 'EMPLOYEE' && <Alert severity="info">{t('createUser.employeeCode')}</Alert>}
    {userType === 'EMPLOYEE' && <TextField select label={t('createUser.department')} fullWidth margin="normal" defaultValue="" {...register('department_id')}><MenuItem value="">{t('createUser.notSpecified')}</MenuItem>{departments.data?.map(item => <MenuItem key={item.id} value={item.id}><span dir="ltr">{item.code}</span> — {getLocalizedName(item,language)}</MenuItem>)}</TextField>}
    <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 2 }}><Avatar src={profilePreview||undefined} alt={t('createUser.profilePreview')} sx={{ width: 72, height: 72 }} /><Button component="label" variant="outlined">{t('createUser.choosePhoto')}<input hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={event=>{const file=event.target.files?.[0];if(file){if(profilePreview)URL.revokeObjectURL(profilePreview);setProfilePicture(file);setProfilePreview(URL.createObjectURL(file))}event.target.value='' }}/></Button><Typography variant="caption" color="text.secondary">{t('createUser.photoHelp')}</Typography></Stack>
    {userType === 'EMPLOYEE' && <><TextField select label={t('createUser.jobTitle')} fullWidth margin="normal" defaultValue="" {...register('job_title')}><MenuItem value="">{t('createUser.notSpecified')}</MenuItem>{jobTitles.map(title => <MenuItem key={title} value={title}>{t(`createUser.jobTitles.${title}`)}</MenuItem>)}</TextField><TextField type="date" label={t('createUser.hireDate')} fullWidth margin="normal" {...register('hire_date')} slotProps={{ inputLabel: { shrink: true } }} /></>}
    <Button size="small" onClick={() => setValue('username', String(watch('email') ?? ''))}>{t('createUser.emailUsername')}</Button>
    {userType === 'EMPLOYEE' && <TextField select label={t('createUser.reportsTo')} fullWidth margin="normal" defaultValue="" {...register('reports_to_user_id')}><MenuItem value="">{t('createUser.noManager')}</MenuItem>{employees.data?.filter((item) => item.user_type === 'EMPLOYEE' && item.is_active).map((item) => <MenuItem key={item.id} value={item.id}>{item.full_name} — {item.job_title ?? <span dir="ltr">{item.username}</span>}</MenuItem>)}</TextField>}
    <TextField label={t('createUser.temporaryPassword')} type="password" fullWidth margin="normal" {...register('password')} error={!!errors.password} helperText={errors.password?.message} inputProps={{dir:'ltr'}} />
    <TextField select label={t('createUser.primaryProfile')} fullWidth margin="normal" defaultValue="" {...register('primary_profile_id')} error={!!errors.primary_profile_id}>
      {profiles.data?.filter(profile=>userType==='API_USER'?profile.profile_type==='API_INTEGRATION':profile.profile_type!=='API_INTEGRATION').map(profile => <MenuItem key={profile.id} value={profile.id}>{profile.name}</MenuItem>)}
    </TextField>
    {userType === 'CLIENT_PORTAL' && <>
      <TextField select required label={t('createUser.authorizedClient')} fullWidth margin="normal" defaultValue="" {...register('client_id')}>
        {clients.data?.map(client => <MenuItem key={client.id} value={client.id}>{client.name}</MenuItem>)}
      </TextField>
      <TextField select required label={t('createUser.clientScope')} fullWidth margin="normal" {...register('client_scope_mode')}>{['CLIENT_ONLY','CLIENT_AND_DIRECT_CHILDREN','CLIENT_AND_ALL_DESCENDANTS'].map(scope=><MenuItem key={scope} value={scope}>{t(`createUser.scopes.${scope}`)}</MenuItem>)}</TextField>
      <TextField select required label={t('createUser.authorizedBranch')} fullWidth margin="normal" defaultValue="" {...register('branch_id')}>
        {branches.data?.map(branch => <MenuItem key={branch.id} value={branch.id}>{branch.name}</MenuItem>)}
      </TextField>
      {!branches.isLoading && clientId > 0 && branches.data?.length === 0 && <Alert severity="warning">{t('createUser.branchRequired')}</Alert>}
    </>}
    {userType === 'API_USER' && <><Alert severity="info" sx={{mt:2}}>API users authenticate only through the integration token endpoint. Client scope is optional for general WhatsApp or email intake accounts.</Alert><TextField select label="Authorized client (optional)" fullWidth margin="normal" defaultValue="" {...register('client_id')}><MenuItem value="">All clients / identify from request</MenuItem>{clients.data?.map(client=><MenuItem key={client.id} value={client.id}>{client.name}</MenuItem>)}</TextField>{clientId>0&&<TextField select label="Client scope" fullWidth margin="normal" {...register('client_scope_mode')}>{['CLIENT_ONLY','CLIENT_AND_DIRECT_CHILDREN','CLIENT_AND_ALL_DESCENDANTS'].map(scope=><MenuItem key={scope} value={scope}>{t(`createUser.scopes.${scope}`)}</MenuItem>)}</TextField>}</>}
    {selected && <Alert severity={selected.risk_level === 'CRITICAL' ? 'warning' : 'info'} sx={{ my: 2 }}><strong>{t('createUser.profilePreviewLabel')}</strong> {selected.name} — {selected.description ?? t('createUser.managedBundle')} ({t('createUser.risk',{level:selected.risk_level})})</Alert>}
    <FormControlLabel control={<Checkbox defaultChecked {...register('is_active')} />} label={t('createUser.active')} />
    {userType==='EMPLOYEE'&&<Paper variant="outlined" sx={{p:2,my:2}}><Typography variant="h6">{t('createUser.scheduling')}</Typography><FormControlLabel control={<Checkbox defaultChecked {...register('participates_in_shifts')}/>} label={t('createUser.shifts')}/><FormControlLabel control={<Checkbox defaultChecked {...register('participates_in_operations')}/>} label={t('createUser.operations')}/></Paper>}
    <FormControlLabel control={<Checkbox defaultChecked {...register('require_password_change')} />} label={t('createUser.passwordChange')} />
    <div><Button type="submit" variant="contained" disabled={isSubmitting}>{t('createUser.create')}</Button> <Button onClick={() => navigate('/users')}>{t('createUser.cancel')}</Button></div>
  </Paper>
}
