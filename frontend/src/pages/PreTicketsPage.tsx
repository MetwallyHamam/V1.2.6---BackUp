import {
  ArrowBack,
} from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Client = {
  id: number;
  name: string;
  is_active: boolean;
  ticket_creation_allowed: boolean;
  ticket_count: number;
};
type Contact = { id: number; full_name: string; is_active: boolean };
type Product = { id: number; name: string; is_active?: boolean; covered?: boolean };
type Module = { id: number; name: string; product_id: number; covered?: boolean };
type Service = { id: number; name: string; module_ids?: number[]; covered?: boolean };
type ContractCatalog = { products: Product[]; modules: Module[]; services: Service[] };
type FormSetting = { field_key: string; is_required: boolean };
type PreTicket = {
  id: number;
  pre_ticket_number: string;
  status: string;
  request_kind: "TICKET_REQUEST" | "CALL_REQUEST";
  source_provider?: string;
  external_caller_name?: string;
  external_caller_number?: string;
  requested_ticket_type_code?: string;
  client_id?: number;
  requester_contact_id?: number;
  product_id?: number;
  product_module_id?: number;
  service_id?: number;
  proposed_priority: string;
  title: string;
  submitted_at: string;
  claimed_by_user_id?: number;
  resulting_ticket_id?: number;
  information_request?: string;
  engineer_response?: string;
  version: number;
};
type Metrics = {
  total: number;
  by_status: Record<string, number>;
  average_minutes_to_claim: number | null;
  average_minutes_claim_to_ticket: number | null;
  average_minutes_to_ticket: number | null;
  by_client: MetricBucket[];
  by_product: MetricBucket[];
  by_priority: MetricBucket[];
  by_submitting_team: MetricBucket[];
  aging_by_status: MetricBucket[];
};
type MetricBucket = { key: string; label: string; count: number; average_age_minutes: number };
type QueueView = { id: number; name: string; search_text: string | null; status_filter: string | null };
type TicketTemplate = { id: number; ticket_number: string; subject: string; client_id: number; product_id?: number; product_module_id?: number; service_id?: number; priority: string };
type ApprovedTemplate = { id: number; name: string; subject: string; client_id?: number; product_id?: number; product_module_id?: number; service_id?: number; priority: string };

const priorities = ["P1", "P2", "P3", "P4"];

export function PreTicketsPage() {
  const { t } = useTranslation();
  const { hasPermission } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = (location.state as { returnTo?: string } | null)?.returnTo;
  const goBack = () => returnTo ? navigate(returnTo) : navigate(-1);
  const client = useQuery({
    queryKey: ["pre-ticket-clients"],
    queryFn: async () =>
      (await api.get<Client[]>("/clients/ticket-options")).data,
    enabled: hasPermission("ticket.pre_ticket.create"),
  });
  const [clientId, setClientId] = useState<number | null>(null);
  const [contact, setContact] = useState<Contact | null>(null);
  const [product, setProduct] = useState<Product | null>(null);
  const [module, setModule] = useState<Module | null>(null);
  const [service, setService] = useState<Service | null>(null);
  const [title, setTitle] = useState("");
  const deferredTitle = useDeferredValue(title.trim());
  const [templateIds, setTemplateIds] = useState<{ product?: number; module?: number; service?: number } | null>(null);
  const [error, setError] = useState("");
  const [action, setAction] = useState<{
    item: PreTicket;
    kind: "needs-information" | "respond" | "reject" | "cancel";
  } | null>(null);
  const [actionText, setActionText] = useState("");
  const [contactOpen, setContactOpen] = useState(false);
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [queueSearch, setQueueSearch] = useState("");
  const [queueStatus, setQueueStatus] = useState("");
  const [queuePage, setQueuePage] = useState(0);
  const [queueViewId, setQueueViewId] = useState("");
  const [queueViewName, setQueueViewName] = useState("");
  const [conversion, setConversion] = useState<{
    item: PreTicket;
    clientId: number | null;
    contact: Contact | null;
    product: Product | null;
    module: Module | null;
    service: Service | null;
  } | null>(null);
  const key = useRef(crypto.randomUUID());
  const cache = useQueryClient();
  const contacts = useQuery({
    queryKey: ["pre-ticket-contacts", clientId],
    enabled: hasPermission("ticket.pre_ticket.create") && Boolean(clientId),
    queryFn: async () =>
      (
        await api.get<Contact[]>("/contacts", {
          params: { client_id: clientId },
        })
      ).data,
  });
  const formSettings = useQuery({ queryKey: ["pre-ticket-form-fields"], queryFn: async () => (await api.get<FormSetting[]>("/system/pre-ticket-form-fields")).data, enabled: hasPermission("ticket.pre_ticket.create") });
  const required = (key: string) => formSettings.data?.find(item => item.field_key === `pre_ticket.${key}`)?.is_required ?? true;
  const contractCatalog = useQuery({ queryKey: ["pre-ticket-contract-catalog", clientId], enabled: hasPermission("ticket.pre_ticket.create") && Boolean(clientId), queryFn: async () => (await api.get<ContractCatalog>("/ticket-contract-catalog", { params: { client_id: clientId, pre_ticket: true } })).data });
  const products = useMemo(() => contractCatalog.data?.products ?? [], [contractCatalog.data?.products]);
  const modules = useMemo(() => contractCatalog.data?.modules.filter(item => item.product_id === product?.id) ?? [], [contractCatalog.data?.modules, product?.id]);
  const services = useMemo(() => (contractCatalog.data?.services ?? []).filter(item => !module || !item.module_ids?.length || item.module_ids.includes(module.id)), [contractCatalog.data?.services, module]);
  const similarMode = deferredTitle.trim().endsWith("*");
  const suggestionTitle = deferredTitle.trim().replace(/\*$/, "").trim();
  const templates = useQuery({ queryKey: ["pre-ticket-keyword-templates", suggestionTitle, clientId], enabled: hasPermission("ticket.pre_ticket.create") && similarMode && suggestionTitle.length >= 3, queryFn: async () => (await api.get<TicketTemplate[]>("/tickets/similar", { params: { subject: suggestionTitle, client_id: clientId || undefined, limit: 5 } })).data });
  const approvedTemplates = useQuery({ queryKey: ["pre-ticket-approved-templates", suggestionTitle, clientId], enabled: hasPermission("ticket.pre_ticket.create") && !similarMode && suggestionTitle.length >= 3, queryFn: async () => (await api.get<ApprovedTemplate[]>("/tickets/templates", { params: { query: suggestionTitle, client_id: clientId || undefined, limit: 5 } })).data });
  useEffect(() => {
    if (!templateIds || !contractCatalog.data) return;
    const nextProduct = products.find(item => item.id === templateIds.product) ?? null;
    if (nextProduct && product?.id !== nextProduct.id) { setProduct(nextProduct); return; }
    const nextModule = modules.find(item => item.id === templateIds.module) ?? null;
    if (nextModule && module?.id !== nextModule.id) { setModule(nextModule); return; }
    const nextService = services.find(item => item.id === templateIds.service) ?? null;
    if (nextService) setService(nextService);
    setTemplateIds(null);
  }, [contractCatalog.data, module?.id, modules, product?.id, products, services, templateIds]);
  const conversionContacts = useQuery({ queryKey: ["pre-ticket-conversion-contacts", conversion?.clientId], enabled: Boolean(conversion?.clientId), queryFn: async () => (await api.get<Contact[]>("/contacts", { params: { client_id: conversion?.clientId } })).data });
  const conversionCatalog = useQuery({ queryKey: ["pre-ticket-conversion-catalog", conversion?.clientId], enabled: Boolean(conversion?.clientId), queryFn: async () => (await api.get<ContractCatalog>("/ticket-contract-catalog", { params: { client_id: conversion?.clientId, pre_ticket: true } })).data });
  const conversionProducts = conversionCatalog.data?.products ?? [];
  const conversionModules = conversionCatalog.data?.modules.filter(item => item.product_id === conversion?.product?.id) ?? [];
  const conversionServices = (conversionCatalog.data?.services ?? []).filter(item => !conversion?.module || !item.module_ids?.length || item.module_ids.includes(conversion.module.id));
  const mine = useQuery({
    queryKey: ["my-pre-tickets"],
    queryFn: async () => (await api.get<PreTicket[]>("/pre-tickets/mine")).data,
    enabled: hasPermission("ticket.pre_ticket.view.own"),
  });
  const queue = useQuery({
    queryKey: ["pre-ticket-queue", queueSearch, queueStatus, queuePage],
    queryFn: async () => {
      const response = await api.get<PreTicket[]>("/pre-tickets/queue", {
        params: {
          search: queueSearch.trim() || undefined,
          status: queueStatus || undefined,
          limit: 10,
          offset: queuePage * 10,
        },
      });
      return {
        items: response.data,
        total: Number(response.headers["x-total-count"] ?? 0),
      };
    },
    enabled: hasPermission("ticket.pre_ticket.queue.view"),
  });
  const metrics = useQuery({
    queryKey: ["pre-ticket-metrics"],
    queryFn: async () =>
      (await api.get<Metrics>("/pre-tickets/metrics/summary")).data,
    enabled: hasPermission("ticket.pre_ticket.report"),
  });
  const queueViews = useQuery({ queryKey: ["pre-ticket-queue-views"], queryFn: async () => (await api.get<QueueView[]>("/pre-tickets/queue/views")).data, enabled: hasPermission("ticket.pre_ticket.queue.view") });
  const metricBreakdowns: Array<[string, MetricBucket[] | undefined]> = [
    [t("preTickets.byStatus"), metrics.data?.aging_by_status],
    [t("preTickets.byPriority"), metrics.data?.by_priority],
    [t("preTickets.byClient"), metrics.data?.by_client],
    [t("preTickets.byProduct"), metrics.data?.by_product],
    [t("preTickets.bySubmittingTeam"), metrics.data?.by_submitting_team],
  ];
  const submit = useMutation({
    mutationFn: async (form: HTMLFormElement) => {
      const values = new FormData(form);
      return (
        await api.post<PreTicket>("/pre-tickets", {
          client_id: clientId,
          requester_contact_id: contact?.id,
          product_id: product?.id,
          product_module_id: module?.id,
          service_id: service?.id,
          proposed_priority: values.get("priority"),
          title: String(values.get("title") ?? "").trim().replace(/\*$/, "").trim(),
          idempotency_key: key.current,
        })
      ).data;
    },
    onSuccess: async () => {
      key.current = crypto.randomUUID();
      setClientId(null);
      setContact(null);
      setProduct(null);
      setModule(null);
      setService(null);
      setTitle("");
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["my-pre-tickets"] }),
        cache.invalidateQueries({ queryKey: ["pre-ticket-action-count"] }),
      ]);
    },
    onError: () =>
      setError(
        "Unable to submit the Pre-Ticket. Check that the feature is enabled and your selections are valid.",
      ),
  });
  const confirm = useMutation({
    mutationFn: async (item: PreTicket) =>
      (
        await api.post<PreTicket>(`/pre-tickets/${item.id}/confirm`, {
          expected_version: item.version,
          conversion_idempotency_key: crypto.randomUUID(),
        })
      ).data,
    onSuccess: () =>
      Promise.all([
        cache.invalidateQueries({ queryKey: ["my-pre-tickets"] }),
        cache.invalidateQueries({ queryKey: ["pre-ticket-action-count"] }),
      ]),
  });
  const claim = useMutation({
    mutationFn: async (item: PreTicket) =>
      (
        await api.post<PreTicket>(`/pre-tickets/${item.id}/claim`, {
          expected_version: item.version,
        })
      ).data,
    onSuccess: () =>
      Promise.all([
        cache.invalidateQueries({ queryKey: ["pre-ticket-queue"] }),
        cache.invalidateQueries({ queryKey: ["pre-ticket-action-count"] }),
      ]),
  });
  const convert = useMutation({
    mutationFn: async (values: NonNullable<typeof conversion>) =>
      (
        await api.post<PreTicket>(`/pre-tickets/${values.item.id}/convert`, {
          expected_version: values.item.version,
          conversion_idempotency_key: crypto.randomUUID(),
          client_id: values.clientId,
          requester_contact_id: values.contact?.id,
          product_id: values.product?.id,
          product_module_id: values.module?.id,
          service_id: values.service?.id,
        })
      ).data,
    onSuccess: async () => {
      setConversion(null);
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["pre-ticket-queue"] }),
        cache.invalidateQueries({ queryKey: ["pre-ticket-action-count"] }),
      ]);
    },
  });
  const openConversion = (item: PreTicket) => setConversion({
    item,
    clientId: item.client_id ?? null,
    contact: item.requester_contact_id ? { id: item.requester_contact_id, full_name: `#${item.requester_contact_id}`, is_active: true } : null,
    product: item.product_id ? { id: item.product_id, name: `#${item.product_id}`, is_active: true } : null,
    module: item.product_module_id ? { id: item.product_module_id, name: `#${item.product_module_id}`, product_id: item.product_id ?? 0 } : null,
    service: item.service_id ? { id: item.service_id, name: `#${item.service_id}` } : null,
  });
  const applyAction = useMutation({
    mutationFn: async () => {
      if (!action) return;
      const payload =
        action.kind === "respond"
          ? { expected_version: action.item.version, response: actionText }
          : { expected_version: action.item.version, reason: actionText };
      return (
        await api.post<PreTicket>(
          `/pre-tickets/${action.item.id}/${action.kind}`,
          payload,
        )
      ).data;
    },
    onSuccess: async () => {
      setAction(null);
      setActionText("");
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["my-pre-tickets"] }),
        cache.invalidateQueries({ queryKey: ["pre-ticket-queue"] }),
        cache.invalidateQueries({ queryKey: ["pre-ticket-action-count"] }),
      ]);
    },
  });
  const createContact = useMutation({
    mutationFn: async () =>
      (
        await api.post<Contact>("/contacts", {
          client_id: clientId,
          full_name: contactName.trim(),
          email: contactEmail.trim() || null,
          phone_number: contactPhone.trim() || null,
        })
      ).data,
    onSuccess: async (created) => {
      setContact(created);
      setContactOpen(false);
      setContactName("");
      setContactEmail("");
      setContactPhone("");
      await cache.invalidateQueries({
        queryKey: ["pre-ticket-contacts", clientId],
      });
    },
    onError: () =>
      setError(
        "Unable to add the contact. Check your permission and contact details.",
      ),
  });
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    if ((required("client_id") && !clientId) || (required("requester_contact_id") && !contact) || (required("product_id") && !product) || (required("product_module_id") && !module) || (required("service_id") && !service)) {
      setError(t("preTickets.requiredFields"));
      return;
    }
    submit.mutate(event.currentTarget);
  };
  const saveQueueView = useMutation({ mutationFn: async () => (await api.post<QueueView>("/pre-tickets/queue/views", { name: queueViewName.trim(), search_text: queueSearch.trim() || null, status_filter: queueStatus || null })).data, onSuccess: async () => { setQueueViewName(""); await cache.invalidateQueries({ queryKey: ["pre-ticket-queue-views"] }); } });
  const deleteQueueView = useMutation({ mutationFn: async () => { if (queueViewId) await api.delete(`/pre-tickets/queue/views/${queueViewId}`); }, onSuccess: async () => { setQueueViewId(""); await cache.invalidateQueries({ queryKey: ["pre-ticket-queue-views"] }); } });
  const queueRows = queue.data?.items ?? [];
  const queuePageSize = 10;
  const queuePageCount = Math.max(
    1,
    Math.ceil((queue.data?.total ?? 0) / queuePageSize),
  );
  const visibleQueueRows = queueRows;
  const exportQueue = async () => {
    const response = await api.get("/pre-tickets/queue/export", {
      params: { search: queueSearch.trim() || undefined, status: queueStatus || undefined },
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "pre-ticket-queue.csv";
    link.click();
    URL.revokeObjectURL(url);
  };
  return (
    <Stack spacing={3}>
      <Box>
        <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 1 }}>
          {t("common.back")}
        </Button>
        <Typography variant="h4">{t("preTickets.title")}</Typography>
        <Typography color="text.secondary">{t("preTickets.help")}</Typography>
      </Box>
      {hasPermission("ticket.pre_ticket.create") && (
        <Paper component="form" onSubmit={onSubmit} sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Typography variant="h6">{t("preTickets.new")}</Typography>
            {error && <Alert severity="error">{error}</Alert>}
            <Autocomplete
              options={client.data ?? []}
              value={(client.data ?? []).find((x) => x.id === clientId) ?? null}
              onChange={(_, value) => {
                setClientId(value?.id ?? null);
                setContact(null);
                setProduct(null);
                setModule(null);
                setService(null);
              }}
              getOptionLabel={(x) =>
                `${x.name} — ${t("createTicket.ticketCount", {
                  count: x.ticket_count,
                })}${x.is_active ? "" : ` — ${t("createTicket.inactive")}`}`
              }
              getOptionDisabled={(x) =>
                !x.is_active || !x.ticket_creation_allowed
              }
              renderOption={(props, option) => (
                <li
                  {...props}
                  style={{
                    ...props.style,
                    color: option.is_active ? undefined : "#d32f2f",
                  }}
                >
                  {option.name} —{" "}
                  {t("createTicket.ticketCount", {
                    count: option.ticket_count,
                  })}
                  {!option.is_active &&
                    ` — ${t("createTicket.inactive")}`}
                </li>
              )}
              renderInput={(params) => (
                <TextField {...params} label={t("preTickets.client")} required={required("client_id")} />
              )}
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <Autocomplete
                sx={{ flex: 1 }}
                disabled={!clientId}
                options={(contacts.data ?? []).filter((x) => x.is_active)}
                value={contact}
                onChange={(_, value) => setContact(value)}
                getOptionLabel={(x) => x.full_name}
                renderInput={(params) => (
                  <TextField {...params} label={t("preTickets.caller")} required={required("requester_contact_id")} />
                )}
              />
              {hasPermission("contact.manage") && (
                <Button
                  disabled={!clientId}
                  onClick={() => setContactOpen(true)}
                >
                  {t("preTickets.addContact")}
                </Button>
              )}
            </Stack>
            <Autocomplete
              disabled={!clientId}
              options={products}
              value={product}
              onChange={(_, value) => { setProduct(value); setModule(null); }}
              getOptionLabel={(x) => x.covered === false ? `${x.name} — ${t("preTickets.uncovered")}` : x.name}
              renderInput={(params) => (
                <TextField {...params} label={t("preTickets.product")} required={required("product_id")} />
              )}
            />
            {product?.covered === false && (
              <Alert severity="warning">{t("preTickets.uncoveredApprovalOnConversion")}</Alert>
            )}
            <Autocomplete disabled={!product} options={modules} value={module} onChange={(_,value)=>{setModule(value);setService(null)}} getOptionLabel={x=>x.name} renderInput={params=><TextField {...params} label={t("preTickets.module")} required={required("product_module_id")} />} />
            <Autocomplete disabled={!clientId} options={services} value={service} onChange={(_,value)=>setService(value)} getOptionLabel={x=>x.name} renderInput={params=><TextField {...params} label={t("preTickets.service")} required={required("service_id")} />} />
            <TextField
              select
              name="priority"
              label={t("preTickets.proposedPriority")}
              defaultValue="P3"
              required
            >
              {priorities.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="title"
              label={t("preTickets.ticketTitle")}
              inputProps={{ minLength: 10, maxLength: 300 }}
              helperText={t("preTickets.ticketTitleHelp")}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
            />
            {similarMode && templates.isFetching && <Typography variant="body2" color="text.secondary">{t("createTicket.checkingSimilar")}</Typography>}
            {!similarMode && !!approvedTemplates.data?.length && <Alert severity="success"><Typography fontWeight={700}>{t("preTickets.approvedTemplates", { defaultValue: "Approved ticket templates" })}</Typography><Stack alignItems="flex-start">{approvedTemplates.data.map(item => <Button key={item.id} size="small" onClick={() => { setTitle(item.subject); if (item.client_id) setClientId(item.client_id); setProduct(null); setModule(null); setService(null); setTemplateIds({ product: item.product_id, module: item.product_module_id, service: item.service_id }); }}>{item.name} — {item.subject}</Button>)}</Stack></Alert>}
            {similarMode && !!templates.data?.length && <Alert severity="info">
              <Typography fontWeight={700}>{t("preTickets.keywordTemplates", { defaultValue: "Suggested ticket templates" })}</Typography>
              <Stack alignItems="flex-start">
                {templates.data.map(item => <Button key={item.id} size="small" onClick={() => { setTitle(item.subject); setClientId(item.client_id); setProduct(null); setModule(null); setService(null); setTemplateIds({ product: item.product_id, module: item.product_module_id, service: item.service_id }); }}>{item.ticket_number} — {item.subject}</Button>)}
              </Stack>
            </Alert>}
            <Button
              type="submit"
              variant="contained"
              disabled={submit.isPending}
            >
              {submit.isPending ? t("preTickets.submitting") : t("preTickets.submit")}
            </Button>
          </Stack>
        </Paper>
      )}
      {hasPermission("ticket.pre_ticket.report") && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6">{t("preTickets.metrics")}</Typography>
          {metrics.isLoading ? (
            <CircularProgress size={22} />
          ) : (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={4}>
                <Typography>{t("preTickets.total")}: {metrics.data?.total ?? 0}</Typography>
                <Typography>{t("preTickets.claimTime")}: {metrics.data?.average_minutes_to_claim == null ? "—" : `${metrics.data.average_minutes_to_claim} min`}</Typography>
                <Typography>{t("preTickets.claimToTicketTime")}: {metrics.data?.average_minutes_claim_to_ticket == null ? "—" : `${metrics.data.average_minutes_claim_to_ticket} min`}</Typography>
                <Typography>{t("preTickets.ticketTime")}: {metrics.data?.average_minutes_to_ticket == null ? "—" : `${metrics.data.average_minutes_to_ticket} min`}</Typography>
              </Stack>
              <Stack direction={{ xs: "column", lg: "row" }} spacing={2} alignItems="flex-start" flexWrap="wrap">
                {metricBreakdowns.map(([label, rows]) => (
                  <Box key={label} sx={{ minWidth: 190 }}>
                    <Typography variant="subtitle2">{label}</Typography>
                    {(rows ?? []).map(row => <Typography variant="body2" key={row.key}>{row.label}: {row.count} · {t("preTickets.averageAge", { minutes: row.average_age_minutes })}</Typography>)}
                  </Box>
                ))}
              </Stack>
            </Stack>
          )}
        </Paper>
      )}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          {t("preTickets.myTickets")}
        </Typography>
        {mine.isLoading ? (
          <CircularProgress />
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("preTickets.number")}</TableCell>
                <TableCell>{t("preTickets.ticketTitle")}</TableCell>
                <TableCell>{t("preTickets.priority")}</TableCell>
                <TableCell>{t("preTickets.status")}</TableCell>
                <TableCell>{t("preTickets.submitted")}</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {(mine.data ?? []).map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.pre_ticket_number}</TableCell>
                  <TableCell>
                    {item.title}
                    {item.information_request && (
                      <Typography
                        variant="caption"
                        display="block"
                        color="warning.main"
                      >
                          {t("preTickets.informationRequested", { reason: item.information_request })}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip label={item.proposed_priority} size="small" />
                  </TableCell>
                  <TableCell>{item.status}</TableCell>
                  <TableCell>
                    {new Date(item.submitted_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {item.resulting_ticket_id ? (
                      <Button
                        component={Link}
                        to={`/tickets/${item.resulting_ticket_id}`}
                      >
                          {t("preTickets.openTicket")}
                      </Button>
                    ) : item.status === "NEEDS_INFORMATION" ? (
                      <Button
                        onClick={() => setAction({ item, kind: "respond" })}
                      >
                          {t("preTickets.respond")}
                      </Button>
                    ) : hasPermission("ticket.pre_ticket.fast_convert.self") &&
                      item.status === "SUBMITTED" ? (
                      <Button
                        onClick={() => confirm.mutate(item)}
                        disabled={confirm.isPending}
                      >
                          {t("preTickets.convert")}
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
      {hasPermission("ticket.pre_ticket.queue.view") && (
        <Paper sx={{ p: 2 }}>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ mb: 2 }}
          >
            <Typography variant="h6">{t("preTickets.queue")}</Typography>
            {hasPermission("ticket.pre_ticket.report") && (
              <Button onClick={exportQueue} disabled={!queueRows.length}>
                {t("preTickets.exportCsv")}
              </Button>
            )}
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 1 }}>
            <TextField select size="small" label={t("preTickets.savedViews")} value={queueViewId} onChange={(event) => { const view = queueViews.data?.find(item => item.id === Number(event.target.value)); setQueueViewId(event.target.value); if (view) { setQueueSearch(view.search_text ?? ""); setQueueStatus(view.status_filter ?? ""); setQueuePage(0); } }} sx={{ minWidth: 220 }}>
              <MenuItem value="">{t("preTickets.selectView")}</MenuItem>
              {queueViews.data?.map(view => <MenuItem key={view.id} value={view.id}>{view.name}</MenuItem>)}
            </TextField>
            <TextField size="small" label={t("preTickets.viewName")} value={queueViewName} onChange={event => setQueueViewName(event.target.value)} />
            <Button onClick={() => saveQueueView.mutate()} disabled={queueViewName.trim().length < 2 || saveQueueView.isPending}>{t("preTickets.saveView")}</Button>
            <Button color="error" onClick={() => deleteQueueView.mutate()} disabled={!queueViewId || deleteQueueView.isPending}>{t("preTickets.deleteView")}</Button>
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
          <TextField
            fullWidth
            size="small"
            label={t("preTickets.queueSearch")}
            value={queueSearch}
            onChange={(event) => {
              setQueueSearch(event.target.value);
              setQueuePage(0);
            }}
          />
          <TextField select size="small" label={t("preTickets.status")} value={queueStatus} onChange={(event) => { setQueueStatus(event.target.value); setQueuePage(0); }} sx={{ minWidth: 190 }}>
            <MenuItem value="">{t("preTickets.allStatuses")}</MenuItem>
            {['SUBMITTED', 'CLAIMED', 'NEEDS_INFORMATION', 'REJECTED', 'CANCELLED', 'CONVERTED'].map(status => <MenuItem key={status} value={status}>{status.replaceAll('_', ' ')}</MenuItem>)}
          </TextField>
          </Stack>
          {queue.isLoading ? (
            <CircularProgress />
          ) : (
            <>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("preTickets.number")}</TableCell>
                    <TableCell>{t("preTickets.ticketTitle")}</TableCell>
                    <TableCell>{t("preTickets.priority")}</TableCell>
                    <TableCell>{t("preTickets.status")}</TableCell>
                    <TableCell>{t("preTickets.age")}</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {visibleQueueRows.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>{item.pre_ticket_number}</TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <span>{item.title}</span>
                          {item.source_provider && <Chip size="small" color={item.request_kind === "CALL_REQUEST" ? "warning" : "info"} label={item.request_kind === "CALL_REQUEST" ? t("preTickets.callRequest") : t("preTickets.ticketRequest")} />}
                        </Stack>
                        {(item.external_caller_name || item.external_caller_number) && <Typography variant="caption" color="text.secondary">{[item.external_caller_name, item.external_caller_number].filter(Boolean).join(" · ")}</Typography>}
                      </TableCell>
                      <TableCell>
                        <Chip label={item.proposed_priority} size="small" />
                      </TableCell>
                      <TableCell>{item.status}</TableCell>
                      <TableCell>
                        {new Date(item.submitted_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {item.resulting_ticket_id ? (
                          <Button
                            component={Link}
                            to={`/tickets/${item.resulting_ticket_id}`}
                          >
                            {t("preTickets.openTicket")}
                          </Button>
                        ) : (hasPermission("ticket.pre_ticket.queue.process") ||
                          hasPermission("ticket.pre_ticket.convert_assign")) &&
                          (item.status === "SUBMITTED" ||
                            item.status === "CLAIMED") ? (
                          <Stack direction="row" flexWrap="wrap">
                            {item.status === "SUBMITTED" && hasPermission("ticket.pre_ticket.queue.process") && (
                              <Button
                                onClick={() => claim.mutate(item)}
                                disabled={claim.isPending}
                              >
                                {t("preTickets.claim")}
                              </Button>
                            )}
                            {hasPermission("ticket.pre_ticket.convert_assign") && (
                              <Button
                                onClick={() => openConversion(item)}
                                disabled={convert.isPending}
                              >
                                {t("preTickets.convert")}
                              </Button>
                            )}
                            {item.status === "CLAIMED" && hasPermission("ticket.pre_ticket.queue.process") && (
                              <Button
                                onClick={() =>
                                  setAction({ item, kind: "needs-information" })
                                }
                              >
                                {t("preTickets.requestInformation")}
                              </Button>
                            )}
                            {hasPermission("ticket.pre_ticket.queue.process") && (
                              <Button
                                onClick={() =>
                                  setAction({ item, kind: "reject" })
                                }
                              >
                                {t("preTickets.reject")}
                              </Button>
                            )}
                            {hasPermission("ticket.pre_ticket.queue.process") && (
                              <Button
                                onClick={() =>
                                  setAction({ item, kind: "cancel" })
                                }
                              >
                                {t("preTickets.cancel")}
                              </Button>
                            )}
                          </Stack>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                justifyContent="flex-end"
                sx={{ mt: 2 }}
              >
                <Typography variant="body2">
                  {t("preTickets.results", {
                    count: queue.data?.total ?? 0,
                    page: queuePage + 1,
                    pages: queuePageCount,
                  })}
                </Typography>
                <Button
                  size="small"
                  disabled={queuePage === 0}
                  onClick={() => setQueuePage((value) => value - 1)}
                >
                  {t("preTickets.previous")}
                </Button>
                <Button
                  size="small"
                  disabled={queuePage + 1 >= queuePageCount}
                  onClick={() => setQueuePage((value) => value + 1)}
                >
                  {t("preTickets.next")}
                </Button>
              </Stack>
            </>
          )}
        </Paper>
      )}
      <Dialog open={Boolean(conversion)} onClose={() => setConversion(null)} fullWidth maxWidth="sm">
        <DialogTitle>{t("preTickets.completeAndConvert")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Alert severity="info">{t("preTickets.completeContextHelp")}</Alert>
            <Autocomplete
              options={(client.data ?? []).filter(item => item.is_active && item.ticket_creation_allowed)}
              value={(client.data ?? []).find(item => item.id === conversion?.clientId) ?? null}
              disabled={Boolean(conversion?.item.client_id)}
              onChange={(_, value) => setConversion(current => current ? { ...current, clientId: value?.id ?? null, contact: null, product: null, module: null, service: null } : null)}
              getOptionLabel={item => item.name}
              renderInput={params => <TextField {...params} required label={t("preTickets.client")} />}
            />
            <Autocomplete
              options={(conversionContacts.data ?? []).filter(item => item.is_active)}
              value={(conversionContacts.data ?? []).find(item => item.id === conversion?.contact?.id) ?? conversion?.contact ?? null}
              disabled={!conversion?.clientId || Boolean(conversion?.item.requester_contact_id)}
              onChange={(_, value) => setConversion(current => current ? { ...current, contact: value } : null)}
              getOptionLabel={item => item.full_name}
              renderInput={params => <TextField {...params} label={t("preTickets.caller")} />}
            />
            <Autocomplete
              options={conversionProducts}
              value={conversionProducts.find(item => item.id === conversion?.product?.id) ?? conversion?.product ?? null}
              disabled={!conversion?.clientId || Boolean(conversion?.item.product_id)}
              onChange={(_, value) => setConversion(current => current ? { ...current, product: value, module: null, service: null } : null)}
              getOptionLabel={item => item.name}
              renderInput={params => <TextField {...params} label={t("preTickets.product")} />}
            />
            <Autocomplete
              options={conversionModules}
              value={conversionModules.find(item => item.id === conversion?.module?.id) ?? conversion?.module ?? null}
              disabled={!conversion?.product || Boolean(conversion?.item.product_module_id)}
              onChange={(_, value) => setConversion(current => current ? { ...current, module: value, service: null } : null)}
              getOptionLabel={item => item.name}
              renderInput={params => <TextField {...params} label={t("preTickets.module")} />}
            />
            <Autocomplete
              options={conversionServices}
              value={conversionServices.find(item => item.id === conversion?.service?.id) ?? conversion?.service ?? null}
              disabled={!conversion?.clientId || Boolean(conversion?.item.service_id)}
              onChange={(_, value) => setConversion(current => current ? { ...current, service: value } : null)}
              getOptionLabel={item => item.name}
              renderInput={params => <TextField {...params} label={t("preTickets.service")} />}
            />
            {convert.isError && <Alert severity="error">{t("preTickets.convertFailed")}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConversion(null)}>{t("preTickets.back")}</Button>
          <Button variant="contained" disabled={!conversion?.clientId || convert.isPending} onClick={() => conversion && convert.mutate(conversion)}>{t("preTickets.convert")}</Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(action)} onClose={() => setAction(null)} fullWidth>
        <DialogTitle>
          {action?.kind === "respond"
            ? t("preTickets.respondTitle")
            : action?.kind === "needs-information"
              ? t("preTickets.requestInformationTitle")
              : action?.kind === "reject"
                ? t("preTickets.rejectTitle")
                : t("preTickets.cancelTitle")}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            multiline
            minRows={3}
            fullWidth
            margin="dense"
            label={action?.kind === "respond" ? t("preTickets.response") : t("preTickets.reason")}
            value={actionText}
            onChange={(event) => setActionText(event.target.value)}
            helperText={t("preTickets.actionHelp")}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAction(null)}>{t("preTickets.back")}</Button>
          <Button
            variant="contained"
            disabled={actionText.trim().length < 5 || applyAction.isPending}
            onClick={() => applyAction.mutate()}
          >
            {t("preTickets.save")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={contactOpen}
        onClose={() => setContactOpen(false)}
        fullWidth
      >
        <DialogTitle>{t("preTickets.addContact")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField
              autoFocus
              required
              label={t("preTickets.fullName")}
              value={contactName}
              onChange={(event) => setContactName(event.target.value)}
            />
            <TextField
              label={t("preTickets.email")}
              type="email"
              value={contactEmail}
              onChange={(event) => setContactEmail(event.target.value)}
            />
            <TextField
              label={t("preTickets.phone")}
              value={contactPhone}
              onChange={(event) => setContactPhone(event.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setContactOpen(false)}>{t("preTickets.back")}</Button>
          <Button
            variant="contained"
            disabled={contactName.trim().length < 2 || createContact.isPending}
            onClick={() => createContact.mutate()}
          >
            {t("preTickets.addContact")}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
