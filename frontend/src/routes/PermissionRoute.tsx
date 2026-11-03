import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function PermissionRoute({ anyOf }: { anyOf: string[] }) {
  const { hasPermission } = useAuth()
  const location = useLocation()
  if (!anyOf.some(hasPermission)) return <Navigate to={`/unauthorized?return=${encodeURIComponent(`${location.pathname}${location.search}`)}`} replace state={{ from: location }} />
  return <Outlet />
}
