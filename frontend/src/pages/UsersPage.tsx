import { AccountTree, Add, Email, Search } from '@mui/icons-material'
import { Alert, Avatar, Box, Button, ButtonGroup, Chip, CircularProgress, InputAdornment, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { getLocalizedName } from '../i18n/localizedMasterData'
import { serverDateInput } from '../utils/serverTime'

type User = { id: number; full_name: string; username: string; email: string; department?: string; department_id?: number; job_title?: string; reports_to_user_id?: number; profile_picture_url?: string; is_active: boolean }
type Department = { id: number; name: string; name_ar?:string|null }
type DepartmentNode = { id: number; code: string; name: string; name_ar?:string|null; is_active: boolean; parent_department_id?: number; head_user_id?: number; effective_from?: string; effective_until?: string; path: string[]; path_ar?:string[]; descendant_count: number }
const hierarchyOrientations=new WeakMap<Map<number,User[]>, 'HORIZONTAL'|'VERTICAL'>()

function PersonNode({ user, childrenByManager, departmentNames, orientation=hierarchyOrientations.get(childrenByManager)??'HORIZONTAL' }: { user: User; childrenByManager: Map<number, User[]>; departmentNames:Map<number,string>; orientation?:'HORIZONTAL'|'VERTICAL' }) {
  const {t}=useTranslation()
  const reports = childrenByManager.get(user.id) ?? []
  return <Box sx={{display:'flex',flexDirection:orientation==='HORIZONTAL'?'row':'column',alignItems:orientation==='HORIZONTAL'?'flex-start':'center',gap:2,minWidth:'max-content'}}>
    <Paper component={RouterLink} to={`/users/${user.id}/edit`} variant="outlined" sx={{ position: 'relative', display: 'block', color: 'inherit', textDecoration: 'none', p: 1.5, mb: 1, maxWidth: 520, borderInlineStart: 4, borderInlineStartColor: user.is_active ? 'primary.main' : 'text.disabled', transition: '150ms', '&:hover': { boxShadow: 3, transform: 'translateY(-1px)' } }}>
      <Stack direction="row" spacing={1.5} alignItems="center"><Avatar src={user.profile_picture_url || undefined} alt={user.full_name}>{user.full_name.slice(0, 1)}</Avatar><Box minWidth={0} flexGrow={1}><Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Typography fontWeight={800}>{user.full_name}</Typography><Chip size="small" label={t(user.is_active?'usersPage.active':'usersPage.inactive')} color={user.is_active ? 'success' : 'default'} /></Stack><Typography variant="body2">{user.job_title ?? t('usersPage.employee')}{user.department_id&&departmentNames.has(user.department_id)?` · ${departmentNames.get(user.department_id)}`:user.department?` · ${user.department}`:''}</Typography><Typography variant="caption" color="text.secondary">{t('usersPage.directReports',{count:reports.length})}</Typography></Box></Stack>
    </Paper>
    {reports.length>0&&<Box sx={{display:'flex',flexDirection:orientation==='HORIZONTAL'?'column':'row',gap:2,p:2,borderInlineStart:orientation==='HORIZONTAL'?'2px solid':0,borderTop:orientation==='VERTICAL'?'2px solid':0,borderColor:'divider'}}>{reports.map(report => <PersonNode key={report.id} user={report} childrenByManager={childrenByManager} departmentNames={departmentNames} orientation={orientation}/>)}</Box>}
  </Box>
}

export function UsersPage() {
  const {t,i18n}=useTranslation();const language=i18n.resolvedLanguage==='ar'?'ar':'en'
  const navigate = useNavigate()
  const [view, setView] = useState<'LIST' | 'SMART' | 'DEPARTMENTS'>('LIST')
  const [orientation,setOrientation]=useState<'HORIZONTAL'|'VERTICAL'>('HORIZONTAL')
  const [asOf, setAsOf] = useState(serverDateInput())
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('ALL')
  const [departmentId, setDepartmentId] = useState('ALL')
  const query = useQuery({ queryKey: ['users', 'directory'], queryFn: async () => (await api.get<User[]>('/users', { params: { limit: 200 } })).data })
  const departments = useQuery({ queryKey: ['departments', 'all'], queryFn: async () => (await api.get<Department[]>('/departments', { params: { include_inactive: true } })).data })
  const organization = useQuery({ queryKey: ['department-organization', asOf], queryFn: async () => (await api.get<DepartmentNode[]>('/departments/organization/tree', { params: { as_of: asOf, include_inactive: true } })).data })
  const filtered = useMemo(() => (query.data ?? []).filter(user => {
    const term = search.trim().toLowerCase()
    return (!term || `${user.full_name} ${user.username} ${user.email}`.toLowerCase().includes(term)) && (status === 'ALL' || user.is_active === (status === 'ACTIVE')) && (departmentId === 'ALL' || user.department_id === Number(departmentId))
  }), [query.data, search, status, departmentId])
  if (query.isLoading) return <CircularProgress aria-label={t('usersPage.loading')} />
  if (query.isError) return <Alert severity="error">{t('usersPage.loadFailed')}</Alert>
  const visibleIds = new Set(filtered.map(user => user.id))
  const departmentNames=new Map((departments.data??[]).map(item=>[item.id,getLocalizedName(item,language)]))
  const childrenByManager = new Map<number, User[]>()
  filtered.forEach(user => { if (user.reports_to_user_id && visibleIds.has(user.reports_to_user_id)) childrenByManager.set(user.reports_to_user_id, [...(childrenByManager.get(user.reports_to_user_id) ?? []), user]) })
  const roots = filtered.filter(user => !user.reports_to_user_id || !visibleIds.has(user.reports_to_user_id))
  hierarchyOrientations.set(childrenByManager,orientation)
  return <Paper sx={{ p: { xs: 1.5, sm: 3 } }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} alignItems={{ sm: 'center' }} mb={2}><Typography variant="h4" flexGrow={1}>{t('usersPage.title')}</Typography><Button component={RouterLink} to="/users/create" variant="contained" startIcon={<Add />}>{t('usersPage.create')}</Button></Stack>
    <Stack direction={{ xs: 'column', md: 'row' }} gap={1.5} mb={2}><TextField size="small" label={t('usersPage.search')} value={search} onChange={event => setSearch(event.target.value)} sx={{ minWidth: 260 }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><Search /></InputAdornment> } }} /><TextField select size="small" label={t('usersPage.status')} value={status} onChange={event => setStatus(event.target.value)} sx={{ minWidth: 150 }}><MenuItem value="ALL">{t('usersPage.allStatuses')}</MenuItem><MenuItem value="ACTIVE">{t('usersPage.active')}</MenuItem><MenuItem value="INACTIVE">{t('usersPage.inactive')}</MenuItem></TextField><TextField select size="small" label={t('usersPage.department')} value={departmentId} onChange={event => setDepartmentId(event.target.value)} sx={{ minWidth: 210 }}><MenuItem value="ALL">{t('usersPage.allDepartments')}</MenuItem>{departments.data?.map(item => <MenuItem key={item.id} value={item.id}>{getLocalizedName(item,language)}</MenuItem>)}</TextField><Chip label={t('usersPage.userCount',{count:filtered.length})} /></Stack>
    <Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'center'}} mb={2}><ButtonGroup><Button variant={view === 'LIST' ? 'contained' : 'outlined'} onClick={() => setView('LIST')}>{t('usersPage.list')}</Button><Button startIcon={<AccountTree />} variant={view === 'SMART' ? 'contained' : 'outlined'} onClick={() => setView('SMART')}>{t('usersPage.peopleHierarchy')}</Button><Button startIcon={<AccountTree />} variant={view === 'DEPARTMENTS' ? 'contained' : 'outlined'} onClick={() => setView('DEPARTMENTS')}>{t('usersPage.departmentStructure')}</Button></ButtonGroup>{view==='SMART'&&<ButtonGroup><Button variant={orientation==='HORIZONTAL'?'contained':'outlined'} onClick={()=>setOrientation('HORIZONTAL')}>{t('usersPage.horizontal')}</Button><Button variant={orientation==='VERTICAL'?'contained':'outlined'} onClick={()=>setOrientation('VERTICAL')}>{t('usersPage.vertical')}</Button></ButtonGroup>}{view==='DEPARTMENTS'&&<TextField size="small" type="date" label={t('usersPage.asOf')} value={asOf} onChange={event=>setAsOf(event.target.value)} slotProps={{inputLabel:{shrink:true}}}/>}</Stack>
    {view === 'DEPARTMENTS' ? organization.isLoading ? <CircularProgress aria-label={t('usersPage.loadingStructure')}/> : organization.isError ? <Alert severity="error">{t('usersPage.structureFailed')}</Alert> : <Stack spacing={1}>{organization.data?.map(item=><Paper key={item.id} variant="outlined" sx={{p:1.5,marginInlineStart:{xs:Math.max(0,item.path.length-1)*1.5,sm:Math.max(0,item.path.length-1)*3},borderInlineStart:4,borderInlineStartColor:item.is_active?'primary.main':'text.disabled'}}><Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'center'}}><Box flexGrow={1}><Typography fontWeight={800}><span dir="ltr">{item.code}</span> — {getLocalizedName(item,language)}</Typography><Typography variant="body2" color="text.secondary">{(language==='ar'&&item.path_ar?.length?item.path_ar:item.path).join(' › ')}</Typography></Box><Chip size="small" label={t('usersPage.descendants',{count:item.descendant_count})}/>{item.head_user_id?<Button component={RouterLink} to={`/users/${item.head_user_id}/edit`} size="small">{query.data?.find(user=>user.id===item.head_user_id)?.full_name??t('usersPage.viewHead')}</Button>:<Chip size="small" color="warning" label={t('usersPage.headVacant')}/>}</Stack></Paper>)}</Stack> : !filtered.length ? <Alert severity="info">{t('usersPage.noMatches')}</Alert> : view === 'SMART' ? <Box sx={{ overflowX: 'auto', pb: 1 }}><Stack spacing={2} minWidth={{ md: 560 }}>{roots.map(root => <PersonNode key={root.id} user={root} childrenByManager={childrenByManager} departmentNames={departmentNames}/>)}</Stack></Box> :
      <TableContainer><Table size="small"><TableHead><TableRow><TableCell>{t('usersPage.employee')}</TableCell><TableCell>{t('usersPage.email')}</TableCell><TableCell>{t('usersPage.department')}</TableCell><TableCell>{t('usersPage.reportsTo')}</TableCell><TableCell>{t('usersPage.status')}</TableCell></TableRow></TableHead><TableBody>{filtered.map(user => <TableRow hover key={user.id} onClick={() => navigate(`/users/${user.id}/edit`)} sx={{ cursor: 'pointer' }}><TableCell><Stack direction="row" gap={1} alignItems="center"><Avatar src={user.profile_picture_url || undefined} sx={{ width: 34, height: 34 }}>{user.full_name[0]}</Avatar><Box><Typography fontWeight={700}>{user.full_name}</Typography><Typography variant="caption" dir="ltr">{user.username}</Typography></Box></Stack></TableCell><TableCell><Stack direction="row" gap={.5} alignItems="center" dir="ltr"><Email fontSize="small" color="action" />{user.email}</Stack></TableCell><TableCell>{user.department_id?departmentNames.get(user.department_id)??user.department??'—':user.department??'—'}</TableCell><TableCell>{query.data?.find(manager => manager.id === user.reports_to_user_id)?.full_name ?? '—'}</TableCell><TableCell><Chip size="small" label={t(user.is_active?'usersPage.active':'usersPage.inactive')} color={user.is_active ? 'success' : 'default'} /></TableCell></TableRow>)}</TableBody></Table></TableContainer>}
  </Paper>
}
