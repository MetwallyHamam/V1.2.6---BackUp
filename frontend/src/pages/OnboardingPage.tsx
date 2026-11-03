import { serverDateInput } from "../utils/serverTime";
import {
  AccountTree,
  Add,
  CheckCircle,
  Dashboard,
  Delete,
  MenuBook,
  Settings,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { OrganizationHierarchyViewer } from "../components/OrganizationHierarchyViewer";

type Item = {
  id: number;
  title: string;
  description?: string;
  status: string;
  required: boolean;
  available_date?: string;
  due_date?: string;
  material_id?: number;
  version: number;
  task_type_code?: string;
  completion_type_code?: string;
  requires_approval?: boolean;
  approval_status?: string;
  review_comment?: string;
  mentor_mode?: string;
  mentor_user_id?: number;
  mentor_name?: string;
};
type Plan = {
  id: number;
  template_name: string;
  start_date: string;
  status: string;
  completed: number;
  total: number;
  items: Item[];
  mentor_user_id?: number;
  mentor_name?: string;
};
type ProgressPlan = Plan & {
  user_name: string;
  department?: string;
  job_title?: string;
  manager_name?: string;
  overdue_count: number;
  pending_approval_count: number;
  expected_completion_date?: string;
};
type Resource = {
  id: number;
  name: string;
  type: string;
  url: string;
  display_order?: number;
  is_active?: boolean;
};
type ResourceDraft = {
  id?: number;
  name: string;
  type: string;
  url: string;
  display_order: number;
  is_active: boolean;
};
type Material = {
  id: number;
  title: string;
  description?: string;
  category_id?: number;
  required: boolean;
  display_order?: number;
  is_active?: boolean;
  show_in_client_portal: boolean;
  resources: Resource[];
};
type Person = {
  id: number;
  name: string;
  job_title?: string;
  department?: string;
  manager_id?: number;
  picture?: string;
};
type Category = {
  id: number;
  name: string;
  display_order: number;
  is_active: boolean;
};
type TemplateItem = {
  id?: number;
  title: string;
  description?: string;
  required: boolean;
  material_id?: number;
  start_after_days?: number;
  due_after_days?: number;
  task_type_code?: string;
  completion_type_code?: string;
  requires_approval?: boolean;
};
type Template = {
  id: number;
  code?: string;
  name: string;
  description?: string;
  category_id?: number;
  default_duration_days?: number;
  display_order?: number;
  version: number;
  is_active: boolean;
  items: TemplateItem[];
};
type Bundle = {
  id: number;
  code: string;
  name: string;
  description?: string;
  default_duration_days?: number;
  version: number;
  is_active: boolean;
  items: Array<{
    template_id: number;
    sequence_no: number;
    start_after_days: number;
    required: boolean;
  }>;
};
type Approval = {
  plan_id: number;
  item_id: number;
  employee_name: string;
  title: string;
  completion_type_code: string;
  submitted_at?: string;
  version: number;
};
type Catalogs = {
  task_types: Array<{ code: string; name: string }>;
  completion_types: Array<{ code: string; name: string }>;
};
type Employee = {
  id: number;
  name: string;
  department?: string;
  has_active_plan: boolean;
  active_plan_id?: number;
  active_plan_name?: string;
  active_plan_version?: number;
};
type AssignmentTask = {
  id: number;
  title: string;
  duration_days: number;
  mentor_mode: "INHERIT" | "SPECIFIC" | "NONE";
  mentor_user_id?: number;
};

export function OnboardingPage() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const { hasPermission } = useAuth(),
    [tab, setTab] = useState("checklist"),
    queryClient = useQueryClient();
  const [categoryOpen, setCategoryOpen] = useState(false),
    [materialOpen, setMaterialOpen] = useState(false),
    [templateOpen, setTemplateOpen] = useState(false),
    [bundleOpen, setBundleOpen] = useState(false),
    [assignOpen, setAssignOpen] = useState(false),
    [unassignOpen, setUnassignOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null),
    [editingMaterial, setEditingMaterial] = useState<Material | null>(null),
    [editingTemplate, setEditingTemplate] = useState<Template | null>(null),
    [editingBundle, setEditingBundle] = useState<Bundle | null>(null),
    [editingResource, setEditingResource] = useState<Resource | null>(null);
  const [templateItems, setTemplateItems] = useState<TemplateItem[]>([
      { title: "", description: "", required: true },
    ]),
    [selectedMaterialId, setSelectedMaterialId] = useState<number | null>(null);
  const [materialResources, setMaterialResources] = useState<ResourceDraft[]>([
    { name: "", type: "WEBSITE", url: "", display_order: 0, is_active: true },
  ]);
  useEffect(() => {
    if (!materialOpen) return;
    setMaterialResources(
      editingMaterial?.resources.length
        ? editingMaterial.resources.map((resource) => ({
            ...resource,
            display_order: resource.display_order ?? 0,
            is_active: resource.is_active ?? true,
          }))
        : [
            {
              name: "",
              type: "WEBSITE",
              url: "",
              display_order: 0,
              is_active: true,
            },
          ],
    );
  }, [materialOpen, editingMaterial]);
  const [bundleItems, setBundleItems] = useState<
    Array<{
      template_id: number | string;
      sequence_no: number;
      start_after_days: number;
      required: boolean;
    }>
  >([
    { template_id: "", sequence_no: 10, start_after_days: 0, required: true },
  ]);
  const [assignUserId, setAssignUserId] = useState(""),
    [assignSource, setAssignSource] = useState("");
  const [assignMentorId, setAssignMentorId] = useState("");
  const [assignmentTasks, setAssignmentTasks] = useState<AssignmentTask[]>([]);
  const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null),
    [dropLane, setDropLane] = useState<"TODO" | "WAITING" | "COMPLETED" | null>(
      null,
    );
  const plan = useQuery({
    queryKey: ["onboarding-me"],
    queryFn: async () => (await api.get<Plan | null>("/onboarding/me")).data,
  });
  const materials = useQuery({
    queryKey: ["onboarding-materials"],
    queryFn: async () =>
      (await api.get<Material[]>("/onboarding/materials")).data,
  });
  const hierarchy = useQuery({
    queryKey: ["onboarding-hierarchy"],
    queryFn: async () =>
      (await api.get<Person[]>("/onboarding/hierarchy")).data,
  });
  const categories = useQuery({
    queryKey: ["onboarding-categories"],
    queryFn: async () =>
      (await api.get<Category[]>("/onboarding/material-categories")).data,
  });
  const templates = useQuery({
    queryKey: ["onboarding-templates"],
    queryFn: async () =>
      (await api.get<Template[]>("/onboarding/templates")).data,
    enabled:
      hasPermission("onboarding.template.manage") ||
      hasPermission("onboarding.assign"),
  });
  const bundles = useQuery({
    queryKey: ["onboarding-bundles"],
    queryFn: async () => (await api.get<Bundle[]>("/onboarding/bundles")).data,
    enabled:
      hasPermission("onboarding.template.manage") ||
      hasPermission("onboarding.assign"),
  });
  const catalogs = useQuery({
    queryKey: ["onboarding-catalogs"],
    queryFn: async () => (await api.get<Catalogs>("/onboarding/catalogs")).data,
  });
  const approvals = useQuery({
    queryKey: ["onboarding-approvals"],
    queryFn: async () =>
      (await api.get<Approval[]>("/onboarding/approvals")).data,
  });
  const employees = useQuery({
    queryKey: ["onboarding-employees"],
    queryFn: async () =>
      (await api.get<Employee[]>("/onboarding/employees")).data,
    enabled: hasPermission("onboarding.assign"),
  });
  const canViewProgress = true;
  const progress = useQuery({
    queryKey: ["onboarding-progress"],
    queryFn: async () =>
      (await api.get<ProgressPlan[]>("/onboarding/progress")).data,
    enabled: canViewProgress,
  });
  const mentors = useQuery({
    queryKey: ["onboarding-mentor-candidates"],
    queryFn: async () =>
      (await api.get<Employee[]>("/onboarding/mentor-candidates")).data,
    enabled: hasPermission("onboarding.assign"),
  });
  const update = useMutation({
    mutationFn: async ({ item, status }: { item: Item; status: string }) =>
      api.patch(`/onboarding/${plan.data?.id}/items/${item.id}`, {
        status,
        version: item.version,
      }),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["onboarding-me"] }),
  });
  const createCategory = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/onboarding/material-categories", payload),
    onSuccess: async () => {
      setCategoryOpen(false);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-categories"],
      });
    },
  });
  const saveCategory = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch(
        `/onboarding/material-categories/${editingCategory?.id}`,
        payload,
      ),
    onSuccess: async () => {
      setCategoryOpen(false);
      setEditingCategory(null);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-categories"],
      });
    },
  });
  const removeCategory = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/onboarding/material-categories/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["onboarding-categories"] }),
  });
  const createMaterial = useMutation({
    mutationFn: async ({
      material,
      resources,
    }: {
      material: Record<string, unknown>;
      resources: ResourceDraft[];
    }) => {
      const response = await api.post("/onboarding/materials", material);
      await Promise.all(
        resources.map((resource) =>
          api.post(`/onboarding/materials/${response.data.id}/resources`, {
            name: resource.name,
            resource_type: resource.type,
            url: resource.url,
            display_order: resource.display_order,
            is_active: resource.is_active,
          }),
        ),
      );
      return response;
    },
    onSuccess: async (response) => {
      setMaterialOpen(false);
      setMaterialResources([
        {
          name: "",
          type: "WEBSITE",
          url: "",
          display_order: 0,
          is_active: true,
        },
      ]);
      setSelectedMaterialId(response.data.id);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-materials"],
      });
    },
  });
  const saveMaterial = useMutation({
    mutationFn: async ({
      material,
      resources,
    }: {
      material: Record<string, unknown>;
      resources: ResourceDraft[];
    }) => {
      await api.patch(`/onboarding/materials/${editingMaterial?.id}`, material);
      const retainedIds = new Set(
        resources.flatMap((resource) => (resource.id ? [resource.id] : [])),
      );
      await Promise.all(
        (editingMaterial?.resources ?? [])
          .filter((resource) => !retainedIds.has(resource.id))
          .map((resource) =>
            api.delete(`/onboarding/material-resources/${resource.id}`),
          ),
      );
      return Promise.all(
        resources.map((resource) =>
          resource.id
            ? api.patch(`/onboarding/material-resources/${resource.id}`, {
                name: resource.name,
                resource_type: resource.type,
                url: resource.url,
                display_order: resource.display_order,
                is_active: resource.is_active,
              })
            : api.post(
                `/onboarding/materials/${editingMaterial?.id}/resources`,
                {
                  name: resource.name,
                  resource_type: resource.type,
                  url: resource.url,
                  display_order: resource.display_order,
                  is_active: resource.is_active,
                },
              ),
        ),
      );
    },
    onSuccess: async () => {
      setMaterialOpen(false);
      setEditingMaterial(null);
      setMaterialResources([
        {
          name: "",
          type: "WEBSITE",
          url: "",
          display_order: 0,
          is_active: true,
        },
      ]);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-materials"],
      });
    },
  });
  const removeMaterial = useMutation({
    mutationFn: async (id: number) => api.delete(`/onboarding/materials/${id}`),
    onSuccess: async () => {
      setSelectedMaterialId(null);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-materials"],
      });
    },
  });
  const addResource = useMutation({
    mutationFn: async ({
      materialId,
      payload,
    }: {
      materialId: number;
      payload: Record<string, unknown>;
    }) => api.post(`/onboarding/materials/${materialId}/resources`, payload),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["onboarding-materials"] }),
  });
  const removeResource = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/onboarding/material-resources/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["onboarding-materials"] }),
  });
  const saveResource = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch(
        `/onboarding/material-resources/${editingResource?.id}`,
        payload,
      ),
    onSuccess: async () => {
      setEditingResource(null);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-materials"],
      });
    },
  });
  const createTemplate = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/onboarding/templates", payload),
    onSuccess: async () => {
      setTemplateOpen(false);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-templates"],
      });
    },
  });
  const saveTemplate = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch(`/onboarding/templates/${editingTemplate?.id}`, payload),
    onSuccess: async () => {
      setTemplateOpen(false);
      setEditingTemplate(null);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-templates"],
      });
    },
  });
  const removeTemplate = useMutation({
    mutationFn: async (id: number) => api.delete(`/onboarding/templates/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["onboarding-templates"] }),
  });
  const createBundle = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/onboarding/bundles", payload),
    onSuccess: async () => {
      setBundleOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["onboarding-bundles"] });
    },
  });
  const saveBundle = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch(`/onboarding/bundles/${editingBundle?.id}`, payload),
    onSuccess: async () => {
      setBundleOpen(false);
      setEditingBundle(null);
      await queryClient.invalidateQueries({ queryKey: ["onboarding-bundles"] });
    },
  });
  const removeBundle = useMutation({
    mutationFn: async (id: number) => api.delete(`/onboarding/bundles/${id}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["onboarding-bundles"] }),
  });
  const assign = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/onboarding/assign", payload),
    onSuccess: async () => {
      setAssignOpen(false);
      setAssignUserId("");
      setAssignSource("");
      setAssignMentorId("");
      setAssignmentTasks([]);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-employees"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-progress"],
      });
    },
  });
  const replaceAssignment = useMutation({
    mutationFn: async ({
      planId,
      payload,
    }: {
      planId: number;
      payload: Record<string, unknown>;
    }) => api.post(`/onboarding/${planId}/replace`, payload),
    onSuccess: async () => {
      setAssignOpen(false);
      setAssignUserId("");
      setAssignSource("");
      setAssignmentTasks([]);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-employees"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-progress"],
      });
    },
  });
  const unassign = useMutation({
    mutationFn: async (payload: {
      planId: number;
      version: number;
      reason: string;
    }) =>
      api.post(`/onboarding/${payload.planId}/unassign`, {
        version: payload.version,
        reason: payload.reason,
      }),
    onSuccess: async () => {
      setUnassignOpen(false);
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-employees"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["onboarding-progress"],
      });
    },
  });
  const review = useMutation({
    mutationFn: async ({
      row,
      decision,
    }: {
      row: Approval;
      decision: string;
    }) =>
      api.post(`/onboarding/${row.plan_id}/items/${row.item_id}/review`, {
        decision,
        comment:
          decision === "APPROVED" ? "Approved" : "Returned for correction",
      }),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["onboarding-approvals"] }),
  });
  const canAdmin =
    hasPermission("onboarding.template.manage") ||
    hasPermission("onboarding.material.manage") ||
    hasPermission("onboarding.assign");
  function submitCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget),
      payload = {
        name: data.get("name"),
        display_order: Number(data.get("display_order") || 0),
        is_active: data.get("is_active") === "on",
      };
    if (editingCategory) saveCategory.mutate(payload);
    else createCategory.mutate(payload);
  }
  function submitMaterial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget),
      material = {
        title: data.get("title"),
        description: data.get("description") || null,
        category_id: data.get("category_id")
          ? Number(data.get("category_id"))
          : null,
        is_required: data.get("is_required") === "on",
        display_order: Number(data.get("display_order") || 0),
        is_active: data.get("is_active") === "on",
        show_in_client_portal: data.get("show_in_client_portal") === "on",
      },
      resources = materialResources.map((resource, index) => ({
        ...resource,
        name: resource.name.trim() || String(data.get("title")).trim(),
        display_order: index,
      }));
    if (editingMaterial) saveMaterial.mutate({ material, resources });
    else createMaterial.mutate({ material, resources });
  }
  function submitResource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedMaterialId) return;
    const data = new FormData(event.currentTarget);
    addResource.mutate({
      materialId: selectedMaterialId,
      payload: {
        name: data.get("name"),
        resource_type: data.get("resource_type"),
        url: data.get("url"),
        display_order: Number(data.get("display_order") || 0),
        is_active: true,
      },
    });
    event.currentTarget.reset();
  }
  function submitTemplate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget),
      payload = {
        code: data.get("code") || null,
        name: data.get("name"),
        description: data.get("description") || null,
        category_id: data.get("category_id")
          ? Number(data.get("category_id"))
          : null,
        default_duration_days: data.get("default_duration_days")
          ? Number(data.get("default_duration_days"))
          : null,
        display_order: Number(data.get("display_order") || 0),
        items: templateItems.map((item, index) => ({
          ...item,
          display_order: index,
          is_active: true,
        })),
      };
    if (editingTemplate) saveTemplate.mutate(payload);
    else createTemplate.mutate(payload);
  }
  function selectAssignmentSource(source: string) {
    setAssignSource(source);
    const selectedTemplates = source.startsWith("template:")
      ? templates.data?.filter((row) => row.id === Number(source.slice(9)))
      : templates.data?.filter((row) =>
          bundles.data
            ?.find((bundle) => bundle.id === Number(source.slice(7)))
            ?.items.some((item) => item.template_id === row.id),
        );
    setAssignmentTasks(
      (selectedTemplates ?? []).flatMap((template) =>
        template.items
          .filter((item) => item.id)
          .map((item) => ({
            id: item.id!,
            title: item.title,
            duration_days: Math.max(
              1,
              item.due_after_days !== undefined
                ? item.due_after_days - (item.start_after_days ?? 0)
                : (template.default_duration_days ?? 1),
            ),
            mentor_mode: "INHERIT" as const,
          })),
      ),
    );
  }
  function submitAssign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget),
      source = String(data.get("source")),
      employee = employees.data?.find(
        (row) => row.id === Number(data.get("user_id")),
      ),
      payload = {
        user_id: Number(data.get("user_id")),
        template_id: source.startsWith("template:")
          ? Number(source.slice(9))
          : null,
        bundle_id: source.startsWith("bundle:")
          ? Number(source.slice(7))
          : null,
        start_date: data.get("start_date"),
        mentor_user_id: assignMentorId ? Number(assignMentorId) : null,
        task_durations: assignmentTasks.map((task) => ({
          template_item_id: task.id,
          duration_days: task.duration_days,
          mentor_mode: task.mentor_mode,
          mentor_user_id:
            task.mentor_mode === "SPECIFIC" ? task.mentor_user_id : null,
        })),
      };
    if (employee?.active_plan_id && employee.active_plan_version)
      replaceAssignment.mutate({
        planId: employee.active_plan_id,
        payload: {
          ...payload,
          version: employee.active_plan_version,
          reason: data.get("reason"),
        },
      });
    else assign.mutate(payload);
  }
  function submitBundle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget),
      payload = {
        code: data.get("code"),
        name: data.get("name"),
        description: data.get("description") || null,
        default_duration_days: data.get("default_duration_days")
          ? Number(data.get("default_duration_days"))
          : null,
        items: bundleItems
          .filter((item) => item.template_id)
          .map((item) => ({ ...item, template_id: Number(item.template_id) })),
      };
    if (editingBundle) saveBundle.mutate(payload);
    else createBundle.mutate(payload);
  }
  function taskLane(item: Item) {
    return item.status === "COMPLETED" || item.status === "SKIPPED"
      ? "COMPLETED"
      : item.approval_status === "PENDING"
        ? "WAITING"
        : "TODO";
  }
  function dropTask(lane: "TODO" | "WAITING" | "COMPLETED") {
    const item = plan.data?.items.find((row) => row.id === draggedTaskId);
    setDraggedTaskId(null);
    setDropLane(null);
    if (!item || taskLane(item) === lane) return;
    const locked = Boolean(
      item.available_date && new Date(item.available_date) > new Date(),
    );
    const needsReview =
      item.requires_approval ||
      item.completion_type_code?.includes("APPROVAL") ||
      item.completion_type_code === "MENTOR_CONFIRMATION";
    if (locked || (lane === "WAITING" && !needsReview)) return;
    if (lane === "TODO") update.mutate({ item, status: "PENDING" });
    else update.mutate({ item, status: "COMPLETED" });
  }
  const hierarchyNodes = (hierarchy.data ?? []).map((person) => ({
    id: person.id,
    parent_id: person.manager_id ?? null,
    name: person.name,
    node_type: "TEAM_MEMBER",
    title: person.job_title || t("onboarding.employee"),
    image_url: person.picture,
    notes: person.department || t("onboarding.noDepartment"),
    is_active: true,
  }));
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" fontWeight={900}>
          {t("onboarding.title")}
        </Typography>
        <Typography color="text.secondary">
          {t("onboarding.subtitle")}
        </Typography>
        <Tabs
          value={tab}
          onChange={(_, value) => setTab(value)}
          variant="scrollable"
        >
          <Tab
            value="checklist"
            icon={<CheckCircle />}
            iconPosition="start"
            label={t("onboarding.tabs.checklist")}
          />
          {canViewProgress && (
            <Tab
              value="dashboard"
              icon={<Dashboard />}
              iconPosition="start"
              label="Progress dashboard"
            />
          )}
          <Tab
            value="materials"
            icon={<MenuBook />}
            iconPosition="start"
            label={t("onboarding.tabs.materials")}
          />
          <Tab
            value="hierarchy"
            icon={<AccountTree />}
            iconPosition="start"
            label={t("onboarding.tabs.hierarchy")}
          />
          {canAdmin && (
            <Tab
              value="administration"
              icon={<Settings />}
              iconPosition="start"
              label={t("onboarding.tabs.administration")}
            />
          )}
        </Tabs>
      </Paper>
      {tab === "dashboard" && canViewProgress && (
        <Stack spacing={2}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(3,1fr)" },
              gap: 2,
            }}
          >
            <Paper sx={{ p: 2 }}>
              <Typography color="text.secondary">Active programs</Typography>
              <Typography variant="h4" fontWeight={900}>
                {progress.data?.filter((row) => row.status === "IN_PROGRESS")
                  .length ?? 0}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2 }}>
              <Typography color="text.secondary">Average progress</Typography>
              <Typography variant="h4" fontWeight={900}>
                {Math.round(
                  (progress.data ?? []).reduce(
                    (sum, row) =>
                      sum + (row.total ? (row.completed / row.total) * 100 : 0),
                    0,
                  ) / Math.max(progress.data?.length ?? 0, 1),
                )}
                %
              </Typography>
            </Paper>
            <Paper sx={{ p: 2 }}>
              <Typography color="text.secondary">Overdue tasks</Typography>
              <Typography variant="h4" fontWeight={900} color="error.main">
                {(progress.data ?? []).reduce(
                  (sum, row) => sum + row.overdue_count,
                  0,
                )}
              </Typography>
            </Paper>
          </Box>
          {Boolean(approvals.data?.length) && (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" fontWeight={900}>
                Tasks waiting for your review
              </Typography>
              {approvals.data?.map((row) => (
                <Stack
                  key={row.item_id}
                  direction={{ xs: "column", sm: "row" }}
                  gap={1}
                  alignItems={{ sm: "center" }}
                  py={1}
                >
                  <Box flex={1}>
                    <Typography fontWeight={800}>
                      {row.employee_name} · {row.title}
                    </Typography>
                  </Box>
                  <Button
                    color="error"
                    onClick={() => review.mutate({ row, decision: "REJECTED" })}
                  >
                    Return
                  </Button>
                  <Button
                    color="success"
                    variant="contained"
                    onClick={() => review.mutate({ row, decision: "APPROVED" })}
                  >
                    Approve
                  </Button>
                </Stack>
              ))}
            </Paper>
          )}
          {progress.data?.map((row) => (
            <Paper key={row.id} variant="outlined" sx={{ p: 2 }}>
              <Stack
                direction={{ xs: "column", md: "row" }}
                gap={2}
                alignItems={{ md: "center" }}
              >
                <Box flex={1}>
                  <Typography variant="h6" fontWeight={900}>
                    {row.user_name}
                  </Typography>
                  <Typography color="text.secondary">
                    {row.job_title || "Employee"} ·{" "}
                    {row.department || "No department"} · {row.template_name}
                  </Typography>
                  <Typography variant="body2">
                    Manager: {row.manager_name || "—"} · Mentor:{" "}
                    {row.mentor_name || "—"} · Expected:{" "}
                    {row.expected_completion_date
                      ? new Date(
                          row.expected_completion_date,
                        ).toLocaleDateString(locale)
                      : "—"}
                  </Typography>
                </Box>
                <Box sx={{ minWidth: 220 }}>
                  <Typography fontWeight={800}>
                    {row.total
                      ? Math.round((row.completed / row.total) * 100)
                      : 0}
                    % complete
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={row.total ? (row.completed / row.total) * 100 : 0}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>
                <Stack direction="row" gap={1}>
                  <Chip
                    color={row.overdue_count ? "error" : "default"}
                    label={`${row.overdue_count} overdue`}
                  />
                  <Chip
                    color={row.pending_approval_count ? "warning" : "default"}
                    label={`${row.pending_approval_count} waiting`}
                  />
                </Stack>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}
      {tab === "checklist" && (
        <Stack spacing={1.5}>
          {!plan.data && (
            <Alert severity="info">{t("onboarding.noPlan")}</Alert>
          )}
          {plan.data && (
            <>
              <Paper sx={{ p: 2 }}>
                <Stack direction="row" justifyContent="space-between">
                  <Box>
                    <Typography variant="h5" fontWeight={900}>
                      {plan.data.template_name}
                    </Typography>
                    <Typography color="text.secondary">
                      {t("onboarding.started", {
                        date: new Date(plan.data.start_date).toLocaleDateString(
                          locale,
                        ),
                      })}
                    </Typography>
                    {plan.data.mentor_name && (
                      <Typography variant="body2">
                        Program mentor: {plan.data.mentor_name}
                      </Typography>
                    )}
                  </Box>
                  <Chip
                    color="primary"
                    label={t("onboarding.progress", {
                      completed: Intl.NumberFormat(locale).format(
                        plan.data.completed,
                      ),
                      total: Intl.NumberFormat(locale).format(plan.data.total),
                    })}
                  />
                </Stack>
                <LinearProgress
                  variant="determinate"
                  value={
                    plan.data.total
                      ? (plan.data.completed / plan.data.total) * 100
                      : 0
                  }
                  sx={{ mt: 2, height: 10, borderRadius: 5 }}
                />
              </Paper>
              {plan.data.items.some(
                (item) =>
                  item.status !== "COMPLETED" && item.status !== "SKIPPED",
              ) && (
                <Alert severity="success">
                  <strong>Next task:</strong>{" "}
                  {
                    plan.data.items.find(
                      (item) =>
                        item.status !== "COMPLETED" &&
                        item.status !== "SKIPPED",
                    )?.title
                  }
                </Alert>
              )}
              <Typography variant="body2" color="text.secondary">
                Drag a task card between lanes to update it. Tasks requiring
                approval remain in Waiting approval until a manager or mentor
                reviews them.
              </Typography>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    lg: "repeat(3, minmax(0, 1fr))",
                  },
                  gap: 2,
                  alignItems: "start",
                }}
              >
                {(["TODO", "WAITING", "COMPLETED"] as const).map((group) => {
                  const rows = plan.data!.items.filter(
                    (item) => taskLane(item) === group,
                  );
                  return (
                    <Paper
                      key={group}
                      variant="outlined"
                      onDragOver={(event) => {
                        event.preventDefault();
                        event.dataTransfer.dropEffect = "move";
                        setDropLane(group);
                      }}
                      onDragLeave={(event) => {
                        if (
                          !event.currentTarget.contains(
                            event.relatedTarget as Node | null,
                          )
                        )
                          setDropLane(null);
                      }}
                      onDrop={(event) => {
                        event.preventDefault();
                        dropTask(group);
                      }}
                      sx={{
                        p: 1.5,
                        minHeight: 280,
                        bgcolor:
                          dropLane === group
                            ? "action.selected"
                            : "action.hover",
                        borderTop: 4,
                        borderTopColor:
                          group === "COMPLETED"
                            ? "success.main"
                            : group === "WAITING"
                              ? "warning.main"
                              : "primary.main",
                        outline: dropLane === group ? "2px dashed" : "none",
                        outlineColor: "primary.main",
                        outlineOffset: -5,
                        borderRadius: 3,
                      }}
                    >
                      <Typography variant="h6" fontWeight={900}>
                        {group === "TODO"
                          ? "To do"
                          : group === "WAITING"
                            ? "Waiting approval"
                            : "Completed"}{" "}
                        <Chip size="small" label={rows.length} />
                      </Typography>
                      {rows.map((item) => {
                        const locked = Boolean(
                          item.available_date &&
                          new Date(item.available_date) > new Date(),
                        );
                        return (
                          <Paper
                            key={item.id}
                            variant="outlined"
                            draggable={!locked && !update.isPending}
                            onDragStart={(event) => {
                              event.dataTransfer.effectAllowed = "move";
                              event.dataTransfer.setData(
                                "text/onboarding-task",
                                String(item.id),
                              );
                              setDraggedTaskId(item.id);
                            }}
                            onDragEnd={() => {
                              setDraggedTaskId(null);
                              setDropLane(null);
                            }}
                            sx={{
                              p: 2,
                              mb: 1,
                              opacity:
                                draggedTaskId === item.id
                                  ? 0.5
                                  : locked
                                    ? 0.65
                                    : 1,
                              cursor: locked ? "not-allowed" : "grab",
                              bgcolor: "background.paper",
                              boxShadow: 1,
                              transition:
                                "transform .15s ease, box-shadow .15s ease",
                              "&:hover": locked
                                ? undefined
                                : {
                                    transform: "translateY(-2px)",
                                    boxShadow: 4,
                                  },
                              "&:active": {
                                cursor: locked ? "not-allowed" : "grabbing",
                              },
                            }}
                          >
                            <Stack
                              direction={{ xs: "column", sm: "row" }}
                              gap={1}
                              alignItems={{ sm: "center" }}
                            >
                              <Box flex={1}>
                                <Typography fontWeight={800}>
                                  {item.title}{" "}
                                  {item.required && (
                                    <Chip
                                      size="small"
                                      label={t("onboarding.required")}
                                    />
                                  )}
                                </Typography>
                                <Typography color="text.secondary">
                                  {item.description}
                                </Typography>
                                {item.mentor_name && (
                                  <Chip
                                    size="small"
                                    variant="outlined"
                                    label={`Mentor: ${item.mentor_name}`}
                                    sx={{ mt: 0.5 }}
                                  />
                                )}
                                {item.due_date && (
                                  <Typography variant="caption" display="block">
                                    {t("onboarding.due", {
                                      date: new Date(
                                        item.due_date,
                                      ).toLocaleDateString(locale),
                                    })}
                                  </Typography>
                                )}
                                {item.approval_status && (
                                  <Alert
                                    severity={
                                      item.approval_status === "REJECTED"
                                        ? "error"
                                        : "info"
                                    }
                                    sx={{ mt: 1 }}
                                  >
                                    {t("onboarding.review", {
                                      status: t(
                                        `onboarding.statuses.${item.approval_status}`,
                                        { defaultValue: item.approval_status },
                                      ),
                                    })}{" "}
                                    {item.review_comment &&
                                      `— ${item.review_comment}`}
                                  </Alert>
                                )}
                              </Box>
                              <Chip
                                label={t(`onboarding.statuses.${item.status}`, {
                                  defaultValue: item.status,
                                })}
                              />
                              {item.status !== "COMPLETED" &&
                                item.approval_status !== "PENDING" && (
                                  <Button
                                    variant="contained"
                                    disabled={update.isPending || locked}
                                    onClick={() =>
                                      update.mutate({
                                        item,
                                        status: "COMPLETED",
                                      })
                                    }
                                  >
                                    {t(
                                      item.requires_approval ||
                                        item.completion_type_code?.includes(
                                          "APPROVAL",
                                        ) ||
                                        item.completion_type_code ===
                                          "MENTOR_CONFIRMATION"
                                        ? "onboarding.submitApproval"
                                        : "onboarding.markComplete",
                                    )}
                                  </Button>
                                )}
                            </Stack>
                          </Paper>
                        );
                      })}
                    </Paper>
                  );
                })}
              </Box>
            </>
          )}
        </Stack>
      )}
      {tab === "materials" && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2,1fr)" },
            gap: 2,
          }}
        >
          {materials.data?.map((material) => (
            <Paper key={material.id} variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" fontWeight={900}>
                {material.title}
              </Typography>
              <Typography color="text.secondary">
                {material.description}
              </Typography>
              <Stack direction="row" gap={1} mt={2} flexWrap="wrap">
                {material.resources.map((resource) => (
                  <Button
                    key={resource.id}
                    component="a"
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="outlined"
                  >
                    {resource.name}
                  </Button>
                ))}
              </Stack>
            </Paper>
          ))}
        </Box>
      )}
      {tab === "hierarchy" && (
        <Paper sx={{ p: 2 }}>
          <OrganizationHierarchyViewer
            nodes={hierarchyNodes}
            loading={hierarchy.isLoading}
            emptyText={t("onboarding.hierarchyNotice")}
            notice={<Alert severity="info">{t("onboarding.hierarchyNotice")}</Alert>}
          />
        </Paper>
      )}
      {tab === "administration" && canAdmin && (
        <Stack spacing={2}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h5" fontWeight={900}>
              {t("onboarding.adminTitle")}
            </Typography>
            <Typography color="text.secondary">
              {t("onboarding.adminSubtitle")}
            </Typography>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              mt={2}
              flexWrap="wrap"
            >
              {hasPermission("onboarding.category.manage") && (
                <Button
                  startIcon={<Add />}
                  variant="outlined"
                  onClick={() => setCategoryOpen(true)}
                >
                  {t("onboarding.category")}
                </Button>
              )}
              {hasPermission("onboarding.material.manage") && (
                <Button
                  startIcon={<Add />}
                  variant="outlined"
                  onClick={() => setMaterialOpen(true)}
                >
                  {t("onboarding.trainingMaterial")}
                </Button>
              )}
              {hasPermission("onboarding.template.manage") && (
                <Button
                  startIcon={<Add />}
                  variant="outlined"
                  onClick={() => {
                    setTemplateItems([
                      { title: "", description: "", required: true },
                    ]);
                    setTemplateOpen(true);
                  }}
                >
                  {t("onboarding.checklistTemplate")}
                </Button>
              )}
              {hasPermission("onboarding.template.manage") && (
                <Button
                  startIcon={<Add />}
                  variant="outlined"
                  onClick={() => {
                    setBundleItems([
                      {
                        template_id: "",
                        sequence_no: 10,
                        start_after_days: 0,
                        required: true,
                      },
                    ]);
                    setBundleOpen(true);
                  }}
                >
                  {t("onboarding.roleProgram")}
                </Button>
              )}
              {hasPermission("onboarding.assign") && (
                <Button
                  startIcon={<CheckCircle />}
                  variant="contained"
                  onClick={() => setAssignOpen(true)}
                >
                  {t("onboarding.assignOnboarding")}
                </Button>
              )}
              {hasPermission("onboarding.assign") && (
                <Button
                  color="error"
                  variant="outlined"
                  onClick={() => setUnassignOpen(true)}
                  disabled={
                    !employees.data?.some(
                      (employee) => employee.has_active_plan,
                    )
                  }
                >
                  {t("onboarding.unassignUser")}
                </Button>
              )}
            </Stack>
          </Paper>
          <Stack direction={{ xs: "column", lg: "row" }} gap={2}>
            <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
              <Typography variant="h6" fontWeight={900}>
                {t("onboarding.materialCategories")}
              </Typography>
              {categories.data?.map((row) => (
                <Stack
                  key={row.id}
                  direction="row"
                  alignItems="center"
                  py={0.5}
                >
                  <Box flex={1}>
                    {row.name}{" "}
                    <Chip
                      size="small"
                      label={t(
                        row.is_active
                          ? "onboarding.active"
                          : "onboarding.inactive",
                      )}
                    />
                  </Box>
                  {hasPermission("onboarding.category.manage") && (
                    <>
                      <Button
                        size="small"
                        onClick={() => {
                          setEditingCategory(row);
                          setCategoryOpen(true);
                        }}
                      >
                        {t("onboarding.edit")}
                      </Button>
                      {row.is_active && (
                        <Button
                          size="small"
                          color="error"
                          onClick={() => removeCategory.mutate(row.id)}
                        >
                          {t("onboarding.delete")}
                        </Button>
                      )}
                    </>
                  )}
                </Stack>
              ))}
            </Paper>
            <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
              <Typography variant="h6" fontWeight={900}>
                {t("onboarding.trainingMaterials")}
              </Typography>
              {materials.data?.map((row) => (
                <Stack key={row.id} direction="row" alignItems="center">
                  <Button
                    fullWidth
                    sx={{ justifyContent: "flex-start" }}
                    variant={
                      selectedMaterialId === row.id ? "contained" : "text"
                    }
                    onClick={() => setSelectedMaterialId(row.id)}
                  >
                    {row.title} ·{" "}
                    {t("onboarding.resources", { count: row.resources.length })}{" "}
                    {row.show_in_client_portal && (
                      <Chip
                        size="small"
                        color="success"
                        label={t("onboarding.portalVisible")}
                        sx={{ marginInlineStart: 1 }}
                      />
                    )}
                  </Button>
                  {hasPermission("onboarding.material.manage") && (
                    <>
                      <Button
                        size="small"
                        onClick={() => {
                          setEditingMaterial(row);
                          setMaterialOpen(true);
                        }}
                      >
                        {t("onboarding.edit")}
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => removeMaterial.mutate(row.id)}
                      >
                        {t("onboarding.delete")}
                      </Button>
                    </>
                  )}
                </Stack>
              ))}
            </Paper>
            <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
              <Typography variant="h6" fontWeight={900}>
                {t("onboarding.checklistTemplates")}
              </Typography>
              {templates.data?.map((row) => (
                <Stack
                  key={row.id}
                  direction="row"
                  alignItems="center"
                  py={0.5}
                >
                  <Box flex={1}>
                    {row.name}{" "}
                    <Chip
                      size="small"
                      label={t("onboarding.items", { count: row.items.length })}
                    />
                  </Box>
                  {hasPermission("onboarding.template.manage") && (
                    <>
                      <Button
                        size="small"
                        onClick={() => {
                          setEditingTemplate(row);
                          setTemplateItems(row.items);
                          setTemplateOpen(true);
                        }}
                      >
                        {t("onboarding.edit")}
                      </Button>
                      {row.is_active && (
                        <Button
                          size="small"
                          color="error"
                          onClick={() => removeTemplate.mutate(row.id)}
                        >
                          {t("onboarding.delete")}
                        </Button>
                      )}
                    </>
                  )}
                </Stack>
              ))}
            </Paper>
          </Stack>
          {hasPermission("onboarding.template.manage") && (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" fontWeight={900}>
                {t("onboarding.programs")}
              </Typography>
              {!bundles.data?.length && (
                <Typography color="text.secondary">
                  {t("onboarding.programsEmpty")}
                </Typography>
              )}
              {bundles.data?.map((row) => (
                <Stack
                  key={row.id}
                  direction="row"
                  alignItems="center"
                  py={0.5}
                >
                  <Box flex={1}>
                    <Typography fontWeight={800}>{row.name}</Typography>
                    <Typography variant="caption">
                      <span dir="ltr">{row.code}</span> ·{" "}
                      {t("onboarding.programSummary", {
                        count: Intl.NumberFormat(locale).format(
                          row.items.length,
                        ),
                        version: Intl.NumberFormat(locale).format(row.version),
                      })}
                    </Typography>
                  </Box>
                  <Button
                    size="small"
                    onClick={() => {
                      setEditingBundle(row);
                      setBundleItems(row.items);
                      setBundleOpen(true);
                    }}
                  >
                    {t("onboarding.edit")}
                  </Button>
                  {row.is_active && (
                    <Button
                      size="small"
                      color="error"
                      onClick={() => removeBundle.mutate(row.id)}
                    >
                      {t("onboarding.delete")}
                    </Button>
                  )}
                </Stack>
              ))}
            </Paper>
          )}
          {hasPermission("onboarding.item.override") && (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" fontWeight={900}>
                {t("onboarding.approvals")}
              </Typography>
              {!approvals.data?.length && (
                <Typography color="text.secondary">
                  {t("onboarding.noApprovals")}
                </Typography>
              )}
              {approvals.data?.map((row) => (
                <Stack
                  key={row.item_id}
                  direction={{ xs: "column", sm: "row" }}
                  gap={1}
                  alignItems={{ sm: "center" }}
                  py={1}
                >
                  <Box flex={1}>
                    <Typography fontWeight={800}>
                      {row.employee_name} · {row.title}
                    </Typography>
                    <Typography variant="caption">
                      {catalogs.data?.completion_types.find(
                        (value) => value.code === row.completion_type_code,
                      )?.name ?? row.completion_type_code}
                      {row.submitted_at &&
                        ` · ${t("onboarding.submitted", { date: new Date(row.submitted_at).toLocaleString(locale) })}`}
                    </Typography>
                  </Box>
                  <Button
                    color="error"
                    disabled={review.isPending}
                    onClick={() => review.mutate({ row, decision: "REJECTED" })}
                  >
                    {t("onboarding.return")}
                  </Button>
                  <Button
                    color="success"
                    variant="contained"
                    disabled={review.isPending}
                    onClick={() => review.mutate({ row, decision: "APPROVED" })}
                  >
                    {t("onboarding.approve")}
                  </Button>
                </Stack>
              ))}
            </Paper>
          )}
          {selectedMaterialId &&
            hasPermission("onboarding.material.manage") && (
              <Paper
                component="form"
                onSubmit={submitResource}
                variant="outlined"
                sx={{ p: 2 }}
              >
                <Typography variant="h6">
                  {t("onboarding.resourcesFor", {
                    title: materials.data?.find(
                      (row) => row.id === selectedMaterialId,
                    )?.title,
                  })}
                </Typography>
                {materials.data
                  ?.find((row) => row.id === selectedMaterialId)
                  ?.resources.map((resource) => (
                    <Stack
                      key={resource.id}
                      direction="row"
                      alignItems="center"
                      gap={1}
                      py={0.5}
                    >
                      <Box flex={1}>
                        {resource.name} ·{" "}
                        {t(`onboarding.resourceTypes.${resource.type}`, {
                          defaultValue: resource.type,
                        })}
                      </Box>
                      <Button component="a" href={resource.url} target="_blank">
                        {t("onboarding.open")}
                      </Button>
                      <Button onClick={() => setEditingResource(resource)}>
                        {t("onboarding.edit")}
                      </Button>
                      <Button
                        color="error"
                        startIcon={<Delete />}
                        onClick={() => removeResource.mutate(resource.id)}
                      >
                        {t("onboarding.remove")}
                      </Button>
                    </Stack>
                  ))}
                <Stack direction={{ xs: "column", md: "row" }} gap={1} mt={2}>
                  <TextField
                    required
                    name="name"
                    label={t("onboarding.resourceName")}
                  />
                  <TextField
                    required
                    select
                    name="resource_type"
                    label={t("onboarding.type")}
                    defaultValue="WEBSITE"
                  >
                    {[
                      "PDF",
                      "SHAREPOINT",
                      "VIDEO",
                      "KNOWLEDGE",
                      "WEBSITE",
                      "MICROSOFT_LEARN",
                      "OTHER",
                    ].map((value) => (
                      <MenuItem key={value} value={value}>
                        {t(`onboarding.resourceTypes.${value}`)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    required
                    name="url"
                    type="url"
                    label={t("onboarding.url")}
                    fullWidth
                  />
                  <TextField
                    name="display_order"
                    type="number"
                    label={t("onboarding.order")}
                    defaultValue="0"
                  />
                  <Button type="submit" variant="contained">
                    {t("onboarding.addResource")}
                  </Button>
                </Stack>
              </Paper>
            )}
        </Stack>
      )}
      <Dialog
        open={categoryOpen}
        onClose={() => {
          setCategoryOpen(false);
          setEditingCategory(null);
        }}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          key={editingCategory?.id ?? "new-category"}
          onSubmit={submitCategory}
        >
          <DialogTitle>
            {t("onboarding.categoryDialog", {
              action: t(
                editingCategory ? "onboarding.edit" : "onboarding.create",
              ),
            })}
          </DialogTitle>
          <DialogContent>
            <TextField
              required
              name="name"
              label={t("onboarding.categoryName")}
              defaultValue={editingCategory?.name ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="display_order"
              type="number"
              label={t("onboarding.displayOrder")}
              defaultValue={editingCategory?.display_order ?? 0}
              fullWidth
            />
            <FormControlLabel
              control={
                <Checkbox
                  name="is_active"
                  defaultChecked={editingCategory?.is_active ?? true}
                />
              }
              label={t("onboarding.active")}
            />
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setCategoryOpen(false);
                setEditingCategory(null);
              }}
            >
              {t("onboarding.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("onboarding.save")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={materialOpen}
        onClose={() => {
          setMaterialOpen(false);
          setEditingMaterial(null);
        }}
        fullWidth
        maxWidth="md"
      >
        <Box
          component="form"
          key={editingMaterial?.id ?? "new-material"}
          onSubmit={submitMaterial}
        >
          <DialogTitle>
            {t("onboarding.materialDialog", {
              action: t(
                editingMaterial ? "onboarding.edit" : "onboarding.create",
              ),
            })}
          </DialogTitle>
          <DialogContent>
            <Alert severity="info">{t("onboarding.materialNotice")}</Alert>
            <TextField
              required
              name="title"
              label={t("onboarding.topicTitle")}
              defaultValue={editingMaterial?.title ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="category_id"
              select
              label={t("onboarding.category")}
              defaultValue={editingMaterial?.category_id ?? ""}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("onboarding.noCategory")}</MenuItem>
              {categories.data
                ?.filter(
                  (row) =>
                    row.is_active || row.id === editingMaterial?.category_id,
                )
                .map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
                  </MenuItem>
                ))}
            </TextField>
            <Typography variant="h6" mt={1}>
              {t("onboarding.materialContent")}
            </Typography>
            {materialResources.map((resource, index) => (
              <Paper
                key={resource.id ?? `new-${index}`}
                variant="outlined"
                sx={{ p: 1.5, mt: 1 }}
              >
                <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                  <TextField
                    required
                    select
                    label={t("onboarding.materialType")}
                    value={resource.type}
                    onChange={(event) =>
                      setMaterialResources((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? { ...row, type: event.target.value }
                            : row,
                        ),
                      )
                    }
                    sx={{ minWidth: 180 }}
                  >
                    {[
                      "PDF",
                      "SHAREPOINT",
                      "VIDEO",
                      "KNOWLEDGE",
                      "WEBSITE",
                      "MICROSOFT_LEARN",
                      "OTHER",
                    ].map((value) => (
                      <MenuItem key={value} value={value}>
                        {t(`onboarding.resourceTypes.${value}`)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label={t("onboarding.contentName")}
                    value={resource.name}
                    onChange={(event) =>
                      setMaterialResources((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? { ...row, name: event.target.value }
                            : row,
                        ),
                      )
                    }
                    fullWidth
                  />
                  <TextField
                    required
                    type="url"
                    label={t("onboarding.materialUrl")}
                    placeholder="https://..."
                    value={resource.url}
                    onChange={(event) =>
                      setMaterialResources((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? { ...row, url: event.target.value }
                            : row,
                        ),
                      )
                    }
                    fullWidth
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={resource.is_active}
                        onChange={(_, checked) =>
                          setMaterialResources((rows) =>
                            rows.map((row, i) =>
                              i === index
                                ? { ...row, is_active: checked }
                                : row,
                            ),
                          )
                        }
                      />
                    }
                    label={t("onboarding.active")}
                  />
                  <Button
                    type="button"
                    color="error"
                    disabled={materialResources.length === 1}
                    onClick={() =>
                      setMaterialResources((rows) =>
                        rows.filter((_, i) => i !== index),
                      )
                    }
                  >
                    {t("onboarding.remove")}
                  </Button>
                </Stack>
              </Paper>
            ))}
            <Button
              type="button"
              startIcon={<Add />}
              sx={{ mt: 1 }}
              onClick={() =>
                setMaterialResources((rows) => [
                  ...rows,
                  {
                    name: "",
                    type: "WEBSITE",
                    url: "",
                    display_order: rows.length,
                    is_active: true,
                  },
                ])
              }
            >
              {t("onboarding.addMaterialType")}
            </Button>
            <TextField
              name="description"
              label={t("onboarding.description")}
              defaultValue={editingMaterial?.description ?? ""}
              fullWidth
              multiline
              rows={3}
              margin="normal"
            />
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              alignItems={{ sm: "center" }}
            >
              <TextField
                name="display_order"
                type="number"
                label={t("onboarding.displayOrder")}
                defaultValue={editingMaterial?.display_order ?? 0}
                fullWidth
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="is_required"
                    defaultChecked={editingMaterial?.required ?? false}
                  />
                }
                label={t("onboarding.requiredTopic")}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="is_active"
                    defaultChecked={editingMaterial?.is_active ?? true}
                  />
                }
                label={t("onboarding.active")}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="show_in_client_portal"
                    defaultChecked={
                      editingMaterial?.show_in_client_portal ?? false
                    }
                  />
                }
                label={t("onboarding.showPortal")}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setMaterialOpen(false);
                setEditingMaterial(null);
              }}
            >
              {t("onboarding.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={
                createMaterial.isPending ||
                saveMaterial.isPending ||
                !materialResources.length
              }
            >
              {t("onboarding.saveMaterial")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={templateOpen}
        onClose={() => {
          setTemplateOpen(false);
          setEditingTemplate(null);
        }}
        fullWidth
        maxWidth="md"
      >
        <Box
          component="form"
          key={editingTemplate?.id ?? "new-template"}
          onSubmit={submitTemplate}
        >
          <DialogTitle>
            {t("onboarding.templateDialog", {
              action: t(
                editingTemplate ? "onboarding.edit" : "onboarding.create",
              ),
            })}
          </DialogTitle>
          <DialogContent>
            <TextField
              name="code"
              label={t("onboarding.stableCode")}
              defaultValue={editingTemplate?.code ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              required
              name="name"
              label={t("onboarding.templateName")}
              defaultValue={editingTemplate?.name ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="category_id"
              select
              label={t("onboarding.category")}
              defaultValue={editingTemplate?.category_id ?? ""}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("onboarding.noCategory")}</MenuItem>
              {categories.data
                ?.filter(
                  (row) =>
                    row.is_active || row.id === editingTemplate?.category_id,
                )
                .map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
                  </MenuItem>
                ))}
            </TextField>
            <Stack direction="row" gap={1}>
              <TextField
                name="default_duration_days"
                type="number"
                label={t("onboarding.durationDays")}
                defaultValue={editingTemplate?.default_duration_days ?? ""}
                fullWidth
              />
              <TextField
                name="display_order"
                type="number"
                label={t("onboarding.order")}
                defaultValue={editingTemplate?.display_order ?? 0}
                fullWidth
              />
            </Stack>
            <TextField
              name="description"
              label={t("onboarding.description")}
              defaultValue={editingTemplate?.description ?? ""}
              fullWidth
              multiline
              rows={2}
            />
            <Typography variant="h6" mt={2}>
              {t("onboarding.checklistItems")}
            </Typography>
            {templateItems.map((item, index) => (
              <Paper key={index} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
                <Stack direction={{ xs: "column", md: "row" }} gap={1}>
                  <TextField
                    required
                    label={t("onboarding.fieldTitle")}
                    value={item.title}
                    onChange={(event) =>
                      setTemplateItems((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? { ...row, title: event.target.value }
                            : row,
                        ),
                      )
                    }
                    fullWidth
                  />
                  <TextField
                    label={t("onboarding.startAfterDays")}
                    type="number"
                    value={item.start_after_days ?? 0}
                    onChange={(event) =>
                      setTemplateItems((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? {
                                ...row,
                                start_after_days: Number(
                                  event.target.value || 0,
                                ),
                              }
                            : row,
                        ),
                      )
                    }
                  />
                  <TextField
                    label={t("onboarding.dueAfterDays")}
                    type="number"
                    value={item.due_after_days ?? ""}
                    onChange={(event) =>
                      setTemplateItems((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? {
                                ...row,
                                due_after_days: event.target.value
                                  ? Number(event.target.value)
                                  : undefined,
                              }
                            : row,
                        ),
                      )
                    }
                  />
                  <TextField
                    select
                    label={t("onboarding.material")}
                    value={item.material_id ?? ""}
                    onChange={(event) =>
                      setTemplateItems((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? {
                                ...row,
                                material_id: event.target.value
                                  ? Number(event.target.value)
                                  : undefined,
                              }
                            : row,
                        ),
                      )
                    }
                    sx={{ minWidth: 220 }}
                  >
                    <MenuItem value="">{t("onboarding.none")}</MenuItem>
                    {materials.data?.map((material) => (
                      <MenuItem key={material.id} value={material.id}>
                        {material.title}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    label={t("onboarding.taskType")}
                    value={item.task_type_code ?? "OTHER"}
                    onChange={(event) =>
                      setTemplateItems((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? { ...row, task_type_code: event.target.value }
                            : row,
                        ),
                      )
                    }
                    sx={{ minWidth: 180 }}
                  >
                    {catalogs.data?.task_types.map((value) => (
                      <MenuItem key={value.code} value={value.code}>
                        {value.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    label={t("onboarding.completion")}
                    value={item.completion_type_code ?? "SELF_COMPLETE"}
                    onChange={(event) =>
                      setTemplateItems((rows) =>
                        rows.map((row, i) =>
                          i === index
                            ? {
                                ...row,
                                completion_type_code: event.target.value,
                                requires_approval:
                                  event.target.value === "MANAGER_APPROVAL" ||
                                  event.target.value === "MENTOR_CONFIRMATION",
                              }
                            : row,
                        ),
                      )
                    }
                    sx={{ minWidth: 190 }}
                  >
                    {catalogs.data?.completion_types.map((value) => (
                      <MenuItem key={value.code} value={value.code}>
                        {value.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={item.required}
                        onChange={(_, checked) =>
                          setTemplateItems((rows) =>
                            rows.map((row, i) =>
                              i === index ? { ...row, required: checked } : row,
                            ),
                          )
                        }
                      />
                    }
                    label={t("onboarding.required")}
                  />
                  <Button
                    color="error"
                    disabled={templateItems.length === 1}
                    onClick={() =>
                      setTemplateItems((rows) =>
                        rows.filter((_, i) => i !== index),
                      )
                    }
                  >
                    {t("onboarding.remove")}
                  </Button>
                </Stack>
                <TextField
                  label={t("onboarding.instructions")}
                  value={item.description ?? ""}
                  onChange={(event) =>
                    setTemplateItems((rows) =>
                      rows.map((row, i) =>
                        i === index
                          ? { ...row, description: event.target.value }
                          : row,
                      ),
                    )
                  }
                  fullWidth
                  multiline
                  sx={{ mt: 1 }}
                />
              </Paper>
            ))}
            <Button
              startIcon={<Add />}
              onClick={() =>
                setTemplateItems((rows) => [
                  ...rows,
                  { title: "", description: "", required: true },
                ])
              }
            >
              {t("onboarding.addChecklistItem")}
            </Button>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setTemplateOpen(false);
                setEditingTemplate(null);
              }}
            >
              {t("onboarding.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!templateItems.length}
            >
              {t("onboarding.saveTemplate")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={bundleOpen}
        onClose={() => {
          setBundleOpen(false);
          setEditingBundle(null);
        }}
        fullWidth
        maxWidth="md"
      >
        <Box
          component="form"
          key={editingBundle?.id ?? "new-bundle"}
          onSubmit={submitBundle}
        >
          <DialogTitle>
            {t("onboarding.programDialog", {
              action: t(
                editingBundle ? "onboarding.edit" : "onboarding.create",
              ),
            })}
          </DialogTitle>
          <DialogContent>
            <TextField
              required
              name="code"
              label={t("onboarding.stableCode")}
              defaultValue={editingBundle?.code ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              required
              name="name"
              label={t("onboarding.programName")}
              defaultValue={editingBundle?.name ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="description"
              label={t("onboarding.description")}
              defaultValue={editingBundle?.description ?? ""}
              fullWidth
              multiline
              rows={2}
            />
            <TextField
              name="default_duration_days"
              type="number"
              label={t("onboarding.defaultDurationDays")}
              defaultValue={editingBundle?.default_duration_days ?? 60}
              fullWidth
              margin="normal"
            />
            <Typography variant="h6" mt={2}>
              {t("onboarding.programTemplates")}
            </Typography>
            {bundleItems.map((item, index) => (
              <Stack
                key={index}
                direction={{ xs: "column", md: "row" }}
                gap={1}
                mb={1}
              >
                <TextField
                  required
                  select
                  label={t("onboarding.checklistTemplate")}
                  value={item.template_id}
                  onChange={(event) =>
                    setBundleItems((rows) =>
                      rows.map((row, i) =>
                        i === index
                          ? { ...row, template_id: Number(event.target.value) }
                          : row,
                      ),
                    )
                  }
                  fullWidth
                >
                  {templates.data
                    ?.filter((row) => row.is_active)
                    .map((row) => (
                      <MenuItem key={row.id} value={row.id}>
                        {row.name}
                      </MenuItem>
                    ))}
                </TextField>
                <TextField
                  type="number"
                  label={t("onboarding.sequence")}
                  value={item.sequence_no}
                  onChange={(event) =>
                    setBundleItems((rows) =>
                      rows.map((row, i) =>
                        i === index
                          ? { ...row, sequence_no: Number(event.target.value) }
                          : row,
                      ),
                    )
                  }
                />
                <TextField
                  type="number"
                  label={t("onboarding.startAfterDays")}
                  value={item.start_after_days}
                  onChange={(event) =>
                    setBundleItems((rows) =>
                      rows.map((row, i) =>
                        i === index
                          ? {
                              ...row,
                              start_after_days: Number(event.target.value),
                            }
                          : row,
                      ),
                    )
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={item.required}
                      onChange={(_, checked) =>
                        setBundleItems((rows) =>
                          rows.map((row, i) =>
                            i === index ? { ...row, required: checked } : row,
                          ),
                        )
                      }
                    />
                  }
                  label={t("onboarding.required")}
                />
                <Button
                  color="error"
                  disabled={bundleItems.length === 1}
                  onClick={() =>
                    setBundleItems((rows) => rows.filter((_, i) => i !== index))
                  }
                >
                  {t("onboarding.remove")}
                </Button>
              </Stack>
            ))}
            <Button
              startIcon={<Add />}
              onClick={() =>
                setBundleItems((rows) => [
                  ...rows,
                  {
                    template_id: "",
                    sequence_no: (rows.length + 1) * 10,
                    start_after_days: 0,
                    required: true,
                  },
                ])
              }
            >
              {t("onboarding.addTemplate")}
            </Button>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setBundleOpen(false);
                setEditingBundle(null);
              }}
            >
              {t("onboarding.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!bundleItems.some((item) => item.template_id)}
            >
              {t("onboarding.saveProgram")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={assignOpen}
        onClose={() => {
          setAssignOpen(false);
          setAssignUserId("");
          setAssignSource("");
          setAssignMentorId("");
          setAssignmentTasks([]);
        }}
        fullWidth
        maxWidth="md"
      >
        <Box component="form" onSubmit={submitAssign}>
          <DialogTitle>
            {t(
              employees.data?.find(
                (employee) => employee.id === Number(assignUserId),
              )?.has_active_plan
                ? "onboarding.changeAssignment"
                : "onboarding.assignOnboarding",
            )}
          </DialogTitle>
          <DialogContent>
            <TextField
              required
              select
              name="user_id"
              label={t("onboarding.employeeField")}
              value={assignUserId}
              onChange={(event) => setAssignUserId(event.target.value)}
              fullWidth
              margin="normal"
            >
              {employees.data?.map((employee) => (
                <MenuItem key={employee.id} value={employee.id}>
                  {employee.name} ·{" "}
                  {employee.department ?? t("onboarding.noDepartment")}
                  {employee.has_active_plan
                    ? ` · ${t("onboarding.current", { name: employee.active_plan_name })}`
                    : ""}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              required
              select
              name="source"
              label={t("onboarding.source")}
              value={assignSource}
              onChange={(event) => selectAssignmentSource(event.target.value)}
              fullWidth
              margin="normal"
            >
              {bundles.data
                ?.filter((row) => row.is_active)
                .map((bundle) => (
                  <MenuItem
                    key={`bundle-${bundle.id}`}
                    value={`bundle:${bundle.id}`}
                  >
                    {t("onboarding.programOption", {
                      name: bundle.name,
                      count: Intl.NumberFormat(locale).format(
                        bundle.items.length,
                      ),
                    })}
                  </MenuItem>
                ))}
              {templates.data
                ?.filter((row) => row.is_active)
                .map((template) => (
                  <MenuItem
                    key={`template-${template.id}`}
                    value={`template:${template.id}`}
                  >
                    {t("onboarding.templateOption", {
                      name: template.name,
                      count: Intl.NumberFormat(locale).format(
                        template.items.length,
                      ),
                    })}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              required
              name="start_date"
              type="date"
              label={t("onboarding.startDate")}
              defaultValue={serverDateInput()}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              select
              label="Program mentor"
              value={assignMentorId}
              onChange={(event) => setAssignMentorId(event.target.value)}
              fullWidth
              margin="normal"
            >
              <MenuItem value="">No program mentor</MenuItem>
              {mentors.data
                ?.filter((person) => person.id !== Number(assignUserId))
                .map((person) => (
                  <MenuItem key={person.id} value={person.id}>
                    {person.name} · {person.department || "No department"}
                  </MenuItem>
                ))}
            </TextField>
            {assignmentTasks.length > 0 && (
              <Box mt={2}>
                <Typography fontWeight={800}>
                  Task schedule and mentors
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Tasks inherit the program mentor unless you choose a different
                  mentor or no mentor.
                </Typography>
                {assignmentTasks.map((task, index) => (
                  <Paper key={task.id} variant="outlined" sx={{ p: 1, mb: 1 }}>
                    <Stack
                      direction={{ xs: "column", md: "row" }}
                      gap={1}
                      alignItems={{ md: "center" }}
                    >
                      <Typography flex={1}>{task.title}</Typography>
                      <TextField
                        required
                        type="number"
                        label={t("onboarding.days")}
                        value={task.duration_days}
                        onChange={(event) =>
                          setAssignmentTasks((rows) =>
                            rows.map((row, i) =>
                              i === index
                                ? {
                                    ...row,
                                    duration_days: Number(event.target.value),
                                  }
                                : row,
                            ),
                          )
                        }
                        inputProps={{ min: 1, max: 730 }}
                        sx={{ width: 120 }}
                      />
                      <TextField
                        select
                        label="Mentor"
                        value={task.mentor_mode}
                        onChange={(event) =>
                          setAssignmentTasks((rows) =>
                            rows.map((row, i) =>
                              i === index
                                ? {
                                    ...row,
                                    mentor_mode: event.target
                                      .value as AssignmentTask["mentor_mode"],
                                    mentor_user_id: undefined,
                                  }
                                : row,
                            ),
                          )
                        }
                        sx={{ minWidth: 180 }}
                      >
                        <MenuItem value="INHERIT">Program mentor</MenuItem>
                        <MenuItem value="SPECIFIC">Different mentor</MenuItem>
                        <MenuItem value="NONE">No mentor</MenuItem>
                      </TextField>
                      {task.mentor_mode === "SPECIFIC" && (
                        <TextField
                          required
                          select
                          label="Person"
                          value={task.mentor_user_id ?? ""}
                          onChange={(event) =>
                            setAssignmentTasks((rows) =>
                              rows.map((row, i) =>
                                i === index
                                  ? {
                                      ...row,
                                      mentor_user_id: Number(
                                        event.target.value,
                                      ),
                                    }
                                  : row,
                              ),
                            )
                          }
                          sx={{ minWidth: 220 }}
                        >
                          {mentors.data
                            ?.filter(
                              (person) => person.id !== Number(assignUserId),
                            )
                            .map((person) => (
                              <MenuItem key={person.id} value={person.id}>
                                {person.name}
                              </MenuItem>
                            ))}
                        </TextField>
                      )}
                    </Stack>
                  </Paper>
                ))}
              </Box>
            )}
            {employees.data?.find(
              (employee) => employee.id === Number(assignUserId),
            )?.has_active_plan && (
              <>
                <Alert severity="warning" sx={{ mt: 1 }}>
                  {t("onboarding.replaceWarning")}
                </Alert>
                <TextField
                  required
                  name="reason"
                  label={t("onboarding.changeReason")}
                  multiline
                  rows={3}
                  inputProps={{ minLength: 5 }}
                  fullWidth
                  margin="normal"
                />
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setAssignOpen(false);
                setAssignUserId("");
                setAssignSource("");
                setAssignMentorId("");
                setAssignmentTasks([]);
              }}
            >
              {t("onboarding.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={assign.isPending || replaceAssignment.isPending}
            >
              {t(
                employees.data?.find(
                  (employee) => employee.id === Number(assignUserId),
                )?.has_active_plan
                  ? "onboarding.change"
                  : "onboarding.assignSnapshot",
              )}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={unassignOpen}
        onClose={() => setUnassignOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget),
              employee = employees.data?.find(
                (row) => row.id === Number(data.get("user_id")),
              );
            if (employee?.active_plan_id && employee.active_plan_version)
              unassign.mutate({
                planId: employee.active_plan_id,
                version: employee.active_plan_version,
                reason: String(data.get("reason")),
              });
          }}
        >
          <DialogTitle>{t("onboarding.unassignTitle")}</DialogTitle>
          <DialogContent>
            <Alert severity="warning">{t("onboarding.unassignWarning")}</Alert>
            <TextField
              required
              select
              name="user_id"
              label={t("onboarding.assignedUser")}
              defaultValue=""
              fullWidth
              margin="normal"
            >
              {employees.data
                ?.filter((employee) => employee.has_active_plan)
                .map((employee) => (
                  <MenuItem key={employee.id} value={employee.id}>
                    {employee.name} · {employee.active_plan_name}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              required
              name="reason"
              label={t("onboarding.unassignReason")}
              multiline
              rows={3}
              inputProps={{ minLength: 5 }}
              fullWidth
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setUnassignOpen(false)}>
              {t("onboarding.cancel")}
            </Button>
            <Button
              type="submit"
              color="error"
              variant="contained"
              disabled={unassign.isPending}
            >
              {t("onboarding.unassignUser")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(editingResource)}
        onClose={() => setEditingResource(null)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          key={editingResource?.id}
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            saveResource.mutate({
              name: data.get("name"),
              resource_type: data.get("resource_type"),
              url: data.get("url"),
              display_order: Number(data.get("display_order") || 0),
              is_active: data.get("is_active") === "on",
            });
          }}
        >
          <DialogTitle>{t("onboarding.editContent")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="name"
              label={t("onboarding.resourceName")}
              defaultValue={editingResource?.name ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              required
              select
              name="resource_type"
              label={t("onboarding.type")}
              defaultValue={editingResource?.type ?? "WEBSITE"}
              fullWidth
              margin="normal"
            >
              {[
                "PDF",
                "SHAREPOINT",
                "VIDEO",
                "KNOWLEDGE",
                "WEBSITE",
                "MICROSOFT_LEARN",
                "OTHER",
              ].map((value) => (
                <MenuItem key={value} value={value}>
                  {t(`onboarding.resourceTypes.${value}`)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              required
              name="url"
              type="url"
              label={t("onboarding.url")}
              defaultValue={editingResource?.url ?? ""}
              fullWidth
              margin="normal"
            />
            <TextField
              name="display_order"
              type="number"
              label={t("onboarding.order")}
              defaultValue={editingResource?.display_order ?? 0}
              fullWidth
            />
            <FormControlLabel
              control={
                <Checkbox
                  name="is_active"
                  defaultChecked={editingResource?.is_active ?? true}
                />
              }
              label={t("onboarding.active")}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditingResource(null)}>
              {t("onboarding.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("onboarding.saveContent")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
