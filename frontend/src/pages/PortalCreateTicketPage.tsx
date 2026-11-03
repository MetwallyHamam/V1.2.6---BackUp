import { ArrowBack, CheckCircle } from "@mui/icons-material";
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import {
  FormEvent,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { SearchableDropdown } from "../components/SearchableDropdown";
import { priorityOptions } from "../utils/priority";
import { getLocalizedName } from "../i18n/localizedMasterData";

type CatalogItem = {
  id: number;
  name: string;
  name_ar?: string | null;
  covered: boolean;
};
type ServiceItem = CatalogItem & { module_ids: number[] };
type Catalog = {
  clients: Array<{ id: number; code: string; name: string }>;
  visibility_mode: string;
  products: CatalogItem[];
  modules: Array<CatalogItem & { product_id: number }>;
  services: ServiceItem[];
};
type Candidate = {
  contract_id: number;
  contract_number: string;
  contract_name: string;
  end_date: string;
  status: string;
  reason: string;
};
type TicketType = {
  id: number;
  code: string;
  name: string;
  name_ar?: string | null;
};
type Contact = {
  id: number;
  full_name: string;
  phone_number?: string | null;
  email?: string | null;
  job_title?: string | null;
};
type Payload = Record<string, unknown>;

export function isMosaicMode(method: string | null) {
  return method?.toLocaleLowerCase() === "mosaic";
}
export function servicesForModule(services: ServiceItem[], moduleId: string) {
  return moduleId
    ? services.filter((item) => item.module_ids.includes(Number(moduleId)))
    : [];
}

function SelectionCards({
  title,
  items,
  selectedId,
  empty,
  onSelect,
}: {
  title: string;
  items: CatalogItem[];
  selectedId: string;
  empty: string;
  onSelect: (value: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  return (
    <Box
      component="section"
      aria-labelledby={`mosaic-${title.toLocaleLowerCase()}-title`}
    >
      <Typography
        id={`mosaic-${title.toLocaleLowerCase()}-title`}
        variant="h5"
        fontWeight={850}
        mb={2}
      >
        {t("portalCreate.choose", { item: title })}
      </Typography>
      {!items.length && <Alert severity="info">{empty}</Alert>}
      <Grid container spacing={2}>
        {items.map((item) => {
          const selected = selectedId === String(item.id);
          return (
            <Grid key={item.id} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card
                variant="outlined"
                sx={{
                  height: "100%",
                  borderWidth: selected ? 2 : 1,
                  borderColor: selected ? "primary.main" : "divider",
                }}
              >
                <CardActionArea
                  aria-pressed={selected}
                  onClick={() => onSelect(String(item.id))}
                  sx={{
                    height: "100%",
                    alignItems: "stretch",
                    "&:focus-visible": {
                      outline: "3px solid",
                      outlineColor: "primary.main",
                      outlineOffset: 2,
                    },
                  }}
                >
                  <CardContent
                    sx={{
                      minHeight: 126,
                      display: "flex",
                      flexDirection: "column",
                      gap: 1,
                    }}
                  >
                    <Stack direction="row" gap={1} alignItems="flex-start">
                      <Typography
                        fontWeight={800}
                        flex={1}
                        sx={{ overflowWrap: "anywhere" }}
                      >
                        {getLocalizedName(item, language)}
                      </Typography>
                      {selected && (
                        <CheckCircle
                          color="primary"
                          aria-label={t("portalCreate.selected")}
                        />
                      )}
                    </Stack>
                    <Chip
                      size="small"
                      sx={{ alignSelf: "flex-start" }}
                      color={item.covered ? "success" : "warning"}
                      variant={item.covered ? "filled" : "outlined"}
                      label={t(
                        item.covered
                          ? "portalCreate.included"
                          : "portalCreate.approvalRequired",
                      )}
                    />
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
}

export function PortalCreateTicketPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const localized = (
    item: { name: string; name_ar?: string | null } | undefined,
  ) => getLocalizedName(item, language);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const mosaic = isMosaicMode(searchParams.get("method"));
  const locked = useRef(false);
  const key = useRef(crypto.randomUUID());
  const creationIdempotencyKey = useRef(crypto.randomUUID());
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const canManageCallers = hasPermission("portal.caller.manage");
  const [error, setError] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [clientId, setClientId] = useState(searchParams.get("client") ?? "");
  const [catalogClientId, setCatalogClientId] = useState("");
  const [productId, setProductId] = useState(searchParams.get("product") ?? "");
  const [moduleId, setModuleId] = useState(searchParams.get("module") ?? "");
  const [serviceId, setServiceId] = useState(searchParams.get("service") ?? "");
  const [contractId, setContractId] = useState("");
  const [ticketTypeId, setTicketTypeId] = useState("");
  const [priority, setPriority] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [changeKind, setChangeKind] = useState("UPDATE_EXISTING_FEATURE");
  const [changePurpose, setChangePurpose] = useState("");
  const [changeDescription, setChangeDescription] = useState("");
  const [changeBusinessImpact, setChangeBusinessImpact] = useState("");
  const [changeExpectedResult, setChangeExpectedResult] = useState("");
  const [changeRequiredPermissions, setChangeRequiredPermissions] =
    useState("");
  const [reviewing, setReviewing] = useState(false);
  const [callerId, setCallerId] = useState("");
  const [callerDialog, setCallerDialog] = useState(false);
  const [callerError, setCallerError] = useState("");
  const [pending, setPending] = useState<Payload | null>(null);
  const [justification, setJustification] = useState("");
  const catalog = useQuery({
    queryKey: ["portal-catalog", catalogClientId],
    queryFn: async () =>
      (
        await api.get<Catalog>("/portal/catalog", {
          params: {
            client_id: catalogClientId ? Number(catalogClientId) : undefined,
          },
        })
      ).data,
  });
  const types = useQuery({
    queryKey: ["ticket-types"],
    queryFn: async () =>
      (await api.get<TicketType[]>("/ticket-types")).data.filter((item) =>
        ["INCIDENT", "SERVICE_REQUEST", "CHANGE_REQUEST"].includes(item.code),
      ),
  });
  const callers = useQuery({
    queryKey: ["portal-callers", clientId],
    queryFn: async () =>
      (
        await api.get<Contact[]>("/portal/callers", {
          params: { client_id: Number(clientId) },
        })
      ).data,
    enabled: canManageCallers && Boolean(clientId),
  });
  const createCaller = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post<Contact>("/portal/callers", payload)).data,
    onSuccess: async (contact) => {
      setCallerId(String(contact.id));
      setCallerDialog(false);
      setCallerError("");
      await queryClient.invalidateQueries({
        queryKey: ["portal-callers", clientId],
      });
    },
    onError: (caught) =>
      setCallerError(
        axios.isAxiosError(caught)
          ? (caught.response?.data?.error?.message ??
              t("portalCreate.callerCreateFailed"))
          : t("portalCreate.callerCreateFailed"),
      ),
  });
  useLayoutEffect(() => {
    if (!clientId && catalog.data?.clients.length === 1)
      setClientId(String(catalog.data.clients[0].id));
  }, [catalog.data?.clients, clientId]);
  useEffect(() => {
    if (
      clientId &&
      (catalog.data?.clients.length ?? 0) > 1 &&
      catalogClientId !== clientId
    )
      setCatalogClientId(clientId);
  }, [catalog.data?.clients.length, catalogClientId, clientId]);
  useEffect(() => {
    if (!mosaic) return;
    setClientId(
      searchParams.get("client") ??
        (catalog.data?.clients.length === 1
          ? String(catalog.data.clients[0].id)
          : ""),
    );
    setProductId(searchParams.get("product") ?? "");
    setModuleId(searchParams.get("module") ?? "");
    setServiceId(searchParams.get("service") ?? "");
  }, [catalog.data?.clients, mosaic, searchParams]); // Browser Back/Forward restores the governed path.
  useEffect(() => {
    if (!catalog.data) return;
    if (
      productId &&
      !catalog.data.products.some((item) => item.id === Number(productId))
    ) {
      setProductId("");
      setModuleId("");
      setServiceId("");
    }
  }, [catalog.data, productId]);
  const modules = useMemo(
    () =>
      catalog.data?.modules.filter(
        (item) => item.product_id === Number(productId),
      ) ?? [],
    [catalog.data?.modules, productId],
  );
  const services = useMemo(
    () => servicesForModule(catalog.data?.services ?? [], moduleId),
    [catalog.data?.services, moduleId],
  );
  const selectedService = useMemo(
    () =>
      catalog.data?.services.find((item) => item.id === Number(serviceId)),
    [catalog.data?.services, serviceId],
  );
  const servicesForProduct = useMemo(() => {
    const productModuleIds = new Set(modules.map((item) => item.id));
    return (catalog.data?.services ?? []).filter(
      (item) =>
        item.module_ids.length === 0 ||
        item.module_ids.some((moduleIdValue) => productModuleIds.has(moduleIdValue)),
    );
  }, [catalog.data?.services, modules]);
  const compatibleModules = useMemo(
    () =>
      selectedService?.module_ids.length
        ? modules.filter((item) => selectedService.module_ids.includes(item.id))
        : modules,
    [modules, selectedService],
  );
  const serviceRequiresModule = Boolean(selectedService?.module_ids.length);
  useEffect(() => {
    if (moduleId && !modules.some((item) => item.id === Number(moduleId))) {
      setModuleId("");
      setServiceId("");
    }
  }, [moduleId, modules]);
  useEffect(() => {
    if (
      serviceId &&
      !catalog.data?.services.some((item) => item.id === Number(serviceId))
    )
      setServiceId("");
  }, [catalog.data?.services, serviceId]);
  useEffect(() => {
    if (!serviceRequiresModule || moduleId) return;
    if (compatibleModules.length === 1) setModuleId(String(compatibleModules[0].id));
  }, [compatibleModules, moduleId, serviceRequiresModule]);
  const candidates = useQuery({
    queryKey: ["portal-candidates", clientId, productId, moduleId, serviceId],
    enabled: Boolean(clientId && productId && serviceId),
    queryFn: async () =>
      (
        await api.get<Candidate[]>("/entitlements/candidates", {
          params: {
            client_id: Number(clientId),
            product_id: Number(productId),
            product_module_id: moduleId ? Number(moduleId) : undefined,
            service_id: Number(serviceId),
          },
        })
      ).data,
  });
  const covered = useMemo(
    () => (candidates.data ?? []).filter((item) => item.status === "COVERED"),
    [candidates.data],
  );
  useEffect(
    () =>
      setContractId(covered.length === 1 ? String(covered[0].contract_id) : ""),
    [covered],
  );
  const selectionComplete = Boolean(clientId && productId && moduleId && serviceId);

  function mosaicUrl(next: {
    client?: string;
    product?: string;
    module?: string;
    service?: string;
  }) {
    const params = new URLSearchParams(searchParams);
    params.set("method", "mosaic");
    if (clientId) params.set("client", clientId);
    for (const [name, value] of Object.entries(next)) {
      if (value) params.set(name, value);
      else params.delete(name);
    }
    setSearchParams(params);
  }
  function changeClient(value: string) {
    setReviewing(false);
    setClientId(value);
    setCallerId("");
    setCatalogClientId((catalog.data?.clients.length ?? 0) > 1 ? value : "");
    setProductId("");
    setModuleId("");
    setServiceId("");
    setContractId("");
    if (mosaic)
      mosaicUrl({ client: value, product: "", module: "", service: "" });
  }
  function chooseProduct(value: string) {
    setReviewing(false);
    setProductId(value);
    setModuleId("");
    setServiceId("");
    setContractId("");
    mosaicUrl({ product: value, module: "", service: "" });
  }
  function chooseModule(value: string) {
    setReviewing(false);
    setModuleId(value);
    setServiceId("");
    setContractId("");
    mosaicUrl({ module: value, service: "" });
  }
  function chooseService(value: string) {
    setReviewing(false);
    setServiceId(value);
    setContractId("");
    mosaicUrl({ service: value });
  }
  function payload(): Payload {
    const isChangeRequest =
      types.data?.find((item) => item.id === Number(ticketTypeId))?.code ===
      "CHANGE_REQUEST";
    return {
      creation_method: mosaic ? "MOSAIC" : "PORTAL",
      client_id: Number(clientId),
      requester_contact_id:
        canManageCallers && callerId ? Number(callerId) : null,
      contract_id: contractId ? Number(contractId) : null,
      ticket_type_id: Number(ticketTypeId),
      product_id: Number(productId),
      product_module_id: moduleId ? Number(moduleId) : null,
      service_id: Number(serviceId),
      priority,
      impact: "MEDIUM",
      urgency: "MEDIUM",
      subject,
      description,
      change_request: isChangeRequest
        ? {
            request_kind: changeKind,
            purpose: changePurpose.trim(),
            detailed_description: changeDescription.trim(),
            business_impact: changeBusinessImpact.trim(),
            expected_result: changeExpectedResult.trim(),
            required_permissions: changeRequiredPermissions.trim() || null,
            requested_priority:
              priority === "P1"
                ? "CRITICAL"
                : priority === "P2"
                  ? "HIGH"
                  : priority === "P3"
                    ? "MEDIUM"
                    : "LOW",
          }
        : null,
    };
  }
  function submitCaller(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    createCaller.mutate({
      client_id: Number(clientId),
      full_name: String(values.full_name).trim(),
      phone_number: values.phone_number || null,
      email: values.email || null,
      job_title: values.job_title || null,
      is_active: true,
    });
  }
  async function send(body: Payload, approval = false) {
    if (locked.current) return;
    locked.current = true;
    setSubmitting(true);
    setError("");
    try {
      const response = await api.post("/portal/tickets", {
        ...body,
        request_entitlement_approval: approval,
        entitlement_approval_justification: approval
          ? justification.trim()
          : null,
        submission_idempotency_key: approval ? key.current : null,
        creation_idempotency_key: creationIdempotencyKey.current,
      });
      let attachmentUploadFailed = false;
      for (const file of files) {
        const data = new FormData();
        data.append("file", file);
        try {
          await api.post(`/tickets/${response.data.id}/attachments`, data);
        } catch {
          attachmentUploadFailed = true;
        }
      }
      navigate("/portal/tickets", {
        replace: true,
        state: {
          ticketCreated: true,
          ticketNumber: response.data.ticket_number,
          attachmentUploadFailed,
          pendingApproval: approval,
        },
      });
    } catch (caught) {
      locked.current = false;
      setSubmitting(false);
      setError(
        axios.isAxiosError(caught)
          ? (caught.response?.data?.error?.message ??
              t("portalCreate.submitFailed"))
          : t("portalCreate.submitFailed"),
      );
    }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!clientId || (mosaic && !selectionComplete)) {
      setError(
        t(mosaic ? "portalCreate.completePath" : "portalCreate.selectClient"),
      );
      return;
    }
    const body = payload();
    if (covered.length > 1 && !contractId) {
      setError(t("portalCreate.selectContractError"));
      return;
    }
    if (mosaic && !reviewing) {
      setError("");
      setReviewing(true);
      return;
    }
    if (!covered.length) {
      setPending(body);
      return;
    }
    void send(body);
  }

  const details = (
    <Stack spacing={1.5} mt={3}>
      <Typography variant="h5" fontWeight={850}>
        {t(mosaic ? "portalCreate.completeDetails" : "portalCreate.details")}
      </Typography>
      {mosaic && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography fontWeight={800}>
            {t("portalCreate.selectedPath")}
          </Typography>
          <Typography sx={{ overflowWrap: "anywhere" }}>
            {localized(
              catalog.data?.products.find(
                (item) => item.id === Number(productId),
              ),
            )}{" "}
            → {localized(modules.find((item) => item.id === Number(moduleId)))}{" "}
            →{" "}
            {localized(services.find((item) => item.id === Number(serviceId)))}
          </Typography>
        </Paper>
      )}
      <SearchableDropdown
        label={t("portalCreate.requestType")}
        required
        value={ticketTypeId}
        onChange={(value) => {
          setReviewing(false);
          setTicketTypeId(value);
        }}
        options={(types.data ?? []).map((item) => ({
          value: item.id,
          label: localized(item),
        }))}
      />
      <SearchableDropdown
        label={t("tickets.priority")}
        required
        value={priority}
        onChange={(value) => {
          setReviewing(false);
          setPriority(value);
        }}
        options={priorityOptions.map((item) => ({
          value: item.value,
          label: t(`priority.${item.value}`, { defaultValue: item.label }),
        }))}
      />
      {canManageCallers && (
        <Stack
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          alignItems={{ sm: "center" }}
        >
          <Box flex={1}>
            <SearchableDropdown
              label={t("portalCreate.caller")}
              value={callerId}
              onChange={(value) => {
                setReviewing(false);
                setCallerId(value);
              }}
              options={[
                { value: "", label: t("portalCreate.noCaller") },
                ...(callers.data ?? []).map((item) => ({
                  value: item.id,
                  label: `${item.full_name}${item.phone_number || item.email ? ` — ${item.phone_number ?? item.email}` : ""}`,
                })),
              ]}
            />
          </Box>
          <Button
            type="button"
            variant="outlined"
            disabled={!clientId}
            onClick={() => {
              setCallerError("");
              setCallerDialog(true);
            }}
          >
            {t("portalCreate.addCaller")}
          </Button>
        </Stack>
      )}
      {covered.length === 1 && (
        <Alert severity="info">
          {t("portalCreate.contract")}: {covered[0].contract_number} —{" "}
          {covered[0].contract_name}. {covered[0].reason}
        </Alert>
      )}
      {covered.length > 1 && (
        <SearchableDropdown
          required
          label={t("portalCreate.agreedContract")}
          value={contractId}
          onChange={(value) => {
            setReviewing(false);
            setContractId(value);
          }}
          options={[
            { value: "", label: t("portalCreate.selectContract") },
            ...covered.map((item) => ({
              value: item.contract_id,
              label: t("portalCreate.contractOption", {
                number: item.contract_number,
                name: item.contract_name,
                date: new Date(item.end_date).toLocaleDateString(i18n.language),
              } as Record<string, unknown>),
            })),
          ]}
        />
      )}
      <TextField
        label={t("portalCreate.subject")}
        required
        value={subject}
        onChange={(event) => {
          setReviewing(false);
          setSubject(event.target.value);
        }}
        inputProps={{ minLength: 5 }}
      />
      <TextField
        label={t("portalCreate.description")}
        required
        multiline
        rows={7}
        value={description}
        onChange={(event) => {
          setReviewing(false);
          setDescription(event.target.value);
        }}
        inputProps={{ minLength: 10 }}
      />
      {types.data?.find((item) => item.id === Number(ticketTypeId))?.code ===
        "CHANGE_REQUEST" && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Change Request details
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Describe the requested change and its expected business outcome.
          </Typography>
          <Stack gap={2}>
            <TextField
              select
              label="Request kind"
              value={changeKind}
              onChange={(event) => setChangeKind(event.target.value)}
              required
            >
              <MenuItem value="NEW_FEATURE">New feature</MenuItem>
              <MenuItem value="UPDATE_EXISTING_FEATURE">
                Update existing feature
              </MenuItem>
            </TextField>
            <TextField
              label="Purpose of the request"
              value={changePurpose}
              onChange={(event) => setChangePurpose(event.target.value)}
              required
              multiline
              inputProps={{ minLength: 3 }}
            />
            <TextField
              label="Clear change description"
              value={changeDescription}
              onChange={(event) => setChangeDescription(event.target.value)}
              required
              multiline
              minRows={3}
              inputProps={{ minLength: 5 }}
            />
            <TextField
              label="Business impact"
              value={changeBusinessImpact}
              onChange={(event) => setChangeBusinessImpact(event.target.value)}
              required
              multiline
              inputProps={{ minLength: 3 }}
            />
            <TextField
              label="Expected result"
              value={changeExpectedResult}
              onChange={(event) => setChangeExpectedResult(event.target.value)}
              required
              multiline
              inputProps={{ minLength: 3 }}
            />
            <TextField
              label="Required permissions or access"
              value={changeRequiredPermissions}
              onChange={(event) =>
                setChangeRequiredPermissions(event.target.value)
              }
              multiline
            />
          </Stack>
        </Paper>
      )}
      <Button
        component="label"
        variant="outlined"
        sx={{ alignSelf: "flex-start" }}
      >
        {t("portalCreate.selectAttachments")}
        <input
          hidden
          multiple
          type="file"
          onChange={(event) => {
            setReviewing(false);
            setFiles(Array.from(event.target.files ?? []));
          }}
        />
      </Button>
      {files.length > 0 && (
        <Typography>
          {t("portalCreate.attachmentsSelected", { count: files.length })}
        </Typography>
      )}
      {mosaic && reviewing && (
        <Alert severity="success">
          <Typography fontWeight={800}>
            {t("portalCreate.reviewReady")}
          </Typography>
          {t("portalCreate.reviewNotice", { count: files.length })}
        </Alert>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
        <Button
          type="submit"
          variant="contained"
          disabled={
            submitting ||
            !clientId ||
            !productId ||
            !serviceId ||
            ((mosaic || serviceRequiresModule) && !moduleId) ||
            !ticketTypeId ||
            !priority
          }
        >
          {submitting
            ? t("portalCreate.submitting")
            : mosaic && !reviewing
              ? t("portalCreate.review")
              : t("portalCreate.submit")}
        </Button>
        {mosaic && reviewing && (
          <Button type="button" onClick={() => setReviewing(false)}>
            {t("portalCreate.editDetails")}
          </Button>
        )}
        <Button type="button" onClick={() => navigate("/portal/tickets")}>
          {t("common.actions.cancel")}
        </Button>
      </Stack>
    </Stack>
  );

  return (
    <>
      <Paper
        component="form"
        onSubmit={submit}
        sx={{ p: { xs: 2, md: 3 }, maxWidth: mosaic ? 1100 : 1000, mx: "auto" }}
      >
        <Typography variant="h4" fontWeight={900}>
          {t(mosaic ? "portalCreate.createMosaic" : "portalCreate.title")}
        </Typography>
        <Typography color="text.secondary">
          {mosaic
            ? t("portalCreate.mosaicSubtitle")
            : t(
                catalog.data?.visibility_mode === "ALL_WITH_COVERAGE_STATUS"
                  ? "portalCreate.allItems"
                  : "portalCreate.coveredItems",
              )}
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
        {catalog.isError && (
          <Alert
            severity="error"
            action={
              <Button onClick={() => void catalog.refetch()}>
                {t("portalCreate.retry")}
              </Button>
            }
            sx={{ mt: 2 }}
          >
            {t("portalCreate.catalogFailed")}
          </Alert>
        )}
        {(catalog.data?.clients.length ?? 0) > 1 && (
          <SearchableDropdown
            required
            label={t("portalCreate.affectedClient")}
            value={clientId}
            onChange={changeClient}
            margin="normal"
            options={[
              { value: "", label: t("portalCreate.selectAffectedClient") },
              ...(catalog.data?.clients ?? []).map((item) => ({
                value: item.id,
                label: `${item.name} (${item.code})`,
              })),
            ]}
          />
        )}
        {mosaic ? (
          <Stack spacing={3} mt={3}>
            <Breadcrumbs aria-label={t("portalCreate.mosaicSelection")}>
              <Button
                size="small"
                onClick={() => {
                  setProductId("");
                  setModuleId("");
                  setServiceId("");
                  mosaicUrl({ product: "", module: "", service: "" });
                }}
              >
                {t("portalCreate.product")}
                {productId
                  ? `: ${localized(catalog.data?.products.find((item) => item.id === Number(productId)))}`
                  : ""}
              </Button>
              <Button
                size="small"
                disabled={!productId}
                onClick={() => {
                  setModuleId("");
                  setServiceId("");
                  mosaicUrl({ module: "", service: "" });
                }}
              >
                {t("portalCreate.module")}
                {moduleId
                  ? `: ${localized(modules.find((item) => item.id === Number(moduleId)))}`
                  : ""}
              </Button>
              <Typography color={serviceId ? "primary.main" : "text.secondary"}>
                {t("portalCreate.service")}
                {serviceId
                  ? `: ${localized(services.find((item) => item.id === Number(serviceId)))}`
                  : ""}
              </Typography>
            </Breadcrumbs>
            {catalog.isLoading && (
              <Grid container spacing={2}>
                {[1, 2, 3].map((item) => (
                  <Grid key={item} size={{ xs: 12, sm: 6, md: 4 }}>
                    <Skeleton variant="rounded" height={126} />
                  </Grid>
                ))}
              </Grid>
            )}
            {!catalog.isLoading && !productId && (
              <SelectionCards
                title={t("portalCreate.product")}
                items={clientId ? (catalog.data?.products ?? []) : []}
                selectedId={productId}
                empty={t(
                  clientId
                    ? "portalCreate.noProducts"
                    : "portalCreate.selectClientFirst",
                )}
                onSelect={chooseProduct}
              />
            )}
            {productId && !moduleId && (
              <>
                <Button
                  startIcon={<ArrowBack />}
                  sx={{ alignSelf: "flex-start" }}
                  onClick={() => {
                    setProductId("");
                    mosaicUrl({ product: "", module: "", service: "" });
                  }}
                >
                  {t("portalCreate.backProducts")}
                </Button>
                <SelectionCards
                  title={t("portalCreate.module")}
                  items={modules}
                  selectedId={moduleId}
                  empty={t("portalCreate.noModules")}
                  onSelect={chooseModule}
                />
              </>
            )}
            {moduleId && !serviceId && (
              <>
                <Button
                  startIcon={<ArrowBack />}
                  sx={{ alignSelf: "flex-start" }}
                  onClick={() => {
                    setModuleId("");
                    mosaicUrl({ module: "", service: "" });
                  }}
                >
                  {t("portalCreate.backModules")}
                </Button>
                <SelectionCards
                  title={t("portalCreate.service")}
                  items={services}
                  selectedId={serviceId}
                  empty={t("portalCreate.noServices")}
                  onSelect={chooseService}
                />
              </>
            )}
            {selectionComplete && (
              <>
                <Button
                  startIcon={<ArrowBack />}
                  sx={{ alignSelf: "flex-start" }}
                  onClick={() => {
                    setServiceId("");
                    mosaicUrl({ service: "" });
                  }}
                >
                  {t("portalCreate.changeService")}
                </Button>
                {details}
              </>
            )}
          </Stack>
        ) : (
          <>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <SearchableDropdown
                label={t("portalCreate.product")}
                required
                value={productId}
                disabled={!clientId}
                margin="normal"
                sx={{ width: "100%", minWidth: { md: 320 }, flex: 1 }}
                onChange={(value) => {
                  setProductId(value);
                  setModuleId("");
                  setServiceId("");
                }}
                options={(catalog.data?.products ?? []).map((item) => ({
                  value: item.id,
                  label: `${localized(item)} — ${t(item.covered ? "portalCreate.included" : "portalCreate.approvalRequired")}`,
                }))}
              />
              <SearchableDropdown
                label={t("portalCreate.module")}
                required={serviceRequiresModule}
                value={moduleId}
                disabled={!productId}
                margin="normal"
                sx={{ width: "100%", minWidth: { md: 320 }, flex: 1 }}
                onChange={(value) => {
                  setModuleId(value);
                  if (
                    selectedService?.module_ids.length &&
                    value &&
                    !selectedService.module_ids.includes(Number(value))
                  )
                    setServiceId("");
                }}
                options={[
                  ...(!serviceRequiresModule
                    ? [{ value: "", label: t("portalCreate.generalModules") }]
                    : []),
                  ...compatibleModules.map((item) => ({
                    value: item.id,
                    label: localized(item),
                  })),
                ]}
              />
            </Stack>
            <SearchableDropdown
              label={t("portalCreate.service")}
              required
              value={serviceId}
              disabled={!clientId}
              onChange={(value) => {
                setReviewing(false);
                setServiceId(value);
                const service = catalog.data?.services.find(
                  (item) => item.id === Number(value),
                );
                if (
                  moduleId &&
                  service?.module_ids.length &&
                  !service.module_ids.includes(Number(moduleId))
                )
                  setModuleId("");
              }}
              options={servicesForProduct.map((item) => ({
                value: item.id,
                label: `${localized(item)} — ${t(item.covered ? "portalCreate.included" : "portalCreate.approvalRequired")}`,
              }))}
            />
            {serviceRequiresModule && !moduleId && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                This service requires a module. Select one of the compatible modules above.
              </Alert>
            )}
            {details}
          </>
        )}
      </Paper>
      <Dialog
        open={callerDialog}
        onClose={() => setCallerDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitCaller}>
          <DialogTitle>{t("portalCreate.addCaller")}</DialogTitle>
          <DialogContent>
            {callerError && (
              <Alert severity="error" sx={{ mb: 1 }}>
                {callerError}
              </Alert>
            )}
            <TextField
              required
              name="full_name"
              label={t("portalCreate.callerName")}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 2 }}
            />
            <TextField
              name="phone_number"
              label={t("portalCreate.callerPhone")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="email"
              type="email"
              label={t("portalCreate.callerEmail")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="job_title"
              label={t("portalCreate.callerJobTitle")}
              fullWidth
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button type="button" onClick={() => setCallerDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createCaller.isPending}
            >
              {t("portalCreate.addAndSelectCaller")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(pending)}
        onClose={() => setPending(null)}
        fullWidth
      >
        <DialogTitle>{t("portalCreate.outOfContract")}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t("portalCreate.approvalNotice")}
          </Alert>
          <TextField
            required
            fullWidth
            multiline
            rows={3}
            label={t("portalCreate.justification")}
            value={justification}
            onChange={(event) => setJustification(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPending(null)}>
            {t("portalCreate.changeSelection")}
          </Button>
          <Button
            color="warning"
            variant="contained"
            disabled={justification.trim().length < 5}
            onClick={() => {
              const body = pending;
              if (body) {
                setPending(null);
                void send(body, true);
              }
            }}
          >
            {t("portalCreate.submitApproval")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
