import {
  Alert,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";

type FieldConfig = { enabled: boolean; required: boolean; path: string };
type Profile = {
  name: string;
  provider_key: string;
  enabled: boolean;
  source_type: string;
  processing_mode: string;
  default_priority: string;
  default_ticket_type_code: string;
  client_match_mode: string;
  fields: Record<string, FieldConfig>;
  request_type_mapping: Record<string, string>;
};
type Settings = { version: number; values: { profiles: Profile[] } };
type ApiClient = {
  id: number;
  name: string;
  key_prefix: string;
  provider_key?: string;
  auth_type: string;
  username?: string;
  is_active: boolean;
  last_used_at?: string;
};
type TicketType = { code: string; name: string; is_active: boolean };
type TestResult = {
  pre_ticket_number: string;
  request_type: string;
  client_match: string;
};
const fieldKeys = [
  "event_id",
  "request_type",
  "client",
  "ticket_type",
  "title",
  "description",
  "caller_name",
  "caller_number",
] as const;
const essential = new Set(["event_id", "request_type", "title"]);
const defaultFields = () =>
  Object.fromEntries(
    fieldKeys.map((key) => [
      key,
      { enabled: true, required: essential.has(key), path: key },
    ]),
  );

function mapPayload(
  fields: Record<string, FieldConfig>,
  values: Record<string, string>,
) {
  const payload: Record<string, unknown> = {};
  Object.entries(values).forEach(([key, value]) => {
    const field = fields[key];
    if (!field?.enabled || !value) return;
    const parts = field.path.split(".");
    let target = payload;
    parts.forEach((part, index) => {
      if (index === parts.length - 1) target[part] = value;
      else {
        if (!target[part] || typeof target[part] !== "object")
          target[part] = {};
        target = target[part] as Record<string, unknown>;
      }
    });
  });
  return payload;
}

export function InboundIntegrationSettings() {
  const qc = useQueryClient(),
    [selected, setSelected] = useState(""),
    [newKey, setNewKey] = useState(""),
    [testKey, setTestKey] = useState(""),
    [authType, setAuthType] = useState("API_KEY"),
    [result, setResult] = useState<TestResult | null>(null);
  const settings = useQuery({
    queryKey: ["inbound-settings"],
    queryFn: async () =>
      (await api.get<Settings>("/integrations/inbound-pre-ticket/settings"))
        .data,
  });
  const credentials = useQuery({
    queryKey: ["integration-api-clients"],
    queryFn: async () =>
      (await api.get<ApiClient[]>("/integrations/api-clients")).data,
  });
  const ticketTypes = useQuery({
    queryKey: ["ticket-types", "inbound"],
    queryFn: async () =>
      (await api.get<TicketType[]>("/ticket-types")).data.filter(
        (item) => item.is_active,
      ),
  });
  useEffect(() => {
    if (!selected && settings.data?.values.profiles[0])
      setSelected(settings.data.values.profiles[0].provider_key);
  }, [selected, settings.data]);
  const profile =
    settings.data?.values.profiles.find(
      (item) => item.provider_key === selected,
    ) ?? settings.data?.values.profiles[0];
  const saveAll = useMutation({
    mutationFn: (profiles: Profile[]) =>
      api.put("/integrations/inbound-pre-ticket/settings", {
        profiles,
        expected_version: settings.data?.version,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inbound-settings"] }),
  });
  const createKey = useMutation({
    mutationFn: async (values: Record<string, string>) =>
      (
        await api.post<{ api_key?: string; username?: string }>(
          "/integrations/api-clients",
          { ...values, provider_key: profile?.provider_key },
        )
      ).data,
    onSuccess: async (data) => {
      setNewKey(
        data.api_key ?? `Username: ${data.username} · password saved securely`,
      );
      if (data.api_key) setTestKey(data.api_key);
      await qc.invalidateQueries({ queryKey: ["integration-api-clients"] });
    },
  });
  const revoke = useMutation({
    mutationFn: (id: number) => api.delete(`/integrations/api-clients/${id}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["integration-api-clients"] }),
  });
  const test = useMutation({
    mutationFn: async (values: Record<string, string>) =>
      (
        await api.post<TestResult>(
          `/integrations/inbound/v1/${profile?.provider_key}/requests`,
          mapPayload(profile?.fields ?? {}, values),
          { headers: { "X-API-Key": testKey } },
        )
      ).data,
    onSuccess: (data) => setResult(data),
  });
  if (!settings.data || !profile)
    return <Paper sx={{ p: 3 }}>Loading inbound integrations…</Paper>;
  const activeProfile = profile;
  const profiles = settings.data.values.profiles,
    error = axios.isAxiosError(test.error)
      ? test.error.response?.data?.error
      : undefined;
  const ticketValues = Object.entries(profile.request_type_mapping)
      .filter(([, v]) => v === "CREATE_TICKET")
      .map(([k]) => k)
      .join(", "),
    callValues = Object.entries(profile.request_type_mapping)
      .filter(([, v]) => v === "REQUEST_CALL")
      .map(([k]) => k)
      .join(", ");
  function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget),
      request_type_mapping: Record<string, string> = {};
    String(f.get("ticket_values"))
      .split(",")
      .map((v) => v.trim().toUpperCase())
      .filter(Boolean)
      .forEach((v) => (request_type_mapping[v] = "CREATE_TICKET"));
    String(f.get("call_values"))
      .split(",")
      .map((v) => v.trim().toUpperCase())
      .filter(Boolean)
      .forEach((v) => (request_type_mapping[v] = "REQUEST_CALL"));
    const fields = Object.fromEntries(
      fieldKeys.map((key) => [
        key,
        {
          enabled: essential.has(key) || f.get(`enabled_${key}`) === "on",
          required: essential.has(key) || f.get(`required_${key}`) === "on",
          path: String(f.get(`path_${key}`) ?? "").trim(),
        },
      ]),
    );
    const updated = {
      name: String(f.get("name")),
      provider_key: String(f.get("provider_key")).toLowerCase(),
      enabled: f.get("enabled") === "on",
      source_type: String(f.get("source_type")),
      processing_mode: String(f.get("processing_mode")),
      default_priority: String(f.get("default_priority")),
      default_ticket_type_code: String(f.get("default_ticket_type_code")),
      client_match_mode: String(f.get("client_match_mode")),
      fields,
      request_type_mapping,
    };
    saveAll.mutate(
      profiles.map((item) =>
        item.provider_key === activeProfile.provider_key ? updated : item,
      ),
      { onSuccess: () => setSelected(updated.provider_key) },
    );
  }
  function addProfile() {
    let index = profiles.length + 1,
      key = `vendor-${index}`;
    while (profiles.some((item) => item.provider_key === key)) {
      index += 1;
      key = `vendor-${index}`;
    }
    const created: Profile = {
      name: `New Vendor ${index}`,
      provider_key: key,
      enabled: false,
      source_type: "OTHER",
      processing_mode: "PRE_TICKET",
      default_priority: "P3",
      default_ticket_type_code: ticketTypes.data?.[0]?.code ?? "INCIDENT",
      client_match_mode: "CODE_OR_EXACT_NAME",
      fields: defaultFields(),
      request_type_mapping: {
        CREATE_TICKET: "CREATE_TICKET",
        REQUEST_CALL: "REQUEST_CALL",
      },
    };
    saveAll.mutate([...profiles, created], {
      onSuccess: () => setSelected(key),
    });
  }
  function runTest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget),
      kind = String(f.get("request_type")),
      externalType =
        Object.entries(activeProfile.request_type_mapping).find(
          ([, v]) => v === kind,
        )?.[0] ?? kind;
    setResult(null);
    test.mutate({
      event_id: `ui-test-${Date.now()}`,
      request_type: externalType,
      client: String(f.get("client") ?? ""),
      ticket_type: String(f.get("ticket_type") ?? ""),
      title: String(f.get("title") ?? ""),
      description: String(f.get("description") ?? ""),
      caller_name: String(f.get("caller_name") ?? ""),
      caller_number: String(f.get("caller_number") ?? ""),
    });
  }
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2 }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          alignItems={{ sm: "center" }}
        >
          <TextField
            select
            label="Vendor profile"
            value={profile.provider_key}
            onChange={(e) => {
              setSelected(e.target.value);
              setResult(null);
              setNewKey("");
            }}
            sx={{ minWidth: 260 }}
          >
            {profiles.map((item) => (
              <MenuItem key={item.provider_key} value={item.provider_key}>
                {item.name} ({item.provider_key})
              </MenuItem>
            ))}
          </TextField>
          <Chip
            color={profile.enabled ? "success" : "default"}
            label={profile.enabled ? "Enabled" : "Disabled"}
          />
          <Button variant="outlined" onClick={addProfile}>
            Add vendor profile
          </Button>
          <Button
            color="error"
            disabled={profiles.length === 1}
            onClick={() =>
              saveAll.mutate(
                profiles.filter(
                  (item) => item.provider_key !== profile.provider_key,
                ),
                {
                  onSuccess: () =>
                    setSelected(
                      profiles.find(
                        (item) => item.provider_key !== profile.provider_key,
                      )?.provider_key ?? "",
                    ),
                },
              )
            }
          >
            Delete profile
          </Button>
        </Stack>
      </Paper>
      <Paper
        component="form"
        key={`${profile.provider_key}-${settings.data.version}`}
        onSubmit={saveProfile}
        sx={{ p: 3 }}
      >
        <Typography variant="h5">Vendor configuration</Typography>
        <Typography color="text.secondary" mb={2}>
          Each vendor has its own endpoint, credential scope, ticket defaults
          and payload rules.
        </Typography>
        {saveAll.isSuccess && (
          <Alert severity="success">Vendor configuration saved.</Alert>
        )}
        {saveAll.isError && (
          <Alert severity="error">Configuration could not be saved.</Alert>
        )}
        <Stack spacing={1.5} mt={1}>
          <FormControlLabel
            control={<Switch name="enabled" defaultChecked={profile.enabled} />}
            label="Enable this vendor"
          />
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              required
              name="name"
              label="Vendor name"
              defaultValue={profile.name}
              fullWidth
            />
            <TextField
              required
              name="provider_key"
              label="Provider key"
              defaultValue={profile.provider_key}
              helperText="Unique URL key; lowercase letters, numbers, - or _"
              fullWidth
            />
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              select
              name="source_type"
              label="Source"
              defaultValue={profile.source_type ?? "WHATSAPP"}
              fullWidth
            >
              {["WHATSAPP", "MONITORING", "EMAIL", "API", "OTHER"].map(
                (value) => (
                  <MenuItem key={value} value={value}>
                    {value}
                  </MenuItem>
                ),
              )}
            </TextField>
            <TextField
              select
              name="processing_mode"
              label="Processing"
              defaultValue={profile.processing_mode ?? "PRE_TICKET"}
              fullWidth
            >
              <MenuItem value="PRE_TICKET">Create pre-ticket</MenuItem>
              <MenuItem value="DIRECT_TICKET">Create ticket directly</MenuItem>
            </TextField>
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              select
              name="default_ticket_type_code"
              label="Default Ticket Type"
              defaultValue={profile.default_ticket_type_code}
              fullWidth
            >
              {ticketTypes.data?.map((item) => (
                <MenuItem key={item.code} value={item.code}>
                  {item.name} ({item.code})
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="default_priority"
              label="Default priority"
              defaultValue={profile.default_priority}
              fullWidth
            >
              {["P1", "P2", "P3", "P4"].map((v) => (
                <MenuItem key={v} value={v}>
                  {v}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="client_match_mode"
              label="Client matching"
              defaultValue={profile.client_match_mode}
              fullWidth
            >
              <MenuItem value="CODE_OR_EXACT_NAME">Code or exact name</MenuItem>
              <MenuItem value="CODE">Code only</MenuItem>
              <MenuItem value="EXACT_NAME">Exact name only</MenuItem>
            </TextField>
          </Stack>
          <Typography variant="h6">Request values</Typography>
          <Stack direction={{ xs: "column", md: "row" }} gap={1}>
            <TextField
              name="ticket_values"
              label="Create-ticket values"
              defaultValue={ticketValues}
              fullWidth
            />
            <TextField
              name="call_values"
              label="Request-call values"
              defaultValue={callValues}
              fullWidth
            />
          </Stack>
          <Typography variant="h6">Fields</Typography>
          <Typography variant="body2" color="text.secondary">
            Disabled fields are ignored. Required fields return a clear API
            validation error when missing. Core technical fields are locked.
          </Typography>
          {fieldKeys.map((key) => {
            const field = profile.fields[key] ?? {
                enabled: false,
                required: false,
                path: key,
              },
              locked = essential.has(key);
            return (
              <Stack
                key={key}
                direction={{ xs: "column", sm: "row" }}
                alignItems={{ sm: "center" }}
                gap={1}
              >
                <Typography sx={{ width: 150 }}>
                  {key.replaceAll("_", " ")}
                </Typography>
                <FormControlLabel
                  control={
                    <Checkbox
                      name={`enabled_${key}`}
                      defaultChecked={field.enabled}
                      disabled={locked}
                    />
                  }
                  label="Enabled"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      name={`required_${key}`}
                      defaultChecked={field.required}
                      disabled={locked}
                    />
                  }
                  label="Required"
                />
                <TextField
                  required
                  name={`path_${key}`}
                  label="JSON path"
                  defaultValue={field.path}
                  size="small"
                  fullWidth
                  inputProps={{ dir: "ltr" }}
                />
              </Stack>
            );
          })}
          <Button type="submit" variant="contained">
            Save vendor
          </Button>
        </Stack>
      </Paper>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Credentials for {profile.name}</Typography>
        <Stack
          component="form"
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          my={1}
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget),
              name = String(f.get("name")).trim();
            if (name)
              createKey.mutate({
                name,
                auth_type: authType,
                username: String(f.get("username") ?? ""),
                password: String(f.get("password") ?? ""),
              });
          }}
        >
          <TextField required name="name" label="Credential name" fullWidth />
          <TextField
            select
            label="Authentication"
            value={authType}
            onChange={(e) => setAuthType(e.target.value)}
            sx={{ minWidth: 180 }}
          >
            <MenuItem value="API_KEY">API key</MenuItem>
            <MenuItem value="BASIC">Username/password</MenuItem>
          </TextField>
          {authType === "BASIC" && (
            <>
              <TextField required name="username" label="API username" />
              <TextField
                required
                name="password"
                type="password"
                label="API password"
                inputProps={{ minLength: 12 }}
              />
            </>
          )}
          <Button type="submit" variant="outlined">
            Create credential
          </Button>
        </Stack>
        {newKey && (
          <Alert severity="warning" sx={{ wordBreak: "break-all" }}>
            Copy now: <span dir="ltr">{newKey}</span>
          </Alert>
        )}
        <Stack spacing={1} mt={1}>
          {credentials.data
            ?.filter(
              (row) =>
                row.provider_key === profile.provider_key ||
                (!row.provider_key && profile.provider_key === "whatsapp"),
            )
            .map((row) => (
              <Stack key={row.id} direction="row" alignItems="center" gap={1}>
                <Typography sx={{ flex: 1 }}>
                  {row.name} ·{" "}
                  {row.auth_type === "BASIC" ? row.username : row.key_prefix}
                </Typography>
                <Chip size="small" label={row.auth_type} />
                <Chip
                  size="small"
                  color={row.is_active ? "success" : "default"}
                  label={row.is_active ? "Active" : "Revoked"}
                />
                <Button
                  color="error"
                  size="small"
                  disabled={!row.is_active}
                  onClick={() => revoke.mutate(row.id)}
                >
                  Revoke
                </Button>
              </Stack>
            ))}
        </Stack>
      </Paper>
      <Paper component="form" onSubmit={runTest} sx={{ p: 3 }}>
        <Typography variant="h6">Test {profile.name}</Typography>
        {!profile.enabled && (
          <Alert severity="warning">
            Enable and save this vendor before testing.
          </Alert>
        )}
        {error && (
          <Alert severity="error">
            <strong>{error.code}</strong>: {error.message}
          </Alert>
        )}
        {result && (
          <Alert severity="success">
            Created {result.pre_ticket_number} · Client {result.client_match}
          </Alert>
        )}
        <Stack spacing={1.5} mt={1}>
          <TextField
            required
            type="password"
            label="Scoped API key"
            value={testKey}
            onChange={(e) => setTestKey(e.target.value)}
          />
          <TextField
            select
            name="request_type"
            label="Request type"
            defaultValue="REQUEST_CALL"
          >
            <MenuItem value="REQUEST_CALL">Request call</MenuItem>
            <MenuItem value="CREATE_TICKET">Create ticket request</MenuItem>
          </TextField>
          {fieldKeys
            .filter(
              (key) =>
                !["event_id", "request_type"].includes(key) &&
                profile.fields[key]?.enabled,
            )
            .map((key) => (
              <TextField
                key={key}
                name={key}
                label={key.replaceAll("_", " ")}
                required={profile.fields[key].required}
                defaultValue={
                  key === "ticket_type"
                    ? profile.default_ticket_type_code
                    : key === "title"
                      ? `${profile.name} integration test`
                      : ""
                }
                multiline={key === "description"}
              />
            ))}
          <Button
            type="submit"
            variant="contained"
            disabled={!profile.enabled || !testKey || test.isPending}
          >
            Create test Pre-Ticket
          </Button>
        </Stack>
      </Paper>
      <Alert severity="info">
        Endpoint: POST /api/v1/integrations/inbound/v1/{profile.provider_key}
        /requests · Ticket Types: GET /ticket-types · Vendor credentials cannot
        be used with another profile.
      </Alert>
    </Stack>
  );
}
