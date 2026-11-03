import { zodResolver } from '@hookform/resolvers/zod'
import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../auth/AuthContext'

type Form = { currentPassword: string; newPassword: string; confirmPassword: string }

export function ChangePasswordPage() {
  const { t } = useTranslation()
  const { user, changePassword } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const schema = z.object({
    currentPassword: z.string().min(8, t('auth.change.currentRequired')),
    newPassword: z.string().min(12, t('auth.change.minimum')),
    confirmPassword: z.string(),
  }).refine((values) => values.newPassword === values.confirmPassword, {
    message: t('auth.change.mismatch'), path: ['confirmPassword'],
  }).refine((values) => values.currentPassword !== values.newPassword, {
    message: t('auth.change.mustDiffer'), path: ['newPassword'],
  })
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) })

  const submit = async (values: Form) => {
    setError('')
    try {
      await changePassword(values.currentPassword, values.newPassword)
      navigate(user?.user_type === 'CLIENT_PORTAL' ? '/portal' : '/', { replace: true })
    }
    catch { setError(t('auth.change.failed')) }
  }

  return <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: 'background.default' }}>
    <Paper component="form" onSubmit={handleSubmit(submit)} sx={{ p: 4, width: 420, maxWidth: 'calc(100vw - 32px)' }}>
      <Typography variant="h4" gutterBottom>{t('auth.change.title')}</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>{t('auth.change.instructions')}</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <TextField fullWidth label={t('auth.change.currentPassword')} type="password" autoComplete="current-password" margin="normal" inputProps={{ dir: 'ltr' }} {...register('currentPassword')} error={!!errors.currentPassword} helperText={errors.currentPassword?.message} />
      <TextField fullWidth label={t('auth.change.newPassword')} type="password" autoComplete="new-password" margin="normal" inputProps={{ dir: 'ltr' }} {...register('newPassword')} error={!!errors.newPassword} helperText={errors.newPassword?.message} />
      <TextField fullWidth label={t('auth.change.confirmPassword')} type="password" autoComplete="new-password" margin="normal" inputProps={{ dir: 'ltr' }} {...register('confirmPassword')} error={!!errors.confirmPassword} helperText={errors.confirmPassword?.message} />
      <Button fullWidth variant="contained" type="submit" disabled={isSubmitting} sx={{ mt: 2 }}>{isSubmitting ? t('auth.change.changing') : t('auth.change.action')}</Button>
    </Paper>
  </Box>
}
