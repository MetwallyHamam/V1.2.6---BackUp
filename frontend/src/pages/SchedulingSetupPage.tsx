import { Alert, Paper, Stack, Tab, Tabs } from '@mui/material'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { AssignmentRotationsPanel } from './AssignmentRotationsPanel'
import { EmployeeShiftEligibilityPanel } from './EmployeeShiftEligibilityPanel'
import { OperationTypesPanel } from './OperationTypesPanel'
import { ScheduleRecipesPanel } from './ScheduleRecipesPanel'
import { ShiftTypesPanel } from './ShiftTypesPanel'

type SetupSection='SHIFT_TYPES'|'OPERATION_TYPES'|'ELIGIBILITY'|'ROTATIONS'|'RECIPES'

export function SchedulingSetupPage(){
  const {t}=useTranslation()
  const {hasPermission}=useAuth()
  const canShift=hasPermission('shift.manage'),canOperationTypes=hasPermission('internal_operation.type.manage')||hasPermission('internal_operation.manage'),canOperationTemplates=hasPermission('internal_operation.template.manage')||hasPermission('internal_operation.manage')
  const first:SetupSection=canShift?'SHIFT_TYPES':'OPERATION_TYPES'
  const [section,setSection]=useState<SetupSection>(first)
  return <Stack spacing={2}><Paper><Tabs value={section} onChange={(_,value:SetupSection)=>setSection(value)} variant="scrollable" scrollButtons="auto" aria-label={t('schedulingSetup.sections')}>{canShift&&<Tab value="SHIFT_TYPES" label={t('schedulingSetup.shiftTypes')}/>}{canOperationTypes&&<Tab value="OPERATION_TYPES" label={t('schedulingSetup.operationTypes')}/>}{canShift&&<Tab value="ELIGIBILITY" label={t('schedulingSetup.eligibility')}/>}{canShift&&<Tab value="ROTATIONS" label={t('schedulingSetup.rotations')}/>}{canShift&&<Tab value="RECIPES" label={t('schedulingSetup.recipes')}/>}</Tabs></Paper>{section==='SHIFT_TYPES'&&canShift&&<ShiftTypesPanel/>}{section==='OPERATION_TYPES'&&canOperationTypes&&<OperationTypesPanel/>}{section==='ELIGIBILITY'&&canShift&&<EmployeeShiftEligibilityPanel/>}{section==='ROTATIONS'&&canShift&&<AssignmentRotationsPanel/>}{section==='RECIPES'&&canShift&&<ScheduleRecipesPanel/>}{!canShift&&!canOperationTypes&&!canOperationTemplates&&<Alert severity="warning">{t('schedulingSetup.noPermission')}</Alert>}</Stack>
}
