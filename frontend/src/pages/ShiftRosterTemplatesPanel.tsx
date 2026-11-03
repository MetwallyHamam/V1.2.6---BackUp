import { Add, ContentCopy, Delete, Edit } from '@mui/icons-material';
import { Alert, Box, Button, Checkbox, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FormEvent, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { getLocalizedName } from '../i18n/localizedMasterData';
import { serverDateInput } from '../utils/serverTime'
type ShiftType = {
    id: number;
    code: string;
    name: string;
    name_ar?: string;
    color: string;
};
type Department = {
    id: number;
    name: string;
    name_ar?: string;
    source_name?: string;
};
type User = {
    id: number;
    full_name: string;
    department?: string;
};
type RosterRow = {
    id?: number;
    shift_type_id: number | string;
    weekday: number;
    week_numbers: number[];
    start_time: string;
    end_time: string;
    work_location: string;
    user_ids: number[];
    notes: string;
};
type Roster = {
    id: number;
    department_id: number;
    code: string;
    name: string;
    week_start_day: number;
    effective_from?: string;
    effective_to?: string;
    is_active: boolean;
    rows: RosterRow[];
};
const days = [['Sunday', 6], ['Monday', 0], ['Tuesday', 1], ['Wednesday', 2], ['Thursday', 3], ['Friday', 4], ['Saturday', 5]] as const;
const blankRow = (shiftTypeId: number | string = ''): RosterRow => ({ shift_type_id: shiftTypeId, weekday: 6, week_numbers: [1, 2, 3, 4], start_time: '09:00', end_time: '17:00', work_location: 'WORK_FROM_HOME', user_ids: [], notes: '' });
export function ShiftRosterTemplatesPanel({ onApplied }: {
    onApplied?: () => void;
}) {
    const { t, i18n } = useTranslation(), language = i18n.resolvedLanguage === 'ar' ? 'ar' : 'en', dayLabel = (label: string) => t(`rosterTemplates.days.${label.toLowerCase()}`);
    const queryClient = useQueryClient(), [editing, setEditing] = useState<Roster | null>(null), [creating, setCreating] = useState(false), [deleting, setDeleting] = useState<Roster | null>(null), [applying, setApplying] = useState<Roster | null>(null), [rows, setRows] = useState<RosterRow[]>([]), [departmentId, setDepartmentId] = useState<number | string>(''), [name, setName] = useState(''), [weekStart, setWeekStart] = useState(6), [notice, setNotice] = useState(''), [expanded, setExpanded] = useState<number[]>([]);
    const rosters = useQuery({ queryKey: ['shift-roster-templates'], queryFn: async () => (await api.get<Roster[]>('/shift-roster-templates')).data }), types = useQuery({ queryKey: ['shift-types', language], queryFn: async () => (await api.get<ShiftType[]>('/shift-types')).data.map(type => ({ ...type, name: getLocalizedName(type, language) })) }), departments = useQuery({ queryKey: ['departments', language], queryFn: async () => (await api.get<Department[]>('/departments')).data.map(department => ({ ...department, source_name: department.name, name: getLocalizedName(department, language) })) }), users = useQuery({ queryKey: ['shift-template-users'], queryFn: async () => (await api.get<User[]>('/shift-employees')).data });
    const refresh = async () => queryClient.invalidateQueries({ queryKey: ['shift-roster-templates'] });
    const save = useMutation({ mutationFn: async (payload: Record<string, unknown>) => editing ? api.patch(`/shift-roster-templates/${editing.id}`, payload) : api.post('/shift-roster-templates', payload), onSuccess: async () => { await refresh(); closeEditor(); setNotice(t('rosterTemplates.saved')); } });
    const remove = useMutation({ mutationFn: async () => api.delete(`/shift-roster-templates/${deleting?.id}`), onSuccess: async () => { await refresh(); setDeleting(null); setNotice(t('rosterTemplates.deleted')); } });
    const apply = useMutation({ mutationFn: async (payload: Record<string, unknown>) => (await api.post<{
            created: number;
            skipped: number;
        }>(`/shift-roster-templates/${applying?.id}/apply-month`, payload)).data, onSuccess: async (result) => { await queryClient.invalidateQueries({ queryKey: ['shift-calendar'] }); setApplying(null); setNotice(t('rosterTemplates.generated', { created: result.created, skipped: result.skipped })); onApplied?.(); } });
    const departmentName = departments.data?.find(item => item.id === Number(departmentId))?.source_name;
    const eligibleUsers = useMemo(() => users.data?.filter(user => !departmentName || user.department === departmentName) ?? [], [users.data, departmentName]);
    const defaultType = types.data?.find(type => type.code.includes('WFH')) ?? types.data?.find(type => type.code === 'DAY') ?? types.data?.[0];
    function closeEditor() { setCreating(false); setEditing(null); }
    function openNew() { setEditing(null); setDepartmentId(''); setName(''); setWeekStart(6); setRows([blankRow(defaultType?.id)]); setCreating(true); }
    function openEdit(item: Roster) { setEditing(item); setDepartmentId(item.department_id); setName(item.name); setWeekStart(item.week_start_day); setRows(item.rows.map(row => ({ ...row, start_time: row.start_time.slice(0, 5), end_time: row.end_time.slice(0, 5), notes: row.notes ?? '' }))); }
    const update = (index: number, values: Partial<RosterRow>) => setRows(current => current.map((row, rowIndex) => rowIndex === index ? { ...row, ...values } : row));
    function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); save.mutate({ department_id: Number(departmentId), name, week_start_day: weekStart, effective_from: form.get('effective_from') || null, effective_to: form.get('effective_to') || null, is_active: true, rows: rows.map(row => ({ ...row, shift_type_id: Number(row.shift_type_id), id: undefined })) }); }
    const applyingDepartment = departments.data?.find(item => item.id === applying?.department_id)?.name;
    const applyingUsers = users.data?.filter(user => user.department === applyingDepartment) ?? [];
    return <Stack spacing={2}>
  <Paper sx={{ p: 2, borderInlineStart: '6px solid #00897b' }}><Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} gap={1}><Box flex={1}><Typography variant="h5" fontWeight={900}>{t('rosterTemplates.title')}</Typography><Typography color="text.secondary">{t('rosterTemplates.subtitle')}</Typography></Box><Button startIcon={<Add />} variant="contained" onClick={openNew}>{t('rosterTemplates.new')}</Button></Stack></Paper>
  {!rosters.data?.length && <Alert severity="info">{t('rosterTemplates.empty')}</Alert>}
  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(2,1fr)' }, gap: 2 }}>{rosters.data?.map(item => { const isExpanded = expanded.includes(item.id); return <Paper key={item.id} variant="outlined" sx={{ p: 2 }}><Stack direction="row"><Box flex={1}><Typography variant="h6" fontWeight={900}>{item.name}</Typography><Typography color="text.secondary">{departments.data?.find(row => row.id === item.department_id)?.name} · {t('rosterTemplates.rowCount', { count: item.rows.length })}</Typography></Box><Chip size="small" label={<span dir="ltr">{item.code}</span>}/></Stack><Stack spacing={.75} mt={1.5}>{item.rows.slice(0, isExpanded ? undefined : 5).map(row => <Typography key={row.id} variant="body2"><b>{dayLabel(days.find(([, value]) => value === row.weekday)?.[0] ?? '')}</b> · {types.data?.find(type => type.id === row.shift_type_id)?.name} · <span dir="ltr">{row.start_time.slice(0, 5)}–{row.end_time.slice(0, 5)}</span> · {t('rosterTemplates.weeksValue', { weeks: row.week_numbers.join(', ') })}</Typography>)}{item.rows.length > 5 && <Button size="small" sx={{ alignSelf: 'flex-start' }} aria-expanded={isExpanded} onClick={() => setExpanded(current => isExpanded ? current.filter(id => id !== item.id) : [...current, item.id])}>{isExpanded ? t('rosterTemplates.showLess') : t('rosterTemplates.moreRows', { count: item.rows.length - 5 })}</Button>}</Stack><Stack direction="row" mt={1}><Button startIcon={<Edit />} onClick={() => openEdit(item)}>{t('rosterTemplates.edit')}</Button><Button color="error" startIcon={<Delete />} onClick={() => setDeleting(item)}>{t('common.actions.delete')}</Button></Stack><Button fullWidth variant="contained" startIcon={<ContentCopy />} onClick={() => setApplying(item)}>{t('rosterTemplates.use')}</Button></Paper>; })}</Box>
  <Dialog open={creating || Boolean(editing)} onClose={closeEditor} fullWidth maxWidth="lg"><Box component="form" onSubmit={submit}><DialogTitle>{t(editing ? 'rosterTemplates.editTitle' : 'rosterTemplates.createTitle')}</DialogTitle><DialogContent><Alert severity="info">{t('rosterTemplates.editorHint')}</Alert><Stack direction={{ xs: 'column', md: 'row' }} gap={1}><TextField required label={t('rosterTemplates.name')} value={name} onChange={e => setName(e.target.value)} fullWidth margin="normal"/><TextField select required label={t('rosterTemplates.department')} value={departmentId} onChange={e => { setDepartmentId(Number(e.target.value)); setRows(current => current.map(row => ({ ...row, user_ids: [] }))); }} fullWidth margin="normal">{departments.data?.map(item => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField><TextField select label={t('rosterTemplates.weekStarts')} value={weekStart} onChange={e => setWeekStart(Number(e.target.value))} fullWidth margin="normal">{days.map(([label, value]) => <MenuItem key={value} value={value}>{dayLabel(label)}</MenuItem>)}</TextField></Stack><Stack direction={{ xs: 'column', sm: 'row' }} gap={1}><TextField required name="effective_from" type="date" label={t('rosterTemplates.dateFrom')} defaultValue={editing?.effective_from ?? ''} fullWidth margin="normal" slotProps={{ inputLabel: { shrink: true } }}/><TextField required name="effective_to" type="date" label={t('rosterTemplates.dateTo')} defaultValue={editing?.effective_to ?? ''} fullWidth margin="normal" slotProps={{ inputLabel: { shrink: true } }}/></Stack><Stack spacing={1.5} mt={1}>{rows.map((row, index) => <Paper key={index} variant="outlined" sx={{ p: 1.5 }}><Stack direction={{ xs: 'column', lg: 'row' }} gap={1} flexWrap="wrap"><TextField select label={t('rosterTemplates.day')} value={row.weekday} onChange={e => update(index, { weekday: Number(e.target.value) })}>{days.map(([label, value]) => <MenuItem key={value} value={value}>{dayLabel(label)}</MenuItem>)}</TextField><TextField select required label={t('rosterTemplates.shiftType')} value={row.shift_type_id} onChange={e => update(index, { shift_type_id: Number(e.target.value) })} sx={{ minWidth: 180 }}>{types.data?.map(type => <MenuItem key={type.id} value={type.id}>{type.name}</MenuItem>)}</TextField><TextField type="time" label={t('rosterTemplates.from')} value={row.start_time} onChange={e => update(index, { start_time: e.target.value })} slotProps={{ inputLabel: { shrink: true } }}/><TextField type="time" label={t('rosterTemplates.to')} value={row.end_time} onChange={e => update(index, { end_time: e.target.value })} slotProps={{ inputLabel: { shrink: true } }}/><TextField select label={t('rosterTemplates.location')} value={row.work_location} onChange={e => update(index, { work_location: e.target.value })}>{['OFFICE','WORK_FROM_HOME','HYBRID'].map(value=><MenuItem key={value} value={value}>{t(`rosterTemplates.locations.${value}`)}</MenuItem>)}</TextField><Button color="error" disabled={rows.length === 1} onClick={() => setRows(current => current.filter((_, rowIndex) => rowIndex !== index))}>{t('rosterTemplates.remove')}</Button></Stack><Typography fontWeight={800} mt={1}>{t('rosterTemplates.weeks')}</Typography>{[1, 2, 3, 4].map(week => <FormControlLabel key={week} control={<Checkbox checked={row.week_numbers.includes(week)} onChange={(_, checked) => update(index, { week_numbers: checked ? [...row.week_numbers, week] : row.week_numbers.filter(value => value !== week) })}/>} label={t('rosterTemplates.week',{value:week})}/>)}<TextField select fullWidth label={t('rosterTemplates.defaultEngineers')} value={row.user_ids} onChange={e => update(index, { user_ids: (e.target.value as unknown as number[]).map(Number) })} SelectProps={{ multiple: true, renderValue: value => (value as number[]).map(id => eligibleUsers.find(user => user.id === id)?.full_name).filter(Boolean).join(', ') }}>{eligibleUsers.map(user => <MenuItem key={user.id} value={user.id}><Checkbox checked={row.user_ids.includes(user.id)}/>{user.full_name}</MenuItem>)}</TextField><TextField fullWidth label={t('rosterTemplates.notes')} value={row.notes} onChange={e => update(index, { notes: e.target.value })} margin="normal"/></Paper>)}</Stack><Button startIcon={<Add />} sx={{ mt: 1 }} onClick={() => setRows(current => [...current, blankRow(defaultType?.id)])}>{t('rosterTemplates.addRow')}</Button>{save.isError && <Alert severity="error" sx={{ mt: 1 }}>{t('rosterTemplates.saveFailed')}</Alert>}</DialogContent><DialogActions><Button onClick={closeEditor}>{t('common.actions.cancel')}</Button><Button type="submit" variant="contained" disabled={!departmentId || !name.trim() || rows.some(row => !row.shift_type_id || !row.week_numbers.length)}>{t('rosterTemplates.saveRoster')}</Button></DialogActions></Box></Dialog>
  <Dialog open={Boolean(applying)} onClose={() => setApplying(null)} fullWidth maxWidth="sm"><Box component="form" onSubmit={event => { event.preventDefault(); const form = new FormData(event.currentTarget); apply.mutate({ date_from: form.get('date_from'), date_to: form.get('date_to'), user_ids: form.getAll('user_ids').map(Number), timezone: form.get('timezone'), skip_conflicts: true }); }}><DialogTitle>{t('rosterTemplates.useTitle', { name: applying?.name })}</DialogTitle><DialogContent><Alert severity="info">{t('rosterTemplates.applyHint')}</Alert><Stack direction={{ xs: 'column', sm: 'row' }} gap={1}><TextField required name="date_from" type="date" label={t('rosterTemplates.dateFrom')} defaultValue={serverDateInput()} fullWidth margin="normal" slotProps={{ inputLabel: { shrink: true } }}/><TextField required name="date_to" type="date" label={t('rosterTemplates.dateTo')} defaultValue={serverDateInput()} fullWidth margin="normal" slotProps={{ inputLabel: { shrink: true } }}/></Stack><TextField select required name="user_ids" label={t('rosterTemplates.engineers')} fullWidth margin="normal" slotProps={{ select: { multiple: true, defaultValue: [] } }}>{applyingUsers.map(user => <MenuItem key={user.id} value={user.id}>{user.full_name}</MenuItem>)}</TextField><TextField required name="timezone" label={t('rosterTemplates.timezone')} defaultValue="Africa/Cairo" inputProps={{ dir: 'ltr' }} fullWidth margin="normal"/>{applying?.rows.map(row => <Typography key={row.id} variant="body2">{dayLabel(days.find(([, value]) => value === row.weekday)?.[0] ?? '')} · {types.data?.find(type => type.id === row.shift_type_id)?.name} · {t('rosterTemplates.weeksValue', { weeks: row.week_numbers.join(', ') })}</Typography>)}</DialogContent><DialogActions><Button onClick={() => setApplying(null)}>{t('common.actions.cancel')}</Button><Button type="submit" variant="contained" disabled={apply.isPending}>{t('rosterTemplates.generateRoster')}</Button></DialogActions></Box></Dialog>
  <Dialog open={Boolean(deleting)} onClose={() => setDeleting(null)}><DialogTitle>{t('rosterTemplates.deleteTitle')}</DialogTitle><DialogContent><Typography>{deleting?.name}</Typography><Alert severity="warning" sx={{ mt: 1 }}>{t('rosterTemplates.deleteHint')}</Alert></DialogContent><DialogActions><Button onClick={() => setDeleting(null)}>{t('common.actions.cancel')}</Button><Button color="error" variant="contained" onClick={() => remove.mutate()}>{t('rosterTemplates.deleteAction')}</Button></DialogActions></Dialog>
  {notice && <Alert severity="success" onClose={() => setNotice('')}>{notice}</Alert>}
 </Stack>;
}
