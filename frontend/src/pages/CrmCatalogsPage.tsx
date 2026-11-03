import { serverDateInput } from "../utils/serverTime";
import {
  Add,
  Check,
  Delete,
  Edit,
  ExpandMore,
  Search,
  Settings,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Menu,
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
  Switch,
  Tab,
  Tabs,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getLocalizedName } from "../i18n/localizedMasterData";
import axios from "axios";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";

const resources = [
  { key: "countries", endpoint: "/countries" },
  { key: "departments", endpoint: "/departments" },
  { key: "contractTemplateTypes", endpoint: "/contract-template-types" },
  { key: "contacts", endpoint: "/contacts" },
  { key: "products", endpoint: "/products" },
  { key: "installations", endpoint: "/installations" },
  { key: "services", endpoint: "/services" },
  { key: "vendors", endpoint: "/vendors" },
  { key: "clientStatuses", endpoint: "/client-statuses" },
  { key: "ticketStatuses", endpoint: "/ticket-statuses" },
  { key: "ticketTypes", endpoint: "/ticket-types" },
  { key: "deploymentIssueTypes", endpoint: "/deployment-issue-types" },
  { key: "environments", endpoint: "/environments" },
  { key: "ticketCategories", endpoint: "/ticket-categories" },
  { key: "rootCauses", endpoint: "/root-causes" },
  { key: "ticketFlags", endpoint: "/ticket-flags" },
  { key: "supportTeams", endpoint: "/support-teams" },
  { key: "skills", endpoint: "/skills" },
  { key: "adjustmentReasons", endpoint: "/manager-finance/adjustment-reasons" },
];
const resourceGroup = (endpoint: string) =>
  [
    "/ticket-statuses",
    "/ticket-types",
    "/deployment-issue-types",
    "/ticket-categories",
    "/root-causes",
    "/ticket-flags",
    "/support-teams",
    "/skills",
  ].includes(endpoint)
    ? "ticket"
    : endpoint === "/departments"
      ? "user"
      : [
            "/contract-template-types",
            "/manager-finance/adjustment-reasons",
          ].includes(endpoint)
        ? "contracts"
        : [
              "/contacts",
              "/products",
              "/installations",
              "/services",
              "/vendors",
              "/client-statuses",
              "/environments",
              "/countries",
            ].includes(endpoint)
          ? "crm"
          : "other";
const resourceGroups = ["ticket", "user", "crm", "contracts", "other"];
const multilingualCatalogEndpoints = [
  "/departments",
  "/services",
  "/client-statuses",
  "/ticket-statuses",
  "/ticket-types",
  "/deployment-issue-types",
  "/environments",
  "/ticket-categories",
  "/root-causes",
];
const getLocalizedDescription = (
  item: { description?: string; description_ar?: string },
  language: "ar" | "en",
) =>
  language === "ar"
    ? item.description_ar?.trim() || item.description?.trim() || ""
    : item.description?.trim() || item.description_ar?.trim() || "";
type Product = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  description?: string;
  description_ar?: string;
  is_active: boolean;
};
type ProductModule = {
  id: number;
  product_id: number;
  code: string;
  name: string;
  name_ar?: string;
  is_active: boolean;
};
type ManagedCatalog = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  color?: string;
  pauses_sla?: boolean;
  sort_order?: number;
  number_prefix?: string;
  category_id?: number;
  description?: string;
  description_ar?: string;
  contact_name?: string;
  email?: string;
  phone_number?: string;
  portal_allowed?: boolean;
  ticket_creation_allowed?: boolean;
  is_production?: boolean;
  is_active: boolean;
  skill_ids?: number[];
  member_user_ids?: number[];
  module_ids?: number[];
  leader_user_id?: number;
  parent_department_id?: number;
  head_user_id?: number;
  effective_from?: string;
  effective_until?: string;
  requires_resolution_outcome?: boolean;
  requires_permanent_fix?: boolean;
  is_default_resolution_service?: boolean;
  available_for_deployment_issue?: boolean;
  is_default?: boolean;
};
type Employee = {
  id: number;
  full_name: string;
  username: string;
  job_title?: string;
  user_type: string;
  is_active: boolean;
};
type TicketSubcategory = {
  id: number;
  category_id: number;
  code: string;
  name: string;
  name_ar?: string;
  is_active: boolean;
};
type Client = { id: number; code: string; name: string };
type Country = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  default_timezone?: string;
  is_active: boolean;
};
type City = {
  id: number;
  country_id: number;
  code: string;
  name: string;
  name_ar?: string;
  is_active: boolean;
};
type Branch = { id: number; client_id: number; code: string; name: string };
type Contact = {
  id: number;
  client_id: number;
  branch_id?: number;
  full_name: string;
  email?: string;
  phone_number?: string;
  job_title?: string;
  contact_role?: string;
  is_escalation_contact: boolean;
  is_primary: boolean;
  is_active: boolean;
};
type Catalog = { id: number; code: string; name: string; name_ar?: string };
type InstallationComponent = {
  id?: number;
  product_id: number;
  product_module_id?: number;
};
type Installation = {
  id: number;
  client_id: number;
  branch_id?: number;
  product_id: number;
  product_module_id?: number;
  environment_id: number;
  installation_name: string;
  version?: string;
  server_name?: string;
  database_name?: string;
  support_owner?: string;
  is_active: boolean;
  components: InstallationComponent[];
};
type AdjustmentReason = {
  id: number;
  code: string;
  name: string;
  adjustment_type: "DISCOUNT" | "ADDITIONAL" | "BOTH";
  is_active: boolean;
};

export function CrmCatalogsPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const locale = language === "ar" ? "ar-EG" : "en-US";
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [catalogMenuAnchor, setCatalogMenuAnchor] =
    useState<HTMLElement | null>(null);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [countryDialog, setCountryDialog] = useState(false);
  const [editingCountry, setEditingCountry] = useState<Country | null>(null);
  const [cityDialog, setCityDialog] = useState(false);
  const [editingCity, setEditingCity] = useState<City | null>(null);
  const [cityCountryId, setCityCountryId] = useState("");
  const [productDialog, setProductDialog] = useState(false);
  const [moduleDialog, setModuleDialog] = useState(false);
  const [moduleProductId, setModuleProductId] = useState("");
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [editingModule, setEditingModule] = useState<ProductModule | null>(
    null,
  );
  const [catalogDialog, setCatalogDialog] = useState(false);
  const [editingCatalog, setEditingCatalog] = useState<ManagedCatalog | null>(
    null,
  );
  const [teamSkillIds, setTeamSkillIds] = useState<number[]>([]);
  const [teamMemberIds, setTeamMemberIds] = useState<number[]>([]);
  const [serviceModuleIds, setServiceModuleIds] = useState<number[]>([]);
  const [subcategoryCategory, setSubcategoryCategory] =
    useState<ManagedCatalog | null>(null);
  const [editingSubcategory, setEditingSubcategory] =
    useState<TicketSubcategory | null>(null);
  const [contactDialog, setContactDialog] = useState(false);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);
  const [contactClientId, setContactClientId] = useState("");
  const [contactBranchId, setContactBranchId] = useState("");
  const [contactSearch, setContactSearch] = useState("");
  const [installationDialog, setInstallationDialog] = useState(false);
  const [editingInstallation, setEditingInstallation] =
    useState<Installation | null>(null);
  const [installationClientId, setInstallationClientId] = useState("");
  const [installationBranchId, setInstallationBranchId] = useState("");
  const [installationComponents, setInstallationComponents] = useState<
    Array<{ product_id: string; product_module_id: string }>
  >([{ product_id: "", product_module_id: "" }]);
  const [reasonDialog, setReasonDialog] = useState(false);
  const [editingReason, setEditingReason] = useState<AdjustmentReason | null>(
    null,
  );
  const resource = resources[tab];
  const activeResourceGroup = resourceGroup(resource.endpoint);
  const visibleResourceGroups = resourceGroups.filter((group) =>
    resources.some((item) => resourceGroup(item.endpoint) === group),
  );
  const selectableResources = resources.filter((item) => {
    if (resourceGroup(item.endpoint) !== activeResourceGroup) return false;
    const label = t(`crmCatalogs.resources.${item.key}`);
    return label.toLocaleLowerCase(locale).includes(
      catalogSearch.trim().toLocaleLowerCase(locale),
    );
  });
  const selectResourceGroup = (group: string) => {
    const index = resources.findIndex(
      (item) => resourceGroup(item.endpoint) === group,
    );
    if (index >= 0) setTab(index);
    setCatalogSearch("");
    setCatalogMenuAnchor(null);
  };
  const selectResource = (index: number) => {
    setTab(index);
    setCatalogSearch("");
    setCatalogMenuAnchor(null);
  };
  useEffect(() => {
    if (resource.endpoint === "/services" && editingCatalog)
      setServiceModuleIds(editingCatalog.module_ids ?? []);
  }, [editingCatalog, resource.endpoint]);
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canManage = hasPermission("installation.manage");
  const canManageClientCatalog = hasPermission("client.manage");
  const canManageContacts = hasPermission("contact.manage");
  const canManageSupport = hasPermission("configuration.manage");
  const canManageUsers = hasPermission("user.manage");
  const query = useQuery({
    queryKey: ["crm-catalog", resource.endpoint],
    queryFn: async () =>
      (
        await api.get<Record<string, unknown>[]>(resource.endpoint, {
          params: [
            "/root-causes",
            "/ticket-types",
            "/deployment-issue-types",
            "/departments",
            "/ticket-flags",
            "/manager-finance/adjustment-reasons",
          ].includes(resource.endpoint)
            ? { include_inactive: true }
            : undefined,
        })
      ).data,
  });
  const products =
    resource.endpoint === "/products"
      ? (query.data as Product[] | undefined)
      : undefined;
  const managedCatalog = [
    "/departments",
    "/contract-template-types",
    "/services",
    "/vendors",
    "/client-statuses",
    "/ticket-statuses",
    "/ticket-types",
    "/deployment-issue-types",
    "/environments",
    "/ticket-categories",
    "/root-causes",
    "/ticket-flags",
    "/support-teams",
    "/skills",
  ].includes(resource.endpoint)
    ? (query.data as ManagedCatalog[] | undefined)
    : undefined;
  const canManageCurrentCatalog =
    resource.endpoint === "/ticket-flags"
      ? hasPermission("ticket.flag.manage")
      : resource.endpoint === "/contract-template-types"
      ? hasPermission("contract.template.manage")
      : resource.endpoint === "/departments"
        ? canManageUsers
        : [
              "/ticket-statuses",
              "/ticket-types",
              "/deployment-issue-types",
              "/ticket-categories",
              "/root-causes",
              "/support-teams",
              "/skills",
            ].includes(resource.endpoint)
          ? canManageSupport
          : resource.endpoint === "/environments"
            ? canManage
            : canManageClientCatalog;
  const supportSkills = useQuery({
    queryKey: ["support-skills"],
    queryFn: async () => (await api.get<ManagedCatalog[]>("/skills")).data,
    enabled: resource.endpoint === "/support-teams",
  });
  const supportEmployees = useQuery({
    queryKey: ["users", "organization-options"],
    queryFn: async () => (await api.get<Employee[]>("/users?limit=200")).data,
    enabled:
      (resource.endpoint === "/support-teams" && canManageSupport) ||
      (resource.endpoint === "/departments" && canManageUsers),
  });
  const ticketSubcategories = useQuery({
    queryKey: ["ticket-subcategories-admin", subcategoryCategory?.id],
    queryFn: async () =>
      (
        await api.get<TicketSubcategory[]>(
          `/ticket-categories/${subcategoryCategory?.id}/subcategories`,
        )
      ).data,
    enabled: Boolean(subcategoryCategory),
  });
  const contacts =
    resource.endpoint === "/contacts"
      ? (query.data as Contact[] | undefined)
      : undefined;
  const countries =
    resource.endpoint === "/countries"
      ? (query.data as Country[] | undefined)
      : undefined;
  const installations =
    resource.endpoint === "/installations"
      ? (query.data as Installation[] | undefined)
      : undefined;
  const adjustmentReasons =
    resource.endpoint === "/manager-finance/adjustment-reasons"
      ? (query.data as AdjustmentReason[] | undefined)
      : undefined;
  const clientsQuery = useQuery({
    queryKey: ["clients-for-contacts"],
    enabled: resource.endpoint === "/contacts",
    queryFn: async () => (await api.get<Client[]>("/clients")).data,
  });
  const branchesQuery = useQuery({
    queryKey: ["branches-for-contact", contactClientId],
    enabled: Boolean(contactDialog && contactClientId),
    queryFn: async () =>
      (await api.get<Branch[]>(`/clients/${contactClientId}/branches`)).data,
  });
  const cities = useQuery({
    queryKey: ["cities"],
    queryFn: async () =>
      (await api.get<City[]>("/cities", { params: { active_only: false } }))
        .data,
    enabled: resource.endpoint === "/countries",
  });
  const installationClients = useQuery({
    queryKey: ["clients-for-installations"],
    enabled: resource.endpoint === "/installations",
    queryFn: async () => (await api.get<Client[]>("/clients")).data,
  });
  const installationProducts = useQuery({
    queryKey: ["products-for-installations"],
    enabled: resource.endpoint === "/installations",
    queryFn: async () => (await api.get<Product[]>("/products")).data,
  });
  const environments = useQuery({
    queryKey: ["environments"],
    enabled: resource.endpoint === "/installations",
    queryFn: async () => (await api.get<Catalog[]>("/environments")).data,
  });
  const installationBranches = useQuery({
    queryKey: ["branches-for-installation", installationClientId],
    enabled: Boolean(installationDialog && installationClientId),
    queryFn: async () =>
      (await api.get<Branch[]>(`/clients/${installationClientId}/branches`))
        .data,
  });
  const installationModules = useQuery({
    queryKey: [
      "modules-for-installations",
      installationProducts.data?.map((product) => product.id),
    ],
    enabled: Boolean(
      resource.endpoint === "/installations" &&
      installationProducts.data?.length,
    ),
    queryFn: async () => {
      const responses = await Promise.all(
        (installationProducts.data ?? []).map((product) =>
          api.get<ProductModule[]>(`/products/${product.id}/modules`),
        ),
      );
      return responses.flatMap((response) => response.data);
    },
  });
  const modulesQuery = useQuery({
    queryKey: ["product-modules-admin", products?.map((product) => product.id)],
    enabled: resource.endpoint === "/products" && Boolean(products?.length),
    queryFn: async () => {
      const responses = await Promise.all(
        (products ?? []).map((product) =>
          api.get<ProductModule[]>(
            `/products/${product.id}/modules?include_inactive=true`,
          ),
        ),
      );
      return responses.flatMap((response) => response.data);
    },
  });
  const serviceProducts = useQuery({
    queryKey: ["service-link-products"],
    queryFn: async () => (await api.get<Product[]>("/products")).data,
    enabled: resource.endpoint === "/services",
  });
  const serviceModules = useQuery({
    queryKey: [
      "service-link-modules",
      serviceProducts.data?.map((item) => item.id),
    ],
    enabled:
      resource.endpoint === "/services" &&
      Boolean(serviceProducts.data?.length),
    queryFn: async () => {
      const responses = await Promise.all(
        (serviceProducts.data ?? []).map((product) =>
          api.get<ProductModule[]>(`/products/${product.id}/modules`),
        ),
      );
      return responses.flatMap((response) => response.data);
    },
  });
  const createProduct = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/products", payload),
    onSuccess: async () => {
      setProductDialog(false);
      await queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/products"],
      });
      await queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
  const saveCountry = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingCountry
        ? api.patch(`/countries/${editingCountry.id}`, payload)
        : api.post("/countries", payload),
    onSuccess: async () => {
      setCountryDialog(false);
      setEditingCountry(null);
      await queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/countries"],
      });
      await queryClient.invalidateQueries({ queryKey: ["countries"] });
      await queryClient.invalidateQueries({ queryKey: ["cities"] });
    },
  });
  const saveCity = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingCity
        ? api.patch(`/cities/${editingCity.id}`, payload)
        : api.post("/cities", payload),
    onSuccess: async () => {
      setCityDialog(false);
      setEditingCity(null);
      setCityCountryId("");
      await queryClient.invalidateQueries({ queryKey: ["cities"] });
    },
  });
  const createModule = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/products/${moduleProductId}/modules`, payload),
    onSuccess: async () => {
      setModuleDialog(false);
      await queryClient.invalidateQueries({ queryKey: ["product-modules"] });
      await queryClient.invalidateQueries({
        queryKey: ["product-modules-admin"],
      });
    },
  });
  const updateProduct = useMutation({
    mutationFn: async (payload: {
      id: number;
      name: string;
      name_ar: string;
      description: string | null;
      description_ar: string | null;
      is_active: boolean;
    }) => api.patch(`/products/${payload.id}`, payload),
    onSuccess: async () => {
      setEditingProduct(null);
      await queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/products"],
      });
      await queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
  const updateModule = useMutation({
    mutationFn: async (payload: {
      id: number;
      product_id: number;
      name: string;
      name_ar: string;
      is_active: boolean;
    }) =>
      api.patch(
        `/products/${payload.product_id}/modules/${payload.id}`,
        payload,
      ),
    onSuccess: async () => {
      setEditingModule(null);
      await queryClient.invalidateQueries({
        queryKey: ["product-modules-admin"],
      });
      await queryClient.invalidateQueries({ queryKey: ["product-modules"] });
    },
  });
  const saveCatalog = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (resource.endpoint === "/departments" && editingCatalog) {
        const {
          parent_department_id,
          head_user_id,
          effective_from,
          effective_until,
          ...department
        } = payload;
        await api.patch(
          `${resource.endpoint}/${editingCatalog.id}`,
          department,
        );
        return api.post(
          `/departments/${editingCatalog.id}/organization-history`,
          {
            parent_department_id,
            head_user_id,
            effective_from,
            effective_until,
          },
        );
      }
      return editingCatalog
        ? api.patch(`${resource.endpoint}/${editingCatalog.id}`, payload)
        : api.post(resource.endpoint, payload);
    },
    onSuccess: async () => {
      setCatalogDialog(false);
      setEditingCatalog(null);
      await queryClient.invalidateQueries({
        queryKey: ["crm-catalog", resource.endpoint],
      });
      await queryClient.invalidateQueries({
        queryKey: ["department-organization"],
      });
    },
  });
  const deleteRootCause = useMutation({
    mutationFn: async (id: number) => api.delete(`/root-causes/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/root-causes"],
      }),
  });
  const deleteTicketFlag = useMutation({
    mutationFn: async (id: number) => api.delete(`/ticket-flags/${id}`),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["crm-catalog", "/ticket-flags"] }),
  });
  const deleteTemplateType = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/contract-template-types/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/contract-template-types"],
      }),
  });
  const saveSubcategory = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingSubcategory
        ? api.patch(
            `/ticket-categories/${subcategoryCategory?.id}/subcategories/${editingSubcategory.id}`,
            payload,
          )
        : api.post(
            `/ticket-categories/${subcategoryCategory?.id}/subcategories`,
            payload,
          ),
    onSuccess: async () => {
      setEditingSubcategory(null);
      await queryClient.invalidateQueries({
        queryKey: ["ticket-subcategories-admin", subcategoryCategory?.id],
      });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-subcategories"],
      });
    },
  });
  const saveContact = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingContact
        ? api.patch(`/contacts/${editingContact.id}`, payload)
        : api.post("/contacts", payload),
    onSuccess: async () => {
      setContactDialog(false);
      setEditingContact(null);
      setContactClientId("");
      setContactBranchId("");
      await queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/contacts"],
      });
    },
  });
  const saveInstallation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingInstallation
        ? api.patch(`/installations/${editingInstallation.id}`, payload)
        : api.post("/installations", payload),
    onSuccess: async () => {
      setInstallationDialog(false);
      setEditingInstallation(null);
      await queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/installations"],
      });
    },
  });
  const saveAdjustmentReason = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingReason
        ? api.patch(
            `/manager-finance/adjustment-reasons/${editingReason.id}`,
            payload,
          )
        : api.post("/manager-finance/adjustment-reasons", payload),
    onSuccess: async () => {
      setReasonDialog(false);
      setEditingReason(null);
      await queryClient.invalidateQueries({
        queryKey: ["crm-catalog", "/manager-finance/adjustment-reasons"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["finance-adjustment-reasons"],
      });
    },
  });

  function submitProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    createProduct.mutate({
      name: String(values.name).trim(),
      name_ar: String(values.name_ar).trim(),
      description: String(values.description).trim() || null,
      description_ar: String(values.description_ar).trim() || null,
      is_active: true,
    });
  }
  function submitAdjustmentReason(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveAdjustmentReason.mutate({
      name: String(values.name).trim(),
      adjustment_type: values.adjustment_type,
      is_active: values.is_active === "on",
    });
  }
  function submitCountry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveCountry.mutate({
      name: String(values.name).trim(),
      name_ar: String(values.name_ar ?? "").trim() || null,
      default_timezone: String(values.default_timezone).trim() || null,
      is_active: values.is_active !== "false",
      ...(!editingCountry
        ? {
            city_name: String(values.city_name).trim() || null,
            city_name_ar: String(values.city_name_ar ?? "").trim() || null,
          }
        : {}),
    });
  }
  function submitCity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveCity.mutate({
      ...(editingCity ? {} : { country_id: Number(values.country_id) }),
      name: String(values.name).trim(),
      name_ar: String(values.name_ar ?? "").trim() || null,
      is_active: values.is_active !== "false",
    });
  }
  function submitModule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    createModule.mutate({
      name: String(values.name).trim(),
      name_ar: String(values.name_ar).trim(),
      is_active: true,
    });
  }
  function submitProductEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingProduct) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    updateProduct.mutate({
      id: editingProduct.id,
      name: String(values.name).trim(),
      name_ar: String(values.name_ar).trim(),
      description: String(values.description).trim() || null,
      description_ar: String(values.description_ar).trim() || null,
      is_active: values.is_active === "on",
    });
  }
  function submitModuleEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingModule) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    updateModule.mutate({
      id: editingModule.id,
      product_id: editingModule.product_id,
      name: String(values.name).trim(),
      name_ar: String(values.name_ar).trim(),
      is_active: values.is_active === "on",
    });
  }
  function submitCatalog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const payload: Record<string, unknown> = {
      name: String(values.name).trim(),
      is_active: values.is_active === "on",
    };
    if (multilingualCatalogEndpoints.includes(resource.endpoint))
      payload.name_ar = String(values.name_ar).trim();
    if (resource.endpoint === "/ticket-types") {
      payload.number_prefix = String(values.number_prefix).trim().toUpperCase();
      payload.color = String(values.color);
      payload.available_for_deployment_issue =
        values.available_for_deployment_issue === "on";
    }
    if (resource.endpoint === "/deployment-issue-types")
      payload.is_default = values.is_default === "on";
    if (
      [
        "/departments",
        "/contract-template-types",
        "/services",
        "/ticket-categories",
        "/root-causes",
        "/deployment-issue-types",
      ].includes(resource.endpoint)
    )
      payload.description = String(values.description).trim() || null;
    if (
      [
        "/departments",
        "/services",
        "/ticket-categories",
        "/root-causes",
        "/deployment-issue-types",
      ].includes(resource.endpoint)
    )
      payload.description_ar = String(values.description_ar).trim() || null;
    if (resource.endpoint === "/services") {
      payload.module_ids = serviceModuleIds;
      payload.is_default_resolution_service =
        values.is_default_resolution_service === "on";
    }
    if (resource.endpoint === "/root-causes") {
      payload.requires_resolution_outcome =
        values.requires_resolution_outcome === "on";
      payload.requires_permanent_fix = values.requires_permanent_fix === "on";
    }
    if (resource.endpoint === "/ticket-flags") {
      payload.description = String(values.description).trim() || null;
      payload.color = String(values.color);
      payload.pauses_sla = values.pauses_sla === "on";
      payload.sort_order = Number(values.sort_order);
    }
    if (resource.endpoint === "/departments") {
      payload.parent_department_id = values.parent_department_id
        ? Number(values.parent_department_id)
        : null;
      payload.head_user_id = values.head_user_id
        ? Number(values.head_user_id)
        : null;
      payload.effective_from = String(values.effective_from);
      payload.effective_until = values.effective_until
        ? String(values.effective_until)
        : null;
    }
    if (resource.endpoint === "/vendors") {
      payload.contact_name = String(values.contact_name).trim() || null;
      payload.email = String(values.email).trim() || null;
      payload.phone_number = String(values.phone_number).trim() || null;
    }
    if (resource.endpoint === "/client-statuses") {
      payload.portal_allowed = values.portal_allowed === "on";
      payload.ticket_creation_allowed = values.ticket_creation_allowed === "on";
    }
    if (resource.endpoint === "/ticket-statuses")
      payload.color = String(values.color);
    if (resource.endpoint === "/environments")
      payload.is_production = values.is_production === "on";
    if (["/support-teams", "/skills"].includes(resource.endpoint))
      payload.description = String(values.description).trim() || null;
    if (resource.endpoint === "/support-teams") {
      payload.skill_ids = teamSkillIds;
      payload.member_user_ids = teamMemberIds;
      payload.leader_user_id = values.leader_user_id
        ? Number(values.leader_user_id)
        : null;
    }
    saveCatalog.mutate(payload);
  }
  function submitSubcategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveSubcategory.mutate({
      name: String(values.name).trim(),
      name_ar: String(values.name_ar).trim(),
      is_active: values.is_active === "on",
    });
  }
  function submitContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveContact.mutate({
      client_id: Number(values.client_id),
      branch_id: values.branch_id ? Number(values.branch_id) : null,
      full_name: String(values.full_name).trim(),
      email: String(values.email).trim() || null,
      phone_number: String(values.phone_number).trim() || null,
      job_title: String(values.job_title).trim() || null,
      contact_role: String(values.contact_role).trim() || null,
      is_escalation_contact: values.is_escalation_contact === "on",
      is_primary: values.is_primary === "on",
      is_active: values.is_active === "on",
    });
  }
  const openContact = (contact?: Contact) => {
    setEditingContact(contact ?? null);
    setContactClientId(String(contact?.client_id ?? ""));
    setContactBranchId(String(contact?.branch_id ?? ""));
    setContactDialog(true);
  };
  function submitInstallation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveInstallation.mutate({
      client_id: Number(values.client_id),
      branch_id: values.branch_id ? Number(values.branch_id) : null,
      product_id: Number(installationComponents[0].product_id),
      product_module_id: installationComponents[0].product_module_id
        ? Number(installationComponents[0].product_module_id)
        : null,
      components: installationComponents.map((component) => ({
        product_id: Number(component.product_id),
        product_module_id: component.product_module_id
          ? Number(component.product_module_id)
          : null,
      })),
      environment_id: Number(values.environment_id),
      installation_name: String(values.installation_name).trim(),
      version: String(values.version).trim() || null,
      server_name: String(values.server_name).trim() || null,
      database_name: String(values.database_name).trim() || null,
      support_owner: String(values.support_owner).trim() || null,
      is_active: values.is_active === "on",
    });
  }
  const openInstallation = (item?: Installation) => {
    setEditingInstallation(item ?? null);
    setInstallationClientId(String(item?.client_id ?? ""));
    setInstallationBranchId(String(item?.branch_id ?? ""));
    const components = item?.components?.length
      ? item.components
      : item
        ? [
            {
              product_id: item.product_id,
              product_module_id: item.product_module_id,
            },
          ]
        : [];
    setInstallationComponents(
      components.length
        ? components.map((component) => ({
            product_id: String(component.product_id),
            product_module_id: String(component.product_module_id ?? ""),
          }))
        : [{ product_id: "", product_module_id: "" }],
    );
    setInstallationDialog(true);
  };
  const closeInstallation = () => {
    setInstallationDialog(false);
    setEditingInstallation(null);
    setInstallationClientId("");
    setInstallationBranchId("");
    setInstallationComponents([{ product_id: "", product_module_id: "" }]);
  };

  return (
    <Paper
      elevation={0}
      sx={{ p: 0, minWidth: 0, overflow: "hidden", bgcolor: "transparent" }}
    >
      <Paper
        variant="outlined"
        sx={{
          p: { xs: 1.5, sm: 2.25 },
          mb: 1.5,
          borderRadius: 2.5,
          background:
            "linear-gradient(120deg, rgba(25,118,210,.08), rgba(0,150,136,.04) 58%, transparent)",
        }}
      >
        <Stack
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          alignItems={{ sm: "center" }}
        >
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h4" fontWeight={900} letterSpacing={-0.5}>
              {t("crmCatalogs.title")}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {t(`crmCatalogs.groups.${activeResourceGroup}`)} ·{" "}
              {t(`crmCatalogs.resources.${resource.key}`)}
            </Typography>
          </Box>
          {resource.endpoint === "/products" && canManage && (
            <>
              <Button
                startIcon={<Add />}
                onClick={() => setModuleDialog(true)}
                disabled={!products?.length}
              >
                {t("crmCatalogs.addModule")}
              </Button>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => setProductDialog(true)}
              >
                {t("crmCatalogs.addProduct")}
              </Button>
            </>
          )}
          {resource.endpoint === "/countries" && canManageClientCatalog && (
            <Stack direction="row" gap={1}>
              <Button
                startIcon={<Add />}
                onClick={() => {
                  setEditingCity(null);
                  setCityDialog(true);
                }}
              >
                {t("crmCatalogs.addCity")}
              </Button>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => {
                  setEditingCountry(null);
                  setCountryDialog(true);
                }}
              >
                {t("crmCatalogs.addCountry")}
              </Button>
            </Stack>
          )}
          {managedCatalog && canManageCurrentCatalog && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => {
                setEditingCatalog(null);
                setTeamSkillIds([]);
                setTeamMemberIds([]);
                setServiceModuleIds([]);
                setCatalogDialog(true);
              }}
            >
              {t("crmCatalogs.addResource", {
                resource: t(`crmCatalogs.resources.${resource.key}`),
              })}
            </Button>
          )}
          {contacts && canManageContacts && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => openContact()}
            >
              {t("crmCatalogs.addContact")}
            </Button>
          )}
          {installations && canManage && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => openInstallation()}
            >
              {t("crmCatalogs.addInstallation")}
            </Button>
          )}
          {adjustmentReasons && hasPermission("finance.manage") && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => {
                setEditingReason(null);
                setReasonDialog(true);
              }}
            >
              {t("crmCatalogs.addAdjustment")}
            </Button>
          )}
        </Stack>
      </Paper>
      <Paper variant="outlined" sx={{ mb: 1.5, borderRadius: 2 }}>
        <Tabs
          value={activeResourceGroup}
          onChange={(_, value: string) => selectResourceGroup(value)}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          sx={{
            px: 1,
            borderBottom: 1,
            borderColor: "divider",
            "& .MuiTab-root": {
              minHeight: 44,
              textTransform: "none",
              fontWeight: 750,
            },
          }}
        >
          {visibleResourceGroups.map((group) => (
            <Tab
              key={group}
              value={group}
              label={t(`crmCatalogs.groups.${group}`)}
            />
          ))}
        </Tabs>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          alignItems={{ sm: "center" }}
          sx={{ p: 1.25 }}
        >
          <Button
            variant="outlined"
            endIcon={<ExpandMore />}
            onClick={(event) => setCatalogMenuAnchor(event.currentTarget)}
            sx={{
              minWidth: { xs: "100%", sm: 300 },
              justifyContent: "space-between",
              textTransform: "none",
              fontWeight: 750,
            }}
          >
            {t(`crmCatalogs.resources.${resource.key}`)}
          </Button>
          <Menu
            anchorEl={catalogMenuAnchor}
            open={Boolean(catalogMenuAnchor)}
            onClose={() => {
              setCatalogMenuAnchor(null);
              setCatalogSearch("");
            }}
            slotProps={{ paper: { sx: { width: 360, maxWidth: "90vw" } } }}
          >
            <Box sx={{ px: 1.25, pt: 0.75, pb: 1 }}>
              <TextField
                autoFocus
                fullWidth
                size="small"
                value={catalogSearch}
                onChange={(event) => setCatalogSearch(event.target.value)}
                onKeyDown={(event) => event.stopPropagation()}
                placeholder={t("crmCatalogs.searchSections")}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search fontSize="small" />
                      </InputAdornment>
                    ),
                  },
                }}
              />
            </Box>
            {selectableResources.map((item) => {
              const index = resources.indexOf(item);
              return (
                <MenuItem
                  key={item.endpoint}
                  selected={index === tab}
                  onClick={() => selectResource(index)}
                  sx={{ minHeight: 44 }}
                >
                  <Typography sx={{ flexGrow: 1 }}>
                    {t(`crmCatalogs.resources.${item.key}`)}
                  </Typography>
                  {index === tab && <Check color="primary" fontSize="small" />}
                </MenuItem>
              );
            })}
            {!selectableResources.length && (
              <Typography color="text.secondary" variant="body2" px={2} py={1.5}>
                {t("crmCatalogs.noMatchingSections")}
              </Typography>
            )}
          </Menu>
          <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
            {query.data
              ? t("crmCatalogs.itemsCount", { count: query.data.length })
              : ""}
          </Typography>
          {hasPermission("knowledge.create") && (
            <Button
              variant="text"
              startIcon={<Settings />}
              onClick={() => navigate("/knowledge?admin=1")}
            >
              {t("crmCatalogs.knowledgeAdmin")}
            </Button>
          )}
        </Stack>
      </Paper>
      {query.isLoading && <CircularProgress />}
      {query.isError && (
        <Alert severity="error">
          {t("crmCatalogs.loadFailed", {
            resource: t(`crmCatalogs.resources.${resource.key}`),
          })}
        </Alert>
      )}
      {contacts && (
        <TextField
          size="small"
          fullWidth
          label={t("crmCatalogs.searchContacts")}
          value={contactSearch}
          onChange={(event) => setContactSearch(event.target.value)}
          sx={{ mb: 2, maxWidth: 420 }}
        />
      )}
      {adjustmentReasons ? (
        adjustmentReasons.length ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("crmCatalogTables.code")}</TableCell>
                <TableCell>{t("crmCatalogTables.reason")}</TableCell>
                <TableCell>{t("crmCatalogTables.usedFor")}</TableCell>
                <TableCell>{t("crmCatalogTables.status")}</TableCell>
                {hasPermission("finance.manage") && (
                  <TableCell align="right">
                    {t("crmCatalogTables.actions")}
                  </TableCell>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {adjustmentReasons.map((reason) => (
                <TableRow key={reason.id}>
                  <TableCell sx={{ direction: "ltr" }}>{reason.code}</TableCell>
                  <TableCell>{reason.name}</TableCell>
                  <TableCell>
                    {t(
                      `crmCatalogTables.adjustmentTypes.${reason.adjustment_type}`,
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={t(
                        reason.is_active
                          ? "crmCatalogTables.active"
                          : "crmCatalogTables.inactive",
                      )}
                      color={reason.is_active ? "success" : "default"}
                    />
                  </TableCell>
                  {hasPermission("finance.manage") && (
                    <TableCell align="right">
                      <IconButton
                        aria-label={t("crmCatalogTables.edit", {
                          name: reason.name,
                        })}
                        onClick={() => {
                          setEditingReason(reason);
                          setReasonDialog(true);
                        }}
                      >
                        <Edit />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <Alert severity="info">
            {t("crmCatalogTables.emptyAdjustments")}
          </Alert>
        )
      ) : countries ? (
        countries.length ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("crmCatalogTables.countryCode")}</TableCell>
                <TableCell>{t("crmCatalogTables.country")}</TableCell>
                <TableCell>{t("crmCatalogTables.cities")}</TableCell>
                <TableCell>{t("crmCatalogTables.status")}</TableCell>
                {canManageClientCatalog && (
                  <TableCell align="right">
                    {t("crmCatalogTables.actions")}
                  </TableCell>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {countries.map((country) => (
                <TableRow key={country.id} sx={{ verticalAlign: "top" }}>
                  <TableCell sx={{ direction: "ltr" }}>
                    <b>{country.code}</b>
                    <Typography
                      variant="caption"
                      display="block"
                      color="text.secondary"
                    >
                      {t("crmCatalogTables.generated")}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {getLocalizedName(country, language)}
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      dir="ltr"
                    >
                      {country.default_timezone ??
                        t("crmCatalogTables.noTimezone")}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Stack gap={0.5}>
                      {cities.data
                        ?.filter((city) => city.country_id === country.id)
                        .map((city) => (
                          <Stack
                            key={city.id}
                            direction="row"
                            alignItems="center"
                            gap={0.5}
                          >
                            <Chip
                              size="small"
                              label={`${city.code} · ${getLocalizedName(city, language)}`}
                              color={city.is_active ? "primary" : "default"}
                              variant="outlined"
                              sx={{ direction: "ltr" }}
                            />
                            {canManageClientCatalog && (
                              <IconButton
                                size="small"
                                aria-label={t("crmCatalogTables.edit", {
                                  name: getLocalizedName(city, language),
                                })}
                                onClick={() => {
                                  setEditingCity(city);
                                  setCityCountryId(String(country.id));
                                  setCityDialog(true);
                                }}
                              >
                                <Edit fontSize="small" />
                              </IconButton>
                            )}
                          </Stack>
                        ))}
                      {!cities.data?.some(
                        (city) => city.country_id === country.id,
                      ) && (
                        <Typography variant="body2" color="text.secondary">
                          {t("crmCatalogTables.noCities")}
                        </Typography>
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={t(
                        country.is_active
                          ? "crmCatalogTables.active"
                          : "crmCatalogTables.inactive",
                      )}
                      color={country.is_active ? "success" : "default"}
                    />
                  </TableCell>
                  {canManageClientCatalog && (
                    <TableCell align="right">
                      <IconButton
                        aria-label={t("crmCatalogTables.edit", {
                          name: getLocalizedName(country, language),
                        })}
                        onClick={() => {
                          setEditingCountry(country);
                          setCountryDialog(true);
                        }}
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        color="primary"
                        aria-label={t("crmCatalogs.addCity")}
                        onClick={() => {
                          setEditingCity(null);
                          setCityCountryId(String(country.id));
                          setCityDialog(true);
                        }}
                      >
                        <Add />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <Alert severity="info">{t("crmCatalogTables.emptyCountries")}</Alert>
        )
      ) : resource.endpoint === "/products" && products ? (
        products.length ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("crmCatalogTables.code")}</TableCell>
                <TableCell>{t("crmCatalogTables.productModules")}</TableCell>
                <TableCell>{t("crmCatalogTables.description")}</TableCell>
                <TableCell>{t("crmCatalogTables.status")}</TableCell>
                {canManage && (
                  <TableCell align="right">
                    {t("crmCatalogTables.actions")}
                  </TableCell>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {products.map((product) => (
                <TableRow key={product.id} sx={{ verticalAlign: "top" }}>
                  <TableCell sx={{ direction: "ltr" }}>
                    {product.code}
                  </TableCell>
                  <TableCell>
                    <Typography>
                      {getLocalizedName(product, language)}
                    </Typography>
                    <Stack spacing={0.5} sx={{ mt: 1 }}>
                      {modulesQuery.data
                        ?.filter((module) => module.product_id === product.id)
                        .map((module) => (
                          <Stack
                            direction="row"
                            alignItems="center"
                            spacing={1}
                            key={module.id}
                          >
                            <Typography variant="body2" color="text.secondary">
                              <span dir="ltr">{module.code}</span> —{" "}
                              {getLocalizedName(module, language)}
                            </Typography>
                            <Chip
                              size="small"
                              label={t(
                                module.is_active
                                  ? "crmCatalogTables.active"
                                  : "crmCatalogTables.inactive",
                              )}
                              color={module.is_active ? "success" : "default"}
                            />
                            {canManage && (
                              <IconButton
                                size="small"
                                aria-label={t("crmCatalogTables.edit", {
                                  name: getLocalizedName(module, language),
                                })}
                                onClick={() => setEditingModule(module)}
                              >
                                <Edit fontSize="small" />
                              </IconButton>
                            )}
                          </Stack>
                        ))}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    {getLocalizedDescription(product, language) || "—"}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={t(
                        product.is_active
                          ? "crmCatalogTables.active"
                          : "crmCatalogTables.inactive",
                      )}
                      color={product.is_active ? "success" : "default"}
                    />
                  </TableCell>
                  {canManage && (
                    <TableCell align="right">
                      <IconButton
                        aria-label={t("crmCatalogTables.edit", {
                          name: getLocalizedName(product, language),
                        })}
                        onClick={() => setEditingProduct(product)}
                      >
                        <Edit />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <Alert severity="info">{t("crmCatalogTables.emptyProducts")}</Alert>
        )
      ) : installations ? (
        installations.length ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("crmCatalogTables.installation")}</TableCell>
                <TableCell>{t("crmCatalogTables.client")}</TableCell>
                <TableCell>
                  {t("crmCatalogTables.productEnvironment")}
                </TableCell>
                <TableCell>{t("crmCatalogTables.technicalDetails")}</TableCell>
                <TableCell>{t("crmCatalogTables.owner")}</TableCell>
                <TableCell>{t("crmCatalogTables.status")}</TableCell>
                {canManage && (
                  <TableCell align="right">
                    {t("crmCatalogTables.actions")}
                  </TableCell>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {installations.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    {item.installation_name}
                    <Typography variant="body2" color="text.secondary">
                      {t("crmCatalogTables.version", {
                        value: item.version ?? "—",
                      })}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {installationClients.data?.find(
                      (client) => client.id === item.client_id,
                    )?.name ??
                      t("crmCatalogTables.clientId", { id: item.client_id })}
                  </TableCell>
                  <TableCell>
                    <Stack spacing={0.5}>
                      {(item.components?.length
                        ? item.components
                        : [
                            {
                              product_id: item.product_id,
                              product_module_id: item.product_module_id,
                            },
                          ]
                      ).map((component, index) => {
                        const product = installationProducts.data?.find(
                          (entry) => entry.id === component.product_id,
                        );
                        const module = installationModules.data?.find(
                          (entry) => entry.id === component.product_module_id,
                        );
                        return (
                          <Typography
                            variant="body2"
                            key={component.id ?? index}
                          >
                            {product
                              ? getLocalizedName(product, language)
                              : t("crmCatalogTables.productId", {
                                  id: component.product_id,
                                })}
                            {component.product_module_id
                              ? ` — ${module ? getLocalizedName(module, language) : t("crmCatalogTables.moduleId", { id: component.product_module_id })}`
                              : ""}
                          </Typography>
                        );
                      })}
                      <Typography variant="caption" color="text.secondary">
                        {(() => {
                          const environment = environments.data?.find(
                            (entry) => entry.id === item.environment_id,
                          );
                          return environment
                            ? getLocalizedName(environment, language)
                            : t("crmCatalogTables.environmentId", {
                                id: item.environment_id,
                              });
                        })()}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell sx={{ direction: "ltr" }}>
                    {item.server_name ?? "—"}
                    <Typography variant="body2" color="text.secondary">
                      {t("crmCatalogTables.database", {
                        value: item.database_name ?? "—",
                      })}
                    </Typography>
                  </TableCell>
                  <TableCell>{item.support_owner ?? "—"}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={t(
                        item.is_active
                          ? "crmCatalogTables.active"
                          : "crmCatalogTables.inactive",
                      )}
                      color={item.is_active ? "success" : "default"}
                    />
                  </TableCell>
                  {canManage && (
                    <TableCell align="right">
                      <IconButton
                        aria-label={t("crmCatalogTables.edit", {
                          name: item.installation_name,
                        })}
                        onClick={() => openInstallation(item)}
                      >
                        <Edit />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <Alert severity="info">
            {t("crmCatalogTables.emptyInstallations")}
          </Alert>
        )
      ) : contacts ? (
        contacts.length ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("crmCatalogTables.contact")}</TableCell>
                <TableCell>{t("crmCatalogTables.clientBranch")}</TableCell>
                <TableCell>{t("crmCatalogTables.contactDetails")}</TableCell>
                <TableCell>{t("crmCatalogTables.primary")}</TableCell>
                <TableCell>{t("crmCatalogTables.status")}</TableCell>
                {canManageContacts && (
                  <TableCell align="right">
                    {t("crmCatalogTables.actions")}
                  </TableCell>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {contacts
                .filter((contact) =>
                  `${contact.full_name} ${contact.email ?? ""} ${contact.phone_number ?? ""}`
                    .toLowerCase()
                    .includes(contactSearch.toLowerCase()),
                )
                .map((contact) => {
                  const owner = clientsQuery.data?.find(
                    (client) => client.id === contact.client_id,
                  );
                  return (
                    <TableRow key={contact.id}>
                      <TableCell>
                        {contact.full_name}
                        <Typography variant="body2" color="text.secondary">
                          {contact.job_title ?? "—"}
                          {contact.contact_role
                            ? ` · ${contact.contact_role}`
                            : ""}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {owner?.name ??
                          t("crmCatalogTables.clientId", {
                            id: contact.client_id,
                          })}
                        {contact.branch_id && (
                          <Typography variant="body2" color="text.secondary">
                            {t("crmCatalogTables.branchId", {
                              id: contact.branch_id,
                            })}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ direction: "ltr" }}>
                        {contact.email ?? "—"}
                        {contact.phone_number && (
                          <Typography variant="body2" color="text.secondary">
                            {contact.phone_number}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {t(
                          contact.is_primary
                            ? "crmCatalogTables.yes"
                            : "crmCatalogTables.no",
                        )}
                        {contact.is_escalation_contact && (
                          <Typography
                            variant="caption"
                            display="block"
                            color="warning.main"
                          >
                            {t("crmCatalogTables.escalation")}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={t(
                            contact.is_active
                              ? "crmCatalogTables.active"
                              : "crmCatalogTables.inactive",
                          )}
                          color={contact.is_active ? "success" : "default"}
                        />
                      </TableCell>
                      {canManageContacts && (
                        <TableCell align="right">
                          <IconButton
                            aria-label={t("crmCatalogTables.edit", {
                              name: contact.full_name,
                            })}
                            onClick={() => openContact(contact)}
                          >
                            <Edit />
                          </IconButton>
                        </TableCell>
                      )}
                    </TableRow>
                  );
                })}
            </TableBody>
          </Table>
        ) : (
          <Alert severity="info">{t("crmCatalogTables.emptyContacts")}</Alert>
        )
      ) : managedCatalog ? (
        managedCatalog.length ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("crmCatalogTables.code")}</TableCell>
                <TableCell>{t("crmCatalogTables.name")}</TableCell>
                <TableCell>{t("crmCatalogTables.details")}</TableCell>
                <TableCell>{t("crmCatalogTables.status")}</TableCell>
                {canManageCurrentCatalog && (
                  <TableCell align="right">
                    {t("crmCatalogTables.actions")}
                  </TableCell>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {managedCatalog.map((item) => {
                const localizedName = getLocalizedName(item, language);
                return (
                  <TableRow key={item.id}>
                    <TableCell sx={{ direction: "ltr" }}>{item.code}</TableCell>
                    <TableCell>{localizedName}</TableCell>
                    <TableCell>
                      {[
                        "/contract-template-types",
                        "/services",
                        "/ticket-categories",
                        "/root-causes",
                      ].includes(resource.endpoint) ? (
                        getLocalizedDescription(item, language) || "—"
                      ) : resource.endpoint === "/vendors" ? (
                        <>
                          {item.contact_name ?? "—"}
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            dir="ltr"
                          >
                            {item.email ?? item.phone_number ?? "—"}
                          </Typography>
                        </>
                      ) : resource.endpoint === "/client-statuses" ? (
                        t("crmCatalogTables.portalTickets", {
                          portal: t(
                            item.portal_allowed
                              ? "crmCatalogTables.allowed"
                              : "crmCatalogTables.blocked",
                          ),
                          tickets: t(
                            item.ticket_creation_allowed
                              ? "crmCatalogTables.allowed"
                              : "crmCatalogTables.blocked",
                          ),
                        })
                      ) : resource.endpoint === "/environments" ? (
                        t(
                          item.is_production
                            ? "crmCatalogTables.production"
                            : "crmCatalogTables.nonProduction",
                        )
                      ) : resource.endpoint === "/support-teams" ? (
                        <>
                          {item.skill_ids
                            ?.map((id) => {
                              const skill = supportSkills.data?.find(
                                (entry) => entry.id === id,
                              );
                              return skill
                                ? getLocalizedName(skill, language)
                                : `#${id}`;
                            })
                            .join(", ") || t("crmCatalogTables.noSkills")}
                          <Typography variant="body2" color="text.secondary">
                            {t("crmCatalogTables.leaderMembers", {
                              leader:
                                supportEmployees.data?.find(
                                  (employee) =>
                                    employee.id === item.leader_user_id,
                                )?.full_name ??
                                t("crmCatalogTables.notAssigned"),
                              count: (
                                item.member_user_ids?.length ?? 0
                              ).toLocaleString(locale),
                            })}
                          </Typography>
                        </>
                      ) : (
                        getLocalizedDescription(item, language) || "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={t(
                          item.is_active
                            ? "crmCatalogTables.active"
                            : "crmCatalogTables.inactive",
                        )}
                        color={item.is_active ? "success" : "default"}
                      />
                    </TableCell>
                    {canManageCurrentCatalog && (
                      <TableCell align="right">
                        {resource.endpoint === "/ticket-categories" && (
                          <IconButton
                            aria-label={t(
                              "crmCatalogTables.manageSubcategories",
                              { name: localizedName },
                            )}
                            onClick={() => setSubcategoryCategory(item)}
                          >
                            <Settings />
                          </IconButton>
                        )}
                        <IconButton
                          aria-label={t("crmCatalogTables.edit", {
                            name: localizedName,
                          })}
                          onClick={() => {
                            setEditingCatalog(item);
                            setTeamSkillIds(item.skill_ids ?? []);
                            setTeamMemberIds(item.member_user_ids ?? []);
                            setCatalogDialog(true);
                          }}
                        >
                          <Edit />
                        </IconButton>
                        {resource.endpoint === "/root-causes" && (
                          <IconButton
                            color="error"
                            aria-label={t("crmCatalogTables.delete", {
                              name: localizedName,
                            })}
                            onClick={() => deleteRootCause.mutate(item.id)}
                          >
                            <Delete />
                          </IconButton>
                        )}
                        {resource.endpoint === "/contract-template-types" && (
                          <IconButton
                            color="error"
                            aria-label={t("crmCatalogTables.delete", {
                              name: localizedName,
                            })}
                            onClick={() => deleteTemplateType.mutate(item.id)}
                          >
                            <Delete />
                          </IconButton>
                        )}
                        {resource.endpoint === "/ticket-flags" && (
                          <IconButton color="error" aria-label={`Delete ${localizedName}`} onClick={() => { if (window.confirm(`Delete flag ${localizedName}? Used flags must be made inactive instead.`)) deleteTicketFlag.mutate(item.id) }}>
                            <Delete />
                          </IconButton>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        ) : (
          <Alert severity="info">
            {t("crmCatalogs.noneConfigured", {
              resource: t(`crmCatalogs.resources.${resource.key}`),
            })}
          </Alert>
        )
      ) : (
        query.data && (
          <Typography color="text.secondary">
            {t(
              query.data.length === 0
                ? "crmCatalogs.noneConfigured"
                : "crmCatalogs.configuredCount",
              {
                resource: t(`crmCatalogs.resources.${resource.key}`),
                count: query.data.length,
              },
            )}
          </Typography>
        )
      )}

      <Dialog
        open={reasonDialog}
        onClose={() => {
          setReasonDialog(false);
          setEditingReason(null);
        }}
        fullWidth
        maxWidth="sm"
      >
        <Stack
          component="form"
          key={editingReason?.id ?? "new-adjustment-reason"}
          onSubmit={submitAdjustmentReason}
        >
          <DialogTitle>
            {t(
              editingReason
                ? "crmCatalogDialogs.editAdjustment"
                : "crmCatalogDialogs.addAdjustment",
            )}
          </DialogTitle>
          <DialogContent>
            {saveAdjustmentReason.isError && (
              <Alert severity="error">
                {t("crmCatalogDialogs.adjustmentFailed")}
              </Alert>
            )}
            {editingReason && (
              <TextField
                label={t("crmCatalogDialogs.code")}
                value={editingReason.code}
                disabled
                fullWidth
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
            )}
            {!editingReason && (
              <Alert severity="info" sx={{ mt: 1 }}>
                {t("crmCatalogDialogs.reasonCodeGenerated")}
              </Alert>
            )}
            <TextField
              required
              name="name"
              label={t("crmCatalogDialogs.reasonName")}
              defaultValue={editingReason?.name ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              select
              required
              name="adjustment_type"
              label={t("crmCatalogDialogs.usedFor")}
              defaultValue={editingReason?.adjustment_type ?? "DISCOUNT"}
              fullWidth
              margin="normal"
            >
              {(["DISCOUNT", "ADDITIONAL", "BOTH"] as const).map((value) => (
                <MenuItem key={value} value={value}>
                  {t(`crmCatalogTables.adjustmentTypes.${value}`)}
                </MenuItem>
              ))}
            </TextField>
            <FormControlLabel
              control={
                <Switch
                  name="is_active"
                  defaultChecked={editingReason?.is_active ?? true}
                />
              }
              label={t("crmCatalogDialogs.active")}
            />
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setReasonDialog(false);
                setEditingReason(null);
              }}
            >
              {t("crmCatalogDialogs.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveAdjustmentReason.isPending}
            >
              {t("crmCatalogDialogs.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={productDialog}
        onClose={() => setProductDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Stack component="form" onSubmit={submitProduct}>
          <DialogTitle>{t("crmCatalogDialogs.addProduct")}</DialogTitle>
          <DialogContent>
            {createProduct.isError && (
              <Alert severity="error">
                {t("crmCatalogDialogs.productFailed")}
              </Alert>
            )}
            <TextField
              name="name"
              label={t("crmCatalogDialogs.productNameEn")}
              required
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="name_ar"
              label={t("crmCatalogDialogs.productNameAr")}
              required
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("crmCatalogDialogs.productCodeGenerated")}
            </Alert>
            <TextField
              name="description"
              label={t("crmCatalogDialogs.descriptionEn")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="description_ar"
              label={t("crmCatalogDialogs.descriptionAr")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setProductDialog(false)}>
              {t("crmCatalogDialogs.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createProduct.isPending}
            >
              {t("crmCatalogDialogs.saveProduct")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={countryDialog}
        onClose={() => {
          setCountryDialog(false);
          setEditingCountry(null);
        }}
        fullWidth
        maxWidth="xs"
      >
        <Stack
          component="form"
          key={editingCountry?.id ?? "new-country"}
          onSubmit={submitCountry}
        >
          <DialogTitle>
            {t(
              editingCountry
                ? "crmCatalogDialogs.editCountry"
                : "crmCatalogDialogs.addCountryCity",
            )}
          </DialogTitle>
          <DialogContent>
            {saveCountry.isError && (
              <Alert severity="error">
                {t("crmCatalogDialogs.countryExists")}
              </Alert>
            )}
            <TextField
              required
              name="name"
              label={t("crmCatalogDialogs.countryName")}
              defaultValue={editingCountry?.name ?? ""}
              fullWidth
              margin="normal"
              helperText={t("crmCatalogDialogs.countryCodeGenerated")}
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              required
              name="name_ar"
              label={t("crmCatalogDialogs.nameAr")}
              defaultValue={editingCountry?.name_ar ?? ""}
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
            {!editingCountry && (
              <>
                <TextField
                  required
                  name="city_name"
                  label={t("crmCatalogDialogs.firstCity")}
                  fullWidth
                  margin="normal"
                  helperText={t("crmCatalogDialogs.cityExample")}
                  inputProps={{ dir: "ltr" }}
                />
                <TextField
                  required
                  name="city_name_ar"
                  label={t("crmCatalogDialogs.nameAr")}
                  fullWidth
                  margin="normal"
                  inputProps={{ dir: "rtl" }}
                />
              </>
            )}
            <TextField
              name="default_timezone"
              label={t("crmCatalogDialogs.defaultTimezone")}
              defaultValue={editingCountry?.default_timezone ?? ""}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              select
              name="is_active"
              label={t("crmCatalogDialogs.status")}
              defaultValue={String(editingCountry?.is_active ?? true)}
              fullWidth
              margin="normal"
            >
              <MenuItem value="true">{t("crmCatalogTables.active")}</MenuItem>
              <MenuItem value="false">
                {t("crmCatalogTables.inactive")}
              </MenuItem>
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setCountryDialog(false);
                setEditingCountry(null);
              }}
            >
              {t("crmCatalogDialogs.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveCountry.isPending}
            >
              {t("crmCatalogDialogs.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={cityDialog}
        onClose={() => {
          setCityDialog(false);
          setEditingCity(null);
          setCityCountryId("");
        }}
        fullWidth
        maxWidth="xs"
      >
        <Stack
          component="form"
          key={editingCity?.id ?? "new-city"}
          onSubmit={submitCity}
        >
          <DialogTitle>
            {t(
              editingCity
                ? "crmCatalogDialogs.editCity"
                : "crmCatalogDialogs.addCity",
            )}
          </DialogTitle>
          <DialogContent>
            {saveCity.isError && (
              <Alert severity="error">
                {t("crmCatalogDialogs.cityExists")}
              </Alert>
            )}
            <TextField
              required
              select
              name="country_id"
              label={t("crmCatalogDialogs.country")}
              value={cityCountryId}
              disabled={Boolean(editingCity)}
              onChange={(event) => setCityCountryId(event.target.value)}
              fullWidth
              margin="normal"
            >
              {countries?.map((country) => (
                <MenuItem key={country.id} value={country.id}>
                  {getLocalizedName(country, language)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              required
              name="name"
              label={t("crmCatalogDialogs.cityName")}
              defaultValue={editingCity?.name ?? ""}
              fullWidth
              margin="normal"
              helperText={t("crmCatalogDialogs.cityCodeGenerated")}
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              required
              name="name_ar"
              label={t("crmCatalogDialogs.nameAr")}
              defaultValue={editingCity?.name_ar ?? ""}
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
            <TextField
              select
              name="is_active"
              label={t("crmCatalogDialogs.status")}
              defaultValue={String(editingCity?.is_active ?? true)}
              fullWidth
              margin="normal"
            >
              <MenuItem value="true">{t("crmCatalogTables.active")}</MenuItem>
              <MenuItem value="false">
                {t("crmCatalogTables.inactive")}
              </MenuItem>
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setCityDialog(false);
                setEditingCity(null);
                setCityCountryId("");
              }}
            >
              {t("crmCatalogDialogs.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveCity.isPending || (!editingCity && !cityCountryId)}
            >
              {t("crmCatalogDialogs.saveCity")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={Boolean(subcategoryCategory)}
        onClose={() => {
          setSubcategoryCategory(null);
          setEditingSubcategory(null);
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {t("crmCatalogDialogs.subcategories", {
            name: subcategoryCategory
              ? getLocalizedName(subcategoryCategory, language)
              : "",
          })}
        </DialogTitle>
        <DialogContent>
          {ticketSubcategories.isLoading && <CircularProgress size={24} />}
          {ticketSubcategories.isError && (
            <Alert severity="error">
              {t("crmCatalogDialogs.subcategoriesFailed")}
            </Alert>
          )}
          {!ticketSubcategories.isLoading &&
            ticketSubcategories.data?.length === 0 && (
              <Alert severity="info">
                {t("crmCatalogDialogs.noSubcategories")}
              </Alert>
            )}
          {ticketSubcategories.data?.map((item) => (
            <Stack
              key={item.id}
              direction="row"
              alignItems="center"
              spacing={1}
              sx={{ py: 0.75 }}
            >
              <Typography sx={{ flexGrow: 1 }}>
                <span dir="ltr">{item.code}</span> —{" "}
                {getLocalizedName(item, language)}
              </Typography>
              <Chip
                size="small"
                label={t(
                  item.is_active
                    ? "crmCatalogTables.active"
                    : "crmCatalogTables.inactive",
                )}
                color={item.is_active ? "success" : "default"}
              />
              <IconButton
                aria-label={t("crmCatalogTables.edit", {
                  name: getLocalizedName(item, language),
                })}
                onClick={() => setEditingSubcategory(item)}
              >
                <Edit />
              </IconButton>
            </Stack>
          ))}
          <Paper
            component="form"
            key={editingSubcategory?.id ?? "new-subcategory"}
            onSubmit={submitSubcategory}
            variant="outlined"
            sx={{ p: 2, mt: 2 }}
          >
            <Typography fontWeight={600}>
              {t(
                editingSubcategory
                  ? "crmCatalogDialogs.editSubcategory"
                  : "crmCatalogDialogs.addSubcategory",
              )}
            </Typography>
            {saveSubcategory.isError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {t("crmCatalogDialogs.subcategoryFailed")}
              </Alert>
            )}
            {editingSubcategory ? (
              <TextField
                label={t("crmCatalogDialogs.code")}
                value={editingSubcategory.code}
                disabled
                fullWidth
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
            ) : (
              <Alert severity="info" sx={{ mt: 1 }}>
                {t("crmCatalogDialogs.subcategoryCodeGenerated")}
              </Alert>
            )}
            <TextField
              name="name"
              label={t("crmCatalogDialogs.nameEn")}
              defaultValue={editingSubcategory?.name ?? ""}
              required
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="name_ar"
              label={t("crmCatalogDialogs.nameAr")}
              defaultValue={editingSubcategory?.name_ar ?? ""}
              required
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
            <FormControlLabel
              control={
                <Switch
                  name="is_active"
                  defaultChecked={editingSubcategory?.is_active ?? true}
                />
              }
              label={t("crmCatalogDialogs.active")}
            />
            <Stack direction="row" justifyContent="flex-end" spacing={1}>
              <Button
                type="button"
                onClick={() => setEditingSubcategory(null)}
                disabled={!editingSubcategory}
              >
                {t("crmCatalogDialogs.clear")}
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={saveSubcategory.isPending}
              >
                {t(
                  editingSubcategory
                    ? "crmCatalogDialogs.saveChanges"
                    : "crmCatalogDialogs.add",
                )}
              </Button>
            </Stack>
          </Paper>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setSubcategoryCategory(null);
              setEditingSubcategory(null);
            }}
          >
            {t("crmCatalogDialogs.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={moduleDialog}
        onClose={() => setModuleDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Stack component="form" onSubmit={submitModule}>
          <DialogTitle>{t("crmCatalogDialogs.addModule")}</DialogTitle>
          <DialogContent>
            {createModule.isError && (
              <Alert severity="error">
                {t("crmCatalogDialogs.moduleFailed")}
              </Alert>
            )}
            <TextField
              select
              label={t("crmCatalogDialogs.product")}
              required
              fullWidth
              margin="normal"
              value={moduleProductId}
              onChange={(event) => setModuleProductId(event.target.value)}
            >
              {products?.map((product) => (
                <MenuItem key={product.id} value={product.id}>
                  {getLocalizedName(product, language)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="name"
              label={t("crmCatalogDialogs.moduleNameEn")}
              required
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="name_ar"
              label={t("crmCatalogDialogs.moduleNameAr")}
              required
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("crmCatalogDialogs.moduleCodeGenerated")}
            </Alert>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setModuleDialog(false)}>
              {t("crmCatalogDialogs.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createModule.isPending || !moduleProductId}
            >
              {t("crmCatalogDialogs.saveModule")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={Boolean(editingProduct)}
        onClose={() => setEditingProduct(null)}
        fullWidth
        maxWidth="sm"
      >
        {editingProduct && (
          <Stack component="form" onSubmit={submitProductEdit}>
            <DialogTitle>{t("crmCatalogDialogs.editProduct")}</DialogTitle>
            <DialogContent>
              {updateProduct.isError && (
                <Alert severity="error">
                  {t("crmCatalogDialogs.productUpdateFailed")}
                </Alert>
              )}
              <TextField
                label={t("crmCatalogDialogs.productCode")}
                value={editingProduct.code}
                disabled
                fullWidth
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="name"
                label={t("crmCatalogDialogs.productNameEn")}
                defaultValue={editingProduct.name}
                required
                fullWidth
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="name_ar"
                label={t("crmCatalogDialogs.productNameAr")}
                defaultValue={editingProduct.name_ar ?? ""}
                required
                fullWidth
                margin="normal"
                inputProps={{ dir: "rtl" }}
              />
              <TextField
                name="description"
                label={t("crmCatalogDialogs.descriptionEn")}
                defaultValue={editingProduct.description ?? ""}
                fullWidth
                multiline
                rows={2}
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="description_ar"
                label={t("crmCatalogDialogs.descriptionAr")}
                defaultValue={editingProduct.description_ar ?? ""}
                fullWidth
                multiline
                rows={2}
                margin="normal"
                inputProps={{ dir: "rtl" }}
              />
              <FormControlLabel
                control={
                  <Switch
                    name="is_active"
                    defaultChecked={editingProduct.is_active}
                  />
                }
                label={t("crmCatalogDialogs.active")}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditingProduct(null)}>
                {t("crmCatalogDialogs.cancel")}
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={updateProduct.isPending}
              >
                {t("crmCatalogDialogs.saveChanges")}
              </Button>
            </DialogActions>
          </Stack>
        )}
      </Dialog>
      <Dialog
        open={Boolean(editingModule)}
        onClose={() => setEditingModule(null)}
        fullWidth
        maxWidth="sm"
      >
        {editingModule && (
          <Stack component="form" onSubmit={submitModuleEdit}>
            <DialogTitle>{t("crmCatalogDialogs.editModule")}</DialogTitle>
            <DialogContent>
              {updateModule.isError && (
                <Alert severity="error">
                  {t("crmCatalogDialogs.moduleUpdateFailed")}
                </Alert>
              )}
              <TextField
                label={t("crmCatalogDialogs.moduleCode")}
                value={editingModule.code}
                disabled
                fullWidth
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="name"
                label={t("crmCatalogDialogs.moduleNameEn")}
                defaultValue={editingModule.name}
                required
                fullWidth
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="name_ar"
                label={t("crmCatalogDialogs.moduleNameAr")}
                defaultValue={editingModule.name_ar ?? ""}
                required
                fullWidth
                margin="normal"
                inputProps={{ dir: "rtl" }}
              />
              <FormControlLabel
                control={
                  <Switch
                    name="is_active"
                    defaultChecked={editingModule.is_active}
                  />
                }
                label={t("crmCatalogDialogs.active")}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditingModule(null)}>
                {t("crmCatalogDialogs.cancel")}
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={updateModule.isPending}
              >
                {t("crmCatalogDialogs.saveChanges")}
              </Button>
            </DialogActions>
          </Stack>
        )}
      </Dialog>
      <Dialog
        open={catalogDialog}
        onClose={() => {
          setCatalogDialog(false);
          setEditingCatalog(null);
        }}
        fullWidth
        maxWidth="sm"
      >
        <Stack
          component="form"
          key={`${resource.endpoint}-${editingCatalog?.id ?? "new"}`}
          onSubmit={submitCatalog}
        >
          <DialogTitle>
            {t(
              editingCatalog
                ? "crmCatalogs.editResource"
                : "crmCatalogs.addResource",
              { resource: t(`crmCatalogs.resources.${resource.key}`) },
            )}
          </DialogTitle>
          <DialogContent>
            {saveCatalog.isError && (
              <Alert severity="error">
                {axios.isAxiosError(saveCatalog.error)
                  ? (saveCatalog.error.response?.data?.error?.message ??
                    t("crmCatalogForm.saveFailed"))
                  : t("crmCatalogForm.saveFailed")}
              </Alert>
            )}
            {editingCatalog ? (
              <TextField
                label={t("crmCatalogForm.code")}
                value={editingCatalog.code}
                disabled
                fullWidth
                margin="normal"
                helperText={t("crmCatalogForm.generated")}
                inputProps={{ dir: "ltr" }}
              />
            ) : (
              <Alert severity="info" sx={{ mt: 1 }}>
                {t("crmCatalogForm.codeGenerated")}
              </Alert>
            )}
            <TextField
              name="name"
              label={t("crmCatalogForm.nameEn")}
              defaultValue={editingCatalog?.name ?? ""}
              required
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            {multilingualCatalogEndpoints.includes(resource.endpoint) && (
              <TextField
                name="name_ar"
                label={t("crmCatalogForm.nameAr")}
                defaultValue={editingCatalog?.name_ar ?? ""}
                required
                fullWidth
                margin="normal"
                inputProps={{ dir: "rtl" }}
              />
            )}
            {resource.endpoint === "/ticket-statuses" && (
              <TextField
                name="color"
                type="color"
                label={t("crmCatalogForm.statusColor")}
                defaultValue={editingCatalog?.color ?? "#607D8B"}
                InputLabelProps={{ shrink: true }}
                fullWidth
                margin="normal"
              />
            )}
            {resource.endpoint === "/ticket-types" && (
              <>
                <TextField
                  name="number_prefix"
                  label={t("crmCatalogForm.numberPrefix")}
                  defaultValue={editingCatalog?.number_prefix ?? ""}
                  required
                  fullWidth
                  margin="normal"
                  inputProps={{ pattern: "[A-Za-z0-9_-]{1,10}", dir: "ltr" }}
                />
                <TextField
                  name="color"
                  type="color"
                  label={t("crmCatalogForm.typeColor")}
                  defaultValue={editingCatalog?.color ?? "#607D8B"}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  margin="normal"
                />
                <FormControlLabel
                  control={
                    <Switch
                      name="available_for_deployment_issue"
                      defaultChecked={
                        editingCatalog?.available_for_deployment_issue ?? false
                      }
                    />
                  }
                  label="Show when creating a ticket from a deployment issue"
                />
              </>
            )}
            {[
              "/departments",
              "/contract-template-types",
              "/services",
              "/ticket-categories",
              "/root-causes",
              "/deployment-issue-types",
            ].includes(resource.endpoint) && (
              <TextField
                name="description"
                label={t("crmCatalogForm.descriptionEn")}
                defaultValue={editingCatalog?.description ?? ""}
                fullWidth
                multiline
                rows={2}
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
            )}
            {[
              "/departments",
              "/services",
              "/ticket-categories",
              "/root-causes",
              "/deployment-issue-types",
            ].includes(resource.endpoint) && (
              <TextField
                name="description_ar"
                label={t("crmCatalogForm.descriptionAr")}
                defaultValue={editingCatalog?.description_ar ?? ""}
                fullWidth
                multiline
                rows={2}
                margin="normal"
                inputProps={{ dir: "rtl" }}
              />
            )}
            {resource.endpoint === "/services" && (
              <TextField
                select
                label={t("crmCatalogForm.linkedModules")}
                value={serviceModuleIds}
                onChange={(event) =>
                  setServiceModuleIds(event.target.value as unknown as number[])
                }
                SelectProps={{ multiple: true }}
                fullWidth
                margin="normal"
              >
                {serviceModules.data?.map((module) => {
                  const product = serviceProducts.data?.find(
                    (entry) => entry.id === module.product_id,
                  );
                  return (
                    <MenuItem key={module.id} value={module.id}>
                      {product ? getLocalizedName(product, language) : ""} ·{" "}
                      {getLocalizedName(module, language)}
                    </MenuItem>
                  );
                })}
              </TextField>
            )}
            {resource.endpoint === "/deployment-issue-types" && (
              <FormControlLabel
                control={<Switch name="is_default" defaultChecked={editingCatalog?.is_default ?? false} />}
                label="Default deployment issue type"
              />
            )}
            {resource.endpoint === "/services" && (
              <FormControlLabel
                control={
                  <Switch
                    name="is_default_resolution_service"
                    defaultChecked={
                      editingCatalog?.is_default_resolution_service ?? false
                    }
                  />
                }
                label={t("crmCatalogForm.defaultResolutionService")}
              />
            )}
            {resource.endpoint === "/root-causes" && (
              <Stack>
                <FormControlLabel
                  control={
                    <Switch
                      name="requires_resolution_outcome"
                      defaultChecked={
                        editingCatalog?.requires_resolution_outcome ?? false
                      }
                    />
                  }
                  label={t("crmCatalogForm.resolutionOutcome")}
                />
                <FormControlLabel
                  control={
                    <Switch
                      name="requires_permanent_fix"
                      defaultChecked={
                        editingCatalog?.requires_permanent_fix ?? false
                      }
                    />
                  }
                  label={t("crmCatalogForm.permanentFix")}
                />
              </Stack>
            )}
            {resource.endpoint === "/ticket-flags" && (
              <Stack>
                <TextField name="description" label="Description" defaultValue={editingCatalog?.description ?? ""} fullWidth multiline rows={2} margin="normal" />
                <TextField name="color" type="color" label="Flag color" defaultValue={editingCatalog?.color ?? "#607D8B"} InputLabelProps={{ shrink: true }} fullWidth margin="normal" />
                <TextField name="sort_order" type="number" label="Display order" defaultValue={editingCatalog?.sort_order ?? 100} inputProps={{ min: 0, max: 10000 }} fullWidth margin="normal" />
                <FormControlLabel control={<Switch name="pauses_sla" defaultChecked={editingCatalog?.pauses_sla ?? false} />} label="Pause resolution SLA while this flag is active" />
              </Stack>
            )}
            {resource.endpoint === "/departments" && (
              <>
                <TextField
                  select
                  name="parent_department_id"
                  label={t("crmCatalogForm.parentDepartment")}
                  defaultValue={editingCatalog?.parent_department_id ?? ""}
                  fullWidth
                  margin="normal"
                >
                  <MenuItem value="">{t("crmCatalogForm.topLevel")}</MenuItem>
                  {managedCatalog
                    ?.filter(
                      (item) =>
                        item.id !== editingCatalog?.id && item.is_active,
                    )
                    .map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        <span dir="ltr">{item.code}</span> —{" "}
                        {getLocalizedName(item, language)}
                      </MenuItem>
                    ))}
                </TextField>
                <TextField
                  select
                  name="head_user_id"
                  label={t("crmCatalogForm.departmentHead")}
                  defaultValue={editingCatalog?.head_user_id ?? ""}
                  fullWidth
                  margin="normal"
                >
                  <MenuItem value="">{t("crmCatalogForm.vacant")}</MenuItem>
                  {supportEmployees.data
                    ?.filter(
                      (item) => item.user_type === "EMPLOYEE" && item.is_active,
                    )
                    .map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        {item.full_name} —{" "}
                        {item.job_title ?? (
                          <span dir="ltr">{item.username}</span>
                        )}
                      </MenuItem>
                    ))}
                </TextField>
                <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                  <TextField
                    required
                    name="effective_from"
                    type="date"
                    label={t("crmCatalogForm.effectiveFrom")}
                    defaultValue={
                      editingCatalog?.effective_from ?? serverDateInput()
                    }
                    fullWidth
                    margin="normal"
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <TextField
                    name="effective_until"
                    type="date"
                    label={t("crmCatalogForm.effectiveUntil")}
                    defaultValue={editingCatalog?.effective_until ?? ""}
                    fullWidth
                    margin="normal"
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                </Stack>
              </>
            )}
            {resource.endpoint === "/vendors" && (
              <>
                <TextField
                  name="contact_name"
                  label={t("crmCatalogForm.contactName")}
                  defaultValue={editingCatalog?.contact_name ?? ""}
                  fullWidth
                  margin="normal"
                />
                <TextField
                  name="email"
                  label={t("crmCatalogForm.email")}
                  type="email"
                  defaultValue={editingCatalog?.email ?? ""}
                  fullWidth
                  margin="normal"
                  inputProps={{ dir: "ltr" }}
                />
                <TextField
                  name="phone_number"
                  label={t("crmCatalogForm.phone")}
                  defaultValue={editingCatalog?.phone_number ?? ""}
                  fullWidth
                  margin="normal"
                  inputProps={{ dir: "ltr" }}
                />
              </>
            )}
            {resource.endpoint === "/client-statuses" && (
              <Stack>
                <FormControlLabel
                  control={
                    <Switch
                      name="portal_allowed"
                      defaultChecked={editingCatalog?.portal_allowed ?? true}
                    />
                  }
                  label={t("crmCatalogForm.portalAccess")}
                />
                <FormControlLabel
                  control={
                    <Switch
                      name="ticket_creation_allowed"
                      defaultChecked={
                        editingCatalog?.ticket_creation_allowed ?? true
                      }
                    />
                  }
                  label={t("crmCatalogForm.ticketCreation")}
                />
              </Stack>
            )}
            {resource.endpoint === "/environments" && (
              <FormControlLabel
                control={
                  <Switch
                    name="is_production"
                    defaultChecked={editingCatalog?.is_production ?? false}
                  />
                }
                label={t("crmCatalogForm.production")}
              />
            )}
            {["/support-teams", "/skills"].includes(resource.endpoint) && (
              <TextField
                name="description"
                label={t("crmCatalogForm.description")}
                defaultValue={editingCatalog?.description ?? ""}
                fullWidth
                multiline
                rows={2}
                margin="normal"
              />
            )}
            {resource.endpoint === "/support-teams" && (
              <TextField
                select
                label={t("crmCatalogForm.teamSkills")}
                value={teamSkillIds}
                onChange={(event) =>
                  setTeamSkillIds(event.target.value as unknown as number[])
                }
                SelectProps={{ multiple: true }}
                fullWidth
                margin="normal"
              >
                {supportSkills.data?.map((skill) => (
                  <MenuItem key={skill.id} value={skill.id}>
                    {getLocalizedName(skill, language)}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {resource.endpoint === "/support-teams" && (
              <TextField
                select
                name="leader_user_id"
                label={t("crmCatalogForm.teamLeader")}
                defaultValue={editingCatalog?.leader_user_id ?? ""}
                fullWidth
                margin="normal"
              >
                <MenuItem value="">{t("crmCatalogForm.noLeader")}</MenuItem>
                {supportEmployees.data
                  ?.filter(
                    (item) => item.user_type === "EMPLOYEE" && item.is_active,
                  )
                  .map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.full_name} —{" "}
                      {item.job_title ?? <span dir="ltr">{item.username}</span>}
                    </MenuItem>
                  ))}
              </TextField>
            )}
            {resource.endpoint === "/support-teams" && (
              <TextField
                select
                label={t("crmCatalogForm.teamMembers")}
                value={teamMemberIds}
                onChange={(event) =>
                  setTeamMemberIds(event.target.value as unknown as number[])
                }
                SelectProps={{ multiple: true }}
                helperText={t("crmCatalogForm.teamHelp")}
                fullWidth
                margin="normal"
              >
                {supportEmployees.data
                  ?.filter(
                    (item) => item.user_type === "EMPLOYEE" && item.is_active,
                  )
                  .map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.full_name} —{" "}
                      {item.job_title ?? <span dir="ltr">{item.username}</span>}
                    </MenuItem>
                  ))}
              </TextField>
            )}
            <FormControlLabel
              control={
                <Switch
                  name="is_active"
                  defaultChecked={editingCatalog?.is_active ?? true}
                />
              }
              label={t("crmCatalogForm.active")}
            />
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setCatalogDialog(false);
                setEditingCatalog(null);
              }}
            >
              {t("crmCatalogForm.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveCatalog.isPending}
            >
              {t("crmCatalogForm.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={contactDialog}
        onClose={() => {
          setContactDialog(false);
          setEditingContact(null);
          setContactClientId("");
          setContactBranchId("");
        }}
        fullWidth
        maxWidth="sm"
      >
        <Stack
          component="form"
          key={editingContact?.id ?? "new-contact"}
          onSubmit={submitContact}
        >
          <DialogTitle>
            {t(editingContact ? "crmContactForm.edit" : "crmContactForm.add")}
          </DialogTitle>
          <DialogContent>
            {saveContact.isError && (
              <Alert severity="error">{t("crmContactForm.failed")}</Alert>
            )}
            <TextField
              select
              name="client_id"
              label={t("crmContactForm.client")}
              value={contactClientId}
              onChange={(event) => {
                setContactClientId(event.target.value);
                setContactBranchId("");
              }}
              required
              fullWidth
              margin="normal"
            >
              {clientsQuery.data?.map((client) => (
                <MenuItem key={client.id} value={client.id}>
                  {client.code} — {client.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="branch_id"
              label={t("crmContactForm.branch")}
              value={contactBranchId}
              onChange={(event) => setContactBranchId(event.target.value)}
              disabled={!contactClientId}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("crmContactForm.allBranches")}</MenuItem>
              {branchesQuery.data?.map((branch) => (
                <MenuItem key={branch.id} value={branch.id}>
                  {branch.code} — {branch.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="full_name"
              label={t("crmContactForm.fullName")}
              defaultValue={editingContact?.full_name ?? ""}
              required
              fullWidth
              margin="normal"
            />
            <TextField
              name="job_title"
              label={t("crmContactForm.jobTitle")}
              defaultValue={editingContact?.job_title ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="contact_role"
              label={t("crmContactForm.role")}
              defaultValue={editingContact?.contact_role ?? ""}
              fullWidth
              margin="normal"
              helperText={t("crmContactForm.roleHelp")}
            />
            <TextField
              name="email"
              label={t("crmContactForm.email")}
              type="email"
              defaultValue={editingContact?.email ?? ""}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              name="phone_number"
              label={t("crmContactForm.phone")}
              defaultValue={editingContact?.phone_number ?? ""}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <Stack direction="row" spacing={2}>
              <FormControlLabel
                control={
                  <Switch
                    name="is_primary"
                    defaultChecked={editingContact?.is_primary ?? false}
                  />
                }
                label={t("crmContactForm.primary")}
              />
              <FormControlLabel
                control={
                  <Switch
                    name="is_escalation_contact"
                    defaultChecked={
                      editingContact?.is_escalation_contact ?? false
                    }
                  />
                }
                label={t("crmContactForm.escalation")}
              />
              <FormControlLabel
                control={
                  <Switch
                    name="is_active"
                    defaultChecked={editingContact?.is_active ?? true}
                  />
                }
                label={t("crmContactForm.active")}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setContactDialog(false);
                setEditingContact(null);
                setContactClientId("");
                setContactBranchId("");
              }}
            >
              {t("crmContactForm.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveContact.isPending || !contactClientId}
            >
              {t("crmContactForm.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={installationDialog}
        onClose={closeInstallation}
        fullWidth
        maxWidth="md"
      >
        <Stack
          component="form"
          key={editingInstallation?.id ?? "new-installation"}
          onSubmit={submitInstallation}
        >
          <DialogTitle>
            {t(
              editingInstallation
                ? "crmInstallationForm.edit"
                : "crmInstallationForm.add",
            )}
          </DialogTitle>
          <DialogContent>
            {saveInstallation.isError && (
              <Alert severity="error">{t("crmInstallationForm.failed")}</Alert>
            )}
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                select
                name="client_id"
                label={t("crmInstallationForm.client")}
                value={installationClientId}
                onChange={(event) => {
                  setInstallationClientId(event.target.value);
                  setInstallationBranchId("");
                }}
                required
                fullWidth
                margin="normal"
              >
                {installationClients.data?.map((client) => (
                  <MenuItem key={client.id} value={client.id}>
                    <span dir="ltr">{client.code}</span> — {client.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="branch_id"
                label={t("crmInstallationForm.branch")}
                value={installationBranchId}
                onChange={(event) =>
                  setInstallationBranchId(event.target.value)
                }
                disabled={!installationClientId}
                fullWidth
                margin="normal"
              >
                <MenuItem value="">
                  {t("crmInstallationForm.clientWide")}
                </MenuItem>
                {installationBranches.data?.map((branch) => (
                  <MenuItem key={branch.id} value={branch.id}>
                    <span dir="ltr">{branch.code}</span> — {branch.name}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>
              {t("crmInstallationForm.products")}
            </Typography>
            {installationComponents.map((component, index) => (
              <Stack
                key={index}
                direction={{ xs: "column", md: "row" }}
                spacing={2}
                alignItems="center"
              >
                <TextField
                  select
                  label={t("crmInstallationForm.product")}
                  value={component.product_id}
                  onChange={(event) =>
                    setInstallationComponents((current) =>
                      current.map((row, rowIndex) =>
                        rowIndex === index
                          ? {
                              product_id: event.target.value,
                              product_module_id: "",
                            }
                          : row,
                      ),
                    )
                  }
                  required
                  fullWidth
                  margin="normal"
                >
                  {installationProducts.data?.map((product) => (
                    <MenuItem key={product.id} value={product.id}>
                      <span dir="ltr">{product.code}</span> —{" "}
                      {getLocalizedName(product, language)}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  label={t("crmInstallationForm.module")}
                  value={component.product_module_id}
                  onChange={(event) =>
                    setInstallationComponents((current) =>
                      current.map((row, rowIndex) =>
                        rowIndex === index
                          ? { ...row, product_module_id: event.target.value }
                          : row,
                      ),
                    )
                  }
                  disabled={!component.product_id}
                  fullWidth
                  margin="normal"
                >
                  <MenuItem value="">
                    {t("crmInstallationForm.allModules")}
                  </MenuItem>
                  {installationModules.data
                    ?.filter(
                      (module) =>
                        module.product_id === Number(component.product_id),
                    )
                    .map((module) => (
                      <MenuItem key={module.id} value={module.id}>
                        <span dir="ltr">{module.code}</span> —{" "}
                        {getLocalizedName(module, language)}
                      </MenuItem>
                    ))}
                </TextField>
                <IconButton
                  aria-label={t("crmInstallationForm.remove")}
                  disabled={installationComponents.length === 1}
                  onClick={() =>
                    setInstallationComponents((current) =>
                      current.filter((_, rowIndex) => rowIndex !== index),
                    )
                  }
                >
                  <Delete />
                </IconButton>
              </Stack>
            ))}
            <Button
              startIcon={<Add />}
              onClick={() =>
                setInstallationComponents((current) => [
                  ...current,
                  { product_id: "", product_module_id: "" },
                ])
              }
            >
              {t("crmInstallationForm.addComponent")}
            </Button>
            <TextField
              select
              name="environment_id"
              label={t("crmInstallationForm.environment")}
              defaultValue={editingInstallation?.environment_id ?? ""}
              required
              fullWidth
              margin="normal"
            >
              {environments.data?.map((environment) => (
                <MenuItem key={environment.id} value={environment.id}>
                  {getLocalizedName(environment, language)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="installation_name"
              label={t("crmInstallationForm.name")}
              defaultValue={editingInstallation?.installation_name ?? ""}
              required
              fullWidth
              margin="normal"
            />
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                name="version"
                label={t("crmInstallationForm.version")}
                defaultValue={editingInstallation?.version ?? ""}
                fullWidth
                margin="normal"
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="support_owner"
                label={t("crmInstallationForm.owner")}
                defaultValue={editingInstallation?.support_owner ?? ""}
                fullWidth
                margin="normal"
              />
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                name="server_name"
                label={t("crmInstallationForm.server")}
                defaultValue={editingInstallation?.server_name ?? ""}
                fullWidth
                margin="normal"
                helperText={t("crmInstallationForm.serverHelp")}
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                name="database_name"
                label={t("crmInstallationForm.database")}
                defaultValue={editingInstallation?.database_name ?? ""}
                fullWidth
                margin="normal"
                helperText={t("crmInstallationForm.databaseHelp")}
                inputProps={{ dir: "ltr" }}
              />
            </Stack>
            <FormControlLabel
              control={
                <Switch
                  name="is_active"
                  defaultChecked={editingInstallation?.is_active ?? true}
                />
              }
              label={t("crmInstallationForm.active")}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={closeInstallation}>
              {t("crmInstallationForm.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={
                saveInstallation.isPending ||
                !installationClientId ||
                installationComponents.some(
                  (component) => !component.product_id,
                )
              }
            >
              {t("crmInstallationForm.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
    </Paper>
  );
}
