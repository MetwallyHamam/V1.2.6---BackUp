import { Alert, Avatar, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { getLocalizedName } from '../i18n/localizedMasterData'

type User = { id: number; full_name: string; username: string; email: string; support_notification_email?: string; employee_code?: string; phone_number?: string; department?: string; department_id?: number; job_title?: string; profile_picture_url?: string; hire_date?: string; reports_to_user_id?: number; user_type: string; is_active: boolean; participates_in_shifts:boolean;participates_in_operations:boolean; require_password_change: boolean; last_login_at?: string }
type Department = { id: number; code: string; name: string; name_ar?:string|null }
const jobTitles = ['Fresh Technical Support', 'Technical Support', 'Junior Technical Support', 'Senior Technical Support', 'Team Leader', 'Manager']
type Profile = { id: number; code: string; name: string; profile_type: string }
type Assignment = { id: number; profile_id: number; profile_code: string; profile_name: string; is_primary: boolean; valid_to?: string }
type OrganizationHistory = { memberships: Array<{id:number;department_id:number;effective_from:string;effective_until?:string;is_primary:boolean}>; reporting_lines: Array<{id:number;manager_user_id:number;effective_from:string;effective_until?:string}> }
type PermissionAccess = { effective_permissions:string[]; profile_permissions:Array<{permission_code:string;profile_id:number;profile_code:string;profile_name:string;is_primary:boolean;active:boolean}>; overrides:Array<{id:number;permission_code:string;effect:'ALLOW'|'DENY';scope_type:string;scope_reference_id?:number;valid_from:string;valid_to?:string;reason:string;approved_by_name?:string;created_by_name?:string;active:boolean}> }

export function EditUserPage() {
  const {t,i18n}=useTranslation();const language=i18n.resolvedLanguage==='ar'?'ar':'en',locale=language==='ar'?'ar-EG':'en-US'
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { hasPermission } = useAuth()
  const [error, setError] = useState('')
  const [resetOpen, setResetOpen] = useState(false)
  const [resetSuccess, setResetSuccess] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const query = useQuery({ queryKey: ['user', id], queryFn: async () => (await api.get<User>(`/users/${id}`)).data })
  const employees = useQuery({ queryKey: ['users', 'manager-options'], queryFn: async () => (await api.get<User[]>('/users?limit=200')).data })
  const departments = useQuery({ queryKey: ['departments'], queryFn: async () => (await api.get<Department[]>('/departments')).data })
  const assignments = useQuery({ queryKey: ['user-profiles', id], queryFn: async () => (await api.get<Assignment[]>(`/users/${id}/profiles`)).data, enabled: hasPermission('profile.manage') })
  const permissionAccess = useQuery({ queryKey: ['user-permission-access', id], queryFn: async () => (await api.get<PermissionAccess>(`/users/${id}/permission-access`)).data, enabled: hasPermission('profile.manage') })
  const organizationHistory = useQuery({ queryKey: ['user-organization-history', id], queryFn: async () => (await api.get<OrganizationHistory>(`/users/${id}/organization-history`)).data })
  const profiles = useQuery({ queryKey: ['profiles'], queryFn: async () => (await api.get<Profile[]>('/profiles')).data, enabled: hasPermission('profile.manage') })
  const update = useMutation({
    mutationFn: async (data: Record<string, unknown>) => api.patch(`/users/${id}`, data),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['users'] }); navigate('/users') },
    onError: (requestError) => setError(axios.isAxiosError(requestError) ? requestError.response?.data?.error?.message ?? t('editUser.errors.update') : t('editUser.errors.update')),
  })
  const resetPassword = useMutation({
    mutationFn: async (data: Record<string, unknown>) => api.post(`/users/${id}/reset-password`, data),
    onSuccess: async () => { setResetOpen(false); setResetSuccess(true); setError(''); await queryClient.invalidateQueries({ queryKey: ['user', id] }) },
    onError: (requestError) => setError(axios.isAxiosError(requestError) ? requestError.response?.data?.error?.message ?? t('editUser.errors.password') : t('editUser.errors.password')),
  })
  const assignProfile = useMutation({
    mutationFn: async (data: Record<string, unknown>) => api.post(`/users/${id}/profiles`, data),
    onSuccess: async () => { setProfileOpen(false); setError(''); await queryClient.invalidateQueries({ queryKey: ['user-profiles', id] }) },
    onError: (requestError) => setError(axios.isAxiosError(requestError) ? requestError.response?.data?.error?.message ?? t('editUser.errors.profile') : t('editUser.errors.profile')),
  })
  const removeProfile = useMutation({
    mutationFn: async (profileId: number) => api.delete(`/users/${id}/profiles/${profileId}`),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['user-profiles', id] }),
    onError: (requestError) => setError(axios.isAxiosError(requestError) ? requestError.response?.data?.error?.message ?? t('editUser.errors.removeProfile') : t('editUser.errors.removeProfile')),
  })
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget))
    update.mutate({
      full_name: String(values.full_name).trim(), email: String(values.email).trim(), support_notification_email: String(values.support_notification_email).trim() || null,
      phone_number: String(values.phone_number).trim() || null,
      department_id: values.department_id ? Number(values.department_id) : null,
      job_title: String(values.job_title).trim() || null,
      profile_picture_url: String(values.profile_picture_url).trim() || null,
      hire_date: values.hire_date || null,
      reports_to_user_id: values.reports_to_user_id ? Number(values.reports_to_user_id) : null,
      is_active: values.is_active === 'true',
      participates_in_shifts: values.participates_in_shifts === 'true',
      participates_in_operations: values.participates_in_operations === 'true',
      require_password_change: values.require_password_change === 'true',
    })
  }
  function submitReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget))
    resetPassword.mutate({ temporary_password: values.temporary_password, reason: values.reason })
  }
  function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget))
    assignProfile.mutate({ profile_id: Number(values.profile_id), is_primary: values.is_primary === 'true', reason: String(values.reason).trim() || null })
  }
  async function downloadApiDocumentation(){
    const response=await api.get(`/integrations/api-users/${id}/documentation`,{responseType:'blob'})
    const url=URL.createObjectURL(response.data);const link=document.createElement('a');link.href=url;link.download=`supporthub-api-${query.data?.username??id}.md`;link.click();URL.revokeObjectURL(url)
  }
  const formatDate = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString(locale)
  if (query.isLoading) return <CircularProgress />
  if (query.isError || !query.data) return <Alert severity="error">{t('editUser.loadFailed')}</Alert>
  const user = query.data
  return <><Paper component="form" key={user.id} onSubmit={submit} sx={{ p: 3, maxWidth: 800 }}>
    <Typography variant="h4">{t('editUser.title')}</Typography><Typography color="text.secondary" mb={2}><span dir="ltr">{user.username}</span> · {t(`editUser.types.${user.user_type}`, { defaultValue: user.user_type.replaceAll('_', ' ') })}</Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {resetSuccess && <Alert severity="success" sx={{ mb: 2 }}>{t('editUser.passwordSuccess')}</Alert>}
    <TextField required name="full_name" label={t('editUser.fullName')} defaultValue={user.full_name} fullWidth margin="normal" />
    <TextField required type="email" name="email" label={t('editUser.email')} defaultValue={user.email} fullWidth margin="normal" inputProps={{ dir: 'ltr' }} />
    <TextField type="email" name="support_notification_email" label={t('editUser.notificationEmail')} defaultValue={user.support_notification_email ?? ''} fullWidth margin="normal" helperText={t('editUser.notificationHelp')} inputProps={{ dir: 'ltr' }} />
    <Stack direction="row" spacing={2} alignItems="center" sx={{ my: 1 }}><Avatar src={user.profile_picture_url || undefined} alt={user.full_name} sx={{ width: 64, height: 64 }} /><TextField type="url" name="profile_picture_url" label={t('editUser.pictureUrl')} defaultValue={user.profile_picture_url ?? ''} fullWidth helperText={t('editUser.pictureHelp')} inputProps={{ dir: 'ltr' }} /></Stack>
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}><TextField label={t('editUser.employeeCode')} value={user.employee_code ?? t('editUser.notApplicable')} disabled helperText={t('editUser.generated')} fullWidth margin="normal" inputProps={{ dir: 'ltr' }} /><TextField name="phone_number" label={t('editUser.phone')} defaultValue={user.phone_number ?? ''} fullWidth margin="normal" inputProps={{ dir: 'ltr' }} /></Stack>
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}><TextField select name="department_id" label={t('editUser.department')} defaultValue={user.department_id ?? ''} fullWidth margin="normal"><MenuItem value="">{t('editUser.notSpecified')}</MenuItem>{departments.data?.map(item => <MenuItem key={item.id} value={item.id}><span dir="ltr">{item.code}</span> — {getLocalizedName(item, language)}</MenuItem>)}</TextField><TextField select name="job_title" label={t('editUser.jobTitle')} defaultValue={user.job_title ?? ''} fullWidth margin="normal"><MenuItem value="">{t('editUser.notSpecified')}</MenuItem>{jobTitles.map(title => <MenuItem key={title} value={title}>{t(`editUser.jobTitles.${title}`)}</MenuItem>)}</TextField><TextField type="date" name="hire_date" label={t('editUser.hireDate')} defaultValue={user.hire_date ?? ''} fullWidth margin="normal" slotProps={{ inputLabel: { shrink: true } }} /></Stack>
    {user.user_type === 'EMPLOYEE' && <TextField select name="reports_to_user_id" label={t('editUser.reportsTo')} defaultValue={user.reports_to_user_id ?? ''} fullWidth margin="normal"><MenuItem value="">{t('editUser.noManager')}</MenuItem>{employees.data?.filter((item) => item.id !== user.id && item.user_type === 'EMPLOYEE' && item.is_active).map((item) => <MenuItem key={item.id} value={item.id}>{item.full_name} — {item.job_title ? t(`editUser.jobTitles.${item.job_title}`, { defaultValue: item.job_title }) : <span dir="ltr">{item.username}</span>}</MenuItem>)}</TextField>}
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} my={2}><FormControlLabel control={<Switch name="is_active" value="true" defaultChecked={user.is_active} />} label={t('editUser.active')} /><FormControlLabel control={<Switch name="require_password_change" value="true" defaultChecked={user.require_password_change} />} label={t('editUser.passwordChange')} /></Stack>
    {user.user_type==='EMPLOYEE'&&<Paper variant="outlined" sx={{p:2,mb:2}}><Typography variant="h6">{t('editUser.scheduling')}</Typography><Typography color="text.secondary" variant="body2" mb={1}>{t('editUser.schedulingHelp')}</Typography><Stack direction={{xs:'column',sm:'row'}}><FormControlLabel control={<Switch name="participates_in_shifts" value="true" defaultChecked={user.participates_in_shifts}/>} label={t('editUser.shifts')}/><FormControlLabel control={<Switch name="participates_in_operations" value="true" defaultChecked={user.participates_in_operations}/>} label={t('editUser.operations')}/></Stack></Paper>}
    <Typography variant="body2" color="text.secondary" mb={2}>{t('editUser.lastLogin', { date: user.last_login_at ? new Date(user.last_login_at).toLocaleString(locale) : t('editUser.never') })}</Typography>
    {user.user_type === 'EMPLOYEE' && <Paper variant="outlined" sx={{p:2,mb:2}}><Typography variant="h6">{t('editUser.organizationHistory')}</Typography>{organizationHistory.isLoading&&<CircularProgress size={22}/>}<Stack spacing={.75} mt={1}>{organizationHistory.data?.memberships.map(item=>{const department=departments.data?.find(entry=>entry.id===item.department_id);return <Typography key={`department-${item.id}`} variant="body2">{t('editUser.departmentPeriod',{name:department?getLocalizedName(department,language):`#${item.department_id}`,from:formatDate(item.effective_from),to:item.effective_until?formatDate(item.effective_until):t('editUser.current')})}</Typography>})}{organizationHistory.data?.reporting_lines.map(item=><Typography key={`manager-${item.id}`} variant="body2">{t('editUser.managerPeriod',{name:employees.data?.find(employee=>employee.id===item.manager_user_id)?.full_name??`#${item.manager_user_id}`,from:formatDate(item.effective_from),to:item.effective_until?formatDate(item.effective_until):t('editUser.current')})}</Typography>)}</Stack>{organizationHistory.data&&!organizationHistory.data.memberships.length&&!organizationHistory.data.reporting_lines.length&&<Typography color="text.secondary" variant="body2">{t('editUser.noOrganization')}</Typography>}</Paper>}
    {hasPermission('profile.manage') && <Paper variant="outlined" sx={{ p: 2, mb: 2 }}><Stack direction="row" alignItems="center" mb={1}><Typography variant="h6" sx={{ flexGrow: 1 }}>{t('editUser.assignedProfiles')}</Typography><Button type="button" onClick={() => setProfileOpen(true)}>{t('editUser.addPrimary')}</Button></Stack>{assignments.isLoading && <CircularProgress size={24} />}{assignments.data?.map((item) => <Stack key={item.id} direction="row" spacing={1} alignItems="center" sx={{ py: 0.75 }}><Typography sx={{ flexGrow: 1 }}>{item.profile_name} <Typography component="span" variant="caption" color="text.secondary" dir="ltr">({item.profile_code})</Typography></Typography>{item.is_primary && <Chip size="small" color="primary" label={t('editUser.primary')} />}{item.valid_to && <Chip size="small" label={t('editUser.until',{date:new Date(item.valid_to).toLocaleDateString(locale)})} />}{!item.is_primary && <Button type="button" size="small" color="error" disabled={removeProfile.isPending} onClick={() => removeProfile.mutate(item.profile_id)}>{t('editUser.remove')}</Button>}</Stack>)}</Paper>}
    {hasPermission('profile.manage') && <Paper variant="outlined" sx={{p:2,mb:2}}><Typography variant="h6">{t('editUser.permissionSources')}</Typography><Typography variant="body2" color="text.secondary" mb={1}>{t('editUser.permissionHelp')}</Typography>{permissionAccess.isLoading&&<CircularProgress size={24}/>} {permissionAccess.isError&&<Alert severity="error">{t('editUser.permissionFailed')}</Alert>}<Typography fontWeight={700} mt={1}>{t('editUser.directOverrides')}</Typography>{permissionAccess.data?.overrides.map(item=><Paper key={item.id} variant="outlined" sx={{p:1.25,my:.75,borderColor:item.active?(item.effect==='ALLOW'?'success.main':'error.main'):'divider'}}><Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'center'}}><Typography fontFamily="monospace" flexGrow={1} dir="ltr">{item.permission_code}</Typography><Chip size="small" color={item.effect==='ALLOW'?'success':'error'} label={t(`editUser.effects.${item.effect}`)}/><Chip size="small" variant="outlined" label={item.active?t('usersPage.active'):t('editUser.expired')}/></Stack><Typography variant="body2">{item.reason}</Typography><Typography variant="caption" color="text.secondary">{t('editUser.overrideMeta',{from:new Date(item.valid_from).toLocaleString(locale),to:item.valid_to?new Date(item.valid_to).toLocaleString(locale):t('editUser.untilRevoked'),approver:item.approved_by_name??t('editUser.unknown'),scope:`${item.scope_type}${item.scope_reference_id?` #${item.scope_reference_id}`:''}`})}</Typography></Paper>)}{permissionAccess.data&&!permissionAccess.data.overrides.length&&<Typography variant="body2" color="text.secondary">{t('editUser.noOverrides')}</Typography>}<Typography fontWeight={700} mt={2}>{t('editUser.effectivePermissions',{count:(permissionAccess.data?.effective_permissions.length??0).toLocaleString(locale)})}</Typography><Stack direction="row" useFlexGap flexWrap="wrap" gap={.75} mt={1}>{permissionAccess.data?.effective_permissions.map(code=><Chip key={code} size="small" label={code} sx={{direction:'ltr'}}/>)}</Stack><Typography variant="caption" color="text.secondary" display="block" mt={1}>{t('editUser.profileSourceCount',{count:(permissionAccess.data?.profile_permissions.filter(item=>item.active).length??0).toLocaleString(locale)})}</Typography></Paper>}
    <Button type="submit" variant="contained" disabled={update.isPending}>{update.isPending ? t('editUser.saving') : t('editUser.save')}</Button><Button type="button" color="warning" onClick={() => setResetOpen(true)} sx={{ marginInlineStart: 1 }}>{t('editUser.resetPassword')}</Button>{user.user_type==='API_USER'&&<Button type="button" onClick={downloadApiDocumentation} sx={{marginInlineStart:1}}>Download API documentation</Button>}<Button type="button" onClick={() => navigate('/users')} sx={{ marginInlineStart: 1 }}>{t('editUser.cancel')}</Button>
  </Paper>
  <Dialog open={resetOpen} onClose={() => setResetOpen(false)} fullWidth maxWidth="sm"><form onSubmit={submitReset}><DialogTitle>{t('editUser.resetTitle',{name:user.full_name})}</DialogTitle><DialogContent><Alert severity="warning" sx={{ mb: 2 }}>{t('editUser.resetWarning')}</Alert><TextField required type="password" name="temporary_password" label={t('editUser.temporaryPassword')} fullWidth margin="normal" inputProps={{ minLength: 12, dir:'ltr' }} helperText={t('editUser.passwordHelp')} /><TextField required name="reason" label={t('editUser.adminReason')} fullWidth multiline rows={2} margin="normal" inputProps={{ minLength: 5 }} /></DialogContent><DialogActions><Button onClick={() => setResetOpen(false)}>{t('editUser.cancel')}</Button><Button type="submit" color="warning" variant="contained" disabled={resetPassword.isPending}>{t('editUser.resetPassword')}</Button></DialogActions></form></Dialog>
  <Dialog open={profileOpen} onClose={() => setProfileOpen(false)} fullWidth maxWidth="sm"><form onSubmit={submitProfile}><DialogTitle>{t('editUser.assignProfile')}</DialogTitle><DialogContent><TextField required select name="profile_id" label={t('editUser.profile')} fullWidth margin="normal" defaultValue="">{profiles.data?.filter((item) => item.profile_type === (user.user_type==='API_USER'?'API_INTEGRATION':user.user_type) || item.profile_type === 'ADMINISTRATOR').map((item) => <MenuItem key={item.id} value={item.id}>{item.name} <span dir="ltr">({item.code})</span></MenuItem>)}</TextField><FormControlLabel control={<Switch name="is_primary" value="true" />} label={t('editUser.makePrimary')} /><TextField required name="reason" label={t('editUser.assignmentReason')} fullWidth multiline rows={2} margin="normal" inputProps={{ minLength: 5 }} /></DialogContent><DialogActions><Button onClick={() => setProfileOpen(false)}>{t('editUser.cancel')}</Button><Button type="submit" variant="contained" disabled={assignProfile.isPending}>{t('editUser.applyProfile')}</Button></DialogActions></form></Dialog></>
}
