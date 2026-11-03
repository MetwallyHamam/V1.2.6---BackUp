import { Add, AutoAwesome, Event, Work } from '@mui/icons-material'
import { Paper, SpeedDial, SpeedDialAction, Stack, Tab, Tabs } from '@mui/material'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { InternalOperationsPage } from './InternalOperationsPage'
import { OperationalReportsPage } from './OperationalReportsPage'
import { SchedulingOverviewPage } from './SchedulingOverviewPage'
import { SchedulingSetupPage } from './SchedulingSetupPage'
import { SchedulingWorkloadPage } from './SchedulingWorkloadPage'
import { ShiftsPage } from './ShiftsPage'
import { VisitOperationsPage } from './VisitOperationsPage'
import { ShiftMastersPanel } from './ShiftMastersPanel'
import { OperationTemplatesPanel } from './OperationTemplatesPanel'

type Section='overview'|'planner'|'workload'|'setup'
type PlannerSource='calendar'|'internal'|'visits'|'templates'

export function OperationsWorkspacePage(){
  const {t}=useTranslation()
  const {hasPermission}=useAuth(),location=useLocation(),navigate=useNavigate(),[searchParams]=useSearchParams()
  const canShift=hasPermission('shift.view'),canInternal=hasPermission('internal_operation.view'),canVisits=hasPermission('visit.entitlement.view'),canSetup=hasPermission('shift.manage')||hasPermission('internal_operation.manage')||hasPermission('internal_operation.type.manage')
  const legacyVisits=location.pathname==='/visit-operations'||searchParams.get('section')==='visits'
  const legacyReports=location.pathname==='/operational-reports'||searchParams.get('section')==='reports'
  const requested=searchParams.get('section')
  const section:Section=legacyReports?'overview':requested==='planner'||requested==='operations'||requested==='calendar'?'planner':requested==='workload'?'workload':requested==='setup'?'setup':'overview'
  const canTemplates=hasPermission('shift.manage')||hasPermission('internal_operation.template.manage')||hasPermission('internal_operation.manage')
  const requestedSource=legacyVisits?'visits':searchParams.get('job')==='visits'?'visits':searchParams.get('job')==='internal'||requested==='operations'?'internal':searchParams.get('job')==='templates'?'templates':'calendar'
  const source:PlannerSource=requestedSource==='templates'&&canTemplates?'templates':requestedSource==='visits'&&canVisits?'visits':requestedSource==='internal'&&canInternal?'internal':canShift?'calendar':canInternal?'internal':'visits'
  const tabs=[{value:'overview' as const,label:t('operationsWorkspace.overview'),visible:canShift||canInternal||canVisits},{value:'planner' as const,label:t('operationsWorkspace.planner'),visible:canShift||canInternal||canVisits},{value:'workload' as const,label:t('operationsWorkspace.workload'),visible:canShift},{value:'setup' as const,label:t('operationsWorkspace.setup'),visible:canSetup}].filter(row=>row.visible)
  const active=tabs.some(row=>row.value===section)?section:tabs[0]?.value??'overview'
  const quickActions=[
    {name:t('operationsWorkspace.quickShift'),icon:<Event/>,visible:hasPermission('shift.create')||hasPermission('shift.manage'),url:'/internal-operations?section=planner&job=calendar&create=shift'},
    {name:t('operationsWorkspace.generateShifts'),icon:<AutoAwesome/>,visible:hasPermission('shift.manage'),url:'/internal-operations?section=planner&job=calendar&create=generate'},
    {name:t('operationsWorkspace.quickOperation'),icon:<Work/>,visible:hasPermission('internal_operation.create')||hasPermission('internal_operation.manage'),url:'/internal-operations?section=planner&job=internal&create=operation'},
    {name:t('operationsWorkspace.generateOperations'),icon:<AutoAwesome/>,visible:hasPermission('internal_operation.manage'),url:'/internal-operations?section=planner&job=internal&create=generate'},
    {name:t('operationsWorkspace.scheduleVisit'),icon:<Work/>,visible:canVisits,url:'/internal-operations?section=planner&job=visits'},
  ].filter(row=>row.visible)
  return <>
    <Paper sx={{mb:2}}><Tabs value={active} onChange={(_,value:Section)=>navigate(`/internal-operations?section=${value}`)} variant="scrollable" scrollButtons="auto" aria-label={t('operationsWorkspace.sections')}>{tabs.map(row=><Tab key={row.value} value={row.value} label={row.label}/>)}</Tabs></Paper>
    {active==='overview'&&(legacyReports?<OperationalReportsPage/>:<SchedulingOverviewPage/>)}
    {active==='planner'&&<><Paper sx={{mb:2}}><Tabs value={source} onChange={(_,value:PlannerSource)=>navigate(`/internal-operations?section=planner&job=${value}`)} variant="scrollable" scrollButtons="auto" aria-label={t('operationsWorkspace.sources')}>{canShift&&<Tab value="calendar" label={t('operationsWorkspace.calendar')}/>}{canInternal&&<Tab value="internal" label={t('operationsWorkspace.internalOperations')}/>}{canVisits&&<Tab value="visits" label={t('operationsWorkspace.fieldVisits')}/>}{canTemplates&&<Tab value="templates" label={t('operationsWorkspace.advancedTemplates')}/>}</Tabs></Paper>{source==='calendar'&&canShift&&<ShiftsPage/>}{source==='internal'&&canInternal&&<InternalOperationsPage/>}{source==='visits'&&canVisits&&<VisitOperationsPage/>}{source==='templates'&&canTemplates&&<Stack spacing={2}>{hasPermission('shift.manage')&&<ShiftMastersPanel section="TEMPLATES" showSmart={false}/>} {(hasPermission('internal_operation.template.manage')||hasPermission('internal_operation.manage'))&&<OperationTemplatesPanel/>}</Stack>}</>}
    {active==='workload'&&canShift&&<SchedulingWorkloadPage/>}
    {active==='setup'&&canSetup&&<SchedulingSetupPage/>}
    {quickActions.length>0&&<SpeedDial ariaLabel={t('operationsWorkspace.quickActions')} icon={<Add/>} sx={{display:{xs:'flex',md:'none'},position:'fixed',right:20,bottom:20}}>{quickActions.map(row=><SpeedDialAction key={row.name} icon={row.icon} slotProps={{tooltip:{title:row.name,open:true}}} onClick={()=>navigate(row.url)}/>)}</SpeedDial>}
  </>
}
