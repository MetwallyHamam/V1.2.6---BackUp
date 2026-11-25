import { Navigate, Outlet, useLocation, useOutletContext } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function PermissionRoute({ anyOf }: { anyOf: string[] }) {
  const { hasPermission } = useAuth()
  const location = useLocation()
  const context = useOutletContext()
  if (!anyOf.some(hasPermission)) return <Navigate to={`/unauthorized?return=${encodeURIComponent(`${location.pathname}${location.search}`)}`} replace state={{ from: location }} />
  return <Outlet context={context} />
}
