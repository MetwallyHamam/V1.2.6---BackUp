import { Alert, Box, Button, Checkbox, Chip, FormControlLabel, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { getLocalizedName } from '../i18n/localizedMasterData'

type Eligibility = { employee_id:number;employee_name:string;department?:string;shift_type_id:number;shift_type_name:string;is_eligible:boolean }
type ShiftType = { id:number;name:string;name_ar?:string;enforce_employee_eligibility:boolean }

export function EmployeeShiftEligibilityPanel() {
  const {t,i18n}=useTranslation(),language=i18n.resolvedLanguage==='ar'?'ar':'en'
  const queryClient=useQueryClient()
  const rows=useQuery({queryKey:['shift-eligibilities'],queryFn:async()=>(await api.get<Eligibility[]>('/shift-eligibilities')).data})
  const types=useQuery({queryKey:['shift-types',language],queryFn:async()=>(await api.get<ShiftType[]>('/shift-types')).data.map(type=>({...type,name:getLocalizedName(type,language)}))})
  const [values,setValues]=useState<Record<string,boolean>>({}),[search,setSearch]=useState(''),[department,setDepartment]=useState('')
  useEffect(()=>{if(rows.data)setValues(Object.fromEntries(rows.data.map(row=>[`${row.employee_id}:${row.shift_type_id}`,row.is_eligible])))},[rows.data])
  const employees=useMemo(()=>Array.from(new Map((rows.data??[]).map(row=>[row.employee_id,{id:row.employee_id,name:row.employee_name,department:row.department??''}])).values()).filter(row=>(!department||row.department===department)&&row.name.toLowerCase().includes(search.toLowerCase())),[rows.data,department,search])
  const departments=useMemo(()=>[...new Set((rows.data??[]).map(row=>row.department).filter(Boolean) as string[])].sort(),[rows.data])
  const activeTypes=types.data??[]
  const key=(employeeId:number,typeId:number)=>`${employeeId}:${typeId}`
  const setEmployee=(employeeId:number,value:boolean)=>setValues(current=>({...current,...Object.fromEntries(activeTypes.map(type=>[key(employeeId,type.id),value]))}))
  const setType=(typeId:number,value:boolean)=>setValues(current=>({...current,...Object.fromEntries(employees.map(employee=>[key(employee.id,typeId),value]))}))
  const save=useMutation({mutationFn:async()=>api.put('/shift-eligibilities',{rows:(rows.data??[]).map(row=>({employee_id:row.employee_id,shift_type_id:row.shift_type_id,is_eligible:Boolean(values[key(row.employee_id,row.shift_type_id)])}))}),onSuccess:async()=>queryClient.invalidateQueries({queryKey:['shift-eligibilities']})})
  return <Paper variant="outlined" sx={{p:2}}><Stack spacing={2}>
    <Box><Typography variant="h6" fontWeight={900}>{t('shiftEligibility.title')}</Typography><Typography color="text.secondary">{t('shiftEligibility.subtitle')}</Typography></Box>
    <Alert severity="info">{t('shiftEligibility.hint')}</Alert>
    <Stack direction={{xs:'column',sm:'row'}} gap={1}><TextField size="small" label={t('shiftEligibility.engineer')} value={search} onChange={event=>setSearch(event.target.value)} fullWidth/><TextField select size="small" label={t('shiftEligibility.department')} value={department} onChange={event=>setDepartment(event.target.value)} fullWidth><MenuItem value="">{t('shiftEligibility.allDepartments')}</MenuItem>{departments.map(value=><MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField><Button variant="contained" disabled={save.isPending||!rows.data?.length} onClick={()=>save.mutate()}>{save.isPending?t('shiftEligibility.saving'):t('shiftEligibility.save')}</Button></Stack>
    {rows.isError&&<Alert severity="error">{t('shiftEligibility.loadFailed')}</Alert>}{save.isError&&<Alert severity="error">{t('shiftEligibility.saveFailed')}</Alert>}{save.isSuccess&&<Alert severity="success">{t('shiftEligibility.saved')}</Alert>}
    <TableContainer sx={{display:{xs:'none',md:'block'}}}><Table size="small"><TableHead><TableRow><TableCell>{t('shiftEligibility.engineer')}</TableCell>{activeTypes.map(type=><TableCell key={type.id} align="center"><Typography fontWeight={800}>{type.name}</Typography><Stack direction="row" justifyContent="center"><Button size="small" onClick={()=>setType(type.id,true)}>{t('shiftEligibility.all')}</Button><Button size="small" onClick={()=>setType(type.id,false)}>{t('shiftEligibility.clear')}</Button></Stack>{type.enforce_employee_eligibility&&<Chip size="small" color="warning" label={t('shiftEligibility.enforced')}/>}</TableCell>)}</TableRow></TableHead><TableBody>{employees.map(employee=><TableRow key={employee.id}><TableCell><Typography fontWeight={800}>{employee.name}</Typography><Typography variant="caption" color="text.secondary">{employee.department||t('shiftEligibility.noDepartment')}</Typography><Stack direction="row"><Button size="small" onClick={()=>setEmployee(employee.id,true)}>{t('shiftEligibility.selectRow')}</Button><Button size="small" onClick={()=>setEmployee(employee.id,false)}>{t('shiftEligibility.clearRow')}</Button></Stack></TableCell>{activeTypes.map(type=><TableCell key={type.id} align="center"><Checkbox checked={Boolean(values[key(employee.id,type.id)])} onChange={(_,checked)=>setValues(current=>({...current,[key(employee.id,type.id)]:checked}))} inputProps={{'aria-label':t('shiftEligibility.eligibleFor',{employee:employee.name,type:type.name})}}/></TableCell>)}</TableRow>)}</TableBody></Table></TableContainer>
    <Stack sx={{display:{xs:'flex',md:'none'}}} spacing={1}>{employees.map(employee=><Paper key={employee.id} variant="outlined" sx={{p:1.5}}><Typography fontWeight={900}>{employee.name}</Typography><Typography variant="caption" color="text.secondary">{employee.department||t('shiftEligibility.noDepartment')}</Typography><Stack mt={1}>{activeTypes.map(type=><FormControlLabel key={type.id} control={<Checkbox checked={Boolean(values[key(employee.id,type.id)])} onChange={(_,checked)=>setValues(current=>({...current,[key(employee.id,type.id)]:checked}))}/>} label={<>{type.name}{type.enforce_employee_eligibility&&<Chip size="small" color="warning" label={t('shiftEligibility.enforced')} sx={{ml:1}}/>}</>}/>)}</Stack><Stack direction="row"><Button size="small" onClick={()=>setEmployee(employee.id,true)}>{t('shiftEligibility.selectAll')}</Button><Button size="small" onClick={()=>setEmployee(employee.id,false)}>{t('shiftEligibility.clearAll')}</Button></Stack></Paper>)}</Stack>
  </Stack></Paper>
}
