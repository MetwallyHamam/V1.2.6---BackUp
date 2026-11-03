import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

type ContractSummary = {
  id: number
  contract_number: string
  ticket_catalog_visibility: 'CONTRACT_ONLY' | 'ALL_WITH_COVERAGE_STATUS'
}

export function ContractCatalogVisibilityCard({ contract, canManage, onSaved }: {
  contract: ContractSummary | null
  canManage: boolean
  onSaved: (mode: ContractSummary['ticket_catalog_visibility']) => void
}) {
  const {t}=useTranslation()
  const [mode, setMode] = useState<ContractSummary['ticket_catalog_visibility']>('CONTRACT_ONLY')
  useEffect(() => setMode(contract?.ticket_catalog_visibility ?? 'CONTRACT_ONLY'), [contract])
  const save = useMutation({
    mutationFn: async () => api.patch(`/contracts/${contract?.id}`, { ticket_catalog_visibility: mode }),
    onSuccess: () => onSaved(mode),
  })
  if (!contract) return null
  return <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
    <Typography variant="h6">{t('contractCatalogVisibility.title')}</Typography>
    <Typography color="text.secondary">{t('contractCatalogVisibility.subtitle',{contract:contract.contract_number})}</Typography>
    <Stack direction={{ xs: 'column', md: 'row' }} gap={1} mt={1.5}>
      <TextField select fullWidth label={t('contractCatalogVisibility.field')} value={mode} disabled={!canManage || save.isPending} onChange={event => setMode(event.target.value as ContractSummary['ticket_catalog_visibility'])}>
        <MenuItem value="CONTRACT_ONLY">{t('contractCatalogVisibility.contractOnly')}</MenuItem>
        <MenuItem value="ALL_WITH_COVERAGE_STATUS">{t('contractCatalogVisibility.allWithStatus')}</MenuItem>
      </TextField>
      {canManage && <Button variant="contained" disabled={save.isPending} onClick={() => save.mutate()}>{t('contractCatalogVisibility.save')}</Button>}
    </Stack>
    {mode === 'ALL_WITH_COVERAGE_STATUS' && <Alert severity="warning" sx={{ mt: 1 }}>{t('contractCatalogVisibility.warning')}</Alert>}
    {save.isSuccess && <Alert severity="success" sx={{ mt: 1 }}>{t('contractCatalogVisibility.saved')}</Alert>}
    {save.isError && <Alert severity="error" sx={{ mt: 1 }}>{t('contractCatalogVisibility.saveFailed')}</Alert>}
  </Paper>
}
