import { AccountBalance, Description, Payments, TrendingUp } from '@mui/icons-material'
import { Alert, Box, Paper, Stack, Tab, Tabs, Typography } from '@mui/material'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { FinancialAnalyticsDashboard } from '../components/FinancialAnalyticsDashboard'
import { ManagerFinancePage } from './ManagerFinancePage'
import { PaymentsPage } from './PaymentsPage'

export function FinancialPage(){
 const {t}=useTranslation()
 const {hasPermission}=useAuth(),canDashboard=hasPermission('finance.dashboard.view'),canFinance=hasPermission('finance.view')
 const [tab,setTab]=useState(canDashboard?'dashboard':'invoices')
 if(!canDashboard&&!canFinance)return <Alert severity="error">{t('financialPage.accessDenied')}</Alert>
 return <Stack spacing={2}><Paper><Stack direction="row" alignItems="center" p={2}><AccountBalance color="primary"/><Box sx={{marginInlineStart:1}}><Typography variant="h4" fontWeight={900}>{t('financialPage.title')}</Typography><Typography color="text.secondary">{t('financialPage.subtitle')}</Typography></Box></Stack><Tabs value={tab} onChange={(_,value)=>setTab(value)} variant="scrollable" scrollButtons="auto">{canDashboard&&<Tab icon={<TrendingUp/>} iconPosition="start" value="dashboard" label={t('financialPage.analysis')}/>} {canFinance&&<Tab icon={<Payments/>} iconPosition="start" value="invoices" label={t('financialPage.invoicesPayments')}/>} {canFinance&&<Tab icon={<Description/>} iconPosition="start" value="ticket-finance" label={t('financialPage.ticketFinance')}/>}</Tabs></Paper>{tab==='dashboard'&&canDashboard&&<FinancialAnalyticsDashboard/>}{tab==='invoices'&&canFinance&&<PaymentsPage/>}{tab==='ticket-finance'&&canFinance&&<ManagerFinancePage/>}</Stack>
}
