import { serverDateInput } from '../utils/serverTime'
import { ExpandMore } from '@mui/icons-material'
import { Accordion,AccordionDetails,AccordionSummary,Alert,Box,Button,Chip,Dialog,DialogActions,DialogContent,DialogTitle,MenuItem,Paper,Stack,TextField,Typography,useMediaQuery,useTheme } from '@mui/material'
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { FormEvent,useEffect,useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { MobileMultiAutocomplete } from '../components/MobileMultiAutocomplete'
import { TechnicalText } from '../components/TechnicalText'
import { getLocalizedName } from '../i18n/localizedMasterData'

type Assignment='MANUAL'|'SUGGESTED'|'AUTO_BALANCE'
type ShiftType={id:number;name:string;name_ar?:string;color:string;default_start_time:string;default_end_time:string;default_required_headcount:number;crosses_midnight:boolean}
type Candidate={employee_id:number;employee_name:string;available:boolean;shift_count:number;shift_minutes:number;reason:string}
type Context={required_headcount:number;candidates:Candidate[]}
const today=()=>serverDateInput()

export function QuickShiftDialog({open,initialDate,initialShiftTypeId,initialTeam,onClose}:{open:boolean;initialDate?:string;initialShiftTypeId?:number;initialTeam?:string|null;onClose:()=>void}){
  const {t,i18n}=useTranslation()
  const language=i18n.resolvedLanguage?.startsWith('ar')?'ar':'en'
  const locale=i18n.resolvedLanguage?.startsWith('ar')?'ar-EG':'en-US'
  const number=(value:number,options?:Intl.NumberFormatOptions)=>new Intl.NumberFormat(locale,options).format(value)
  const theme=useTheme(),fullScreen=useMediaQuery(theme.breakpoints.down('sm')),queryClient=useQueryClient(),initial=initialDate??today()
  const [dateFrom,setDateFrom]=useState(initial),[dateTo,setDateTo]=useState(initial),[shiftTypeId,setShiftTypeId]=useState(''),[assignment,setAssignment]=useState<Assignment>('MANUAL'),[selected,setSelected]=useState<Candidate[]>([]),[error,setError]=useState('')
  const types=useQuery({queryKey:['shift-types',language],queryFn:async()=>(await api.get<ShiftType[]>('/shift-types')).data.map(type=>({...type,name:getLocalizedName(type,language)})),enabled:open})
  const validRange=Boolean(dateFrom&&dateTo&&dateTo>=dateFrom)
  const context=useQuery({queryKey:['quick-shift-context',dateFrom,dateTo,shiftTypeId],queryFn:async()=>(await api.get<Context>('/shifts/quick-context',{params:{date:dateFrom,date_to:dateTo,shift_type_id:Number(shiftTypeId),timezone:'Africa/Cairo'}})).data,enabled:open&&validRange&&Boolean(shiftTypeId)})
  const save=useMutation({mutationFn:async(payload:Record<string,unknown>)=>api.post('/shifts/quick',payload),onSuccess:async()=>{await Promise.all([queryClient.invalidateQueries({queryKey:['shift-calendar']}),queryClient.invalidateQueries({queryKey:['shift-coverage-slots']}),queryClient.invalidateQueries({queryKey:['scheduling-workload']})]);onClose()},onError:requestError=>setError(axios.isAxiosError(requestError)&&!locale.startsWith('ar')?requestError.response?.data?.error?.message??t('quickShiftDialog.createError'):t('quickShiftDialog.createError'))})
  useEffect(()=>{if(open){const value=initialDate??today();setDateFrom(value);setDateTo(value);setShiftTypeId(initialShiftTypeId?String(initialShiftTypeId):'')}},[open,initialDate,initialShiftTypeId])
  useEffect(()=>{setSelected([]);setError('')},[dateFrom,dateTo,shiftTypeId,assignment])
  useEffect(()=>{if(assignment==='SUGGESTED'&&context.data)setSelected(context.data.candidates.filter(row=>row.available).slice(0,context.data.required_headcount))},[assignment,context.data])
  const available=context.data?.candidates.filter(row=>row.available)??[],autoSelection=available.slice(0,context.data?.required_headcount??0)
  const coverageCount=assignment==='AUTO_BALANCE'?autoSelection.length:selected.length
  const selectedType=types.data?.find(row=>row.id===Number(shiftTypeId))
  const timeLabel=selectedType?selectedType.default_start_time.slice(0,5)+' → '+selectedType.default_end_time.slice(0,5)+(selectedType.crosses_midnight?t('quickShiftDialog.nextDay'):''):t('quickShiftDialog.selectType')
  const dayCount=validRange?Math.round((new Date(dateTo+'T00:00:00Z').getTime()-new Date(dateFrom+'T00:00:00Z').getTime())/86400000)+1:0
  function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();const values=Object.fromEntries(new FormData(event.currentTarget));save.mutate({date_from:dateFrom,date_to:dateTo,shift_type_id:Number(shiftTypeId),assignment_mode:assignment,user_ids:assignment==='AUTO_BALANCE'?[]:selected.map(row=>row.employee_id),timezone:'Africa/Cairo',notes:values.notes||null,work_location:values.work_location||'OFFICE',team:values.team||null,on_call_role:values.on_call_role||null,overlap_override_reason:values.overlap_override_reason||null,override_start_time:values.override_start_time||null,override_end_time:values.override_end_time||null})}
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" fullScreen={fullScreen}><Box component="form" onSubmit={submit}>
    <DialogTitle>{t('quickShiftDialog.title')}</DialogTitle><DialogContent dividers><Stack spacing={1.5}>
      {error&&<Alert severity="error">{error}</Alert>}
      <Stack direction={{xs:'column',sm:'row'}} gap={1}><TextField required fullWidth type="date" label={t('quickShiftDialog.dateFrom')} value={dateFrom} onChange={event=>{setDateFrom(event.target.value);if(dateTo<event.target.value)setDateTo(event.target.value)}} slotProps={{inputLabel:{shrink:true}}}/><TextField required fullWidth type="date" label={t('quickShiftDialog.dateTo')} value={dateTo} onChange={event=>setDateTo(event.target.value)} slotProps={{inputLabel:{shrink:true},htmlInput:{min:dateFrom}}}/></Stack>
      {dayCount>0&&<Typography variant="body2" color="text.secondary">{t('quickShiftDialog.daysSelected',{count:dayCount})}</Typography>}
      <TextField required select label={t('quickShiftDialog.shiftType')} value={shiftTypeId} onChange={event=>setShiftTypeId(event.target.value)}>{(types.data??[]).map(row=><MenuItem key={row.id} value={row.id}>{row.name}</MenuItem>)}</TextField>
      <Paper variant="outlined" sx={{p:1.5,borderInlineStart:'5px solid '+(selectedType?.color??'#bdbdbd')}}><Typography fontWeight={900}><TechnicalText>{timeLabel}</TechnicalText></Typography><Typography variant="body2" color="text.secondary">{t('quickShiftDialog.inherited')}</Typography></Paper>
      <TextField select label={t('quickShiftDialog.assignment')} value={assignment} onChange={event=>setAssignment(event.target.value as Assignment)}><MenuItem value="MANUAL">{t('quickShiftDialog.manual')}</MenuItem><MenuItem value="SUGGESTED">{t('quickShiftDialog.suggested')}</MenuItem><MenuItem value="AUTO_BALANCE">{t('quickShiftDialog.autoBalance')}</MenuItem></TextField>
      {context.isLoading&&<Typography color="text.secondary">{t('quickShiftDialog.checking')}</Typography>}{context.isError&&<Alert severity="error">{t('quickShiftDialog.availabilityError')}</Alert>}
      {context.data&&assignment!=='AUTO_BALANCE'&&<MobileMultiAutocomplete options={context.data.candidates} value={selected} onChange={(_,value)=>setSelected(value)} getOptionLabel={option=>option.employee_name} isOptionEqualToValue={(a,b)=>a.employee_id===b.employee_id} getOptionDisabled={option=>!option.available} groupBy={option=>option.available?t('quickShiftDialog.availableRange'):t('quickShiftDialog.unavailable')} renderTags={(value,getTagProps)=>value.map((option,index)=><Chip label={option.employee_name} {...getTagProps({index})} key={option.employee_id}/>)} renderOption={(props,option)=><li {...props} key={option.employee_id}><Box><Typography fontWeight={800}>{option.employee_name}</Typography><Typography variant="caption" color={option.available?'text.secondary':'error'}>{t('quickShiftDialog.workload',{shifts:number(option.shift_count),hours:number(option.shift_minutes/60,{maximumFractionDigits:1}),reason:option.reason})}</Typography></Box></li>} renderInput={params=><TextField {...params} label={t('quickShiftDialog.engineers')} placeholder={t('quickShiftDialog.searchEngineer')} helperText={t('quickShiftDialog.availableHelp')}/>}/>} 
      {context.data&&assignment==='AUTO_BALANCE'&&<Paper variant="outlined" sx={{p:1.5}}><Typography fontWeight={900}>{t('quickShiftDialog.autoPreview')}</Typography><Typography variant="body2" color="text.secondary">{t('quickShiftDialog.autoHelp')}</Typography><Stack direction="row" gap={.5} flexWrap="wrap" mt={1}>{autoSelection.map(row=><Chip key={row.employee_id} label={row.employee_name} color="primary"/>)}{!autoSelection.length&&<Chip label={t('quickShiftDialog.noneAvailable')} color="error"/>}</Stack></Paper>}
      {context.data&&<Alert severity={coverageCount>=context.data.required_headcount?'success':'warning'}>{t('quickShiftDialog.coverage',{coverage:number(coverageCount),required:number(context.data.required_headcount),days:number(dayCount),complete:coverageCount>=context.data.required_headcount?'✓':''})}</Alert>}
      <TextField name="notes" label={t('quickShiftDialog.notes')} multiline rows={2}/>
      <Accordion disableGutters><AccordionSummary expandIcon={<ExpandMore/>}><Typography fontWeight={800}>{t('quickShiftDialog.advanced')}</Typography></AccordionSummary><AccordionDetails><Stack spacing={1.5}><Stack direction={{xs:'column',sm:'row'}} gap={1}><TextField name="override_start_time" type="time" label={t('quickShiftDialog.overrideStart')} fullWidth slotProps={{inputLabel:{shrink:true},htmlInput:{dir:'ltr'}}}/><TextField name="override_end_time" type="time" label={t('quickShiftDialog.overrideEnd')} fullWidth slotProps={{inputLabel:{shrink:true},htmlInput:{dir:'ltr'}}}/></Stack><TextField select name="work_location" label={t('quickShiftDialog.location')} defaultValue="OFFICE"><MenuItem value="OFFICE">{t('quickShiftDialog.office')}</MenuItem><MenuItem value="WORK_FROM_HOME">{t('quickShiftDialog.workFromHome')}</MenuItem><MenuItem value="HYBRID">{t('quickShiftDialog.hybrid')}</MenuItem></TextField><TextField name="team" label={t('quickShiftDialog.team')} defaultValue={initialTeam??''}/><TextField select name="on_call_role" label={t('quickShiftDialog.onCallRole')} defaultValue=""><MenuItem value="">{t('quickShiftDialog.none')}</MenuItem><MenuItem value="PRIMARY">{t('quickShiftDialog.primary')}</MenuItem><MenuItem value="BACKUP">{t('quickShiftDialog.backup')}</MenuItem></TextField><TextField name="overlap_override_reason" label={t('quickShiftDialog.overlapReason')}/></Stack></AccordionDetails></Accordion>
    </Stack></DialogContent><DialogActions><Button onClick={onClose}>{t('quickShiftDialog.cancel')}</Button><Button type="submit" variant="contained" disabled={!shiftTypeId||!context.data||coverageCount===0||dayCount<1||dayCount>31||save.isPending}>{t('quickShiftDialog.create',{count:dayCount})}</Button></DialogActions>
  </Box></Dialog>
}

