import { ArrowBack } from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
} from "@mui/material";
import axios from "axios";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FormEvent,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, apiErrorMessage } from "../api/client";
import { MobileMultiAutocomplete } from "../components/MobileMultiAutocomplete";
import { useAuth } from "../auth/AuthContext";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { serverDateInput } from "../utils/serverTime";

type Catalog = { id: number; code: string; name: string; name_ar?: string };
type Client = {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  ticket_creation_allowed: boolean;
  ticket_count: number;
};
type Contact = {
  id: number;
  client_id: number;
  full_name: string;
  email?: string;
  phone_number?: string;
  job_title?: string;
  is_active: boolean;
};
type Assignee = {
  id: number;
  full_name: string;
  username: string;
  department?: string;
  job_title?: string;
};
type Branch = { id: number; name: string; code: string; is_active: boolean };
type TicketPayload = Record<string, unknown>;
type WorkAssignmentSource = {
  id: number;
  title: string;
  description: string;
  version: number;
  assignment_type: string;
  context: Record<string, string>;
  clients: Array<{ client_id: number; name: string }>;
};
type TicketFormFieldSetting = {
  field_key: string;
  is_visible: boolean;
  is_required: boolean;
  default_value?: string;
  permission?: string;
};
type SimilarTicket = {
  id: number;
  ticket_number: string;
  ticket_type_id: number;
  client_id: number;
  subject: string;
  description: string;
  product_id?: number;
  product_module_id?: number;
  service_id?: number;
  category_id?: number;
  subcategory_id?: number;
  environment_id?: number;
  branch_id?: number;
  requester_contact_id?: number;
  source_channel?: string;
  priority: string;
  impact: string;
  urgency: string;
  category?: string;
  affected_users?: string;
  patient_safety_flag: boolean;
  security_incident_flag?: boolean;
  updated_at: string;
};
type TicketTemplate = {
  id: number;
  name: string;
  ticket_type_id: number;
  client_id?: number;
  subject: string;
  description: string;
  product_id?: number;
  product_module_id?: number;
  service_id?: number;
  category_id?: number;
  subcategory_id?: number;
  environment_id?: number;
  priority: string;
  impact: string;
  urgency: string;
  assigned_team?: string;
};

type SearchOption = {
  id: number;
  name: string;
  name_ar?: string;
  code?: string;
  covered?: boolean;
};
type ContractCatalog = {
  visibility_mode: "CONTRACT_ONLY" | "ALL_WITH_COVERAGE_STATUS";
  products: Array<Catalog & { covered: boolean }>;
  modules: Array<Catalog & { product_id: number; covered: boolean }>;
  services: Array<Catalog & { covered: boolean }>;
};
type ContractCandidate = {
  contract_id: number;
  contract_number: string;
  contract_name: string;
  contract_type?: string;
  precedence: number;
  end_date: string;
  status: string;
  reason: string;
};
type IntakeAiSuggestion = {
  client: string;
  client_id?: number;
  title: string;
  professional_description: string;
  ticket_type_id?: number;
  product_id?: number;
  product_module_id?: number;
  priority: string;
  impact: string;
  urgency: string;
  missing_information: string[];
  suggested_actions: string[];
};

const recentKey = (field: string) =>
  `support-hub-recent-${serverDateInput()}-${field}`;
function recentIds(field: string): number[] {
  try {
    return JSON.parse(
      window.localStorage.getItem(recentKey(field)) ?? "[]",
    ) as number[];
  } catch {
    return [];
  }
}
function rememberRecent(field: string, id?: number) {
  if (!id) return;
  window.localStorage.setItem(
    recentKey(field),
    JSON.stringify(
      [id, ...recentIds(field).filter((item) => item !== id)].slice(0, 3),
    ),
  );
}
function ranked<T extends { id: number }>(field: string, options: T[]): T[] {
  const order = recentIds(field);
  return [...options].sort((a, b) => {
    const ai = order.indexOf(a.id);
    const bi = order.indexOf(b.id);
    return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
  });
}

function SearchableSelect({
  name,
  label,
  options,
  required = false,
  disabled = false,
  valueId,
  defaultValueId,
  emptyLabel = "Not specified",
  getLabel,
  getOptionColor,
  getOptionDisabled,
  onChange,
  margin,
}: {
  name: string;
  label: string;
  options: SearchOption[];
  required?: boolean;
  disabled?: boolean;
  valueId?: number | null;
  defaultValueId?: number | null;
  emptyLabel?: string;
  getLabel?: (option: SearchOption) => string;
  getOptionColor?: (option: SearchOption) => string | undefined;
  getOptionDisabled?: (option: SearchOption) => boolean;
  onChange?: (option: SearchOption | null) => void;
  margin?: "normal";
}) {
  const { t } = useTranslation();
  const controlled = valueId !== undefined;
  const [internalId, setInternalId] = useState<number | null>(
    defaultValueId ?? null,
  );
  useEffect(() => {
    if (!controlled && defaultValueId) setInternalId(defaultValueId);
  }, [controlled, defaultValueId]);
  const selectedId = controlled ? valueId : internalId;
  const selected = options.find((option) => option.id === selectedId) ?? null;
  return (
    <>
      <input type="hidden" name={name} value={selected?.id ?? ""} />
      <Autocomplete
        fullWidth
        options={ranked(name, options)}
        value={selected}
        disabled={disabled}
        onChange={(_, option) => {
          if (!controlled) setInternalId(option?.id ?? null);
          rememberRecent(name, option?.id);
          onChange?.(option);
        }}
        getOptionLabel={getLabel ?? ((option) => option.name)}
        getOptionDisabled={getOptionDisabled}
        isOptionEqualToValue={(option, value) => option.id === value.id}
        noOptionsText={t("createTicket.noMatchingResults")}
        renderOption={(props, option) => (
          <li
            {...props}
            style={{ ...props.style, color: getOptionColor?.(option) }}
          >
            {getLabel?.(option) ?? option.name}
          </li>
        )}
        renderInput={(params) => (
          <TextField
            {...params}
            size="small"
            required={required}
            label={label}
            margin={margin}
            placeholder={t("createTicket.searchField", { field: label })}
            helperText={
              !required && !selected
                ? emptyLabel === "Not specified"
                  ? t("createTicket.notSpecified")
                  : emptyLabel
                : undefined
            }
          />
        )}
      />
    </>
  );
}

type CreateTicketCompletionMode = "close" | "new";

export function CreateTicketPage({
  onCreated,
}: {
  onCreated?: (mode: CreateTicketCompletionMode) => void;
} = {}) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const copyFromId = Number(searchParams.get("copy_from")) || null;
  const workAssignmentId =
    Number(searchParams.get("work_assignment_id")) || null;
  const returnTo = (location.state as { returnTo?: string } | null)?.returnTo;
  const goBack = () => (returnTo ? navigate(returnTo) : navigate(-1));
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const mobile = useMediaQuery((theme) => theme.breakpoints.down("md"));
  const [additionalOpen, setAdditionalOpen] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(
    null,
  );
  const [selectedModuleId, setSelectedModuleId] = useState<number | null>(null);
  const [selectedServiceId, setSelectedServiceId] = useState<number | null>(
    null,
  );
  const [selectedContractId, setSelectedContractId] = useState<number | null>(
    null,
  );
  const [selectedCaller, setSelectedCaller] = useState<Contact | null>(null);
  const [selectedFollowers, setSelectedFollowers] = useState<Assignee[]>([]);
  const [selectedAssignee, setSelectedAssignee] = useState<Assignee | null>(
    null,
  );
  const [selectedTeam, setSelectedTeam] = useState<Catalog | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(
    null,
  );
  const [newCallerOpen, setNewCallerOpen] = useState(false);
  const [callerSaving, setCallerSaving] = useState(false);
  const [callerError, setCallerError] = useState("");
  const [existingCallerSearch, setExistingCallerSearch] = useState("");
  const [selectedExistingCaller, setSelectedExistingCaller] =
    useState<Contact | null>(null);
  const [branchOpen, setBranchOpen] = useState(false);
  const [branchError, setBranchError] = useState("");
  const [selectedBranchId, setSelectedBranchId] = useState<number | null>(null);
  const [pendingInactiveTicket, setPendingInactiveTicket] =
    useState<TicketPayload | null>(null);
  const [pendingEntitlementTicket, setPendingEntitlementTicket] = useState<{
    payload: TicketPayload;
    inactiveConfirmed: boolean;
    message: string;
  } | null>(null);
  const approvalSubmissionKey = useRef(crypto.randomUUID());
  const creationIdempotencyKey = useRef(crypto.randomUUID());
  const completionMode = useRef<CreateTicketCompletionMode>("close");
  const [entitlementReason, setEntitlementReason] = useState("");
  const [subject, setSubject] = useState("");
  const [aiSuggestion, setAiSuggestion] = useState<IntakeAiSuggestion | null>(
    null,
  );
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [initialAttachments, setInitialAttachments] = useState<File[]>([]);
  const [selectedSimilarId, setSelectedSimilarId] = useState<number | null>(
    null,
  );
  const deferredSubject = useDeferredValue(subject);
  const rawSuggestionSubject = deferredSubject.trim();
  const similarTicketMode = rawSuggestionSubject.endsWith("*");
  const similaritySubject = rawSuggestionSubject.replace(/\*$/, "").trim();
  const similarityTriggered =
    similarTicketMode && similaritySubject.length >= 3;
  const templateTriggered = !similarTicketMode && similaritySubject.length >= 3;
  const [pendingModuleId, setPendingModuleId] = useState<number | null>(null);
  const [reusedFromTicket, setReusedFromTicket] =
    useState<SimilarTicket | null>(null);
  const copiedTicketApplied = useRef(false);
  const workAssignmentApplied = useRef(false);
  const [copiedRequesterContactId, setCopiedRequesterContactId] = useState<
    number | null
  >(null);
  const formRef = useRef<HTMLFormElement>(null);
  const formSettings = useQuery({
    queryKey: ["ticket-form-fields"],
    queryFn: async () =>
      (await api.get<TicketFormFieldSetting[]>("/system/ticket-form-fields"))
        .data,
  });
  const copiedTicket = useQuery({
    queryKey: ["ticket-copy-source", copyFromId],
    queryFn: async () =>
      (await api.get<SimilarTicket>(`/tickets/${copyFromId}`)).data,
    enabled: Boolean(copyFromId && hasPermission("ticket.copy")),
  });
  const workAssignment = useQuery({
    queryKey: ["work-assignment-ticket-source", workAssignmentId],
    queryFn: async () =>
      (
        await api.get<WorkAssignmentSource>(
          `/work-assignments/${workAssignmentId}`,
        )
      ).data,
    enabled: Boolean(workAssignmentId),
  });
  const setting = (key: string) =>
    formSettings.data?.find((item) => item.field_key === key);
  const isVisible = (key: string) => {
    const item = setting(key);
    return (
      (item?.is_visible ?? true) &&
      (!item?.permission || hasPermission(item.permission))
    );
  };
  const isRequired = (key: string) => setting(key)?.is_required ?? false;
  const types = useQuery({
    queryKey: ["ticket-types"],
    queryFn: async () => (await api.get<Catalog[]>("/ticket-types")).data,
  });
  const defaultTicketTypeId = types.data?.find(
    (item) => item.code === setting("ticket_type_id")?.default_value,
  )?.id;
  const clients = useQuery({
    queryKey: ["clients", "ticket-create", "ranked"],
    queryFn: async () =>
      (await api.get<Client[]>("/clients/ticket-options")).data,
  });
  const selectedClient = clients.data?.find(
    (item) => item.id === selectedClientId,
  );
  const contacts = useQuery({
    queryKey: ["contacts", "ticket-create", selectedClientId],
    queryFn: async () =>
      (
        await api.get<Contact[]>("/contacts", {
          params: { client_id: selectedClientId },
        })
      ).data,
    enabled: Boolean(selectedClientId),
  });
  useEffect(() => {
    if (!selectedClientId || !contacts.data) return;
    setSelectedCaller((current) =>
      current && contacts.data.some((contact) => contact.id === current.id)
        ? current
        : (contacts.data.find(
            (contact) => contact.is_active && contact.phone_number,
          ) ??
          contacts.data.find((contact) => contact.is_active) ??
          null),
    );
  }, [contacts.data, selectedClientId]);
  useEffect(() => {
    if (!copiedRequesterContactId || !contacts.data) return;
    const caller = contacts.data.find(
      (item) => item.id === copiedRequesterContactId && item.is_active,
    );
    if (caller) setSelectedCaller(caller);
    setCopiedRequesterContactId(null);
  }, [contacts.data, copiedRequesterContactId]);
  const deferredCallerSearch = useDeferredValue(existingCallerSearch.trim());
  const existingCallers = useQuery({
    queryKey: [
      "contacts",
      "search-existing",
      selectedClientId,
      deferredCallerSearch,
    ],
    queryFn: async () =>
      (
        await api.get<Contact[]>("/contacts/search-existing", {
          params: { client_id: selectedClientId, query: deferredCallerSearch },
        })
      ).data,
    enabled:
      newCallerOpen &&
      hasPermission("contact.link_existing") &&
      Boolean(selectedClientId) &&
      deferredCallerSearch.length >= 2,
  });
  const assignees = useQuery({
    queryKey: ["ticket-assignees"],
    queryFn: async () => (await api.get<Assignee[]>("/ticket-assignees")).data,
    enabled: hasPermission("ticket.assign.team"),
  });
  const teams = useQuery({
    queryKey: ["support-teams"],
    queryFn: async () => (await api.get<Catalog[]>("/support-teams")).data,
    enabled: hasPermission("ticket.assign.team"),
  });
  const branches = useQuery({
    queryKey: ["branches", "ticket-create", selectedClientId],
    queryFn: async () =>
      (await api.get<Branch[]>(`/clients/${selectedClientId}/branches`)).data,
    enabled: Boolean(selectedClientId),
  });
  const createBranch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedClientId) return;
    setBranchError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const row = (
        await api.post<Branch>(`/clients/${selectedClientId}/branches`, {
          name: String(values.name).trim(),
          timezone: String(values.timezone).trim() || null,
          address: String(values.address).trim() || null,
          is_active: true,
        })
      ).data;
      setSelectedBranchId(row.id);
      setBranchOpen(false);
      await queryClient.invalidateQueries({
        queryKey: ["branches", "ticket-create", selectedClientId],
      });
    } catch {
      setBranchError(t("createTicket.branchCreateFailed"));
    }
  };
  const environments = useQuery({
    queryKey: ["environments", "ticket-create"],
    queryFn: async () => (await api.get<Catalog[]>("/environments")).data,
  });
  const contractCatalog = useQuery({
    queryKey: ["ticket-contract-catalog", selectedClientId],
    queryFn: async () =>
      (
        await api.get<ContractCatalog>("/ticket-contract-catalog", {
          params: { client_id: selectedClientId },
        })
      ).data,
    enabled: Boolean(selectedClientId),
  });
  const categories = useQuery({
    queryKey: ["ticket-categories"],
    queryFn: async () => (await api.get<Catalog[]>("/ticket-categories")).data,
  });
  const subcategories = useQuery({
    queryKey: ["ticket-subcategories", selectedCategoryId],
    queryFn: async () =>
      (
        await api.get<Catalog[]>(
          `/ticket-categories/${selectedCategoryId}/subcategories`,
        )
      ).data,
    enabled: Boolean(selectedCategoryId),
  });
  const products = contractCatalog.data?.products ?? [];
  const services = contractCatalog.data?.services ?? [];
  const modules = useMemo(
    () =>
      contractCatalog.data?.modules.filter(
        (item) => item.product_id === selectedProductId,
      ) ?? [],
    [contractCatalog.data?.modules, selectedProductId],
  );
  const contractCandidates = useQuery({
    queryKey: [
      "ticket-contract-candidates",
      selectedClientId,
      selectedProductId,
      selectedModuleId,
      selectedServiceId,
    ],
    enabled: Boolean(selectedClientId),
    queryFn: async () =>
      (
        await api.get<ContractCandidate[]>("/entitlements/candidates", {
          params: {
            client_id: selectedClientId,
            product_id: selectedProductId || undefined,
            product_module_id: selectedModuleId || undefined,
            service_id: selectedServiceId || undefined,
          },
        })
      ).data,
  });
  useEffect(
    () =>
      setSelectedContractId(
        contractCandidates.data?.length === 1
          ? contractCandidates.data[0].contract_id
          : null,
      ),
    [contractCandidates.data],
  );
  const similarTickets = useQuery({
    queryKey: ["similar-tickets", similaritySubject, selectedClientId],
    queryFn: async () =>
      (
        await api.get<SimilarTicket[]>("/tickets/similar", {
          params: {
            subject: similaritySubject,
            client_id: selectedClientId || undefined,
            limit: 5,
          },
        })
      ).data,
    enabled: similarityTriggered,
  });
  const ticketTemplates = useQuery({
    queryKey: ["ticket-templates", similaritySubject, selectedClientId],
    queryFn: async () =>
      (
        await api.get<TicketTemplate[]>("/tickets/templates", {
          params: {
            query: similaritySubject,
            client_id: selectedClientId || undefined,
            limit: 5,
          },
        })
      ).data,
    enabled: templateTriggered,
  });
  const orderedSimilarTickets = useMemo(
    () =>
      [...(similarTickets.data ?? [])].sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      ),
    [similarTickets.data],
  );
  const selectedSimilar =
    orderedSimilarTickets.find((item) => item.id === selectedSimilarId) ??
    orderedSimilarTickets[0];
  useEffect(() => {
    setSelectedSimilarId(orderedSimilarTickets[0]?.id ?? null);
  }, [orderedSimilarTickets]);
  const callerHistory = useQuery({
    queryKey: ["caller-ticket-history", selectedCaller?.id],
    queryFn: async () =>
      (
        await api.get<SimilarTicket[]>("/tickets", {
          params: { requester_contact_id: selectedCaller?.id, limit: 5 },
        })
      ).data,
    enabled: Boolean(selectedCaller),
  });
  useEffect(() => {
    if (!pendingModuleId || !modules.length || !formRef.current) return;
    const field = formRef.current.elements.namedItem(
      "product_module_id",
    ) as HTMLSelectElement | null;
    if (field) field.value = String(pendingModuleId);
    setPendingModuleId(null);
  }, [modules, pendingModuleId]);

  function reuseTicketDetails(ticket: SimilarTicket) {
    const form = formRef.current;
    if (!form) return;
    const setValue = (
      name: string,
      value: string | number | boolean | null | undefined,
    ) => {
      const field = form.elements.namedItem(name) as
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null;
      if (field)
        field.value =
          value === null || value === undefined ? "" : String(value);
    };
    setValue("ticket_type_id", ticket.ticket_type_id);
    setValue("client_id", ticket.client_id);
    setSelectedClientId(ticket.client_id);
    setValue("description", ticket.description);
    setValue("priority", ticket.priority);
    setValue("impact", ticket.impact);
    setValue("urgency", ticket.urgency);
    setValue("category", ticket.category);
    setValue("affected_users", ticket.affected_users);
    setValue("patient_safety_flag", ticket.patient_safety_flag);
    setValue("security_incident_flag", ticket.security_incident_flag);
    setValue("source_channel", ticket.source_channel);
    setValue("product_id", ticket.product_id);
    setSelectedProductId(ticket.product_id ?? null);
    setSelectedServiceId(ticket.service_id ?? null);
    setSelectedCategoryId(ticket.category_id ?? null);
    setSelectedBranchId(ticket.branch_id ?? null);
    setCopiedRequesterContactId(ticket.requester_contact_id ?? null);
    setPendingModuleId(ticket.product_module_id ?? null);
    setReusedFromTicket(ticket);
  }
  function applyTicketTemplate(template: TicketTemplate) {
    reuseTicketDetails({
      ...template,
      ticket_number: template.name,
      client_id: template.client_id ?? selectedClientId ?? 0,
      patient_safety_flag: false,
      updated_at: new Date().toISOString(),
    });
    setSelectedClientId(template.client_id ?? selectedClientId);
    setSubject(template.subject);
    if (template.assigned_team)
      setSelectedTeam(
        teams.data?.find((item) => item.name === template.assigned_team) ??
          null,
      );
  }

  function setFormValue(name: string, value: string | number | undefined) {
    const field = formRef.current?.elements.namedItem(name) as
      HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null;
    if (field && value !== undefined && value !== "")
      field.value = String(value);
  }

  useEffect(() => {
    const assignment = workAssignment.data;
    if (
      !assignment ||
      formSettings.isLoading ||
      !formRef.current ||
      workAssignmentApplied.current
    )
      return;
    workAssignmentApplied.current = true;
    setSubject(assignment.title);
    setSelectedClientId(assignment.clients[0]?.client_id ?? null);
    const details = Object.entries(assignment.context)
      .filter(([, value]) => value.trim())
      .map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`)
      .join("\n");
    setFormValue(
      "description",
      [
        assignment.description,
        details,
        `Converted from work assignment #${assignment.id} (${assignment.assignment_type.replaceAll("_", " ")}).`,
      ]
        .filter(Boolean)
        .join("\n\n"),
    );
  }, [formSettings.isLoading, workAssignment.data]);

  function applyAiSuggestion(suggestion: IntakeAiSuggestion) {
    if (suggestion.client_id && suggestion.client_id !== selectedClientId) {
      setSelectedClientId(suggestion.client_id);
      setSelectedCaller(null);
      setSelectedBranchId(null);
    }
    if (suggestion.title) setSubject(suggestion.title);
    setFormValue("description", suggestion.professional_description);
    setFormValue("ticket_type_id", suggestion.ticket_type_id);
    setFormValue("priority", suggestion.priority);
    setFormValue("impact", suggestion.impact.toUpperCase());
    setFormValue("urgency", suggestion.urgency.toUpperCase());
    if (suggestion.product_id) {
      setSelectedProductId(suggestion.product_id);
      setFormValue("product_id", suggestion.product_id);
      setPendingModuleId(suggestion.product_module_id ?? null);
    }
  }

  async function analyzeWithLocalAi() {
    const form = formRef.current;
    const description = String(
      (form?.elements.namedItem("description") as HTMLTextAreaElement | null)
        ?.value ?? "",
    ).trim();
    if (description.length < 10) {
      setAiError("Enter at least 10 characters in the description first.");
      return;
    }
    setAiLoading(true);
    setAiError("");
    try {
      const source = (
        form?.elements.namedItem("source_channel") as HTMLSelectElement | null
      )?.value;
      const result = (
        await api.post<IntakeAiSuggestion>(
          "/tickets/ai/intake",
          {
            description,
            client_id: selectedClientId,
            source,
          },
          { timeout: 150_000 },
        )
      ).data;
      setAiSuggestion(result);
      applyAiSuggestion(result);
    } catch (requestError) {
      setAiError(
        apiErrorMessage(
          requestError,
          "The local AI could not analyze this ticket.",
        ),
      );
    } finally {
      setAiLoading(false);
    }
  }

  useEffect(() => {
    if (!copiedTicket.data || !formSettings.data || copiedTicketApplied.current)
      return;
    copiedTicketApplied.current = true;
    reuseTicketDetails(copiedTicket.data);
    setSubject(copiedTicket.data.subject);
  }, [copiedTicket.data, formSettings.data]);

  async function createTicket(
    payload: TicketPayload,
    inactiveClientConfirmed = false,
  ) {
    setSaving(true);
    setError("");
    try {
      const ticketPayload = {
        ...payload,
        creation_idempotency_key: creationIdempotencyKey.current,
        inactive_client_confirmed: inactiveClientConfirmed,
      };
      const response = workAssignment.data
        ? await api.post(
            `/work-assignments/${workAssignment.data.id}/convert-to-ticket`,
            {
              expected_version: workAssignment.data.version,
              ticket: ticketPayload,
            },
          )
        : await api.post("/tickets", ticketPayload);
      if (reusedFromTicket && hasPermission("ticket.relate")) {
        try {
          await api.post(`/tickets/${response.data.id}/relations`, {
            related_ticket_id: reusedFromTicket.id,
            relation_type: "DUPLICATE",
            reason: `Details reused from ${reusedFromTicket.ticket_number} during ticket creation.`,
          });
        } catch {
          // Ticket creation succeeded; relation failure must not hide the new ticket.
        }
      }
      const uploadFailures: string[] = [];
      for (const file of initialAttachments) {
        const body = new FormData();
        body.append("file", file);
        body.append("operation_key", crypto.randomUUID());
        try {
          await api.post(`/tickets/${response.data.id}/attachments`, body);
        } catch {
          uploadFailures.push(file.name);
        }
      }
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
      if (completionMode.current === "new") {
        formRef.current?.reset();
        setError("");
        setAdditionalOpen(false);
        setSelectedClientId(null);
        setSelectedProductId(null);
        setSelectedModuleId(null);
        setSelectedServiceId(null);
        setSelectedContractId(null);
        setSelectedCaller(null);
        setSelectedFollowers([]);
        setSelectedAssignee(null);
        setSelectedTeam(null);
        setSelectedCategoryId(null);
        setSelectedBranchId(null);
        setSubject("");
        setInitialAttachments([]);
        setSelectedSimilarId(null);
        setReusedFromTicket(null);
        setCopiedRequesterContactId(null);
        setPendingModuleId(null);
        setPendingInactiveTicket(null);
        setPendingEntitlementTicket(null);
        setEntitlementReason("");
        creationIdempotencyKey.current = crypto.randomUUID();
        approvalSubmissionKey.current = crypto.randomUUID();
        onCreated?.("new");
        return;
      }
      if (onCreated) {
        onCreated("close");
        return;
      }
      if (workAssignment.data) {
        navigate(`/tickets/${response.data.id}`, {
          replace: true,
          state: {
            ticketCreated: true,
            ticketNumber: response.data.ticket_number,
            convertedFromAssignmentId: workAssignment.data.id,
            ...(uploadFailures.length
              ? {
                  attachmentError: `Ticket created, but these attachments need to be retried: ${uploadFailures.join(", ")}`,
                }
              : {}),
          },
        });
        return;
      }
      navigate(returnTo ?? "/tickets", {
        replace: true,
        state: {
          ticketCreated: true,
          ticketNumber: response.data.ticket_number,
          ...(uploadFailures.length
            ? {
                attachmentError: `Ticket created, but these attachments need to be retried: ${uploadFailures.join(", ")}`,
              }
            : {}),
        },
      });
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        const code = requestError.response?.data?.error?.code;
        const message = requestError.response?.data?.error?.message;
        if (code === "ENTITLEMENT_OVERRIDE_REQUIRED") {
          setPendingEntitlementTicket({
            payload,
            inactiveConfirmed: inactiveClientConfirmed,
            message,
          });
          return;
        }
        setError(message ?? t("createTicket.createFailed"));
      } else {
        setError(t("createTicket.createFailed"));
      }
    } finally {
      setSaving(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      isVisible("requester_contact_id") &&
      isRequired("requester_contact_id") &&
      !selectedCaller
    ) {
      setError(t("createTicket.selectCallerError"));
      return;
    }
    if ((contractCandidates.data?.length ?? 0) > 1 && !selectedContractId) {
      setError(t("createTicket.selectContractError"));
      return;
    }
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const payload = {
      ...values,
      subject: String(values.subject).trim().replace(/\*$/, "").trim(),
      ticket_type_id: Number(values.ticket_type_id),
      client_id: Number(values.client_id),
      requester_contact_id: selectedCaller?.id ?? null,
      assigned_user_id: values.assigned_user_id
        ? Number(values.assigned_user_id)
        : null,
      assigned_team: values.assigned_team || null,
      follower_user_ids: selectedFollowers.map((item) => item.id),
      branch_id: values.branch_id ? Number(values.branch_id) : null,
      environment_id: values.environment_id
        ? Number(values.environment_id)
        : null,
      service_id: values.service_id ? Number(values.service_id) : null,
      category_id: values.category_id ? Number(values.category_id) : null,
      subcategory_id: values.subcategory_id
        ? Number(values.subcategory_id)
        : null,
      product_id: values.product_id ? Number(values.product_id) : null,
      product_module_id: values.product_module_id
        ? Number(values.product_module_id)
        : null,
      contract_id: selectedContractId,
      priority: values.priority || null,
      patient_safety_flag: values.patient_safety_flag === "true",
      security_incident_flag: values.security_incident_flag === "true",
      first_occurred_at: values.first_occurred_at || null,
    };
    if (selectedClient && !selectedClient.ticket_creation_allowed) {
      setPendingInactiveTicket(payload);
      return;
    }
    void createTicket(payload);
  }

  async function createCaller(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedClientId) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    setCallerSaving(true);
    setCallerError("");
    try {
      const response = await api.post<Contact>("/contacts", {
        client_id: selectedClientId,
        full_name: String(values.full_name).trim(),
        phone_number: String(values.phone_number).trim() || null,
        email: String(values.email).trim() || null,
        job_title: String(values.job_title).trim() || null,
        is_active: true,
      });
      setSelectedCaller(response.data);
      await queryClient.invalidateQueries({
        queryKey: ["contacts", "ticket-create", selectedClientId],
      });
      setNewCallerOpen(false);
    } catch (requestError) {
      setCallerError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ??
              t("createTicket.callerCreateFailed"))
          : t("createTicket.callerCreateFailed"),
      );
    } finally {
      setCallerSaving(false);
    }
  }

  async function linkExistingCaller() {
    if (!selectedClientId || !selectedExistingCaller) return;
    setCallerSaving(true);
    setCallerError("");
    try {
      const response = await api.post<Contact>(
        `/clients/${selectedClientId}/contacts/link`,
        { contact_id: selectedExistingCaller.id },
      );
      await queryClient.invalidateQueries({
        queryKey: ["contacts", "ticket-create", selectedClientId],
      });
      setSelectedCaller(response.data);
      setExistingCallerSearch("");
      setSelectedExistingCaller(null);
      setNewCallerOpen(false);
    } catch (requestError) {
      setCallerError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ??
              t("createTicket.callerLinkFailed"))
          : t("createTicket.callerLinkFailed"),
      );
    } finally {
      setCallerSaving(false);
    }
  }

  if (formSettings.isLoading)
    return (
      <Paper sx={{ minHeight: 320, display: "grid", placeItems: "center" }}>
        <Stack alignItems="center" spacing={1}>
          <CircularProgress />
          <Typography color="text.secondary">
            {t("createTicket.preparing")}
          </Typography>
        </Stack>
      </Paper>
    );

  return (
    <>
      <Paper
        ref={formRef}
        component="form"
        onSubmit={submit}
        onInvalid={(event) => {
          if (
            mobile &&
            (event.target as HTMLElement).closest("[data-additional-fields]")
          )
            setAdditionalOpen(true);
        }}
        elevation={0}
        sx={{
          p: { xs: 1.5, md: 2 },
          pb: { xs: 11, md: 2 },
          border: 1,
          borderColor: "divider",
          overflow: "hidden",
          "& .MuiInputBase-root:not(.MuiInputBase-multiline)": {
            minHeight: 40,
          },
          "& .MuiFormHelperText-root": { mt: 0.5 },
        }}
      >
        <Box
          sx={{
            mx: { xs: -1.5, md: -2 },
            mt: { xs: -1.5, md: -2 },
            mb: 2,
            px: { xs: 2, md: 2.5 },
            py: { xs: 1.75, md: 2 },
            color: "primary.contrastText",
            background: (theme) =>
              `linear-gradient(125deg, ${theme.palette.primary.dark}, ${theme.palette.secondary.main})`,
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            gap={2}
          >
            <Box>
              <Button
                color="inherit"
                startIcon={<ArrowBack />}
                onClick={goBack}
                size="small"
              >
                {t("common.back")}
              </Button>
              <Typography
                variant="overline"
                display="block"
                sx={{ opacity: 0.8, letterSpacing: 1.2 }}
              >
                {t("createTicket.serviceWorkspace")}
              </Typography>
              <Typography variant="h5">{t("createTicket.title")}</Typography>
            </Box>
            <Button
              type="submit"
              variant="contained"
              color="inherit"
              disabled={
                saving ||
                !clients.data?.length ||
                formSettings.isLoading ||
                Boolean(workAssignmentId && !workAssignment.data)
              }
              sx={{
                bgcolor: "background.paper",
                color: "primary.main",
                flexShrink: 0,
                "&:hover": { bgcolor: "grey.100" },
              }}
              onClick={() => {
                completionMode.current = "close";
              }}
            >
              {saving
                ? t("createTicket.creating")
                : workAssignment.data
                  ? "Convert to ticket"
                  : t("createTicket.create")}
            </Button>
          </Stack>
          <Typography
            variant="body2"
            sx={{ mt: 0.5, maxWidth: 720, opacity: 0.88 }}
          >
            {t("createTicket.subtitle")}
          </Typography>
        </Box>
        {formSettings.isError && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t("createTicket.preferencesFailed")}
          </Alert>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {workAssignment.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            The work assignment could not be loaded or is outside your scope.
          </Alert>
        )}
        {workAssignment.data && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Creating this ticket will link it to work assignment #
            {workAssignment.data.id} and transfer KPI attribution to the ticket.
          </Alert>
        )}
        {selectedClient && !selectedClient.ticket_creation_allowed && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t("createTicket.clientRestricted")}
          </Alert>
        )}
        {reusedFromTicket && (
          <Alert
            severity="info"
            sx={{ mb: 2 }}
            action={
              <Button
                color="inherit"
                size="small"
                onClick={() => setReusedFromTicket(null)}
              >
                {t("createTicket.clear")}
              </Button>
            }
          >
            {t("createTicket.reusing", {
              number: reusedFromTicket.ticket_number,
            })}
          </Alert>
        )}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 340px" },
            gap: 2,
            alignItems: "start",
          }}
        >
          <Paper
            variant="outlined"
            sx={{
              p: { xs: 1.5, md: 2 },
              boxShadow: (theme) => `0 8px 24px ${theme.palette.action.hover}`,
            }}
          >
            <Typography variant="h6" gutterBottom>
              {t("createTicket.issueDetails")}
            </Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.25}>
              <SearchableSelect
                key={defaultTicketTypeId ?? "ticket-type-default"}
                required
                name="ticket_type_id"
                label={t("createTicket.ticketType")}
                options={types.data ?? []}
                defaultValueId={defaultTicketTypeId}
              />
              <SearchableSelect
                required
                name="client_id"
                label={t("createTicket.client")}
                options={clients.data ?? []}
                valueId={selectedClientId}
                getLabel={(raw) => {
                  const item = raw as Client;
                  return `${item.name} — ${t("createTicket.ticketCount", { count: item.ticket_count })}${item.ticket_creation_allowed ? "" : item.is_active ? ` — ${t("createTicket.ticketsRestricted")}` : ` — ${t("createTicket.inactive")}`}`;
                }}
                getOptionColor={(raw) =>
                  (raw as Client).is_active ? undefined : "#d32f2f"
                }
                onChange={(raw) => {
                  setSelectedClientId(raw?.id ?? null);
                  setSelectedProductId(null);
                  setSelectedCaller(null);
                  setSelectedBranchId(null);
                }}
              />
              <TextField
                size="small"
                select
                required
                name="source_channel"
                label={t("createTicket.origin")}
                fullWidth
                defaultValue="WEB"
              >
                <MenuItem value="WEB">{t("createTicket.originWeb")}</MenuItem>
                <MenuItem value="PHONE">
                  {t("createTicket.originPhone")}
                </MenuItem>
                <MenuItem value="EMAIL">
                  {t("createTicket.originEmail")}
                </MenuItem>
                <MenuItem value="WALK_IN">
                  {t("createTicket.originWalkIn")}
                </MenuItem>
                <MenuItem value="MONITORING">
                  {t("createTicket.originMonitoring")}
                </MenuItem>
                <MenuItem value="OTHER">{t("createTicket.other")}</MenuItem>
              </TextField>
            </Stack>
            <TextField
              required
              name="subject"
              label={t("createTicket.subject")}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 5 }}
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              helperText={t("createTicket.keywordSuggestionsHint", {
                defaultValue:
                  "Type at least 3 characters for templates, or end with * to search similar tickets.",
              })}
            />
            {templateTriggered && !!ticketTemplates.data?.length && (
              <Alert severity="info" sx={{ mb: 1 }}>
                <Typography fontWeight={700}>
                  {t("createTicket.approvedTemplates", {
                    defaultValue: "Approved ticket templates",
                  })}
                </Typography>
                <Stack alignItems="flex-start">
                  {ticketTemplates.data.map((template) => (
                    <Button
                      key={template.id}
                      size="small"
                      onClick={() => applyTicketTemplate(template)}
                    >
                      {template.name} — {template.subject}
                    </Button>
                  ))}
                </Stack>
              </Alert>
            )}
            {similarityTriggered && similarTickets.isFetching && (
              <Typography variant="body2" color="text.secondary">
                {t("createTicket.checkingSimilar")}
              </Typography>
            )}
            {similarityTriggered &&
              !similarTickets.isFetching &&
              similarTickets.data?.length === 0 && (
                <Alert severity="success" sx={{ mb: 1 }}>
                  {t("createTicket.noSimilar")}
                </Alert>
              )}
            {similarityTriggered &&
              !!orderedSimilarTickets.length &&
              selectedSimilar && (
                <Alert severity="warning" sx={{ mb: 1 }}>
                  <Typography fontWeight={600}>
                    {t("createTicket.similarFound")}
                  </Typography>
                  <TextField
                    select
                    size="small"
                    fullWidth
                    label={t("createTicket.similarCount", {
                      count: orderedSimilarTickets.length,
                    })}
                    value={selectedSimilar.id}
                    onChange={(event) =>
                      setSelectedSimilarId(Number(event.target.value))
                    }
                    sx={{ mt: 1, mb: 1 }}
                  >
                    {orderedSimilarTickets.map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        {item.ticket_number} — {item.subject}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography fontWeight={600}>
                      {selectedSimilar.ticket_number} —{" "}
                      {selectedSimilar.subject}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {selectedSimilar.description.length > 180
                        ? `${selectedSimilar.description.slice(0, 180)}…`
                        : selectedSimilar.description}
                    </Typography>
                    <Stack direction="row" spacing={1} mt={1}>
                      <Button
                        size="small"
                        onClick={() =>
                          navigate(`/tickets/${selectedSimilar.id}`)
                        }
                      >
                        {t("createTicket.viewTicket")}
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => reuseTicketDetails(selectedSimilar)}
                      >
                        {t("createTicket.reuseDetails")}
                      </Button>
                    </Stack>
                  </Paper>
                </Alert>
              )}
            <TextField
              required
              name="description"
              label={t("createTicket.description")}
              fullWidth
              multiline
              rows={4}
              margin="dense"
              inputProps={{ minLength: 10 }}
            />
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              alignItems={{ sm: "center" }}
              sx={{ mb: 1 }}
            >
              <Button
                variant="outlined"
                onClick={analyzeWithLocalAi}
                disabled={aiLoading}
              >
                {aiLoading
                  ? "Analyzing with local AI…"
                  : "Improve and classify with local AI"}
              </Button>
              <Typography variant="caption" color="text.secondary">
                Suggestions are applied to the form for your review; nothing is
                saved automatically.
              </Typography>
            </Stack>
            {aiError && (
              <Alert severity="error" sx={{ mb: 1 }}>
                {aiError}
              </Alert>
            )}
            {aiSuggestion &&
              (aiSuggestion.missing_information.length > 0 ||
                aiSuggestion.suggested_actions.length > 0) && (
                <Alert severity="info" sx={{ mb: 1 }}>
                  {aiSuggestion.missing_information.length > 0 && (
                    <Typography variant="body2">
                      <strong>Missing information:</strong>{" "}
                      {aiSuggestion.missing_information.join(" · ")}
                    </Typography>
                  )}
                  {aiSuggestion.suggested_actions.length > 0 && (
                    <Typography variant="body2">
                      <strong>Suggested checks:</strong>{" "}
                      {aiSuggestion.suggested_actions.join(" · ")}
                    </Typography>
                  )}
                </Alert>
              )}

            {(isVisible("product_id") || isVisible("product_module_id")) && (
              <Stack direction={{ xs: "column", md: "row" }} spacing={2} mt={1}>
                {isVisible("product_id") && (
                  <SearchableSelect
                    required={isRequired("product_id")}
                    name="product_id"
                    label={t("createTicket.contractProduct")}
                    options={products}
                    valueId={selectedProductId}
                    getLabel={(item) =>
                      `${getLocalizedName(item, language)} — ${t(item.covered ? "createTicket.included" : "createTicket.notIncluded")}`
                    }
                    disabled={!selectedClientId || contractCatalog.isLoading}
                    onChange={(item) => {
                      setSelectedProductId(item?.id ?? null);
                      setSelectedModuleId(null);
                      setSelectedContractId(null);
                    }}
                  />
                )}
                {isVisible("product_module_id") && (
                  <SearchableSelect
                    key={`${selectedClientId ?? "no-client"}-${selectedProductId ?? "no-product"}`}
                    required={isRequired("product_module_id")}
                    name="product_module_id"
                    label={t("createTicket.contractModule")}
                    options={modules}
                    getLabel={(item) =>
                      `${getLocalizedName(item, language)} — ${t(item.covered ? "createTicket.included" : "createTicket.notIncluded")}`
                    }
                    disabled={!selectedProductId}
                    onChange={(item) => setSelectedModuleId(item?.id ?? null)}
                  />
                )}
              </Stack>
            )}
            {(isVisible("category_id") || isVisible("subcategory_id")) && (
              <Stack direction={{ xs: "column", md: "row" }} spacing={2} mt={2}>
                {isVisible("category_id") && (
                  <SearchableSelect
                    required={isRequired("category_id")}
                    name="category_id"
                    label={t("createTicket.category")}
                    options={categories.data ?? []}
                    valueId={selectedCategoryId}
                    onChange={(item) => setSelectedCategoryId(item?.id ?? null)}
                  />
                )}
                {isVisible("subcategory_id") && (
                  <SearchableSelect
                    key={selectedCategoryId ?? "no-category"}
                    required={isRequired("subcategory_id")}
                    name="subcategory_id"
                    label={t("createTicket.subcategory")}
                    options={subcategories.data ?? []}
                    disabled={!selectedCategoryId}
                  />
                )}
              </Stack>
            )}
            {(isVisible("service_id") || isVisible("environment_id")) && (
              <Stack direction={{ xs: "column", md: "row" }} spacing={2} mt={2}>
                {isVisible("service_id") && (
                  <SearchableSelect
                    key={selectedClientId ?? "no-client-service"}
                    required={isRequired("service_id")}
                    name="service_id"
                    label={t("createTicket.contractService")}
                    options={services}
                    getLabel={(item) =>
                      `${getLocalizedName(item, language)} — ${t(item.covered ? "createTicket.included" : "createTicket.notIncluded")}`
                    }
                    disabled={!selectedClientId || contractCatalog.isLoading}
                    onChange={(item) => setSelectedServiceId(item?.id ?? null)}
                  />
                )}
                {isVisible("environment_id") && (
                  <SearchableSelect
                    required={isRequired("environment_id")}
                    name="environment_id"
                    label={t("createTicket.environment")}
                    options={environments.data ?? []}
                  />
                )}
              </Stack>
            )}
            {contractCandidates.data?.length === 1 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                {t("createTicket.contract")}:{" "}
                {contractCandidates.data[0].contract_number} —{" "}
                {contractCandidates.data[0].contract_name}.{" "}
                {contractCandidates.data[0].reason}
              </Alert>
            )}
            {(contractCandidates.data?.length ?? 0) > 1 && (
              <TextField
                select
                required
                label={t("createTicket.agreedContract")}
                value={selectedContractId ?? ""}
                onChange={(event) =>
                  setSelectedContractId(Number(event.target.value))
                }
                fullWidth
                margin="normal"
                helperText={t("createTicket.contractHint")}
              >
                <MenuItem value="">{t("createTicket.selectContract")}</MenuItem>
                {contractCandidates.data?.map((item) => (
                  <MenuItem key={item.contract_id} value={item.contract_id}>
                    {item.contract_number} — {item.contract_name} (
                    {item.contract_type ?? t("createTicket.general")}) ·{" "}
                    {t("createTicket.expires")} {item.end_date}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {contractCandidates.data &&
              !contractCandidates.data.length &&
              selectedProductId &&
              selectedServiceId && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  {t("createTicket.noContract")}
                </Alert>
              )}
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} mt={2}>
              <TextField
                select
                required
                name="impact"
                label={t("createTicket.impact")}
                fullWidth
                defaultValue="MEDIUM"
              >
                {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => (
                  <MenuItem key={item} value={item}>
                    {t(`createTicket.${item.toLowerCase()}`)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                required
                name="urgency"
                label={t("createTicket.urgency")}
                fullWidth
                defaultValue="MEDIUM"
              >
                {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => (
                  <MenuItem key={item} value={item}>
                    {t(`createTicket.${item.toLowerCase()}`)}
                  </MenuItem>
                ))}
              </TextField>
              {isVisible("priority") && (
                <TextField
                  select
                  name="priority"
                  label={t("createTicket.priority")}
                  fullWidth
                  defaultValue="P3"
                >
                  <MenuItem value="P1">
                    P1 — {t("createTicket.critical")}
                  </MenuItem>
                  <MenuItem value="P2">P2 — {t("createTicket.high")}</MenuItem>
                  <MenuItem value="P3">
                    P3 — {t("createTicket.medium")}
                  </MenuItem>
                  <MenuItem value="P4">P4 — {t("createTicket.low")}</MenuItem>
                </TextField>
              )}
            </Stack>
            {isVisible("affected_users") && (
              <TextField
                required={isRequired("affected_users")}
                name="affected_users"
                label={t("createTicket.affectedUsers")}
                fullWidth
                margin="normal"
              />
            )}
            {isVisible("first_occurred_at") && (
              <TextField
                required={isRequired("first_occurred_at")}
                type="datetime-local"
                name="first_occurred_at"
                label={t("createTicket.firstOccurred")}
                fullWidth
                margin="normal"
                slotProps={{ inputLabel: { shrink: true } }}
              />
            )}
            {(isVisible("patient_safety_flag") ||
              isVisible("security_incident_flag")) && (
              <Stack direction={{ xs: "column", md: "row" }} spacing={2} mt={1}>
                {isVisible("patient_safety_flag") && (
                  <TextField
                    select
                    name="patient_safety_flag"
                    label={t("createTicket.patientSafety")}
                    fullWidth
                    defaultValue="false"
                  >
                    <MenuItem value="false">{t("createTicket.no")}</MenuItem>
                    <MenuItem value="true">{t("createTicket.yes")}</MenuItem>
                  </TextField>
                )}
                {isVisible("security_incident_flag") && (
                  <TextField
                    select
                    name="security_incident_flag"
                    label={t("createTicket.securityIncident")}
                    fullWidth
                    defaultValue="false"
                  >
                    <MenuItem value="false">{t("createTicket.no")}</MenuItem>
                    <MenuItem value="true">{t("createTicket.yes")}</MenuItem>
                  </TextField>
                )}
              </Stack>
            )}
          </Paper>

          {mobile && additionalOpen && (
            <Box
              aria-hidden
              onClick={() => setAdditionalOpen(false)}
              sx={{
                position: "fixed",
                inset: 0,
                bgcolor: "rgba(15,23,42,.48)",
                zIndex: 1299,
              }}
            />
          )}
          <Paper
            data-additional-fields
            variant="outlined"
            sx={{
              p: { xs: 2, md: 1.75 },
              position: { xs: "fixed", md: "sticky" },
              insetInline: { xs: 8, md: "auto" },
              bottom: { xs: 72, md: "auto" },
              top: { xs: 72, md: 80 },
              zIndex: { xs: 1300, md: "auto" },
              overflowY: { xs: "auto", md: "visible" },
              transform: {
                xs: additionalOpen
                  ? "translateY(0)"
                  : "translateY(calc(100% + 96px))",
                md: "none",
              },
              transition: "transform .22s ease",
              boxShadow: { xs: 12, md: 0 },
              borderRadius: { xs: 3, md: 1 },
            }}
          >
            <Stack direction="row" alignItems="center">
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                {t("createTicket.additionalInformation")}
              </Typography>
              {mobile && (
                <Button onClick={() => setAdditionalOpen(false)}>
                  {t("common.close", { defaultValue: "Close" })}
                </Button>
              )}
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t("createTicket.additionalSubtitle")}
            </Typography>
            {isVisible("requester_contact_id") && (
              <>
                <Autocomplete
                  fullWidth
                  options={
                    contacts.data?.filter((contact) => contact.is_active) ?? []
                  }
                  value={selectedCaller}
                  onChange={(_, caller) => setSelectedCaller(caller)}
                  getOptionLabel={(caller) =>
                    `${caller.full_name}${caller.phone_number ? ` — ${caller.phone_number}` : ""}`
                  }
                  isOptionEqualToValue={(option, value) =>
                    option.id === value.id
                  }
                  disabled={!selectedClientId}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      required={isRequired("requester_contact_id")}
                      label={t("createTicket.caller")}
                      placeholder={t("createTicket.callerPlaceholder")}
                    />
                  )}
                  filterOptions={(options, state) => {
                    const term = state.inputValue.toLowerCase();
                    return options.filter((caller) =>
                      `${caller.full_name} ${caller.phone_number ?? ""} ${caller.email ?? ""} ${caller.job_title ?? ""}`
                        .toLowerCase()
                        .includes(term),
                    );
                  }}
                />
                {(hasPermission("contact.manage") ||
                  hasPermission("contact.link_existing")) && (
                  <Button
                    size="small"
                    sx={{ mt: 1 }}
                    disabled={!selectedClientId}
                    onClick={() => {
                      setCallerError("");
                      setNewCallerOpen(true);
                    }}
                  >
                    {t("createTicket.addCaller")}
                  </Button>
                )}
                {selectedCaller && (
                  <Paper
                    variant="outlined"
                    sx={{ p: 1.25, mt: 1, bgcolor: "action.hover" }}
                  >
                    <Typography fontWeight={600}>
                      {selectedCaller.full_name}
                    </Typography>
                    <Typography variant="caption">
                      {selectedCaller.phone_number ??
                        t("createTicket.noMobile")}{" "}
                      · {selectedCaller.email ?? t("createTicket.noEmail")}
                    </Typography>
                  </Paper>
                )}
                {selectedCaller && !!callerHistory.data?.length && (
                  <TextField
                    select
                    size="small"
                    fullWidth
                    label={t("createTicket.recentCallerTickets")}
                    value=""
                    onChange={(event) =>
                      navigate(`/tickets/${event.target.value}`)
                    }
                    sx={{ mt: 1 }}
                  >
                    <MenuItem value="" disabled>
                      {t("createTicket.recentCallerTickets")}
                    </MenuItem>
                    {callerHistory.data.map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        {item.ticket_number} — {item.subject}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              </>
            )}
            {isVisible("branch_id") && (
              <>
                <SearchableSelect
                  required={isRequired("branch_id")}
                  name="branch_id"
                  label={t("createTicket.branchSite")}
                  options={
                    branches.data?.filter((item) => item.is_active) ?? []
                  }
                  valueId={selectedBranchId}
                  onChange={(item) => setSelectedBranchId(item?.id ?? null)}
                  disabled={!selectedClientId}
                  emptyLabel={t("createTicket.clientWide")}
                  margin="normal"
                />
                {hasPermission("client.manage") && (
                  <Button
                    size="small"
                    disabled={!selectedClientId}
                    onClick={() => setBranchOpen(true)}
                  >
                    {t("createTicket.createBranchForClient")}
                  </Button>
                )}
              </>
            )}
            {isVisible("assigned_team") && (
              <>
                <input
                  type="hidden"
                  name="assigned_team"
                  value={selectedTeam?.name ?? ""}
                />
                <Autocomplete
                  fullWidth
                  options={teams.data ?? []}
                  value={selectedTeam}
                  onChange={(_, item) => setSelectedTeam(item)}
                  getOptionLabel={(item) => item.name}
                  isOptionEqualToValue={(option, value) =>
                    option.id === value.id
                  }
                  noOptionsText={t("createTicket.noMatchingTeams")}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={t("createTicket.assignTeam")}
                      margin="normal"
                      placeholder={t("createTicket.searchTeams")}
                      helperText={
                        !selectedTeam ? t("createTicket.noTeam") : undefined
                      }
                    />
                  )}
                />
              </>
            )}
            {isVisible("assigned_user_id") && (
              <>
                <input
                  type="hidden"
                  name="assigned_user_id"
                  value={selectedAssignee?.id ?? ""}
                />
                <Autocomplete
                  fullWidth
                  options={assignees.data ?? []}
                  value={selectedAssignee}
                  onChange={(_, item) => setSelectedAssignee(item)}
                  getOptionLabel={(item) =>
                    `${item.full_name} — ${item.job_title ?? item.department ?? item.username}`
                  }
                  isOptionEqualToValue={(option, value) =>
                    option.id === value.id
                  }
                  noOptionsText={t("createTicket.noMatchingEngineers")}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={t("createTicket.assignEngineer")}
                      margin="normal"
                      placeholder={t("createTicket.searchEngineers")}
                      helperText={
                        !selectedAssignee
                          ? t("createTicket.leaveUnassigned")
                          : undefined
                      }
                    />
                  )}
                  filterOptions={(options, state) => {
                    const term = state.inputValue.toLowerCase();
                    return options.filter((item) =>
                      `${item.full_name} ${item.username} ${item.department ?? ""} ${item.job_title ?? ""}`
                        .toLowerCase()
                        .includes(term),
                    );
                  }}
                />
              </>
            )}
            {isVisible("follower_user_ids") && (
              <MobileMultiAutocomplete
                options={assignees.data ?? []}
                value={selectedFollowers}
                onChange={(_, value) => setSelectedFollowers(value)}
                getOptionLabel={(item) =>
                  `${item.full_name} — ${item.username}`
                }
                isOptionEqualToValue={(option, value) => option.id === value.id}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label={t("createTicket.followers")}
                    margin="normal"
                    helperText={t("createTicket.followersHint")}
                  />
                )}
              />
            )}
          </Paper>
        </Box>
        <Box mt={2}>
          <Button component="label" variant="outlined" disabled={saving}>
            Add initial attachments
            <input
              hidden
              type="file"
              multiple
              onChange={(event) =>
                setInitialAttachments(Array.from(event.target.files ?? []))
              }
            />
          </Button>
          {initialAttachments.length > 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {initialAttachments.map((file) => file.name).join(", ")}
            </Typography>
          )}
        </Box>
        <Stack
          direction="row"
          justifyContent="flex-end"
          spacing={1}
          mt={2}
          sx={{
            position: { xs: "fixed", md: "sticky" },
            insetInline: { xs: 0, md: "auto" },
            bottom: 0,
            // Keep the frozen actions above form content, but below MUI menus,
            // dialogs, and the mobile additional-information drawer.
            zIndex: { xs: 1200, md: 10 },
            bgcolor: "background.paper",
            borderTop: 1,
            borderColor: "divider",
            p: 1,
            boxShadow: "0 -8px 24px rgba(15,23,42,.12)",
          }}
        >
          <Button onClick={goBack}>{t("createTicket.cancel")}</Button>
          {mobile && (
            <Button variant="outlined" onClick={() => setAdditionalOpen(true)}>
              {t("createTicket.additionalInformation")}
            </Button>
          )}
          {!workAssignmentId && (
            <Button
              type="submit"
              variant="outlined"
              disabled={
                saving || !clients.data?.length || formSettings.isLoading
              }
              onClick={() => {
                completionMode.current = "new";
              }}
            >
              {saving && completionMode.current === "new"
                ? t("createTicket.creating")
                : t("createTicket.createAndNew")}
            </Button>
          )}
          <Button
            type="submit"
            variant="contained"
            disabled={
              saving ||
              !clients.data?.length ||
              formSettings.isLoading ||
              Boolean(workAssignmentId && !workAssignment.data)
            }
            onClick={() => {
              completionMode.current = "close";
            }}
          >
            {saving
              ? t("createTicket.creating")
              : workAssignment.data
                ? "Convert to ticket"
                : t("createTicket.create")}
          </Button>
        </Stack>
      </Paper>

      <Dialog
        open={Boolean(pendingInactiveTicket)}
        onClose={() => setPendingInactiveTicket(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t("createTicket.inactiveTitle")}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t("createTicket.inactiveWarning")}
          </Alert>
          <Typography>
            {t("createTicket.inactivePrompt", { client: selectedClient?.name })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setPendingInactiveTicket(null)}
            disabled={saving}
          >
            {t("createTicket.goBack")}
          </Button>
          <Button
            color="warning"
            variant="contained"
            disabled={saving}
            onClick={() => {
              const payload = pendingInactiveTicket;
              setPendingInactiveTicket(null);
              if (payload) void createTicket(payload, true);
            }}
          >
            {t("createTicket.confirmCreate")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(pendingEntitlementTicket)}
        onClose={() => setPendingEntitlementTicket(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t("createTicket.outOfContract")}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {pendingEntitlementTicket?.message}
          </Alert>
          <Typography sx={{ mb: 1 }}>
            {t("createTicket.approvalExplanation")}
          </Typography>
          <TextField
            autoFocus
            required
            label={t("createTicket.businessJustification")}
            value={entitlementReason}
            onChange={(event) => setEntitlementReason(event.target.value)}
            fullWidth
            multiline
            rows={3}
            inputProps={{ minLength: 5, maxLength: 500 }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setPendingEntitlementTicket(null);
              setEntitlementReason("");
            }}
            disabled={saving}
          >
            {t("createTicket.cancel")}
          </Button>
          <Button
            color="warning"
            variant="contained"
            disabled={saving || entitlementReason.trim().length < 5}
            onClick={() => {
              const pending = pendingEntitlementTicket;
              if (!pending) return;
              setPendingEntitlementTicket(null);
              const reason = entitlementReason.trim();
              setEntitlementReason("");
              void createTicket(
                {
                  ...pending.payload,
                  assigned_user_id: null,
                  assigned_team: null,
                  request_entitlement_approval: true,
                  entitlement_approval_justification: reason,
                  submission_idempotency_key: approvalSubmissionKey.current,
                },
                pending.inactiveConfirmed,
              );
            }}
          >
            {t("createTicket.createRequestApproval")}
          </Button>
          {hasPermission("contract.override_entitlement") && (
            <Button
              color="warning"
              variant="contained"
              disabled={saving || entitlementReason.trim().length < 5}
              onClick={() => {
                const pending = pendingEntitlementTicket;
                if (!pending) return;
                setPendingEntitlementTicket(null);
                const reason = entitlementReason.trim();
                setEntitlementReason("");
                void createTicket(
                  { ...pending.payload, entitlement_override_reason: reason },
                  pending.inactiveConfirmed,
                );
              }}
            >
              {t("createTicket.overrideCreate")}
            </Button>
          )}
        </DialogActions>
      </Dialog>
      <Dialog
        open={branchOpen}
        onClose={() => setBranchOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <Box component="form" onSubmit={createBranch}>
          <DialogTitle>
            {t("createTicket.createBranchTitle", {
              client: selectedClient?.name,
            })}
          </DialogTitle>
          <DialogContent>
            {branchError && (
              <Alert severity="error" sx={{ mb: 1 }}>
                {branchError}
              </Alert>
            )}
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("createTicket.branchCodeAutomatic")}
            </Alert>
            <TextField
              required
              name="name"
              label={t("createTicket.branchName")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="timezone"
              label={t("createTicket.timezoneOverride")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="address"
              label={t("createTicket.address")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setBranchOpen(false)}>
              {t("createTicket.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("createTicket.createSelect")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog
        open={newCallerOpen}
        onClose={() => setNewCallerOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <form onSubmit={createCaller}>
          <DialogTitle>
            {t("createTicket.addCallerTitle", { client: selectedClient?.name })}
          </DialogTitle>
          <DialogContent>
            {callerError && (
              <Alert severity="error" sx={{ mb: 1 }}>
                {callerError}
              </Alert>
            )}
            {hasPermission("contact.link_existing") && (
              <Paper variant="outlined" sx={{ p: 2, mt: 1, mb: 2 }}>
                <Typography fontWeight={700}>
                  {t("createTicket.findExistingCaller")}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 1 }}
                >
                  {t("createTicket.findExistingCallerHelp")}
                </Typography>
                <Autocomplete
                  options={existingCallers.data ?? []}
                  value={selectedExistingCaller}
                  inputValue={existingCallerSearch}
                  onInputChange={(_, value) => setExistingCallerSearch(value)}
                  onChange={(_, value) => setSelectedExistingCaller(value)}
                  getOptionLabel={(caller) =>
                    `${caller.full_name}${caller.phone_number ? ` — ${caller.phone_number}` : caller.email ? ` — ${caller.email}` : ""}`
                  }
                  isOptionEqualToValue={(option, value) =>
                    option.id === value.id
                  }
                  loading={existingCallers.isFetching}
                  noOptionsText={
                    deferredCallerSearch.length < 2
                      ? t("createTicket.existingCallerMinimum")
                      : t("createTicket.noExistingCaller")
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={t("createTicket.searchExistingCaller")}
                      placeholder={t("createTicket.callerPlaceholder")}
                    />
                  )}
                />
                <Button
                  type="button"
                  variant="outlined"
                  fullWidth
                  sx={{ mt: 1 }}
                  disabled={!selectedExistingCaller || callerSaving}
                  onClick={() => void linkExistingCaller()}
                >
                  {t("createTicket.linkSelectCaller")}
                </Button>
              </Paper>
            )}
            {hasPermission("contact.manage") && (
              <>
                <Typography fontWeight={700}>
                  {t("createTicket.createNewCaller")}
                </Typography>
                <TextField
                  required
                  name="full_name"
                  label={t("createTicket.callerName")}
                  fullWidth
                  margin="normal"
                  inputProps={{ minLength: 2 }}
                />
                <TextField
                  name="phone_number"
                  label={t("createTicket.mobileNumber")}
                  fullWidth
                  margin="normal"
                  inputProps={{ dir: "ltr" }}
                />
                <TextField
                  name="email"
                  type="email"
                  label={t("createTicket.email")}
                  fullWidth
                  margin="normal"
                  inputProps={{ dir: "ltr" }}
                />
                <TextField
                  name="job_title"
                  label={t("createTicket.jobTitle")}
                  fullWidth
                  margin="normal"
                />
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => setNewCallerOpen(false)}
              disabled={callerSaving}
            >
              {t("createTicket.cancel")}
            </Button>
            {hasPermission("contact.manage") && (
              <Button type="submit" variant="contained" disabled={callerSaving}>
                {callerSaving
                  ? t("createTicket.adding")
                  : t("createTicket.addSelectCaller")}
              </Button>
            )}
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
}
