import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, Switch, TextField, Typography } from '@mui/material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { api, apiErrorMessage } from '../api/client'
import { UatLibraryActions } from './UatLibraryActions'

type Case = { id: number; code: string; title: string; is_active: boolean; product_id: number | null; module_id: number | null; feature_name: string | null; description: string | null; preconditions: string | null; expected_result: string; priority: string; is_mandatory: boolean; steps: { action: string; expected_result: string }[] }
type Template = { id: number; code: string; name: string; description: string | null; product_id: number | null; category_id: number | null; scope_type: 'GLOBAL' | 'CLIENT' | 'CONTRACT'; client_id: number | null; client_ids: number[]; contract_id: number | null; current_version: number; is_active: boolean; test_case_ids: number[]; section_names: Record<number, string> }
type Metadata = { products: { id: number; name: string }[]; clients: { id: number; name: string }[]; contracts: { id: number; client_id: number; name: string }[]; modules: { id: number; product_id: number; name: string }[] }
type Category = { id: number; code: string; name: string; is_active: boolean }
type Draft = Omit<Template, 'id' | 'current_version' | 'is_active'> & { id?: number }
type CaseDraft = Omit<Case, 'id' | 'is_active'> & { id?: number }
const emptyDraft = (): Draft => ({ code: '', name: '', description: '', product_id: null, category_id: null, scope_type: 'GLOBAL', client_id: null, client_ids: [], contract_id: null, test_case_ids: [], section_names: {} })

export function UatChecklistBuilder({ cases, templates, metadata, canManage, onSaved }: { cases: Case[]; templates: Template[]; metadata: Metadata; canManage: boolean; onSaved: () => Promise<void> }) {
  const cache = useQueryClient()
  const [draft, setDraft] = useState<Draft | null>(null)
  const [draftMode, setDraftMode] = useState<'create' | 'edit' | 'version'>('create')
  const [sections, setSections] = useState<string[]>(['General'])
  const [newSection, setNewSection] = useState('')
  const [search, setSearch] = useState('')
  const [categoryCode, setCategoryCode] = useState('')
  const [categoryName, setCategoryName] = useState('')
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [editingCase, setEditingCase] = useState<CaseDraft | null>(null)
  const categories = useQuery({ queryKey: ['uat-checklist-categories'], queryFn: async () => (await api.get<Category[]>('/uat/checklist-categories')).data })
  const refresh = async () => { await onSaved(); await cache.invalidateQueries({ queryKey: ['uat-checklist-categories'] }) }
  const run = async (work: () => Promise<unknown>) => { setBusy(true); setError(''); try { await work(); await refresh() } catch (cause) { setError(apiErrorMessage(cause, 'Could not save the checklist.')) } finally { setBusy(false) } }
  const openTemplate = (template: Template, mode: 'edit' | 'version') => {
    setDraft({ id: template.id, code: template.code, name: template.name, description: template.description ?? '', product_id: template.product_id, category_id: template.category_id, scope_type: template.scope_type, client_id: template.client_id, client_ids: [...template.client_ids], contract_id: template.contract_id, test_case_ids: [...template.test_case_ids], section_names: { ...template.section_names } })
    setDraftMode(mode)
    setSections(['General', ...new Set(Object.values(template.section_names).filter((name) => name !== 'General'))])
    setError('')
  }
  const move = (index: number, direction: -1 | 1) => {
    if (!draft) return
    const ids = [...draft.test_case_ids]
    ;[ids[index], ids[index + direction]] = [ids[index + direction], ids[index]]
    setDraft({ ...draft, test_case_ids: ids })
  }
  const moveTo = (index: number, position: number) => {
    if (!draft) return
    const target = Math.max(0, Math.min(draft.test_case_ids.length - 1, position - 1))
    const ids = [...draft.test_case_ids]
    const [id] = ids.splice(index, 1)
    ids.splice(target, 0, id)
    setDraft({ ...draft, test_case_ids: ids })
  }
  const orderByModule = () => {
    if (!draft) return
    const moduleName = (id: number) => {
      const moduleId = cases.find((item) => item.id === id)?.module_id
      return metadata.modules.find((item) => item.id === moduleId)?.name ?? 'ZZZ · No module'
    }
    setDraft({ ...draft, test_case_ids: [...draft.test_case_ids].sort((left, right) => moduleName(left).localeCompare(moduleName(right)) || left - right) })
  }
  const changeModule = (item: Case, moduleId: number | null) => run(() => api.put(`/uat/test-cases/${item.id}`, {
    code: item.code, title: item.title, product_id: item.product_id, module_id: moduleId,
    feature_name: item.feature_name, description: item.description, preconditions: item.preconditions,
    expected_result: item.expected_result, priority: item.priority, is_mandatory: item.is_mandatory,
    steps: item.steps,
  }))
  const saveCase = async () => {
    if (!editingCase) return
    const isNew = !editingCase.id
    await run(async () => {
      const response = isNew ? await api.post<Case>('/uat/test-cases', editingCase) : await api.put<Case>(`/uat/test-cases/${editingCase.id}`, editingCase)
      if (isNew && draft) setDraft({ ...draft, test_case_ids: [...draft.test_case_ids, response.data.id], section_names: { ...draft.section_names, [response.data.id]: 'General' } })
      setEditingCase(null)
    })
  }
  const save = (event: FormEvent) => {
    event.preventDefault()
    if (!draft) return
    const payload = { ...draft, scope_type: 'GLOBAL', client_id: null, client_ids: [], contract_id: null, section_names: Object.fromEntries(draft.test_case_ids.map((id) => [id, draft.section_names[id] || 'General'])) }
    run(async () => {
      if (!draft.id) await api.post('/uat/templates', payload)
      else if (draftMode === 'version') await api.post(`/uat/templates/${draft.id}/versions`, payload)
      else await api.put(`/uat/templates/${draft.id}`, payload)
      setDraft(null)
    })
  }
  const available = cases.filter((item) => item.is_active && !draft?.test_case_ids.includes(item.id) && `${item.code} ${item.title}`.toLowerCase().includes(search.toLowerCase()))
  const exportTemplate = async (template: Template) => {
    const response = await api.get(`/uat/templates/${template.id}/export.xlsx`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data); const link = document.createElement('a')
    link.href = url; link.download = `${template.code}.xlsx`; link.click(); URL.revokeObjectURL(url)
  }
  return <Stack spacing={2}>
    {error && <Alert severity="error">{error}</Alert>}
    {canManage && <Button sx={{ alignSelf: 'flex-start' }} onClick={() => { setDraft(emptyDraft()); setDraftMode('create'); setSections(['General']); setError('') }}>New master template</Button>}
    {draft && <Paper component="form" sx={{ p: 2 }} onSubmit={save}><Stack spacing={1.5}>
      <Typography variant="h6">{draftMode === 'version' ? 'Create new template version' : draftMode === 'edit' ? 'Edit current template' : 'Create master template'}</Typography>
      <TextField required label="Code" value={draft.code} onChange={(event) => setDraft({ ...draft, code: event.target.value })} />
      <TextField required label="Name" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
      <TextField multiline label="Description" value={draft.description ?? ''} onChange={(event) => setDraft({ ...draft, description: event.target.value })} />
      <TextField select label="Category" value={draft.category_id ?? ''} onChange={(event) => setDraft({ ...draft, category_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">Uncategorized</MenuItem>{categories.data?.filter((item) => item.is_active || item.id === draft.category_id).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField select label="Product" value={draft.product_id ?? ''} onChange={(event) => setDraft({ ...draft, product_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">All products</MenuItem>{metadata.products.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <Alert severity="info">Master templates are reusable for every client. Choose the client only when starting a UAT cycle.</Alert>
      <Typography fontWeight={700}>Sections</Typography><Stack direction="row" gap={1}><TextField size="small" label="New section" value={newSection} onChange={(event) => setNewSection(event.target.value)} /><Button disabled={!newSection.trim() || sections.some((name) => name.toLowerCase() === newSection.trim().toLowerCase())} onClick={() => { setSections([...sections, newSection.trim()]); setNewSection('') }}>Add section</Button></Stack>
      {sections.filter((name) => name !== 'General').map((name) => <Stack key={name} direction="row" alignItems="center" gap={1}><Typography sx={{ flex: 1 }}>{name}</Typography><Button size="small" color="warning" onClick={() => { setSections(sections.filter((item) => item !== name)); setDraft({ ...draft, section_names: Object.fromEntries(Object.entries(draft.section_names).map(([id, section]) => [id, section === name ? 'General' : section])) }) }}>Remove section</Button></Stack>)}
      <Stack direction="row" alignItems="center"><Typography fontWeight={700} flex={1}>Selected tests · numbered execution order</Typography><Button onClick={orderByModule}>Order by module</Button></Stack>
      {draft.test_case_ids.map((id, index) => { const item = cases.find((row) => row.id === id); return <Stack key={id} direction={{ xs: 'column', md: 'row' }} alignItems={{ md: 'center' }} gap={1}><TextField size="small" type="number" label="Order" value={index + 1} onChange={(event) => moveTo(index, Number(event.target.value))} slotProps={{ htmlInput: { min: 1, max: draft.test_case_ids.length } }} sx={{ width: 90 }} /><Typography sx={{ flex: 1 }}>{item?.code ?? id} · {item?.title ?? 'Test case'}</Typography><TextField select size="small" label="Section" value={draft.section_names[id] || 'General'} onChange={(event) => setDraft({ ...draft, section_names: { ...draft.section_names, [id]: event.target.value } })} sx={{ minWidth: 180 }}>{sections.map((name) => <MenuItem key={name} value={name}>{name}</MenuItem>)}</TextField>{item && <TextField select size="small" label="Library module" value={item.module_id ?? ''} disabled={busy} onChange={(event) => changeModule(item, event.target.value ? Number(event.target.value) : null)} sx={{ minWidth: 170 }}><MenuItem value="">None</MenuItem>{metadata.modules.filter((module) => !item.product_id || module.product_id === item.product_id).map((module) => <MenuItem key={module.id} value={module.id}>{module.name}</MenuItem>)}</TextField>}<Button size="small" disabled={index === 0} onClick={() => move(index, -1)}>Up</Button><Button size="small" disabled={index === draft.test_case_ids.length - 1} onClick={() => move(index, 1)}>Down</Button>{item && <Button size="small" onClick={() => setEditingCase({ ...item })}>Edit case</Button>}<Button size="small" color="warning" onClick={() => setDraft({ ...draft, test_case_ids: draft.test_case_ids.filter((value) => value !== id) })}>Remove</Button></Stack> })}
      <Stack direction="row" gap={1}><TextField size="small" label="Search library tests" value={search} onChange={(event) => setSearch(event.target.value)} /><Button onClick={() => setEditingCase({ code: '', title: '', product_id: draft.product_id, module_id: null, feature_name: '', description: '', preconditions: '', expected_result: '', priority: 'MEDIUM', is_mandatory: true, steps: [{ action: '', expected_result: '' }] })}>Create library test</Button></Stack>
      <Stack direction="row" flexWrap="wrap" gap={1}>{available.slice(0, 50).map((item) => <Button key={item.id} size="small" variant="outlined" onClick={() => setDraft({ ...draft, test_case_ids: [...draft.test_case_ids, item.id], section_names: { ...draft.section_names, [item.id]: 'General' } })}>Add {item.code}</Button>)}</Stack>
      <Stack direction="row" gap={1}><Button type="submit" variant="contained" disabled={busy || !draft.test_case_ids.length}>{draftMode === 'version' ? 'Create version' : 'Save template'}</Button><Button onClick={() => setDraft(null)}>Cancel</Button></Stack>
    </Stack></Paper>}
    {templates.map((template) => <Paper key={template.id} sx={{ p: 2 }}><Stack direction="row" justifyContent="space-between" gap={1}><Stack><Typography fontWeight={700}>{template.code} · {template.name}</Typography><Typography variant="body2">Version {template.current_version} · {template.test_case_ids.length} tests · {categories.data?.find((item) => item.id === template.category_id)?.name ?? 'Uncategorized'}</Typography><Typography variant="caption">{[...new Set(Object.values(template.section_names))].join(' · ') || 'General section'} · reusable for every client</Typography></Stack><Stack direction="row" gap={1} flexWrap="wrap"><Button onClick={() => exportTemplate(template)}>Export master</Button>{canManage && <>{template.is_active && <Button onClick={() => openTemplate(template, 'edit')}>Edit</Button>}{template.is_active && <Button variant="contained" onClick={() => openTemplate(template, 'version')}>New version</Button>}<UatLibraryActions kind="templates" item={{ id: template.id, code: template.code, name: template.name, is_active: template.is_active }} onSaved={refresh} /></>}</Stack></Stack></Paper>)}
    {canManage && <Paper variant="outlined" sx={{ p: 2 }}><Typography variant="h6">Checklist categories</Typography><Stack direction={{ xs: 'column', md: 'row' }} gap={1}><TextField size="small" label="Code" value={categoryCode} onChange={(event) => setCategoryCode(event.target.value)} /><TextField size="small" label="Name" value={categoryName} onChange={(event) => setCategoryName(event.target.value)} /><Button disabled={busy || !categoryCode.trim() || !categoryName.trim()} onClick={() => run(async () => { await (editingCategoryId ? api.put(`/uat/checklist-categories/${editingCategoryId}`, { code: categoryCode, name: categoryName }) : api.post('/uat/checklist-categories', { code: categoryCode, name: categoryName })); setCategoryCode(''); setCategoryName(''); setEditingCategoryId(null) })}>{editingCategoryId ? 'Save category' : 'Add category'}</Button>{editingCategoryId && <Button onClick={() => { setEditingCategoryId(null); setCategoryCode(''); setCategoryName('') }}>Cancel</Button>}</Stack><Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 1 }}>{categories.data?.filter((item) => item.is_active).map((item) => <Stack key={item.id} direction="row" alignItems="center"><Typography variant="body2">{item.name}</Typography><Button size="small" onClick={() => { setEditingCategoryId(item.id); setCategoryCode(item.code); setCategoryName(item.name) }}>Edit</Button><Button size="small" color="warning" onClick={() => run(() => api.post(`/uat/checklist-categories/${item.id}/archive`))}>Archive</Button></Stack>)}</Stack></Paper>}
    <Dialog open={editingCase !== null} onClose={() => !busy && setEditingCase(null)} fullWidth maxWidth="md"><DialogTitle>{editingCase?.id ? 'Edit library test case' : 'Create library test case'}</DialogTitle><DialogContent>{editingCase && <Stack spacing={1.5} sx={{ pt: 1 }}>
      <TextField required label="Code" value={editingCase.code} onChange={(event) => setEditingCase({ ...editingCase, code: event.target.value })} />
      <TextField required label="Title" value={editingCase.title} onChange={(event) => setEditingCase({ ...editingCase, title: event.target.value })} />
      <TextField select label="Product" value={editingCase.product_id ?? ''} onChange={(event) => setEditingCase({ ...editingCase, product_id: event.target.value ? Number(event.target.value) : null, module_id: null })}><MenuItem value="">None</MenuItem>{metadata.products.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField select label="Module" value={editingCase.module_id ?? ''} onChange={(event) => setEditingCase({ ...editingCase, module_id: event.target.value ? Number(event.target.value) : null })}><MenuItem value="">None</MenuItem>{metadata.modules.filter((item) => !editingCase.product_id || item.product_id === editingCase.product_id).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField label="Feature" value={editingCase.feature_name ?? ''} onChange={(event) => setEditingCase({ ...editingCase, feature_name: event.target.value })} />
      <TextField multiline label="Description" value={editingCase.description ?? ''} onChange={(event) => setEditingCase({ ...editingCase, description: event.target.value })} />
      <TextField multiline label="Preconditions" value={editingCase.preconditions ?? ''} onChange={(event) => setEditingCase({ ...editingCase, preconditions: event.target.value })} />
      <TextField required multiline label="Expected result" value={editingCase.expected_result} onChange={(event) => setEditingCase({ ...editingCase, expected_result: event.target.value })} />
      <TextField select label="Priority" value={editingCase.priority} onChange={(event) => setEditingCase({ ...editingCase, priority: event.target.value })}>{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</TextField>
      <FormControlLabel label="Mandatory" control={<Switch checked={editingCase.is_mandatory} onChange={(event) => setEditingCase({ ...editingCase, is_mandatory: event.target.checked })} />} />
      {editingCase.steps.map((step, index) => <Stack key={index} direction="row" gap={1}><TextField fullWidth required label={`Step ${index + 1}`} value={step.action} onChange={(event) => setEditingCase({ ...editingCase, steps: editingCase.steps.map((row, position) => position === index ? { ...row, action: event.target.value } : row) })} /><TextField fullWidth required label="Expected" value={step.expected_result} onChange={(event) => setEditingCase({ ...editingCase, steps: editingCase.steps.map((row, position) => position === index ? { ...row, expected_result: event.target.value } : row) })} /><Button disabled={editingCase.steps.length === 1} onClick={() => setEditingCase({ ...editingCase, steps: editingCase.steps.filter((_, position) => position !== index) })}>Remove</Button></Stack>)}
      <Button onClick={() => setEditingCase({ ...editingCase, steps: [...editingCase.steps, { action: '', expected_result: '' }] })}>Add step</Button>
    </Stack>}</DialogContent><DialogActions><Button disabled={busy} onClick={() => setEditingCase(null)}>Cancel</Button><Button variant="contained" disabled={busy || !editingCase?.code.trim() || !editingCase.title.trim() || !editingCase.expected_result.trim() || editingCase.steps.some((step) => !step.action.trim() || !step.expected_result.trim())} onClick={saveCase}>Save test case</Button></DialogActions></Dialog>
  </Stack>
}
