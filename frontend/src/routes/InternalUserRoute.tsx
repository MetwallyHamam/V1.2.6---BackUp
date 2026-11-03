import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function InternalUserRoute() {
  const { user } = useAuth()
  if (user?.user_type === 'CLIENT_PORTAL') return <Navigate to="/portal" replace />
  return <Outlet />
}
