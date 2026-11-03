import {
  Add,
  ArrowForwardIos,
  CheckCircle,
  ConfirmationNumber,
  Description,
  DragIndicator,
  HourglassBottom,
  Inbox,
  InfoOutlined,
  Launch,
  MoreVert,
  PersonAdd,
  PlayArrow,
  Refresh,
  SpaceDashboard,
  Settings,
  SwapHoriz,
  TrendingUp,
  UnfoldLess,
  UnfoldMore,
  WarningAmber,
  Work,
  WidthNormal,
} from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControlLabel,
  IconButton,
  ListSubheader,
  Menu,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TicketSendActionsDialog } from "../components/TicketSendActions";
import { OperationPanels } from "../components/HomeOperations";
import { TechnicalText } from "../components/TechnicalText";
import { playNotificationSound } from "../utils/notificationSound";

type TicketCard = {
  id: number;
  ticket_number: string;
  subject: string;
  client_name?: string;
  priority: string;
  status_id: number;
  assigned_user_id?: number;
  assigned_user_name?: string;
  is_shared_assignment?: boolean;
  version: number;
  updated_at: string;
  created_at: string;
  resolved_at?: string;
  support_follow_up_flag: boolean;
  sla_resolution_target_minutes?: number;
  sla_actual_business_minutes?: number;
  sla_overrun_minutes?: number;
  sla_resolution_state?: string;
};
type TicketStatus = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  color?: string;
};
type PreTicketCard = {
  id: number;
  pre_ticket_number: string;
  title: string;
  proposed_priority: string;
  status: string;
  submitted_at: string;
};
type TicketPreview = TicketCard & {
  description: string;
  assigned_team?: string;
  pending_reason?: string;
};
type PreviewComment = {
  id: number;
  body: string;
  is_internal: boolean;
  created_at: string;
};
type PreviewAttachment = {
  id: number;
  original_filename: string;
  size_bytes: number;
};
type Module =
  | "queue"
  | "mine"
  | "resolved"
  | "backlog"
  | "follow-up"
  | "sla-risk"
  | "missing-resolution"
  | "pre-tickets"
  | "ops";
type BacklogPeriod =
  "TODAY" | "THIS_WEEK" | "LAST_WEEK" | "THIS_MONTH" | "CUSTOM";
type AssistantSettings = {
  queue_refresh_seconds: number;
  count_refresh_seconds: number;
  unreceived_warning_minutes: number;
  queue_tab_attention_enabled: boolean;
  overdue_card_animation_enabled: boolean;
  mine_show_resolved: boolean;
  mine_show_closed: boolean;
  backlog_default_period: BacklogPeriod;
  page_size: number;
  allow_user_overrides: boolean;
  tab_sorting: Record<string, string>;
};
type TabFilters = { search: string; priority: string; status_code: string };
type WorkspaceState = {
  compact: boolean;
  width: number;
  page_size: number;
  hidden_card_fields: string[];
  tab_sorting: Record<string, string>;
  tab_filters: Record<string, TabFilters>;
  density: "comfortable" | "compact" | "dense";
  layout: "cards" | "list";
};
type CustomTab = {
  id: string;
  name: string;
  source_module: Exclude<Module, "pre-tickets">;
  filters: TabFilters;
  sorting: string;
};
type AssistantPreferences = {
  pinned_ticket_ids: number[];
  default_tab: string;
  workspace_state: WorkspaceState;
  custom_tabs: CustomTab[];
};

const PAGE_SIZE = 12;
const DEFAULT_SORTING: Record<Module, string> = {
  queue: "created_at:asc",
  mine: "updated_at:desc",
  resolved: "resolved_at:asc",
  backlog: "created_at:asc",
  "follow-up": "updated_at:desc",
  "sla-risk": "updated_at:desc",
  "missing-resolution": "updated_at:desc",
  "pre-tickets": "submitted_at:asc",
  ops: "updated_at:desc",
};
const UNRECEIVED_WARNING_MINUTES = 9;
const COMPACT_WIDTH = 480;
const STANDARD_WIDTH = 760;
const WIDE_WIDTH = 1080;
const legacyContextActionsVisible = () => false;
const MODULES: Module[] = [
  "queue",
  "mine",
  "resolved",
  "backlog",
  "follow-up",
  "sla-risk",
  "missing-resolution",
  "pre-tickets",
  "ops",
];
const EMPTY_FILTERS: TabFilters = { search: "", priority: "", status_code: "" };
const CARD_FIELDS = [
  "client",
  "priority",
  "status",
  "updated",
  "created",
  "sla",
];
const SORT_OPTIONS = [
  "created_at:asc",
  "created_at:desc",
  "updated_at:asc",
  "updated_at:desc",
  "resolved_at:asc",
  "resolved_at:desc",
  "priority:asc",
  "priority:desc",
  "submitted_at:asc",
  "submitted_at:desc",
];

export function clampAssistantWidth(width: number, viewportWidth: number) {
  return Math.min(1200, Math.max(360, Math.min(width, viewportWidth - 24)));
}

function readAssistantPreference(key: string) {
  try {
    return typeof globalThis.localStorage?.getItem === "function"
      ? globalThis.localStorage.getItem(key)
      : null;
  } catch {
    return null;
  }
}

function saveAssistantPreference(key: string, value: string) {
  try {
    if (typeof globalThis.localStorage?.setItem === "function")
      globalThis.localStorage.setItem(key, value);
  } catch {
    // Storage can be disabled in private or managed browser sessions.
  }
}

export function isUnreceivedQueueTicket(
  ticket: Pick<TicketCard, "assigned_user_id" | "created_at">,
  now = Date.now(),
  isInUnassignedQueue = false,
  warningMinutes = UNRECEIVED_WARNING_MINUTES,
) {
  const createdAt = Date.parse(ticket.created_at);
  return (
    (isInUnassignedQueue || ticket.assigned_user_id == null) &&
    Number.isFinite(createdAt) &&
    now - createdAt >= warningMinutes * 60_000
  );
}

function slaText(
  ticket: TicketCard,
  t: (key: string, values?: Record<string, unknown>) => string,
) {
  if (ticket.sla_overrun_minutes && ticket.sla_overrun_minutes > 0)
    return t("supportWorkspace.slaOverdue", {
      minutes: Math.ceil(ticket.sla_overrun_minutes),
    });
  if (
    ticket.sla_resolution_target_minutes == null ||
    ticket.sla_actual_business_minutes == null
  )
    return t("supportWorkspace.slaUnavailable");
  return t("supportWorkspace.slaRemaining", {
    minutes: Math.max(
      0,
      Math.ceil(
        ticket.sla_resolution_target_minutes -
          ticket.sla_actual_business_minutes,
      ),
    ),
  });
}

export function SupportWorkspacePage() {
  const isIndependentWindow = window.name === "support-assistant";
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("sm"));
  const { t, i18n } = useTranslation();
  const { hasPermission, user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const resolutionWorkflowSettings = useQuery({
    queryKey: ["site-settings", "ticket-resolution-workflow"],
    queryFn: async () =>
      (
        await api.get<{ resolution_details_required_on_close?: boolean }>(
          "/system/site-settings",
        )
      ).data,
  });
  const activeMajorIncidents = useQuery({
    queryKey: ["support-workspace", "active-major-incidents"],
    queryFn: async () =>
      (
        await api.get<
          Array<{
            id: number;
            major_incident_number: string;
            severity: string;
            status: string;
            client_name?: string | null;
            subject: string;
            current_status_summary: string;
            next_update_at?: string | null;
          }>
        >("/major-incident-portfolio", { params: { limit: 50 } })
      ).data.filter(
        (item) =>
          ["SEV1", "SEV2"].includes(item.severity) &&
          !["CLOSED", "CANCELLED"].includes(item.status),
      ),
    enabled: hasPermission("major_incident.view"),
    refetchInterval: 60_000,
  });
  const tabAccess: Record<Module, boolean> = {
    queue: hasPermission("support_assistant.queue.view"),
    mine: hasPermission("support_assistant.mine.view"),
    resolved: hasPermission("support_assistant.mine.view"),
    backlog: hasPermission("support_assistant.backlog.view"),
    "follow-up": hasPermission("support_assistant.follow_up.view"),
    "sla-risk": hasPermission("support_assistant.sla_risk.view"),
    "missing-resolution":
      hasPermission("support_assistant.mine.view") &&
      resolutionWorkflowSettings.data?.resolution_details_required_on_close ===
        true,
    "pre-tickets":
      hasPermission("support_assistant.pre_ticket.view") &&
      (hasPermission("ticket.pre_ticket.queue.view") ||
        hasPermission("ticket.pre_ticket.view.own")),
    ops:
      hasPermission("support_assistant.ops.view") &&
      hasPermission("internal_operation.view"),
  };
  const canViewQueue = Object.entries(tabAccess).some(
    ([key, value]) => key !== "pre-tickets" && value,
  );
  const canViewPreTickets = tabAccess["pre-tickets"];
  const canClaim = hasPermission("ticket.assign.self");
  const canChangeStatus = hasPermission("ticket.change.status");
  const canStartProgress = hasPermission("ticket.start.progress");
  const requestedModule = searchParams.get("tab") as Module | null;
  const requestedCustomTabId = searchParams.get("custom");
  const [module, setModule] = useState<Module>(() =>
    requestedModule &&
    MODULES.includes(requestedModule) &&
    tabAccess[requestedModule]
      ? requestedModule
      : ((Object.keys(tabAccess) as Module[]).find((key) => tabAccess[key]) ??
        "queue"),
  );
  const [page, setPage] = useState(0);
  const [backlogPeriod, setBacklogPeriod] = useState<BacklogPeriod | null>(
    null,
  );
  const [backlogFrom, setBacklogFrom] = useState("");
  const [backlogTo, setBacklogTo] = useState("");
  const widthStorageKey = `support-assistant-width-${user?.id ?? "anonymous"}`;
  const compactStorageKey = `support-assistant-compact-${user?.id ?? "anonymous"}`;
  const [compact, setCompact] = useState(
    () => readAssistantPreference(compactStorageKey) === "true",
  );
  const [workspaceWidth, setWorkspaceWidth] = useState(() => {
    const saved = Number(readAssistantPreference(widthStorageKey));
    return Number.isFinite(saved) && saved >= 360 ? saved : STANDARD_WIDTH;
  });
  const lastExpandedWidth = useRef(
    workspaceWidth > COMPACT_WIDTH ? workspaceWidth : STANDARD_WIDTH,
  );
  const [widthMenuAnchor, setWidthMenuAnchor] = useState<HTMLElement | null>(
    null,
  );
  const [defaultTabMenu, setDefaultTabMenu] = useState<{
    anchor: HTMLElement;
    tab: Module;
  } | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsSection, setSettingsSection] = useState(0);
  const [activeCustomTabId, setActiveCustomTabId] = useState<string | null>(
    null,
  );
  const [selectedTicket, setSelectedTicket] = useState<TicketCard | null>(null);
  const [personalTabMenu, setPersonalTabMenu] = useState<{
    anchor: HTMLElement;
    tab: CustomTab;
  } | null>(null);
  const [draggedCustomTabId, setDraggedCustomTabId] = useState<string | null>(
    null,
  );
  const [draftPageSize, setDraftPageSize] = useState(PAGE_SIZE);
  const [draftHiddenFields, setDraftHiddenFields] = useState<string[]>([]);
  const [draftSorting, setDraftSorting] = useState<Record<string, string>>({});
  const [draftFilters, setDraftFilters] = useState<Record<string, TabFilters>>(
    {},
  );
  const [draftCustomTabs, setDraftCustomTabs] = useState<CustomTab[]>([]);
  const [newTabName, setNewTabName] = useState("");
  const [newTabSource, setNewTabSource] =
    useState<Exclude<Module, "pre-tickets">>("queue");
  const [draftDensity, setDraftDensity] =
    useState<WorkspaceState["density"]>("comfortable");
  const [showSubtitle, setShowSubtitle] = useState(false);
  const [queueAttention, setQueueAttention] = useState(false);
  const knownQueueIds = useRef<Set<number> | null>(null);
  const pendingQueueSound = useRef(false);
  const [clock, setClock] = useState(() => Date.now());
  const [actionError, setActionError] = useState("");
  const [menu, setMenu] = useState<{
    position: { top: number; left: number };
    ticket: TicketCard;
  } | null>(null);
  const [otherActionsAnchor, setOtherActionsAnchor] =
    useState<HTMLElement | null>(null);
  const [draggedTicketId, setDraggedTicketId] = useState<number | null>(null);
  const [headerMenuAnchor, setHeaderMenuAnchor] = useState<HTMLElement | null>(
    null,
  );
  const [sendTicketId, setSendTicketId] = useState<number | null>(null);
  const [online, setOnline] = useState(() => navigator.onLine);
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const resizeIndependentWindow = (contentWidth: number) => {
    if (!isIndependentWindow) return;
    const browserFrameWidth = Math.max(
      0,
      window.outerWidth - window.innerWidth,
    );
    window.resizeTo(contentWidth + browserFrameWidth, window.outerHeight);
  };
  const setAssistantWidth = (width: number, makeCompact = false) => {
    const next = isIndependentWindow
      ? Math.min(WIDE_WIDTH, Math.max(COMPACT_WIDTH, width))
      : clampAssistantWidth(width, window.innerWidth);
    setWorkspaceWidth(next);
    setCompact(makeCompact);
    if (!makeCompact) lastExpandedWidth.current = next;
    resizeIndependentWindow(width);
  };
  const toggleCompact = () => {
    if (compact) setAssistantWidth(lastExpandedWidth.current);
    else {
      lastExpandedWidth.current = workspaceWidth;
      setAssistantWidth(COMPACT_WIDTH, true);
    }
  };
  const startResize = (event: ReactPointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = workspaceWidth;
    const direction = i18n.dir();
    const move = (pointerEvent: PointerEvent) => {
      const delta =
        (pointerEvent.clientX - startX) * (direction === "rtl" ? -1 : 1);
      const next = isIndependentWindow
        ? Math.min(WIDE_WIDTH, Math.max(COMPACT_WIDTH, startWidth + delta))
        : clampAssistantWidth(startWidth + delta, window.innerWidth);
      setWorkspaceWidth(next);
      if (!compact) lastExpandedWidth.current = next;
      resizeIndependentWindow(next);
    };
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
  };
  useEffect(() => {
    saveAssistantPreference(widthStorageKey, String(workspaceWidth));
    saveAssistantPreference(compactStorageKey, String(compact));
  }, [compact, compactStorageKey, workspaceWidth, widthStorageKey]);
  useEffect(() => {
    const fitToViewport = () =>
      setWorkspaceWidth((current) =>
        isIndependentWindow
          ? Math.min(WIDE_WIDTH, Math.max(COMPACT_WIDTH, window.innerWidth))
          : clampAssistantWidth(current, window.innerWidth),
      );
    window.addEventListener("resize", fitToViewport);
    return () => window.removeEventListener("resize", fitToViewport);
  }, [isIndependentWindow]);
  const notificationPreferences = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: async () =>
      (
        await api.get<{
          sound_enabled: boolean;
          sound_code: string;
          volume_percent: number;
        }>("/notification-preferences/me")
      ).data,
  });
  const preferences = useQuery({
    queryKey: ["support-assistant-preferences"],
    queryFn: async () =>
      (
        await api.get<AssistantPreferences>(
          "/tickets/support-assistant/preferences",
        )
      ).data,
    enabled: canViewQueue || canViewPreTickets,
  });
  const savePreferences = useMutation({
    mutationFn: async (data: AssistantPreferences) =>
      (
        await api.put<AssistantPreferences>(
          "/tickets/support-assistant/preferences",
          data,
        )
      ).data,
    onSuccess: (data) =>
      queryClient.setQueryData(["support-assistant-preferences"], data),
    onError: () => setActionError(t("supportWorkspace.preferenceFailed")),
  });
  const assistantSettings = useQuery({
    queryKey: ["support-assistant-settings"],
    queryFn: async () =>
      (
        await api.get<{ values: AssistantSettings }>(
          "/system/site-settings/support-assistant",
        )
      ).data.values,
    staleTime: 60_000,
  });
  const settings = assistantSettings.data;
  const refreshMs = (settings?.queue_refresh_seconds ?? 30) * 1000;
  const countRefreshMs = (settings?.count_refresh_seconds ?? 30) * 1000;
  const workspaceState: WorkspaceState = preferences.data?.workspace_state ?? {
    compact: false,
    width: STANDARD_WIDTH,
    page_size: settings?.page_size ?? PAGE_SIZE,
    hidden_card_fields: [],
    tab_sorting: {},
    tab_filters: {},
    density: "comfortable",
    layout: "cards",
  };
  const density = workspaceState.density;
  const customTabs = preferences.data?.custom_tabs ?? [];
  const activeCustomTab = customTabs.find(
    (tab) => tab.id === activeCustomTabId,
  );
  const activeTabKey = activeCustomTab
    ? `custom:${activeCustomTab.id}`
    : module;
  const activeFilters =
    activeCustomTab?.filters ??
    workspaceState.tab_filters[module] ??
    EMPTY_FILTERS;
  const backlogCountFilters =
    workspaceState.tab_filters.backlog ?? EMPTY_FILTERS;
  const pageSize = workspaceState.page_size;
  const selectedBacklogPeriod =
    backlogPeriod ?? settings?.backlog_default_period ?? "THIS_MONTH";
  const dateValue = (date: Date) => date.toLocaleDateString("en-CA");
  const backlogDates = (() => {
    const today = new Date();
    if (selectedBacklogPeriod === "CUSTOM")
      return { from: backlogFrom || undefined, to: backlogTo || undefined };
    if (selectedBacklogPeriod === "TODAY")
      return { from: dateValue(today), to: dateValue(today) };
    if (selectedBacklogPeriod === "THIS_MONTH")
      return {
        from: dateValue(new Date(today.getFullYear(), today.getMonth(), 1)),
        to: dateValue(today),
      };
    const mondayOffset = (today.getDay() + 6) % 7;
    const monday = new Date(today);
    monday.setDate(today.getDate() - mondayOffset);
    if (selectedBacklogPeriod === "THIS_WEEK")
      return { from: dateValue(monday), to: dateValue(today) };
    const lastMonday = new Date(monday);
    lastMonday.setDate(monday.getDate() - 7);
    const lastSunday = new Date(monday);
    lastSunday.setDate(monday.getDate() - 1);
    return { from: dateValue(lastMonday), to: dateValue(lastSunday) };
  })();
  const queueWatcher = useQuery({
    queryKey: ["support-workspace", "queue-watch", user?.id],
    queryFn: async () =>
      (
        await api.get<TicketCard[]>("/tickets", {
          params: { assistant_module: "queue", limit: 50, offset: 0 },
        })
      ).data,
    enabled: tabAccess.queue,
    refetchInterval: refreshMs,
    refetchIntervalInBackground: false,
  });
  const statuses = useQuery({
    queryKey: ["ticket-statuses"],
    queryFn: async () =>
      (await api.get<TicketStatus[]>("/ticket-statuses")).data,
    enabled: canViewQueue,
    staleTime: 300_000,
  });
  const ticketPreview = useQuery({
    queryKey: ["support-assistant-preview", selectedTicket?.id],
    queryFn: async () =>
      (await api.get<TicketPreview>(`/tickets/${selectedTicket!.id}`)).data,
    enabled: Boolean(selectedTicket),
  });
  const previewComments = useQuery({
    queryKey: ["ticket-comments", selectedTicket?.id],
    queryFn: async () =>
      (
        await api.get<PreviewComment[]>(
          `/tickets/${selectedTicket!.id}/comments`,
        )
      ).data,
    enabled: Boolean(selectedTicket),
  });
  const previewAttachments = useQuery({
    queryKey: ["ticket-attachments", selectedTicket?.id],
    queryFn: async () =>
      (
        await api.get<PreviewAttachment[]>(
          `/tickets/${selectedTicket!.id}/attachments`,
        )
      ).data,
    enabled: Boolean(selectedTicket),
  });
  const ticketQuery = useQuery({
    queryKey: [
      "support-workspace",
      activeTabKey,
      module,
      page,
      user?.id,
      selectedBacklogPeriod,
      backlogDates.from,
      backlogDates.to,
      backlogCountFilters.search,
      backlogCountFilters.priority,
      backlogCountFilters.status_code,
      settings,
      workspaceState,
      activeFilters,
    ],
    queryFn: async () => {
      const filters: Record<string, unknown> = { assistant_module: module };
      if (activeFilters.search) filters.search = activeFilters.search;
      if (activeFilters.priority) filters.priority = activeFilters.priority;
      if (activeFilters.status_code)
        filters.status_code = activeFilters.status_code;
      if (module === "backlog") {
        filters.created_from = backlogDates.from;
        filters.created_to = backlogDates.to;
      }
      if (module === "mine" && settings && !activeFilters.status_code) {
        const codes = [
          "NEW",
          "TRIAGED",
          "ASSIGNED",
          "IN_PROGRESS",
          "PENDING_CLIENT",
          "PENDING_INTERNAL",
          "PENDING_VENDOR",
          "REOPENED",
        ];
        if (settings.mine_show_resolved) codes.push("RESOLVED");
        if (settings.mine_show_closed) codes.push("CLOSED");
        filters.status_code = codes.join(",");
      }
      if (module === "resolved") filters.incomplete_resolution_only = true;
      const [sort_by, sort_direction] = (
        activeCustomTab?.sorting ??
        workspaceState?.tab_sorting?.[module] ??
        settings?.tab_sorting?.[module] ??
        DEFAULT_SORTING[module]
      ).split(":");
      const response = await api.get<TicketCard[]>("/tickets", {
        params: {
          ...filters,
          limit: pageSize,
          offset: page * pageSize,
          sort_by,
          sort_direction,
        },
      });
      return {
        items: response.data,
        total: Number(
          response.headers["x-total-count"] ?? response.data.length,
        ),
      };
    },
    enabled: module !== "pre-tickets" && module !== "ops" && tabAccess[module],
    refetchInterval: refreshMs,
    refetchIntervalInBackground: false,
  });
  const visibleQueueItems =
    module === "queue" ? ticketQuery.data?.items : undefined;
  useEffect(() => {
    const observed = visibleQueueItems ?? queueWatcher.data;
    if (!observed) return;
    if (!knownQueueIds.current) {
      knownQueueIds.current = new Set(observed.map((ticket) => ticket.id));
      return;
    }
    const additions = observed.filter(
      (ticket) => !knownQueueIds.current?.has(ticket.id),
    );
    observed.forEach((ticket) => knownQueueIds.current?.add(ticket.id));
    if (!additions.length) return;
    if (settings?.queue_tab_attention_enabled !== false)
      setQueueAttention(true);
    pendingQueueSound.current = true;
    if (notificationPreferences.data?.sound_enabled) {
      pendingQueueSound.current = false;
      void playNotificationSound(
        notificationPreferences.data.sound_code,
        notificationPreferences.data.volume_percent,
      );
    }
  }, [
    notificationPreferences.data,
    queueWatcher.data,
    settings?.queue_tab_attention_enabled,
    visibleQueueItems,
  ]);
  useEffect(() => {
    if (!pendingQueueSound.current || !notificationPreferences.data) return;
    pendingQueueSound.current = false;
    if (notificationPreferences.data.sound_enabled)
      void playNotificationSound(
        notificationPreferences.data.sound_code,
        notificationPreferences.data.volume_percent,
      );
  }, [notificationPreferences.data]);
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  const preTicketQuery = useQuery({
    queryKey: [
      "support-workspace",
      "pre-tickets",
      page,
      pageSize,
      workspaceState?.tab_sorting?.["pre-tickets"],
      settings?.tab_sorting?.["pre-tickets"],
    ],
    queryFn: async () => {
      const [, preTicketSortDirection] = (
        workspaceState?.tab_sorting?.["pre-tickets"] ??
        settings?.tab_sorting?.["pre-tickets"] ??
        DEFAULT_SORTING["pre-tickets"]
      ).split(":");
      if (!hasPermission("ticket.pre_ticket.queue.view")) {
        const response = await api.get<PreTicketCard[]>("/pre-tickets/mine", {
          params: {
            unconverted_only: true,
            submitted_from: new Date().toLocaleDateString("en-CA"),
            submitted_to: new Date().toLocaleDateString("en-CA"),
            sort_direction: preTicketSortDirection,
          },
        });
        return {
          items: response.data.slice(
            page * pageSize,
            page * pageSize + pageSize,
          ),
          total: Number(
            response.headers["x-total-count"] ?? response.data.length,
          ),
        };
      }
      const today = new Date().toLocaleDateString("en-CA");
      const response = await api.get<PreTicketCard[]>("/pre-tickets/queue", {
        params: {
          unconverted_only: true,
          submitted_from: today,
          submitted_to: today,
          sort_direction: preTicketSortDirection,
          limit: pageSize,
          offset: page * pageSize,
        },
      });
      return {
        items: response.data,
        total: Number(
          response.headers["x-total-count"] ?? response.data.length,
        ),
      };
    },
    enabled: module === "pre-tickets" && canViewPreTickets,
    refetchInterval: refreshMs,
    refetchIntervalInBackground: false,
  });
  const tabCounts = useQuery({
    queryKey: [
      "support-workspace-counts",
      user?.id,
      backlogDates.from,
      backlogDates.to,
    ],
    queryFn: async () => {
      const ticketCount = async (
        assistant_module: Exclude<Module, "pre-tickets" | "ops">,
        status_code?: string,
      ) => {
        const response = await api.get<TicketCard[]>("/tickets", {
          params: {
            assistant_module,
            status_code,
            incomplete_resolution_only:
              assistant_module === "resolved" ? true : undefined,
            limit: 1,
          },
        });
        return Number(
          response.headers["x-total-count"] ?? response.data.length,
        );
      };
      const result: Partial<Record<Module, string>> = {};
      await Promise.all(
        (Object.keys(tabAccess) as Module[])
          .filter((key) => tabAccess[key])
          .map(async (key) => {
            if (key === "pre-tickets") {
              const today = new Date().toLocaleDateString("en-CA");
              const path = hasPermission("ticket.pre_ticket.queue.view")
                ? "/pre-tickets/queue"
                : "/pre-tickets/mine";
              const response = await api.get<PreTicketCard[]>(path, {
                params: {
                  unconverted_only: true,
                  submitted_from: today,
                  submitted_to: today,
                  limit: 1,
                },
              });
              result[key] = String(
                Number(
                  response.headers["x-total-count"] ?? response.data.length,
                ),
              );
            } else if (key === "mine") {
              const visibleCodes = [
                "NEW",
                "TRIAGED",
                "ASSIGNED",
                "IN_PROGRESS",
                "PENDING_CLIENT",
                "PENDING_INTERNAL",
                "PENDING_VENDOR",
                "REOPENED",
              ];
              const completedCodes: string[] = [];
              if (settings?.mine_show_resolved !== false) {
                visibleCodes.push("RESOLVED");
                completedCodes.push("RESOLVED");
              }
              if (settings?.mine_show_closed !== false) {
                visibleCodes.push("CLOSED");
                completedCodes.push("CLOSED");
              }
              const [all, completed] = await Promise.all([
                ticketCount(key, visibleCodes.join(",")),
                completedCodes.length
                  ? ticketCount(key, completedCodes.join(","))
                  : Promise.resolve(0),
              ]);
              result[key] = `${completed}/${all}`;
            } else if (key === "backlog") {
              const response = await api.get<TicketCard[]>("/tickets", {
                params: {
                  assistant_module: "backlog",
                  created_from: backlogDates.from,
                  created_to: backlogDates.to,
                  search: backlogCountFilters.search || undefined,
                  priority: backlogCountFilters.priority || undefined,
                  status_code: backlogCountFilters.status_code || undefined,
                  limit: 1,
                },
              });
              result[key] = String(
                Number(
                  response.headers["x-total-count"] ?? response.data.length,
                ),
              );
            } else if (key !== "ops")
              result[key] = String(await ticketCount(key));
          }),
      );
      return result;
    },
    refetchInterval: countRefreshMs,
  });
  const refresh = async () => {
    setActionError("");
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["support-workspace"] }),
      queryClient.invalidateQueries({ queryKey: ["support-workspace-counts"] }),
    ]);
  };
  const ticketAction = useMutation({
    mutationFn: async ({
      ticket,
      action,
    }: {
      ticket: TicketCard;
      action: "claim" | "start" | "claim-and-start";
    }) => {
      if (action === "claim")
        return api.post(`/tickets/${ticket.id}/claim`, {
          version: ticket.version,
        });
      let version = ticket.version;
      if (action === "claim-and-start") {
        const claimed = await api.post<TicketCard>(
          `/tickets/${ticket.id}/claim`,
          { version },
        );
        version = claimed.data.version;
      }
      return api.post(`/tickets/${ticket.id}/transition`, {
        to_status_code: "IN_PROGRESS",
        reason: "Work started from Support Assistant",
        version,
      });
    },
    onSuccess: refresh,
    onError: () => setActionError(t("supportWorkspace.actionFailed")),
  });
  const followUpAction = useMutation({
    mutationFn: async (ticket: TicketCard) =>
      api.put(`/tickets/${ticket.id}/support-follow-up`, {
        marked: !ticket.support_follow_up_flag,
        version: ticket.version,
      }),
    onSuccess: refresh,
    onError: () => setActionError(t("supportWorkspace.actionFailed")),
  });
  const active = module === "pre-tickets" ? preTicketQuery : ticketQuery;
  const total = active.data?.total ?? 0;
  const statusFor = (ticket: TicketCard) => {
    const status = statuses.data?.find((item) => item.id === ticket.status_id);
    if (ticket.is_shared_assignment && status?.code === "ASSIGNED")
      return statuses.data?.find((item) => item.code === "NEW") ?? status;
    return status;
  };
  const selectedStatuses = (value: string) => {
    const codes = new Set(
      value
        .split(",")
        .map((code) => code.trim())
        .filter(Boolean),
    );
    return (statuses.data ?? []).filter((status) => codes.has(status.code));
  };
  const statusLabel = (status: TicketStatus) =>
    language === "ar" && status.name_ar ? status.name_ar : status.name;
  const statusMultiSelect = (
    value: string,
    onChange: (value: string) => void,
  ) => (
    <Autocomplete
      multiple
      size="small"
      options={statuses.data ?? []}
      value={selectedStatuses(value)}
      loading={statuses.isLoading}
      disableCloseOnSelect
      getOptionLabel={statusLabel}
      isOptionEqualToValue={(option, selected) => option.code === selected.code}
      onChange={(_, selected) =>
        onChange(selected.map((status) => status.code).join(","))
      }
      renderOption={(props, option, { selected }) => (
        <li {...props} key={option.code}>
          <Checkbox checked={selected} size="small" sx={{ mr: 1 }} />
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              bgcolor: option.color || "text.disabled",
              mr: 1,
              flex: "0 0 auto",
            }}
          />
          <Box>
            <Typography variant="body2">{statusLabel(option)}</Typography>
            <Typography variant="caption" color="text.secondary">
              {option.code}
            </Typography>
          </Box>
        </li>
      )}
      renderTags={(selected, getTagProps) =>
        selected.map((status, index) => (
          <Chip
            {...getTagProps({ index })}
            key={status.code}
            size="small"
            label={statusLabel(status)}
            sx={{
              borderInlineStart: 3,
              borderInlineStartColor: status.color || "text.disabled",
            }}
          />
        ))
      }
      renderInput={(params) => (
        <TextField
          {...params}
          label={t("supportWorkspace.filterStatus", {
            defaultValue: "Statuses",
          })}
          placeholder={
            value
              ? ""
              : t("supportWorkspace.selectStatuses", {
                  defaultValue: "Select statuses",
                })
          }
        />
      )}
      sx={{ minWidth: 240 }}
    />
  );
  const pinnedIds = preferences.data?.pinned_ticket_ids ?? [];
  const defaultTab = preferences.data?.default_tab ?? "queue";
  const defaultBuiltInTab = MODULES.includes(defaultTab as Module)
    ? (defaultTab as Module)
    : null;
  const defaultCustomTab = defaultTab.startsWith("custom:")
    ? customTabs.find((tab) => tab.id === defaultTab.slice(7))
    : undefined;
  const canUseDefaultTab = Boolean(
    defaultBuiltInTab && tabAccess[defaultBuiltInTab],
  );
  const canUseDefaultCustomTab = Boolean(
    defaultCustomTab && tabAccess[defaultCustomTab.source_module],
  );
  const requestedModuleAccessible = Boolean(
    requestedModule &&
    MODULES.includes(requestedModule) &&
    tabAccess[requestedModule],
  );
  const requestedCustomTab = requestedCustomTabId
    ? customTabs.find((tab) => tab.id === requestedCustomTabId)
    : undefined;
  const requestedCustomAccessible = Boolean(
    requestedCustomTab && tabAccess[requestedCustomTab.source_module],
  );
  const defaultTabApplied = useRef(false);
  useEffect(() => {
    if (defaultTabApplied.current || !preferences.data) return;
    defaultTabApplied.current = true;
    if (requestedCustomTab && requestedCustomAccessible) {
      setActiveCustomTabId(requestedCustomTab.id);
      setModule(requestedCustomTab.source_module);
    } else if (requestedModule && requestedModuleAccessible) {
      setModule(requestedModule);
    } else if (defaultCustomTab && canUseDefaultCustomTab) {
      setActiveCustomTabId(defaultCustomTab.id);
      setModule(defaultCustomTab.source_module);
    } else if (defaultBuiltInTab && canUseDefaultTab)
      setModule(defaultBuiltInTab);
    setCompact(workspaceState.compact);
    setWorkspaceWidth(workspaceState.width);
  }, [
    canUseDefaultCustomTab,
    canUseDefaultTab,
    defaultBuiltInTab,
    defaultCustomTab,
    preferences.data,
    requestedCustomAccessible,
    requestedCustomTab,
    requestedModule,
    requestedModuleAccessible,
    workspaceState.compact,
    workspaceState.width,
  ]);
  const preferencePayload = (
    overrides: Partial<AssistantPreferences> = {},
  ): AssistantPreferences => ({
    pinned_ticket_ids: pinnedIds,
    default_tab: defaultTab,
    workspace_state: workspaceState,
    custom_tabs: customTabs,
    ...overrides,
  });
  const openSettings = () => {
    setDraftPageSize(pageSize);
    setDraftHiddenFields(workspaceState?.hidden_card_fields ?? []);
    setDraftSorting(workspaceState?.tab_sorting ?? {});
    setDraftFilters(workspaceState?.tab_filters ?? {});
    setDraftCustomTabs(customTabs);
    setDraftDensity(workspaceState?.density ?? "comfortable");
    setSettingsSection(0);
    setNewTabName("");
    setSettingsOpen(true);
  };
  const saveWorkspaceSettings = () => {
    savePreferences.mutate(
      preferencePayload({
        workspace_state: {
          compact,
          width: workspaceWidth,
          page_size: draftPageSize,
          hidden_card_fields: draftHiddenFields,
          tab_sorting: draftSorting,
          tab_filters: draftFilters,
          density: draftDensity,
          layout: "cards",
        },
        custom_tabs: draftCustomTabs,
        default_tab:
          defaultTab.startsWith("custom:") &&
          !draftCustomTabs.some((tab) => `custom:${tab.id}` === defaultTab)
            ? "queue"
            : defaultTab,
      }),
      { onSuccess: () => setSettingsOpen(false) },
    );
  };
  const updateDraftFilter = (
    tab: string,
    field: keyof TabFilters,
    value: string,
  ) =>
    setDraftFilters((current) => ({
      ...current,
      [tab]: { ...(current[tab] ?? EMPTY_FILTERS), [field]: value },
    }));
  const addCustomTab = () => {
    const name = newTabName.trim();
    if (name.length < 2 || draftCustomTabs.length >= 12) return;
    setDraftCustomTabs((current) => [
      ...current,
      {
        id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
        name,
        source_module: newTabSource,
        filters: { ...EMPTY_FILTERS },
        sorting: DEFAULT_SORTING[newTabSource],
      },
    ]);
    setNewTabName("");
  };
  const displayedTickets = [...(ticketQuery.data?.items ?? [])].sort(
    (left, right) => {
      if (module === "queue" || module === "mine") {
        const leftReopened = statusFor(left)?.code === "REOPENED";
        const rightReopened = statusFor(right)?.code === "REOPENED";
        if (leftReopened !== rightReopened) return leftReopened ? -1 : 1;
      }
      const leftIndex = pinnedIds.indexOf(left.id),
        rightIndex = pinnedIds.indexOf(right.id);
      if (leftIndex >= 0 && rightIndex >= 0) return leftIndex - rightIndex;
      if (leftIndex >= 0) return -1;
      if (rightIndex >= 0) return 1;
      return 0;
    },
  );
  const hiddenCardFields = new Set(workspaceState?.hidden_card_fields ?? []);
  const togglePin = (ticketId: number) =>
    savePreferences.mutate(
      preferencePayload({
        pinned_ticket_ids: pinnedIds.includes(ticketId)
          ? pinnedIds.filter((id) => id !== ticketId)
          : [...pinnedIds, ticketId],
      }),
    );
  const reorderCards = (targetTicketId: number) => {
    if (draggedTicketId == null || draggedTicketId === targetTicketId) return;
    const visibleIds = displayedTickets.map((ticket) => ticket.id);
    const from = visibleIds.indexOf(draggedTicketId);
    const to = visibleIds.indexOf(targetTicketId);
    if (from < 0 || to < 0) return;
    const reordered = [...visibleIds];
    reordered.splice(to, 0, reordered.splice(from, 1)[0]);
    savePreferences.mutate(
      preferencePayload({
        pinned_ticket_ids: [
          ...reordered,
          ...pinnedIds.filter((id) => !visibleIds.includes(id)),
        ],
      }),
    );
    setDraggedTicketId(null);
  };
  const openIndependent = () =>
    window.open(
      `${import.meta.env.BASE_URL}support-workspace`,
      "support-assistant",
      "popup=yes,width=520,height=820,resizable=yes,scrollbars=yes",
    );
  const openSupportHub = () =>
    window.open(import.meta.env.BASE_URL, "support-hub");
  const openAction = (ticket: TicketCard, action: string) => {
    setMenu(null);
    navigate(`/tickets/${ticket.id}?action=${encodeURIComponent(action)}`, {
      state: {
        returnTo: `/support-workspace?tab=${module}${activeCustomTab ? `&custom=${activeCustomTab.id}` : ""}`,
      },
    });
  };
  const openWhatsApp = async (ticket: TicketCard) => {
    const popup = window.open("about:blank", "_blank");
    setMenu(null);
    try {
      const result = (
        await api.get<{ url: string }>(`/tickets/${ticket.id}/whatsapp-contact`)
      ).data;
      if (popup) {
        popup.opener = null;
        popup.location.href = result.url;
      } else window.open(result.url, "_blank", "noopener,noreferrer");
    } catch {
      popup?.close();
      window.alert("The caller does not have a valid WhatsApp number.");
    }
  };
  const openTicket = (ticketId: number) =>
    navigate(`/tickets/${ticketId}`, {
      state: {
        returnTo: `/support-workspace?tab=${module}${activeCustomTab ? `&custom=${activeCustomTab.id}` : ""}`,
      },
    });
  const setDefaultTab = (tab: string) => {
    savePreferences.mutate(preferencePayload({ default_tab: tab }));
    setDefaultTabMenu(null);
    setPersonalTabMenu(null);
  };
  const saveCustomTabs = (tabs: CustomTab[]) => {
    const nextDefault =
      defaultTab.startsWith("custom:") &&
      !tabs.some((tab) => `custom:${tab.id}` === defaultTab)
        ? "queue"
        : defaultTab;
    savePreferences.mutate(
      preferencePayload({ custom_tabs: tabs, default_tab: nextDefault }),
    );
  };
  const reorderCustomTabs = (targetId: string) => {
    if (!draggedCustomTabId || draggedCustomTabId === targetId) return;
    const from = customTabs.findIndex((tab) => tab.id === draggedCustomTabId);
    const to = customTabs.findIndex((tab) => tab.id === targetId);
    if (from < 0 || to < 0) return;
    const reordered = [...customTabs];
    reordered.splice(to, 0, reordered.splice(from, 1)[0]);
    saveCustomTabs(reordered);
    setDraggedCustomTabId(null);
  };
  const moveCustomTab = (tabId: string, offset: -1 | 1) => {
    const from = customTabs.findIndex((tab) => tab.id === tabId);
    const to = from + offset;
    if (from < 0 || to < 0 || to >= customTabs.length) return;
    const reordered = [...customTabs];
    [reordered[from], reordered[to]] = [reordered[to], reordered[from]];
    saveCustomTabs(reordered);
    setPersonalTabMenu(null);
  };
  const clearActiveFilter = (field?: keyof TabFilters) => {
    const cleared = field
      ? { ...activeFilters, [field]: "" }
      : { ...EMPTY_FILTERS };
    if (activeCustomTab) {
      saveCustomTabs(
        customTabs.map((tab) =>
          tab.id === activeCustomTab.id ? { ...tab, filters: cleared } : tab,
        ),
      );
    } else {
      savePreferences.mutate(
        preferencePayload({
          workspace_state: {
            ...preferencePayload().workspace_state,
            tab_filters: {
              ...preferencePayload().workspace_state.tab_filters,
              [module]: cleared,
            },
          },
        }),
      );
    }
    setPage(0);
  };
  useEffect(() => {
    const connected = () => {
      setOnline(true);
      void queryClient.invalidateQueries({ queryKey: ["support-workspace"] });
    };
    const disconnected = () => setOnline(false);
    window.addEventListener("online", connected);
    window.addEventListener("offline", disconnected);
    return () => {
      window.removeEventListener("online", connected);
      window.removeEventListener("offline", disconnected);
    };
  }, [queryClient]);
  const menuStatusCode = menu ? statusFor(menu.ticket)?.code : undefined;
  const menuIsTerminal = ["RESOLVED", "CLOSED", "CANCELLED"].includes(
    menuStatusCode ?? "",
  );
  const menuCanHandover =
    ["ASSIGNED", "NEW", "TRIAGED"].includes(menuStatusCode ?? "") ||
    Boolean(menuStatusCode?.startsWith("PENDING_"));
  const menuCanEscalate =
    menuStatusCode === "IN_PROGRESS" ||
    Boolean(menuStatusCode?.startsWith("PENDING_"));
  const menuIsPending = Boolean(menuStatusCode?.startsWith("PENDING_"));
  const openDefaultTabMenuFromKeyboard = (
    event: ReactKeyboardEvent<HTMLElement>,
    tab: Module,
  ) => {
    if (event.key !== "ContextMenu" && !(event.shiftKey && event.key === "F10"))
      return;
    event.preventDefault();
    setDefaultTabMenu({ anchor: event.currentTarget, tab });
  };

  return (
    <Stack
      spacing={compact ? 1 : 2}
      sx={{
        width: "100%",
        maxWidth: isIndependentWindow ? "none" : `${workspaceWidth}px`,
        mx: "auto",
        minHeight: "100%",
        p: compact ? 1 : { xs: 1, md: 2 },
        position: "relative",
        borderRadius: 4,
        background:
          "radial-gradient(circle at 8% 0%, rgba(25,118,210,.10), transparent 34%), radial-gradient(circle at 92% 8%, rgba(0,150,136,.08), transparent 28%)",
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        gap={1}
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 6,
          bgcolor: "background.default",
          py: 0.5,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant={compact ? "h6" : "h5"} fontWeight={900}>
            {t("supportWorkspace.title")}
          </Typography>
          {!compact && showSubtitle && (
            <Typography color="text.secondary">
              {t("supportWorkspace.subtitle")}
            </Typography>
          )}
        </Box>
        <Stack direction="row" sx={{ marginInlineStart: "auto" }}>
          <Tooltip title={t("supportWorkspace.aboutAssistant")}>
            <IconButton
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
              aria-label={t("supportWorkspace.aboutAssistant")}
              aria-expanded={showSubtitle}
              onClick={() => setShowSubtitle((value) => !value)}
            >
              <InfoOutlined />
            </IconButton>
          </Tooltip>
          <Tooltip title={t("supportWorkspace.openSupportHub")}>
            <IconButton
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
              aria-label={t("supportWorkspace.openSupportHub")}
              onClick={openSupportHub}
            >
              <SpaceDashboard />
            </IconButton>
          </Tooltip>
          <Tooltip title={t("supportWorkspace.refresh")}>
            <IconButton
              aria-label={t("supportWorkspace.refresh")}
              onClick={refresh}
            >
              <Refresh />
            </IconButton>
          </Tooltip>
          <Tooltip
            title={t("supportWorkspace.personalSettings", {
              defaultValue: "Personal Assistant settings",
            })}
          >
            <IconButton
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
              aria-label={t("supportWorkspace.personalSettings", {
                defaultValue: "Personal Assistant settings",
              })}
              onClick={openSettings}
            >
              <Settings />
            </IconButton>
          </Tooltip>
          <Tooltip
            title={
              compact
                ? t("supportWorkspace.expand")
                : t("supportWorkspace.compact")
            }
          >
            <IconButton
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
              aria-label={
                compact
                  ? t("supportWorkspace.expand")
                  : t("supportWorkspace.compact")
              }
              onClick={toggleCompact}
              disabled={settings?.allow_user_overrides === false}
            >
              {compact ? <UnfoldMore /> : <UnfoldLess />}
            </IconButton>
          </Tooltip>
          <Tooltip title={t("supportWorkspace.width")}>
            <IconButton
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
              aria-label={t("supportWorkspace.width")}
              aria-haspopup="menu"
              aria-expanded={Boolean(widthMenuAnchor)}
              onClick={(event) => setWidthMenuAnchor(event.currentTarget)}
              disabled={settings?.allow_user_overrides === false}
            >
              <WidthNormal />
            </IconButton>
          </Tooltip>
          <Tooltip title={t("supportWorkspace.openWindow")}>
            <IconButton
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
              aria-label={t("supportWorkspace.openWindow")}
              onClick={openIndependent}
            >
              <Launch />
            </IconButton>
          </Tooltip>
          <IconButton
            sx={{ display: { xs: "inline-flex", sm: "none" } }}
            aria-label={t("supportWorkspace.moreActions", {
              defaultValue: "More actions",
            })}
            onClick={(event) => setHeaderMenuAnchor(event.currentTarget)}
          >
            <MoreVert />
          </IconButton>
        </Stack>
      </Stack>
      {!!activeMajorIncidents.data?.length && (
        <Alert
          severity="error"
          icon={<WarningAmber />}
          sx={{ border: 1, borderColor: "error.main" }}
        >
          <Typography fontWeight={900}>
            {t("serviceManagement.activeMajorIncidents")}
          </Typography>
          <Stack
            direction={{ xs: "column", md: "row" }}
            gap={1}
            mt={0.5}
            flexWrap="wrap"
          >
            {activeMajorIncidents.data.map((incident) => (
              <Button
                key={incident.id}
                color="error"
                variant="outlined"
                size="small"
                onClick={() => navigate(`/major-incidents/${incident.id}`)}
              >
                <TechnicalText>{incident.major_incident_number}</TechnicalText>
                &nbsp;· {incident.severity} ·{" "}
                {incident.client_name || incident.subject} ·{" "}
                {incident.status.replaceAll("_", " ")}
              </Button>
            ))}
          </Stack>
        </Alert>
      )}
      <Menu
        anchorEl={headerMenuAnchor}
        open={Boolean(headerMenuAnchor)}
        onClose={() => setHeaderMenuAnchor(null)}
      >
        <MenuItem
          onClick={() => {
            setShowSubtitle((value) => !value);
            setHeaderMenuAnchor(null);
          }}
        >
          {t("supportWorkspace.aboutAssistant")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            openSupportHub();
            setHeaderMenuAnchor(null);
          }}
        >
          {t("supportWorkspace.openSupportHub")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            openSettings();
            setHeaderMenuAnchor(null);
          }}
        >
          {t("supportWorkspace.personalSettings", {
            defaultValue: "Personal Assistant settings",
          })}
        </MenuItem>
        <MenuItem
          disabled={settings?.allow_user_overrides === false}
          onClick={() => {
            toggleCompact();
            setHeaderMenuAnchor(null);
          }}
        >
          {compact
            ? t("supportWorkspace.expand")
            : t("supportWorkspace.compact")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            openIndependent();
            setHeaderMenuAnchor(null);
          }}
        >
          {t("supportWorkspace.openWindow")}
        </MenuItem>
      </Menu>
      <Menu
        anchorEl={widthMenuAnchor}
        open={Boolean(widthMenuAnchor)}
        onClose={() => setWidthMenuAnchor(null)}
      >
        {[
          ["compactWidth", COMPACT_WIDTH, true],
          ["standardWidth", STANDARD_WIDTH, false],
          ["wideWidth", WIDE_WIDTH, false],
        ].map(([label, width, isCompact]) => (
          <MenuItem
            key={String(label)}
            selected={workspaceWidth === width}
            onClick={() => {
              setAssistantWidth(Number(width), Boolean(isCompact));
              setWidthMenuAnchor(null);
            }}
          >
            {t(`supportWorkspace.${label}`, { width })}
          </MenuItem>
        ))}
      </Menu>
      <Menu
        anchorEl={defaultTabMenu?.anchor}
        open={Boolean(defaultTabMenu)}
        onClose={() => setDefaultTabMenu(null)}
      >
        <MenuItem
          onClick={() => defaultTabMenu && setDefaultTab(defaultTabMenu.tab)}
        >
          {t("supportWorkspace.setDefaultTab", {
            defaultValue: "Set as default tab",
          })}
        </MenuItem>
        {hasPermission("ticket.copy") && (
          <MenuItem
            onClick={() => {
              if (menu)
                navigate(`/tickets/create?copy_from=${menu.ticket.id}`, {
                  state: {
                    returnTo: `/support-workspace?tab=${module}`,
                  },
                });
              setMenu(null);
            }}
          >
            {t("supportWorkspace.copyToNewTicket", {
              defaultValue: "Copy to new ticket",
            })}
          </MenuItem>
        )}
      </Menu>
      <Menu
        anchorEl={personalTabMenu?.anchor}
        open={Boolean(personalTabMenu)}
        onClose={() => setPersonalTabMenu(null)}
      >
        <MenuItem
          onClick={() =>
            personalTabMenu && setDefaultTab(`custom:${personalTabMenu.tab.id}`)
          }
        >
          {t("supportWorkspace.setDefaultTab")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (!personalTabMenu) return;
            openSettings();
            setSettingsSection(3);
            setPersonalTabMenu(null);
          }}
        >
          {t("common.actions.edit")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (!personalTabMenu) return;
            const source = personalTabMenu.tab;
            saveCustomTabs([
              ...customTabs,
              {
                ...source,
                id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
                name: `${source.name} Copy`.slice(0, 30),
              },
            ]);
            setPersonalTabMenu(null);
          }}
        >
          {t("supportWorkspace.duplicate", { defaultValue: "Duplicate" })}
        </MenuItem>
        <MenuItem
          disabled={
            !personalTabMenu ||
            customTabs.findIndex((tab) => tab.id === personalTabMenu.tab.id) ===
              0
          }
          onClick={() =>
            personalTabMenu && moveCustomTab(personalTabMenu.tab.id, -1)
          }
        >
          {t("supportWorkspace.moveLeft", { defaultValue: "Move left" })}
        </MenuItem>
        <MenuItem
          disabled={
            !personalTabMenu ||
            customTabs.findIndex((tab) => tab.id === personalTabMenu.tab.id) ===
              customTabs.length - 1
          }
          onClick={() =>
            personalTabMenu && moveCustomTab(personalTabMenu.tab.id, 1)
          }
        >
          {t("supportWorkspace.moveRight", { defaultValue: "Move right" })}
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (!personalTabMenu) return;
            const id = personalTabMenu.tab.id;
            saveCustomTabs(customTabs.filter((tab) => tab.id !== id));
            if (activeCustomTabId === id) setActiveCustomTabId(null);
            setPersonalTabMenu(null);
          }}
          sx={{ color: "error.main" }}
        >
          {t("common.actions.delete")}
        </MenuItem>
      </Menu>
      <Dialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {t("supportWorkspace.personalSettings", {
            defaultValue: "Personal Assistant settings",
          })}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Tabs
              value={settingsSection}
              onChange={(_, value: number) => setSettingsSection(value)}
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
            >
              <Tab
                label={t("supportWorkspace.appearance", {
                  defaultValue: "Appearance",
                })}
              />
              <Tab
                label={t("supportWorkspace.ticketCards", {
                  defaultValue: "Ticket cards",
                })}
              />
              <Tab
                label={t("supportWorkspace.builtInTabs", {
                  defaultValue: "Built-in tabs",
                })}
              />
              <Tab
                label={t("supportWorkspace.personalTabs", {
                  defaultValue: "Personal tabs",
                })}
              />
            </Tabs>
            {settingsSection === 0 && (
              <>
                <Typography fontWeight={800}>
                  {t("supportWorkspace.workspaceLayout", {
                    defaultValue: "Workspace layout",
                  })}
                </Typography>
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  value={draftDensity}
                  onChange={(_, value: WorkspaceState["density"] | null) =>
                    value && setDraftDensity(value)
                  }
                  aria-label={t("supportWorkspace.density", {
                    defaultValue: "Display density",
                  })}
                >
                  <ToggleButton value="comfortable">
                    {t("supportWorkspace.comfortable", {
                      defaultValue: "Comfortable",
                    })}
                  </ToggleButton>
                  <ToggleButton value="compact">
                    {t("supportWorkspace.compactDensity", {
                      defaultValue: "Compact",
                    })}
                  </ToggleButton>
                  <ToggleButton value="dense">
                    {t("supportWorkspace.dense", { defaultValue: "Dense" })}
                  </ToggleButton>
                </ToggleButtonGroup>
                <TextField
                  size="small"
                  type="number"
                  label={t("supportWorkspace.personalPageSize", {
                    defaultValue: "Tickets per page",
                  })}
                  value={draftPageSize}
                  onChange={(event) =>
                    setDraftPageSize(
                      Math.min(50, Math.max(6, Number(event.target.value))),
                    )
                  }
                  inputProps={{ min: 6, max: 50 }}
                />
              </>
            )}
            {settingsSection === 1 && (
              <>
                <Typography fontWeight={700}>
                  {t("supportWorkspace.hiddenFields", {
                    defaultValue: "Hide ticket-card fields",
                  })}
                </Typography>
                <Stack direction="row" flexWrap="wrap">
                  {CARD_FIELDS.map((field) => (
                    <FormControlLabel
                      key={field}
                      control={
                        <Checkbox
                          checked={draftHiddenFields.includes(field)}
                          onChange={(_, checked) =>
                            setDraftHiddenFields((current) =>
                              checked
                                ? [...current, field]
                                : current.filter((item) => item !== field),
                            )
                          }
                        />
                      }
                      label={t(`supportWorkspace.cardFields.${field}`, {
                        defaultValue: field,
                      })}
                    />
                  ))}
                </Stack>
              </>
            )}
            {settingsSection === 2 && (
              <>
                <Typography fontWeight={800}>
                  {t("supportWorkspace.savedTabBehavior", {
                    defaultValue: "Built-in tab sorting and filters",
                  })}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("supportWorkspace.savedTabBehaviorHelp", {
                    defaultValue:
                      "Choose the filters and ticket order applied whenever you open each built-in tab.",
                  })}
                </Typography>
                {MODULES.filter(
                  (tab) => tabAccess[tab] && tab !== "pre-tickets",
                ).map((tab) => {
                  const filter = draftFilters[tab] ?? EMPTY_FILTERS;
                  return (
                    <Paper
                      key={tab}
                      variant="outlined"
                      sx={{ p: 2, borderRadius: 2 }}
                    >
                      <Stack
                        direction="row"
                        alignItems="center"
                        justifyContent="space-between"
                        mb={1.5}
                      >
                        <Typography fontWeight={800}>
                          {t(
                            `supportWorkspace.${tab === "follow-up" ? "followUp" : tab === "sla-risk" ? "slaRisk" : tab}`,
                          )}
                        </Typography>
                        {(filter.search ||
                          filter.priority ||
                          filter.status_code) && (
                          <Chip
                            size="small"
                            color="primary"
                            variant="outlined"
                            label={t("supportWorkspace.filtersActive", {
                              defaultValue: "Filters active",
                            })}
                          />
                        )}
                      </Stack>
                      <Box
                        sx={{
                          display: "grid",
                          gridTemplateColumns: {
                            xs: "1fr",
                            md: "minmax(180px, 1fr) minmax(130px, .45fr)",
                          },
                          gap: 1.25,
                        }}
                      >
                        <TextField
                          size="small"
                          label={t("supportWorkspace.filterSearch", {
                            defaultValue: "Search",
                          })}
                          value={filter.search}
                          onChange={(event) =>
                            updateDraftFilter(tab, "search", event.target.value)
                          }
                          fullWidth
                        />
                        <TextField
                          size="small"
                          select
                          label={t("supportWorkspace.filterPriority", {
                            defaultValue: "Priority",
                          })}
                          value={filter.priority}
                          onChange={(event) =>
                            updateDraftFilter(
                              tab,
                              "priority",
                              event.target.value,
                            )
                          }
                        >
                          <MenuItem value="">
                            {t("common.all", { defaultValue: "All" })}
                          </MenuItem>
                          {["P1", "P2", "P3", "P4"].map((value) => (
                            <MenuItem key={value} value={value}>
                              {value}
                            </MenuItem>
                          ))}
                        </TextField>
                        {statusMultiSelect(filter.status_code, (value) =>
                          updateDraftFilter(tab, "status_code", value),
                        )}
                        <TextField
                          size="small"
                          select
                          label={t("supportWorkspace.sorting", {
                            defaultValue: "Sorting",
                          })}
                          value={
                            draftSorting[tab] ??
                            settings?.tab_sorting?.[tab] ??
                            DEFAULT_SORTING[tab]
                          }
                          onChange={(event) =>
                            setDraftSorting((current) => ({
                              ...current,
                              [tab]: event.target.value,
                            }))
                          }
                        >
                          {SORT_OPTIONS.map((value) => (
                            <MenuItem key={value} value={value}>
                              {t(
                                `supportAssistantSettings.sortOptions.${value}`,
                              )}
                            </MenuItem>
                          ))}
                        </TextField>
                      </Box>
                    </Paper>
                  );
                })}
                {tabAccess["pre-tickets"] && (
                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography fontWeight={700} mb={1}>
                      {t("supportWorkspace.preTickets")}
                    </Typography>
                    <TextField
                      size="small"
                      select
                      label={t("supportWorkspace.sorting")}
                      value={
                        draftSorting["pre-tickets"] ??
                        settings?.tab_sorting?.["pre-tickets"] ??
                        DEFAULT_SORTING["pre-tickets"]
                      }
                      onChange={(event) =>
                        setDraftSorting((current) => ({
                          ...current,
                          "pre-tickets": event.target.value,
                        }))
                      }
                      sx={{ minWidth: 240 }}
                    >
                      {SORT_OPTIONS.filter((value) =>
                        value.startsWith("submitted_at"),
                      ).map((value) => (
                        <MenuItem key={value} value={value}>
                          {t(`supportAssistantSettings.sortOptions.${value}`)}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Paper>
                )}
              </>
            )}
            {settingsSection === 3 && (
              <>
                <Typography fontWeight={800}>
                  {t("supportWorkspace.customTabs", {
                    defaultValue: "Custom personal tabs",
                  })}
                </Typography>
                <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                  <TextField
                    size="small"
                    label={t("supportWorkspace.customTabName", {
                      defaultValue: "Tab name",
                    })}
                    value={newTabName}
                    onChange={(event) => setNewTabName(event.target.value)}
                    fullWidth
                  />
                  <TextField
                    size="small"
                    select
                    label={t("supportWorkspace.sourceTab", {
                      defaultValue: "Source tab",
                    })}
                    value={newTabSource}
                    onChange={(event) =>
                      setNewTabSource(
                        event.target.value as Exclude<Module, "pre-tickets">,
                      )
                    }
                    sx={{ minWidth: 170 }}
                  >
                    {MODULES.filter(
                      (tab): tab is Exclude<Module, "pre-tickets"> =>
                        tab !== "pre-tickets" && tabAccess[tab],
                    ).map((tab) => (
                      <MenuItem key={tab} value={tab}>
                        {t(
                          `supportWorkspace.${tab === "follow-up" ? "followUp" : tab === "sla-risk" ? "slaRisk" : tab}`,
                        )}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Button
                    startIcon={<Add />}
                    variant="outlined"
                    onClick={addCustomTab}
                    disabled={
                      newTabName.trim().length < 2 ||
                      draftCustomTabs.length >= 12
                    }
                  >
                    {t("common.add", { defaultValue: "Add" })}
                  </Button>
                </Stack>
                {draftCustomTabs.map((tab, index) => (
                  <Paper key={tab.id} variant="outlined" sx={{ p: 1.5 }}>
                    <Stack direction="row" alignItems="center" gap={1}>
                      <TextField
                        size="small"
                        value={tab.name}
                        onChange={(event) =>
                          setDraftCustomTabs((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, name: event.target.value }
                                : item,
                            ),
                          )
                        }
                        inputProps={{
                          "aria-label": t("supportWorkspace.customTabName"),
                        }}
                        sx={{ flexGrow: 1 }}
                      />
                      <Button
                        color="error"
                        size="small"
                        onClick={() =>
                          setDraftCustomTabs((current) =>
                            current.filter((item) => item.id !== tab.id),
                          )
                        }
                      >
                        {t("common.actions.delete")}
                      </Button>
                    </Stack>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      gap={1}
                      mt={1}
                    >
                      <TextField
                        size="small"
                        select
                        label={t("supportWorkspace.sourceTab")}
                        value={tab.source_module}
                        onChange={(event) =>
                          setDraftCustomTabs((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? {
                                    ...item,
                                    source_module: event.target
                                      .value as Exclude<Module, "pre-tickets">,
                                  }
                                : item,
                            ),
                          )
                        }
                        sx={{ minWidth: 150 }}
                      >
                        {MODULES.filter(
                          (value): value is Exclude<Module, "pre-tickets"> =>
                            value !== "pre-tickets" && tabAccess[value],
                        ).map((value) => (
                          <MenuItem key={value} value={value}>
                            {t(
                              `supportWorkspace.${value === "follow-up" ? "followUp" : value === "sla-risk" ? "slaRisk" : value}`,
                            )}
                          </MenuItem>
                        ))}
                      </TextField>
                      <TextField
                        size="small"
                        label={t("supportWorkspace.filterSearch", {
                          defaultValue: "Search",
                        })}
                        value={tab.filters.search}
                        onChange={(event) =>
                          setDraftCustomTabs((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? {
                                    ...item,
                                    filters: {
                                      ...item.filters,
                                      search: event.target.value,
                                    },
                                  }
                                : item,
                            ),
                          )
                        }
                        fullWidth
                      />
                      <TextField
                        size="small"
                        select
                        label={t("supportWorkspace.filterPriority", {
                          defaultValue: "Priority",
                        })}
                        value={tab.filters.priority}
                        onChange={(event) =>
                          setDraftCustomTabs((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? {
                                    ...item,
                                    filters: {
                                      ...item.filters,
                                      priority: event.target.value,
                                    },
                                  }
                                : item,
                            ),
                          )
                        }
                        sx={{ minWidth: 130 }}
                      >
                        <MenuItem value="">
                          {t("common.all", { defaultValue: "All" })}
                        </MenuItem>
                        {["P1", "P2", "P3", "P4"].map((value) => (
                          <MenuItem key={value} value={value}>
                            {value}
                          </MenuItem>
                        ))}
                      </TextField>
                      {statusMultiSelect(tab.filters.status_code, (value) =>
                        setDraftCustomTabs((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index
                              ? {
                                  ...item,
                                  filters: {
                                    ...item.filters,
                                    status_code: value,
                                  },
                                }
                              : item,
                          ),
                        ),
                      )}
                      <TextField
                        size="small"
                        select
                        label={t("supportWorkspace.sorting", {
                          defaultValue: "Sorting",
                        })}
                        value={tab.sorting}
                        onChange={(event) =>
                          setDraftCustomTabs((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, sorting: event.target.value }
                                : item,
                            ),
                          )
                        }
                        sx={{ minWidth: 190 }}
                      >
                        {SORT_OPTIONS.filter(
                          (value) => !value.startsWith("submitted_at"),
                        ).map((value) => (
                          <MenuItem key={value} value={value}>
                            {t(`supportAssistantSettings.sortOptions.${value}`)}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Stack>
                  </Paper>
                ))}
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>
            {t("common.actions.cancel")}
          </Button>
          <Button
            variant="contained"
            onClick={saveWorkspaceSettings}
            disabled={
              savePreferences.isPending ||
              draftCustomTabs.some((tab) => tab.name.trim().length < 2)
            }
          >
            {t("common.actions.save")}
          </Button>
        </DialogActions>
      </Dialog>
      <Box
        component="button"
        type="button"
        aria-label={t("supportWorkspace.resize")}
        title={t("supportWorkspace.resizeHelp")}
        onPointerDown={startResize}
        onDoubleClick={() => setAssistantWidth(STANDARD_WIDTH)}
        sx={{
          position: "absolute",
          insetInlineEnd: -7,
          top: 76,
          bottom: 16,
          width: 14,
          display:
            settings?.allow_user_overrides === false
              ? "none"
              : { xs: "none", sm: "grid" },
          placeItems: "center",
          p: 0,
          border: 0,
          bgcolor: "transparent",
          color: "text.disabled",
          cursor: "ew-resize",
          zIndex: 4,
          touchAction: "none",
          "&::before": {
            content: '""',
            width: 4,
            height: 64,
            borderRadius: 99,
            bgcolor: "currentColor",
            boxShadow: "0 0 0 1px rgba(255,255,255,.65)",
            transition: "height .16s ease, color .16s ease",
          },
          "&:hover, &:focus-visible": {
            color: "primary.main",
            outline: "none",
            "&::before": { height: 92 },
          },
        }}
      >
        <DragIndicator sx={{ opacity: 0, width: 1, height: 1 }} />
      </Box>
      {!online && (
        <Alert severity="warning">{t("supportWorkspace.offline")}</Alert>
      )}
      <Paper
        variant="outlined"
        sx={{
          position: "sticky",
          top: 49,
          zIndex: 5,
          borderRadius: 3,
          overflow: "hidden",
          boxShadow: "0 12px 34px rgba(15,23,42,.08)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Tabs
          value={activeCustomTab ? `custom:${activeCustomTab.id}` : module}
          onChange={(_, value: string) => {
            if (value.startsWith("custom:")) {
              const custom = customTabs.find(
                (tab) => `custom:${tab.id}` === value,
              );
              if (custom) {
                setActiveCustomTabId(custom.id);
                setModule(custom.source_module);
              }
            } else {
              setActiveCustomTabId(null);
              setModule(value as Module);
            }
            setPage(0);
            setActionError("");
          }}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          sx={{
            minHeight: 40,
            "& .MuiTabs-scrollButtons": {
              width: 32,
              flexShrink: 0,
            },
            "& .MuiTabs-scroller": {
              overscrollBehaviorInline: "contain",
              touchAction: "pan-x",
            },
            "& .MuiTabs-flexContainer": { gap: 0 },
            "& .MuiTab-root": {
              minHeight: 40,
              minWidth: "auto",
              px: 1,
              py: 0.5,
              fontSize: "0.78rem",
            },
          }}
        >
          {tabAccess.queue && (
            <Tab
              value="queue"
              icon={<Inbox />}
              iconPosition="start"
              label={`${t("supportWorkspace.queue")} (${tabCounts.data?.queue ?? "…"})`}
              onClick={() => setQueueAttention(false)}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({
                  anchor: event.currentTarget,
                  tab: "queue",
                });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "queue")
              }
              sx={
                queueAttention
                  ? {
                      bgcolor: "warning.main",
                      color: "warning.contrastText",
                      borderRadius: 1.5,
                      "&.Mui-selected": { color: "warning.contrastText" },
                    }
                  : undefined
              }
            />
          )}
          {tabAccess.mine && (
            <Tab
              value="mine"
              icon={<ConfirmationNumber />}
              iconPosition="start"
              label={`${t("supportWorkspace.mine")} (${tabCounts.data?.mine ?? "…"})`}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({ anchor: event.currentTarget, tab: "mine" });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "mine")
              }
            />
          )}
          {tabAccess.resolved && (
            <Tab
              value="resolved"
              icon={<CheckCircle />}
              iconPosition="start"
              label={`${t("supportWorkspace.resolvedAwaitingClosure")} (${tabCounts.data?.resolved ?? "…"})`}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({
                  anchor: event.currentTarget,
                  tab: "resolved",
                });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "resolved")
              }
            />
          )}
          {tabAccess.backlog && (
            <Tab
              value="backlog"
              icon={<HourglassBottom />}
              iconPosition="start"
              label={`${t("supportWorkspace.backlog")} (${tabCounts.data?.backlog ?? "…"})`}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({
                  anchor: event.currentTarget,
                  tab: "backlog",
                });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "backlog")
              }
            />
          )}
          {tabAccess["follow-up"] && (
            <Tab
              value="follow-up"
              label={`${t("supportWorkspace.followUp")} (${tabCounts.data?.["follow-up"] ?? "…"})`}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({
                  anchor: event.currentTarget,
                  tab: "follow-up",
                });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "follow-up")
              }
            />
          )}
          {tabAccess["sla-risk"] && (
            <Tab
              value="sla-risk"
              icon={<WarningAmber />}
              iconPosition="start"
              label={`${t("supportWorkspace.slaRisk")} (${tabCounts.data?.["sla-risk"] ?? "…"})`}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({
                  anchor: event.currentTarget,
                  tab: "sla-risk",
                });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "sla-risk")
              }
            />
          )}
          {tabAccess["missing-resolution"] && (
            <Tab
              value="missing-resolution"
              icon={<Description />}
              iconPosition="start"
              label={`${t("supportWorkspace.missingResolution")} (${tabCounts.data?.["missing-resolution"] ?? "…"})`}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({
                  anchor: event.currentTarget,
                  tab: "missing-resolution",
                });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "missing-resolution")
              }
            />
          )}
          {tabAccess["pre-tickets"] && (
            <Tab
              value="pre-tickets"
              icon={<Description />}
              iconPosition="start"
              label={`${t("supportWorkspace.preTickets")} (${tabCounts.data?.["pre-tickets"] ?? "…"})`}
              onContextMenu={(event) => {
                event.preventDefault();
                setDefaultTabMenu({
                  anchor: event.currentTarget,
                  tab: "pre-tickets",
                });
              }}
              onKeyDown={(event) =>
                openDefaultTabMenuFromKeyboard(event, "pre-tickets")
              }
            />
          )}
          {tabAccess.ops && (
            <Tab value="ops" icon={<Work />} iconPosition="start" label="Ops" />
          )}
          {customTabs
            .filter((tab) => tabAccess[tab.source_module])
            .map((tab) => (
              <Tab
                key={tab.id}
                value={`custom:${tab.id}`}
                label={tab.name}
                draggable
                onDragStart={() => setDraggedCustomTabId(tab.id)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => reorderCustomTabs(tab.id)}
                onContextMenu={(event) => {
                  event.preventDefault();
                  setPersonalTabMenu({ anchor: event.currentTarget, tab });
                }}
                onKeyDown={(event) => {
                  if (
                    event.key === "ContextMenu" ||
                    (event.shiftKey && event.key === "F10")
                  ) {
                    event.preventDefault();
                    setPersonalTabMenu({ anchor: event.currentTarget, tab });
                  }
                }}
              />
            ))}
        </Tabs>
        {(activeFilters.search ||
          activeFilters.priority ||
          activeFilters.status_code) && (
          <Stack
            direction="row"
            gap={0.5}
            px={1}
            pb={1}
            flexWrap="wrap"
            alignItems="center"
          >
            {activeFilters.search && (
              <Chip
                size="small"
                label={`${t("supportWorkspace.filterSearch")}: ${activeFilters.search}`}
                onDelete={() => clearActiveFilter("search")}
              />
            )}
            {activeFilters.priority && (
              <Chip
                size="small"
                label={`${t("supportWorkspace.filterPriority")}: ${activeFilters.priority}`}
                onDelete={() => clearActiveFilter("priority")}
              />
            )}
            {activeFilters.status_code && (
              <Chip
                size="small"
                label={`${t("supportWorkspace.filterStatus")}: ${activeFilters.status_code}`}
                onDelete={() => clearActiveFilter("status_code")}
              />
            )}
            <Button size="small" onClick={() => clearActiveFilter()}>
              {t("supportWorkspace.clearFilters", {
                defaultValue: "Clear filters",
              })}
            </Button>
          </Stack>
        )}
      </Paper>
      {actionError && (
        <Alert severity="error" onClose={() => setActionError("")}>
          {actionError}
        </Alert>
      )}
      {module === "ops" && <OperationPanels personalOnly />}
      {module === "backlog" && (
        <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
          <TextField
            select
            size="small"
            label={t("supportWorkspace.period")}
            value={selectedBacklogPeriod}
            disabled={settings?.allow_user_overrides === false}
            onChange={(event) => {
              setBacklogPeriod(event.target.value as BacklogPeriod);
              setPage(0);
            }}
            sx={{ minWidth: 180 }}
          >
            {["TODAY", "THIS_WEEK", "LAST_WEEK", "THIS_MONTH", "CUSTOM"].map(
              (period) => (
                <MenuItem key={period} value={period}>
                  {t(`supportWorkspace.periods.${period}`)}
                </MenuItem>
              ),
            )}
          </TextField>
          {selectedBacklogPeriod === "CUSTOM" && (
            <>
              <TextField
                size="small"
                type="date"
                label={t("supportWorkspace.from")}
                value={backlogFrom}
                onChange={(event) => {
                  setBacklogFrom(event.target.value);
                  setPage(0);
                }}
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                size="small"
                type="date"
                label={t("supportWorkspace.to")}
                value={backlogTo}
                onChange={(event) => {
                  setBacklogTo(event.target.value);
                  setPage(0);
                }}
                InputLabelProps={{ shrink: true }}
              />
            </>
          )}
        </Stack>
      )}
      {active.isLoading && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" },
            gap: 1.5,
          }}
        >
          {Array.from({ length: Math.min(pageSize, 6) }, (_, index) => (
            <Paper key={index} variant="outlined" sx={{ p: 2 }}>
              <Skeleton width="35%" />
              <Skeleton height={32} />
              <Skeleton width="70%" />
              <Skeleton />
            </Paper>
          ))}
        </Box>
      )}
      {active.isError && (
        <Alert severity="error">{t("supportWorkspace.loadFailed")}</Alert>
      )}
      <Box
        sx={{
          display: "grid",
          overflowX: "visible",
          gridTemplateColumns: compact
            ? "1fr"
            : workspaceWidth < 720
              ? "1fr"
              : workspaceWidth < 1000
                ? { xs: "1fr", md: "repeat(2, 1fr)" }
                : {
                    xs: "1fr",
                    md: "repeat(2, 1fr)",
                    xl: "repeat(3, 1fr)",
                  },
          gap:
            density === "dense"
              ? 0.5
              : compact || density === "compact"
                ? 1
                : 1.5,
        }}
      >
        {module !== "pre-tickets" &&
          displayedTickets.map((ticket) => {
            const status = statusFor(ticket),
              statusCode = status?.code,
              isMine = ticket.assigned_user_id === user?.id;
            const statusColor = status?.color || "#64748b";
            const canStart =
              canStartProgress &&
              ["ASSIGNED", "NEW", "TRIAGED"].includes(statusCode ?? "") &&
              (isMine || ticket.assigned_user_id == null);
            const canResolve =
              canChangeStatus &&
              hasPermission("ticket.resolve") &&
              isMine &&
              ["IN_PROGRESS", "PENDING_CLIENT"].includes(statusCode ?? "");
            const queueCard = module === "queue";
            const unreceivedWarning =
              queueCard &&
              isUnreceivedQueueTicket(
                ticket,
                clock,
                true,
                settings?.unreceived_warning_minutes,
              );
            const mineCard = module === "mine" || module === "resolved";
            const reopenedCard = statusCode === "REOPENED";
            const awaitingProgress = ["ASSIGNED", "NEW", "TRIAGED"].includes(
              statusCode ?? "",
            );
            const activeProgress = statusCode === "IN_PROGRESS";
            const pendingProgress = Boolean(statusCode?.startsWith("PENDING_"));
            const awaitingClosure = statusCode === "RESOLVED";
            const slaProgress =
              ticket.sla_resolution_target_minutes != null &&
              ticket.sla_resolution_target_minutes > 0 &&
              ticket.sla_actual_business_minutes != null
                ? ticket.sla_actual_business_minutes /
                  ticket.sla_resolution_target_minutes
                : 0;
            const slaBreached =
              (ticket.sla_overrun_minutes ?? 0) > 0 ||
              ticket.sla_resolution_state === "BREACHED";
            const slaNearBreach =
              !slaBreached &&
              ticket.sla_resolution_state === "RUNNING" &&
              slaProgress >= 0.5;
            const slaAlert = slaNearBreach || slaBreached;
            return (
              <Paper
                key={ticket.id}
                variant="outlined"
                tabIndex={0}
                draggable
                data-sla-alert={
                  slaNearBreach
                    ? "near-breach"
                    : slaBreached
                      ? "breached"
                      : undefined
                }
                data-queue-warning={unreceivedWarning ? "overdue" : undefined}
                data-reopened={reopenedCard ? "true" : undefined}
                aria-label={`${ticket.ticket_number} ${t("supportWorkspace.draggableCard")}`}
                onDragStart={(event) => {
                  setDraggedTicketId(ticket.id);
                  event.dataTransfer.effectAllowed = "move";
                  event.dataTransfer.setData("text/plain", String(ticket.id));
                }}
                onDragEnd={() => setDraggedTicketId(null)}
                onDragOver={(event) => {
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  reorderCards(ticket.id);
                }}
                onContextMenu={(event) => {
                  event.preventDefault();
                  setMenu({
                    position: { top: event.clientY, left: event.clientX },
                    ticket,
                  });
                }}
                onDoubleClick={() => openTicket(ticket.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") openTicket(ticket.id);
                  if (
                    event.key === "ContextMenu" ||
                    (event.shiftKey && event.key === "F10")
                  ) {
                    event.preventDefault();
                    const bounds = event.currentTarget.getBoundingClientRect();
                    setMenu({
                      position: {
                        top: bounds.top + 36,
                        left: bounds.left + 36,
                      },
                      ticket,
                    });
                  }
                }}
                sx={{
                  minWidth: 0,
                  p:
                    density === "dense"
                      ? 0.75
                      : compact || density === "compact"
                        ? 1.25
                        : 2,
                  position: "relative",
                  borderInlineStart: 5,
                  borderInlineStartColor: unreceivedWarning
                    ? "#f59e0b"
                    : reopenedCard
                      ? "#92400e"
                      : slaAlert
                        ? "#ef4444"
                        : statusColor,
                  borderRadius: 3,
                  overflow: "hidden",
                  cursor:
                    draggedTicketId === ticket.id ? "grabbing" : "pointer",
                  background: (theme) =>
                    theme.palette.mode === "dark"
                      ? "linear-gradient(145deg, rgba(30,41,59,.98), rgba(15,23,42,.94))"
                      : "linear-gradient(145deg, rgba(255,255,255,.98), rgba(248,250,252,.92))",
                  boxShadow: `-10px 0 24px -16px ${statusColor}, 0 10px 28px rgba(15,23,42,.10)`,
                  opacity: draggedTicketId === ticket.id ? 0.58 : 1,
                  transition:
                    "transform .18s ease, box-shadow .18s ease, opacity .18s ease",
                  ...(reopenedCard
                    ? {
                        borderColor: "#92400e",
                        animation:
                          "reopenedTicketFrame 1.25s ease-in-out infinite",
                        "@keyframes reopenedTicketFrame": {
                          "0%, 100%": {
                            boxShadow:
                              "0 10px 28px rgba(15,23,42,.10), 0 0 0 0 rgba(146,64,14,0)",
                          },
                          "50%": {
                            boxShadow:
                              "0 14px 34px rgba(15,23,42,.16), 0 0 24px rgba(146,64,14,.68)",
                          },
                        },
                        "@media (prefers-reduced-motion: reduce)": {
                          animation: "none",
                        },
                      }
                    : unreceivedWarning
                      ? {
                          borderColor: "#f59e0b",
                          animation:
                            settings?.overdue_card_animation_enabled === false
                              ? "none"
                              : "unreceivedQueueFrame 1.2s ease-in-out infinite",
                          "@keyframes unreceivedQueueFrame": {
                            "0%, 100%": {
                              borderColor: "rgba(245,158,11,.58)",
                              boxShadow:
                                "0 10px 28px rgba(15,23,42,.10), 0 0 0 0 rgba(245,158,11,0)",
                            },
                            "50%": {
                              borderColor: "#f59e0b",
                              boxShadow:
                                "0 14px 34px rgba(15,23,42,.15), 0 0 22px rgba(245,158,11,.62)",
                            },
                          },
                          "@media (prefers-reduced-motion: reduce)": {
                            animation: "none",
                            borderColor: "#f59e0b",
                          },
                        }
                      : slaAlert
                        ? {
                            borderColor: slaBreached
                              ? "rgba(220,38,38,.95)"
                              : "rgba(239,68,68,.68)",
                            animation: slaNearBreach
                              ? "slaAlertFrame 1.8s ease-in-out infinite"
                              : "none",
                            "@keyframes slaAlertFrame": {
                              "0%, 100%": {
                                borderColor: "rgba(239,68,68,.55)",
                                boxShadow:
                                  "0 10px 28px rgba(15,23,42,.10), 0 0 0 0 rgba(239,68,68,0)",
                              },
                              "50%": {
                                borderColor: "rgba(239,68,68,1)",
                                boxShadow:
                                  "0 14px 34px rgba(15,23,42,.15), 0 0 20px rgba(239,68,68,.48)",
                              },
                            },
                            "@media (prefers-reduced-motion: reduce)": {
                              animation: "none",
                              borderColor: "rgba(239,68,68,.95)",
                            },
                          }
                        : {}),
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    insetInlineStart: 0,
                    top: 0,
                    bottom: 0,
                    width: 4,
                    bgcolor: unreceivedWarning
                      ? "#f59e0b"
                      : reopenedCard
                        ? "#92400e"
                        : slaAlert
                          ? "#ef4444"
                          : statusColor,
                    boxShadow: `0 0 18px ${unreceivedWarning ? "#f59e0b" : reopenedCard ? "#92400e" : slaAlert ? "#ef4444" : statusColor}`,
                  },
                  "&:hover": {
                    transform: "translateY(-3px)",
                    boxShadow: `-12px 0 28px -15px ${statusColor}, 0 16px 38px rgba(15,23,42,.16)`,
                  },
                  "&:focus-visible": {
                    outline: "3px solid",
                    outlineColor: "primary.main",
                    outlineOffset: 2,
                  },
                }}
              >
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  gap={1}
                  alignItems="flex-start"
                  minWidth={0}
                >
                  <Typography fontWeight={900} sx={{ flex: 1, minWidth: 0 }}>
                    {ticket.ticket_number}
                  </Typography>
                  <Stack
                    direction="row"
                    gap={0.5}
                    alignItems="center"
                    flexWrap="wrap"
                    justifyContent="flex-end"
                  >
                    {(slaBreached ||
                      slaNearBreach ||
                      unreceivedWarning ||
                      ticket.priority === "P1") && (
                      <Chip
                        size="small"
                        variant="outlined"
                        color={
                          slaBreached || ticket.priority === "P1"
                            ? "error"
                            : "warning"
                        }
                        label={
                          slaBreached
                            ? t("supportWorkspace.slaBreached", {
                                defaultValue: "SLA breached",
                              })
                            : slaNearBreach
                              ? t("supportWorkspace.slaRiskLabel", {
                                  defaultValue: "SLA risk",
                                })
                              : unreceivedWarning
                                ? t("supportWorkspace.unreceivedOverdue", {
                                    defaultValue: "Unreceived",
                                  })
                                : "P1"
                        }
                      />
                    )}
                    {!hiddenCardFields.has("priority") && (
                      <Chip
                        size="small"
                        label={ticket.priority}
                        color={
                          ticket.priority === "P1"
                            ? "error"
                            : ticket.priority === "P2"
                              ? "warning"
                              : "default"
                        }
                      />
                    )}
                    {!hiddenCardFields.has("status") && (
                      <Chip
                        size="small"
                        label={
                          status
                            ? language === "ar" && status.name_ar
                              ? status.name_ar
                              : status.name
                            : t("supportWorkspace.unknownStatus")
                        }
                      />
                    )}
                    {awaitingClosure && (
                      <Chip
                        size="small"
                        color="warning"
                        variant="outlined"
                        label={t("supportWorkspace.closureDetailsRequired")}
                      />
                    )}
                    <IconButton
                      size="small"
                      aria-label={t("supportWorkspace.fastActions", {
                        defaultValue: "Ticket actions",
                      })}
                      onClick={(event) => {
                        event.stopPropagation();
                        const bounds =
                          event.currentTarget.getBoundingClientRect();
                        setMenu({
                          position: { top: bounds.bottom, left: bounds.left },
                          ticket,
                        });
                      }}
                    >
                      <MoreVert fontSize="small" />
                    </IconButton>
                  </Stack>
                </Stack>
                {!hiddenCardFields.has("client") && (
                  <Typography variant="caption" color="text.secondary">
                    {ticket.client_name || t("supportWorkspace.unknownClient")}
                  </Typography>
                )}
                {module === "resolved" && ticket.assigned_user_name && (
                  <Typography variant="caption" color="text.secondary">
                    {t("supportWorkspace.assignedEngineer", {
                      name: ticket.assigned_user_name,
                    })}
                  </Typography>
                )}
                <Typography
                  sx={{ my: density === "dense" ? 0.25 : compact ? 0.5 : 1 }}
                  fontWeight={700}
                >
                  {ticket.subject}
                </Typography>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  gap={1}
                  flexWrap="wrap"
                >
                  {!hiddenCardFields.has("sla") && (
                    <Typography
                      variant="caption"
                      color={
                        ticket.sla_overrun_minutes
                          ? "error.main"
                          : slaNearBreach
                            ? "warning.main"
                            : "text.secondary"
                      }
                    >
                      {slaText(ticket, t)}
                    </Typography>
                  )}
                  {!hiddenCardFields.has("created") && (
                    <Typography variant="caption" color="text.secondary">
                      {t("supportWorkspace.created", {
                        date: new Date(ticket.created_at).toLocaleString(),
                      })}
                    </Typography>
                  )}
                  {!hiddenCardFields.has("updated") && (
                    <Typography variant="caption" color="text.secondary">
                      {t("supportWorkspace.updated", {
                        date: new Date(ticket.updated_at).toLocaleString(),
                      })}
                    </Typography>
                  )}
                  {awaitingClosure && ticket.resolved_at && (
                    <Typography
                      variant="caption"
                      color="warning.main"
                      fontWeight={700}
                    >
                      {t("supportWorkspace.awaitingClosureSince", {
                        date: new Date(ticket.resolved_at).toLocaleString(),
                      })}
                    </Typography>
                  )}
                </Stack>
                <Stack direction="row" gap={0.5} mt={1.25} flexWrap="wrap">
                  {queueCard && canClaim && (
                    <Button
                      size="small"
                      startIcon={<PersonAdd />}
                      disabled={ticketAction.isPending}
                      onClick={() =>
                        ticketAction.mutate({ ticket, action: "claim" })
                      }
                    >
                      {t("supportWorkspace.assignToMe")}
                    </Button>
                  )}
                  {queueCard &&
                    canClaim &&
                    canStartProgress &&
                    ["ASSIGNED", "NEW", "TRIAGED"].includes(
                      statusCode ?? "",
                    ) && (
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<PlayArrow />}
                        disabled={ticketAction.isPending}
                        onClick={() =>
                          ticketAction.mutate({
                            ticket,
                            action: "claim-and-start",
                          })
                        }
                      >
                        {t("supportWorkspace.assignAndStart")}
                      </Button>
                    )}
                  {!queueCard && canStart && (
                    <Button
                      size="small"
                      startIcon={<PlayArrow />}
                      disabled={ticketAction.isPending}
                      onClick={() =>
                        ticketAction.mutate({ ticket, action: "start" })
                      }
                    >
                      {t("supportWorkspace.startProgress")}
                    </Button>
                  )}
                  {mineCard && pendingProgress && canStartProgress && (
                    <Button
                      size="small"
                      startIcon={<PlayArrow />}
                      disabled={ticketAction.isPending}
                      onClick={() =>
                        ticketAction.mutate({ ticket, action: "start" })
                      }
                    >
                      {t("supportWorkspace.returnInProgress", {
                        defaultValue: "Return to progress",
                      })}
                    </Button>
                  )}
                  {mineCard && canResolve && (
                    <Button
                      size="small"
                      color="success"
                      startIcon={<CheckCircle />}
                      onClick={() => openAction(ticket, "resolve")}
                    >
                      {t("supportWorkspace.resolve")}
                    </Button>
                  )}
                  {mineCard && awaitingClosure && canChangeStatus && (
                    <Button
                      size="small"
                      variant="contained"
                      color="success"
                      startIcon={<CheckCircle />}
                      onClick={() => openAction(ticket, "close")}
                    >
                      {t("supportWorkspace.closeTicket")}
                    </Button>
                  )}
                  {mineCard && activeProgress && canChangeStatus && (
                    <Button
                      size="small"
                      color="warning"
                      startIcon={<HourglassBottom />}
                      onClick={() => openAction(ticket, "pending")}
                    >
                      {t("supportWorkspace.pending")}
                    </Button>
                  )}
                  {mineCard &&
                    (activeProgress || pendingProgress) &&
                    (hasPermission("ticket.escalate") ||
                      hasPermission("ticket.help.request")) && (
                      <Button
                        size="small"
                        startIcon={<TrendingUp />}
                        onClick={() => openAction(ticket, "escalate")}
                      >
                        {t("supportWorkspace.escalateShort")}
                      </Button>
                    )}
                  {mineCard &&
                    (awaitingProgress || pendingProgress) &&
                    hasPermission("ticket.assign.team") && (
                      <Button
                        size="small"
                        startIcon={<SwapHoriz />}
                        onClick={() => openAction(ticket, "handover")}
                      >
                        {t("supportWorkspace.handoverShort")}
                      </Button>
                    )}
                  {!queueCard && !mineCard && (
                    <Button size="small" onClick={() => openTicket(ticket.id)}>
                      {t("supportWorkspace.openTicket")}
                    </Button>
                  )}
                </Stack>
              </Paper>
            );
          })}
        {module === "pre-tickets" &&
          preTicketQuery.data?.items.map((item) => (
            <Paper
              key={item.id}
              variant="outlined"
              sx={{
                p:
                  density === "dense"
                    ? 0.75
                    : compact || density === "compact"
                      ? 1.25
                      : 2,
              }}
            >
              <Stack direction="row" justifyContent="space-between" gap={1}>
                <Typography fontWeight={900}>
                  {item.pre_ticket_number}
                </Typography>
                <Chip size="small" label={item.status} />
              </Stack>
              <Typography sx={{ my: 1 }}>{item.title}</Typography>
              <Typography variant="caption" color="text.secondary">
                {item.proposed_priority} ·{" "}
                {new Date(item.submitted_at).toLocaleString()}
              </Typography>
              <Box mt={1.5}></Box>
            </Paper>
          ))}
      </Box>
      {!active.isLoading && !total && (
        <Paper variant="outlined" sx={{ p: 5, textAlign: "center" }}>
          <Typography color="text.secondary" mb={1.5}>
            {t("supportWorkspace.empty")}
          </Typography>
          <Stack direction="row" gap={1} justifyContent="center">
            {(activeFilters.search ||
              activeFilters.priority ||
              activeFilters.status_code) && (
              <Button
                size="small"
                variant="outlined"
                onClick={() => clearActiveFilter()}
              >
                {t("supportWorkspace.clearFilters", {
                  defaultValue: "Clear filters",
                })}
              </Button>
            )}
            {module !== "queue" && tabAccess.queue && (
              <Button
                size="small"
                onClick={() => {
                  setActiveCustomTabId(null);
                  setModule("queue");
                }}
              >
                {t("supportWorkspace.goToQueue", {
                  defaultValue: "Go to Queue",
                })}
              </Button>
            )}
          </Stack>
        </Paper>
      )}
      {total > 0 && (
        <Stack
          direction="row"
          justifyContent="flex-end"
          alignItems="center"
          gap={1}
        >
          <Button
            disabled={page === 0}
            onClick={() => setPage((value) => value - 1)}
          >
            {t("supportWorkspace.previous")}
          </Button>
          <Typography variant="body2">
            {t("supportWorkspace.page", { page: page + 1 })}
          </Typography>
          <Button
            disabled={(page + 1) * pageSize >= total}
            onClick={() => setPage((value) => value + 1)}
          >
            {t("supportWorkspace.next")}
          </Button>
        </Stack>
      )}
      <Drawer
        anchor={i18n.dir() === "rtl" ? "left" : "right"}
        open={Boolean(selectedTicket)}
        onClose={() => setSelectedTicket(null)}
        PaperProps={{ sx: { width: { xs: "100%", sm: 420 }, p: 2 } }}
      >
        {selectedTicket && (
          <Stack
            spacing={2}
            role="region"
            aria-label={t("supportWorkspace.ticketPreview", {
              defaultValue: "Ticket preview",
            })}
          >
            <Stack direction="row" alignItems="center" gap={1}>
              <Typography variant="h6" fontWeight={900} sx={{ flexGrow: 1 }}>
                {selectedTicket.ticket_number}
              </Typography>
              <Button size="small" onClick={() => setSelectedTicket(null)}>
                {t("common.close", { defaultValue: "Close" })}
              </Button>
            </Stack>
            <Typography variant="h6">{selectedTicket.subject}</Typography>
            <Stack direction="row" gap={1} flexWrap="wrap">
              <Chip
                label={selectedTicket.priority}
                color={selectedTicket.priority === "P1" ? "error" : "default"}
              />
              <Chip
                label={
                  statusFor(selectedTicket)?.name ??
                  t("supportWorkspace.unknownStatus")
                }
              />
            </Stack>
            {ticketPreview.isLoading ? (
              <Skeleton height={100} />
            ) : (
              <Paper variant="outlined" sx={{ p: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  {t("supportWorkspace.description", {
                    defaultValue: "Description",
                  })}
                </Typography>
                <Typography sx={{ whiteSpace: "pre-wrap" }}>
                  {ticketPreview.data?.description || "—"}
                </Typography>
              </Paper>
            )}
            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Typography variant="caption" color="text.secondary">
                {t("supportWorkspace.cardFields.client")}
              </Typography>
              <Typography>
                {selectedTicket.client_name ||
                  t("supportWorkspace.unknownClient")}
              </Typography>
            </Paper>
            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Typography>{slaText(selectedTicket, t)}</Typography>
              <Typography variant="caption" color="text.secondary">
                {t("supportWorkspace.updated", {
                  date: new Date(selectedTicket.updated_at).toLocaleString(),
                })}
              </Typography>
            </Paper>
            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Typography fontWeight={800}>
                {t("supportWorkspace.recentComments", {
                  defaultValue: "Recent comments",
                })}
              </Typography>
              {previewComments.isLoading ? (
                <Skeleton height={60} />
              ) : (
                previewComments.data
                  ?.slice(-3)
                  .reverse()
                  .map((comment) => (
                    <Box key={comment.id} sx={{ mt: 1 }}>
                      <Typography variant="body2">{comment.body}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {comment.is_internal
                          ? t("supportWorkspace.internal", {
                              defaultValue: "Internal",
                            })
                          : t("supportWorkspace.public", {
                              defaultValue: "Public",
                            })}{" "}
                        · {new Date(comment.created_at).toLocaleString()}
                      </Typography>
                    </Box>
                  ))
              )}
              {previewComments.data?.length === 0 && (
                <Typography color="text.secondary">—</Typography>
              )}
            </Paper>
            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Typography fontWeight={800}>
                {t("supportWorkspace.attachments", {
                  defaultValue: "Attachments",
                })}{" "}
                ({previewAttachments.data?.length ?? 0})
              </Typography>
              {previewAttachments.data?.slice(0, 4).map((attachment) => (
                <Typography key={attachment.id} variant="body2" noWrap>
                  {attachment.original_filename}
                </Typography>
              ))}
            </Paper>
            <Stack direction="row" gap={1} flexWrap="wrap">
              <Button
                variant="contained"
                onClick={() => openTicket(selectedTicket.id)}
              >
                {t("supportWorkspace.openTicket")}
              </Button>
              {module === "queue" && canClaim && (
                <Button
                  onClick={() =>
                    ticketAction.mutate({
                      ticket: selectedTicket,
                      action: "claim",
                    })
                  }
                >
                  {t("supportWorkspace.assignToMe")}
                </Button>
              )}
              {selectedTicket.assigned_user_id === user?.id &&
                canStartProgress &&
                ["ASSIGNED", "NEW", "TRIAGED"].includes(
                  statusFor(selectedTicket)?.code ?? "",
                ) && (
                  <Button
                    onClick={() =>
                      ticketAction.mutate({
                        ticket: selectedTicket,
                        action: "start",
                      })
                    }
                  >
                    {t("supportWorkspace.startProgress")}
                  </Button>
                )}
              {module === "mine" &&
                selectedTicket.assigned_user_id === user?.id &&
                canChangeStatus &&
                hasPermission("ticket.resolve") &&
                statusFor(selectedTicket)?.code === "IN_PROGRESS" && (
                  <Button
                    color="success"
                    onClick={() => openAction(selectedTicket, "resolve")}
                  >
                    {t("supportWorkspace.resolve")}
                  </Button>
                )}
            </Stack>
          </Stack>
        )}
      </Drawer>
      {mobile && selectedTicket && (
        <Paper
          elevation={8}
          sx={{
            position: "fixed",
            insetInline: 8,
            bottom: 8,
            zIndex: 1400,
            p: 1,
          }}
        >
          <Stack direction="row" gap={1} justifyContent="center">
            <Button
              size="small"
              variant="contained"
              onClick={() => openTicket(selectedTicket.id)}
            >
              {t("supportWorkspace.openTicket")}
            </Button>
            {module === "queue" && canClaim && (
              <Button
                size="small"
                onClick={() =>
                  ticketAction.mutate({
                    ticket: selectedTicket,
                    action: "claim",
                  })
                }
              >
                {t("supportWorkspace.assignToMe")}
              </Button>
            )}
            {selectedTicket.assigned_user_id === user?.id &&
              canStartProgress &&
              ["ASSIGNED", "NEW", "TRIAGED"].includes(
                statusFor(selectedTicket)?.code ?? "",
              ) && (
                <Button
                  size="small"
                  onClick={() =>
                    ticketAction.mutate({
                      ticket: selectedTicket,
                      action: "start",
                    })
                  }
                >
                  {t("supportWorkspace.startProgress")}
                </Button>
              )}
            {module === "mine" &&
              canChangeStatus &&
              hasPermission("ticket.resolve") &&
              statusFor(selectedTicket)?.code === "IN_PROGRESS" && (
                <Button
                  size="small"
                  color="success"
                  onClick={() => openAction(selectedTicket, "resolve")}
                >
                  {t("supportWorkspace.resolve")}
                </Button>
              )}
          </Stack>
        </Paper>
      )}
      <Menu
        anchorReference="anchorPosition"
        anchorPosition={menu?.position}
        open={Boolean(menu)}
        onClose={() => {
          setOtherActionsAnchor(null);
          setMenu(null);
        }}
        slotProps={{
          paper: {
            sx: {
              maxHeight: "min(70vh, 560px)",
              width: { xs: 280, sm: 500 },
              maxWidth: "calc(100vw - 24px)",
            },
          },
        }}
        MenuListProps={{
          sx: {
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
            p: 1,
            gap: 0.25,
            "& .MuiListSubheader-root, & .MuiDivider-root": {
              gridColumn: "1 / -1",
            },
            "& .MuiMenuItem-root": {
              borderRadius: 1,
              minHeight: 38,
              whiteSpace: "normal",
            },
          },
        }}
      >
        <MenuItem
          disabled={savePreferences.isPending}
          onClick={() => {
            if (menu) togglePin(menu.ticket.id);
            setMenu(null);
          }}
        >
          {menu && pinnedIds.includes(menu.ticket.id)
            ? t("supportWorkspace.unpin")
            : t("supportWorkspace.pin")}
        </MenuItem>
        <Divider />
        <ListSubheader
          disableSticky
          sx={{ lineHeight: "30px", fontWeight: 800 }}
        >
          Common actions
        </ListSubheader>
        {hasPermission("ticket.copy") && (
          <MenuItem
            onClick={() => {
              const id = menu?.ticket.id;
              setMenu(null);
              if (id)
                navigate(`/tickets/create?copy_from=${id}`, {
                  state: { returnTo: `/support-workspace?tab=${module}` },
                });
            }}
          >
            Copy to new ticket
          </MenuItem>
        )}
        {hasPermission("ticket.mention") && (
          <MenuItem onClick={() => menu && openAction(menu.ticket, "mention")}>
            @ Mention users
          </MenuItem>
        )}
        <MenuItem onClick={() => menu && void openWhatsApp(menu.ticket)}>
          Open WhatsApp
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menu) openTicket(menu.ticket.id);
            setMenu(null);
          }}
        >
          {t("supportWorkspace.openTicket")}
        </MenuItem>
        {hasPermission("ticket.assign.team") && (
          <MenuItem onClick={() => menu && openAction(menu.ticket, "assign")}>
            Reassign ticket
          </MenuItem>
        )}
        {hasPermission("ticket.flag.apply") && (
          <MenuItem
            onClick={() => {
              const id = menu?.ticket.id;
              setMenu(null);
              if (id) navigate(`/tickets/${id}?action=flag`);
            }}
          >
            Add ticket flag
          </MenuItem>
        )}
        <Divider />
        <MenuItem
          aria-haspopup="menu"
          aria-expanded={Boolean(otherActionsAnchor)}
          onMouseEnter={(event) => setOtherActionsAnchor(event.currentTarget)}
          onClick={(event) => setOtherActionsAnchor(event.currentTarget)}
        >
          <Box component="span" sx={{ flexGrow: 1 }}>
            Other actions
          </Box>
          <ArrowForwardIos sx={{ fontSize: 14, ml: 2 }} />
        </MenuItem>
        {legacyContextActionsVisible() && (
          <>
            <ListSubheader
              disableSticky
              sx={{ lineHeight: "30px", fontWeight: 800 }}
            >
              Personal &amp; view
            </ListSubheader>
            <MenuItem
              disabled={savePreferences.isPending}
              onClick={() => {
                if (menu) togglePin(menu.ticket.id);
                setMenu(null);
              }}
            >
              {t("supportWorkspace.pin")}
            </MenuItem>
            <Divider />
            <ListSubheader
              disableSticky
              sx={{ lineHeight: "30px", fontWeight: 800 }}
            >
              Workflow
            </ListSubheader>
            {hasPermission("ticket.copy") && (
              <MenuItem
                onClick={() => {
                  const id = menu?.ticket.id;
                  setMenu(null);
                  if (id) navigate(`/tickets/create?copy_from=${id}`);
                }}
              >
                Copy to new ticket
              </MenuItem>
            )}
            <MenuItem
              onClick={() => menu && openAction(menu.ticket, "history")}
            >
              View history
            </MenuItem>
            <MenuItem
              onClick={() => {
                if (menu) setSelectedTicket(menu.ticket);
                setMenu(null);
              }}
            >
              {t("supportWorkspace.previewTicket", {
                defaultValue: "Preview ticket",
              })}
            </MenuItem>
            {hasPermission("ticket.flag.apply") && (
              <MenuItem
                onClick={() => {
                  const id = menu?.ticket.id;
                  setMenu(null);
                  if (id) navigate(`/tickets/${id}?action=flag`);
                }}
              >
                Add ticket flag
              </MenuItem>
            )}
            {!menuIsTerminal && canChangeStatus && (
              <MenuItem
                onClick={() => menu && openAction(menu.ticket, "status")}
              >
                {t("supportWorkspace.changeStatus", {
                  defaultValue: "Change status",
                })}
              </MenuItem>
            )}
            {menuIsPending && canStartProgress && (
              <MenuItem
                onClick={() => {
                  if (menu)
                    ticketAction.mutate({
                      ticket: menu.ticket,
                      action: "start",
                    });
                  setMenu(null);
                }}
              >
                {t("supportWorkspace.returnInProgress", {
                  defaultValue: "Return to progress",
                })}
              </MenuItem>
            )}
            {menuStatusCode === "PENDING_CLIENT" &&
              canChangeStatus &&
              hasPermission("ticket.resolve") && (
                <MenuItem
                  onClick={() => menu && openAction(menu.ticket, "resolve")}
                >
                  {t("supportWorkspace.resolve")}
                </MenuItem>
              )}
            {hasPermission("ticket.comment.public") && (
              <ListSubheader
                disableSticky
                sx={{ lineHeight: "30px", fontWeight: 800 }}
              >
                Communication &amp; collaboration
              </ListSubheader>
            )}
            {hasPermission("ticket.comment.public") && (
              <MenuItem
                onClick={() =>
                  menu && openAction(menu.ticket, "comment-public")
                }
              >
                {t("supportWorkspace.publicComment")}
              </MenuItem>
            )}
            {hasPermission("ticket.comment.internal") && (
              <MenuItem
                onClick={() =>
                  menu && openAction(menu.ticket, "comment-internal")
                }
              >
                {t("supportWorkspace.internalComment")}
              </MenuItem>
            )}
            {hasPermission("ticket.change.status") && (
              <MenuItem onClick={() => menu && openAction(menu.ticket, "task")}>
                Add task
              </MenuItem>
            )}
            {hasPermission("ticket.change.status") && (
              <MenuItem
                onClick={() => menu && openAction(menu.ticket, "checklist")}
              >
                Add checklist item
              </MenuItem>
            )}
            {hasPermission("knowledge.view") && (
              <MenuItem
                onClick={() => menu && openAction(menu.ticket, "knowledge")}
              >
                Link knowledge
              </MenuItem>
            )}
            {hasPermission("ticket.assign.team") && (
              <MenuItem
                onClick={() => menu && openAction(menu.ticket, "assign")}
              >
                Reassign ticket
              </MenuItem>
            )}
            {user?.user_type === "EMPLOYEE" && (
              <MenuItem
                onClick={() => menu && openAction(menu.ticket, "worklog")}
              >
                Log work
              </MenuItem>
            )}
            {!menuIsTerminal &&
              menuCanHandover &&
              hasPermission("ticket.assign.team") && (
                <MenuItem
                  onClick={() => menu && openAction(menu.ticket, "handover")}
                >
                  {t("supportWorkspace.handover")}
                </MenuItem>
              )}
            {!menuIsTerminal &&
              menuCanEscalate &&
              (hasPermission("ticket.escalate") ||
                hasPermission("ticket.help.request")) && (
                <MenuItem
                  onClick={() => menu && openAction(menu.ticket, "escalate")}
                >
                  {t("supportWorkspace.escalate")}
                </MenuItem>
              )}
            {hasPermission("ticket.relate") && (
              <MenuItem onClick={() => menu && openAction(menu.ticket, "link")}>
                {t("supportWorkspace.linkTicket")}
              </MenuItem>
            )}
            {hasPermission("ticket.template.create") && (
              <MenuItem
                onClick={() => menu && openAction(menu.ticket, "template")}
              >
                {t("ticketDetail.createAsTemplate", {
                  defaultValue: "Create as ticket template",
                })}
              </MenuItem>
            )}
            {hasPermission("ticket.mention") && (
              <MenuItem
                onClick={() => menu && openAction(menu.ticket, "mention")}
              >
                @ Mention users
              </MenuItem>
            )}
            {hasPermission("support_assistant.follow_up.view") && (
              <MenuItem
                onClick={() => {
                  if (menu) followUpAction.mutate(menu.ticket);
                  setMenu(null);
                }}
              >
                {menu?.ticket.support_follow_up_flag
                  ? t("supportWorkspace.clearFollowUp")
                  : t("supportWorkspace.markFollowUp")}
              </MenuItem>
            )}
            {[
              "ticket.live_update.send",
              "ticket.satisfaction.send",
              "complaint.tracking.send",
            ].some(hasPermission) && (
              <MenuItem
                onClick={() => {
                  setSendTicketId(menu?.ticket.id ?? null);
                  setMenu(null);
                }}
              >
                {t("supportWorkspace.sendLinks")}
              </MenuItem>
            )}
            <Divider />
            <ListSubheader
              disableSticky
              sx={{ lineHeight: "30px", fontWeight: 800 }}
            >
              Ticket
            </ListSubheader>
            <MenuItem onClick={() => menu && void openWhatsApp(menu.ticket)}>
              Open WhatsApp
            </MenuItem>
            <MenuItem
              onClick={() => {
                if (menu) openTicket(menu.ticket.id);
                setMenu(null);
              }}
            >
              {t("supportWorkspace.openTicket")}
            </MenuItem>
          </>
        )}
      </Menu>
      <Menu
        anchorEl={otherActionsAnchor}
        open={Boolean(menu && otherActionsAnchor)}
        onClose={() => setOtherActionsAnchor(null)}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
        MenuListProps={{ onMouseLeave: () => setOtherActionsAnchor(null) }}
      >
        <MenuItem onClick={() => menu && openAction(menu.ticket, "history")}>
          View status history
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (menu) setSelectedTicket(menu.ticket);
            setMenu(null);
          }}
        >
          {t("supportWorkspace.previewTicket", {
            defaultValue: "Preview ticket",
          })}
        </MenuItem>
        {!menuIsTerminal && canChangeStatus && (
          <MenuItem onClick={() => menu && openAction(menu.ticket, "status")}>
            Change status
          </MenuItem>
        )}
        {menuIsPending && canStartProgress && (
          <MenuItem
            onClick={() => {
              if (menu)
                ticketAction.mutate({ ticket: menu.ticket, action: "start" });
              setMenu(null);
            }}
          >
            Return to progress
          </MenuItem>
        )}
        {hasPermission("ticket.comment.public") && (
          <MenuItem
            onClick={() => menu && openAction(menu.ticket, "comment-public")}
          >
            Public comment
          </MenuItem>
        )}
        {hasPermission("ticket.comment.internal") && (
          <MenuItem
            onClick={() => menu && openAction(menu.ticket, "comment-internal")}
          >
            Internal comment
          </MenuItem>
        )}
        {hasPermission("ticket.change.status") && (
          <MenuItem onClick={() => menu && openAction(menu.ticket, "task")}>
            Add task
          </MenuItem>
        )}
        {user?.user_type === "EMPLOYEE" && (
          <MenuItem onClick={() => menu && openAction(menu.ticket, "worklog")}>
            Log work
          </MenuItem>
        )}
        {!menuIsTerminal &&
          menuCanHandover &&
          hasPermission("ticket.assign.team") && (
            <MenuItem
              onClick={() => menu && openAction(menu.ticket, "handover")}
            >
              Hand over
            </MenuItem>
          )}
        {!menuIsTerminal &&
          menuCanEscalate &&
          (hasPermission("ticket.escalate") ||
            hasPermission("ticket.help.request")) && (
            <MenuItem
              onClick={() => menu && openAction(menu.ticket, "escalate")}
            >
              Escalate / request help
            </MenuItem>
          )}
        {hasPermission("ticket.relate") && (
          <MenuItem onClick={() => menu && openAction(menu.ticket, "link")}>
            Link ticket
          </MenuItem>
        )}
        {[
          "ticket.live_update.send",
          "ticket.satisfaction.send",
          "complaint.tracking.send",
        ].some(hasPermission) && (
          <MenuItem
            onClick={() => {
              setSendTicketId(menu?.ticket.id ?? null);
              setMenu(null);
            }}
          >
            {t("supportWorkspace.sendLinks")}
          </MenuItem>
        )}
      </Menu>
      <TicketSendActionsDialog
        ticketId={sendTicketId}
        open={sendTicketId !== null}
        onClose={() => setSendTicketId(null)}
      />
    </Stack>
  );
}
