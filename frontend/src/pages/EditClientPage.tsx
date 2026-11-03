import { Add, Download, Edit } from "@mui/icons-material";
import {
  Alert,
  Breadcrumbs,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Link,
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
import axios from "axios";
import { FormEvent, useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { MobileMultiAutocomplete } from "../components/MobileMultiAutocomplete";
import { useAuth } from "../auth/AuthContext";
import { ClientAccessVault } from "./ClientAccessVault";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { serverDateInput } from "../utils/serverTime";

type Client = {
  id: number;
  code: string;
  name: string;
  status_id: number;
  owner_department_id: number | null;
  shared_department_ids: number[];
  parent_client_id: number | null;
  timezone: string;
  country_id: number | null;
  city_id: number | null;
  primary_location_id: number | null;
  phone_number: string | null;
  email: string | null;
  address: string | null;
  notes: string | null;
  support_started_at: string | null;
  is_active: boolean;
};
type Department = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  is_active: boolean;
};
type HierarchyNode = {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  parent_client_id: number | null;
  depth: number;
  hierarchy_path: string;
  direct_child_count: number;
  descendant_count: number;
};
type Hierarchy = {
  client: HierarchyNode;
  ancestors: HierarchyNode[];
  descendants: HierarchyNode[];
};
type ClientProfile = {
  metrics: Record<string, number | null>;
  business_impacts: Array<{
    area: string;
    level: string;
    consequence: string;
    evidence: string;
    action: string;
  }>;
};
type Status = { id: number; code: string; name: string; name_ar?: string };
type Branch = {
  id: number;
  client_id: number;
  code: string;
  name: string;
  timezone?: string;
  phone_number?: string;
  email?: string;
  address?: string;
  support_hours?: string;
  escalation_contact_id?: number;
  is_active: boolean;
};
type Contact = {
  id: number;
  client_id: number;
  branch_id?: number;
  full_name: string;
  email?: string;
  phone_number?: string;
  job_title?: string;
  contact_role?: string;
  is_primary: boolean;
  is_active: boolean;
  is_escalation_contact: boolean;
};
type Country = { id: number; name: string; name_ar?: string; code: string };
type City = {
  id: number;
  country_id: number;
  name: string;
  name_ar?: string;
  code: string;
};
type ClientLocation = {
  id: number;
  client_id: number;
  country_id: number;
  code: string;
  name: string;
  zone?: string;
  address?: string;
  timezone?: string;
  latitude?: number;
  longitude?: number;
  is_active: boolean;
};

export function EditClientPage() {
  const { i18n, t } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const { id } = useParams();
  const { hasPermission } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [branchOpen, setBranchOpen] = useState(false);
  const [editingBranch, setEditingBranch] = useState<Branch | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);
  const [locationOpen, setLocationOpen] = useState(false);
  const [countryOpen, setCountryOpen] = useState(false);
  const [cityOpen, setCityOpen] = useState(false);
  const [selectedCountryId, setSelectedCountryId] = useState("");
  const [ownerDepartmentId, setOwnerDepartmentId] = useState("");
  const [sharedDepartments, setSharedDepartments] = useState<Department[]>([]);
  const today = serverDateInput();
  const [reportFrom, setReportFrom] = useState(`${today.slice(0, 8)}01`);
  const [reportTo, setReportTo] = useState(today);
  const [reportPreviewOpen, setReportPreviewOpen] = useState(false);
  const client = useQuery({
    queryKey: ["client", id],
    queryFn: async () => (await api.get<Client>(`/clients/${id}`)).data,
    enabled: Boolean(id),
  });
  const allClients = useQuery({
    queryKey: ["clients", "hierarchy-parent-options"],
    queryFn: async () =>
      (
        await api.get<Client[]>("/clients", {
          params: { account_status: "ALL", active_only: false, limit: 200 },
        })
      ).data,
  });
  const hierarchy = useQuery({
    queryKey: ["client-hierarchy", id],
    queryFn: async () =>
      (await api.get<Hierarchy>(`/clients/${id}/hierarchy`)).data,
    enabled: Boolean(id),
  });
  const statuses = useQuery({
    queryKey: ["client-statuses"],
    queryFn: async () => (await api.get<Status[]>("/client-statuses")).data,
  });
  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: async () => (await api.get<Department[]>("/departments")).data,
  });
  useEffect(() => {
    if (client.data && departments.data) {
      setOwnerDepartmentId(String(client.data.owner_department_id ?? ""));
      setSharedDepartments(
        departments.data.filter((department) =>
          client.data!.shared_department_ids.includes(department.id),
        ),
      );
    }
  }, [client.data, departments.data]);
  useEffect(() => {
    if (!client.isLoading && location.hash) {
      window.requestAnimationFrame(() =>
        document
          .getElementById(location.hash.slice(1))
          ?.scrollIntoView({ behavior: "smooth", block: "start" }),
      );
    }
  }, [client.isLoading, location.hash]);
  const branches = useQuery({
    queryKey: ["client-branches", id],
    queryFn: async () =>
      (await api.get<Branch[]>(`/clients/${id}/branches`)).data,
    enabled: Boolean(id),
  });
  const contacts = useQuery({
    queryKey: ["client-contacts", id],
    queryFn: async () =>
      (await api.get<Contact[]>("/contacts", { params: { client_id: id } }))
        .data,
    enabled: Boolean(id),
  });
  const countries = useQuery({
    queryKey: ["countries"],
    queryFn: async () => (await api.get<Country[]>("/countries")).data,
  });
  const cities = useQuery({
    queryKey: ["cities"],
    queryFn: async () => (await api.get<City[]>("/cities")).data,
  });
  const locations = useQuery({
    queryKey: ["client-locations", id],
    queryFn: async () =>
      (await api.get<ClientLocation[]>(`/clients/${id}/locations`)).data,
    enabled: Boolean(id),
  });
  const reportPreview = useQuery({
    queryKey: ["client-profile-report", id, reportFrom, reportTo],
    queryFn: async () =>
      (
        await api.get<ClientProfile>("/reports/client-profile", {
          params: { client_id: id, date_from: reportFrom, date_to: reportTo },
        })
      ).data,
    enabled:
      reportPreviewOpen && Boolean(id) && hasPermission("client.profile.view"),
  });
  const update = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.patch(`/clients/${id}`, payload)).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["clients"] });
      await queryClient.invalidateQueries({ queryKey: ["client", id] });
      await queryClient.invalidateQueries({ queryKey: ["client-hierarchy"] });
    },
  });
  const saveBranch = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingBranch
        ? api.patch(`/clients/${id}/branches/${editingBranch.id}`, payload)
        : api.post(`/clients/${id}/branches`, payload),
    onSuccess: async () => {
      setBranchOpen(false);
      setEditingBranch(null);
      await queryClient.invalidateQueries({
        queryKey: ["client-branches", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["branches"] });
    },
  });
  const saveContact = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editingContact
        ? api.patch(`/contacts/${editingContact.id}`, payload)
        : api.post("/contacts", { ...payload, client_id: Number(id) }),
    onSuccess: async () => {
      setContactOpen(false);
      setEditingContact(null);
      await queryClient.invalidateQueries({
        queryKey: ["client-contacts", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
  const saveLocation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/clients/${id}/locations`, payload),
    onSuccess: async () => {
      setLocationOpen(false);
      await queryClient.invalidateQueries({
        queryKey: ["client-locations", id],
      });
      await queryClient.invalidateQueries({
        queryKey: ["management-metadata"],
      });
    },
  });
  const createCountry = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post<Country>("/countries", payload)).data,
    onSuccess: async (country) => {
      setCountryOpen(false);
      setSelectedCountryId(String(country.id));
      await queryClient.invalidateQueries({ queryKey: ["countries"] });
      await queryClient.invalidateQueries({ queryKey: ["cities"] });
    },
  });
  const createCity = useMutation({
    mutationFn: async (payload: { name: string; name_ar: string }) =>
      api.post("/cities", {
        country_id: Number(selectedCountryId || client.data?.country_id),
        ...payload,
        is_active: true,
      }),
    onSuccess: async () => {
      setCityOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["cities"] });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    update.mutate({
      name: String(values.name).trim(),
      status_id: Number(values.status_id),
      owner_department_id: Number(ownerDepartmentId),
      shared_department_ids: sharedDepartments
        .map((department) => department.id)
        .filter((departmentId) => departmentId !== Number(ownerDepartmentId)),
      parent_client_id: values.parent_client_id
        ? Number(values.parent_client_id)
        : null,
      country_id: values.country_id ? Number(values.country_id) : null,
      city_id: values.city_id ? Number(values.city_id) : null,
      primary_location_id: values.primary_location_id
        ? Number(values.primary_location_id)
        : null,
      timezone: String(values.timezone).trim(),
      email: String(values.email).trim() || null,
      phone_number: String(values.phone_number).trim() || null,
      address: String(values.address).trim() || null,
      notes: String(values.notes).trim() || null,
      support_started_at: values.support_started_at || null,
      is_active: values.is_active === "true",
    });
  }
  async function exportClientReport() {
    const response = await api.get("/portal/contract-report.xlsx", {
      params: { client_id: id, date_from: reportFrom, date_to: reportTo },
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `client_support_report_${reportFrom}_${reportTo}.xlsx`;
    link.click();
    URL.revokeObjectURL(url);
  }
  async function exportClientProfile() {
    const response = await api.get("/reports/client-profile.docx", {
      params: { client_id: id, date_from: reportFrom, date_to: reportTo },
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Millensys-Client-Profile-${client.data?.code}-${reportFrom}-${reportTo}.docx`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function submitBranch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const payload: Record<string, unknown> = {
      name: String(values.name).trim(),
      timezone: String(values.timezone).trim() || null,
      email: String(values.email).trim() || null,
      phone_number: String(values.phone_number).trim() || null,
      address: String(values.address).trim() || null,
      support_hours: String(values.support_hours).trim() || null,
      escalation_contact_id: values.escalation_contact_id
        ? Number(values.escalation_contact_id)
        : null,
      is_active: values.is_active === "true",
    };
    saveBranch.mutate(payload);
  }
  function submitContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveContact.mutate({
      branch_id: values.branch_id ? Number(values.branch_id) : null,
      full_name: String(values.full_name).trim(),
      email: String(values.email).trim() || null,
      phone_number: String(values.phone_number).trim() || null,
      job_title: String(values.job_title).trim() || null,
      contact_role: String(values.contact_role).trim() || null,
      is_primary: values.is_primary === "true",
      is_escalation_contact: values.is_escalation_contact === "true",
      is_active: values.is_active === "true",
    });
  }
  function submitLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    saveLocation.mutate({
      country_id: Number(values.country_id),
      name: String(values.name).trim(),
      zone: String(values.zone).trim() || null,
      address: String(values.address).trim() || null,
      timezone: String(values.timezone).trim() || null,
      latitude: values.latitude ? Number(values.latitude) : null,
      longitude: values.longitude ? Number(values.longitude) : null,
      is_active: true,
    });
  }
  function submitCountry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    createCountry.mutate({
      name: String(values.name).trim(),
      name_ar: String(values.name_ar).trim(),
      city_name: String(values.city_name).trim(),
      city_name_ar: String(values.city_name_ar).trim(),
      is_active: true,
    });
  }
  function submitCity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    createCity.mutate({
      name: String(values.name).trim(),
      name_ar: String(values.name_ar).trim(),
    });
  }
  const closeBranch = () => {
    setBranchOpen(false);
    setEditingBranch(null);
  };
  const updateError = axios.isAxiosError(update.error)
    ? (update.error.response?.data?.error?.message ??
      t("editClient.updateFailed"))
    : t("editClient.updateFailed");
  const branchError = axios.isAxiosError(saveBranch.error)
    ? (saveBranch.error.response?.data?.error?.message ??
      t("editClient.branchFailed"))
    : t("editClient.branchFailed");
  const contactError = axios.isAxiosError(saveContact.error)
    ? (saveContact.error.response?.data?.error?.message ??
      t("editClient.contactFailed"))
    : t("editClient.contactFailed");
  if (client.isLoading || statuses.isLoading) return <CircularProgress />;
  if (client.isError || !client.data)
    return <Alert severity="error">{t("editClient.loadFailed")}</Alert>;

  return (
    <Stack spacing={3} sx={{ maxWidth: 1000 }}>
      {hierarchy.data && (
        <Paper sx={{ p: 2 }}>
          <Breadcrumbs aria-label={t("editClient.hierarchy")}>
            {hierarchy.data.ancestors.map((node) => (
              <Link
                component="button"
                underline="hover"
                key={node.id}
                onClick={() => navigate(`/clients/${node.id}/edit`)}
              >
                {node.name}
              </Link>
            ))}
            <Typography color="text.primary">
              {hierarchy.data.client.name}
            </Typography>
          </Breadcrumbs>
          <Typography variant="body2" color="text.secondary" mt={1}>
            {t("editClient.children", {
              direct: hierarchy.data.client.direct_child_count,
              total: hierarchy.data.client.descendant_count,
            })}
          </Typography>
          {hierarchy.data.descendants.length > 0 && (
            <Stack mt={1} spacing={0.5}>
              {hierarchy.data.descendants.map((node) => (
                <Link
                  component="button"
                  textAlign="left"
                  underline="hover"
                  key={node.id}
                  onClick={() => navigate(`/clients/${node.id}/edit`)}
                  sx={{
                    pl:
                      Math.max(
                        0,
                        node.depth - hierarchy.data.client.depth - 1,
                      ) * 2,
                  }}
                >
                  {node.name}{" "}
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.secondary"
                  >
                    ({node.hierarchy_path})
                  </Typography>
                </Link>
              ))}
            </Stack>
          )}
        </Paper>
      )}
      <Paper sx={{ p: 2 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ md: "center" }}
        >
          <Typography variant="h6" flexGrow={1}>
            {t("editClient.serviceProfile")}
          </Typography>
          <TextField
            size="small"
            type="date"
            label={t("editClient.from")}
            value={reportFrom}
            onChange={(event) => setReportFrom(event.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            size="small"
            type="date"
            label={t("editClient.to")}
            value={reportTo}
            onChange={(event) => setReportTo(event.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          {hasPermission("client.profile.view") && (
            <Button
              variant="contained"
              onClick={() => navigate(`/clients/${id}/profile`)}
            >
              {t("editClient.openProfile")}
            </Button>
          )}
          {hasPermission("report.export") && (
            <>
              <Button startIcon={<Download />} onClick={exportClientProfile}>
                {t("editClient.brandedWord")}
              </Button>
              <Button startIcon={<Download />} onClick={exportClientReport}>
                {t("editClient.excelEvidence")}
              </Button>
            </>
          )}
        </Stack>
        <Typography variant="body2" color="text.secondary" mt={1}>
          {t("editClient.profileHint")}
        </Typography>
      </Paper>
      <Paper
        id="client-info"
        component="form"
        onSubmit={submit}
        sx={{ p: 3, scrollMarginTop: 96 }}
      >
        <Typography variant="h4" gutterBottom>
          {t("editClient.title")}
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          {t("editClient.clientCode", { code: client.data.code })}
        </Typography>
        {update.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {updateError}
          </Alert>
        )}
        {update.isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {t("editClient.saved")}
          </Alert>
        )}
        <TextField
          name="name"
          label={t("clients.clientName")}
          required
          fullWidth
          margin="normal"
          defaultValue={client.data.name}
        />
        <TextField
          label={t("clients.ownerDepartment")}
          select
          required
          fullWidth
          margin="normal"
          value={ownerDepartmentId}
          onChange={(event) => {
            setOwnerDepartmentId(event.target.value);
            setSharedDepartments((current) =>
              current.filter(
                (department) => department.id !== Number(event.target.value),
              ),
            );
          }}
        >
          {departments.data?.map((department) => (
            <MenuItem key={department.id} value={department.id}>
              {getLocalizedName(department, language)}
            </MenuItem>
          ))}
        </TextField>
        <MobileMultiAutocomplete
          options={(departments.data ?? []).filter(
            (department) => department.id !== Number(ownerDepartmentId),
          )}
          value={sharedDepartments}
          onChange={(_, value) => setSharedDepartments(value)}
          getOptionLabel={(department) =>
            getLocalizedName(department, language)
          }
          isOptionEqualToValue={(option, value) => option.id === value.id}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("clients.sharedDepartments")}
              margin="normal"
              helperText={t("editClient.sharedHint")}
            />
          )}
        />
        <TextField
          name="parent_client_id"
          label={t("clients.parentOptional")}
          select
          fullWidth
          margin="normal"
          defaultValue={client.data.parent_client_id ?? ""}
          helperText={t("editClient.parentHint")}
        >
          <MenuItem value="">{t("clients.rootClient")}</MenuItem>
          {allClients.data
            ?.filter((item) => item.id !== client.data.id)
            .map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name} ({item.code})
                {item.is_active ? "" : ` — ${t("clients.inactive")}`}
              </MenuItem>
            ))}
        </TextField>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            name="status_id"
            label={t("clients.status")}
            select
            required
            fullWidth
            margin="normal"
            defaultValue={client.data.status_id}
          >
            {statuses.data?.map((status) => (
              <MenuItem key={status.id} value={status.id}>
                {getLocalizedName(status, language)}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            name="is_active"
            label={t("clients.account")}
            select
            required
            fullWidth
            margin="normal"
            defaultValue={String(client.data.is_active)}
          >
            <MenuItem value="true">{t("clients.active")}</MenuItem>
            <MenuItem value="false">{t("clients.inactive")}</MenuItem>
          </TextField>
        </Stack>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            name="country_id"
            label={t("clients.countryOptional")}
            select
            fullWidth
            margin="normal"
            defaultValue={client.data.country_id ?? ""}
            onChange={(event) => setSelectedCountryId(event.target.value)}
          >
            <MenuItem value="">{t("editClient.notSpecified")}</MenuItem>
            {countries.data?.map((country) => (
              <MenuItem key={country.id} value={country.id}>
                {getLocalizedName(country, language)} ({country.code})
              </MenuItem>
            ))}
          </TextField>
          <TextField
            name="city_id"
            label={t("clients.cityOptional")}
            select
            fullWidth
            margin="normal"
            defaultValue={client.data.city_id ?? ""}
            disabled={!Number(selectedCountryId || client.data.country_id)}
          >
            <MenuItem value="">{t("editClient.notSpecified")}</MenuItem>
            {cities.data
              ?.filter(
                (city) =>
                  city.country_id ===
                  Number(selectedCountryId || client.data.country_id),
              )
              .map((city) => (
                <MenuItem key={city.id} value={city.id}>
                  {getLocalizedName(city, language)}
                </MenuItem>
              ))}
          </TextField>
          <TextField
            name="primary_location_id"
            label={t("editClient.primaryLocation")}
            select
            fullWidth
            margin="normal"
            defaultValue={client.data.primary_location_id ?? ""}
          >
            <MenuItem value="">{t("editClient.notSpecified")}</MenuItem>
            {locations.data?.map((location) => (
              <MenuItem key={location.id} value={location.id}>
                {location.name}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
        <Stack direction="row" gap={1}>
          <Button size="small" onClick={() => setCountryOpen(true)}>
            {t("editClient.addCountryCity")}
          </Button>
          <Button
            size="small"
            disabled={!Number(selectedCountryId || client.data.country_id)}
            onClick={() => setCityOpen(true)}
          >
            {t("editClient.addCity")}
          </Button>
        </Stack>
        <TextField
          name="timezone"
          label={t("clients.timezone")}
          required
          fullWidth
          margin="normal"
          defaultValue={client.data.timezone}
          inputProps={{ dir: "ltr" }}
        />
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            name="email"
            label={t("clients.supportEmail")}
            type="email"
            fullWidth
            margin="normal"
            defaultValue={client.data.email ?? ""}
            inputProps={{ dir: "ltr" }}
          />
          <TextField
            name="phone_number"
            label={t("clients.phone")}
            fullWidth
            margin="normal"
            defaultValue={client.data.phone_number ?? ""}
            inputProps={{ dir: "ltr" }}
          />
        </Stack>
        <TextField
          name="address"
          label={t("clients.address")}
          fullWidth
          multiline
          rows={2}
          margin="normal"
          defaultValue={client.data.address ?? ""}
        />
        <TextField
          name="notes"
          label={t("clients.internalNotes")}
          fullWidth
          multiline
          rows={3}
          margin="normal"
          defaultValue={client.data.notes ?? ""}
        />
        <TextField
          name="support_started_at"
          type="date"
          label={t("editClient.supportStart")}
          fullWidth
          margin="normal"
          defaultValue={client.data.support_started_at ?? ""}
          slotProps={{ inputLabel: { shrink: true } }}
          helperText={t("editClient.supportStartHint")}
        />
        {hasPermission("client.manage") && (
          <Button type="submit" variant="contained" disabled={update.isPending}>
            {update.isPending
              ? t("editClient.saving")
              : t("editClient.saveChanges")}
          </Button>
        )}
        <Button
          onClick={() =>
            navigate(
              (location.state as { clientsList?: string } | null)
                ?.clientsList ?? "/clients",
            )
          }
          sx={{ ml: 1 }}
        >
          {t("editClient.back")}
        </Button>
      </Paper>

      <Paper id="client-contacts" sx={{ p: 3, scrollMarginTop: 96 }}>
        <Stack direction="row" alignItems="center" mb={2}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            {t("editClient.locationsTitle")}
          </Typography>
          {hasPermission("client.manage") && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setLocationOpen(true)}
            >
              {t("editClient.addLocation")}
            </Button>
          )}
        </Stack>
        <Typography color="text.secondary" mb={2}>
          {t("editClient.locationsHint")}
        </Typography>
        {locations.data?.length === 0 && (
          <Alert severity="info">{t("editClient.noLocations")}</Alert>
        )}
        {!!locations.data?.length && (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("clients.code")}</TableCell>
                <TableCell>{t("editClient.location")}</TableCell>
                <TableCell>{t("editClient.country")}</TableCell>
                <TableCell>{t("editClient.zone")}</TableCell>
                <TableCell>{t("editClient.coordinates")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {locations.data.map((location) => (
                <TableRow key={location.id}>
                  <TableCell>{location.code}</TableCell>
                  <TableCell>
                    {location.name}
                    <Typography variant="body2" color="text.secondary">
                      {location.address ?? "—"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {getLocalizedName(
                      countries.data?.find(
                        (country) => country.id === location.country_id,
                      ),
                      language,
                    ) ?? "—"}
                  </TableCell>
                  <TableCell>{location.zone ?? "—"}</TableCell>
                  <TableCell>
                    {location.latitude != null && location.longitude != null
                      ? `${location.latitude}, ${location.longitude}`
                      : t("editClient.notSet")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>

      <ClientAccessVault clientId={id!} />

      <Paper sx={{ p: 3 }}>
        <Stack direction="row" alignItems="center" mb={2}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            {t("editClient.contactsTitle")}
          </Typography>
          {hasPermission("contact.manage") && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setContactOpen(true)}
            >
              {t("editClient.addCaller")}
            </Button>
          )}
        </Stack>
        <Typography color="text.secondary" mb={2}>
          {t("editClient.contactsHint")}
        </Typography>
        {contacts.isLoading && <CircularProgress size={24} />}
        {contacts.isError && (
          <Alert severity="error">{t("editClient.contactsFailed")}</Alert>
        )}
        {contacts.data?.length === 0 && (
          <Alert severity="info">{t("editClient.noCallers")}</Alert>
        )}
        {!!contacts.data?.length && (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("clients.contact")}</TableCell>
                <TableCell>{t("editClient.mobile")}</TableCell>
                <TableCell>{t("editClient.email")}</TableCell>
                <TableCell>{t("editClient.branch")}</TableCell>
                <TableCell>{t("editClient.role")}</TableCell>
                <TableCell>{t("clients.status")}</TableCell>
                <TableCell align="right">{t("clients.actions")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {contacts.data.map((contact) => (
                <TableRow key={contact.id}>
                  <TableCell>
                    <Typography fontWeight={700}>
                      {contact.full_name}
                    </Typography>
                    {contact.is_primary && (
                      <Chip
                        size="small"
                        color="primary"
                        label={t("editClient.primary")}
                      />
                    )}
                  </TableCell>
                  <TableCell>{contact.phone_number ?? "—"}</TableCell>
                  <TableCell>{contact.email ?? "—"}</TableCell>
                  <TableCell>
                    {branches.data?.find(
                      (branch) => branch.id === contact.branch_id,
                    )?.name ?? t("editClient.allSites")}
                  </TableCell>
                  <TableCell>
                    {contact.job_title ?? contact.contact_role ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={contact.is_active ? "success" : "default"}
                      label={
                        contact.is_active
                          ? t("clients.active")
                          : t("clients.inactive")
                      }
                    />
                    {contact.is_escalation_contact && (
                      <Chip
                        size="small"
                        color="warning"
                        label={t("editClient.escalation")}
                        sx={{ ml: 0.5 }}
                      />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {hasPermission("contact.manage") && (
                      <IconButton
                        aria-label={t("clients.editName", {
                          name: contact.full_name,
                        })}
                        onClick={() => {
                          setEditingContact(contact);
                          setContactOpen(true);
                        }}
                      >
                        <Edit />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack direction="row" alignItems="center" mb={2}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            {t("editClient.branchesTitle")}
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setBranchOpen(true)}
          >
            {t("editClient.addBranch")}
          </Button>
        </Stack>
        {branches.isLoading && <CircularProgress size={24} />}
        {branches.isError && (
          <Alert severity="error">{t("editClient.branchesFailed")}</Alert>
        )}
        {branches.data?.length === 0 && (
          <Alert severity="info">{t("editClient.noBranches")}</Alert>
        )}
        {!!branches.data?.length && (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t("clients.code")}</TableCell>
                <TableCell>{t("editClient.branch")}</TableCell>
                <TableCell>{t("clients.contact")}</TableCell>
                <TableCell>{t("clients.timezone")}</TableCell>
                <TableCell>{t("clients.status")}</TableCell>
                <TableCell align="right">{t("clients.actions")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {branches.data.map((branch) => (
                <TableRow key={branch.id}>
                  <TableCell>{branch.code}</TableCell>
                  <TableCell>
                    {branch.name}
                    <Typography variant="body2" color="text.secondary">
                      {branch.address ?? "—"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {branch.email ?? "—"}
                    <Typography variant="body2" color="text.secondary">
                      {branch.phone_number ?? "—"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {branch.timezone ?? client.data.timezone}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={
                        branch.is_active
                          ? t("clients.active")
                          : t("clients.inactive")
                      }
                      color={branch.is_active ? "success" : "default"}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      aria-label={t("clients.editName", { name: branch.name })}
                      onClick={() => {
                        setEditingBranch(branch);
                        setBranchOpen(true);
                      }}
                    >
                      <Edit />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>

      <Dialog
        open={locationOpen}
        onClose={() => setLocationOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Stack component="form" onSubmit={submitLocation}>
          <DialogTitle>{t("editClient.locationDialog")}</DialogTitle>
          <DialogContent>
            {saveLocation.isError && (
              <Alert severity="error">{t("editClient.locationFailed")}</Alert>
            )}
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("editClient.locationCodeAutomatic")}
            </Alert>
            <TextField
              required
              select
              name="country_id"
              label={t("editClient.country")}
              defaultValue=""
              fullWidth
              margin="normal"
            >
              {countries.data?.map((country) => (
                <MenuItem key={country.id} value={country.id}>
                  {getLocalizedName(country, language)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              required
              name="name"
              label={t("editClient.locationName")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="zone"
              label={t("editClient.zoneRegion")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="timezone"
              label={t("clients.timezone")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="address"
              label={t("clients.address")}
              multiline
              rows={2}
              fullWidth
              margin="normal"
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <TextField
                name="latitude"
                type="number"
                label={t("editClient.latitude")}
                fullWidth
                margin="normal"
                inputProps={{ min: -90, max: 90, step: "any" }}
              />
              <TextField
                name="longitude"
                type="number"
                label={t("editClient.longitude")}
                fullWidth
                margin="normal"
                inputProps={{ min: -180, max: 180, step: "any" }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setLocationOpen(false)}>
              {t("clients.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveLocation.isPending}
            >
              {t("editClient.saveLocation")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={countryOpen}
        onClose={() => setCountryOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <Stack component="form" onSubmit={submitCountry}>
          <DialogTitle>{t("clients.addCountryCity")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="name"
              label={t("clients.countryNameEn")}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              required
              name="name_ar"
              label={t("clients.countryNameAr")}
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
            <TextField
              required
              name="city_name"
              label={t("clients.cityNameEn")}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              required
              name="city_name_ar"
              label={t("clients.cityNameAr")}
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCountryOpen(false)}>
              {t("clients.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("ticketsList.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={cityOpen}
        onClose={() => setCityOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <Stack component="form" onSubmit={submitCity}>
          <DialogTitle>{t("editClient.addCity")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="name"
              label={t("clients.cityNameEn")}
              fullWidth
              margin="normal"
              inputProps={{ dir: "ltr" }}
            />
            <TextField
              required
              name="name_ar"
              label={t("clients.cityNameAr")}
              fullWidth
              margin="normal"
              inputProps={{ dir: "rtl" }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCityOpen(false)}>
              {t("clients.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("ticketsList.save")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog open={branchOpen} onClose={closeBranch} fullWidth maxWidth="sm">
        <Stack
          component="form"
          key={editingBranch?.id ?? "new"}
          onSubmit={submitBranch}
        >
          <DialogTitle>
            {editingBranch
              ? t("editClient.editBranch")
              : t("editClient.addBranch")}
          </DialogTitle>
          <DialogContent>
            {saveBranch.isError && (
              <Alert severity="error">{branchError}</Alert>
            )}
            {editingBranch ? (
              <TextField
                label={t("editClient.branchCode")}
                value={editingBranch.code}
                disabled
                helperText={t("editClient.generated")}
                fullWidth
                margin="normal"
              />
            ) : (
              <Alert severity="info" sx={{ mt: 1 }}>
                {t("editClient.branchCodeAutomatic")}
              </Alert>
            )}
            <TextField
              name="name"
              label={t("editClient.branchName")}
              defaultValue={editingBranch?.name ?? ""}
              required
              fullWidth
              margin="normal"
            />
            <TextField
              name="timezone"
              label={t("editClient.timezoneOverride")}
              defaultValue={editingBranch?.timezone ?? ""}
              fullWidth
              margin="normal"
              helperText={t("editClient.inheritTimezone", {
                timezone: client.data.timezone,
              })}
            />
            <TextField
              name="email"
              label={t("editClient.email")}
              type="email"
              defaultValue={editingBranch?.email ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="phone_number"
              label={t("clients.phone")}
              defaultValue={editingBranch?.phone_number ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="address"
              label={t("clients.address")}
              defaultValue={editingBranch?.address ?? ""}
              multiline
              rows={2}
              fullWidth
              margin="normal"
            />
            <TextField
              name="support_hours"
              label={t("editClient.localHours")}
              defaultValue={editingBranch?.support_hours ?? ""}
              fullWidth
              margin="normal"
              helperText={t("editClient.hoursExample")}
            />
            <TextField
              select
              name="escalation_contact_id"
              label={t("editClient.escalationContact")}
              defaultValue={editingBranch?.escalation_contact_id ?? ""}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("editClient.notAssigned")}</MenuItem>
              {contacts.data
                ?.filter((contact) => contact.is_active)
                .map((contact) => (
                  <MenuItem key={contact.id} value={contact.id}>
                    {contact.full_name}
                    {contact.is_escalation_contact
                      ? ` — ${t("editClient.escalation")}`
                      : ""}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              name="is_active"
              label={t("clients.status")}
              select
              defaultValue={String(editingBranch?.is_active ?? true)}
              required
              fullWidth
              margin="normal"
            >
              <MenuItem value="true">{t("clients.active")}</MenuItem>
              <MenuItem value="false">{t("clients.inactive")}</MenuItem>
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeBranch}>{t("clients.cancel")}</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveBranch.isPending}
            >
              {t("editClient.saveBranch")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={contactOpen}
        onClose={() => {
          setContactOpen(false);
          setEditingContact(null);
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
            {editingContact
              ? t("editClient.editCaller")
              : t("editClient.addCaller")}
          </DialogTitle>
          <DialogContent>
            {saveContact.isError && (
              <Alert severity="error">{contactError}</Alert>
            )}
            <TextField
              required
              name="full_name"
              label={t("editClient.fullName")}
              defaultValue={editingContact?.full_name ?? ""}
              fullWidth
              margin="normal"
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <TextField
                name="phone_number"
                label={t("editClient.mobileNumber")}
                defaultValue={editingContact?.phone_number ?? ""}
                fullWidth
                margin="normal"
              />
              <TextField
                name="email"
                label={t("editClient.email")}
                type="email"
                defaultValue={editingContact?.email ?? ""}
                fullWidth
                margin="normal"
              />
            </Stack>
            <TextField
              select
              name="branch_id"
              label={t("editClient.branchSite")}
              defaultValue={editingContact?.branch_id ?? ""}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("editClient.allSites")}</MenuItem>
              {branches.data?.map((branch) => (
                <MenuItem key={branch.id} value={branch.id}>
                  {branch.name}
                </MenuItem>
              ))}
            </TextField>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <TextField
                name="job_title"
                label={t("editClient.jobTitle")}
                defaultValue={editingContact?.job_title ?? ""}
                fullWidth
                margin="normal"
              />
              <TextField
                name="contact_role"
                label={t("editClient.contactRole")}
                defaultValue={editingContact?.contact_role ?? ""}
                fullWidth
                margin="normal"
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <TextField
                select
                name="is_primary"
                label={t("editClient.primaryCaller")}
                defaultValue={String(editingContact?.is_primary ?? false)}
                fullWidth
                margin="normal"
              >
                <MenuItem value="false">{t("editClient.no")}</MenuItem>
                <MenuItem value="true">{t("editClient.yes")}</MenuItem>
              </TextField>
              <TextField
                select
                name="is_escalation_contact"
                label={t("editClient.escalationContact")}
                defaultValue={String(
                  editingContact?.is_escalation_contact ?? false,
                )}
                fullWidth
                margin="normal"
              >
                <MenuItem value="false">{t("editClient.no")}</MenuItem>
                <MenuItem value="true">{t("editClient.yes")}</MenuItem>
              </TextField>
              <TextField
                select
                name="is_active"
                label={t("clients.status")}
                defaultValue={String(editingContact?.is_active ?? true)}
                fullWidth
                margin="normal"
              >
                <MenuItem value="true">{t("clients.active")}</MenuItem>
                <MenuItem value="false">{t("clients.inactive")}</MenuItem>
              </TextField>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setContactOpen(false);
                setEditingContact(null);
              }}
            >
              {t("clients.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saveContact.isPending}
            >
              {saveContact.isPending
                ? t("editClient.saving")
                : t("editClient.saveCaller")}
            </Button>
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={reportPreviewOpen}
        onClose={() => setReportPreviewOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>{t("editClient.previewTitle")}</DialogTitle>
        <DialogContent>
          {reportPreview.isLoading && <CircularProgress />}
          {reportPreview.isError && (
            <Alert severity="error">{t("editClient.previewFailed")}</Alert>
          )}
          {reportPreview.data && (
            <Stack spacing={1.5}>
              {reportPreview.data.business_impacts.map((impact) => (
                <Paper
                  key={impact.area}
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    borderLeft: 5,
                    borderLeftColor:
                      impact.level === "CRITICAL"
                        ? "error.main"
                        : impact.level === "HIGH"
                          ? "warning.main"
                          : impact.level === "POSITIVE"
                            ? "success.main"
                            : "info.main",
                  }}
                >
                  <Stack direction="row" gap={1} alignItems="center">
                    <Typography fontWeight={800} flexGrow={1}>
                      {impact.area}
                    </Typography>
                    <Chip
                      size="small"
                      label={impact.level}
                      color={
                        impact.level === "CRITICAL"
                          ? "error"
                          : impact.level === "HIGH"
                            ? "warning"
                            : impact.level === "POSITIVE"
                              ? "success"
                              : "info"
                      }
                    />
                  </Stack>
                  <Typography variant="body2" mt={0.5}>
                    {impact.consequence}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <b>{t("clientProfile.evidence")}</b> {impact.evidence}
                  </Typography>
                  <Typography variant="body2" color="primary">
                    <b>{t("clientProfile.action")}</b> {impact.action}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReportPreviewOpen(false)}>
            {t("editClient.close")}
          </Button>
          {hasPermission("report.export") && (
            <Button
              startIcon={<Download />}
              variant="contained"
              onClick={exportClientProfile}
            >
              {t("editClient.generateWord")}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
