import { Box, Button, Paper, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  const { t } = useTranslation()
  return <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2 }}><Paper sx={{ p: 4, width: '100%', maxWidth: 480, textAlign: 'center' }}>
    <Typography variant="h2" component="p" fontWeight={900} dir="ltr">404</Typography>
    <Typography variant="h4" component="h1" gutterBottom>{t('notFound.title')}</Typography>
    <Typography color="text.secondary" sx={{ mb: 3 }}>{t('notFound.message')}</Typography>
    <Button component={Link} to="/" variant="contained">{t('notFound.home')}</Button>
  </Paper></Box>
}
