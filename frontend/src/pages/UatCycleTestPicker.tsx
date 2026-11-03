import { Button, Checkbox, FormControlLabel, Paper, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'

type Case = { id: number; code: string; title: string; is_active: boolean; product_id: number | null }
type Template = { id: number; name: string; current_version: number; is_active: boolean; scope_type: 'GLOBAL' | 'CLIENT' | 'CONTRACT'; client_id: number | null; contract_id: number | null; product_id: number | null; test_case_ids: number[] }
type Cycle = { client_id: number; contract_id: number | null; product_id: number | null; tests: { test_case_id: number | null }[] }
type Selection = { template_ids: number[]; test_case_ids: number[] }

export function UatCycleTestPicker({ cycle, cases, templates, value, onChange }: { cycle: Cycle; cases: Case[]; templates: Template[]; value: Selection; onChange: (value: Selection) => void }) {
  const [search, setSearch] = useState('')
  const existing = new Set(cycle.tests.map((test) => test.test_case_id).filter((id): id is number => id !== null))
  const availableCases = cases.filter((test) => test.is_active && !existing.has(test.id) && (!cycle.product_id || !test.product_id || test.product_id === cycle.product_id))
  const filtered = availableCases.filter((test) => `${test.code} ${test.title}`.toLowerCase().includes(search.toLowerCase()))
  const availableTemplates = templates.filter((template) => template.is_active &&
    (template.scope_type === 'GLOBAL' || template.client_id === cycle.client_id) &&
    (template.scope_type !== 'CONTRACT' || template.contract_id === cycle.contract_id) &&
    (!template.product_id || !cycle.product_id || template.product_id === cycle.product_id))
  const selectedCases = [...value.test_case_ids, ...availableTemplates.filter((template) => value.template_ids.includes(template.id)).flatMap((template) => template.test_case_ids)]
  const toAdd = new Set(selectedCases.filter((id) => !existing.has(id)))
  const skipped = selectedCases.length - toAdd.size
  const selectVisible = () => onChange({ ...value, test_case_ids: [...new Set([...value.test_case_ids, ...filtered.map((test) => test.id)])] })
  return <Paper variant="outlined" sx={{ p: 1.5 }}><Stack spacing={1}>
    <Typography fontWeight={700}>Checklists</Typography><Stack direction="row" flexWrap="wrap" gap={1}>{availableTemplates.map((template) => <FormControlLabel key={template.id} control={<Checkbox checked={value.template_ids.includes(template.id)} onChange={(event) => onChange({ ...value, template_ids: event.target.checked ? [...value.template_ids, template.id] : value.template_ids.filter((id) => id !== template.id) })} />} label={`${template.name} · v${template.current_version} · ${template.test_case_ids.length} tests`} />)}</Stack>
    <Typography fontWeight={700}>Library tests</Typography><Stack direction="row" gap={1}><TextField size="small" label="Search code or title" value={search} onChange={(event) => setSearch(event.target.value)} /><Button onClick={selectVisible} disabled={!filtered.length}>Select visible ({filtered.length})</Button><Button onClick={() => onChange({ ...value, test_case_ids: [] })}>Clear individual tests</Button></Stack>
    <Stack direction="row" flexWrap="wrap" gap={1}>{filtered.slice(0, 100).map((test) => <FormControlLabel key={test.id} control={<Checkbox checked={value.test_case_ids.includes(test.id)} onChange={(event) => onChange({ ...value, test_case_ids: event.target.checked ? [...value.test_case_ids, test.id] : value.test_case_ids.filter((id) => id !== test.id) })} />} label={`${test.code} · ${test.title}`} />)}</Stack>
    {filtered.length > 100 && <Typography variant="caption">Showing the first 100 matches. Narrow the search to find more tests.</Typography>}
    <Typography variant="body2">{toAdd.size} new test{toAdd.size === 1 ? '' : 's'} selected · {skipped} duplicate selection{skipped === 1 ? '' : 's'} skipped</Typography>
  </Stack></Paper>
}
