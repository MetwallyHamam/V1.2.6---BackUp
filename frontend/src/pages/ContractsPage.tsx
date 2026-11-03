import {
  Add,
  Delete,
  Description,
  Groups,
  Inventory2,
  OpenInNew,
  Speed,
} from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
  MenuItem,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { ContractAssignmentWizard } from "./ContractAssignmentWizard";
import { ContractCatalogVisibilityCard } from "./ContractCatalogVisibilityCard";
import { ContractGovernanceCard } from "./ContractGovernanceCard";
import { ProductScopedSlaEditor } from "./ProductScopedSlaEditor";
import { ContractType } from "./ContractTypesPanel";
import { ContractRenewalsPanel } from "./ContractRenewalsPanel";
import { ContractFinancePanel } from "./ContractFinancePanel";
import { ContractVisitsPanel } from "./ContractVisitsPanel";
import { ContractClientBulkSelector } from "./ContractClientBulkSelector";
import { ContractCustomersCompact } from "./ContractCustomersCompact";
type Contract = {
  id: number;
  contract_number: string;
  client_id: number;
  contract_type_id?: number;
  linked_client_ids: number[];
  is_shared_default: boolean;
  applies_to_all_clients: boolean;
  name: string;
  status: string;
  start_date: string;
  end_date: string;
  renewal_notice_date?: string;
  timezone: string;
  calendar_id: number;
  sla_policy_id?: number;
  has_sla: boolean;
  ticket_catalog_visibility: "CONTRACT_ONLY" | "ALL_WITH_COVERAGE_STATUS";
  require_product_on_ticket: boolean;
  require_module_on_ticket: boolean;
  require_service_on_ticket: boolean;
  coverage_validation_level: "CONTRACT" | "PRODUCT" | "PRODUCT_MODULE" | "FULL";
  expiry_grace_days: number;
  approval_group_id?: number;
  support_summary?: string;
  included_request_limit?: number;
  exclusions?: string;
  escalation_contact_id?: number;
  is_active: boolean;
  updated_at?: string;
};
type Catalog = {
  id: number;
  code?: string;
  name: string;
  name_ar?: string;
  product_id?: number;
};
type Contact = {
  id: number;
  full_name: string;
  is_active: boolean;
  is_escalation_contact: boolean;
};
type Coverage = {
  id: number;
  product_id?: number;
  product_module_id?: number;
  branch_id?: number;
  environment_id?: number;
  service_id?: number;
  ticket_type_id?: number;
  is_covered: boolean;
  notes?: string;
  applies_to_all_clients: boolean;
  client_ids: number[];
  effective_from?: string;
  effective_until?: string;
  retired_at?: string;
  retirement_reason?: string;
  current_revision: number;
};
type ContractDocument = {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};
type SlaTarget = {
  id: number;
  policy_id: number;
  product_id?: number;
  product_module_id?: number;
  service_id?: number;
  priority: string;
  first_response_minutes: number;
  resolution_minutes: number;
  warning_percent: number;
  is_fallback: boolean;
  effective_from?: string;
  effective_until?: string;
  context_key: string;
  version: number;
};
type ContractSla = {
  id: number;
  code: string;
  name: string;
  contract_id: number;
  calendar_id: number;
  is_active: boolean;
  include_escalation_time: boolean;
  targets: SlaTarget[];
};
type SlaPolicy = {
  id: number;
  code: string;
  name: string;
  calendar_id: number;
  is_active: boolean;
  include_escalation_time: boolean;
  targets: SlaTarget[];
};
type ContractUsage = {
  included_request_limit?: number;
  used_requests: number;
  remaining_requests?: number;
  overridden_requests: number;
  total_primary_requests: number;
};
type CalendarSchedule = {
  id: number;
  code: string;
  name: string;
  timezone: string;
  days: Array<{
    id: number;
    weekday: number;
    start_time: string;
    end_time: string;
    is_working_day: boolean;
  }>;
};
type WorkspaceTab =
  | "overview"
  | "customers"
  | "coverage"
  | "renewals"
  | "sla"
  | "visits"
  | "finance"
  | "documents";
const statusOptions = ["DRAFT", "ACTIVE", "SUSPENDED", "EXPIRED", "TERMINATED"];
export function ContractsPage({ embedded = false }: { embedded?: boolean }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Contract | null>(null);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("overview");
  const [editingSlaTarget, setEditingSlaTarget] = useState<SlaTarget | null>(null);
  const [slaTargetFormKey, setSlaTargetFormKey] = useState(0);
  const [productId, setProductId] = useState("");
  const [createSharedDefault, setCreateSharedDefault] = useState(false);
  const [createClientIds, setCreateClientIds] = useState<number[]>([]);
  const [linkedClientIds, setLinkedClientIds] = useState<number[]>([]);
  const [sharedDefault, setSharedDefault] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [customerLinkError, setCustomerLinkError] = useState("");
  const [coverageRemoval, setCoverageRemoval] = useState<Coverage | null>(null);
  const [coverageRemovalIds, setCoverageRemovalIds] = useState<number[]>([]);
  const closingContractId = useRef<number | null>(null);
  useEffect(() => {
    if (selected) {
      setLinkedClientIds(
        selected.linked_client_ids?.length
          ? selected.linked_client_ids
          : [selected.client_id],
      );
      setSharedDefault(selected.is_shared_default);
    }
  }, [selected]);
  const contractFilters = searchParams.toString();
  const contracts = useQuery({
    queryKey: ["contracts", contractFilters],
    queryFn: async () =>
      (
        await api.get<Contract[]>("/contracts", {
          params: {
            status: searchParams.get("status") || undefined,
            expires_within: searchParams.get("expires_within") || undefined,
            renewal_missing:
              searchParams.get("renewal_missing") === "true" || undefined,
          },
        })
      ).data,
  });
  useEffect(() => {
    const requestedContractId = Number(searchParams.get("contract_id"));
    if (!requestedContractId) {
      closingContractId.current = null;
      return;
    }
    if (
      closingContractId.current === requestedContractId ||
      selected ||
      !contracts.data
    )
      return;
    const contract = contracts.data.find(
      (item) => item.id === requestedContractId,
    );
    if (!contract) return;
    const requestedTab = searchParams.get("tab");
    const allowedTabs: WorkspaceTab[] = [
      "overview",
      "customers",
      "finance",
      "coverage",
      "renewals",
      "sla",
      "visits",
      "documents",
    ];
    setSelected(contract);
    setWorkspaceTab(
      allowedTabs.includes(requestedTab as WorkspaceTab)
        ? (requestedTab as WorkspaceTab)
        : "overview",
    );
  }, [contracts.data, searchParams, selected]);
  const renewals = useQuery({
    queryKey: ["contract-renewals"],
    queryFn: async () =>
      (
        await api.get<Contract[]>("/contracts/renewals/upcoming", {
          params: { days: 90 },
        })
      ).data,
  });
  const clients = useQuery({
    queryKey: ["clients", "contract-link-catalog"],
    queryFn: async () =>
      (
        await api.get<Catalog[]>("/clients", {
          params: { active_only: false, limit: 200 },
        })
      ).data,
    enabled: open || Boolean(selected),
  });
  const linkedClients = useQuery({
    queryKey: ["contract-linked-clients", selected?.id],
    queryFn: async () =>
      (await api.get<Catalog[]>(`/contracts/${selected?.id}/clients`)).data,
    enabled: Boolean(selected),
  });
  const knownClients = Array.from(
    new Map(
      [...(linkedClients.data ?? []), ...(clients.data ?? [])].map((client) => [
        client.id,
        client,
      ]),
    ).values(),
  );
  const calendars = useQuery({
    queryKey: ["business-calendars"],
    queryFn: async () => (await api.get<Catalog[]>("/business-calendars")).data,
  });
  const approvalGroups = useQuery({
    queryKey: ["contract-approval-group-options"],
    queryFn: async () =>
      (await api.get<Catalog[]>("/contracts/options/approval-groups")).data,
    enabled: hasPermission("contract.manage") && (open || Boolean(selected)),
  });
  const contractTypes = useQuery({
    queryKey: ["contract-types"],
    queryFn: async () =>
      (
        await api.get<ContractType[]>("/contract-types", {
          params: { active_only: true },
        })
      ).data,
  });
  const localizeCatalog = (items: Catalog[]) =>
    items.map((item) => ({
      ...item,
      name: getLocalizedName(item, i18n.language),
    }));
  const products = useQuery({
    queryKey: ["products", i18n.language],
    queryFn: async () =>
      localizeCatalog((await api.get<Catalog[]>("/products")).data),
  });
  const modules = useQuery({
    queryKey: ["contract-modules", productId, i18n.language],
    queryFn: async () =>
      localizeCatalog(
        (await api.get<Catalog[]>(`/products/${productId}/modules`)).data,
      ),
    enabled: Boolean(productId),
  });
  const coverageModules = useQuery({
    queryKey: [
      "contract-coverage-modules",
      products.data?.map((item) => item.id),
      i18n.language,
    ],
    queryFn: async () => {
      const responses = await Promise.all(
        (products.data ?? []).map((item) =>
          api.get<Catalog[]>(`/products/${item.id}/modules`),
        ),
      );
      return localizeCatalog(responses.flatMap((response) => response.data));
    },
    enabled: Boolean(selected && products.data?.length),
  });
  const services = useQuery({
    queryKey: ["services", i18n.language],
    queryFn: async () =>
      localizeCatalog((await api.get<Catalog[]>("/services")).data),
  });
  const ticketTypes = useQuery({
    queryKey: ["ticket-types", i18n.language],
    queryFn: async () =>
      localizeCatalog((await api.get<Catalog[]>("/ticket-types")).data),
  });
  const environments = useQuery({
    queryKey: ["environments", i18n.language],
    queryFn: async () =>
      localizeCatalog((await api.get<Catalog[]>("/environments")).data),
  });
  const branches = useQuery({
    queryKey: ["contract-branches", selected?.id, linkedClientIds],
    queryFn: async () =>
      (await api.get<Catalog[]>(`/contracts/${selected?.id}/branches`))
        .data,
    enabled: Boolean(selected),
  });
  const contacts = useQuery({
    queryKey: ["contract-contacts", selected?.id, linkedClientIds],
    queryFn: async () =>
      (
        await api.get<Contact[]>(`/contracts/${selected?.id}/contacts`)
      ).data,
    enabled: Boolean(selected),
  });
  const coverage = useQuery({
    queryKey: ["contract-coverage", selected?.id],
    queryFn: async () =>
      (await api.get<Coverage[]>(`/contracts/${selected?.id}/coverage`)).data,
    enabled: Boolean(selected),
  });
  const documents = useQuery({
    queryKey: ["contract-documents", selected?.id],
    queryFn: async () =>
      (
        await api.get<ContractDocument[]>(
          `/contracts/${selected?.id}/documents`,
        )
      ).data,
    enabled: Boolean(selected),
  });
  const sla = useQuery({
    queryKey: ["contract-sla", selected?.id],
    queryFn: async () =>
      (await api.get<ContractSla | null>(`/contracts/${selected?.id}/sla`))
        .data,
    enabled: Boolean(selected),
  });
  const calendarSchedule = useQuery({
    queryKey: ["business-calendar-schedule", sla.data?.calendar_id],
    queryFn: async () =>
      (
        await api.get<CalendarSchedule>(
          `/business-calendars/${sla.data?.calendar_id}/schedule`,
        )
      ).data,
    enabled: Boolean(sla.data?.calendar_id),
  });
  const slaPolicies = useQuery({
    queryKey: ["sla-policies"],
    queryFn: async () => (await api.get<SlaPolicy[]>("/sla-policies")).data,
  });
  const slaCoveragePreview = useQuery({
    queryKey: ["contract-sla-coverage-preview", selected?.id, selected?.sla_policy_id],
    queryFn: async () => (await api.get<Array<{ coverage_id: number; product_id: number | null; service_id: number | null; priority: string; target_id: number | null; match_reason: string }>>(`/contracts/${selected?.id}/sla/coverage-preview`)).data,
    enabled: Boolean(selected?.id && selected?.sla_policy_id),
  });
  const usage = useQuery({
    queryKey: ["contract-usage", selected?.id],
    queryFn: async () =>
      (await api.get<ContractUsage>(`/contracts/${selected?.id}/usage`)).data,
    enabled: Boolean(selected),
  });
  const create = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post<Contract>("/contracts", payload),
    onSuccess: async (response) => {
      setOpen(false);
      setCreateClientIds([]);
      setWorkspaceTab("customers");
      setSelected(response.data);
      await queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });
  const deleteContract = useMutation({
    mutationFn: async (contract: Contract) =>
      api.delete(`/contracts/${contract.id}`),
    onSuccess: async () => {
      setDeleteError("");
      setSelected(null);
      await queryClient.invalidateQueries({ queryKey: ["contracts"] });
      await queryClient.invalidateQueries({ queryKey: ["contract-renewals"] });
    },
    onError: () => setDeleteError("deleteFailed"),
  });
  const updateStatus = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: string }) =>
      api.patch(`/contracts/${id}`, { status, is_active: status === "ACTIVE" }),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["contracts"] }),
  });
  const updateContract = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch<Contract>(`/contracts/${selected?.id}`, payload),
    onSuccess: async (response) => {
      setCustomerLinkError("");
      setSelected(response.data);
      setLinkedClientIds(response.data.linked_client_ids);
      await queryClient.invalidateQueries({ queryKey: ["contract-coverage", response.data.id] });
      await queryClient.invalidateQueries({ queryKey: ["contract-lifecycle-board"] });
      await queryClient.invalidateQueries({ queryKey: ["contracts"] });
      await queryClient.invalidateQueries({ queryKey: ["contract-renewals"] });
    },
    onError: () => setCustomerLinkError("customerLinksFailed"),
  });
  const notifyRenewals = useMutation({
    mutationFn: async () =>
      api.post("/contracts/renewals/notify", null, { params: { days: 90 } }),
  });
  const addCoverage = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/contracts/${selected?.id}/coverage`, payload),
    onSuccess: async () =>
      queryClient.invalidateQueries({
        queryKey: ["contract-coverage", selected?.id],
      }),
  });
  const removeCoverage = useMutation({
    mutationFn: async (ids: number[]) =>
      api.post(`/contracts/${selected?.id}/coverage/retire-batch`, {
        coverage_ids: ids,
        reason:
          "Selected product, module, and service coverage retired from the contract workspace.",
      }),
    onSuccess: async () => {
      setCoverageRemoval(null);
      setCoverageRemovalIds([]);
      await queryClient.invalidateQueries({
        queryKey: ["contract-coverage", selected?.id],
      });
    },
  });
  const uploadDocument = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("upload", file);
      return api.post(`/contracts/${selected?.id}/documents`, form);
    },
    onSuccess: async () =>
      queryClient.invalidateQueries({
        queryKey: ["contract-documents", selected?.id],
      }),
  });
  const removeDocument = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/contracts/${selected?.id}/documents/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({
        queryKey: ["contract-documents", selected?.id],
      }),
  });
  const saveSla = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.put<ContractSla>(`/contracts/${selected?.id}/sla`, payload),
    onSuccess: async (response) => {
      if (selected)
        setSelected({ ...selected, sla_policy_id: response.data.id });
      await queryClient.invalidateQueries({
        queryKey: ["contract-sla", selected?.id],
      });
      await queryClient.invalidateQueries({ queryKey: ["contract-sla-coverage-preview", selected?.id] });
    },
  });
  const unlinkSla = useMutation({
    mutationFn: async () => api.delete(`/contracts/${selected?.id}/sla`),
    onSuccess: async () => {
      setSelected((current) => current ? { ...current, sla_policy_id: undefined } : current);
      await queryClient.invalidateQueries({ queryKey: ["contract-sla", selected?.id] });
    },
  });
  const removeSlaTarget = useMutation({
    mutationFn: async (targetId: number) => api.delete(`/contracts/${selected?.id}/sla/targets/${targetId}`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["contract-sla", selected?.id] });
      await queryClient.invalidateQueries({ queryKey: ["contract-sla-coverage-preview", selected?.id] });
      const linked = (await api.get<ContractSla>(`/contracts/${selected?.id}/sla`)).data;
      setSelected((current) => current ? { ...current, sla_policy_id: linked.id } : current);
      await queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });
  const updateSlaPolicy = useMutation({
    mutationFn: async (policy: SlaPolicy) =>
      api.put(`/sla-policies/${policy.id}`, policy),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sla-policies"] });
      await queryClient.invalidateQueries({
        queryKey: ["contract-sla", selected?.id],
      });
    },
  });
  const saveSlaTarget = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/contracts/${selected?.id}/sla/targets`, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["contract-sla", selected?.id],
      });
      await queryClient.invalidateQueries({ queryKey: ["contract-sla-coverage-preview", selected?.id] });
      const linked = (await api.get<ContractSla>(`/contracts/${selected?.id}/sla`)).data;
      setSelected((current) => current ? { ...current, sla_policy_id: linked.id } : current);
      setEditingSlaTarget(null);
      setSlaTargetFormKey((value) => value + 1);
    },
  });
  const saveCalendarSchedule = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.put(`/business-calendars/${sla.data?.calendar_id}/schedule`, payload),
    onSuccess: async () =>
      queryClient.invalidateQueries({
        queryKey: ["business-calendar-schedule", sla.data?.calendar_id],
      }),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    create.mutate({
      ...data,
      contract_type_id: data.contract_type_id
        ? Number(data.contract_type_id)
        : null,
      linked_client_ids: createClientIds,
      is_shared_default: createSharedDefault,
      require_product_on_ticket: data.require_product_on_ticket === "on",
      require_module_on_ticket: data.require_module_on_ticket === "on",
      require_service_on_ticket: data.require_service_on_ticket === "on",
      coverage_validation_level: data.coverage_validation_level || "PRODUCT",
      expiry_grace_days: Number(data.expiry_grace_days || 0),
      approval_group_id: data.approval_group_id ? Number(data.approval_group_id) : null,
      calendar_id: Number(data.calendar_id),
      included_request_limit: data.included_request_limit
        ? Number(data.included_request_limit)
        : null,
      renewal_notice_date: data.renewal_notice_date || null,
      status: "ACTIVE",
      is_active: true,
    });
  }
  function submitContractEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    updateContract.mutate({
      name: String(data.name).trim(),
      status: data.status,
      start_date: data.start_date,
      end_date: data.end_date,
      renewal_notice_date: data.renewal_notice_date || null,
      timezone: String(data.timezone).trim(),
      calendar_id: Number(data.calendar_id),
      ticket_catalog_visibility: data.ticket_catalog_visibility,
      require_product_on_ticket: data.require_product_on_ticket === "on",
      require_module_on_ticket: data.require_module_on_ticket === "on",
      require_service_on_ticket: data.require_service_on_ticket === "on",
      coverage_validation_level: data.coverage_validation_level,
      expiry_grace_days: Number(data.expiry_grace_days || 0),
      approval_group_id: hasPermission("contract.manage") && data.approval_group_id !== undefined
        ? data.approval_group_id ? Number(data.approval_group_id) : null
        : selected?.approval_group_id ?? null,
      support_summary: String(data.support_summary).trim() || null,
      exclusions: String(data.exclusions).trim() || null,
      included_request_limit: data.included_request_limit
        ? Number(data.included_request_limit)
        : null,
      escalation_contact_id: data.escalation_contact_id
        ? Number(data.escalation_contact_id)
        : null,
      is_active: data.status === "ACTIVE",
    });
  }
  function submitCoverage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const numberOrNull = (value: FormDataEntryValue) =>
      value ? Number(value) : null;
    addCoverage.mutate({
      product_id: numberOrNull(data.product_id),
      product_module_id: numberOrNull(data.product_module_id),
      branch_id: numberOrNull(data.branch_id),
      environment_id: numberOrNull(data.environment_id),
      service_id: numberOrNull(data.service_id),
      ticket_type_id: numberOrNull(data.ticket_type_id),
      is_covered: data.is_covered === "true",
      notes: data.notes || null,
      effective_from: data.effective_from || selected?.start_date,
      effective_until: data.effective_until || selected?.end_date,
    });
    event.currentTarget.reset();
    setProductId("");
  }
  function submitSlaTarget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    saveSlaTarget.mutate({
      product_id: editingSlaTarget?.product_id ?? (data.product_id ? Number(data.product_id) : null),
      service_id: editingSlaTarget?.service_id ?? (data.service_id ? Number(data.service_id) : null),
      priority: editingSlaTarget?.priority ?? data.priority,
      first_response_minutes: Number(data.first_response_minutes),
      resolution_minutes: Number(data.resolution_minutes),
      warning_percent: Number(data.warning_percent),
      effective_from: data.effective_from || null,
      effective_until: data.effective_until || null,
    });
  }
  function submitCalendarSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    saveCalendarSchedule.mutate({
      timezone: String(form.get("timezone")),
      days: Array.from({ length: 7 }, (_, weekday) => ({
        weekday,
        start_time: String(form.get(`start_${weekday}`) || "08:00"),
        end_time: String(form.get(`end_${weekday}`) || "00:00"),
        is_working_day: form.get(`working_${weekday}`) === "on",
      })),
    });
  }
  const label = (items: Catalog[] | undefined, id?: number) =>
    id
      ? (items?.find((item) => item.id === id)?.name ?? `#${id}`)
      : t("contractsPage.any");
  const statusLabel = (status: string) =>
    t(`contractsPage.statuses.${status}`, {
      defaultValue: status.replaceAll("_", " "),
    });
  const linkedClientNames = (contract: Contract) => {
    const ids = contract.linked_client_ids?.length
      ? contract.linked_client_ids
      : [contract.client_id];
    return (
      <ContractCustomersCompact
        contractId={contract.id}
        total={new Set(ids).size}
        preview={ids.slice(0, 2).map((id) => label(knownClients, id))}
        allClients={contract.applies_to_all_clients}
      />
    );
  };
  const openWorkspace = (
    contract: Contract,
    tab: WorkspaceTab = "overview",
  ) => {
    closingContractId.current = null;
    setDeleteError("");
    setSelected(contract);
    setWorkspaceTab(tab);
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.set("contract_id", String(contract.id));
        next.set("tab", tab);
        return next;
      },
      { replace: true },
    );
  };
  const selectWorkspaceTab = (tab: WorkspaceTab) => {
    setWorkspaceTab(tab);
    if (selected)
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.set("contract_id", String(selected.id));
          next.set("tab", tab);
          return next;
        },
        { replace: true },
      );
  };
  const closeWorkspace = () => {
    closingContractId.current =
      selected?.id ?? (Number(searchParams.get("contract_id")) || null);
    setSelected(null);
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("contract_id");
        next.delete("tab");
        return next;
      },
      { replace: true },
    );
  };
  const confirmDeleteContract = () => {
    if (
      !selected ||
      !window.confirm(
        t("contractsPage.deleteConfirm", {
          number: selected.contract_number,
          name: selected.name,
        }),
      )
    )
      return;
    deleteContract.mutate(selected);
  };
  const removalCandidates = coverageRemoval
    ? (coverage.data ?? []).filter(
        (row) =>
          row.id === coverageRemoval.id ||
          (coverageRemoval.product_id &&
          !coverageRemoval.product_module_id &&
          !coverageRemoval.service_id
            ? row.product_id === coverageRemoval.product_id
            : coverageRemoval.product_module_id
              ? row.product_id === coverageRemoval.product_id &&
                row.product_module_id === coverageRemoval.product_module_id
              : false),
      )
    : [];
  const openCoverageRemoval = (row: Coverage) => {
    const related = (coverage.data ?? []).filter(
      (item) =>
        item.id === row.id ||
        (row.product_id && !row.product_module_id && !row.service_id
          ? item.product_id === row.product_id
          : row.product_module_id
            ? item.product_id === row.product_id &&
              item.product_module_id === row.product_module_id
            : false),
    );
    setCoverageRemoval(row);
    setCoverageRemovalIds(related.map((item) => item.id));
  };
  return (
    <Paper sx={{ p: { xs: 2, md: 3 } }}>
      <Stack
        direction={{ xs: "column", lg: "row" }}
        alignItems={{ lg: "center" }}
        gap={2}
        mb={3}
      >
        <Box flexGrow={1}>
          <Typography variant={embedded ? "h5" : "h4"} fontWeight={800}>
            {t(
              embedded
                ? "contractsPage.customerContracts"
                : "contractsPage.workspace",
            )}
          </Typography>
          <Typography color="text.secondary">
            {t("contractsPage.subtitle")}
          </Typography>
        </Box>
        {hasPermission("contract.manage") && (
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <Button onClick={() => notifyRenewals.mutate()}>
              {t("contractsPage.sendRenewals")}
            </Button>
            <Button
              variant="outlined"
              startIcon={<Add />}
              onClick={() => {
                setCreateSharedDefault(true);
                setOpen(true);
              }}
            >
              {t("contractsPage.addShared")}
            </Button>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => {
                setCreateSharedDefault(false);
                setOpen(true);
              }}
            >
              {t("contractsPage.addCustomer")}
            </Button>
          </Stack>
        )}
      </Stack>
      {!!renewals.data?.length && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {t("contractsPage.expiring", {
            count: renewals.data.length,
            date: new Date(renewals.data[0].end_date).toLocaleDateString(
              locale,
            ),
          })}
        </Alert>
      )}
      {notifyRenewals.isSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {t("contractsPage.renewalsQueued")}
        </Alert>
      )}
      {selected &&
        workspaceTab === "sla" &&
        hasPermission("contract.manage") && (
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              alignItems={{ md: "center" }}
              spacing={2}
            >
              <Box flexGrow={1}>
                <Typography fontWeight={800}>
                  {t("contractsPage.slaApplicability")}
                </Typography>
                <Typography color="text.secondary">
                  {t("contractsPage.slaApplicabilityHelp")}
                </Typography>
              </Box>
              <TextField
                select
                size="small"
                label={t("contractsPage.contractSla")}
                value={selected.has_sla ? "SLA" : "NO_SLA"}
                onChange={(event) =>
                  updateContract.mutate({
                    has_sla: event.target.value === "SLA",
                  })
                }
                sx={{ minWidth: 220 }}
              >
                <MenuItem value="SLA">{t("contractsPage.slaApplies")}</MenuItem>
                <MenuItem value="NO_SLA">{t("contractsPage.noSla")}</MenuItem>
              </TextField>
            </Stack>
          </Paper>
        )}
      {selected &&
        workspaceTab === "sla" &&
        sla.data &&
        hasPermission("contract.manage") && (
          <Paper
            variant="outlined"
            sx={{ p: 2, mb: 2, borderColor: "primary.main" }}
          >
            <Stack
              direction={{ xs: "column", md: "row" }}
              alignItems={{ md: "center" }}
              spacing={2}
            >
              <Box flexGrow={1}>
                <Typography fontWeight={800}>
                  {t("contractsPage.escalationTreatment")}
                </Typography>
                <Typography color="text.secondary">
                  {t("contractsPage.escalationTreatmentHelp")}
                </Typography>
              </Box>
              <TextField
                select
                size="small"
                label={t("contractsPage.escalationDuration")}
                value={sla.data.include_escalation_time ? "INCLUDE" : "EXCLUDE"}
                onChange={(event) => {
                  const policy = slaPolicies.data?.find(
                    (item) => item.id === sla.data?.id,
                  );
                  if (policy)
                    updateSlaPolicy.mutate({
                      ...policy,
                      include_escalation_time: event.target.value === "INCLUDE",
                    });
                }}
                sx={{ minWidth: 240 }}
              >
                <MenuItem value="INCLUDE">
                  {t("contractsPage.includeSla")}
                </MenuItem>
                <MenuItem value="EXCLUDE">
                  {t("contractsPage.excludeSla")}
                </MenuItem>
              </TextField>
            </Stack>
          </Paper>
        )}
      {contracts.isError && (
        <Alert severity="error">{t("contractsPage.loadFailed")}</Alert>
      )}
      {!contracts.isLoading && !contracts.data?.length && (
        <Alert severity="info">{t("contractsPage.empty")}</Alert>
      )}
      {!!contracts.data?.length && (
        <TableContainer>
          <Table sx={{ minWidth: 1050 }}>
            <TableHead>
              <TableRow>
                {[
                  "contract",
                  "customers",
                  "status",
                  "dates",
                  "requestLimit",
                  "configuration",
                ].map((column) => (
                  <TableCell key={column}>
                    {t(`contractsPage.columns.${column}`)}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {contracts.data.map((item) => (
                <TableRow hover key={item.id}>
                  <TableCell>
                    <Typography fontWeight={800}>
                      <span dir="ltr">{item.contract_number}</span>
                    </Typography>
                    <Typography>{item.name}</Typography>
                    {item.is_shared_default && (
                      <Chip
                        size="small"
                        color="info"
                        label={t("contractsPage.sharedDefault")}
                        sx={{ mt: 0.5 }}
                      />
                    )}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 280 }}>
                    {linkedClientNames(item)}
                  </TableCell>
                  <TableCell>
                    {hasPermission("contract.manage") ? (
                      <TextField
                        select
                        size="small"
                        value={item.status}
                        onChange={(event) =>
                          updateStatus.mutate({
                            id: item.id,
                            status: event.target.value,
                          })
                        }
                      >
                        {statusOptions.map((status) => (
                          <MenuItem key={status} value={status}>
                            {statusLabel(status)}
                          </MenuItem>
                        ))}
                      </TextField>
                    ) : (
                      <Chip
                        size="small"
                        color={item.is_active ? "success" : "default"}
                        label={statusLabel(item.status)}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    {new Date(item.start_date).toLocaleDateString(locale)}
                    <Typography variant="caption" display="block">
                      {t("contractsPage.to")}{" "}
                      {new Date(item.end_date).toLocaleDateString(locale)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {item.included_request_limit ??
                      t("contractsPage.unlimited")}
                  </TableCell>
                  <TableCell>
                    <Stack alignItems="flex-start">
                      <Button
                        variant="contained"
                        size="small"
                        endIcon={<OpenInNew />}
                        onClick={() => openWorkspace(item)}
                      >
                        {t("contractsPage.openWorkspace")}
                      </Button>
                      <Stack direction="row" mt={0.5}>
                        <Button
                          size="small"
                          onClick={() => openWorkspace(item, "coverage")}
                        >
                          {t("contractsPage.productsServices")}
                        </Button>
                        <Button
                          size="small"
                          onClick={() => openWorkspace(item, "sla")}
                        >
                          {t("contractsPage.sla")}
                        </Button>
                      </Stack>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <form onSubmit={submit}>
          <DialogTitle>
            {t(
              createSharedDefault
                ? "contractsPage.createShared"
                : "contractsPage.createCustomer",
            )}
          </DialogTitle>
          <DialogContent>
            {create.isError && (
              <Alert severity="error">{t("contractsPage.saveFailed")}</Alert>
            )}
            {clients.isError && (
              <Alert severity="error">{t("contractsPage.clientsFailed")}</Alert>
            )}
            <TextField
              required
              name="contract_number"
              label={t("contractsPage.contractNumber")}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              required
              name="name"
              label={t("contractsPage.contractName")}
              fullWidth
              margin="normal"
            />
            <TextField
              select
              name="contract_type_id"
              label={t("contractsPage.contractType")}
              fullWidth
              margin="normal"
              defaultValue=""
            >
              <MenuItem value="">{t("contractsPage.legacyBehavior")}</MenuItem>
              {contractTypes.data?.map((type) => (
                <MenuItem key={type.id} value={type.id}>
                  {type.name} —{" "}
                  {t("contractsPage.precedence", { value: type.precedence })}
                </MenuItem>
              ))}
            </TextField>
            <Autocomplete
              multiple
              options={clients.data ?? []}
              value={(clients.data ?? []).filter(client => createClientIds.includes(client.id))}
              getOptionLabel={client => client.name}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              onChange={(_, values) => setCreateClientIds(values.map(client => client.id))}
              disabled={clients.isLoading || clients.isError}
              renderInput={params => <TextField {...params} required={!createClientIds.length} label={t("contractsPage.contractClients")} margin="normal" helperText={t("contractsPage.equalClientsHelp")} />}
            />
            <TextField
              required
              select
              name="calendar_id"
              label={t("contractsPage.businessCalendar")}
              fullWidth
              margin="normal"
              defaultValue=""
            >
              {calendars.data?.map((x) => (
                <MenuItem key={x.id} value={x.id}>
                  {x.name}
                </MenuItem>
              ))}
            </TextField>
            <Stack direction="row" spacing={2}>
              <TextField
                required
                type="date"
                name="start_date"
                label={t("contractsPage.startDate")}
                fullWidth
                margin="normal"
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                required
                type="date"
                name="end_date"
                label={t("contractsPage.endDate")}
                fullWidth
                margin="normal"
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
            <TextField
              type="date"
              name="renewal_notice_date"
              label={t("contractsPage.renewalNotice")}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              type="number"
              name="included_request_limit"
              label={t("contractsPage.includedLimitBlank")}
              fullWidth
              margin="normal"
              inputProps={{ min: 1 }}
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <TextField select name="coverage_validation_level" label={t("contractsPage.coverageValidationLevel")} defaultValue="PRODUCT" fullWidth margin="normal">
                <MenuItem value="CONTRACT">{t("contractsPage.validationContract")}</MenuItem>
                <MenuItem value="PRODUCT">{t("contractsPage.validationProduct")}</MenuItem>
                <MenuItem value="PRODUCT_MODULE">{t("contractsPage.validationProductModule")}</MenuItem>
                <MenuItem value="FULL">{t("contractsPage.validationFull")}</MenuItem>
              </TextField>
              <TextField type="number" name="expiry_grace_days" label={t("contractsPage.expiryGraceDays")} defaultValue={0} inputProps={{ min: 0, max: 3650 }} fullWidth margin="normal" />
              {hasPermission("contract.manage")&&<TextField select name="approval_group_id" disabled={approvalGroups.isLoading || approvalGroups.isError} label={t("contractsPage.approvalGroup")} defaultValue="" fullWidth margin="normal"><MenuItem value="">{t("contractsPage.supportManagersDefault")}</MenuItem>{approvalGroups.data?.map(group=><MenuItem key={group.id} value={group.id}>{group.name}</MenuItem>)}</TextField>}
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }}>
              <FormControlLabel
                control={
                  <Checkbox name="require_product_on_ticket" defaultChecked />
                }
                label={t("contractsPage.requireProductOnTicket")}
              />
              <FormControlLabel
                control={<Checkbox name="require_module_on_ticket" />}
                label={t("contractsPage.requireModuleOnTicket")}
              />
              <FormControlLabel
                control={<Checkbox name="require_service_on_ticket" />}
                label={t("contractsPage.requireServiceOnTicket")}
              />
            </Stack>
            <TextField
              name="support_summary"
              label={t("contractsPage.coverageSummary")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <TextField
              name="exclusions"
              label={t("contractsPage.generalExclusions")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>
              {t("contractsPage.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={
                clients.isLoading || clients.isError || !clients.data?.length
              }
            >
              {t("contractsPage.saveConfigure")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Dialog
        open={Boolean(selected)}
        onClose={closeWorkspace}
        fullWidth
        maxWidth="xl"
      >
        <DialogTitle>
          <Stack
            direction={{ xs: "column", md: "row" }}
            alignItems={{ md: "center" }}
            gap={1}
          >
            <Box flexGrow={1}>
              <Typography variant="h5" fontWeight={800}>
                {selected?.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <span dir="ltr">{selected?.contract_number}</span> ·{" "}
                {selected && statusLabel(selected.status)}
              </Typography>
            </Box>
            {selected?.is_shared_default && (
              <Chip color="info" label={t("contractsPage.sharedDefault")} />
            )}
          </Stack>
        </DialogTitle>
        <Divider />
        <Tabs
          value={workspaceTab}
          onChange={(_, value: WorkspaceTab) => selectWorkspaceTab(value)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: 2 }}
          aria-label={t("contractsPage.workspaceSections")}
        >
          <Tab value="overview" label={t("contractsPage.overview")} />
          <Tab
            icon={<Groups />}
            iconPosition="start"
            value="customers"
            label={t("contractsPage.customersCount", {
              count: linkedClientIds.length,
            })}
          />
          <Tab value="finance" label={t("contractsPage.financials")} />
          <Tab
            icon={<Inventory2 />}
            iconPosition="start"
            value="coverage"
            label={t("contractsPage.productsCount", {
              count: coverage.data?.length ?? 0,
            })}
          />
          <Tab value="renewals" label={t("contractsPage.renewals")} />
          <Tab
            icon={<Speed />}
            iconPosition="start"
            value="sla"
            label={t("contractsPage.dynamicSla", {
              count: sla.data?.targets.length ?? 0,
            })}
          />
          {hasPermission("visit.entitlement.view") && (
            <Tab value="visits" label={t("contractsPage.visitEntitlements")} />
          )}
          <Tab
            icon={<Description />}
            iconPosition="start"
            value="documents"
            label={t("contractsPage.documentsCount", {
              count: documents.data?.length ?? 0,
            })}
          />
        </Tabs>
        <Divider />
        <DialogContent sx={{ minHeight: 520 }}>
          {deleteError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {t(`contractsPage.${deleteError}`)}
            </Alert>
          )}
          {workspaceTab === "overview" && selected && (
            <ContractGovernanceCard
              contract={selected}
              types={contractTypes.data ?? []}
              canManage={hasPermission("contract.manage")}
              onUpdated={(contract) =>
                setSelected((current) =>
                  current ? { ...current, ...contract } : current,
                )
              }
            />
          )}
          {workspaceTab === "overview" && (
            <ContractCatalogVisibilityCard
              contract={selected}
              canManage={hasPermission("contract.manage")}
              onSaved={(mode) => {
                setSelected((current) =>
                  current
                    ? { ...current, ticket_catalog_visibility: mode }
                    : current,
                );
                void queryClient.invalidateQueries({ queryKey: ["contracts"] });
              }}
            />
          )}
          {workspaceTab === "sla" && sla.data && selected && (
            <ProductScopedSlaEditor
              contractId={selected.id}
              targets={sla.data.targets}
              products={products.data ?? []}
              services={services.data ?? []}
              canManage={hasPermission("contract.manage")}
            />
          )}
          {workspaceTab === "coverage" &&
            selected &&
            hasPermission("contract.manage") && (
              <ContractAssignmentWizard
                contract={selected}
                onContractUpdated={(contract) => {
                  setSelected((current) =>
                    current ? { ...current, ...contract } : current,
                  );
                  void queryClient.invalidateQueries({
                    queryKey: ["contracts"],
                  });
                }}
                onSaved={async () => {
                  await queryClient.invalidateQueries({
                    queryKey: ["contract-coverage", selected.id],
                  });
                  await queryClient.invalidateQueries({
                    queryKey: ["contract-linked-clients", selected.id],
                  });
                }}
              />
            )}
          {workspaceTab === "renewals" && selected && (
            <ContractRenewalsPanel
              contractId={selected.id}
              coverage={coverage.data ?? []}
              canManage={hasPermission("contract.manage")}
            />
          )}
          {workspaceTab === "finance" &&
            selected &&
            (hasPermission("finance.view") ? (
              <ContractFinancePanel
                contractId={selected.id}
                canManage={hasPermission("finance.manage")}
              />
            ) : (
              <Alert severity="warning">
                {t("contractsPage.financePermission")}
              </Alert>
            ))}
          {workspaceTab === "visits" && selected && (
            <ContractVisitsPanel
              contractId={selected.id}
              clientIds={Array.from(
                new Set(linkedClientIds),
              )}
              canManage={hasPermission("visit.entitlement.manage")}
            />
          )}
          {workspaceTab === "overview" && (
            <Stack direction={{ xs: "column", sm: "row" }} gap={1.5} mb={2}>
              <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {t("contractsPage.includedUsed")}
                </Typography>
                <Typography variant="h4" fontWeight={800}>
                  {usage.data?.used_requests ?? "—"}
                  {usage.data?.included_request_limit
                    ? ` / ${usage.data.included_request_limit}`
                    : ""}
                </Typography>
              </Paper>
              <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {t("contractsPage.remainingAllowance")}
                </Typography>
                <Typography variant="h4" fontWeight={800}>
                  {usage.data?.remaining_requests ??
                    t("contractsPage.unlimited")}
                </Typography>
              </Paper>
              <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {t("contractsPage.approvedOverrides")}
                </Typography>
                <Typography variant="h4" fontWeight={800}>
                  {usage.data?.overridden_requests ?? "—"}
                </Typography>
              </Paper>
            </Stack>
          )}
          {workspaceTab === "overview" && selected && (
            <Box>
              {hasPermission("contract.manage") ? (
                <Paper
                  component="form"
                  key={`contract-${selected.id}-${selected.updated_at ?? ""}`}
                  onSubmit={submitContractEdit}
                  variant="outlined"
                  sx={{ p: 2 }}
                >
                  <Typography variant="h6">
                    {t("contractsPage.contractDetails")}
                  </Typography>
                  <Typography color="text.secondary">
                    {t("contractsPage.detailsSubtitle")}
                  </Typography>
                  {updateContract.isError && (
                    <Alert severity="error" sx={{ mt: 1 }}>
                      {apiErrorMessage(updateContract.error, t("contractsPage.updateFailed"))}
                    </Alert>
                  )}
                  {updateContract.isSuccess && (
                    <Alert severity="success" sx={{ mt: 1 }}>
                      {t("contractsPage.saved")}
                    </Alert>
                  )}
                  <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
                    <TextField
                      required
                      name="name"
                      label={t("contractsPage.contractName")}
                      defaultValue={selected.name}
                      fullWidth
                      margin="normal"
                    />
                    <TextField
                      select
                      required
                      name="status"
                      label={t("contractsPage.status")}
                      defaultValue={selected.status}
                      fullWidth
                      margin="normal"
                    >
                      {statusOptions.map((status) => (
                        <MenuItem key={status} value={status}>
                          {statusLabel(status)}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      required
                      select
                      name="calendar_id"
                      label={t("contractsPage.businessCalendar")}
                      defaultValue={selected.calendar_id}
                      fullWidth
                      margin="normal"
                    >
                      {calendars.data?.map((calendar) => (
                        <MenuItem key={calendar.id} value={calendar.id}>
                          {calendar.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Stack>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
                    <TextField
                      required
                      type="date"
                      name="start_date"
                      label={t("contractsPage.startDate")}
                      defaultValue={selected.start_date}
                      fullWidth
                      margin="normal"
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                    <TextField
                      required
                      type="date"
                      name="end_date"
                      label={t("contractsPage.endDate")}
                      defaultValue={selected.end_date}
                      fullWidth
                      margin="normal"
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                    <TextField
                      type="date"
                      name="renewal_notice_date"
                      label={t("contractsPage.renewalNotice")}
                      defaultValue={selected.renewal_notice_date ?? ""}
                      fullWidth
                      margin="normal"
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                  </Stack>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
                    <TextField
                      required
                      name="timezone"
                      label={t("contractsPage.timezone")}
                      defaultValue={selected.timezone}
                      fullWidth
                      margin="normal"
                    />
                    <TextField
                      type="number"
                      name="included_request_limit"
                      label={t("contractsPage.includedRequests")}
                      defaultValue={selected.included_request_limit ?? ""}
                      inputProps={{ min: 1 }}
                      fullWidth
                      margin="normal"
                    />
                    <TextField
                      select
                      name="escalation_contact_id"
                      label={t("contractsPage.escalationContact")}
                      defaultValue={selected.escalation_contact_id ?? ""}
                      fullWidth
                      margin="normal"
                    >
                      <MenuItem value="">
                        {t("contractsPage.notAssigned")}
                      </MenuItem>
                      {contacts.data
                        ?.filter((contact) => contact.is_active)
                        .map((contact) => (
                          <MenuItem key={contact.id} value={contact.id}>
                            {contact.full_name}
                            {contact.is_escalation_contact
                              ? ` — ${t("contractsPage.escalationSuffix")}`
                              : ""}
                          </MenuItem>
                        ))}
                    </TextField>
                  </Stack>
                  <Paper variant="outlined" sx={{ p: 1.5, mt: 2 }}>
                    <Typography fontWeight={700}>
                      {t("contractsPage.ticketSelectionRequirements")}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mb: 1 }}
                    >
                      {t("contractsPage.ticketSelectionRequirementsHelp")}
                    </Typography>
                    <Stack direction={{ xs: "column", md: "row" }}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            name="require_product_on_ticket"
                            defaultChecked={selected.require_product_on_ticket}
                          />
                        }
                        label={t("contractsPage.requireProductOnTicket")}
                      />
                      <FormControlLabel
                        control={
                          <Checkbox
                            name="require_module_on_ticket"
                            defaultChecked={selected.require_module_on_ticket}
                          />
                        }
                        label={t("contractsPage.requireModuleOnTicket")}
                      />
                      <FormControlLabel
                        control={
                          <Checkbox
                            name="require_service_on_ticket"
                            defaultChecked={selected.require_service_on_ticket}
                          />
                        }
                        label={t("contractsPage.requireServiceOnTicket")}
                      />
                    </Stack>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={1} mt={1}>
                      <TextField select name="coverage_validation_level" label={t("contractsPage.coverageValidationLevel")} defaultValue={selected.coverage_validation_level??"PRODUCT"} fullWidth>
                        <MenuItem value="CONTRACT">{t("contractsPage.validationContract")}</MenuItem>
                        <MenuItem value="PRODUCT">{t("contractsPage.validationProduct")}</MenuItem>
                        <MenuItem value="PRODUCT_MODULE">{t("contractsPage.validationProductModule")}</MenuItem>
                        <MenuItem value="FULL">{t("contractsPage.validationFull")}</MenuItem>
                      </TextField>
                      <TextField type="number" name="expiry_grace_days" label={t("contractsPage.expiryGraceDays")} defaultValue={selected.expiry_grace_days??0} inputProps={{min:0,max:3650}} fullWidth/>
                      {hasPermission("contract.manage")&&<TextField select name="approval_group_id" disabled={approvalGroups.isLoading || approvalGroups.isError} label={t("contractsPage.approvalGroup")} defaultValue={selected.approval_group_id??""} fullWidth><MenuItem value="">{t("contractsPage.supportManagersDefault")}</MenuItem>{approvalGroups.data?.map(group=><MenuItem key={group.id} value={group.id}>{group.name}</MenuItem>)}</TextField>}
                    </Stack>
                    <Alert severity="info" sx={{mt:1}}>{t("contractsPage.approvalFirstHelp")}</Alert>
                    {approvalGroups.isError && <Alert severity="error">{apiErrorMessage(approvalGroups.error, t("contractsPage.groupLoadFailed"))}</Alert>}
                  </Paper>
                  <TextField
                    name="support_summary"
                    label={t("contractsPage.supportCoverageSummary")}
                    defaultValue={selected.support_summary ?? ""}
                    multiline
                    rows={2}
                    fullWidth
                    margin="normal"
                  />
                  <TextField
                    name="exclusions"
                    label={t("contractsPage.generalExclusions")}
                    defaultValue={selected.exclusions ?? ""}
                    multiline
                    rows={2}
                    fullWidth
                    margin="normal"
                  />
                  <Stack direction="row" justifyContent="flex-end">
                    <Button
                      type="submit"
                      variant="contained"
                      disabled={updateContract.isPending}
                    >
                      {t("contractsPage.saveDetails")}
                    </Button>
                  </Stack>
                </Paper>
              ) : (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="h6">
                    {t("contractsPage.contractDetails")}
                  </Typography>
                  <Typography>
                    {selected.name} · {statusLabel(selected.status)}
                  </Typography>
                  <Typography color="text.secondary">
                    {new Date(selected.start_date).toLocaleDateString(locale)} —{" "}
                    {new Date(selected.end_date).toLocaleDateString(locale)} ·{" "}
                    <span dir="ltr">{selected.timezone}</span>
                  </Typography>
                  <Typography sx={{ mt: 1 }}>
                    {selected.support_summary ||
                      t("contractsPage.noCoverageSummary")}
                  </Typography>
                  {selected.exclusions && (
                    <Alert severity="warning" sx={{ mt: 1 }}>
                      {selected.exclusions}
                    </Alert>
                  )}
                </Paper>
              )}
            </Box>
          )}

          {workspaceTab === "customers" && selected && (
            <Box>
              <Typography variant="h6">
                {t("contractsPage.customersUsing")}
              </Typography>
              <Typography color="text.secondary" mb={2}>
                {t("contractsPage.customersHelp")}
              </Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                {t("contractsPage.equalClientsHelp")}
              </Alert>
              {customerLinkError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {t(`contractsPage.${customerLinkError}`)}
                </Alert>
              )}
              <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  gap={1}
                  alignItems={{ md: "center" }}
                >
                  <TextField
                    select
                    fullWidth
                    label={t("contractsPage.contractBehavior")}
                    value={sharedDefault ? "SHARED" : "SPECIFIC"}
                    disabled={!hasPermission("contract.manage")}
                    onChange={(event) =>
                      setSharedDefault(event.target.value === "SHARED")
                    }
                  >
                    <MenuItem value="SPECIFIC">
                      {t("contractsPage.specificContract")}
                    </MenuItem>
                    <MenuItem value="SHARED">
                      {t("contractsPage.sharedContract")}
                    </MenuItem>
                  </TextField>
                  {hasPermission("contract.manage") && (
                    <Button
                      variant="outlined"
                      disabled={
                        updateContract.isPending ||
                        sharedDefault === selected.is_shared_default
                      }
                      onClick={() =>
                        updateContract.mutate({
                          is_shared_default: sharedDefault,
                        })
                      }
                    >
                      {t("contractsPage.saveBehavior")}
                    </Button>
                  )}
                </Stack>
              </Paper>
              <ContractClientBulkSelector
                contractId={selected.id}
                canManage={hasPermission("contract.manage")}
                onApplied={(contract) => {
                  setSelected((current) =>
                    current
                      ? {
                          ...current,
                          client_id: contract.client_id,
                          linked_client_ids: contract.linked_client_ids,
                        }
                      : current,
                  );
                  setLinkedClientIds(contract.linked_client_ids);
                  queryClient.invalidateQueries({ queryKey: ["contract-lifecycle-board"] });
                  queryClient.invalidateQueries({ queryKey: ["contracts"] });
                  queryClient.invalidateQueries({
                    queryKey: ["contract-linked-clients", selected.id],
                  });
                }}
              />
            </Box>
          )}

          {workspaceTab === "coverage" && (
            <Box>
              <Typography variant="h6">
                {t("contractsPage.coverageTitle")}
              </Typography>
              <Typography color="text.secondary" mb={2}>
                {t("contractsPage.coverageHelp")}
              </Typography>
              {coverage.isError && (
                <Alert severity="error">
                  {t("contractsPage.coverageLoadFailed")}
                </Alert>
              )}
              {!coverage.isLoading && !coverage.data?.length && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  {t("contractsPage.coverageEmpty")}
                </Alert>
              )}
              {coverage.data?.map((row) => (
                <Paper variant="outlined" sx={{ p: 1.5, mb: 1 }} key={row.id}>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    alignItems={{ md: "center" }}
                    spacing={1}
                  >
                    <Chip
                      size="small"
                      color={row.is_covered ? "success" : "error"}
                      label={t(
                        row.is_covered
                          ? "contractsPage.covered"
                          : "contractsPage.excluded",
                      )}
                    />
                    <Box flex={1}>
                      <Typography fontWeight={700}>
                        {t("contractsPage.product")}:{" "}
                        {label(products.data, row.product_id)} ·{" "}
                        {t("contractsPage.module")}:{" "}
                        {label(coverageModules.data, row.product_module_id)} ·{" "}
                        {t("contractsPage.service")}:{" "}
                        {label(services.data, row.service_id)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t("contractsPage.site")}:{" "}
                        {label(branches.data, row.branch_id)} ·{" "}
                        {t("contractsPage.environment")}:{" "}
                        {label(environments.data, row.environment_id)} ·{" "}
                        {t("contractsPage.ticketType")}:{" "}
                        {label(ticketTypes.data, row.ticket_type_id)}
                        {row.notes ? ` · ${row.notes}` : ""}
                      </Typography>
                    </Box>
                    {hasPermission("contract.manage") && (
                      <Button
                        color="error"
                        startIcon={<Delete />}
                        onClick={() => openCoverageRemoval(row)}
                      >
                        {t("contractsPage.remove")}
                      </Button>
                    )}
                  </Stack>
                </Paper>
              ))}
              {hasPermission("contract.manage") && (
                <Paper
                  component="form"
                  onSubmit={submitCoverage}
                  variant="outlined"
                  sx={{ p: 2, mt: 2 }}
                >
                  {addCoverage.isError && (
                    <Alert severity="error" sx={{ mb: 1 }}>
                      {t("contractsPage.coverageRuleFailed")}
                    </Alert>
                  )}
                  <Typography fontWeight={700}>
                    {t("contractsPage.addCoverageTitle")}
                  </Typography>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    mt={1}
                  >
                    <TextField
                      select
                      name="product_id"
                      label={t("contractsPage.product")}
                      value={productId}
                      onChange={(event) => setProductId(event.target.value)}
                      fullWidth
                    >
                      <MenuItem value="">
                        {t("contractsPage.anyProduct")}
                      </MenuItem>
                      {products.data?.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.name}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      select
                      name="product_module_id"
                      label={t("contractsPage.module")}
                      defaultValue=""
                      disabled={!productId}
                      fullWidth
                    >
                      <MenuItem value="">
                        {t("contractsPage.anyModule")}
                      </MenuItem>
                      {modules.data?.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.name}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      select
                      name="service_id"
                      label={t("contractsPage.service")}
                      defaultValue=""
                      fullWidth
                    >
                      <MenuItem value="">
                        {t("contractsPage.anyService")}
                      </MenuItem>
                      {services.data?.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Stack>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    mt={1}
                  >
                    <TextField
                      select
                      name="branch_id"
                      label={t("contractsPage.branchSite")}
                      defaultValue=""
                      fullWidth
                    >
                      <MenuItem value="">{t("contractsPage.anySite")}</MenuItem>
                      {branches.data?.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.name}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      select
                      name="environment_id"
                      label={t("contractsPage.environment")}
                      defaultValue=""
                      fullWidth
                    >
                      <MenuItem value="">
                        {t("contractsPage.anyEnvironment")}
                      </MenuItem>
                      {environments.data?.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.name}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      select
                      name="ticket_type_id"
                      label={t("contractsPage.ticketType")}
                      defaultValue=""
                      fullWidth
                    >
                      <MenuItem value="">
                        {t("contractsPage.anyTicketType")}
                      </MenuItem>
                      {ticketTypes.data?.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Stack>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    mt={1}
                  >
                    <TextField
                      select
                      name="is_covered"
                      label={t("contractsPage.decision")}
                      defaultValue="true"
                      sx={{ minWidth: 180 }}
                    >
                      <MenuItem value="true">
                        {t("contractsPage.includeCovered")}
                      </MenuItem>
                      <MenuItem value="false">
                        {t("contractsPage.excludeNotCovered")}
                      </MenuItem>
                    </TextField>
                    <TextField
                      name="notes"
                      label={t("contractsPage.ruleNotes")}
                      fullWidth
                    />
                    <Button
                      type="submit"
                      variant="contained"
                      disabled={addCoverage.isPending}
                    >
                      {t("contractsPage.addCoverage")}
                    </Button>
                  </Stack>
                </Paper>
              )}
            </Box>
          )}

          {workspaceTab === "sla" && (
            <Box>
              <Typography variant="h6">
                {t("contractsPage.centralSla")}
              </Typography>
              <Typography color="text.secondary" mb={2}>
                {t("contractsPage.centralSlaHelp")}
              </Typography>
              {hasPermission("contract.manage") && (
                <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                  <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                    <TextField
                      select
                      label={t("contractsPage.linkedSla")}
                      value={selected?.sla_policy_id ?? ""}
                      onChange={(event) => {
                        if (event.target.value === "") unlinkSla.mutate();
                        else saveSla.mutate({ policy_id: Number(event.target.value) });
                      }}
                      fullWidth
                    >
                      <MenuItem value="">
                        {t("contractsPage.unlinkSla", { defaultValue: "No SLA linked" })}
                      </MenuItem>
                      {sla.data && sla.data.contract_id === selected?.id && <MenuItem value={sla.data.id} disabled>{sla.data.name} ({t("contractsPage.contractCopy", { defaultValue: "Contract copy" })})</MenuItem>}
                      {slaPolicies.data
                        ?.filter((item) => item.is_active)
                        .map((item) => (
                          <MenuItem key={item.id} value={item.id}>
                            <span dir="ltr">{item.code}</span> — {item.name}
                          </MenuItem>
                        ))}
                    </TextField>
                  </Stack>
                  {(saveSla.isError || unlinkSla.isError) && <Alert severity="error" sx={{ mt: 1 }}>{t("contractsPage.slaSaveFailed", { defaultValue: "Could not change the linked SLA." })}</Alert>}
                  <Button sx={{ mt: 2 }} onClick={() => setSearchParams({ section: 'sla-templates' })}>
                    Manage reusable SLA templates
                  </Button>
                </Paper>
              )}
              {selected?.sla_policy_id && <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Typography fontWeight={800}>SLA coverage preview</Typography>
                <Typography variant="body2" color="text.secondary">Current contract coverage at P1–P4, using today’s effective targets.</Typography>
                {slaCoveragePreview.isError && <Alert severity="error">Could not load the SLA coverage preview.</Alert>}
                {slaCoveragePreview.data?.length === 0 && <Alert severity="info">This contract has no active coverage rows to preview.</Alert>}
                {slaCoveragePreview.data && slaCoveragePreview.data.length > 0 && <Alert severity={slaCoveragePreview.data.some(row => !row.target_id) ? "warning" : "success"}>{slaCoveragePreview.data.filter(row => row.target_id).length} of {slaCoveragePreview.data.length} coverage and priority combinations have an SLA target.</Alert>}
                {slaCoveragePreview.data?.filter(row => !row.target_id).map(row => <Typography key={`${row.coverage_id}-${row.priority}`} variant="body2" color="error.main">{label(products.data, row.product_id ?? undefined)} · {label(services.data, row.service_id ?? undefined)} · {row.priority}: {row.match_reason}</Typography>)}
              </Paper>}
              {sla.isError && (
                <Alert severity="error">
                  {t("contractsPage.slaLoadFailed")}
                </Alert>
              )}
              {!sla.isLoading && !sla.data && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  {t("contractsPage.selectPolicy")}
                </Alert>
              )}
              {sla.data && (
                <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    justifyContent="space-between"
                  >
                    <Box>
                      <Typography fontWeight={800}>{sla.data.name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t("contractsPage.calendar")}:{" "}
                        {label(calendars.data, sla.data.calendar_id)}
                      </Typography>
                    </Box>
                    <Chip
                      color={sla.data.is_active ? "success" : "default"}
                      label={t(
                        sla.data.is_active
                          ? "contractsPage.active"
                          : "contractsPage.inactive",
                      )}
                    />
                  </Stack>
                </Paper>
              )}
              {sla.data?.targets.map((target) => (
                <Paper
                  key={target.id}
                  variant="outlined"
                  sx={{ p: 1.5, mb: 1 }}
                >
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    alignItems={{ md: "center" }}
                    spacing={1}
                  >
                    <Chip label={target.priority} color="primary" />
                    <Box flex={1}>
                      <Typography fontWeight={700}>
                        {target.service_id
                          ? label(services.data, target.service_id)
                          : t("contractsPage.defaultService")}
                      </Typography>
                      <Typography variant="body2">
                        {t("contractsPage.targetSummary", {
                          response: new Intl.NumberFormat(locale).format(
                            target.first_response_minutes,
                          ),
                          resolution: new Intl.NumberFormat(locale).format(
                            target.resolution_minutes,
                          ),
                          warning: new Intl.NumberFormat(locale).format(
                            target.warning_percent,
                          ),
                        })}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {target.product_id ? label(products.data, target.product_id) : 'All products'} · {target.effective_from?.slice(0, 10) ?? 'Any start'} → {target.effective_until?.slice(0, 10) ?? 'No end'}
                      </Typography>
                    </Box>
                    {hasPermission("contract.manage") && <Button onClick={() => setEditingSlaTarget(target)}>Edit</Button>}
                    {hasPermission("contract.manage") && <Button color="error" disabled={removeSlaTarget.isPending} onClick={() => removeSlaTarget.mutate(target.id)}>{t("contractsPage.removeTarget", { defaultValue: "Remove" })}</Button>}
                  </Stack>
                </Paper>
              ))}
              {removeSlaTarget.isError && <Alert severity="error">{t("contractsPage.targetRemoveFailed", { defaultValue: "Could not remove the SLA target." })}</Alert>}
              {saveSlaTarget.isError && <Alert severity="error">{apiErrorMessage(saveSlaTarget.error)}</Alert>}
              {hasPermission("contract.manage") && sla.data && (
                <Paper
                  key={`${editingSlaTarget?.id ?? 'new'}-${slaTargetFormKey}`}
                  component="form"
                  onSubmit={submitSlaTarget}
                  variant="outlined"
                  sx={{ p: 2, mt: 2 }}
                >
                  <Typography fontWeight={700}>
                    {editingSlaTarget ? 'Edit contract SLA target' : t("contractsPage.updateDuration")}
                  </Typography>
                  <Alert severity="info" sx={{ mt: 1 }}>
                    {t("contractsPage.centralUpdateNotice")}
                  </Alert>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    mt={1}
                  >
                    <TextField
                      select
                      name="product_id"
                      label="Product"
                      defaultValue={editingSlaTarget?.product_id ?? ""}
                      disabled={Boolean(editingSlaTarget)}
                      sx={{ minWidth: 180 }}
                    >
                      <MenuItem value="">All products</MenuItem>
                      {products.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
                    </TextField>
                    <TextField
                      select
                      name="service_id"
                      label={t("contractsPage.service")}
                      defaultValue={editingSlaTarget?.service_id ?? ""}
                      disabled={Boolean(editingSlaTarget)}
                      fullWidth
                    >
                      <MenuItem value="">
                        {t("contractsPage.anyServiceDefault")}
                      </MenuItem>
                      {services.data?.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.name}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      select
                      required
                      name="priority"
                      label={t("contractsPage.priority")}
                      defaultValue={editingSlaTarget?.priority ?? "P3"}
                      disabled={Boolean(editingSlaTarget)}
                    >
                      {["P1", "P2", "P3", "P4"].map((priority) => (
                        <MenuItem key={priority} value={priority}>
                          {priority}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      required
                      type="number"
                      name="first_response_minutes"
                      label={t("contractsPage.respondMinutes")}
                      defaultValue={editingSlaTarget?.first_response_minutes ?? ""}
                      inputProps={{ min: 1 }}
                    />
                    <TextField
                      required
                      type="number"
                      name="resolution_minutes"
                      label={t("contractsPage.resolveMinutes")}
                      defaultValue={editingSlaTarget?.resolution_minutes ?? ""}
                      inputProps={{ min: 1 }}
                    />
                    <TextField
                      required
                      type="number"
                      name="warning_percent"
                      label={t("contractsPage.warnPercent")}
                      defaultValue={editingSlaTarget?.warning_percent ?? 75}
                      inputProps={{ min: 1, max: 99 }}
                    />
                    <TextField type="datetime-local" name="effective_from" label="Effective from" defaultValue={editingSlaTarget?.effective_from?.slice(0, 16) ?? ""} slotProps={{ inputLabel: { shrink: true } }} />
                    <TextField type="datetime-local" name="effective_until" label="Effective until" defaultValue={editingSlaTarget?.effective_until?.slice(0, 16) ?? ""} slotProps={{ inputLabel: { shrink: true } }} />
                    <Button
                      type="submit"
                      variant="contained"
                      disabled={saveSlaTarget.isPending}
                    >
                      {t("contractsPage.saveDuration")}
                    </Button>
                    {editingSlaTarget && <Button onClick={() => { setEditingSlaTarget(null); setSlaTargetFormKey((value) => value + 1) }}>New target</Button>}
                  </Stack>
                </Paper>
              )}
            </Box>
          )}

          {workspaceTab === "documents" && (
            <Box>
              <Typography variant="h6">
                {t("contractsPage.documentsTitle")}
              </Typography>
              <Typography color="text.secondary" mb={2}>
                {t("contractsPage.documentsHelp")}
              </Typography>
              {documents.isError && (
                <Alert severity="error">
                  {t("contractsPage.documentsFailed")}
                </Alert>
              )}
              {!documents.isLoading && !documents.data?.length && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  {t("contractsPage.documentsEmpty")}
                </Alert>
              )}
              {documents.data?.map((document) => (
                <Paper
                  key={document.id}
                  variant="outlined"
                  sx={{ p: 1.5, mb: 1 }}
                >
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1}
                    alignItems={{ sm: "center" }}
                  >
                    <Description color="action" />
                    <Box flex={1}>
                      <Typography fontWeight={700}>
                        <span dir="ltr">{document.original_filename}</span>
                      </Typography>
                      <Typography variant="caption">
                        {t("contractsPage.uploaded", {
                          size: new Intl.NumberFormat(locale, {
                            maximumFractionDigits: 1,
                          }).format(document.size_bytes / 1024),
                          date: new Date(document.created_at).toLocaleString(
                            locale,
                          ),
                        })}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      onClick={async () => {
                        const response = await api.get(
                          `/contracts/${selected?.id}/documents/${document.id}/download`,
                          { responseType: "blob" },
                        );
                        const url = URL.createObjectURL(response.data);
                        const link = window.document.createElement("a");
                        link.href = url;
                        link.download = document.original_filename;
                        link.click();
                        URL.revokeObjectURL(url);
                      }}
                    >
                      {t("contractsPage.download")}
                    </Button>
                    {hasPermission("contract.manage") && (
                      <Button
                        color="error"
                        size="small"
                        startIcon={<Delete />}
                        onClick={() => removeDocument.mutate(document.id)}
                      >
                        {t("contractsPage.remove")}
                      </Button>
                    )}
                  </Stack>
                </Paper>
              ))}
              {hasPermission("contract.manage") && (
                <Button
                  component="label"
                  variant="contained"
                  startIcon={<Add />}
                  sx={{ mt: 1 }}
                  disabled={uploadDocument.isPending}
                >
                  {t("contractsPage.uploadDocument")}
                  <input
                    hidden
                    type="file"
                    accept=".pdf,.docx,.xlsx,.txt,.csv,.png,.jpg,.jpeg"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) uploadDocument.mutate(file);
                      event.target.value = "";
                    }}
                  />
                </Button>
              )}
            </Box>
          )}
          {workspaceTab === "sla" && calendarSchedule.data && (
            <Paper
              component="form"
              key={`${calendarSchedule.data.id}-${calendarSchedule.data.days.map((day) => `${day.weekday}${day.start_time}${day.end_time}${day.is_working_day}`).join("-")}`}
              onSubmit={submitCalendarSchedule}
              variant="outlined"
              sx={{ p: 2, mt: 2 }}
            >
              <Typography variant="h6">
                {t("contractsPage.supportHours")}
              </Typography>
              <Typography color="text.secondary">
                {t("contractsPage.supportHoursHelp")}
              </Typography>
              <TextField
                name="timezone"
                label={t("contractsPage.supportTimezone")}
                defaultValue={calendarSchedule.data.timezone}
                fullWidth
                margin="normal"
                disabled={!hasPermission("contract.manage")}
              />
              {Array.from({ length: 7 }, (_, weekday) => weekday).map(
                (weekday) => {
                  const day = calendarSchedule.data?.days.find(
                    (item) => item.weekday === weekday,
                  );
                  return (
                    <Stack
                      key={weekday}
                      direction={{ xs: "column", sm: "row" }}
                      spacing={1}
                      alignItems={{ sm: "center" }}
                      sx={{ py: 0.5 }}
                    >
                      <FormControlLabel
                        sx={{ minWidth: 140 }}
                        control={
                          <Checkbox
                            name={`working_${weekday}`}
                            defaultChecked={day?.is_working_day ?? false}
                            disabled={!hasPermission("contract.manage")}
                          />
                        }
                        label={t(`contractsPage.weekdays.${weekday}`)}
                      />
                      <TextField
                        name={`start_${weekday}`}
                        type="time"
                        label={t("contractsPage.from")}
                        defaultValue={(day?.start_time ?? "08:00").slice(0, 5)}
                        slotProps={{ inputLabel: { shrink: true } }}
                        disabled={!hasPermission("contract.manage")}
                      />
                      <TextField
                        name={`end_${weekday}`}
                        type="time"
                        label={t("contractsPage.to")}
                        defaultValue={(day?.end_time ?? "00:00").slice(0, 5)}
                        slotProps={{ inputLabel: { shrink: true } }}
                        helperText={t("contractsPage.midnightHelp")}
                        disabled={!hasPermission("contract.manage")}
                      />
                    </Stack>
                  );
                },
              )}
              {saveCalendarSchedule.isError && (
                <Alert severity="error">{t("contractsPage.hoursFailed")}</Alert>
              )}
              {saveCalendarSchedule.isSuccess && (
                <Alert severity="success">
                  {t("contractsPage.hoursSaved")}
                </Alert>
              )}
              {hasPermission("contract.manage") && (
                <Button
                  type="submit"
                  variant="contained"
                  disabled={saveCalendarSchedule.isPending}
                >
                  {t("contractsPage.saveHours")}
                </Button>
              )}
            </Paper>
          )}
        </DialogContent>
        <DialogActions>
          {hasPermission("contract.delete") && (
            <Button
              color="error"
              startIcon={<Delete />}
              disabled={deleteContract.isPending}
              onClick={confirmDeleteContract}
            >
              {t(
                deleteContract.isPending
                  ? "contractsPage.deleting"
                  : "contractsPage.deleteContract",
              )}
            </Button>
          )}
          <Button onClick={closeWorkspace}>
            {t("contractsPage.closeWorkspace")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(coverageRemoval)}
        onClose={() => setCoverageRemoval(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Remove product or service coverage?</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Removing this product can also remove its related module and service
            rules. Select exactly which linked items should be removed;
            unchecked items will be kept.
          </Alert>
          <Typography fontWeight={800}>
            {coverageRemoval &&
              label(products.data, coverageRemoval.product_id)}
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={1}>
            Rules without ticket history for this contract’s clients are
            deleted. Rules used by tickets are retired with their audit history
            preserved.
          </Typography>
          <Stack spacing={1}>
            {removalCandidates.map((row) => (
              <Paper key={row.id} variant="outlined" sx={{ p: 1 }}>
                <FormControlLabel
                  sx={{ m: 0, width: "100%" }}
                  control={
                    <Checkbox
                      checked={coverageRemovalIds.includes(row.id)}
                      disabled={row.id === coverageRemoval?.id}
                      onChange={(_, checked) =>
                        setCoverageRemovalIds((current) =>
                          checked
                            ? [...current, row.id]
                            : current.filter((id) => id !== row.id),
                        )
                      }
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight={700}>
                        {row.id === coverageRemoval?.id
                          ? "Selected item"
                          : "Related item"}
                        : {label(products.data, row.product_id)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Module:{" "}
                        {label(coverageModules.data, row.product_module_id)} ·
                        Service: {label(services.data, row.service_id)}
                      </Typography>
                    </Box>
                  }
                />
              </Paper>
            ))}
          </Stack>
          {removeCoverage.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {apiErrorMessage(
                removeCoverage.error,
                "The selected coverage could not be removed. Please retry.",
              )}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCoverageRemoval(null)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            startIcon={<Delete />}
            disabled={removeCoverage.isPending || !coverageRemovalIds.length}
            onClick={() => removeCoverage.mutate(coverageRemovalIds)}
          >
            {removeCoverage.isPending
              ? "Removing…"
              : `Remove ${coverageRemovalIds.length} selected`}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
