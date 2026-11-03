import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from '@mui/material'
import { useState } from 'react'
import { api, apiErrorMessage } from '../api/client'

type Item = { id: number; code: string; name: string; is_active: boolean }

export function UatLibraryActions({ kind, item, onSaved }: { kind: 'test-cases' | 'templates'; item: Item; onSaved: () => Promise<void> }) {
  const [duplicate, setDuplicate] = useState(false)
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const base = `/uat/${kind}/${item.id}`
  const copy = async () => {
    setBusy(true)
    setError('')
    try {
      await api.post(`${base}/duplicate`, { code: code.trim(), name: name.trim() })
      await onSaved()
      setDuplicate(false)
    } catch (cause) { setError(apiErrorMessage(cause, 'Could not duplicate this item.')) }
    finally { setBusy(false) }
  }
  const archive = async () => {
    if (!window.confirm(`Archive ${item.code}? Existing cycles and checklist versions will keep their snapshots.`)) return
    setBusy(true)
    setError('')
    try { await api.post(`${base}/archive`); await onSaved() }
    catch (cause) { setError(apiErrorMessage(cause, 'Could not archive this item.')) }
    finally { setBusy(false) }
  }
  const remove = async () => {
    if (!window.confirm(`Remove ${item.code}? Cases used in checklists or cycles will be archived to preserve history.`)) return
    setBusy(true)
    setError('')
    try { const response = await api.delete<{ message: string }>(base); setNotice(response.data.message); await onSaved() }
    catch (cause) { setError(apiErrorMessage(cause, 'Could not remove this test case.')) }
    finally { setBusy(false) }
  }
  return <>
    <Stack direction="row" gap={1} flexWrap="wrap">
      <Button size="small" disabled={busy} onClick={() => { setCode(`${item.code}-COPY`); setName(`${item.name} copy`); setError(''); setDuplicate(true) }}>Duplicate</Button>
      {item.is_active && <Button size="small" color="warning" disabled={busy} onClick={archive}>Archive</Button>}
      {kind === 'test-cases' && <Button size="small" color="error" disabled={busy} onClick={remove}>Remove</Button>}
    </Stack>
    {notice && <Alert severity="info" onClose={() => setNotice('')}>{notice}</Alert>}
    {error && !duplicate && <Alert severity="error">{error}</Alert>}
    <Dialog open={duplicate} onClose={() => !busy && setDuplicate(false)} fullWidth maxWidth="sm">
      <DialogTitle>Duplicate {kind === 'templates' ? 'checklist' : 'test case'}</DialogTitle>
      <DialogContent><Stack gap={2} sx={{ pt: 1 }}>
        {error && <Alert severity="error">{error}</Alert>}
        <TextField required label="New code" value={code} onChange={(event) => setCode(event.target.value)} />
        <TextField required label="New name" value={name} onChange={(event) => setName(event.target.value)} />
      </Stack></DialogContent>
      <DialogActions><Button disabled={busy} onClick={() => setDuplicate(false)}>Cancel</Button><Button variant="contained" disabled={busy || !code.trim() || !name.trim()} onClick={copy}>Duplicate</Button></DialogActions>
    </Dialog>
  </>
}
