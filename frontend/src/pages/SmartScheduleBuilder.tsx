import { serverDateInput } from '../utils/serverTime'
import { AutoAwesome, ExpandMore, PlayArrow } from '@mui/icons-material'
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip, CircularProgress, MenuItem, Paper, Snackbar, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

type Recipe={id:number;code:string;name:string;timezone:string;effective_from:string|null;effective_to:string|null;rows:{id:number;weekday:number;start_time:string;end_time:string;required_headcount:number}[]}
type Candidate={employee_id:number;employee_name:string;assigned:boolean;available:boolean;eligible:boolean;shift_minutes:number;operation_minutes:number;visit_minutes:number;reason:string}
type Slot={slot_key:string;date:string;shift_type_name:string;starts_at:string;ends_at:string;required_headcount:number;assigned_user_names:string[];unassigned_positions:number;coverage_status:'FULL'|'UNDERSTAFFED'|'UNASSIGNED';candidates:Candidate[]}
type Preview={preview_hash:string;slot_count:number;required_positions:number;assignable_positions:number;unassigned_positions:number;conflict_count:number;coverage_percent:number;workload_balance_percent:number;slots:Slot[]}
type ApplyResult={batch_id:number;created_shifts:number;created_coverage_slots:number;unassigned_positions:number}
type Frequency='ONCE'|'DAILY'|'WEEKLY'|'EVERY_N_WEEKS'|'MONTHLY'|'QUARTERLY'|'SPECIFIC_DATES'|'CUSTOM'
type GeneratorRequest={recipe_id:number;recurrence:{frequency:Frequency;date_from:string;date_to:string;interval:number;weekdays:number[];specific_dates:string[]};timezone:string}

const today=()=>serverDateInput()
const inDays=(days:number)=>{const value=new Date();value.setDate(value.getDate()+days);return serverDateInput(value)}
const weekdays=[['Mon',0],['Tue',1],['Wed',2],['Thu',3],['Fri',4],['Sat',5],['Sun',6]] as const

export function SmartScheduleBuilder({onApplied}:{onApplied?:()=>void}){
  const {t,i18n}=useTranslation(),locale=i18n.resolvedLanguage==='ar'?'ar-EG':'en-US'
  const queryClient=useQueryClient()
  const [recipeId,setRecipeId]=useState(''),[frequency,setFrequency]=useState<Frequency>('WEEKLY'),[dateFrom,setDateFrom]=useState(today()),[dateTo,setDateTo]=useState(inDays(28)),[interval,setInterval]=useState(2),[selectedDays,setSelectedDays]=useState<number[]>([]),[specificDates,setSpecificDates]=useState(''),[notice,setNotice]=useState(''),[previewRequest,setPreviewRequest]=useState<GeneratorRequest|null>(null)
  const recipes=useQuery({queryKey:['schedule-recipes'],queryFn:async()=>(await api.get<Recipe[]>('/schedule-recipes')).data})
  const selected=recipes.data?.find(row=>row.id===Number(recipeId))
  const request=useMemo(()=>({recipe_id:Number(recipeId),recurrence:{frequency,date_from:dateFrom,date_to:dateTo,interval,weekdays:selectedDays,specific_dates:specificDates.split(',').map(value=>value.trim()).filter(Boolean)},timezone:selected?.timezone??'Africa/Cairo'}),[recipeId,frequency,dateFrom,dateTo,interval,selectedDays,specificDates,selected?.timezone])
  const preview=useMutation({mutationFn:async(payload:GeneratorRequest)=>(await api.post<Preview>('/shifts/generator/preview',payload)).data,onSuccess:(_,payload)=>setPreviewRequest(payload)})
  const apply=useMutation({mutationFn:async()=>(await api.post<ApplyResult>('/shifts/generator/apply',{request:previewRequest,preview_hash:preview.data?.preview_hash})).data,onSuccess:async result=>{await queryClient.invalidateQueries({queryKey:['shift-calendar']});await queryClient.invalidateQueries({queryKey:['shift-coverage-summary']});setNotice(t('smartSchedule.generated',{batch:result.batch_id,shifts:result.created_shifts,slots:result.created_coverage_slots}));preview.reset();setPreviewRequest(null);onApplied?.()}})
  function submit(event:FormEvent){event.preventDefault();preview.mutate(request)}
  const changed=Boolean(preview.data&&previewRequest&&JSON.stringify(previewRequest)!==JSON.stringify(request))
  return <Paper sx={{p:2}}>
    <Stack direction={{xs:'column',md:'row'}} gap={1.5} alignItems={{md:'center'}} mb={2}><AutoAwesome color="primary"/><Box flex={1}><Typography variant="h5" fontWeight={900}>{t('smartSchedule.title')}</Typography><Typography color="text.secondary">{t('smartSchedule.subtitle')}</Typography></Box></Stack>
    <Box component="form" onSubmit={submit}><Stack direction={{xs:'column',md:'row'}} gap={1.5}>
      <TextField select required label={t('smartSchedule.recipe')} value={recipeId} onChange={event=>{setRecipeId(event.target.value);preview.reset()}} fullWidth><MenuItem value="">{t('smartSchedule.selectRecipe')}</MenuItem>{recipes.data?.filter(row=>!row.effective_to||row.effective_to>=today()).map(row=><MenuItem key={row.id} value={row.id}>{row.name} · {t('smartSchedule.slotRules',{count:row.rows.length})}</MenuItem>)}</TextField>
      <TextField select label={t('smartSchedule.recurrence')} value={frequency} onChange={event=>{setFrequency(event.target.value as Frequency);preview.reset()}} fullWidth>{(['ONCE','DAILY','WEEKLY','EVERY_N_WEEKS','MONTHLY','QUARTERLY','SPECIFIC_DATES','CUSTOM'] as Frequency[]).map(value=><MenuItem key={value} value={value}>{t(`smartSchedule.frequency.${value}`)}</MenuItem>)}</TextField>
      <TextField required type="date" label={t('common.from')} value={dateFrom} onChange={event=>{setDateFrom(event.target.value);preview.reset()}} fullWidth slotProps={{inputLabel:{shrink:true}}}/>
      <TextField required type="date" label={t('common.to')} value={dateTo} onChange={event=>{setDateTo(event.target.value);preview.reset()}} fullWidth slotProps={{inputLabel:{shrink:true}}}/>
    </Stack>
    {frequency==='EVERY_N_WEEKS'&&<TextField type="number" label={t('smartSchedule.everyNWeeks')} value={interval} onChange={event=>{setInterval(Number(event.target.value));preview.reset()}} inputProps={{min:1,max:52}} sx={{mt:1.5}}/>}
    {frequency==='CUSTOM'&&<Stack direction="row" gap={1} mt={1.5} flexWrap="wrap">{weekdays.map(([label,value])=><Chip key={value} label={t(`smartSchedule.days.${label}`)} color={selectedDays.includes(value)?'primary':'default'} onClick={()=>{setSelectedDays(current=>current.includes(value)?current.filter(day=>day!==value):[...current,value]);preview.reset()}}/>)}</Stack>}
    {frequency==='SPECIFIC_DATES'&&<TextField label={t('smartSchedule.specificDates')} placeholder="2028-09-01, 2028-09-08" inputProps={{dir:'ltr'}} value={specificDates} onChange={event=>{setSpecificDates(event.target.value);preview.reset()}} fullWidth margin="normal"/>}
    {selected&&(selected.effective_from||selected.effective_to)&&<Alert severity="info" sx={{mt:1.5}}>{t('smartSchedule.validity',{from:selected.effective_from??t('smartSchedule.anyDate'),to:selected.effective_to??t('smartSchedule.noEnd')})}</Alert>}
    <Button type="submit" variant="contained" startIcon={preview.isPending?<CircularProgress size={17}/>:<PlayArrow/>} disabled={!recipeId||preview.isPending||dateTo<dateFrom} sx={{mt:2}}>{t('smartSchedule.preview')}</Button></Box>
    {preview.isError&&<Alert severity="error" sx={{mt:2}}>{t('smartSchedule.previewFailed')}</Alert>}
    {preview.data&&<Stack spacing={1.5} mt={2}>
      {changed&&<Alert severity="warning">{t('smartSchedule.changed')}</Alert>}
      <Box sx={{display:'grid',gridTemplateColumns:{xs:'repeat(2,1fr)',md:'repeat(5,1fr)'},gap:1}}>{[
        [t('smartSchedule.coverage'),`${preview.data.coverage_percent}%`],[t('smartSchedule.slots'),preview.data.slot_count],[t('smartSchedule.positions'),preview.data.required_positions],[t('smartSchedule.unassigned'),preview.data.unassigned_positions],[t('smartSchedule.balance'),`${preview.data.workload_balance_percent}%`],
      ].map(([label,value])=><Paper key={label} variant="outlined" sx={{p:1.5}}><Typography variant="overline">{label}</Typography><Typography variant="h5" fontWeight={900}>{typeof value==='number'?value.toLocaleString(locale):value}</Typography></Paper>)}</Box>
      {preview.data.unassigned_positions>0&&<Alert severity="warning">{t('smartSchedule.partial',{count:preview.data.unassigned_positions})}</Alert>}
      <Box sx={{maxHeight:500,overflow:'auto'}}>{preview.data.slots.map(slot=><Accordion key={slot.slot_key} disableGutters><AccordionSummary expandIcon={<ExpandMore/>}><Stack direction={{xs:'column',sm:'row'}} gap={1} alignItems={{sm:'center'}} width="100%"><Box flex={1}><Typography fontWeight={800}>{slot.shift_type_name} · {new Date(slot.starts_at).toLocaleString(locale)}</Typography><Typography variant="body2" color="text.secondary">{slot.assigned_user_names.join(', ')||t('smartSchedule.noAssignment')}</Typography></Box><Chip size="small" color={slot.coverage_status==='FULL'?'success':slot.coverage_status==='UNDERSTAFFED'?'warning':'error'} label={t('smartSchedule.coverageValue',{status:t(`smartSchedule.coverageStatus.${slot.coverage_status}`),assigned:slot.required_headcount-slot.unassigned_positions,required:slot.required_headcount})}/></Stack></AccordionSummary><AccordionDetails><Stack spacing={.75}>{slot.candidates.map(candidate=><Paper key={candidate.employee_id} variant="outlined" sx={{p:1,borderInlineStart:`4px solid ${candidate.assigned?'#2e7d32':candidate.available&&candidate.eligible?'#1976d2':'#bdbdbd'}`}}><Typography fontWeight={700}>{candidate.employee_name}{candidate.assigned?t('smartSchedule.assignedSuffix'):''}</Typography><Typography variant="caption" color="text.secondary">{candidate.reason} · {t('smartSchedule.workload',{shifts:Math.round(candidate.shift_minutes/60),operations:Math.round(candidate.operation_minutes/60),visits:Math.round(candidate.visit_minutes/60)})}</Typography></Paper>)}</Stack></AccordionDetails></Accordion>)}</Box>
      <Stack direction="row" justifyContent="flex-end"><Button variant="contained" color="success" disabled={Boolean(changed)||apply.isPending} onClick={()=>apply.mutate()}>{t(apply.isPending?'smartSchedule.applying':'smartSchedule.apply')}</Button></Stack>
      {apply.isError&&<Alert severity="error">{t('smartSchedule.stale')}</Alert>}
    </Stack>}
    <Snackbar open={Boolean(notice)} autoHideDuration={6000} onClose={()=>setNotice('')} message={notice}/>
  </Paper>
}

