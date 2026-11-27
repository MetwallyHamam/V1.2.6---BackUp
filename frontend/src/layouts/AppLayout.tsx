import {
  AccountTree,
  Assessment,
  AssignmentTurnedIn,
  AccountBalance,
  ArrowDropDown,
  Business,
  ChevronRight,
  Insights,
  Language,
  ConfirmationNumber,
  FactCheck,
  Dashboard,
  Description,
  Dns,
  ExpandMore,
  Group,
  MenuBook,
  ManageSearch,
  Menu as MenuIcon,
  Notifications,
  Newspaper,
  Person,
  ReportProblem,
  Security,
  Storage,
  SettingsBackupRestore,
  SettingsSuggest,
  UploadFile,
  Warning,
  WorkHistory,
  Widgets,
} from "@mui/icons-material";
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  Collapse,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControl,
  FormControlLabel,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  InputLabel,
  Menu,
  MenuItem,
  Paper,
  Switch,
  Select,
  Stack,
  Toolbar,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ReactNode, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Link as RouterLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { authorizedWorkspaces, deliveryWorkspaceLanding, implementationWorkspacePath, implementationWorkspacePermission, isAllowedDeliveryRoute, projectMyWorkPath, projectWorkspacePath, projectWorkspacePermission, rememberWorkspace } from "../auth/projectWorkspaceAccess";
import type { ThemePreset } from "../auth/AuthContext";
import { api } from "../api/client";
import {
  playNotificationSound,
  unlockNotificationSound,
} from "../utils/notificationSound";
import { supportedLanguages, type SupportedLanguage } from "../i18n/config";
import { PageContextHeader } from "../components/PageContextHeader";
import { QuickActions } from "../components/QuickActions";
import { NewsAnnouncementDialog } from "../components/NewsAnnouncementDialog";
import { useAttention } from "../components/AttentionCenter";

const drawerWidth = 272;
const collapsedDrawerWidth = 72;
const secondaryDrawerWidth = 248;

type NavigationItem = {
  label: string;
  path: string;
  icon: ReactNode;
  color: string;
  visible: boolean;
};

type NavigationSection = {
  label: string;
  items: NavigationItem[];
};

type MentionNotification = {
  id: number;
  title: string;
  message: string;
  deep_link?: string;
  created_at: string;
};

export function AppLayout() {
  return <SupportHubLayout />;
}

function SupportHubLayout() {
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const {
    hasPermission,
    logout,
    updateLanguage,
    updateProfilePreferences,
    uploadProfilePicture,
    user,
  } = useAuth();
  const { i18n, t } = useTranslation();
  const deliveryLanding = deliveryWorkspaceLanding(user?.user_type, hasPermission);
  const workspaces = user?.user_type === "EMPLOYEE" ? authorizedWorkspaces(hasPermission) : [];
  const projectOnly = Boolean(deliveryLanding);
  const [profileAnchor, setProfileAnchor] = useState<HTMLElement | null>(null);
  const [navigationMenuAnchor, setNavigationMenuAnchor] =
    useState<HTMLElement | null>(null);
  const [navigationMenuSection, setNavigationMenuSection] = useState<
    string | null
  >(null);
  const [reportsAnchor, setReportsAnchor] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!navigationMenuAnchor) return;

    const closeNavigationMenuOnClickAway = (event: PointerEvent) => {
      const target = event.target as Element | null;
      if (
        target?.closest(
          "[data-header-navigation-trigger], #header-navigation-menu",
        )
      ) {
        return;
      }
      setNavigationMenuAnchor(null);
      setNavigationMenuSection(null);
    };

    document.addEventListener("pointerdown", closeNavigationMenuOnClickAway);
    return () =>
      document.removeEventListener("pointerdown", closeNavigationMenuOnClickAway);
  }, [navigationMenuAnchor]);
  const [languageAnchor, setLanguageAnchor] = useState<HTMLElement | null>(
    null,
  );
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [defaultPage, setDefaultPage] = useState("home");
  const [dashboardScope, setDashboardScope] = useState<"GENERAL" | "MY">(
    "GENERAL",
  );
  const [defaultSavedViewId, setDefaultSavedViewId] = useState("");
  const [themeMode, setThemeMode] = useState<"LIGHT" | "DARK" | "SYSTEM">(
    "SYSTEM",
  );
  const [themePreset, setThemePreset] = useState<ThemePreset>("CLASSIC");
  const [profilePictureUrl, setProfilePictureUrl] = useState("");
  const changeLanguage = useMutation({
    mutationFn: async (language: SupportedLanguage) => {
      const previous = i18n.resolvedLanguage === "ar" ? "ar" : "en";
      await i18n.changeLanguage(language);
      try {
        await updateLanguage(language);
      } catch (error) {
        await i18n.changeLanguage(previous);
        throw error;
      }
    },
    onSettled: () => setLanguageAnchor(null),
  });
  const [navigationCollapsed, setNavigationCollapsed] = useState(
    () =>
      window.localStorage.getItem("support-hub-navigation-collapsed") ===
      "true",
  );
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const [expandedNavigationSections, setExpandedNavigationSections] = useState<
    Set<string>
  >(() => new Set());
  const [navigationSearch, setNavigationSearch] = useState("");
  const [savedViewNavigationSearch, setSavedViewNavigationSearch] =
    useState("");
  const [showAllSavedViews, setShowAllSavedViews] = useState(false);
  const initializedNavigationUserRef = useRef<number | null>(null);
  const compactNavigation = !mobile && navigationCollapsed;
  const previousUnread = useRef<number | null>(null);
  const previousLatestNotificationId = useRef<number | null>(null);
  const preferences = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: async () =>
      (
        await api.get<{
          sound_enabled: boolean;
          desktop_enabled: boolean;
          sound_code: string;
          volume_percent: number;
        }>("/notification-preferences/me")
      ).data,
    enabled: Boolean(user),
  });
  const notificationPreferencesRef = useRef(preferences.data);
  notificationPreferencesRef.current = preferences.data;
  const savePreferences = useMutation({
    mutationFn: async (soundEnabled: boolean) =>
      (
        await api.put("/notification-preferences/me", {
          sound_enabled: soundEnabled,
          desktop_enabled: preferences.data?.desktop_enabled ?? false,
          sound_code: preferences.data?.sound_code ?? "CHIME",
          volume_percent: preferences.data?.volume_percent ?? 70,
        })
      ).data,
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["notification-preferences"] }),
  });
  const unreadNotifications = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: async () =>
      (
        await api.get<Array<{ id: number }>>("/notifications", {
          params: { unread_only: true, date_scope: "ALL" },
        })
      ).data,
    enabled: Boolean(user),
    // WebSocket updates are primary. This is only a slow recovery poll when a
    // proxy or network silently interrupts realtime delivery.
    refetchInterval: 300_000,
    refetchIntervalInBackground: false,
  });
  const mentionNotifications = useQuery({
    queryKey: ["notifications", "mentions", "unacknowledged"],
    queryFn: async () =>
      (
        await api.get<MentionNotification[]>("/notifications", {
          params: {
            notification_type: "TICKET_MENTION",
            unacknowledged_only: true,
            date_scope: "ALL",
          },
        })
      ).data,
    enabled: Boolean(user),
    refetchInterval: 60_000,
  });
  const acknowledgeMention = useMutation({
    mutationFn: async (item: MentionNotification) => {
      await api.post(`/notifications/${item.id}/acknowledge`);
      return item;
    },
    onSuccess: async (item) => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
      navigate(item.deep_link || "/tickets");
    },
  });
  const acknowledgeAllMentions = useMutation({
    mutationFn: async () => api.post("/notifications/mentions/acknowledge-all"),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const personalSavedViews = useQuery({
    queryKey: ["saved-views"],
    queryFn: async () =>
      (
        await api.get<
          Array<{ id: number; name: string; owner_user_id: number }>
        >("/saved-views")
      ).data,
    enabled: Boolean(user),
  });
  const saveProfilePreferences = useMutation({
    mutationFn: async () => {
      const requestedSavedViewId = defaultSavedViewId
        ? Number(defaultSavedViewId)
        : null;
      const validSavedViewId = personalSavedViews.data?.some(
        (view) =>
          view.id === requestedSavedViewId && view.owner_user_id === user?.id,
      )
        ? requestedSavedViewId
        : null;
      return updateProfilePreferences({
        default_page: projectOnly ? "home" : defaultPage,
        default_dashboard_scope: dashboardScope,
        default_saved_view_id: validSavedViewId,
        theme_mode: themeMode,
        theme_preset: themePreset,
        profile_picture_url: profilePictureUrl.trim() || null,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      setPreferencesOpen(false);
    },
  });
  const uploadPicture = useMutation({
    mutationFn: uploadProfilePicture,
    onSuccess: (updatedUser) =>
      setProfilePictureUrl(updatedUser.profile_picture_url ?? ""),
  });
  const openPreferences = () => {
    setDefaultPage(user?.default_page ?? "home");
    setDashboardScope(user?.default_dashboard_scope ?? "GENERAL");
    setDefaultSavedViewId(
      user?.default_saved_view_id ? String(user.default_saved_view_id) : "",
    );
    setThemeMode(user?.theme_mode ?? "SYSTEM");
    setThemePreset(user?.theme_preset ?? "CLASSIC");
    setProfilePictureUrl(user?.profile_picture_url ?? "");
    setPreferencesOpen(true);
  };
  const realtimeUserId = user?.id;

  useEffect(() => {
    if (!user || user.user_type === "CLIENT_PORTAL" || location.pathname === "/my-workspace") return;
    const label = location.pathname.split("/").filter(Boolean).join(" / ") || "Home";
    const timer = window.setTimeout(() => {
      void api.post("/tickets/my-workspace/recent", {
        label: label.replace(/-/g, " "),
        path: `${location.pathname}${location.search}`,
        item_type: location.pathname.startsWith("/tickets/") ? "ticket" : location.pathname.startsWith("/clients/") ? "client" : "page",
      }).then(() => queryClient.invalidateQueries({ queryKey: ["my-workspace"] })).catch(() => undefined);
    }, 800);
    return () => window.clearTimeout(timer);
  }, [location.pathname, location.search, queryClient, user]);

  useEffect(() => {
    const unlock = () => {
      void unlockNotificationSound();
    };
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, []);

  useEffect(() => {
    if (!unreadNotifications.data) return;
    const latestId = unreadNotifications.data.reduce(
      (latest, item) => Math.max(latest, item.id),
      0,
    );
    const previousId = previousLatestNotificationId.current;
    const currentPreferences = notificationPreferencesRef.current;
    if (
      previousId !== null &&
      latestId > previousId &&
      currentPreferences?.sound_enabled
    ) {
      void playNotificationSound(
        currentPreferences.sound_code,
        currentPreferences.volume_percent,
      );
    }
    if (previousId === null || latestId > previousId)
      previousLatestNotificationId.current = latestId;
  }, [unreadNotifications.data]);

  useEffect(() => {
    if (!realtimeUserId) return undefined;
    let socket: WebSocket | undefined;
    let reconnectTimer: number | undefined;
    let stopped = false;
    let retryDelay = 1_000;

    const scheduleReconnect = () => {
      if (stopped) return;
      reconnectTimer = window.setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 30_000);
    };
    const connect = async () => {
      try {
        const response = await api.post<{ ticket: string }>(
          "/notifications/realtime-ticket",
        );
        if (stopped) return;
        const base = new URL(
          api.defaults.baseURL ?? "/api/v1",
          window.location.origin,
        );
        base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
        base.pathname = `${base.pathname.replace(/\/$/, "")}/notifications/ws`;
        base.search = `ticket=${encodeURIComponent(response.data.ticket)}`;
        socket = new WebSocket(base);
        socket.onopen = () => {
          retryDelay = 1_000;
        };
        socket.onmessage = (event) => {
          const message = JSON.parse(String(event.data)) as {
            unread_count?: number;
            latest_id?: number;
          };
          const hasNewNotification =
            typeof message.latest_id === "number" &&
            previousLatestNotificationId.current !== null &&
            message.latest_id > previousLatestNotificationId.current;
          if (typeof message.unread_count === "number") {
            const currentPreferences = notificationPreferencesRef.current;
            if (
              (hasNewNotification ||
                (previousUnread.current !== null &&
                  message.unread_count > previousUnread.current)) &&
              currentPreferences?.sound_enabled
            )
              void playNotificationSound(
                currentPreferences.sound_code,
                currentPreferences.volume_percent,
              );
            previousUnread.current = message.unread_count;
          }
          if (typeof message.latest_id === "number")
            previousLatestNotificationId.current = message.latest_id;
          void queryClient.invalidateQueries({ queryKey: ["notifications"] });
          void queryClient.invalidateQueries({
            queryKey: ["support-workspace"],
          });
          void queryClient.invalidateQueries({
            queryKey: ["support-workspace-counts"],
          });
        };
        socket.onclose = scheduleReconnect;
        socket.onerror = () => undefined;
      } catch {
        scheduleReconnect();
      }
    };
    void connect();
    return () => {
      stopped = true;
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      if (socket?.readyState === WebSocket.OPEN) socket.close();
      else if (socket?.readyState === WebSocket.CONNECTING)
        socket.onopen = () => socket?.close();
    };
  }, [queryClient, realtimeUserId]);
  useEffect(() => {
    if (!user) return undefined;
    let lastActivityAt = Date.now();
    let lastHeartbeatAt = 0;
    const heartbeat = () => {
      const now = Date.now();
      if (
        document.visibilityState === "visible" &&
        now - lastActivityAt <= 2 * 60_000 &&
        now - lastHeartbeatAt >= 60_000
      ) {
        lastHeartbeatAt = now;
        void api.post("/auth/presence");
      }
    };
    const recordActivity = () => {
      lastActivityAt = Date.now();
      heartbeat();
    };
    const activityEvents: (keyof DocumentEventMap)[] = [
      "pointerdown",
      "keydown",
      "scroll",
      "touchstart",
    ];
    heartbeat();
    const timer = window.setInterval(heartbeat, 30_000);
    document.addEventListener("visibilitychange", recordActivity);
    activityEvents.forEach((eventName) =>
      document.addEventListener(eventName, recordActivity, { passive: true }),
    );
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", recordActivity);
      activityEvents.forEach((eventName) =>
        document.removeEventListener(eventName, recordActivity),
      );
    };
  }, [user]);
  const canViewTickets =
    hasPermission("ticket.view.all") ||
    hasPermission("ticket.view.team") ||
    hasPermission("ticket.view.own");
  const canUsePreTickets =
    hasPermission("ticket.pre_ticket.create") ||
    hasPermission("ticket.pre_ticket.view.own") ||
    hasPermission("ticket.pre_ticket.queue.view");
  const canViewExecutiveDashboard =
    hasPermission("dashboard.agent") || hasPermission("dashboard.manager");
  const canViewTopManagementDashboard = hasPermission(
    "topmanagementdashboard.view",
  );
  const canViewReports = !projectOnly && canViewExecutiveDashboard;
  const attention = useAttention(1);

  const employeeSections: NavigationSection[] = [
    {
      label: "My Work",
      items: [
        {
          label: t("navigation.projectMyWork"),
          path: projectMyWorkPath,
          icon: <AssignmentTurnedIn />,
          color: "#3949ab",
          visible: hasPermission("project.portfolio.view") && hasPermission(projectWorkspacePermission),
        },
        {
          label: "My Workspace",
          path: "/my-workspace",
          icon: <Badge color="error" badgeContent={attention.data?.total ?? 0} max={99}><Widgets /></Badge>,
          color: "#7b1fa2",
          visible: true,
        },
        {
          label: "Work Assignments",
          path: "/work-assignments",
          icon: <AssignmentTurnedIn />,
          color: "#5e35b1",
          visible: true,
        },
        {
          label: t("navigation.home"),
          path: "/home",
          icon: <Dashboard />,
          color: "#1976d2",
          visible: true,
        },
        {
          label: t("navigation.supportAssistant"),
          path: "/support-workspace",
          icon: <ManageSearch />,
          color: "#1565c0",
          visible: canViewTickets || canUsePreTickets,
        },
        {
          label: t("navigation.tickets"),
          path: "/tickets",
          icon: <ConfirmationNumber />,
          color: "#e65100",
          visible: canViewTickets,
        },
        {
          label: t("navigation.notifications"),
          path: "/notifications",
          icon: <Notifications />,
          color: "#c62828",
          visible: true,
        },
      ],
    },
    {
      label: "Service Management",
      items: [
        {
          label: "Change Requests",
          path: "/change-requests",
          icon: <FactCheck />,
          color: "#3949ab",
          visible: hasPermission("change_request.view"),
        },
        {
          label: t("serviceManagement.problems.title"),
          path: "/problems",
          icon: <ReportProblem />,
          color: "#ad6800",
          visible: hasPermission("problem.view"),
        },
        {
          label: t("serviceManagement.majorIncidents.title"),
          path: "/major-incidents",
          icon: <Warning />,
          color: "#c62828",
          visible: hasPermission("major_incident.view"),
        },
        {
          label: "Ticket templates",
          path: "/ticket-templates",
          icon: <Description />,
          color: "#00838f",
          visible: hasPermission("ticket.template.manage"),
        },
        {
          label: t("navigation.engineerPreTickets"),
          path: "/tickets/pre-tickets",
          icon: <Description />,
          color: "#6a1b9a",
          visible: canUsePreTickets,
        },
        {
          label: t("navigation.complaints"),
          path: "/complaints",
          icon: <ReportProblem />,
          color: "#c62828",
          visible:
            hasPermission("complaint.create") ||
            hasPermission("complaint.manage") ||
            hasPermission("complaint.view.all"),
        },
      ],
    },
    {
      label: "Analytics",
      items: [
        {
          label: t("navigation.executiveDashboard"),
          path: "/dashboard",
          icon: <Assessment />,
          color: "#5e35b1",
          visible: canViewExecutiveDashboard,
        },
        {
          label: t("navigation.topManagementDashboards"),
          path: "/management-dashboards",
          icon: <Assessment />,
          color: "#283593",
          visible: canViewTopManagementDashboard,
        },
        {
          label: t("navigation.reports"),
          path: "/reports",
          icon: <Assessment />,
          color: "#512da8",
          visible: canViewReports,
        },
      ],
    },
    {
      label: t("navigation.customers"),
      items: [
        {
          label: t("navigation.clients"),
          path: "/clients",
          icon: <Business />,
          color: "#00897b",
          visible: hasPermission("client.view"),
        },
        {
          label: t("navigation.customerStructure"),
          path: "/customer-structure",
          icon: <AccountTree />,
          color: "#00695c",
          visible:
            hasPermission("customer_structure.policy.view") ||
            hasPermission("client.view"),
        },
        {
          label: t("navigation.companyOperationsSetup", { defaultValue: "Company Operations Setup" }),
          path: "/company-operations-setup",
          icon: <SettingsSuggest />,
          color: "#5e35b1",
          visible:
            hasPermission("customer_structure.policy.view") ||
            hasPermission("client.manage") ||
            hasPermission("project.manage"),
        },
        {
          label: t("navigation.customerSuccess"),
          path: "/customer-success",
          icon: <Insights />,
          color: "#00838f",
          visible: hasPermission("customer_success.view"),
        },
        {
          label: t("navigation.contractWorkspace"),
          path: "/contracts",
          icon: <Description />,
          color: "#3949ab",
          visible:
            hasPermission("contract.view") ||
            hasPermission("contract.template.view"),
        },
      ],
    },
    {
      label: t("navigation.operations"),
      items: [
        {
          label: t("navigation.operationsWorkspace"),
          path: "/internal-operations",
          icon: <WorkHistory />,
          color: "#6a1b9a",
          visible:
            hasPermission("internal_operation.workspace.view") ||
            hasPermission("internal_operation.view") ||
            hasPermission("shift.view") ||
            hasPermission("visit.entitlement.view") ||
            hasPermission("dashboard.manager"),
        },
        {
          label: t("navigation.serviceChecklists"),
          path: "/service-checklists",
          icon: <FactCheck />,
          color: "#00796b",
          visible:
            hasPermission("service_checklist.view_own") ||
            hasPermission("service_checklist.template.view") ||
            hasPermission("service_checklist.template.manage"),
        },
        {
          label: "UAT",
          path: "/uat",
          icon: <FactCheck />,
          color: "#512da8",
          visible: hasPermission("uat.view"),
        },
        {
          label: t("navigation.employeeOnboarding"),
          path: "/onboarding",
          icon: <Group />,
          color: "#00897b",
          visible:
            hasPermission("onboarding.view.own") ||
            hasPermission("onboarding.progress.view.department"),
        },
      ],
    },
    {
      label: t("navigation.projectManagement"),
      items: [
        {
          label: t("navigation.projectWorkspace"),
          path: projectWorkspacePath,
          icon: <Dashboard />,
          color: "#3949ab",
          visible: hasPermission("project.portfolio.view") && hasPermission(projectWorkspacePermission),
        },
        {
          label: t("navigation.projects"),
          path: "/projects",
          icon: <AccountTree />,
          color: "#3949ab",
          visible: hasPermission("project.portfolio.view"),
        },
        {
          label: t("navigation.projectTemplates"),
          path: "/project-templates",
          icon: <Description />,
          color: "#3949ab",
          visible: hasPermission("project.create") && hasPermission(projectWorkspacePermission),
        },
        {
          label: t("navigation.projectAnalytics", { defaultValue: "Project Analytics" }),
          path: "/project-analytics",
          icon: <Insights />,
          color: "#5e35b1",
          visible: hasPermission("analytics.project.view"),
        },
        {
          label: t("navigation.implementationWorkspace", { defaultValue: "Implementation Workspace" }),
          path: implementationWorkspacePath,
          icon: <WorkHistory />,
          color: "#00796b",
          visible: hasPermission(implementationWorkspacePermission),
        },
        {
          label: t("navigation.implementationIntake", { defaultValue: "Implementation Intake" }),
          path: "/implementation-intake",
          icon: <AssignmentTurnedIn />,
          color: "#00796b",
          visible: hasPermission(implementationWorkspacePermission) && hasPermission("project.assignment.respond"),
        },
        {
          label: t("navigation.implementationAnalytics", { defaultValue: "Implementation Analytics" }),
          path: "/implementation-analytics",
          icon: <Assessment />,
          color: "#ef6c00",
          visible: hasPermission("analytics.implementation.view"),
        },
        {
          label: t("navigation.supportHandoverInbox", { defaultValue: "Support Handover Inbox" }),
          path: "/support-handover-inbox",
          icon: <FactCheck />,
          color: "#00838f",
          visible: hasPermission("handover.review"),
        },
        {
          label: t("navigation.supportReadiness", { defaultValue: "Support Readiness" }),
          path: "/support-readiness",
          icon: <FactCheck />,
          color: "#00838f",
          visible: hasPermission("analytics.support_readiness.view"),
        },
        {
          label: t("navigation.projectHandovers"),
          path: "/project-handovers",
          icon: <Description />,
          color: "#00838f",
          visible: hasPermission("project_handover.view"),
        },
      ],
    },
    {
      label: t("navigation.knowledge"),
      items: [
        {
          label: t("navigation.knowledgeBase"),
          path: "/knowledge",
          icon: <MenuBook />,
          color: "#43a047",
          visible: hasPermission("knowledge.view"),
        },
        {
          label: t("navigation.news"),
          path: "/news",
          icon: <Newspaper />,
          color: "#1565c0",
          visible: hasPermission("news.view"),
        },
      ],
    },
    {
      label: t("navigation.management"),
      items: [
        {
          label: t("navigation.kpiReviews"),
          path: "/kpis",
          icon: <Assessment />,
          color: "#5e35b1",
          visible:
            hasPermission("kpi.view.team") ||
            hasPermission("kpi.view.department") ||
            hasPermission("kpi.view.all"),
        },
        {
          label: t("navigation.financial"),
          path: "/financial",
          icon: <AccountBalance />,
          color: "#00695c",
          visible:
            hasPermission("finance.view") ||
            hasPermission("finance.dashboard.view"),
        },
        {
          label: t("navigation.users"),
          path: "/users",
          icon: <Group />,
          color: "#1565c0",
          visible: hasPermission("user.manage"),
        },
        {
          label: t("navigation.hierarchyConfiguration"),
          path: "/organization/configure",
          icon: <AccountTree />,
          color: "#3949ab",
          visible: hasPermission("user.manage"),
        },
        {
          label: t("navigation.profilesPrivileges"),
          path: "/profiles",
          icon: <Security />,
          color: "#8e24aa",
          visible: hasPermission("profile.manage"),
        },
        {
          label: t("navigation.dashboardAdministration"),
          path: "/dashboard-admin",
          icon: <Dashboard />,
          color: "#3949ab",
          visible: hasPermission("dashboard.manage_widgets"),
        },
        {
          label: t("navigation.accessRequests"),
          path: "/access-requests",
          icon: <Security />,
          color: "#6a1b9a",
          visible: hasPermission("permission.grant.in_context"),
        },
        {
          label: t("navigation.masterData"),
          path: "/crm",
          icon: <Dns />,
          color: "#00838f",
          visible: hasPermission("client.manage"),
        },
        {
          label: t("navigation.dataImports"),
          path: "/imports",
          icon: <UploadFile />,
          color: "#2e7d32",
          visible: hasPermission("data_migration.manage"),
        },
        {
          label: t("navigation.escalationRules"),
          path: "/escalations",
          icon: <Warning />,
          color: "#f57c00",
          visible: hasPermission("configuration.manage"),
        },
        {
          label: t("navigation.auditTrail"),
          path: "/audit",
          icon: <ManageSearch />,
          color: "#c62828",
          visible: hasPermission("audit.view"),
        },
        {
          label: t("navigation.siteSettings"),
          path: "/system?tab=general",
          icon: <Storage />,
          color: "#546e7a",
          visible: hasPermission("configuration.manage"),
        },
        {
          label: "System Maintenance",
          path: "/maintenance",
          icon: <SettingsBackupRestore />,
          color: "#2e7d32",
          visible: hasPermission("maintenance.view"),
        },
        {
          label: t("navigation.agentKpiReport"),
          path: "/dashboard?report=agents",
          icon: <Assessment />,
          color: "#6a1b9a",
          visible: mobile && hasPermission("dashboard.manager"),
        },
        {
          label: t("navigation.productModuleReport"),
          path: "/dashboard?report=products",
          icon: <Assessment />,
          color: "#7b1fa2",
          visible: mobile && hasPermission("dashboard.manager"),
        },
        {
          label: t("navigation.slaWorkloadReport"),
          path: "/dashboard?report=sla",
          icon: <Assessment />,
          color: "#8e24aa",
          visible: mobile && hasPermission("dashboard.manager"),
        },
        {
          label: t("navigation.operationsReports"),
          path: "/internal-operations?section=reports",
          icon: <Assessment />,
          color: "#512da8",
          visible: mobile && hasPermission("dashboard.manager"),
        },
      ],
    },
  ];

  const portalSections: NavigationSection[] = [
    {
      label: t("navigation.overview"),
      items: [
        {
          label: t("navigation.portalHome"),
          path: "/portal",
          icon: <Dashboard />,
          color: "#00897b",
          visible: true,
        },
        {
          label: t("navigation.clientProfile", {
            defaultValue: "Client profile",
          }),
          path: "/portal/profile",
          icon: <Person />,
          color: "#6a1b9a",
          visible: hasPermission("portal.client_profile.view"),
        },
        {
          label: t("navigation.news"),
          path: "/news",
          icon: <Newspaper />,
          color: "#1565c0",
          visible: hasPermission("news.view"),
        },
      ],
    },
    {
      label: t("navigation.support"),
      items: [
        {
          label: t("navigation.myRequests"),
          path: "/portal/tickets",
          icon: <ConfirmationNumber />,
          color: "#e65100",
          visible: true,
        },
        {
          label: "My UAT tests",
          path: "/portal/uat",
          icon: <Assessment />,
          color: "#5e35b1",
          visible: hasPermission("uat.portal.view"),
        },
        {
          label: t("navigation.knowledgeBase"),
          path: "/knowledge",
          icon: <MenuBook />,
          color: "#43a047",
          visible: true,
        },
      ],
    },
  ];

  const sections = user?.user_type === "CLIENT_PORTAL" ? portalSections : projectOnly
    ? employeeSections.map((section) => ({
      ...section,
      items: section.items.filter((item) => isAllowedDeliveryRoute(item.path.split("?")[0], hasPermission)),
    }))
    : employeeSections;
  useEffect(() => {
    if (!user || initializedNavigationUserRef.current === user.id) return;
    setExpandedNavigationSections(
      new Set(
        sections
          .filter((section) => section.items.some((item) => item.visible))
          .map((section) => section.label),
      ),
    );
    initializedNavigationUserRef.current = user.id;
  }, [sections, user]);
  const isSelected = (path: string) => {
    const [pathname, query = ""] = path.split("?");
    const pathnameMatches =
      pathname === "/"
        ? location.pathname === "/"
        : location.pathname === pathname ||
          location.pathname.startsWith(`${pathname}/`);
    if (!pathnameMatches || !query) return pathnameMatches;
    const expected = new URLSearchParams(query);
    const current = new URLSearchParams(location.search);
    return [...expected.entries()].every(
      ([key, value]) => current.get(key) === value,
    );
  };
  const isChildSelected = (path: string) => Boolean(path) && false;
  const toggleNavigation = () => {
    setNavigationCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem(
        "support-hub-navigation-collapsed",
        String(next),
      );
      return next;
    });
  };

  const contextualParentPath = (() => {
    const path = location.pathname;
    if (path.startsWith("/tickets/"))
      return path === "/tickets/pre-tickets"
        ? "/tickets/pre-tickets"
        : "/tickets";
    if (path.startsWith("/clients/")) return "/clients";
    if (path.startsWith("/projects/")) return "/projects";
    if (path.startsWith("/complaints/")) return "/complaints";
    if (path === "/contract-templates") return "/contracts";
    if (["/shifts", "/visit-operations", "/operational-reports"].includes(path))
      return "/internal-operations";
    if (path.startsWith("/users/")) return "/users";
    if (path.startsWith("/profiles/")) return "/profiles";
    if (path.startsWith("/system/")) return "/system?tab=general";
    if (path.startsWith("/portal/tickets/")) return "/portal/tickets";
    return `${path}${location.search}`;
  })();
  const contextualPathname = contextualParentPath.split("?")[0];
  const isProjectDetail = location.pathname.startsWith("/projects/");
  const isDeliveryPage = ["/projects", projectWorkspacePath, projectMyWorkPath, "/project-templates",
    "/project-analytics", "/implementation-workspace", "/implementation-intake", "/implementation-analytics"].includes(location.pathname);
  const inProjectWorkspace = projectOnly || isProjectDetail || isDeliveryPage;
  const matchesContext = (item: NavigationItem) =>
    item.visible &&
    item.path.split("?")[0] === contextualPathname;
  const activeSection =
    sections.find((section) => section.items.some(matchesContext)) ??
    sections.find((section) =>
      section.items.some((item) => item.visible && isSelected(item.path)),
    );
  const activeSectionLabel = activeSection?.label;
  const activeItem =
    activeSection?.items.find(
      (item) => item.visible && item.path === contextualParentPath,
    ) ??
    activeSection?.items.find(matchesContext) ??
    activeSection?.items.find((item) => item.visible && isSelected(item.path));
  useEffect(() => {
    if (!activeSectionLabel) return;
    setExpandedNavigationSections((current) => {
      if (current.has(activeSectionLabel)) return current;
      const next = new Set(current);
      next.add(activeSectionLabel);
      return next;
    });
  }, [activeSectionLabel]);

  const toggleNavigationSection = (label: string) => {
    setExpandedNavigationSections((current) => {
      const next = new Set(current);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  // Legacy contextual-navigation values are kept empty while the old markup is
  // removed in a follow-up cleanup. The second sidebar is permanently disabled.
  const secondaryNavigationOpen = false;
  const secondaryNavigationItem = sections
    .flatMap((section) => section.items)
    .find(() => false);
  const secondaryNavigationChildren: Array<{ path: string; label: string }> = [];
  const ticketNavigationChildren: Array<{ path: string; label: string }> = [];
  const ticketWorkflowChildren: Array<{ path: string; label: string }> = [];
  const filteredSavedViews = (personalSavedViews.data ?? []).filter((view) =>
    view.name
      .toLocaleLowerCase()
      .includes(savedViewNavigationSearch.trim().toLocaleLowerCase()),
  );
  const visibleSavedViews =
    showAllSavedViews || savedViewNavigationSearch.trim()
      ? filteredSavedViews
      : filteredSavedViews.slice(0, 8);
  const openHeaderNavigationSection = sections.find(
    (section) => section.label === navigationMenuSection,
  );


  return (
    <Box sx={{ display: "flex" }}>
      <AppBar position="fixed" sx={{ zIndex: 1300 }}>
        <Toolbar sx={{ px: { xs: 1, sm: 2 } }}>
          {mobile && (
            <IconButton
              color="inherit"
              aria-label="Open navigation"
              onClick={() => setMobileNavigationOpen(true)}
            >
              <MenuIcon />
            </IconButton>
          )}
          <Typography
            variant="h6"
            noWrap
            sx={{
              flexGrow: mobile ? 1 : 0,
              flexShrink: 0,
              marginInlineStart: mobile ? 1 : 0,
              fontSize: { xs: "1rem", sm: "1.25rem" },
              marginInlineEnd: { md: 1.5 },
            }}
          >
            Millensys Support Hub
          </Typography>
          {!mobile && (
            <>
              <Box
                component="nav"
                aria-label="Main navigation sections"
                sx={{
                  display: "flex",
                  alignItems: "center",
                  flexGrow: 1,
                  minWidth: 0,
                  overflowX: "auto",
                  scrollbarWidth: "none",
                  "&::-webkit-scrollbar": { display: "none" },
                }}
              >
                {sections.map((section) => {
                  const visibleItems = section.items.filter(
                    (item) => item.visible,
                  );
                  if (!visibleItems.length) return null;
                  const menuOpen = navigationMenuSection === section.label;
                  return (
                    <Button
                      key={section.label}
                      data-header-navigation-trigger
                      color="inherit"
                      endIcon={<ArrowDropDown />}
                      onClick={(event) => {
                        if (menuOpen) {
                          setNavigationMenuSection(null);
                          setNavigationMenuAnchor(null);
                          return;
                        }
                        setNavigationMenuSection(section.label);
                        setNavigationMenuAnchor(event.currentTarget);
                      }}
                      aria-haspopup="menu"
                      aria-expanded={menuOpen}
                      sx={{
                        flexShrink: 0,
                        px: 1,
                        minWidth: 0,
                        textTransform: "none",
                        fontWeight:
                          activeSectionLabel === section.label ? 900 : 650,
                        bgcolor:
                          activeSectionLabel === section.label
                            ? "rgba(255,255,255,0.12)"
                            : "transparent",
                      }}
                    >
                      {section.label}
                    </Button>
                  );
                })}
              </Box>
              <Menu
                id="header-navigation-menu"
                anchorEl={navigationMenuAnchor}
                open={Boolean(navigationMenuAnchor && openHeaderNavigationSection)}
                hideBackdrop
                sx={{ pointerEvents: "none" }}
                onClose={() => {
                  setNavigationMenuAnchor(null);
                  setNavigationMenuSection(null);
                }}
                slotProps={{
                  paper: {
                    sx: {
                      width: 320,
                      maxHeight: "calc(100vh - 96px)",
                      pointerEvents: "auto",
                    },
                  },
                }}
              >
                {openHeaderNavigationSection?.items
                  .filter((item) => item.visible)
                  .map((item) => (
                    <MenuItem
                      key={item.path}
                      selected={isSelected(item.path)}
                      onClick={() => {
                        setNavigationMenuAnchor(null);
                        setNavigationMenuSection(null);
                        navigate(item.path);
                      }}
                      sx={{ minHeight: 40 }}
                    >
                      <ListItemIcon sx={{ color: item.color }}>
                        {item.icon}
                      </ListItemIcon>
                      <ListItemText primary={item.label} />
                    </MenuItem>
                  ))}
              </Menu>
            </>
          )}
          {!mobile && user?.user_type !== "CLIENT_PORTAL" && canViewReports && (
            <>
              <Button
                color="inherit"
                startIcon={<Assessment />}
                endIcon={<ArrowDropDown />}
                onMouseEnter={(event) => setReportsAnchor(event.currentTarget)}
                onClick={(event) => setReportsAnchor(event.currentTarget)}
                aria-controls={reportsAnchor ? "reports-menu" : undefined}
              >
                Reports
              </Button>
              <Menu
                id="reports-menu"
                anchorEl={reportsAnchor}
                open={Boolean(reportsAnchor)}
                onClose={() => setReportsAnchor(null)}
                MenuListProps={{
                  onMouseLeave: () => setReportsAnchor(null),
                  onMouseEnter: () => undefined,
                }}
              >
                <MenuItem
                  onClick={() => {
                    setReportsAnchor(null);
                    navigate("/reports");
                  }}
                >
                  Reports Center
                </MenuItem>
                {canViewExecutiveDashboard && (
                  <MenuItem
                    onClick={() => {
                      setReportsAnchor(null);
                      navigate("/dashboard");
                    }}
                  >
                    {t("navigation.executiveDashboard")}
                  </MenuItem>
                )}
                {hasPermission("dashboard.manager") && (
                  <MenuItem
                    onClick={() => {
                      setReportsAnchor(null);
                      navigate("/dashboard?report=agents");
                    }}
                  >
                    {t("navigation.agentKpiReport")}
                  </MenuItem>
                )}
                {hasPermission("dashboard.manager") && (
                  <MenuItem
                    onClick={() => {
                      setReportsAnchor(null);
                      navigate("/dashboard?report=products");
                    }}
                  >
                    {t("navigation.productModuleReport")}
                  </MenuItem>
                )}
                {hasPermission("dashboard.manager") && (
                  <MenuItem
                    onClick={() => {
                      setReportsAnchor(null);
                      navigate("/dashboard?report=sla");
                    }}
                  >
                    {t("navigation.slaWorkloadReport")}
                  </MenuItem>
                )}
                {hasPermission("dashboard.manager") && (
                  <MenuItem
                    onClick={() => {
                      setReportsAnchor(null);
                      navigate("/internal-operations?section=reports");
                    }}
                  >
                    {t("navigation.operationsReports")}
                  </MenuItem>
                )}
              </Menu>
            </>
          )}
          <IconButton
            color="inherit"
            aria-label="Notifications"
            onClick={() =>
              navigate("/notifications", {
                state: { returnTo: `${location.pathname}${location.search}` },
              })
            }
          >
            <Badge
              badgeContent={unreadNotifications.data?.length ?? 0}
              color="error"
              max={99}
            >
              <Notifications />
            </Badge>
          </IconButton>
          <Tooltip title={t("common.language")}>
            <Button
              color="inherit"
              aria-label={t("common.language")}
              startIcon={<Language />}
              onClick={(event) => setLanguageAnchor(event.currentTarget)}
              sx={{ minWidth: 0, px: { xs: 1, sm: 1.5 } }}
            >
              {i18n.resolvedLanguage === "ar" ? "AR" : "EN"}
            </Button>
          </Tooltip>
          <Menu
            anchorEl={languageAnchor}
            open={Boolean(languageAnchor)}
            onClose={() => setLanguageAnchor(null)}
          >
            {supportedLanguages.map((language) => (
              <MenuItem
                key={language.code}
                selected={i18n.resolvedLanguage === language.code}
                disabled={changeLanguage.isPending}
                onClick={() => changeLanguage.mutate(language.code)}
              >
                {language.nativeLabel}
              </MenuItem>
            ))}
          </Menu>
          <IconButton
            color="inherit"
            aria-label={t("profile.menuLabel")}
            onClick={(event) => setProfileAnchor(event.currentTarget)}
          >
            <Avatar
              src={user?.profile_picture_url || undefined}
              alt={user?.full_name ?? "User"}
              sx={{ width: 32, height: 32 }}
            />
          </IconButton>
          <Menu
            anchorEl={profileAnchor}
            open={Boolean(profileAnchor)}
            onClose={() => setProfileAnchor(null)}
          >
            <MenuItem disabled>{user?.full_name}</MenuItem>
            {workspaces.length > 1 && workspaces.map((workspace) => (
              <MenuItem key={workspace.id} onClick={() => {
                if (!user) return;
                rememberWorkspace(user.id, workspace.id);
                setProfileAnchor(null);
                navigate(workspace.path);
              }}>
                {workspace.label}
              </MenuItem>
            ))}
            <MenuItem
              onClick={() => {
                setProfileAnchor(null);
                openPreferences();
              }}
            >
              {t("profile.preferences")}
            </MenuItem>
            <MenuItem
              onClick={() => {
                setProfileAnchor(null);
                logout();
                navigate("/login", {
                  replace: true,
                  state: { manualLogout: true },
                });
              }}
            >
              {t("navigation.logout")}
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Drawer
        variant={mobile ? "temporary" : "permanent"}
        open={mobile ? mobileNavigationOpen : true}
        onClose={() => setMobileNavigationOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          width: mobile
            ? 0
            : compactNavigation
              ? collapsedDrawerWidth
              : drawerWidth,
          flexShrink: 0,
          transition: (theme) => theme.transitions.create("width"),
          "& .MuiDrawer-paper": {
            width: mobile
              ? drawerWidth
              : compactNavigation
                ? collapsedDrawerWidth
                : drawerWidth,
            bgcolor: "background.paper",
            overflowX: "hidden",
            transition: (theme) => theme.transitions.create("width"),
          },
        }}
      >
        <Toolbar />
        {!mobile && (
          <Box
            sx={{
              display: "flex",
              justifyContent: compactNavigation ? "center" : "flex-end",
              px: 1,
              py: 0.5,
            }}
          >
            <Tooltip
              title={
                navigationCollapsed ? "Show navigation" : "Hide navigation"
              }
              placement={i18n.resolvedLanguage === "ar" ? "left" : "right"}
            >
              <IconButton
                onClick={toggleNavigation}
                aria-label={
                  navigationCollapsed ? "Show navigation" : "Hide navigation"
                }
              >
                <MenuIcon />
              </IconButton>
            </Tooltip>
          </Box>
        )}
        {!compactNavigation && (
          <TextField
            size="small"
            fullWidth
            value={navigationSearch}
            onChange={(event) => setNavigationSearch(event.target.value)}
            placeholder="Search navigation"
            inputProps={{ "aria-label": "Search navigation" }}
            sx={{ px: 1.5, pb: 1 }}
          />
        )}
        <Box sx={{ overflowY: "auto", pb: 2 }}>
          {sections.map((section, index) => {
            const normalizedNavigationSearch = navigationSearch
              .trim()
              .toLocaleLowerCase();
            const visibleItems = section.items.filter(
              (item) =>
                item.visible &&
                (!normalizedNavigationSearch ||
                  item.label
                    .toLocaleLowerCase()
                    .includes(normalizedNavigationSearch)),
            );
            if (!visibleItems.length) return null;
            const sectionExpanded = expandedNavigationSections.has(section.label);
            return (
              <Box key={section.label}>
                {index > 0 && compactNavigation && (
                  <Divider sx={{ mx: 1, my: 0.75 }} />
                )}
                {!compactNavigation && (
                  <ListItemButton
                    onClick={() => toggleNavigationSection(section.label)}
                    aria-expanded={sectionExpanded}
                    aria-controls={`navigation-section-${index}`}
                    sx={{
                      mx: 1,
                      mt: index ? 0.5 : 0,
                      px: 1.5,
                      minHeight: 38,
                      borderRadius: 1.5,
                      color:
                        activeSectionLabel === section.label
                          ? "text.primary"
                          : "text.secondary",
                    }}
                  >
                    <ListItemText
                      primary={section.label}
                      primaryTypographyProps={{
                        fontSize: 11,
                        fontWeight: 800,
                        letterSpacing: 0.75,
                        textTransform: "uppercase",
                      }}
                    />
                    {sectionExpanded ? (
                      <ExpandMore fontSize="small" />
                    ) : (
                      <ChevronRight fontSize="small" />
                    )}
                  </ListItemButton>
                )}
                <Collapse
                  id={`navigation-section-${index}`}
                  in={
                    compactNavigation ||
                    sectionExpanded ||
                    Boolean(normalizedNavigationSearch)
                  }
                  timeout="auto"
                  unmountOnExit={!compactNavigation}
                >
                  <List dense disablePadding sx={{ pb: 0.5 }}>
                  {visibleItems.map((item) => {
                    return (
                      <Box key={item.path}>
                        <Tooltip
                          title={compactNavigation ? item.label : ""}
                          placement={
                            i18n.resolvedLanguage === "ar" ? "left" : "right"
                          }
                        >
                          <ListItemButton
                            component={RouterLink}
                            to={item.path}
                            selected={isSelected(item.path)}
                            onClick={() => {
                              setMobileNavigationOpen(false);
                            }}
                            aria-label={item.label}
                            sx={{
                              mx: 1,
                              my: 0.25,
                              borderRadius: 1.5,
                              minHeight: 40,
                              justifyContent: compactNavigation
                                ? "center"
                                : "initial",
                              px: compactNavigation ? 1.5 : 2,
                              color: "text.secondary",
                              "&.Mui-selected": {
                                bgcolor: "action.selected",
                                color: "primary.main",
                              },
                              "&.Mui-selected .MuiListItemText-primary": {
                                fontWeight: 800,
                              },
                              "&.Mui-selected:hover": {
                                bgcolor: "action.selected",
                              },
                            }}
                          >
                            <ListItemIcon
                              sx={{
                                minWidth: compactNavigation ? 0 : 40,
                                justifyContent: "center",
                                color: item.color,
                              }}
                            >
                              {item.icon}
                            </ListItemIcon>
                            {!compactNavigation && (
                              <ListItemText primary={item.label} />
                            )}
                          </ListItemButton>
                        </Tooltip>
                      </Box>
                    );
                  })}
                  </List>
                </Collapse>
              </Box>
            );
          })}
        </Box>
      </Drawer>
      {secondaryNavigationOpen && secondaryNavigationItem && (
        <Drawer
          variant="permanent"
          sx={{
            width: secondaryDrawerWidth,
            flexShrink: 0,
            "& .MuiDrawer-paper": {
              width: secondaryDrawerWidth,
              boxSizing: "border-box",
              borderInlineStart: 0,
              left:
                theme.direction === "ltr"
                  ? compactNavigation
                    ? collapsedDrawerWidth
                    : drawerWidth
                  : "auto",
              right:
                theme.direction === "rtl"
                  ? compactNavigation
                    ? collapsedDrawerWidth
                    : drawerWidth
                  : "auto",
              bgcolor: "background.default",
            },
          }}
        >
          <Toolbar />
          <Box sx={{ px: 2, pt: 2, pb: 1 }}>
            <Typography variant="overline" color="text.secondary">
              Navigation
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              {secondaryNavigationItem.label}
            </Typography>
          </Box>
          <Divider />
          <List dense sx={{ px: 1, py: 1.5 }}>
            {secondaryNavigationItem.path === "/tickets" && (
              <>
                <Typography
                  variant="overline"
                  color="text.secondary"
                  sx={{ display: "block", px: 2, pb: 0.5 }}
                >
                  Tickets
                </Typography>
                {ticketNavigationChildren.map((child) => (
                  <ListItemButton
                    key={child.path}
                    component={RouterLink}
                    to={child.path}
                    selected={isChildSelected(child.path)}
                    sx={{ mb: 0.5, borderRadius: 1.5 }}
                  >
                    <ListItemIcon
                      sx={{ minWidth: 38, color: secondaryNavigationItem.color }}
                    >
                      {secondaryNavigationItem.icon}
                    </ListItemIcon>
                    <ListItemText primary={child.label} />
                  </ListItemButton>
                ))}
                <Typography
                  variant="overline"
                  color="text.secondary"
                  sx={{ display: "block", px: 2, pt: 1.5, pb: 0.5 }}
                >
                  {t("navigation.savedViews")}
                </Typography>
                {(personalSavedViews.data?.length ?? 0) > 8 && (
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="Search saved views"
                    value={savedViewNavigationSearch}
                    onChange={(event) =>
                      setSavedViewNavigationSearch(event.target.value)
                    }
                    sx={{ px: 1, pb: 1 }}
                  />
                )}
                {personalSavedViews.isLoading && (
                  <Typography variant="body2" color="text.secondary" sx={{ px: 2, py: 1 }}>
                    Loading saved views…
                  </Typography>
                )}
                {!personalSavedViews.isLoading &&
                  !personalSavedViews.data?.length && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ px: 2, py: 1 }}
                    >
                      No saved views
                    </Typography>
                  )}
                {visibleSavedViews.map((view) => {
                  const savedViewPath = `/tickets?saved_view_id=${view.id}`;
                  return (
                    <ListItemButton
                      key={`saved-view-${view.id}`}
                      component={RouterLink}
                      to={savedViewPath}
                      selected={isChildSelected(savedViewPath)}
                      sx={{ mb: 0.5, borderRadius: 1.5, px: 2 }}
                    >
                      <ListItemText
                        primary={`${view.name}${view.id === user?.default_saved_view_id ? " ★" : ""}`}
                        primaryTypographyProps={{ noWrap: true }}
                      />
                    </ListItemButton>
                  );
                })}
                {!savedViewNavigationSearch.trim() &&
                  filteredSavedViews.length > 8 && (
                    <Button
                      size="small"
                      onClick={() => setShowAllSavedViews((current) => !current)}
                      sx={{ mx: 1, mb: 0.5 }}
                    >
                      {showAllSavedViews ? "Show less" : "Show all"}
                    </Button>
                  )}
                <Typography
                  variant="overline"
                  color="text.secondary"
                  sx={{ display: "block", px: 2, pt: 1.5, pb: 0.5 }}
                >
                  Workflows
                </Typography>
                {ticketWorkflowChildren.map((child) => (
                  <ListItemButton
                    key={child.path}
                    component={RouterLink}
                    to={child.path}
                    selected={isChildSelected(child.path)}
                    sx={{ mb: 0.5, borderRadius: 1.5, px: 2 }}
                  >
                    <ListItemText primary={child.label} />
                  </ListItemButton>
                ))}
              </>
            )}
            {secondaryNavigationItem.path !== "/tickets" &&
              secondaryNavigationChildren.map((child) => (
              <ListItemButton
                key={child.path}
                component={RouterLink}
                to={child.path}
                selected={isChildSelected(child.path)}
                sx={{ mb: 0.5, borderRadius: 1.5, px: 2 }}
              >
                <ListItemText primary={child.label} />
              </ListItemButton>
              ))}
          </List>
        </Drawer>
      )}
      <Box
        component="main"
        onClick={() => {
          if (!inProjectWorkspace && !mobile && !navigationCollapsed) {
            setNavigationCollapsed(true);
            window.localStorage.setItem(
              "support-hub-navigation-collapsed",
              "true",
            );
          }
        }}
        sx={{
          flexGrow: 1,
          p: { xs: 1.5, sm: 2, md: 3 },
          mt: 8,
          minWidth: 0,
          maxWidth: "100%",
        }}
      >
        {!isProjectDetail && !isDeliveryPage && location.pathname !== "/support-workspace" &&
          activeSection &&
          activeItem && (
            <PageContextHeader
              homeLabel={t("navigation.home")}
              title={activeItem.label}
            />
          )}
        <Outlet />
      </Box>
      {!projectOnly && <QuickActions />}
      <NewsAnnouncementDialog />
      <Dialog
        open={Boolean(mentionNotifications.data?.length)}
        disableEscapeKeyDown
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Mentions requiring your attention</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            {mentionNotifications.data?.map((item) => (
              <Paper key={item.id} variant="outlined" sx={{ p: 2 }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={2}
                  justifyContent="space-between"
                  alignItems={{ xs: "stretch", sm: "center" }}
                >
                  <Box>
                    <Typography fontWeight={700}>{item.title}</Typography>
                    <Typography sx={{ whiteSpace: "pre-wrap" }}>
                      {item.message}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(item.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    disabled={acknowledgeMention.isPending}
                    onClick={() => acknowledgeMention.mutate(item)}
                  >
                    Open Ticket &amp; Mark Informed
                  </Button>
                </Stack>
              </Paper>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            disabled={acknowledgeAllMentions.isPending}
            onClick={() => acknowledgeAllMentions.mutate()}
          >
            Mark all informed
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={preferencesOpen}
        onClose={() => setPreferencesOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Profile preferences</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Avatar
                src={
                  profilePictureUrl || user?.profile_picture_url || undefined
                }
                alt={user?.full_name ?? "Profile preview"}
                sx={{ width: 72, height: 72 }}
              />
              <Stack spacing={1} sx={{ flexGrow: 1 }}>
                <Button
                  component="label"
                  variant="outlined"
                  disabled={uploadPicture.isPending}
                >
                  {uploadPicture.isPending
                    ? "Uploading…"
                    : "Choose profile photo"}
                  <input
                    hidden
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) uploadPicture.mutate(file);
                      event.target.value = "";
                    }}
                  />
                </Button>
                <TextField
                  type="url"
                  size="small"
                  label="Or use an image URL"
                  value={profilePictureUrl}
                  onChange={(event) => setProfilePictureUrl(event.target.value)}
                  fullWidth
                />
              </Stack>
            </Stack>
            <FormControl fullWidth>
              <InputLabel>Default page after login</InputLabel>
              <Select
                value={
                  user?.user_type === "CLIENT_PORTAL" ? "portal" : projectOnly ? "home" : defaultPage
                }
                label="Default page after login"
                disabled={user?.user_type === "CLIENT_PORTAL" || projectOnly}
                onChange={(event) => setDefaultPage(event.target.value)}
              >
                {user?.user_type === "CLIENT_PORTAL"
                  ? [
                      <MenuItem key="portal" value="portal">
                        Client portal
                      </MenuItem>,
                    ]
                  : projectOnly ? [
                      <MenuItem key="home" value="home">{deliveryLanding === implementationWorkspacePath
                        ? t("navigation.implementationWorkspace", { defaultValue: "Implementation Workspace" })
                        : t("navigation.projectWorkspace")}</MenuItem>,
                    ] : [
                      <MenuItem key="home" value="home">
                        Support Now
                      </MenuItem>,
                      (hasPermission("dashboard.agent") ||
                        hasPermission("dashboard.manager")) && (
                        <MenuItem key="dashboard" value="dashboard">
                          Dashboard
                        </MenuItem>
                      ),
                      hasPermission("topmanagementdashboard.view") && (
                        <MenuItem key="top-management" value="top-management">
                          Top Management dashboard
                        </MenuItem>
                      ),
                      hasPermission("ticket.create") && (
                        <MenuItem key="ticket-create" value="ticket-create">
                          Create ticket
                        </MenuItem>
                      ),
                      canViewTickets && (
                        <MenuItem key="tickets" value="tickets">
                          Tickets
                        </MenuItem>
                      ),
                      <MenuItem key="my-workspace" value="my-workspace">My Workspace</MenuItem>,
                      canViewTickets && (
                        <MenuItem key="saved-views" value="saved-views">
                          Saved views
                        </MenuItem>
                      ),
                      hasPermission("client.view") && (
                        <MenuItem key="clients" value="clients">
                          Clients
                        </MenuItem>
                      ),
                      hasPermission("knowledge.view") && (
                        <MenuItem key="knowledge" value="knowledge">
                          Knowledge base
                        </MenuItem>
                      ),
                      (hasPermission("internal_operation.workspace.view") ||
                        hasPermission("internal_operation.view") ||
                        hasPermission("shift.view") ||
                        hasPermission("visit.entitlement.view") ||
                        hasPermission("dashboard.manager")) && (
                        <MenuItem
                          key="internal-operations"
                          value="internal-operations"
                        >
                          Internal Operations
                        </MenuItem>
                      ),
                    ]}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Default dashboard</InputLabel>
              <Select
                value={dashboardScope}
                label="Default dashboard"
                onChange={(event) =>
                  setDashboardScope(event.target.value as "GENERAL" | "MY")
                }
              >
                <MenuItem value="GENERAL">General dashboard</MenuItem>
                <MenuItem value="MY">My dashboard only</MenuItem>
              </Select>
            </FormControl>
            {defaultPage === "tickets" && (
              <FormControl fullWidth>
                <InputLabel>Default ticket saved view</InputLabel>
                <Select
                  value={defaultSavedViewId}
                  label="Default ticket saved view"
                  onChange={(event) =>
                    setDefaultSavedViewId(event.target.value)
                  }
                >
                  <MenuItem value="">None — use general ticket layout</MenuItem>
                  {personalSavedViews.data
                    ?.filter((view) => view.owner_user_id === user?.id)
                    .map((view) => (
                      <MenuItem key={view.id} value={String(view.id)}>
                        {view.name}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            )}
            <FormControl fullWidth>
              <InputLabel>Appearance</InputLabel>
              <Select
                value={themeMode}
                label="Appearance"
                onChange={(event) =>
                  setThemeMode(
                    event.target.value as "LIGHT" | "DARK" | "SYSTEM",
                  )
                }
              >
                <MenuItem value="SYSTEM">Use device setting</MenuItem>
                <MenuItem value="LIGHT">Light mode</MenuItem>
                <MenuItem value="DARK">Dark mode</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Color theme</InputLabel>
              <Select
                value={themePreset}
                label="Color theme"
                onChange={(event) =>
                  setThemePreset(event.target.value as typeof themePreset)
                }
              >
                <MenuItem value="CLASSIC">Nordic Indigo</MenuItem>
                <MenuItem value="OCEAN">Aqua Glass</MenuItem>
                <MenuItem value="FOREST">Neo Mint</MenuItem>
                <MenuItem value="SUNSET">Solar Coral</MenuItem>
                <MenuItem value="PLUM">Electric Violet</MenuItem>
                <MenuItem value="COBALT">Cobalt Sky</MenuItem>
                <MenuItem value="MIDNIGHT">Midnight Cyan</MenuItem>
                <MenuItem value="TERRACOTTA">Sand &amp; Terracotta</MenuItem>
                <MenuItem value="GRAPHITE">Graphite Lime</MenuItem>
                <MenuItem value="NORDIC">Nordic Blue</MenuItem>
                <MenuItem value="AURORA">Aurora Glow</MenuItem>
                <MenuItem value="SAKURA">Sakura Bloom</MenuItem>
                <MenuItem value="NEON">Neon Pulse</MenuItem>
                <MenuItem value="MOCHA">Modern Mocha</MenuItem>
                <MenuItem value="ARCTIC">Arctic Glass</MenuItem>
                <MenuItem value="OBSIDIAN_GOLD">Obsidian Gold</MenuItem>
                <MenuItem value="MILLENSYS">Millensys Brand</MenuItem>
              </Select>
            </FormControl>
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.data?.sound_enabled ?? false}
                  onChange={(_, checked) => {
                    savePreferences.mutate(checked);
                    if (checked)
                      playNotificationSound(
                        preferences.data?.sound_code,
                        preferences.data?.volume_percent,
                      );
                  }}
                />
              }
              label="Play a sound for new notifications"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => playNotificationSound()}>Test sound</Button>
          <Button onClick={() => setPreferencesOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={saveProfilePreferences.isPending}
            onClick={() => saveProfilePreferences.mutate()}
          >
            Save preferences
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
