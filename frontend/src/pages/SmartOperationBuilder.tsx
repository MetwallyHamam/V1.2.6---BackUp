import { AutoAwesome, ExpandMore } from '@mui/icons-material';
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip, MenuItem, Paper, Snackbar, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FormEvent, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { getLocalizedName } from '../i18n/localizedMasterData';
import { serverDateInput } from '../utils/serverTime'
type Frequency = 'ONCE' | 'DAILY' | 'WEEKLY' | 'EVERY_N_WEEKS' | 'MONTHLY' | 'QUARTERLY' | 'SPECIFIC_DATES' | 'CUSTOM';
type Strategy = 'MANUAL' | 'FIXED' | 'ROTATION' | 'AUTO_BALANCE' | 'KEEP_EXISTING';
type OperationType = {
    id: number;
    code: string;
    name: string;
    name_ar?: string;
    requires_client: boolean;
    visit_behavior: string;
};
type Client = {
    id: number;
    code: string;
    name: string;
};
type Employee = {
    id: number;
    full_name: string;
};
type Rotation = {
    id: number;
    name: string;
};
type Candidate = {
    employee_id: number;
    employee_name: string;
    assigned: boolean;
    available: boolean;
    shift_minutes: number;
    operation_minutes: number;
    visit_minutes: number;
    reason: string;
};
type Slot = {
    slot_key: string;
    date: string;
    starts_at: string;
    ends_at: string;
    assigned_user_names: string[];
    unassigned_positions: number;
    candidates: Candidate[];
    entitlement_status: 'NOT_REQUIRED' | 'COVERED' | 'NO_ACTIVE_ENTITLEMENT' | 'ALLOWANCE_EXHAUSTED';
    entitlement_sequence: number | null;
};
type Preview = {
    preview_hash: string;
    slot_count: number;
    required_positions: number;
    assigned_positions: number;
    unassigned_positions: number;
    conflict_count: number;
    entitlement_issue_count: number;
    workload_balance_percent: number;
    slots: Slot[];
};
type Request = {
    title: string;
    operation_type: string;
    client_id: number | null;
    start_time: string;
    end_time: string;
    recurrence: {
        frequency: Frequency;
        date_from: string;
        date_to: string;
        interval: number;
        weekdays: number[];
        specific_dates: string[];
    };
    timezone: string;
    required_headcount: number;
    assignment_strategy: Strategy;
    rotation_id: number | null;
    fixed_user_ids: number[];
    location: string | null;
    description: string | null;
    status: 'PLANNED';
};
const today = () => serverDateInput();
const later = () => serverDateInput(new Date(Date.now() + 28 * 86400000));
const days = [['Mon', 0], ['Tue', 1], ['Wed', 2], ['Thu', 3], ['Fri', 4], ['Sat', 5], ['Sun', 6]] as const;
export function SmartOperationBuilder({ onApplied }: {
    onApplied?: () => void;
}) {
    const { t, i18n } = useTranslation();
    const language = i18n.resolvedLanguage === 'ar' ? 'ar' : 'en';
    const locale = i18n.resolvedLanguage === 'ar' ? 'ar-EG' : 'en-US';
    const queryClient = useQueryClient();
    const [title, setTitle] = useState(''), [operationType, setOperationType] = useState(''), [clientId, setClientId] = useState(''), [startTime, setStartTime] = useState('09:00'), [endTime, setEndTime] = useState('10:00'), [dateFrom, setDateFrom] = useState(today()), [dateTo, setDateTo] = useState(later()), [frequency, setFrequency] = useState<Frequency>('WEEKLY'), [interval, setInterval] = useState(1), [weekdays, setWeekdays] = useState<number[]>([]), [specificDates, setSpecificDates] = useState(''), [headcount, setHeadcount] = useState(1), [strategy, setStrategy] = useState<Strategy>('AUTO_BALANCE'), [rotationId, setRotationId] = useState(''), [fixedIds, setFixedIds] = useState<number[]>([]), [location, setLocation] = useState(''), [description, setDescription] = useState(''), [snapshot, setSnapshot] = useState<Request | null>(null), [notice, setNotice] = useState('');
    const types = useQuery({ queryKey: ['internal-operation-types',language], queryFn: async () => (await api.get<OperationType[]>('/internal-operations/types')).data.map(type=>({...type,name:getLocalizedName(type,language)})) }), clients = useQuery({ queryKey: ['internal-operation-clients'], queryFn: async () => (await api.get<Client[]>('/internal-operations/clients')).data }), employees = useQuery({ queryKey: ['internal-operation-engineers'], queryFn: async () => (await api.get<Employee[]>('/internal-operations/engineers')).data }), rotations = useQuery({ queryKey: ['assignment-rotations'], queryFn: async () => (await api.get<Rotation[]>('/assignment-rotations')).data });
    const selectedType = types.data?.find(row => row.code === operationType), requiresClient = Boolean(selectedType && (selectedType.requires_client || selectedType.visit_behavior === 'REQUIRED' || selectedType.code === 'OUTDOOR_VISIT'));
    const request = useMemo<Request>(() => ({ title, operation_type: operationType, client_id: clientId ? Number(clientId) : null, start_time: startTime, end_time: endTime, recurrence: { frequency, date_from: dateFrom, date_to: dateTo, interval, weekdays, specific_dates: specificDates.split(/[,\s]+/).filter(Boolean) }, timezone: 'Africa/Cairo', required_headcount: headcount, assignment_strategy: strategy, rotation_id: rotationId ? Number(rotationId) : null, fixed_user_ids: fixedIds, location: location || null, description: description || null, status: 'PLANNED' }), [title, operationType, clientId, startTime, endTime, frequency, dateFrom, dateTo, interval, weekdays, specificDates, headcount, strategy, rotationId, fixedIds, location, description]);
    const preview = useMutation({ mutationFn: async (payload: Request) => (await api.post<Preview>('/internal-operations/generator/preview', payload)).data, onSuccess: (_, payload) => setSnapshot(payload) });
    const apply = useMutation({ mutationFn: async () => (await api.post<{
            batch_id: number;
            created_operations: number;
            created_visit_occurrences: number;
        }>('/internal-operations/generator/apply', { request: snapshot, preview_hash: preview.data?.preview_hash })).data, onSuccess: async (result) => { await queryClient.invalidateQueries({ queryKey: ['internal-operations'] }); await queryClient.invalidateQueries({ queryKey: ['overview-operations'] }); setNotice(t('smartOperation.generated', { batch: result.batch_id, operations: result.created_operations, visits: result.created_visit_occurrences })); preview.reset(); setSnapshot(null); onApplied?.(); } });
    const changed = Boolean(snapshot && JSON.stringify(snapshot) !== JSON.stringify(request)), valid = Boolean(title.trim().length >= 3 && operationType && dateTo >= dateFrom && (!requiresClient || clientId) && (strategy !== 'FIXED' || fixedIds.length > 0) && (strategy !== 'ROTATION' || rotationId));
    function submit(event: FormEvent) { event.preventDefault(); preview.mutate(request); }
    return <Paper sx={{ p: 2 }}>
<Stack direction="row" gap={1} alignItems="center">
<AutoAwesome color="secondary"/>
<Box>
<Typography variant="h5" fontWeight={900}>{t('smartOperation.title')}</Typography>
<Typography color="text.secondary">{t('smartOperation.subtitle')}</Typography>
</Box>
</Stack>
<Box component="form" onSubmit={submit}>
<Stack direction={{ xs: 'column', md: 'row' }} gap={1.25} mt={2}>
<TextField required label={t('smartOperation.titleField')} value={title} onChange={event => { setTitle(event.target.value); preview.reset(); }} fullWidth/>
<TextField required select label={t('smartOperation.operationType')} value={operationType} onChange={event => { const code = event.target.value; setOperationType(code); if (!title)
        setTitle(types.data?.find(row => row.code === code)?.name ?? ''); preview.reset(); }} fullWidth>{types.data?.map(row => <MenuItem key={row.id} value={row.code}>{row.name}</MenuItem>)}</TextField>
<TextField select required={requiresClient} label={t('smartOperation.client')} value={clientId} onChange={event => { setClientId(event.target.value); preview.reset(); }} fullWidth>
<MenuItem value="">{t('smartOperation.noClient')}</MenuItem>{clients.data?.map(row => <MenuItem key={row.id} value={row.id}><span dir="ltr">{row.code}</span>&nbsp;— {row.name}</MenuItem>)}</TextField>
</Stack>
<Stack direction={{ xs: 'column', md: 'row' }} gap={1.25} mt={1.25}>
<TextField type="time" label={t('smartOperation.starts')} value={startTime} onChange={event => { setStartTime(event.target.value); preview.reset(); }} slotProps={{ inputLabel: { shrink: true } }}/>
<TextField type="time" label={t('smartOperation.ends')} value={endTime} onChange={event => { setEndTime(event.target.value); preview.reset(); }} slotProps={{ inputLabel: { shrink: true } }}/>
<TextField select label={t('smartOperation.recurrence')} value={frequency} onChange={event => { setFrequency(event.target.value as Frequency); preview.reset(); }} sx={{ minWidth: 190 }}>{(['ONCE', 'DAILY', 'WEEKLY', 'EVERY_N_WEEKS', 'MONTHLY', 'QUARTERLY', 'SPECIFIC_DATES', 'CUSTOM'] as Frequency[]).map(value => <MenuItem key={value} value={value}>{t(`smartOperation.frequency.${value}`)}</MenuItem>)}</TextField>
<TextField type="date" label={t('common.from')} value={dateFrom} onChange={event => { setDateFrom(event.target.value); preview.reset(); }} slotProps={{ inputLabel: { shrink: true } }}/>
<TextField type="date" label={t('common.to')} value={dateTo} onChange={event => { setDateTo(event.target.value); preview.reset(); }} slotProps={{ inputLabel: { shrink: true } }}/>
</Stack>{frequency === 'EVERY_N_WEEKS' && <TextField type="number" label={t('smartOperation.everyNWeeks')} value={interval} onChange={event => setInterval(Number(event.target.value))} inputProps={{ min: 1, max: 52 }} sx={{ mt: 1.25 }}/>} 
{frequency === 'CUSTOM' && <Stack direction="row" gap={.75} mt={1.25}>{days.map(([label, value]) => <Chip key={value} label={t(`smartOperation.days.${label}`)} color={weekdays.includes(value) ? 'secondary' : 'default'} onClick={() => setWeekdays(current => current.includes(value) ? current.filter(day => day !== value) : [...current, value])}/>)}</Stack>}
{frequency === 'SPECIFIC_DATES' && <TextField fullWidth margin="normal" label={t('smartOperation.specificDates')} placeholder="2030-09-01, 2030-09-08" inputProps={{dir:'ltr'}} value={specificDates} onChange={event => setSpecificDates(event.target.value)}/>}<Stack direction={{ xs: 'column', md: 'row' }} gap={1.25} mt={1.25}>
<TextField type="number" label={t('smartOperation.requiredEngineers')} value={headcount} onChange={event => setHeadcount(Number(event.target.value))} inputProps={{ min: 1, max: 100 }}/>
<TextField select label={t('smartOperation.assignment')} value={strategy} onChange={event => { setStrategy(event.target.value as Strategy); preview.reset(); }} sx={{ minWidth: 200 }}>{(['MANUAL', 'FIXED', 'ROTATION', 'AUTO_BALANCE', 'KEEP_EXISTING'] as Strategy[]).map(value => <MenuItem key={value} value={value}>{t(`smartOperation.strategy.${value}`)}</MenuItem>)}</TextField>{strategy === 'ROTATION' && <TextField select label={t('smartOperation.rotation')} value={rotationId} onChange={event => setRotationId(event.target.value)} sx={{ minWidth: 220 }}>{rotations.data?.map(row => <MenuItem key={row.id} value={row.id}>{row.name}</MenuItem>)}</TextField>}
{strategy === 'FIXED' && <TextField select label={t('smartOperation.engineers')} value={fixedIds} onChange={event => { const value = event.target.value; setFixedIds(typeof value === 'string' ? value.split(',').filter(Boolean).map(Number) : value); }} slotProps={{ select: { multiple: true } }} sx={{ minWidth: 260 }}>{employees.data?.map(row => <MenuItem key={row.id} value={row.id}>{row.full_name}</MenuItem>)}</TextField>}</Stack>
<Stack direction={{ xs: 'column', md: 'row' }} gap={1.25} mt={1.25}>
<TextField label={t('smartOperation.location')} value={location} onChange={event => setLocation(event.target.value)} fullWidth/>
<TextField label={t('smartOperation.description')} value={description} onChange={event => setDescription(event.target.value)} fullWidth/>
</Stack>
<Button type="submit" variant="contained" color="secondary" disabled={!valid || preview.isPending} sx={{ mt: 2 }}>{t('smartOperation.preview')}</Button>
</Box>
  {preview.isError && <Alert severity="error" sx={{ mt: 2 }}>{t('smartOperation.previewFailed')}</Alert>}
{preview.data && <Stack spacing={1.25} mt={2}>{changed && <Alert severity="warning">{t('smartOperation.changed')}</Alert>}<Stack direction="row" gap={1} flexWrap="wrap">
<Chip label={t('smartOperation.operations',{count:preview.data.slot_count})}/>
<Chip label={t('smartOperation.assigned',{assigned:preview.data.assigned_positions,required:preview.data.required_positions})} color={preview.data.unassigned_positions ? 'warning' : 'success'}/>
<Chip label={t('smartOperation.balance',{percent:preview.data.workload_balance_percent})}/>{preview.data.entitlement_issue_count > 0 && <Chip color="error" label={t('smartOperation.entitlementIssues',{count:preview.data.entitlement_issue_count})}/>}</Stack>{preview.data.slots.map(slot => <Accordion key={slot.slot_key} disableGutters>
<AccordionSummary expandIcon={<ExpandMore />}>
<Box flex={1}>
<Typography fontWeight={800}>{new Date(slot.starts_at).toLocaleString(locale)} · {slot.assigned_user_names.join(', ') || t('smartOperation.unassigned')}</Typography>
<Typography variant="caption">{slot.entitlement_status === 'COVERED' ? t('smartOperation.covered',{sequence:slot.entitlement_sequence}) : t(`smartOperation.entitlement.${slot.entitlement_status}`)}</Typography>
</Box>
<Chip size="small" color={slot.entitlement_status === 'NO_ACTIVE_ENTITLEMENT' || slot.entitlement_status === 'ALLOWANCE_EXHAUSTED' ? 'error' : slot.unassigned_positions ? 'warning' : 'success'} label={slot.unassigned_positions ? t('smartOperation.unassignedCount',{count:slot.unassigned_positions}) : t('smartOperation.ready')}/>
</AccordionSummary>
<AccordionDetails>{slot.candidates.map(row => <Typography key={row.employee_id} variant="body2">
<b>{row.employee_name}</b> — {row.assigned ? t('smartOperation.assignedLabel') : row.reason} · {t('smartOperation.totalHours',{hours:new Intl.NumberFormat(locale,{maximumFractionDigits:1}).format((row.shift_minutes+row.operation_minutes+row.visit_minutes)/60)})}</Typography>)}</AccordionDetails>
</Accordion>)}<Button variant="contained" color="success" disabled={changed || preview.data.entitlement_issue_count > 0 || apply.isPending} onClick={() => apply.mutate()}>{t('smartOperation.generateReviewed')}</Button>{apply.isError && <Alert severity="error">{t('smartOperation.stale')}</Alert>}</Stack>}<Snackbar open={Boolean(notice)} autoHideDuration={6000} onClose={() => setNotice('')} message={notice}/>
</Paper>;
}
