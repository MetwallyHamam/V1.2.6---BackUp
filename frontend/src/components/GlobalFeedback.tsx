import { Alert, Box, Snackbar } from '@mui/material'
import { ReactNode, useEffect, useRef, useState } from 'react'
import { capabilityForPermission, ProtectedCapability } from '../auth/permissionRegistry'
import { AccessRequired } from './AccessRequired'

type Notice = { id: number; message: string; severity: 'warning' | 'error' }

function fieldLabel(element: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement) {
  const formControl = element.closest('.MuiFormControl-root')
  const label = formControl?.querySelector('label')?.textContent?.replace(/\s*\*\s*$/, '').trim()
  return label || element.getAttribute('aria-label') || element.name.replaceAll('_', ' ') || 'required field'
}

export function GlobalFeedback({ children }: { children: ReactNode }) {
  const [notice, setNotice] = useState<Notice | null>(null)
  const [accessRequired,setAccessRequired]=useState<ProtectedCapability|null>(null)
  const lastNotice = useRef({ message: '', at: 0 })

  useEffect(() => {
    const show = (message: string, severity: Notice['severity']) => {
      const now = Date.now()
      if (lastNotice.current.message === message && now - lastNotice.current.at < 1500) return
      lastNotice.current = { message, at: now }
      setNotice({ id: now, message, severity })
    }
    const apiError = (event: Event) => {
      const detail = (event as CustomEvent<{ message?: string }>).detail
      show(detail?.message || 'The request could not be completed.', 'error')
    }
    const requestAccess=(event:Event)=>{const permission=(event as CustomEvent<{permission?:string}>).detail?.permission;if(permission)setAccessRequired(capabilityForPermission(permission))}
    const reconnecting=()=>show('Connection interrupted. Your session is preserved while Support Hub reconnects.','warning')
    const unavailable=()=>show('Support Hub is temporarily unreachable. Your session was not signed out; retry when the connection returns.','warning')
    const restored=()=>show('Connection restored. Your session is active.','warning')
    const expiryWarning=(event:Event)=>{const minutes=(event as CustomEvent<{minutes?:number}>).detail?.minutes??5;show(`Your session will expire in about ${minutes} minute${minutes===1?'':'s'}. Save your work.`, 'warning')}
    const invalid = (event: Event) => {
      const field = event.target
      if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement)) return
      show(`Complete the required field: ${fieldLabel(field)}.`, 'warning')
    }
    window.addEventListener('support-hub-api-error', apiError)
    window.addEventListener('support-hub-access-required',requestAccess)
    window.addEventListener('support-hub-session-reconnecting',reconnecting)
    window.addEventListener('support-hub-session-unavailable',unavailable)
    window.addEventListener('support-hub-session-restored',restored)
    window.addEventListener('support-hub-session-expiry-warning',expiryWarning)
    document.addEventListener('invalid', invalid, true)
    return () => {
      window.removeEventListener('support-hub-api-error', apiError)
      window.removeEventListener('support-hub-access-required',requestAccess)
      window.removeEventListener('support-hub-session-reconnecting',reconnecting)
      window.removeEventListener('support-hub-session-unavailable',unavailable)
      window.removeEventListener('support-hub-session-restored',restored)
      window.removeEventListener('support-hub-session-expiry-warning',expiryWarning)
      document.removeEventListener('invalid', invalid, true)
    }
  }, [])

  return <>
    {children}
    {accessRequired&&<Box sx={{position:'fixed',insetInlineEnd:16,bottom:16,zIndex:theme=>theme.zIndex.snackbar-1}}><AccessRequired capability={accessRequired} compact/></Box>}
    <Snackbar open={Boolean(notice)} autoHideDuration={7000} onClose={() => setNotice(null)} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
      <Alert severity={notice?.severity ?? 'error'} variant="filled" onClose={() => setNotice(null)} sx={{ width: '100%' }}>{notice?.message}</Alert>
    </Snackbar>
  </>
}
