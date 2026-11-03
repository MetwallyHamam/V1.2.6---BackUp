import { Alert, Box, Breadcrumbs, Link, Paper, Tab, Tabs, Typography } from '@mui/material'
import { Link as RouterLink, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { ContractsPage } from './ContractsPage'
import { ContractTemplatesPage } from './ContractTemplatesPage'
import { SlaTemplatesPage } from './SlaTemplatesPage'
import { ContractTypesPanel } from './ContractTypesPanel'
import { ContractLifecycleBoard } from './ContractLifecycleBoard'
import { VisitTypesPanel } from './VisitTypesPanel'
import { ContractNotificationSettings } from './ContractNotificationSettings'

export type ContractWorkspaceSection = 'lifecycle' | 'contracts' | 'types' | 'templates' | 'sla-templates' | 'visit-types' | 'notifications'

export function resolveContractWorkspaceSection(requested: string | null, canViewContracts: boolean, canViewTemplates: boolean, canManageNotifications = false): ContractWorkspaceSection {
  if (requested === 'notifications' && canManageNotifications) return 'notifications'
  if (requested === 'lifecycle' && canViewContracts) return 'lifecycle'
  if (requested === 'visit-types' && canViewContracts) return 'visit-types'
  if (requested === 'templates' && canViewTemplates) return 'templates'
  if (requested === 'types' && canViewContracts) return 'types'
  if (requested === 'sla-templates' && canViewContracts) return 'sla-templates'
  if (requested === 'contracts' && canViewContracts) return 'contracts'
  return canViewContracts ? 'lifecycle' : 'templates'
}

export function ContractWorkspacePage() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const canViewContracts = hasPermission('contract.view')
  const canViewTemplates = hasPermission('contract.template.view')
  const canManageNotifications = hasPermission('contract.notification_rules.manage')
  const requestedSection = searchParams.get('section') ?? (searchParams.has('contract_id') ? 'contracts' : null)
  const section = resolveContractWorkspaceSection(requestedSection, canViewContracts, canViewTemplates, canManageNotifications)

  const selectSection = (nextSection: ContractWorkspaceSection) => {
    setSearchParams(current => {
      const next = new URLSearchParams(current)
      if (nextSection !== 'lifecycle') next.set('section', nextSection)
      else next.delete('section')
      next.delete('contract_id')
      next.delete('tab')
      return next
    })
  }

  return <Box>
    <Breadcrumbs sx={{ mb: 1 }} aria-label={t('contractWorkspace.breadcrumb')}>
      <Link component={RouterLink} to="/clients" underline="hover" color="inherit">{t('contractWorkspace.customerManagement')}</Link>
      <Typography color="text.primary">{t('contractWorkspace.title')}</Typography>
    </Breadcrumbs>
    <Box mb={2}>
      <Typography variant="h4" fontWeight={800}>{t('contractWorkspace.title')}</Typography>
      <Typography color="text.secondary">{t('contractWorkspace.subtitle')}</Typography>
    </Box>
    <Paper variant="outlined" sx={{ mb: 2 }}>
      <Tabs value={section} onChange={(_, value: ContractWorkspaceSection) => selectSection(value)} variant="scrollable" scrollButtons="auto" aria-label={t('contractWorkspace.navigation')}>
        {canViewContracts && <Tab value="lifecycle" label="Lifecycle board" />}
        {canViewContracts && <Tab value="contracts" label={t('contractWorkspace.contractsSla')} />}
        {canViewContracts && <Tab value="types" label={t('contractTypes.title')} />}
        {canViewTemplates && <Tab value="templates" label={t('contractWorkspace.templates')} />}
        {canViewContracts && <Tab value="sla-templates" label="SLA templates" />}
        {canViewContracts && <Tab value="visit-types" label="Visit types" />}
        {canManageNotifications && <Tab value="notifications" label="Notifications" />}
      </Tabs>
    </Paper>
    {!canViewContracts && !canViewTemplates && <Alert severity="warning">{t('contractWorkspace.accessDenied')}</Alert>}
    {section === 'lifecycle' && canViewContracts && <ContractLifecycleBoard />}
    {section === 'contracts' && canViewContracts && <ContractsPage embedded />}
    {section === 'types' && canViewContracts && <Paper variant="outlined" sx={{ p:2 }}><ContractTypesPanel canManage={hasPermission('contract.manage')} /></Paper>}
    {section === 'templates' && canViewTemplates && <ContractTemplatesPage embedded />}
    {section === 'sla-templates' && canViewContracts && <SlaTemplatesPage />}
    {section === 'visit-types' && canViewContracts && <Paper variant="outlined" sx={{ p:2 }}><VisitTypesPanel canManage={hasPermission('visit.entitlement.manage')} /></Paper>}
    {section === 'notifications' && canManageNotifications && <ContractNotificationSettings />}
  </Box>
}
