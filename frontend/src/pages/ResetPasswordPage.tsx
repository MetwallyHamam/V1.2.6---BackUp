import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material'
import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

export function ResetPasswordPage() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [pending, setPending] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget))
    if (values.new_password !== values.confirm_password) { setError(t('auth.reset.mismatch')); return }
    setPending(true); setError('')
    try {
      await api.post('/auth/reset-password', { token, new_password: values.new_password })
      setSuccess(true)
    } catch {
      setError(t('auth.reset.failed'))
    } finally { setPending(false) }
  }
  return <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: 'background.default', p: 2 }}><Paper component="form" onSubmit={submit} sx={{ p: 4, width: '100%', maxWidth: 420 }}>
    <Typography variant="h4" gutterBottom>{t('auth.reset.title')}</Typography>
    {!token && <Alert severity="error" sx={{ mb: 2 }}>{t('auth.reset.incomplete')}</Alert>}
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {success ? <><Alert severity="success" sx={{ mb: 2 }}>{t('auth.reset.success')}</Alert><Button component={Link} to="/login" variant="contained" fullWidth>{t('auth.signIn')}</Button></> : <>
      <TextField name="new_password" label={t('auth.reset.newPassword')} type="password" autoComplete="new-password" required inputProps={{ minLength: 12, dir: 'ltr' }} helperText={t('auth.reset.minimum')} fullWidth margin="normal" />
      <TextField name="confirm_password" label={t('auth.reset.confirmPassword')} type="password" autoComplete="new-password" required inputProps={{ minLength: 12, dir: 'ltr' }} fullWidth margin="normal" />
      <Button type="submit" variant="contained" fullWidth disabled={pending || !token} sx={{ mt: 2 }}>{pending ? t('auth.reset.resetting') : t('auth.reset.action')}</Button>
    </>}
  </Paper></Box>
}
