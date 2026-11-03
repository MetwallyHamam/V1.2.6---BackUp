import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AccessRequired } from '../components/AccessRequired'
import { capabilityForPath } from '../auth/permissionRegistry'

export function UnauthorizedPage() {
  const { t } = useTranslation()
  const location = useLocation()
  const requested = new URLSearchParams(location.search).get('return') || '/'
  const capability = capabilityForPath(requested) ?? { permission: 'unknown', capability: t('accessRequired.protectedArea'), module: t('accessRequired.supportHub'), resource: requested }
  return <AccessRequired capability={capability} />
}
