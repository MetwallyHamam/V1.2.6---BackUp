import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Box, CircularProgress, Stack, Typography } from '@mui/material'
import { useAuth } from '../auth/AuthContext'
import { deliveryWorkspaceLanding, isAllowedDeliveryRoute, preferredWorkspace } from '../auth/projectWorkspaceAccess'

export function ProtectedRoute() {
  const { user, hasPermission, initializing, reconnecting } = useAuth()
  const location = useLocation()
  if (initializing) return <Box sx={{minHeight:'70vh',display:'grid',placeItems:'center'}}><Stack alignItems="center" gap={2}><CircularProgress aria-label="Restoring session"/><Typography>{reconnecting?'Connection interrupted. Retrying without signing you out…':'Restoring your session…'}</Typography></Stack></Box>
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (user.require_password_change && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />
  }
  if (!user.require_password_change && location.pathname === '/change-password') {
    return <Navigate to={user.user_type === 'CLIENT_PORTAL' ? '/portal' : '/'} replace />
  }
  const landing = deliveryWorkspaceLanding(user.user_type, hasPermission)
  if (user.user_type === 'EMPLOYEE' && ['/', '/home'].includes(location.pathname)) {
    const preferred = preferredWorkspace(user.id, hasPermission)
    if (preferred) return <Navigate to={preferred.path} replace />
  }
  if (landing && !isAllowedDeliveryRoute(location.pathname, hasPermission)) {
    return <Navigate to={landing} replace />
  }
  return <Outlet />
}
