import { Alert, Box, Button, Link, Paper, TextField, Typography } from '@mui/material'
import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link as RouterLink } from 'react-router-dom'
import { api } from '../api/client'

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [localToken, setLocalToken] = useState('')
  const [pending, setPending] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError('')
    try {
      const values = Object.fromEntries(new FormData(event.currentTarget))
      const response = await api.post<{ message: string; reset_token?: string }>('/auth/forgot-password', { login: String(values.login).trim() })
      setMessage(t('auth.forgot.success'))
      setLocalToken(response.data.reset_token ?? '')
    } catch {
      setMessage('')
      setLocalToken('')
      setError(t('auth.forgot.failed'))
    } finally { setPending(false) }
  }
  return <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: 'background.default', p: 2 }}><Paper component="form" onSubmit={submit} sx={{ p: 4, width: '100%', maxWidth: 420 }}>
    <Typography variant="h4" gutterBottom>{t('auth.forgot.title')}</Typography>
    <Typography color="text.secondary" sx={{ mb: 2 }}>{t('auth.forgot.instructions')}</Typography>
    {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {localToken && <Alert severity="info" sx={{ mb: 2 }}>{t('auth.forgot.localDelivery')} <Link component={RouterLink} to={`/reset-password?token=${encodeURIComponent(localToken)}`}>{t('auth.forgot.continueReset')}</Link>.</Alert>}
    <TextField name="login" label={t('auth.username')} autoComplete="username" required fullWidth margin="normal" inputProps={{ dir: 'ltr' }} />
    <Button type="submit" variant="contained" fullWidth disabled={pending} sx={{ mt: 2 }}>{pending ? t('auth.forgot.preparing') : t('auth.forgot.send')}</Button>
    <Button component={RouterLink} to="/login" fullWidth sx={{ mt: 1 }}>{t('auth.forgot.back')}</Button>
  </Paper></Box>
}
