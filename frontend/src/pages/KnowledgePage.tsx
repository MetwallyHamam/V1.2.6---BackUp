import {
  Add,
  Close,
  Clear,
  Delete,
  Download,
  Edit,
  ExpandMore,
  FilterAlt,
  History,
  Link,
  MenuBook,
  OpenInNew,
  Publish,
  Search,
  Settings,
  Unpublished,
  UploadFile,
} from "@mui/icons-material";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Article = {
  id: number;
  title: string;
  summary: string;
  body: string;
  content_type: "ARTICLE" | "DOWNLOAD";
  download_category_id?: number | null;
  status: string;
  category?: string;
  category_id?: number | null;
  tags?: string;
  client_visible: boolean;
  visibility: "INTERNAL" | "CLIENT_PORTAL" | "BOTH";
  product_ids: number[];
  product_module_ids: number[];
  service_ids: number[];
  client_ids: number[];
  resolution_summary_template?: string | null;
  root_cause_ids: number[];
  resolution_service_ids: number[];
  resolution_outcome_id?: number | null;
  permanent_fix_summary_template?: string | null;
  permanent_fix_status?: "PLANNED" | "IMPLEMENTED" | "NOT_REQUIRED" | null;
};
type ArticleVersion = {
  id: number;
  version: number;
  title: string;
  summary: string;
  body: string;
  status: string;
  changed_by_name: string;
  created_at: string;
};
type Resource = {
  id: number;
  article_id: number;
  resource_type: "URL" | "FILE";
  name: string;
  description?: string;
  external_url?: string;
  original_filename?: string;
  size_bytes?: number;
  sha256?: string;
  created_at: string;
};
type TrainingResource = { id: number; name: string; type: string; url: string };
type TrainingMaterial = {
  id: number;
  title: string;
  description?: string;
  category_id?: number;
  required: boolean;
  resources: TrainingResource[];
};
type MaterialCategory = { id: number; name: string; is_active: boolean };
type Option = { id: number; name: string; code?: string; product_id?: number; is_active?: boolean };

export type KnowledgeSection = "articles" | "downloads" | "training";
export function resolveKnowledgeSection(
  requested: string | null,
  canViewTraining: boolean,
): KnowledgeSection {
  if (requested === "downloads") return "downloads";
  return requested === "training" && canViewTraining ? "training" : "articles";
}
export function trainingMaterialsEndpoint(portalUser: boolean) {
  return portalUser ? "/portal/training-materials" : "/onboarding/materials";
}

export function KnowledgePage() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const { user, hasPermission: rawHasPermission } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const administer = searchParams.get("admin") === "1";
  const portalUser = user?.user_type === "CLIENT_PORTAL";
  const canViewTraining =
    !portalUser || rawHasPermission("portal.training.view");
  const hasPermission = rawHasPermission;
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<KnowledgeSection>(() =>
    resolveKnowledgeSection(searchParams.get("section"), canViewTraining),
  );
  const [search, setSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [downloadCategoryFilter, setDownloadCategoryFilter] = useState("");
  const [categoryManagerOpen, setCategoryManagerOpen] = useState(false);
  const [categoryName, setCategoryName] = useState("");
  const [categoryEditing, setCategoryEditing] = useState<Option | null>(null);
  const [newContentType, setNewContentType] = useState<"ARTICLE" | "DOWNLOAD">(
    "ARTICLE",
  );
  const [productFilter, setProductFilter] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [clientFilter, setClientFilter] = useState("");
  const [selected, setSelected] = useState<Article | null>(null);
  const [editing, setEditing] = useState<Article | null>(null);
  const [historyArticle, setHistoryArticle] = useState<Article | null>(null);
  const [deleting, setDeleting] = useState<Article | null>(null);
  const [unlinkBeforeDelete, setUnlinkBeforeDelete] = useState(false);
  const [error, setError] = useState("");
  const [resourceOpen, setResourceOpen] = useState<"URL" | "FILE" | null>(null);
  const [resourceFile, setResourceFile] = useState<File | null>(null);
  const query = useQuery({
    queryKey: [
      "knowledge",
      search,
      categoryFilter,
      productFilter,
      moduleFilter,
      clientFilter,
      downloadCategoryFilter,
      section,
    ],
    queryFn: async () =>
      (
        await api.get<Article[]>("/knowledge", {
          params: {
            search: search || undefined,
            category_id: categoryFilter || undefined,
            product_id: productFilter || undefined,
            product_module_id: moduleFilter || undefined,
            client_id: clientFilter || undefined,
            content_type: section === "downloads" ? "DOWNLOAD" : "ARTICLE",
            download_category_id:
              section === "downloads" ? downloadCategoryFilter || undefined : undefined,
          },
        })
      ).data,
    enabled: section === "articles" || section === "downloads",
  });
  const categories = useQuery({
    queryKey: ["knowledge-categories"],
    queryFn: async () =>
      (await api.get<Option[]>("/knowledge/categories")).data,
    enabled: (section === "articles" || section === "downloads") && !portalUser,
  });
  const downloadCategories = useQuery({
    queryKey: ["knowledge-download-categories", categoryManagerOpen],
    queryFn: async () =>
      (await api.get<Option[]>("/knowledge/download-categories", {
        params: { include_inactive: categoryManagerOpen || undefined },
      })).data,
    enabled: section === "downloads" || open || Boolean(editing) || categoryManagerOpen,
  });
  const products = useQuery({
    queryKey: ["knowledge-products"],
    queryFn: async () => (await api.get<Option[]>("/products")).data,
    enabled: (section === "articles" || section === "downloads") && !portalUser,
  });
  const modules = useQuery({
    queryKey: [
      "knowledge-product-modules",
      products.data?.map((row) => row.id),
    ],
    queryFn: async () => {
      const responses = await Promise.all(
        (products.data ?? []).map((product) =>
          api.get<Option[]>(`/products/${product.id}/modules`),
        ),
      );
      return responses.flatMap((response) => response.data);
    },
    enabled:
      (section === "articles" || section === "downloads") && !portalUser && Boolean(products.data?.length),
  });
  const clients = useQuery({
    queryKey: ["knowledge-clients"],
    queryFn: async () =>
      (await api.get<Option[]>("/clients", { params: { limit: 200 } })).data,
    enabled: (section === "articles" || section === "downloads") && !portalUser,
  });
  const services = useQuery({
    queryKey: ["knowledge-services"],
    queryFn: async () => (await api.get<Option[]>("/services")).data,
    enabled: (section === "articles" || section === "downloads") && !portalUser,
  });
  const rootCauses = useQuery({
    queryKey: ["knowledge-root-causes"],
    queryFn: async () => (await api.get<Option[]>("/root-causes")).data,
    enabled: section === "articles" && !portalUser,
  });
  const resolutionOutcomes = useQuery({
    queryKey: ["knowledge-resolution-outcomes"],
    queryFn: async () => (await api.get<Option[]>("/resolution-outcomes")).data,
    enabled: section === "articles" && !portalUser,
  });
  const trainingMaterials = useQuery({
    queryKey: [
      "knowledge-training-materials",
      portalUser ? "portal" : "employee",
    ],
    queryFn: async () =>
      (await api.get<TrainingMaterial[]>(trainingMaterialsEndpoint(portalUser)))
        .data,
    enabled: section === "training" && canViewTraining,
  });
  const materialCategories = useQuery({
    queryKey: ["knowledge-training-categories"],
    queryFn: async () =>
      (await api.get<MaterialCategory[]>("/onboarding/material-categories"))
        .data,
    enabled: section === "training" && !portalUser,
  });
  const versions = useQuery({
    queryKey: ["knowledge-versions", historyArticle?.id],
    queryFn: async () =>
      (
        await api.get<ArticleVersion[]>(
          `/knowledge/articles/${historyArticle?.id}/versions`,
        )
      ).data,
    enabled: Boolean(historyArticle),
  });
  const resources = useQuery({
    queryKey: ["knowledge-resources", selected?.id],
    queryFn: async () =>
      (
        await api.get<Resource[]>(
          `/knowledge/articles/${selected?.id}/resources`,
        )
      ).data,
    enabled: Boolean(selected),
  });
  const addUrl = useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      api.post(`/knowledge/articles/${selected?.id}/resources/url`, data),
    onSuccess: async () => {
      setResourceOpen(null);
      await queryClient.invalidateQueries({
        queryKey: ["knowledge-resources", selected?.id],
      });
    },
    onError: () => setError(t("knowledge.errors.url")),
  });
  const addFile = useMutation({
    mutationFn: async (data: { name: string; description: string }) => {
      const body = new FormData();
      body.append("name", data.name);
      body.append("description", data.description);
      body.append("upload", resourceFile!);
      return api.post(
        `/knowledge/articles/${selected?.id}/resources/file`,
        body,
      );
    },
    onSuccess: async () => {
      setResourceOpen(null);
      setResourceFile(null);
      await queryClient.invalidateQueries({
        queryKey: ["knowledge-resources", selected?.id],
      });
    },
    onError: () => setError(t("knowledge.errors.upload")),
  });
  const removeResource = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/knowledge/articles/${selected?.id}/resources/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({
        queryKey: ["knowledge-resources", selected?.id],
      }),
  });
  const saveDownloadCategory = useMutation({
    mutationFn: async () =>
      categoryEditing
        ? api.patch(`/knowledge/download-categories/${categoryEditing.id}`, {
            name: categoryName,
            is_active: categoryEditing.is_active ?? true,
          })
        : api.post("/knowledge/download-categories", { name: categoryName }),
    onSuccess: async () => {
      setCategoryName("");
      setCategoryEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["knowledge-download-categories"] });
    },
  });
  const toggleDownloadCategory = useMutation({
    mutationFn: async (category: Option) =>
      api.patch(`/knowledge/download-categories/${category.id}`, {
        name: category.name,
        is_active: !(category.is_active ?? true),
      }),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["knowledge-download-categories"] }),
  });
  const removeDownloadCategory = useMutation({
    mutationFn: async (categoryId: number) =>
      api.delete(`/knowledge/download-categories/${categoryId}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["knowledge-download-categories"] }),
    onError: (requestError) =>
      setError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ?? t("knowledge.errors.categoryDelete"))
          : t("knowledge.errors.categoryDelete"),
      ),
  });
  async function downloadResource(resource: Resource) {
    if (resource.resource_type === "URL") {
      window.open(resource.external_url, "_blank", "noopener,noreferrer");
      return;
    }
    const response = await api.get(
      `/knowledge/articles/${resource.article_id}/resources/${resource.id}/download`,
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(response.data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = resource.original_filename ?? resource.name;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  const create = useMutation({
    mutationFn: async (data: Record<string, unknown>) =>
      api.post("/knowledge", data),
    onSuccess: async (response) => {
      setOpen(false);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["knowledge"] });
      setSelected(response.data as Article);
    },
    onError: (requestError) =>
      setError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ??
              t("knowledge.errors.create"))
          : t("knowledge.errors.create"),
      ),
  });
  const publish = useMutation({
    mutationFn: async (articleId: number) =>
      api.post(`/knowledge/articles/${articleId}/publish`),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: (requestError) =>
      setError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ??
              t("knowledge.errors.publish"))
          : t("knowledge.errors.publish"),
      ),
  });
  const unpublish = useMutation({
    mutationFn: async (articleId: number) =>
      api.post(`/knowledge/articles/${articleId}/unpublish`),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: (requestError) =>
      setError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ??
              t("knowledge.errors.unpublish"))
          : t("knowledge.errors.unpublish"),
      ),
  });
  const update = useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: Record<string, unknown>;
    }) => api.patch(`/knowledge/articles/${id}`, data),
    onSuccess: async () => {
      setEditing(null);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: (requestError) =>
      setError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ??
              t("knowledge.errors.update"))
          : t("knowledge.errors.update"),
      ),
  });
  const remove = useMutation({
    mutationFn: async ({
      articleId,
      unlinkTickets,
    }: {
      articleId: number;
      unlinkTickets: boolean;
    }) =>
      api.delete(`/knowledge/articles/${articleId}`, {
        params: { unlink_tickets: unlinkTickets },
      }),
    onSuccess: async () => {
      setDeleting(null);
      setUnlinkBeforeDelete(false);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: (requestError) => {
      if (
        axios.isAxiosError(requestError) &&
        requestError.response?.data?.error?.code === "ARTICLE_IN_USE"
      ) {
        setUnlinkBeforeDelete(true);
        return;
      }
      setDeleting(null);
      setUnlinkBeforeDelete(false);
      setError(
        axios.isAxiosError(requestError)
          ? (requestError.response?.data?.error?.message ??
              t("knowledge.errors.delete"))
          : t("knowledge.errors.delete"),
      );
    },
  });
  function articlePayload(form: HTMLFormElement) {
    const raw = Object.fromEntries(new FormData(form));
    const ids = (value: FormDataEntryValue | undefined) =>
      String(value ?? "")
        .split(",")
        .map(Number)
        .filter(Boolean);
    return {
      ...raw,
      category_id: raw.category_id ? Number(raw.category_id) : null,
      download_category_id: raw.download_category_id
        ? Number(raw.download_category_id)
        : null,
      product_ids: ids(raw.product_ids),
      client_ids: ids(raw.client_ids),
      product_module_ids: ids(raw.product_module_ids),
      service_ids: ids(raw.service_ids),
      root_cause_ids: ids(raw.root_cause_ids),
      resolution_service_ids: ids(raw.resolution_service_ids),
      resolution_outcome_id: raw.resolution_outcome_id
        ? Number(raw.resolution_outcome_id)
        : null,
      permanent_fix_summary_template:
        String(raw.permanent_fix_summary_template ?? "").trim() || null,
      permanent_fix_status: raw.permanent_fix_status || null,
    };
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate(articlePayload(event.currentTarget));
  }
  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    update.mutate({
      id: editing.id,
      data: articlePayload(event.currentTarget),
    });
  }
  const activeFilterCount = [
    categoryFilter,
    downloadCategoryFilter,
    productFilter,
    moduleFilter,
    clientFilter,
  ].filter(Boolean).length;
  const clearFilters = () => {
    setCategoryFilter("");
    setDownloadCategoryFilter("");
    setProductFilter("");
    setModuleFilter("");
    setClientFilter("");
  };
  return (
    <Paper
      elevation={0}
      sx={{
        p: { xs: 1, sm: 2 },
        width: "100%",
        minWidth: 0,
        overflow: "hidden",
        bgcolor: "transparent",
      }}
    >
      <Box
        sx={{
          p: { xs: 2, md: 3 },
          borderRadius: 3,
          color: "common.white",
          background: (theme) =>
            `linear-gradient(125deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 58%, ${theme.palette.info.main} 140%)`,
          boxShadow: (theme) => `0 14px 36px ${theme.palette.primary.main}2b`,
        }}
      >
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        alignItems={{ md: "center" }}
      >
        <div style={{ flex: 1 }}>
          <Stack direction="row" alignItems="center" spacing={1.25}>
            <MenuBook sx={{ fontSize: 34 }} />
            <Typography variant="h4" fontWeight={800}>{t("knowledge.title")}</Typography>
          </Stack>
          <Typography sx={{ mt: 0.5, color: "rgba(255,255,255,.78)" }}>
            {t(administer ? "knowledge.adminSubtitle" : "knowledge.subtitle")}
          </Typography>
        </div>
        {(section === "articles" || section === "downloads") && (
          <>
            <TextField
              size="small"
              label={t("knowledge.search")}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              slotProps={{
                input: {
                  startAdornment: (
                    <Search fontSize="small" sx={{ mr: 0.75, color: "text.secondary" }} />
                  ),
                },
              }}
              sx={{
                width: { xs: "100%", md: 390 },
                "& .MuiOutlinedInput-root": {
                  bgcolor: "background.paper",
                  borderRadius: 2.5,
                },
              }}
            />
            {hasPermission("knowledge.create") && (
              <Button
                variant="contained"
                startIcon={<Add />}
                sx={{
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                  bgcolor: "common.white",
                  color: "primary.dark",
                  fontWeight: 800,
                  "&:hover": { bgcolor: "grey.100" },
                }}
                onClick={() => {
                  setNewContentType(section === "downloads" ? "DOWNLOAD" : "ARTICLE");
                  setOpen(true);
                }}
              >
                {t(section === "downloads" ? "knowledge.newDownload" : "knowledge.newArticle")}
              </Button>
            )}
          </>
        )}
      </Stack>
      {(section === "articles" || section === "downloads") && query.data && (
        <Stack direction="row" spacing={1} mt={2} useFlexGap flexWrap="wrap">
          <Chip
            sx={{ bgcolor: "rgba(255,255,255,.16)", color: "common.white", fontWeight: 700 }}
            label={t("knowledge.resultsCount", { count: query.data.length })}
          />
          <Chip
            sx={{ bgcolor: "rgba(255,255,255,.16)", color: "common.white" }}
            label={`${t("knowledge.statuses.PUBLISHED", { defaultValue: "Published" })}: ${query.data.filter((item) => item.status === "PUBLISHED").length}`}
          />
          <Chip
            sx={{ bgcolor: "rgba(255,255,255,.16)", color: "common.white" }}
            label={`${t("knowledge.filters.category")}: ${new Set(query.data.map((item) => section === "downloads" ? item.download_category_id : item.category_id ?? item.category)).size}`}
          />
        </Stack>
      )}
      </Box>
      {(section === "articles" || section === "downloads") && !portalUser && (
        <Paper
          elevation={0}
          sx={{ mt: 2, p: 1.25, border: 1, borderColor: "divider", borderRadius: 2.5 }}
        >
          <Stack direction="row" alignItems="center" gap={1}>
            <Button
              startIcon={<FilterAlt />}
              endIcon={<ExpandMore sx={{ transform: filtersOpen ? "rotate(180deg)" : "none", transition: "transform .2s" }} />}
              onClick={() => setFiltersOpen((value) => !value)}
              aria-expanded={filtersOpen}
              sx={{ fontWeight: 750, textTransform: "none" }}
            >
              {t(
                filtersOpen
                  ? "knowledge.hideFilters"
                  : "knowledge.showFilters",
              )}
            </Button>
            {activeFilterCount > 0 && (
              <Chip
                size="small"
                color="primary"
                label={t("knowledge.activeFiltersCount", {
                  count: activeFilterCount,
                })}
              />
            )}
            <span style={{ flex: 1 }} />
            {activeFilterCount > 0 && (
              <Button size="small" startIcon={<Clear />} onClick={clearFilters}>
                {t("knowledge.clearFilters")}
              </Button>
            )}
          </Stack>
          <Collapse in={filtersOpen}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1}
              mt={1.5}
              useFlexGap
              flexWrap="wrap"
            >
          <TextField
            select
            size="small"
            label={t("knowledge.filters.category")}
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            SelectProps={{ native: true }}
            InputLabelProps={{ shrink: true }}
            sx={{ flex: "1 1 190px", minWidth: 180 }}
          >
            <option value="">{t("knowledge.filters.allCategories")}</option>
            {categories.data?.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </TextField>
          {section === "downloads" && (
            <TextField
              select
              size="small"
              label={t("knowledge.filters.downloadCategory")}
              value={downloadCategoryFilter}
              onChange={(event) => setDownloadCategoryFilter(event.target.value)}
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
              sx={{ flex: "1 1 210px", minWidth: 190 }}
            >
              <option value="">{t("knowledge.filters.allDownloadCategories")}</option>
              {downloadCategories.data?.filter((row) => row.is_active !== false).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </TextField>
          )}
          {section === "downloads" && hasPermission("knowledge.approve") && (
            <Button startIcon={<Settings />} onClick={() => setCategoryManagerOpen(true)}>
              {t("knowledge.manageDownloadCategories")}
            </Button>
          )}
          <TextField
            select
            size="small"
            label={t("knowledge.filters.product")}
            value={productFilter}
            onChange={(event) => {
              setProductFilter(event.target.value);
              setModuleFilter("");
            }}
            SelectProps={{ native: true }}
            InputLabelProps={{ shrink: true }}
            sx={{ flex: "1 1 190px", minWidth: 180 }}
          >
            <option value="">{t("knowledge.filters.allProducts")}</option>
            {products.data?.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label={t("knowledge.filters.module")}
            value={moduleFilter}
            onChange={(event) => setModuleFilter(event.target.value)}
            SelectProps={{ native: true }}
            InputLabelProps={{ shrink: true }}
            sx={{ flex: "1 1 190px", minWidth: 180 }}
          >
            <option value="">{t("knowledge.filters.allModules")}</option>
            {modules.data
              ?.filter(
                (row) =>
                  !productFilter || row.product_id === Number(productFilter),
              )
              .map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
          </TextField>
          <TextField
            select
            size="small"
            label={t("knowledge.filters.client")}
            value={clientFilter}
            onChange={(event) => setClientFilter(event.target.value)}
            SelectProps={{ native: true }}
            InputLabelProps={{ shrink: true }}
            sx={{ flex: "1 1 220px", minWidth: 200 }}
          >
            <option value="">{t("knowledge.filters.allClients")}</option>
            {clients.data?.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </TextField>
            </Stack>
          </Collapse>
        </Paper>
      )}
      <Tabs
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        value={section}
        onChange={(_, value: KnowledgeSection) => {
          setSection(value);
          const next = new URLSearchParams(searchParams);
          if (value !== "articles") next.set("section", value);
          else next.delete("section");
          setSearchParams(next, { replace: true });
        }}
        sx={{
          mt: 2,
          p: 0.5,
          minHeight: 48,
          bgcolor: "background.paper",
          border: 1,
          borderColor: "divider",
          borderRadius: 2.5,
          "& .MuiTabs-indicator": { display: "none" },
          "& .MuiTab-root": {
            minHeight: 38,
            borderRadius: 2,
            fontWeight: 750,
            textTransform: "none",
            "&.Mui-selected": {
              bgcolor: "primary.main",
              color: "primary.contrastText",
              WebkitTextFillColor: "currentColor",
              "& .MuiTab-iconWrapper": {
                color: "inherit",
              },
            },
          },
        }}
      >
        <Tab value="articles" label={t("knowledge.articlesTab")} />
        <Tab
          value="downloads"
          icon={<Download />}
          iconPosition="start"
          label={t("knowledge.downloadsTab")}
        />
        {canViewTraining && (
          <Tab
            value="training"
            icon={<MenuBook />}
            iconPosition="start"
            label={t("knowledge.trainingTab")}
          />
        )}
      </Tabs>
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
      {(section === "articles" || section === "downloads") && (
        <>
          {query.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {t(section === "downloads" ? "knowledge.downloadsLoadFailed" : "knowledge.articlesLoadFailed")}
            </Alert>
          )}
          {query.isLoading && (
            <Stack alignItems="center" py={6} gap={1.5}>
              <CircularProgress size={30} />
              <Typography color="text.secondary">
                {t("knowledge.loadingContent")}
              </Typography>
            </Stack>
          )}
          {query.data?.length === 0 && (
            <Alert severity="info" sx={{ mt: 3 }}>
              {t(section === "downloads" ? "knowledge.noDownloads" : "knowledge.noArticles")}
            </Alert>
          )}
          {query.data && (
            <Stack direction="row" justifyContent="space-between" alignItems="center" mt={2.5}>
              <Typography variant="subtitle2" color="text.secondary">
                {t("knowledge.resultsCount", { count: query.data.length })}
              </Typography>
              {(search || activeFilterCount > 0) && (
                <Button size="small" startIcon={<Clear />} onClick={() => { setSearch(""); clearFilters(); }}>
                  {t("knowledge.clearSearchFilters")}
                </Button>
              )}
            </Stack>
          )}
          <Stack spacing={1.25} mt={1.5}>
            {Object.entries(
              (query.data ?? []).reduce<Record<string, Article[]>>((groups, item) => {
                const key = section === "downloads"
                  ? `download:${item.download_category_id ?? "none"}`
                  : `article:${item.category_id ?? item.category ?? "none"}`;
                (groups[key] ??= []).push(item);
                return groups;
              }, {}),
            )
              .sort(([left], [right]) => left.localeCompare(right, locale))
              .map(([groupKey, items], groupIndex, groups) => {
                const first = items[0];
                const categoryName = section === "downloads"
                  ? downloadCategories.data?.find(
                      (row) => row.id === first.download_category_id,
                    )?.name ?? t("knowledge.uncategorized")
                  : first.category ?? t("knowledge.uncategorized");
                return (
                <Accordion
                  key={groupKey}
                  defaultExpanded={groups.length === 1 || Boolean(search)}
                  disableGutters
                  sx={{
                    border: 1,
                    borderColor: "divider",
                    borderRadius: "16px !important",
                    overflow: "hidden",
                    boxShadow: "0 5px 18px rgba(15, 45, 65, .06)",
                    "&:before": { display: "none" },
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMore />}
                    sx={{
                      minHeight: 62,
                      bgcolor: "action.hover",
                      borderBottom: 1,
                      borderColor: "divider",
                      "&.Mui-expanded": { minHeight: 62 },
                    }}
                  >
                    <Stack direction="row" alignItems="center" spacing={1} width="100%">
                      <Box
                        sx={{
                          width: 36,
                          height: 36,
                          display: "grid",
                          placeItems: "center",
                          borderRadius: 2,
                          bgcolor: "primary.main",
                          color: "primary.contrastText",
                        }}
                      >
                        {section === "downloads" ? <Download fontSize="small" /> : <MenuBook fontSize="small" />}
                      </Box>
                      <Typography variant="h6" fontWeight={800} flex={1}>{categoryName}</Typography>
                      <Chip
                        size="small"
                        label={t("knowledge.articleCount", { count: items.length })}
                      />
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails sx={{ p: { xs: 1, sm: 1.5 }, bgcolor: "background.default" }}>
                    <Grid container spacing={1.5}>
            {(
              section === "articles" && categoryName === "Tickets Knowledge Base"
                ? Object.entries(
                    items.reduce<Record<string, Article[]>>((productGroups, item) => {
                      const productKey = String(item.product_ids[0] ?? "none");
                      (productGroups[productKey] ??= []).push(item);
                      return productGroups;
                    }, {}),
                  )
                : [["all", items] as [string, Article[]]]
            ).map(([productKey, productItems]) => {
              const cards = productItems.map((item) => (
              <Grid key={item.id} size={{ xs: 12, xl: 6 }}>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  bgcolor: "background.paper",
                  borderRadius: 2.5,
                  transition: "transform .18s ease, box-shadow .18s ease, border-color .18s ease",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: "0 10px 24px rgba(15, 45, 65, .10)",
                    borderColor: "primary.light",
                  },
                }}
              >
                <Stack
                  spacing={1.25}
                  height="100%"
                >
                  <div style={{ flex: 1 }}>
                    <Typography variant="h6" fontWeight={800} lineHeight={1.3}>{item.title}</Typography>
                    <Typography
                      color="text.secondary"
                      sx={{ mt: 0.75, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}
                    >
                      {item.summary}
                    </Typography>
                    <Stack direction="row" spacing={0.75} mt={1.25} useFlexGap flexWrap="wrap">
                      <Chip
                        size="small"
                        label={t(`knowledge.statuses.${item.status}`, {
                          defaultValue: item.status,
                        })}
                        color={
                          item.status === "PUBLISHED" ? "success" : "default"
                        }
                      />
                      {item.content_type === "DOWNLOAD" && item.download_category_id && (
                        <Chip
                          size="small"
                          color="primary"
                          variant="outlined"
                          label={downloadCategories.data?.find((row) => row.id === item.download_category_id)?.name ?? t("knowledge.uncategorized")}
                        />
                      )}
                      <Chip
                        size="small"
                        label={item.category ?? t("knowledge.uncategorized")}
                      />
                    </Stack>
                  </div>
                  <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" pt={0.75} sx={{ borderTop: 1, borderColor: "divider" }}>
                  <Button size="small" variant="contained" onClick={() => setSelected(item)}>
                    {t(item.content_type === "DOWNLOAD" ? "knowledge.openDownload" : "knowledge.viewDetails")}
                  </Button>
                  <Button
                    size="small"
                    startIcon={<History />}
                    onClick={() => setHistoryArticle(item)}
                  >
                    {t("knowledge.history")}
                  </Button>
                  {hasPermission("knowledge.create") && (
                    <Button
                      size="small"
                      startIcon={<Edit />}
                      onClick={() => setEditing(item)}
                    >
                      {t("knowledge.edit")}
                    </Button>
                  )}
                  {hasPermission("knowledge.approve") &&
                    item.status !== "PUBLISHED" && (
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<Publish />}
                        disabled={publish.isPending}
                        onClick={() => publish.mutate(item.id)}
                      >
                        {t("knowledge.publish")}
                      </Button>
                    )}
                  {hasPermission("knowledge.approve") &&
                    item.status === "PUBLISHED" && (
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<Unpublished />}
                        disabled={unpublish.isPending}
                        onClick={() => unpublish.mutate(item.id)}
                      >
                        {t("knowledge.unpublish")}
                      </Button>
                    )}
                  {hasPermission("knowledge.approve") && (
                    <Button
                      size="small"
                      color="error"
                      startIcon={<Delete />}
                      onClick={() => setDeleting(item)}
                    >
                      {t("knowledge.delete")}
                    </Button>
                  )}
                  </Stack>
                </Stack>
              </Paper>
              </Grid>
              ));
              if (productKey === "all") return cards;
              const productName = productKey === "none"
                ? t("knowledge.noProductAssigned")
                : products.data?.find((product) => product.id === Number(productKey))?.name
                  ?? t("knowledge.productNumber", { id: productKey });
              return (
                <Accordion
                  key={productKey}
                  variant="outlined"
                  disableGutters
                  sx={{
                    borderRadius: "8px !important",
                    "&:before": { display: "none" },
                  }}
                >
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Stack direction="row" alignItems="center" spacing={1} width="100%">
                      <Typography fontWeight={700} flex={1}>{productName}</Typography>
                      <Chip
                        size="small"
                        variant="outlined"
                        label={t("knowledge.articleCount", { count: productItems.length })}
                      />
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails sx={{ pt: 0 }}>
                    <Grid container spacing={1.5}>{cards}</Grid>
                  </AccordionDetails>
                </Accordion>
              );
            })}
                    </Grid>
                  </AccordionDetails>
                </Accordion>
                );
              })}
          </Stack>
        </>
      )}
      {section === "training" && (
        <Stack spacing={1.5} mt={3}>
          {trainingMaterials.isLoading && <CircularProgress size={24} />}{" "}
          {trainingMaterials.isError && (
            <Alert severity="error">{t("knowledge.trainingLoadFailed")}</Alert>
          )}
          {trainingMaterials.data?.length === 0 && (
            <Alert severity="info">{t("knowledge.noTraining")}</Alert>
          )}
          {trainingMaterials.data?.map((material) => (
            <Paper key={material.id} variant="outlined" sx={{ p: 2 }}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                gap={1}
                alignItems={{ sm: "flex-start" }}
              >
                <Box flex={1}>
                  <Stack
                    direction="row"
                    gap={1}
                    alignItems="center"
                    flexWrap="wrap"
                  >
                    <Typography variant="h6">{material.title}</Typography>
                    {material.required && (
                      <Chip
                        size="small"
                        color="primary"
                        label={t("knowledge.required")}
                      />
                    )}
                    <Chip
                      size="small"
                      variant="outlined"
                      label={
                        materialCategories.data?.find(
                          (category) => category.id === material.category_id,
                        )?.name ?? t("knowledge.uncategorized")
                      }
                    />
                  </Stack>
                  {material.description && (
                    <Typography color="text.secondary" mt={0.5}>
                      {material.description}
                    </Typography>
                  )}
                </Box>
                <Chip
                  size="small"
                  label={t("knowledge.resourceCount", {
                    count: material.resources.length,
                  })}
                />
              </Stack>
              {material.resources.length === 0 ? (
                <Typography variant="body2" color="text.secondary" mt={1}>
                  {t("knowledge.noActiveResources")}
                </Typography>
              ) : (
                <Stack direction="row" gap={1} flexWrap="wrap" mt={1.5}>
                  {material.resources.map((resource) => (
                    <Button
                      key={resource.id}
                      component="a"
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      variant="outlined"
                      size="small"
                      startIcon={<OpenInNew />}
                    >
                      {resource.name} ·{" "}
                      {t(`knowledge.resourceTypes.${resource.type}`, {
                        defaultValue: resource.type.replaceAll("_", " "),
                      })}
                    </Button>
                  ))}
                </Stack>
              )}
            </Paper>
          ))}
        </Stack>
      )}
      <Dialog open={categoryManagerOpen} onClose={() => setCategoryManagerOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t("knowledge.manageDownloadCategories")}</DialogTitle>
        <DialogContent dividers>
          <Stack direction="row" spacing={1} mb={2}>
            <TextField
              size="small"
              fullWidth
              label={t("knowledge.fields.categoryName")}
              value={categoryName}
              onChange={(event) => setCategoryName(event.target.value)}
            />
            <Button
              variant="contained"
              disabled={categoryName.trim().length < 2 || saveDownloadCategory.isPending}
              onClick={() => saveDownloadCategory.mutate()}
            >
              {categoryEditing ? t("knowledge.saveChanges") : t("knowledge.addCategory")}
            </Button>
          </Stack>
          <Stack spacing={1}>
            {downloadCategories.data?.map((category) => (
              <Paper key={category.id} variant="outlined" sx={{ p: 1.5 }}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Typography flex={1}>{category.name}</Typography>
                  <Chip size="small" label={category.is_active === false ? t("knowledge.inactive") : t("knowledge.active")} />
                  <Button size="small" onClick={() => { setCategoryEditing(category); setCategoryName(category.name); }}>
                    {t("knowledge.edit")}
                  </Button>
                  <Button size="small" onClick={() => toggleDownloadCategory.mutate(category)}>
                    {category.is_active === false ? t("knowledge.activate") : t("knowledge.deactivate")}
                  </Button>
                  <Button size="small" color="error" onClick={() => removeDownloadCategory.mutate(category.id)}>
                    {t("knowledge.delete")}
                  </Button>
                </Stack>
              </Paper>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions><Button onClick={() => setCategoryManagerOpen(false)}>{t("knowledge.close")}</Button></DialogActions>
      </Dialog>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <form onSubmit={submit}>
          <DialogTitle>
            {t(newContentType === "DOWNLOAD" ? "knowledge.newDownloadTitle" : "knowledge.newTitle")}
          </DialogTitle>
          <DialogContent>
            <Typography color="text.secondary">
              {t("knowledge.draftNotice")}
            </Typography>
            <TextField
              select
              required
              name="content_type"
              label={t("knowledge.fields.contentType")}
              fullWidth
              margin="normal"
              value={newContentType}
              onChange={(event) =>
                setNewContentType(event.target.value as "ARTICLE" | "DOWNLOAD")
              }
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="ARTICLE">{t("knowledge.contentTypes.ARTICLE")}</option>
              <option value="DOWNLOAD">{t("knowledge.contentTypes.DOWNLOAD")}</option>
            </TextField>
            {newContentType === "DOWNLOAD" && (
              <TextField
                select
                required
                name="download_category_id"
                label={t("knowledge.fields.downloadCategory")}
                fullWidth
                margin="normal"
                defaultValue=""
                SelectProps={{ native: true }}
                InputLabelProps={{ shrink: true }}
              >
                <option value="">{t("knowledge.fields.selectDownloadCategory")}</option>
                {downloadCategories.data?.filter((row) => row.is_active !== false).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </TextField>
            )}
            <TextField
              required
              name="title"
              label={t("knowledge.fields.title")}
              fullWidth
              margin="normal"
            />
            <TextField
              required
              name="summary"
              label={t("knowledge.fields.summary")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <TextField
              required
              name="body"
              label={t("knowledge.fields.body")}
              fullWidth
              multiline
              rows={10}
              margin="normal"
            />
            <TextField
              select
              name="category_id"
              label={t("knowledge.fields.structuredCategory")}
              fullWidth
              margin="normal"
              defaultValue=""
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="">{t("knowledge.uncategorized")}</option>
              {categories.data?.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </TextField>
            <TextField
              select
              name="product_ids"
              label={t("knowledge.fields.applicableProducts")}
              fullWidth
              margin="normal"
              defaultValue={[]}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {products.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="client_ids"
              label={t("knowledge.fields.applicableClients")}
              fullWidth
              margin="normal"
              defaultValue={[]}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {clients.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="product_module_ids"
              label={t("knowledge.fields.applicableModules")}
              fullWidth
              margin="normal"
              defaultValue={[]}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {modules.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="tags"
              label={t("knowledge.fields.tagsComma")}
              fullWidth
              margin="normal"
            />
            <TextField
              select
              name="service_ids"
              label={t("knowledge.fields.applicableServices")}
              fullWidth
              margin="normal"
              defaultValue={[]}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {services.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="resolution_summary_template"
              label={t("knowledge.fields.resolutionTemplate")}
              helperText={t("knowledge.fields.resolutionTemplateHelp")}
              fullWidth
              multiline
              rows={4}
              margin="normal"
            />
            <TextField
              select
              name="root_cause_ids"
              label={t("knowledge.fields.rootCauses")}
              fullWidth
              margin="normal"
              defaultValue={[]}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {rootCauses.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="resolution_service_ids"
              label={t("knowledge.fields.resolutionServices")}
              fullWidth
              margin="normal"
              defaultValue={[]}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {services.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="resolution_outcome_id"
              label={t("knowledge.fields.resolutionOutcome")}
              fullWidth
              margin="normal"
              defaultValue=""
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="">
                {t("knowledge.fields.noResolutionOutcome")}
              </option>
              {resolutionOutcomes.data?.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </TextField>
            <TextField
              name="permanent_fix_summary_template"
              label={t("knowledge.fields.permanentFixTemplate")}
              fullWidth
              multiline
              rows={3}
              margin="normal"
            />
            <TextField
              select
              name="permanent_fix_status"
              label={t("knowledge.fields.permanentFixStatus")}
              fullWidth
              margin="normal"
              defaultValue=""
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="">
                {t("knowledge.fields.noPermanentFixStatus")}
              </option>
              <option value="PLANNED">
                {t("knowledge.permanentFixStatuses.PLANNED")}
              </option>
              <option value="IMPLEMENTED">
                {t("knowledge.permanentFixStatuses.IMPLEMENTED")}
              </option>
              <option value="NOT_REQUIRED">
                {t("knowledge.permanentFixStatuses.NOT_REQUIRED")}
              </option>
            </TextField>
            <TextField
              select
              name="visibility"
              label={t("knowledge.fields.visibility")}
              fullWidth
              margin="normal"
              defaultValue="INTERNAL"
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="INTERNAL">
                {t("knowledge.visibility.INTERNAL")}
              </option>
              <option value="CLIENT_PORTAL">
                {t("knowledge.visibility.CLIENT_PORTAL")}
              </option>
              <option value="BOTH">{t("knowledge.visibility.BOTH")}</option>
            </TextField>
            <Paper
              variant="outlined"
              sx={{ p: 2, mt: 2, bgcolor: "action.hover" }}
            >
              <Typography variant="subtitle1" fontWeight={700}>
                {t("knowledge.tools")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t("knowledge.toolsAfterSave")}
              </Typography>
            </Paper>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>
              {t("knowledge.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={create.isPending}
            >
              {create.isPending
                ? t("knowledge.saving")
                : t("knowledge.saveAddTools")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Dialog
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        fullWidth
        maxWidth="md"
      >
        <form key={editing?.id} onSubmit={submitEdit}>
          <DialogTitle>{t("knowledge.editTitle")}</DialogTitle>
          <DialogContent>
            <TextField
              select
              required
              name="content_type"
              label={t("knowledge.fields.contentType")}
              fullWidth
              margin="normal"
              defaultValue={editing?.content_type ?? "ARTICLE"}
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="ARTICLE">{t("knowledge.contentTypes.ARTICLE")}</option>
              <option value="DOWNLOAD">{t("knowledge.contentTypes.DOWNLOAD")}</option>
            </TextField>
            {editing?.content_type === "DOWNLOAD" && (
              <TextField
                select
                required
                name="download_category_id"
                label={t("knowledge.fields.downloadCategory")}
                fullWidth
                margin="normal"
                defaultValue={editing?.download_category_id ?? ""}
                SelectProps={{ native: true }}
                InputLabelProps={{ shrink: true }}
              >
                {downloadCategories.data?.filter((row) => row.is_active !== false || row.id === editing?.download_category_id).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </TextField>
            )}
            <TextField
              required
              name="title"
              label={t("knowledge.fields.title")}
              fullWidth
              margin="normal"
              defaultValue={editing?.title}
            />
            <TextField
              required
              name="summary"
              label={t("knowledge.fields.summary")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              defaultValue={editing?.summary}
            />
            <TextField
              required
              name="body"
              label={t("knowledge.fields.body")}
              fullWidth
              multiline
              rows={10}
              margin="normal"
              defaultValue={editing?.body}
            />
            <TextField
              select
              name="category_id"
              label={t("knowledge.fields.structuredCategory")}
              fullWidth
              margin="normal"
              defaultValue={editing?.category_id ?? ""}
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="">{t("knowledge.uncategorized")}</option>
              {categories.data?.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </TextField>
            <TextField
              select
              name="product_ids"
              label={t("knowledge.fields.applicableProducts")}
              fullWidth
              margin="normal"
              defaultValue={editing?.product_ids ?? []}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {products.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="client_ids"
              label={t("knowledge.fields.applicableClients")}
              fullWidth
              margin="normal"
              defaultValue={editing?.client_ids ?? []}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {clients.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="product_module_ids"
              label={t("knowledge.fields.applicableModules")}
              fullWidth
              margin="normal"
              defaultValue={editing?.product_module_ids ?? []}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {modules.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="tags"
              label={t("knowledge.fields.tags")}
              fullWidth
              margin="normal"
              defaultValue={editing?.tags ?? ""}
            />
            <TextField
              select
              name="service_ids"
              label={t("knowledge.fields.applicableServices")}
              fullWidth
              margin="normal"
              defaultValue={editing?.service_ids ?? []}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {services.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="resolution_summary_template"
              label={t("knowledge.fields.resolutionTemplate")}
              fullWidth
              multiline
              rows={4}
              margin="normal"
              defaultValue={editing?.resolution_summary_template ?? ""}
            />
            <TextField
              select
              name="root_cause_ids"
              label={t("knowledge.fields.rootCauses")}
              fullWidth
              margin="normal"
              defaultValue={editing?.root_cause_ids ?? []}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {rootCauses.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="resolution_service_ids"
              label={t("knowledge.fields.resolutionServices")}
              fullWidth
              margin="normal"
              defaultValue={editing?.resolution_service_ids ?? []}
              SelectProps={{ multiple: true }}
              InputLabelProps={{ shrink: true }}
            >
              {services.data?.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="resolution_outcome_id"
              label={t("knowledge.fields.resolutionOutcome")}
              fullWidth
              margin="normal"
              defaultValue={editing?.resolution_outcome_id ?? ""}
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="">
                {t("knowledge.fields.noResolutionOutcome")}
              </option>
              {resolutionOutcomes.data?.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </TextField>
            <TextField
              name="permanent_fix_summary_template"
              label={t("knowledge.fields.permanentFixTemplate")}
              fullWidth
              multiline
              rows={3}
              margin="normal"
              defaultValue={editing?.permanent_fix_summary_template ?? ""}
            />
            <TextField
              select
              name="permanent_fix_status"
              label={t("knowledge.fields.permanentFixStatus")}
              fullWidth
              margin="normal"
              defaultValue={editing?.permanent_fix_status ?? ""}
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="">
                {t("knowledge.fields.noPermanentFixStatus")}
              </option>
              <option value="PLANNED">
                {t("knowledge.permanentFixStatuses.PLANNED")}
              </option>
              <option value="IMPLEMENTED">
                {t("knowledge.permanentFixStatuses.IMPLEMENTED")}
              </option>
              <option value="NOT_REQUIRED">
                {t("knowledge.permanentFixStatuses.NOT_REQUIRED")}
              </option>
            </TextField>
            <TextField
              select
              name="visibility"
              label={t("knowledge.fields.visibility")}
              fullWidth
              margin="normal"
              defaultValue={editing?.visibility ?? "INTERNAL"}
              SelectProps={{ native: true }}
              InputLabelProps={{ shrink: true }}
            >
              <option value="INTERNAL">
                {t("knowledge.visibility.INTERNAL")}
              </option>
              <option value="CLIENT_PORTAL">
                {t("knowledge.visibility.CLIENT_PORTAL")}
              </option>
              <option value="BOTH">{t("knowledge.visibility.BOTH")}</option>
            </TextField>
            <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                gap={1}
                alignItems={{ sm: "center" }}
              >
                <Box flexGrow={1}>
                  <Typography variant="subtitle1" fontWeight={700}>
                    {t("knowledge.tools")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("knowledge.toolsAttach")}
                  </Typography>
                </Box>
                <Button
                  type="button"
                  variant="outlined"
                  startIcon={<Link />}
                  onClick={() => {
                    if (editing) setSelected(editing);
                    setEditing(null);
                    setResourceOpen("URL");
                  }}
                >
                  {t("knowledge.addUrl")}
                </Button>
                <Button
                  type="button"
                  variant="outlined"
                  startIcon={<UploadFile />}
                  onClick={() => {
                    if (editing) setSelected(editing);
                    setEditing(null);
                    setResourceOpen("FILE");
                  }}
                >
                  {t("knowledge.uploadFile")}
                </Button>
              </Stack>
            </Paper>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditing(null)}>
              {t("knowledge.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={update.isPending}
            >
              {t("knowledge.saveChanges")}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Drawer
        anchor="right"
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "100%", sm: "min(680px, 50vw)" },
              maxWidth: "100%",
              top: { xs: 48, sm: 52 },
              height: { xs: "calc(100% - 48px)", sm: "calc(100% - 52px)" },
              bgcolor: "background.default",
              overflow: "hidden",
            },
          },
        }}
      >
        <Box
          sx={{
            position: "sticky",
            top: 0,
            zIndex: 2,
            px: { xs: 2, sm: 3 },
            py: 2,
            bgcolor: "background.paper",
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <Stack direction="row" alignItems="flex-start" gap={1.5}>
            <Box flex={1} minWidth={0}>
              <Typography variant="overline" color="primary.main" fontWeight={800}>
                {selected?.category ?? t("knowledge.uncategorized")}
              </Typography>
              <Typography variant="h5" fontWeight={850} lineHeight={1.25}>
                {selected?.title}
              </Typography>
            </Box>
            <IconButton onClick={() => setSelected(null)} aria-label={t("knowledge.close")}>
              <Close />
            </IconButton>
          </Stack>
          <Stack direction="row" spacing={1} mt={1.5} useFlexGap flexWrap="wrap">
            <Chip
              size="small"
              label={t(`knowledge.statuses.${selected?.status}`, {
                defaultValue: selected?.status,
              })}
              color={selected?.status === "PUBLISHED" ? "success" : "default"}
            />
            <Chip
              size="small"
              label={selected?.category ?? t("knowledge.uncategorized")}
            />
            {selected?.content_type === "DOWNLOAD" && selected.download_category_id && (
              <Chip
                size="small"
                color="primary"
                label={downloadCategories.data?.find((row) => row.id === selected.download_category_id)?.name ?? t("knowledge.uncategorized")}
              />
            )}
            <Chip
              size="small"
              label={t(
                `knowledge.visibility.${selected?.visibility === "BOTH" ? "BOTH_SHORT" : (selected?.visibility ?? "INTERNAL")}`,
              )}
            />
          </Stack>
        </Box>
        <Box sx={{ px: { xs: 2, sm: 3 }, py: 3, flex: 1, overflowY: "auto" }}>
          <Stack spacing={3}>
            <Paper variant="outlined" sx={{ p: 2.25, borderRadius: 2.5 }}>
              <Typography variant="subtitle1" fontWeight={700}>
                {t("knowledge.fields.summary")}
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 0.75, lineHeight: 1.7 }}>
                {selected?.summary}
              </Typography>
            </Paper>
            <Box>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mt: 2 }}>
                {t("knowledge.procedure")}
              </Typography>
              <Typography sx={{ whiteSpace: "pre-wrap", lineHeight: 1.85, mt: 1, overflowWrap: "anywhere" }}>
                {selected?.body}
              </Typography>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mt: 2 }}>
                {t("knowledge.fields.tags")}
              </Typography>
              <Typography>{selected?.tags || t("knowledge.noTags")}</Typography>
            </Box>
              <Paper variant="outlined" sx={{ p: 2, borderRadius: 2.5 }}>
                <Stack direction="row" alignItems="center" mb={1}>
                  <Typography variant="h6" flexGrow={1}>
                    {t("knowledge.tools")}
                  </Typography>
                  {hasPermission("knowledge.create") && (
                    <>
                      <Button
                        size="small"
                        startIcon={<Link />}
                        onClick={() => setResourceOpen("URL")}
                      >
                        {t("knowledge.url")}
                      </Button>
                      <Button
                        size="small"
                        startIcon={<UploadFile />}
                        onClick={() => setResourceOpen("FILE")}
                      >
                        {t("knowledge.upload")}
                      </Button>
                    </>
                  )}
                </Stack>
                {resources.isLoading && <CircularProgress size={22} />}{" "}
                {!resources.isLoading && !resources.data?.length && (
                  <Typography color="text.secondary">
                    {t("knowledge.noResources")}
                  </Typography>
                )}
                {resources.data?.map((resource) => (
                  <Paper
                    key={resource.id}
                    variant="outlined"
                    sx={{ p: 1.25, my: 1 }}
                  >
                    <Typography fontWeight={700} sx={{ overflowWrap: "anywhere" }}>{resource.name}</Typography>
                    {resource.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ overflowWrap: "anywhere" }}>
                        {resource.description}
                      </Typography>
                    )}
                    <Typography variant="caption">
                      {resource.resource_type === "FILE" ? (
                        <>
                          <span dir="ltr">{resource.original_filename}</span> ·{" "}
                          {Intl.NumberFormat(locale).format(
                            Math.ceil((resource.size_bytes ?? 0) / 1024),
                          )}{" "}
                          KB
                        </>
                      ) : (
                        t("knowledge.externalLink")
                      )}
                    </Typography>
                    <Stack direction="row" mt={1}>
                      <Button
                        size="small"
                        startIcon={<Download />}
                        onClick={() => void downloadResource(resource)}
                      >
                        {t("knowledge.download")}
                      </Button>
                      {hasPermission("knowledge.create") && (
                        <Button
                          size="small"
                          color="error"
                          onClick={() => removeResource.mutate(resource.id)}
                        >
                          {t("knowledge.remove")}
                        </Button>
                      )}
                    </Stack>
                  </Paper>
                ))}
              </Paper>
          </Stack>
        </Box>
        <Stack
          direction="row"
          justifyContent="flex-end"
          gap={1}
          sx={{ position: "sticky", bottom: 0, p: 1.5, bgcolor: "background.paper", borderTop: 1, borderColor: "divider" }}
        >
          {selected && hasPermission("knowledge.create") && (
            <Button
              startIcon={<Edit />}
              onClick={() => {
                setEditing(selected);
                setSelected(null);
              }}
            >
              {t("knowledge.edit")}
            </Button>
          )}
          <Button onClick={() => setSelected(null)}>
            {t("knowledge.close")}
          </Button>
        </Stack>
      </Drawer>
      <Dialog
        open={resourceOpen === "URL"}
        onClose={() => setResourceOpen(null)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            addUrl.mutate(
              Object.fromEntries(new FormData(event.currentTarget)),
            );
          }}
        >
          <DialogTitle>{t("knowledge.urlDialog")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="name"
              label={t("knowledge.resourceName")}
              fullWidth
              margin="normal"
            />
            <TextField
              required
              name="external_url"
              type="url"
              label={t("knowledge.downloadUrl")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="description"
              label={t("knowledge.resourceDescription")}
              fullWidth
              multiline
              rows={3}
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setResourceOpen(null)}>
              {t("knowledge.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={addUrl.isPending}
            >
              {t("knowledge.addUrl")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={resourceOpen === "FILE"}
        onClose={() => setResourceOpen(null)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            addFile.mutate({
              name: String(values.name),
              description: String(values.description ?? ""),
            });
          }}
        >
          <DialogTitle>{t("knowledge.uploadDialog")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="name"
              label={t("knowledge.resourceName")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="description"
              label={t("knowledge.resourceDescription")}
              fullWidth
              multiline
              rows={3}
              margin="normal"
            />
            <Button
              component="label"
              variant="outlined"
              startIcon={<UploadFile />}
              sx={{ mt: 1 }}
            >
              {t("knowledge.selectFile")}
              <input
                hidden
                type="file"
                accept=".zip,.exe,.msi,.msix,.pdf,.txt,.docx,.xlsx"
                onChange={(event) =>
                  setResourceFile(event.target.files?.[0] ?? null)
                }
              />
            </Button>
            {resourceFile && (
              <Alert severity="info" sx={{ mt: 1 }}>
                <span dir="ltr">{resourceFile.name}</span> ·{" "}
                {Intl.NumberFormat(locale).format(
                  Math.ceil(resourceFile.size / 1024),
                )}{" "}
                KB
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setResourceOpen(null)}>
              {t("knowledge.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!resourceFile || addFile.isPending}
            >
              {t("knowledge.uploadTool")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(historyArticle)}
        onClose={() => setHistoryArticle(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {t("knowledge.revisionHistory", { title: historyArticle?.title })}
        </DialogTitle>
        <DialogContent>
          {versions.isLoading && <CircularProgress />}
          {versions.isError && (
            <Alert severity="error">{t("knowledge.historyLoadFailed")}</Alert>
          )}
          {versions.data?.map((item) => (
            <Accordion key={item.id}>
              <AccordionSummary>
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  width="100%"
                >
                  <Typography fontWeight={600}>
                    {t("knowledge.version", {
                      version: Intl.NumberFormat(locale).format(item.version),
                    })}
                  </Typography>
                  <Chip
                    size="small"
                    label={t(`knowledge.statuses.${item.status}`, {
                      defaultValue: item.status,
                    })}
                  />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ marginInlineStart: "auto" }}
                  >
                    {item.changed_by_name} ·{" "}
                    {new Date(item.created_at).toLocaleString(locale)}
                  </Typography>
                </Stack>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="h6">{item.title}</Typography>
                <Typography color="text.secondary" sx={{ mb: 2 }}>
                  {item.summary}
                </Typography>
                <Typography sx={{ whiteSpace: "pre-wrap" }}>
                  {item.body}
                </Typography>
              </AccordionDetails>
            </Accordion>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryArticle(null)}>
            {t("knowledge.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(deleting)}
        onClose={() => {
          setDeleting(null);
          setUnlinkBeforeDelete(false);
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {t(
            unlinkBeforeDelete
              ? "knowledge.linkedTitle"
              : "knowledge.deleteTitle",
          )}
        </DialogTitle>
        <DialogContent>
          {unlinkBeforeDelete ? (
            <>
              <Alert severity="warning" sx={{ mb: 2 }}>
                {t("knowledge.linkedWarning")}
              </Alert>
              <Typography>
                {t("knowledge.linkedMessage", { title: deleting?.title })}
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1 }}>
                {t("knowledge.unlinkExplanation")}
              </Typography>
            </>
          ) : (
            <>
              <Alert severity="warning" sx={{ mb: 2 }}>
                {t("knowledge.permanentWarning")}
              </Alert>
              <Typography>
                {t("knowledge.deleteQuestion", { title: deleting?.title })}
              </Typography>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setDeleting(null);
              setUnlinkBeforeDelete(false);
            }}
          >
            {t("knowledge.cancel")}
          </Button>
          <Button
            color="error"
            variant="contained"
            startIcon={<Delete />}
            disabled={remove.isPending}
            onClick={() =>
              deleting &&
              remove.mutate({
                articleId: deleting.id,
                unlinkTickets: unlinkBeforeDelete,
              })
            }
          >
            {t(
              unlinkBeforeDelete
                ? "knowledge.unlinkDelete"
                : "knowledge.deletePermanently",
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
