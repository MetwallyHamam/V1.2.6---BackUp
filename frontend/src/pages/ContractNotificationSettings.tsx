import { Alert, Autocomplete, Button, Chip, Divider, FormControlLabel, Paper, Stack, Switch, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";

type Settings = {
  enabled: boolean;
  reminder_days: number[];
  to_user_ids: number[];
  cc_user_ids: number[];
  subject_template: string;
  body_template: string;
  version: number;
};

type UserOption = { id: number; full_name: string; email: string };

type Delivery = {
  id: number;
  contract_number: string;
  contract_name: string;
  contract_end_date: string;
  milestone_key: string;
  channel: "SYSTEM" | "EMAIL";
  recipient: string;
  to: string[];
  cc: string[];
  status: string;
  queued_at: string;
  sent_at: string | null;
  last_error: string | null;
};

export function ContractNotificationSettings() {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["contract-notification-settings"],
    queryFn: async () => (await api.get<Settings>("/contracts/notification-settings")).data,
  });
  const deliveries = useQuery({
    queryKey: ["contract-notification-deliveries"],
    queryFn: async () => (await api.get<Delivery[]>("/contracts/notification-deliveries?limit=100")).data,
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
  });
  const users = useQuery({
    queryKey: ["contract-notification-recipient-options"],
    queryFn: async () => (await api.get<UserOption[]>("/contracts/notification-recipient-options")).data,
  });
  const [draft, setDraft] = useState<Settings | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => { if (query.data) setDraft(query.data); }, [query.data]);
  const save = useMutation({
    mutationFn: async (value: Settings) => (await api.put<Settings>("/contracts/notification-settings", value)).data,
    onSuccess: async value => { setDraft(value); setMessage("Rule saved and active contracts evaluated."); await Promise.all([cache.invalidateQueries({ queryKey: ["contract-notification-settings"] }), cache.invalidateQueries({ queryKey: ["contract-notification-deliveries"] })]); },
    onError: cause => setMessage(apiErrorMessage(cause, "The notification rule could not be saved.")),
  });
  if (query.isLoading || !draft) return <Typography color="text.secondary">Loading contract notification settings…</Typography>;
  if (query.isError) return <Alert severity="error">Contract notification settings could not be loaded.</Alert>;
  return <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
    <Typography variant="h5" fontWeight={800}>Contract expiration notifications</Typography>
    <Typography color="text.secondary" mb={2}>Configure email reminders. Saving evaluates active contracts immediately; scheduled checks handle future milestones. In-system reminders are delivered to eligible contract managers.</Typography>
    {message && <Alert severity={save.isError ? "error" : "success"} sx={{ mb: 2 }}>{message}</Alert>}
    <Stack spacing={2}>
      <FormControlLabel control={<Switch checked={draft.enabled} onChange={event => setDraft({ ...draft, enabled: event.target.checked })} />} label="Enable expiration emails" />
      <TextField label="Reminder days before expiration" value={draft.reminder_days.join(", ")} onChange={event => setDraft({ ...draft, reminder_days: event.target.value.split(",").map(value => Number(value.trim())).filter(value => Number.isInteger(value) && value >= 0) })} helperText="Example: 60, 30, 14, 7, 0. Each milestone is sent once per contract term." />
      <Autocomplete multiple options={users.data ?? []} value={(users.data ?? []).filter(user => draft.to_user_ids.includes(user.id))} getOptionLabel={user => `${user.full_name} (${user.email})`} isOptionEqualToValue={(option, value) => option.id === value.id} onChange={(_, value) => setDraft({ ...draft, to_user_ids: value.map(user => user.id), cc_user_ids: draft.cc_user_ids.filter(id => !value.some(user => user.id === id)) })} renderInput={params => <TextField {...params} required={draft.enabled} label="To users" helperText="These users receive both an in-system reminder and email." />} />
      <Autocomplete multiple options={(users.data ?? []).filter(user => !draft.to_user_ids.includes(user.id))} value={(users.data ?? []).filter(user => draft.cc_user_ids.includes(user.id))} getOptionLabel={user => `${user.full_name} (${user.email})`} isOptionEqualToValue={(option, value) => option.id === value.id} onChange={(_, value) => setDraft({ ...draft, cc_user_ids: value.map(user => user.id) })} renderInput={params => <TextField {...params} label="CC users" helperText="Optional users who receive the same in-system reminder and a copied email." />} />
      <TextField label="Email subject" value={draft.subject_template} onChange={event => setDraft({ ...draft, subject_template: event.target.value })} inputProps={{ dir: "ltr" }} />
      <TextField label="Email body" value={draft.body_template} onChange={event => setDraft({ ...draft, body_template: event.target.value })} multiline minRows={6} />
      <Alert severity="info">Available placeholders: {"{contract_number}, {contract_name}, {end_date}, {days_remaining}, {renewal_status}"}</Alert>
      <Button variant="contained" disabled={save.isPending || !draft.reminder_days.length || (draft.enabled && !draft.to_user_ids.length)} onClick={() => save.mutate(draft)} sx={{ alignSelf: "flex-start" }}>Save notification rule</Button>
      <Divider />
      <Typography variant="h6" fontWeight={800}>Recent notification activity</Typography>
      <Typography variant="body2" color="text.secondary">SENT means the mail server accepted the email, not that it reached the inbox. UNKNOWN means delivery could not be confirmed; automatic retries are stopped to avoid duplicates. PROCESSING that remains unchanged requires administrator review.</Typography>
      {deliveries.isLoading && <Typography color="text.secondary">Loading delivery activity…</Typography>}
      {deliveries.isError && <Alert severity="error">Delivery activity could not be loaded.</Alert>}
      {deliveries.isSuccess && !deliveries.data?.length && <Alert severity="info">No expiration notifications have been applied yet.</Alert>}
      {deliveries.data?.map(delivery => <Paper key={delivery.id} variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
          <Typography fontWeight={700}>{delivery.contract_number} — {delivery.contract_name}</Typography>
          <Chip size="small" label={delivery.channel === "SYSTEM" ? "In system" : "Email"} />
          <Chip size="small" color={delivery.status === "SENT" || delivery.status === "DELIVERED" ? "success" : delivery.status === "FAILED" || delivery.status === "SKIPPED" ? "error" : "warning"} label={delivery.status} />
        </Stack>
        <Typography variant="body2" color="text.secondary">Expires {delivery.contract_end_date} · milestone {delivery.milestone_key} · {delivery.channel === "EMAIL" ? `To: ${delivery.to.join("; ")}${delivery.cc.length ? ` · CC: ${delivery.cc.join("; ")}` : ""}` : delivery.recipient === "none" ? "No eligible contract manager" : `User ID: ${delivery.recipient}`}</Typography>
        {delivery.last_error && <Typography variant="body2" color="error.main">{delivery.last_error}</Typography>}
      </Paper>)}
    </Stack>
  </Paper>;
}
