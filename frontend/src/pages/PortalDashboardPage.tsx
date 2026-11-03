import { ServiceManagementWidget } from '../components/ServiceManagementCards'
import { PersonalDashboardGrid } from '../components/PersonalDashboardGrid'
import { serverDateInput } from '../utils/serverTime'
import { AccessTime, Add, Assessment, CheckCircle, ConfirmationNumber, Download, ErrorOutline, PendingActions, Savings } from '@mui/icons-material'
import { Alert, Box, Button, Card, CardActionArea, CardContent, Chip, Grid, LinearProgress, Paper, Stack, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

type Insights = {
  clients: Array<{id:number;name:string}>
  contracts: Array<{id:number;number:string;name:string;start_date:string;end_date:string;days_to_expiry:number;included_request_limit?:number;support_summary?:string}>
  coverage: {products:string[];modules:string[];services:string[]}
  sla_targets: Array<{service:string;priority:string;first_response_minutes:number;resolution_minutes:number}>
  support_calendars: Array<{id:number;name:string;timezone:string;days:Array<{weekday:number;start_time:string;end_time:string;is_working_day:boolean}>}>
  metrics: {total_requests:number;incident_count:number;closed_count:number;pending_count:number;sla_evaluated:number;sla_met:number;sla_breached:number;sla_compliance_percent?:number;total_resolution_lifecycle_hours:number;average_resolution_hours?:number;feedback_count:number;average_feedback_rating?:number;saved_business_hours:number;sla_target_business_hours:number;spent_business_hours:number;total_working_hours:number;sla_evidence_excluded:number;customer_pending_minutes_excluded:number;millensys_pending_minutes_included:number;escalation_minutes:number}
  calculation_methods: Array<{name:string;formula:string;details:string}>
  measurement_notes: string[]
}

export function PortalDashboardPage() {
  const { t, i18n } = useTranslation()
  const duration = (minutes:number) => minutes < 60 ? t('time.minutes', { count: minutes }) : t('time.hours', { count: Math.round(minutes / 6) / 10 })
  const navigate = useNavigate()
  const today = serverDateInput(); const [dateFrom,setDateFrom]=useState(`${today.slice(0,8)}01`); const [dateTo,setDateTo]=useState(today)
  const period={date_from:dateFrom,date_to:dateTo}
  const insights = useQuery({ queryKey: ['portal-contract-insights',period], queryFn: async () => (await api.get<Insights>('/portal/contract-insights',{params:period})).data })
  const data = insights.data
  const metrics = data?.metrics
  const cards = [
    [<ConfirmationNumber color="primary" />, metrics?.total_requests, t('portalDashboard.metrics.contractRequests'), 'all'],
    [<Assessment color="info" />, metrics?.incident_count, t('portalDashboard.metrics.incidents'), 'incident'],
    [<CheckCircle color="success" />, metrics?.closed_count, t('portalDashboard.metrics.closedRequests'), 'closed'],
    [<PendingActions color="warning" />, metrics?.pending_count, t('portalDashboard.metrics.pendingRequests'), 'pending'],
    [<ErrorOutline color="error" />, metrics?.sla_breached, t('portalDashboard.metrics.slaBreaches'), 'sla-breached'],
    [<Savings color={metrics && metrics.saved_business_hours < 0 ? 'error' : 'success'} />, metrics?.saved_business_hours, t('portalDashboard.metrics.netSaved'), 'closed'],
    [<AccessTime color="primary" />, metrics?.total_working_hours, t('portalDashboard.metrics.workingHours'), 'closed'],
  ] as const
  async function exportReport(){const response=await api.get('/portal/contract-report.xlsx',{params:period,responseType:'blob'});const url=URL.createObjectURL(response.data);const link=document.createElement('a');link.href=url;link.download=`client_support_report_${dateFrom}_${dateTo}.xlsx`;link.click();URL.revokeObjectURL(url)}
  return <Stack spacing={3}>
    <Paper variant="outlined" sx={{p:1.5}}><Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'center'}}><Typography flex={1} fontWeight={700}>{t('portalDashboard.creationOptions')}</Typography><Button variant="outlined" onClick={()=>navigate('/portal/tickets/create?method=mosaic')}>{t('portalDashboard.createMosaic')}</Button></Stack></Paper>
    <Paper sx={{ p: 4, background: 'linear-gradient(120deg, #145da0, #0b8f87)', color: 'white' }}>
      <Typography variant="h3">{t('portalDashboard.title')}</Typography>
      <Typography sx={{ mt: 1, mb: 3 }}>{t('portalDashboard.subtitle')}</Typography>
      <Button variant="contained" color="inherit" startIcon={<Add />} onClick={() => navigate('/portal/tickets/create')}>{t('portalTickets.create')}</Button>
    </Paper>
    <Paper variant="outlined" sx={{p:2}}><Stack direction={{xs:'column',sm:'row'}} spacing={1} alignItems={{sm:'center'}}><Typography fontWeight={700} flexGrow={1}>{t('portalDashboard.reportingPeriod')}</Typography><TextField size="small" type="date" label={t('portalDashboard.from')} value={dateFrom} onChange={event=>setDateFrom(event.target.value)} slotProps={{inputLabel:{shrink:true}}}/><TextField size="small" type="date" label={t('portalDashboard.to')} value={dateTo} onChange={event=>setDateTo(event.target.value)} slotProps={{inputLabel:{shrink:true}}}/><Button startIcon={<Download/>} variant="contained" onClick={exportReport}>{t('portalDashboard.exportReport')}</Button></Stack></Paper>
    {insights.isError && <Alert severity="error">{t('portalDashboard.loadFailed')}</Alert>}
    {insights.isLoading && <LinearProgress />}
    <PersonalDashboardGrid storageKey="supporthub-portal-home-service-widgets" tiles={[
      {code:'service_change_requests',width:6,content:<ServiceManagementWidget category="changes" filters={period} portal/>},
      {code:'service_problems',width:6,content:<ServiceManagementWidget category="problems" filters={period} portal/>},
    ]}/>
    {data && !data.contracts.length && <Alert severity="warning">{t('portalDashboard.noContract')}</Alert>}
    {data?.contracts.map(contract => <Paper key={contract.id} variant="outlined" sx={{p:2}}><Stack direction={{xs:'column',md:'row'}} justifyContent="space-between"><Box><Typography variant="h6">{contract.number} — {contract.name}</Typography><Typography color="text.secondary">{t('portalDashboard.contractPeriod', { from: new Date(contract.start_date).toLocaleDateString(i18n.language), to: new Date(contract.end_date).toLocaleDateString(i18n.language) })}</Typography>{contract.support_summary && <Typography mt={1}>{contract.support_summary}</Typography>}</Box><Chip color={contract.days_to_expiry <= 60 ? 'warning' : 'success'} label={t('portalDashboard.daysToExpiry', { count: contract.days_to_expiry })} /></Stack></Paper>)}
    <Grid container spacing={2}>{cards.map(([icon,value,label,view]) => <Grid key={label} size={{xs:12,sm:6,md:4}}><Card><CardActionArea onClick={()=>navigate(`/portal/tickets?view=${view}&date_from=${dateFrom}&date_to=${dateTo}`)}><CardContent>{icon}<Typography variant="h4">{value ?? '—'}</Typography><Typography color="text.secondary">{label}</Typography></CardContent></CardActionArea></Card></Grid>)}</Grid>
    {metrics && <Paper id="sla-performance" variant="outlined" sx={{p:2}}><Typography variant="h6">{t('portalDashboard.slaPerformance')}</Typography><Typography variant="h3" color={metrics.sla_breached ? 'error.main' : 'success.main'}>{metrics.sla_compliance_percent ?? '—'}{metrics.sla_compliance_percent != null && '%'}</Typography><Typography color="text.secondary">{t('portalDashboard.slaCounts', { met: metrics.sla_met, breached: metrics.sla_breached, evaluated: metrics.sla_evaluated, excluded: metrics.sla_evidence_excluded })}</Typography><Typography mt={1}>{t('portalDashboard.slaHours', { target: metrics.sla_target_business_hours, spent: metrics.spent_business_hours, saved: metrics.saved_business_hours })}</Typography><Typography mt={1}>{t('portalDashboard.slaWaiting', { customer: duration(metrics.customer_pending_minutes_excluded), millensys: duration(metrics.millensys_pending_minutes_included), escalation: duration(metrics.escalation_minutes) })}</Typography></Paper>}
    {data && <Paper variant="outlined" sx={{p:2}}><Typography variant="h6">{t('portalDashboard.calculationTitle')}</Typography><Typography color="text.secondary" mb={2}>{t('portalDashboard.calculationSubtitle')}</Typography>{data.support_calendars.map(calendar=><Box key={calendar.id} sx={{mb:2,p:1.5,bgcolor:'action.hover',borderRadius:2}}><Typography fontWeight={800}>{calendar.name} · {calendar.timezone}</Typography><Typography variant="body2">{calendar.days.filter(day=>day.is_working_day).map(day=>`${t(`portalDashboard.weekdays.${day.weekday}`)} ${day.start_time}–${day.end_time==='00:00'?'24:00':day.end_time}`).join(' · ')}</Typography><Typography variant="caption" color="text.secondary">{t('portalDashboard.calendarNotice')}</Typography></Box>)}<Grid container spacing={2}>{data.calculation_methods.map(method=><Grid key={method.name} size={{xs:12,md:6}}><Box sx={{p:1.5,height:'100%',border:1,borderColor:'divider',borderRadius:2}}><Typography fontWeight={800}>{method.name}</Typography><Typography color="primary.main" fontWeight={700} my={.5}>{method.formula}</Typography><Typography variant="body2" color="text.secondary">{method.details}</Typography></Box></Grid>)}</Grid></Paper>}
    {data && <Grid container spacing={2}><Grid size={{xs:12,md:6}}><Paper variant="outlined" sx={{p:2,height:'100%'}}><Typography variant="h6">{t('portalDashboard.productsModules')}</Typography><Typography fontWeight={700} mt={1}>{t('portalDashboard.products')}</Typography><Stack direction="row" gap={1} flexWrap="wrap">{data.coverage.products.map(item=><Chip key={item} label={item}/>)}{!data.coverage.products.length&&<Typography color="text.secondary">{t('portalDashboard.noProducts')}</Typography>}</Stack><Typography fontWeight={700} mt={2}>{t('portalDashboard.modules')}</Typography><Stack direction="row" gap={1} flexWrap="wrap">{data.coverage.modules.map(item=><Chip key={item} label={item} variant="outlined"/>)}{!data.coverage.modules.length&&<Typography color="text.secondary">{t('portalDashboard.noModules')}</Typography>}</Stack></Paper></Grid><Grid size={{xs:12,md:6}}><Paper variant="outlined" sx={{p:2,height:'100%'}}><Typography variant="h6">{t('portalDashboard.services')}</Typography><Stack direction="row" gap={1} flexWrap="wrap" mt={1}>{data.coverage.services.map(item=><Chip key={item} color="primary" label={item}/>)}{!data.coverage.services.length&&<Typography color="text.secondary">{t('portalDashboard.noServices')}</Typography>}</Stack><Typography variant="h6" mt={3}>{t('portalDashboard.slaAgreement')}</Typography>{data.sla_targets.map((item,index)=><Typography key={`${item.service}-${item.priority}-${index}`}>{t('portalDashboard.slaTarget', { service: item.service, priority: t(`priority.${item.priority}`, { defaultValue: item.priority }), response: duration(item.first_response_minutes), resolution: duration(item.resolution_minutes) })}</Typography>)}{!data.sla_targets.length&&<Typography color="text.secondary">{t('portalDashboard.noSla')}</Typography>}</Paper></Grid></Grid>}
    {data?.measurement_notes.map(note=><Alert key={note} severity="info">{note}</Alert>)}
  </Stack>
}

