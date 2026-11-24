import {
  Add,
  ArrowForwardIos,
  ContentCopy,
  ContactPage,
  Business,
  Close,
  Delete,
  DragIndicator,
  Download,
  Edit,
  ExpandLess,
  ExpandMore,
  FilterAlt,
  MoreVert,
  Save,
  Search,
  Send,
  Settings,
  TableRows,
  ViewKanban,
  ViewColumn,
  Visibility,
  WhatsApp,
  Flag,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  ListSubheader,
  Menu,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tab,
  Tabs,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, apiErrorMessage } from "../api/client";
import { SemanticLink } from "../components/SemanticLink";
import { TicketSendActionsDialog } from "../components/TicketSendActions";
import { useAuth } from "../auth/AuthContext";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { PreTicketsPage } from "./PreTicketsPage";
import { TicketReportsTab } from "./TicketReportsTab";
import {
  ClientAccessManagerDialog,
  ClientContactsDialog,
} from "./ClientContextDialogs";
import { serverDateInput } from "../utils/serverTime";

type Ticket = {
  id: number;
  ticket_number: string;
  subject: string;
  client_id: number;
  client_name?: string;
  created_by_user_id: number;
  created_by_name?: string;
  department_id?: number;
  department_name?: string;
  parent_department_id?: number;
  parent_department_name?: string;
  status_id: number;
  version: number;
  priority: string;
  updated_at: string;
  source_channel: string;
  is_uat_defect?: boolean;
  uat_cycle_id?: number;
  uat_cycle_test_id?: number;
  uat_attempt_id?: number;
  uat_cycle_code?: string;
  uat_test_code?: string;
  uat_release_version?: string;
  ticket_type_id: number;
  branch_id?: number;
  requester_contact_id?: number;
  requester_name?: string;
  requester_phone_number?: string;
  requester_email?: string;
  requester_job_title?: string;
  active_flags?: Array<{
    id: number;
    flag_id: number;
    code: string;
    name: string;
    color: string;
    pauses_sla: boolean;
  }>;
  contract_id?: number;
  entitlement_status?: string;
  assigned_user_id?: number;
  is_shared_assignment?: boolean;
  assigned_team?: string;
  escalation_assignee_user_id?: number;
  product_id?: number;
  product_module_id?: number;
  environment_id?: number;
  service_id?: number;
  category_id?: number;
  subcategory_id?: number;
  category?: string;
  impact: string;
  urgency: string;
  description: string;
  affected_users?: string;
  first_occurred_at?: string;
  patient_safety_flag: boolean;
  security_incident_flag: boolean;
  resolution_summary?: string;
  root_cause_summary?: string;
  created_at: string;
  progress_started_at?: string;
  resolved_at?: string;
  closed_at?: string;
  archived_at?: string;
  archived_by_user_id?: number;
  archive_reason?: string;
  shift_handover_status?: string;
  shift_handover_reason?: string;
  shift_handover_by_user_id?: number;
  shift_handover_to_user_id?: number;
  shift_handover_at?: string;
  shift_handover_completed_at?: string;
  sla_resolution_target_minutes?: number;
  sla_actual_business_minutes?: number;
  sla_saved_minutes?: number;
  sla_overrun_minutes?: number;
  sla_resolution_state?: string;
  sla_match_reason?: string;
  sla_target_id?: number;
  sla_policy_version?: number;
  sla_calendar_id?: number;
};
type TicketFlagOption = {
  id: number;
  name: string;
  color: string;
  pauses_sla: boolean;
};
type Catalog = {
  id: number;
  code: string;
  name: string;
  name_ar?: string;
  color?: string;
  is_default_resolution_service?: boolean;
};
type RootCause = Catalog & {
  requires_resolution_outcome: boolean;
  requires_permanent_fix: boolean;
};
type KnowledgeArticle = {
  id: number;
  title: string;
  summary: string;
  category?: string;
};
type ResolutionApplication = {
  resolution_summary: string;
  root_cause_ids: number[];
  resolution_service_ids: number[];
  resolution_outcome_id?: number | null;
  permanent_fix_summary?: string | null;
  permanent_fix_status?: string | null;
};
type SupportTeam = Catalog & {
  is_active: boolean;
  leader_user_id?: number;
  member_user_ids?: number[];
};
type Client = { id: number; name: string };
type Assignee = { id: number; full_name: string; username: string };
type Contact = {
  id: number;
  client_id: number;
  branch_id?: number | null;
  full_name: string;
  email?: string | null;
  phone_number?: string | null;
  job_title?: string | null;
  contact_role?: string | null;
  is_primary: boolean;
  is_escalation_contact: boolean;
  is_active: boolean;
};
type Filters = Record<string, string>;
type SavedView = {
  id: number;
  owner_user_id: number;
  name: string;
  scope: string;
  team_id?: number;
  department_id?: number;
  filter_json: string;
  columns_json?: string;
  sort_json?: string;
  has_layout: boolean;
  is_default: boolean;
};
type GridPreference = {
  columns: string[];
  column_widths: Record<string, number>;
  density: "COMPACT" | "STANDARD";
  page_size: 25 | 50 | 100;
  sort_by:
    "updated_at" | "created_at" | "resolved_at" | "priority" | "ticket_number";
  sort_direction: "asc" | "desc";
  group_by: string;
  default_view_mode: TicketViewMode;
  selected_group_values: string[];
  board_settings: Partial<BoardSettings>;
};
type TicketViewMode = "GRID" | "CARDS";

type TicketQueueTab =
  | "all"
  | "pre-tickets"
  | "escalations"
  | "handovers"
  | "approvals"
  | "reports"
  | "trash";

const dedicatedListTabs = new Set<TicketQueueTab>([
  "escalations",
  "handovers",
  "approvals",
  "trash",
]);

const dedicatedListColumns: Partial<Record<TicketQueueTab, readonly string[]>> = {
  escalations: [
    "ticket_number",
    "subject",
    "client",
    "priority",
    "status",
    "department",
    "assigned_engineer",
    "escalation_engineer",
    "updated_at",
  ],
  handovers: [
    "ticket_number",
    "subject",
    "client",
    "priority",
    "status",
    "assigned_engineer",
    "shift_handover_status",
    "shift_handover_reason",
    "updated_at",
  ],
  approvals: [
    "ticket_number",
    "subject",
    "client",
    "entitlement_status",
    "priority",
    "status",
    "assigned_engineer",
    "updated_at",
  ],
  trash: [
    "ticket_number",
    "subject",
    "client",
    "status",
    "assigned_engineer",
    "archived_at",
    "archive_reason",
  ],
};

export function resolveTicketViewMode(
  requestedMode: TicketViewMode,
  queueTab: TicketQueueTab,
): TicketViewMode {
  return dedicatedListTabs.has(queueTab) ? "GRID" : requestedMode;
}

export function resolveTicketListColumns(
  requestedColumns: readonly string[],
  queueTab: TicketQueueTab,
): readonly string[] {
  return dedicatedListColumns[queueTab] ?? requestedColumns;
}
export const ticketResolutionPath = (ticketId: number) =>
  `/tickets/${ticketId}?action=resolve`;
export const ticketCardTransitionMode = (statusCode: string) =>
  statusCode === "RESOLVED" ||
  statusCode === "CLOSED" ||
  statusCode.startsWith("PENDING_")
    ? "status-dialog"
    : "direct";
export const ticketCardDropMode = (
  statusCode: string,
  ticket: Pick<Ticket, "assigned_user_id" | "is_shared_assignment">,
  resolutionDetailsRequiredOnClose = false,
) =>
  statusCode === "ASSIGNED" &&
  (ticket.is_shared_assignment || !ticket.assigned_user_id)
    ? "self-assignment"
    : statusCode === "RESOLVED" && resolutionDetailsRequiredOnClose
      ? "direct"
      : ticketCardTransitionMode(statusCode);
export const ticketCardNeedsStatusMove = (
  targetStatusCode: string,
  targetStatusId: number,
  ticket: Pick<Ticket, "status_id" | "is_shared_assignment">,
) =>
  ticket.status_id !== targetStatusId ||
  (targetStatusCode === "ASSIGNED" && Boolean(ticket.is_shared_assignment));
export const ticketCardRequiresResolution = (
  targetStatus: string,
  currentStatus: string,
  resolutionDetailsRequiredOnClose = false,
) =>
  resolutionDetailsRequiredOnClose
    ? targetStatus === "CLOSED"
    : targetStatus === "RESOLVED" ||
      (targetStatus === "CLOSED" &&
        !["RESOLVED", "CLIENT_CONFIRMATION"].includes(currentStatus));
export const ticketCardRequestStatus = (
  targetStatus: string,
  currentStatus: string,
) =>
  targetStatus === "CLOSED" &&
  ticketCardRequiresResolution(targetStatus, currentStatus)
    ? "RESOLVED"
    : targetStatus;

export const ticketCardAllowsResolutionAttachments = (targetStatus: string) =>
  targetStatus === "RESOLVED" || targetStatus === "CLOSED";

export const ticketCardAllowsKnowledgeResolution = (
  targetStatus: string,
  canViewKnowledge: boolean,
) => canViewKnowledge && ticketCardAllowsResolutionAttachments(targetStatus);
export const ticketNeedsApprovalAttention = (
  ticket: Pick<Ticket, "entitlement_status">,
) => ticket.entitlement_status === "PENDING_APPROVAL";

export const PENDING_BOARD_LANE_KEY = "__PENDING__";
const isPendingStatusCode = (code?: string) =>
  Boolean(code?.startsWith("PENDING_"));
export const DEFAULT_STATUS_LANE_CODES = [
  "NEW",
  "ASSIGNED",
  "IN_PROGRESS",
  "RESOLVED",
  "CLOSED",
  "PENDING",
] as const;
export const defaultStatusLaneRank = (code?: string) => {
  const index = DEFAULT_STATUS_LANE_CODES.indexOf(
    code as (typeof DEFAULT_STATUS_LANE_CODES)[number],
  );
  return index < 0 ? DEFAULT_STATUS_LANE_CODES.length : index;
};

export const ticketStatusLaneId = (
  ticket: Pick<Ticket, "status_id" | "progress_started_at">,
  statusCatalog: Pick<Catalog, "id" | "code">[],
) => {
  const currentStatus = statusCatalog.find(
    (item) => item.id === ticket.status_id,
  );
  if (isPendingStatusCode(currentStatus?.code)) return PENDING_BOARD_LANE_KEY;
  if (
    ticket.progress_started_at &&
    currentStatus &&
    !currentStatus.code.startsWith("PENDING_") &&
    !["ASSIGNED", "RESOLVED", "CLOSED", "CANCELLED"].includes(
      currentStatus.code,
    )
  ) {
    return (
      statusCatalog.find((item) => item.code === "IN_PROGRESS")?.id ??
      ticket.status_id
    );
  }
  return ticket.status_id;
};

type BoardSettings = {
  density: "COMPACT" | "STANDARD" | "DETAILED";
  fields: string[];
  collapsed: string[];
  laneOrder: string[];
  laneLimits: Record<string, number>;
  swimlane: "" | "priority" | "assigned_engineer" | "client";
  cardOrder: number[];
};
const defaultBoardSettings: BoardSettings = {
  density: "STANDARD",
  fields: ["client", "assigned_engineer", "priority", "status", "updated_at"],
  collapsed: [],
  laneOrder: [],
  laneLimits: {},
  swimlane: "",
  cardOrder: [],
};
const parseBoardSettings = (value?: string): BoardSettings => {
  if (!value) return defaultBoardSettings;
  try {
    return {
      ...defaultBoardSettings,
      ...(JSON.parse(value) as Partial<BoardSettings>),
    };
  } catch {
    return defaultBoardSettings;
  }
};
type ApprovalRequest = {
  id: number;
  status: string;
  ticket_id?: number;
  reason_code: string;
  justification: string;
  created_at: string;
  approval_deadline?: string;
};
type DeletionRequest = {
  id: number;
  ticket_id: number;
  ticket_number?: string;
  ticket_subject?: string;
  requested_by_user_id: number;
  requested_by_name?: string;
  reason: string;
  status: string;
  created_at: string;
  version: number;
};
type TicketFilterOptions = {
  creators: Array<{ id: number; name: string }>;
  departments: Array<{
    id: number;
    name: string;
    parent_department_id?: number;
  }>;
};

const filterKeys = [
  "ticket_number",
  "subject",
  "search",
  "uat_defect_only",
  "uat_cycle_code",
  "uat_release_version",
  "description",
  "created_by_user_id",
  "department_id",
  "parent_department_id",
  "source_channel",
  "status_code",
  "priority",
  "impact",
  "urgency",
  "affected_users",
  "patient_safety_flag",
  "security_incident_flag",
  "resolution_summary",
  "client_id",
  "requester_contact_id",
  "branch_id",
  "country_id",
  "zone",
  "location_id",
  "team_id",
  "engineer_id",
  "assigned_user_id",
  "assigned_team",
  "my_teams_only",
  "my_department_requests",
  "department_requests_only",
  "escalations_sent_only",
  "routing_status",
  "open_only",
  "unassigned_only",
  "strictly_unassigned_only",
  "due_soon",
  "needs_attention",
  "breached_only",
  "resolved_only",
  "incomplete_resolution_only",
  "without_product",
  "uat_defect_only",
  "ticket_type_id",
  "product_id",
  "product_module_id",
  "environment_id",
  "service_id",
  "category_id",
  "subcategory_id",
  "root_cause_id",
  "entitlement_status",
  "sla_state",
  "first_occurred_from",
  "first_occurred_to",
  "created_from",
  "created_to",
  "updated_from",
  "updated_to",
  "resolved_from",
  "resolved_to",
  "closed_from",
  "closed_to",
  "assigned_from",
  "assigned_to",
];
const hiddenFilterKeys = [
  "requester_contact_id",
  "country_id",
  "zone",
  "location_id",
  "team_id",
  "engineer_id",
  "assigned_from",
  "assigned_to",
  "my_teams_only",
  "my_department_requests",
  "department_requests_only",
  "escalations_sent_only",
  "open_only",
  "unassigned_only",
  "due_soon",
  "needs_attention",
  "breached_only",
  "resolved_only",
  "incomplete_resolution_only",
  "without_product",
];
const defaultFilterKeys = [
  "ticket_number",
  "source_channel",
  "status_code",
  "assigned_user_id",
  "created_from",
  "created_to",
];
const filterLabels: Record<string, string> = {
  ticket_number: "Ticket number",
  subject: "Subject",
  search: "Search",
  uat_defect_only: "UAT defects only",
  uat_cycle_code: "UAT cycle code",
  uat_release_version: "UAT release",
  description: "Description",
  created_by_user_id: "Created by",
  department_id: "Department",
  parent_department_id: "Parent department",
  source_channel: "Source",
  status_code: "Status",
  priority: "Priority",
  impact: "Impact",
  urgency: "Urgency",
  affected_users: "Affected users",
  patient_safety_flag: "Patient safety",
  security_incident_flag: "Security incident",
  resolution_summary: "Resolution summary",
  client_id: "Client",
  branch_id: "Branch / site",
  assigned_user_id: "Engineer",
  assigned_team: "Support team",
  routing_status: "Department request status",
  ticket_type_id: "Ticket type",
  product_id: "Product",
  product_module_id: "Module",
  environment_id: "Environment",
  service_id: "Service",
  category_id: "Category",
  subcategory_id: "Subcategory",
  root_cause_id: "Root cause",
  entitlement_status: "Entitlement",
  sla_state: "SLA state",
  first_occurred_from: "First occurred from",
  first_occurred_to: "First occurred to",
  created_from: "Created from",
  created_to: "Created to",
  updated_from: "Updated from",
  updated_to: "Updated to",
  resolved_from: "Resolved from",
  resolved_to: "Resolved to",
  closed_from: "Closed from",
  closed_to: "Closed to",
};
const priorityColor = {
  P1: "error",
  P2: "warning",
  P3: "info",
  P4: "default",
} as const;
const legacyContextActionsVisible = () => false;
const baseColumns = [
  ["ticket_number", "Ticket number"],
  ["subject", "Subject"],
  ["created_by", "Created by"],
  ["department", "Department"],
  ["parent_department", "Parent department"],
  ["ticket_type", "Ticket type"],
  ["client", "Client"],
  ["branch", "Branch"],
  ["contact", "Contact / Caller"],
  ["flags", "Flags"],
  ["status", "Status"],
  ["shift_handover_status", "Handover status"],
  ["shift_handover_reason", "Handover reason"],
  ["contract", "Contract"],
  ["entitlement_status", "Entitlement"],
  ["assigned_engineer", "Assigned engineer"],
  ["assigned_team", "Assigned team"],
  ["escalation_engineer", "Escalation engineer"],
  ["product", "Product"],
  ["module", "Module"],
  ["environment", "Environment"],
  ["service", "Service"],
  ["category", "Category"],
  ["subcategory", "Subcategory"],
  ["source_channel", "Source"],
  ["impact", "Impact"],
  ["urgency", "Urgency"],
  ["priority", "Priority"],
  ["description", "Description"],
  ["affected_users", "Affected users"],
  ["first_occurred_at", "First occurred"],
  ["patient_safety_flag", "Patient safety"],
  ["security_incident_flag", "Security incident"],
  ["resolution_summary", "Resolution"],
  ["root_cause_summary", "Root cause"],
  ["sla_resolution_target", "SLA resolution target"],
  ["sla_actual_business_time", "Actual SLA time"],
  ["sla_time_balance", "SLA time saved / overrun"],
  ["sla_resolution_state", "Resolution SLA state"],
  ["created_at", "Created"],
  ["updated_at", "Updated"],
  ["resolved_at", "Resolved"],
  ["closed_at", "Closed"],
  ["archived_at", "Archived"],
  ["archive_reason", "Archive reason"],
] as const;
const availableColumns = [
  ...baseColumns,
  ["sla_match_reason", "SLA match reason"],
  ["sla_target_id", "SLA target ID"],
  ["sla_policy_version", "SLA policy version"],
] as const;
const columnKeys = availableColumns.map(([key]) => key);
const defaultColumns = [
  "ticket_number",
  "subject",
  "client",
  "contact",
  "flags",
  "service",
  "status",
  "priority",
  "assigned_engineer",
  "sla_resolution_target",
  "updated_at",
];
const today = () => {
  return serverDateInput();
};
const isoDate = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};
type DateType = "created" | "updated" | "assigned" | "resolved" | "closed";
type DatePreset =
  | "today"
  | "yesterday"
  | "this_week"
  | "last_week"
  | "this_month"
  | "last_month"
  | "custom"
  | "all";
const dateTypes: DateType[] = [
  "created",
  "updated",
  "assigned",
  "resolved",
  "closed",
];
const datePresets: DatePreset[] = [
  "today",
  "yesterday",
  "this_week",
  "last_week",
  "this_month",
  "last_month",
  "custom",
  "all",
];
const savedDateTypeKey = "__date_type";
const savedDatePresetKey = "__date_preset";
const dateTimeInputValue = (value: string, edge: "from" | "to") => {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value))
    return `${value}T${edge === "from" ? "00:00" : "23:59"}`;
  return value.slice(0, 16);
};

export const dateRangeForPreset = (
  preset: DatePreset,
  referenceToday: string,
) => {
  let from = "";
  let to = "";
  if (preset === "all" || preset === "custom") return { from, to };
  const now = new Date(`${referenceToday}T12:00:00`);
  const start = new Date(now);
  const end = new Date(now);
  if (preset === "yesterday") {
    start.setDate(start.getDate() - 1);
    end.setDate(end.getDate() - 1);
  }
  if (preset === "this_week")
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  if (preset === "last_week") {
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7) - 7);
    end.setTime(start.getTime());
    end.setDate(end.getDate() + 6);
  }
  if (preset === "this_month") start.setDate(1);
  if (preset === "last_month") {
    start.setMonth(start.getMonth() - 1, 1);
    end.setDate(0);
  }
  from = isoDate(start);
  to = isoDate(end);
  return { from, to };
};

export const resolveSavedViewDates = (
  rawFilters: Filters,
  referenceToday: string,
) => {
  const storedType = rawFilters[savedDateTypeKey];
  const dateType = dateTypes.includes(storedType as DateType)
    ? (storedType as DateType)
    : (dateTypes.find(
        (type) => rawFilters[`${type}_from`] || rawFilters[`${type}_to`],
      ) ?? "created");
  const storedPreset = rawFilters[savedDatePresetKey];
  const hasStoredDate = dateTypes.some(
    (type) => rawFilters[`${type}_from`] || rawFilters[`${type}_to`],
  );
  // Views created before date-period metadata existed retain their exact range
  // and are labelled Custom, avoiding a misleading "Today" label.
  const datePreset = datePresets.includes(storedPreset as DatePreset)
    ? (storedPreset as DatePreset)
    : hasStoredDate
      ? "custom"
      : "all";
  const filters = Object.fromEntries(
    Object.entries(rawFilters).filter(
      ([key]) => key !== savedDateTypeKey && key !== savedDatePresetKey,
    ),
  ) as Filters;
  if (storedPreset && datePreset !== "custom") {
    for (const type of dateTypes) {
      filters[`${type}_from`] = "";
      filters[`${type}_to`] = "";
    }
    const range = dateRangeForPreset(datePreset, referenceToday);
    filters[`${dateType}_from`] = range.from;
    filters[`${dateType}_to`] = range.to;
  }
  return { filters, dateType, datePreset };
};
const splitFilter = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
const uniqueCatalog = (groups: Catalog[][]) =>
  Array.from(new Map(groups.flat().map((item) => [item.id, item])).values());

export const filtersFromSearchParams = (
  params: URLSearchParams,
  defaultToToday = false,
) => {
  const values = Object.fromEntries(
    filterKeys.map((key) => [key, params.get(key) ?? ""]),
  ) as Filters;
  if (defaultToToday && !params.toString())
    values.created_from = values.created_to = today();
  return values;
};

export const dateSelectionFromFilters = (filters: Filters) => {
  const dateType =
    dateTypes.find(
      (type) => filters[`${type}_from`] || filters[`${type}_to`],
    ) ?? "created";
  const from = filters[`${dateType}_from`] ?? "";
  const to = filters[`${dateType}_to`] ?? "";
  if (!from && !to) return { dateType, datePreset: "all" as DatePreset };
  const referenceToday = today();
  const matchingPreset = datePresets.find((preset) => {
    if (preset === "custom" || preset === "all") return false;
    const range = dateRangeForPreset(preset, referenceToday);
    return range.from === from && range.to === to;
  });
  return {
    dateType,
    datePreset: (matchingPreset ?? "custom") as DatePreset,
  };
};

export function TicketsPage() {
  const { i18n, t } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const filterLabel = (key: string) =>
    t(`ticketsList.fields.${key}`, { defaultValue: filterLabels[key] ?? key });
  const columnLabel = (key: string, fallback: string) =>
    t(`ticketsList.fields.${key}`, { defaultValue: fallback });
  const slaDuration = (minutes?: number) =>
    minutes == null
      ? "—"
      : minutes < 60
        ? t("ticketsList.minutes", { count: minutes })
        : t("ticketsList.hours", { count: Math.round(minutes / 6) / 10 });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission, user, refreshPermissions } = useAuth();
  const canViewPreTickets =
    hasPermission("ticket.pre_ticket.create") ||
    hasPermission("ticket.pre_ticket.view.own") ||
    hasPermission("ticket.pre_ticket.queue.view");
  const canUseAssignmentFilters =
    hasPermission("ticket.assign.team") ||
    hasPermission("ticket.view.team") ||
    hasPermission("configuration.manage");
  const [searchParams, setSearchParams] = useSearchParams();
  const ticketListSearch = searchParams.toString();
  const ticketListReturnTo = `/tickets${ticketListSearch ? `?${ticketListSearch}` : ""}`;
  const ticketLinkState = { returnTo: ticketListReturnTo };
  const openTicket = (ticketId: number, action?: string) =>
    navigate(`/tickets/${ticketId}${action ? `?action=${action}` : ""}`, {
      state: ticketLinkState,
    });
  const [filters, setFilters] = useState<Filters>(() =>
    filtersFromSearchParams(searchParams, true),
  );
  const lastHandledSearchRef = useRef(searchParams.toString());
  const applyingExternalFiltersRef = useRef(false);
  const requestedSavedViewIdRef = useRef(
    Number(searchParams.get("saved_view_id") || 0),
  );
  const appliedRequestedViewRef = useRef<number | null>(null);
  const [visibleFilterKeys, setVisibleFilterKeys] = useState<string[]>(() =>
    Array.from(
      new Set([
        ...defaultFilterKeys.filter(
          (key) => key !== "assigned_user_id" || canUseAssignmentFilters,
        ),
        ...filterKeys.filter(
          (key) =>
            !hiddenFilterKeys.includes(key) && Boolean(searchParams.get(key)),
        ),
      ]),
    ),
  );
  const [filterToAdd, setFilterToAdd] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [editingViewId, setEditingViewId] = useState<number | null>(null);
  const [activeSavedViewId, setActiveSavedViewId] = useState<number | null>(
    null,
  );
  const [viewName, setViewName] = useState("");
  const [makeDefault, setMakeDefault] = useState(false);
  const [saveViewLayout, setSaveViewLayout] = useState(false);
  const [viewScope, setViewScope] = useState<
    "PRIVATE" | "TEAM" | "DEPARTMENT" | "GLOBAL"
  >("PRIVATE");
  const [viewTeamId, setViewTeamId] = useState("");
  const [defaultApplied, setDefaultApplied] = useState(
    () => searchParams.toString().length > 0,
  );
  const [layoutApplied, setLayoutApplied] = useState(false);
  const [ticketQueryReady, setTicketQueryReady] = useState(false);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [groupBy, setGroupBy] = useState("");
  const [viewMode, setViewMode] = useState<TicketViewMode>("GRID");
  const [selectedGroupValues, setSelectedGroupValues] = useState<string[]>([]);
  const [layoutDirty, setLayoutDirty] = useState(false);
  const [density, setDensity] = useState<"COMPACT" | "STANDARD">("COMPACT");
  const [dateType, setDateType] = useState<DateType>("created");
  const [datePreset, setDatePreset] = useState<DatePreset>("today");
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const [draggedTicketId, setDraggedTicketId] = useState<number | null>(null);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const ticketGridScrollRef = useRef<HTMLDivElement>(null);
  const floatingGridScrollRef = useRef<HTMLDivElement>(null);
  const [floatingGridScroll, setFloatingGridScroll] = useState({
    visible: false,
    left: 0,
    width: 0,
    contentWidth: 0,
  });
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [groupPickerOpen, setGroupPickerOpen] = useState(false);
  const [boardSettingsOpen, setBoardSettingsOpen] = useState(false);
  const [boardSettings, setBoardSettings] =
    useState<BoardSettings>(defaultBoardSettings);
  const [previewTicket, setPreviewTicket] = useState<Ticket | null>(null);
  const [boardMessage, setBoardMessage] = useState("");
  const [draggedLaneKey, setDraggedLaneKey] = useState<string | null>(null);
  const [visibleColumns, setVisibleColumns] =
    useState<string[]>(defaultColumns);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkTeam, setBulkTeam] = useState("");
  const [bulkUser, setBulkUser] = useState("");
  const [bulkReason, setBulkReason] = useState("");
  const [statusOpen, setStatusOpen] = useState(false);
  const [bulkStatus, setBulkStatus] = useState("");
  const [choosePendingStatus, setChoosePendingStatus] = useState(false);
  const [bulkPendingOwner, setBulkPendingOwner] = useState("");
  const [bulkPendingFollowUp, setBulkPendingFollowUp] = useState("");
  const [bulkPendingParty, setBulkPendingParty] = useState<
    "CUSTOMER" | "MILLENSYS"
  >("CUSTOMER");
  const [cardTransitionTicket, setCardTransitionTicket] =
    useState<Ticket | null>(null);
  const [cardResolutionServiceIds, setCardResolutionServiceIds] = useState<
    number[]
  >([]);
  const [cardResolutionAttachments, setCardResolutionAttachments] = useState<
    File[]
  >([]);
  const [cardKnowledgeSearch, setCardKnowledgeSearch] = useState("");
  const [cardKnowledgeError, setCardKnowledgeError] = useState("");
  const [cardRootCauseIds, setCardRootCauseIds] = useState<number[]>([]);
  const [cardResolutionOutcomeId, setCardResolutionOutcomeId] = useState("");
  const [cardPermanentFixStatus, setCardPermanentFixStatus] =
    useState("PLANNED");
  const [cardPermanentFixSummary, setCardPermanentFixSummary] = useState("");
  const [cardCreateKnowledge, setCardCreateKnowledge] = useState(false);
  const [cardCloseAfterResolve, setCardCloseAfterResolve] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [pendingTicket, setPendingTicket] = useState<Ticket | null>(null);
  const [rowMenu, setRowMenu] = useState<{
    ticket: Ticket;
    mouseX: number;
    mouseY: number;
  } | null>(null);
  const [otherActionsAnchor, setOtherActionsAnchor] =
    useState<HTMLElement | null>(null);
  const assistantPreferences = useQuery({
    queryKey: ["support-assistant-preferences"],
    queryFn: async () =>
      (
        await api.get<
          Record<string, unknown> & { pinned_ticket_ids: number[] }
        >("/tickets/support-assistant/preferences")
      ).data,
  });
  const saveAssistantPreferences = useMutation({
    mutationFn: async (pinned_ticket_ids: number[]) =>
      (
        await api.put("/tickets/support-assistant/preferences", {
          ...assistantPreferences.data,
          pinned_ticket_ids,
        })
      ).data,
    onSuccess: (data) =>
      queryClient.setQueryData(["support-assistant-preferences"], data),
  });
  const pinnedTicketIds = assistantPreferences.data?.pinned_ticket_ids ?? [];
  const toggleTicketPin = (ticketId: number) =>
    saveAssistantPreferences.mutate(
      pinnedTicketIds.includes(ticketId)
        ? pinnedTicketIds.filter((id) => id !== ticketId)
        : [...pinnedTicketIds, ticketId],
    );
  const [sendTicketId, setSendTicketId] = useState<number | null>(null);
  const resolutionWorkflowSettings = useQuery({
    queryKey: ["site-settings", "ticket-resolution-workflow"],
    queryFn: async () =>
      (
        await api.get<{ resolution_details_required_on_close?: boolean }>(
          "/system/site-settings",
        )
      ).data,
  });
  const resolutionDetailsRequiredOnClose =
    resolutionWorkflowSettings.data?.resolution_details_required_on_close ===
    true;
  const [clientMenu, setClientMenu] = useState<{
    anchor: HTMLElement;
    ticket: Ticket;
  } | null>(null);
  const [clientAccessDialog, setClientAccessDialog] = useState<{
    clientId: number;
    editMode: boolean;
  } | null>(null);
  const [clientContactsDialog, setClientContactsDialog] = useState<{
    clientId: number;
    ticketId: number;
  } | null>(null);
  const [contactMenu, setContactMenu] = useState<{
    anchor: HTMLElement;
    ticket: Ticket;
  } | null>(null);
  const [flagDialogTicket, setFlagDialogTicket] = useState<Ticket | null>(null);
  const [selectedFlagId, setSelectedFlagId] = useState("");
  const [flagReason, setFlagReason] = useState("");
  const ticketFlagOptions = useQuery({
    queryKey: ["ticket-flag-options"],
    enabled: flagDialogTicket !== null,
    queryFn: async () =>
      (await api.get<TicketFlagOption[]>("/ticket-flags")).data,
  });
  const applyTicketFlag = useMutation({
    mutationFn: async () =>
      api.post(`/ticket-flags/ticket/${flagDialogTicket?.id}`, {
        flag_id: Number(selectedFlagId),
        reason: flagReason.trim(),
      }),
    onSuccess: async () => {
      setFlagDialogTicket(null);
      setSelectedFlagId("");
      setFlagReason("");
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });
  const [contactDialog, setContactDialog] = useState<Contact | null>(null);
  const [contactMessage, setContactMessage] = useState<string | null>(null);
  const loadContact = useMutation({
    mutationFn: async (ticket: Ticket) => {
      if (!ticket.requester_contact_id) throw new Error("No caller");
      const rows = (
        await api.get<Contact[]>("/contacts", {
          params: { client_id: ticket.client_id },
        })
      ).data;
      const contact = rows.find(
        (item) => item.id === ticket.requester_contact_id,
      );
      if (!contact) throw new Error("Caller not found");
      return contact;
    },
    onSuccess: (contact) => {
      setContactDialog(contact);
      setContactMessage(null);
    },
  });
  const saveContact = useMutation({
    mutationFn: async (payload: Partial<Contact>) =>
      (await api.patch<Contact>(`/contacts/${contactDialog?.id}`, payload))
        .data,
    onSuccess: async (contact) => {
      setContactDialog(contact);
      setContactMessage("Contact information was updated.");
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });
  const [queueTab, setQueueTab] = useState<TicketQueueTab>(() =>
    searchParams.get("tab") === "pre-tickets" && canViewPreTickets
      ? "pre-tickets"
      : searchParams.get("tab") === "trash" &&
          hasPermission("ticket.trash.view")
        ? "trash"
        : searchParams.get("tab") === "escalations" &&
            hasPermission("ticket.view.department")
          ? "escalations"
          : searchParams.get("tab") === "handovers"
            ? "handovers"
            : searchParams.get("tab") === "reports" &&
                hasPermission("report.export")
              ? "reports"
              : searchParams.get("tab") === "approvals" &&
                  (hasPermission("entitlement_approval.view") ||
                    hasPermission("ticket.delete.approve"))
                ? "approvals"
                : "all",
  );
  const [escalationQueue, setEscalationQueue] = useState<
    "received" | "sent" | "returned"
  >("received");
  const approvalTab = queueTab === "approvals";
  const handoverTab = queueTab === "handovers";
  const trashTab = queueTab === "trash";
  const preTicketsTab = queueTab === "pre-tickets";
  const reportsTab = queueTab === "reports";
  const dedicatedListTab = dedicatedListTabs.has(queueTab);
  const effectiveViewMode = resolveTicketViewMode(viewMode, queueTab);
  const showLegacyFastActionPanel = false;
  const listColumns = resolveTicketListColumns(visibleColumns, queueTab);
  const listDensity = dedicatedListTab ? "STANDARD" : density;
  const effectiveGroupBy = dedicatedListTab ? "" : groupBy;

  // Dashboard and report widgets navigate to this same mounted route. Treat
  // their URL as the source of truth and replace the current ticket view,
  // rather than merging it with stale local or saved-view filters.
  useLayoutEffect(() => {
    const serialized = searchParams.toString();
    if (serialized === lastHandledSearchRef.current) return;
    lastHandledSearchRef.current = serialized;
    applyingExternalFiltersRef.current = true;
    const nextFilters = filtersFromSearchParams(
      searchParams,
      serialized.length === 0,
    );
    const nextDateSelection = dateSelectionFromFilters(nextFilters);
    setFilters(nextFilters);
    setDateType(nextDateSelection.dateType);
    setDatePreset(nextDateSelection.datePreset);
    setVisibleFilterKeys(
      Array.from(
        new Set([
          ...defaultFilterKeys.filter(
            (key) => key !== "assigned_user_id" || canUseAssignmentFilters,
          ),
          ...filterKeys.filter(
            (key) =>
              !hiddenFilterKeys.includes(key) && Boolean(nextFilters[key]),
          ),
        ]),
      ),
    );
    setActiveSavedViewId(null);
    setSelectedIds([]);
    setPage(0);
    const requestedTab = searchParams.get("tab");
    setQueueTab(
      requestedTab === "pre-tickets" && canViewPreTickets
        ? "pre-tickets"
        : requestedTab === "trash" && hasPermission("ticket.trash.view")
          ? "trash"
          : requestedTab === "escalations" &&
              hasPermission("ticket.view.department")
            ? "escalations"
            : requestedTab === "handovers"
              ? "handovers"
              : requestedTab === "reports" && hasPermission("report.export")
                ? "reports"
                : requestedTab === "approvals" &&
                    (hasPermission("entitlement_approval.view") ||
                      hasPermission("ticket.delete.approve"))
                  ? "approvals"
                  : "all",
    );
  }, [canUseAssignmentFilters, canViewPreTickets, hasPermission, searchParams]);

  useEffect(() => {
    if (applyingExternalFiltersRef.current) {
      applyingExternalFiltersRef.current = false;
      return;
    }
    const active = Object.fromEntries(
      Object.entries(filters).filter(
        ([key, value]) => value && key !== "entitlement_status",
      ),
    );
    if (preTicketsTab) active.tab = "pre-tickets";
    else if (reportsTab) active.tab = "reports";
    else if (trashTab) active.tab = "trash";
    else if (approvalTab) active.tab = "approvals";
    else if (handoverTab) active.tab = "handovers";
    else if (queueTab === "escalations") active.tab = "escalations";
    else if (filters.entitlement_status)
      active.entitlement_status = filters.entitlement_status;
    const nextParams = new URLSearchParams(active).toString();
    if (nextParams === searchParams.toString()) return;
    lastHandledSearchRef.current = nextParams;
    setSearchParams(active, { replace: true });
  }, [
    approvalTab,
    handoverTab,
    preTicketsTab,
    reportsTab,
    trashTab,
    queueTab,
    filters,
    searchParams,
    setSearchParams,
  ]);

  function selectEscalationQueue(queue: "received" | "sent" | "returned") {
    setEscalationQueue(queue);
    setPage(0);
    setFilters((current) => ({
      ...current,
      my_department_requests:
        queue === "received" || queue === "returned" ? "true" : "",
      department_requests_only:
        queue === "received" || queue === "returned" ? "true" : "",
      escalations_sent_only: queue === "sent" ? "true" : "",
      routing_status:
        queue === "returned"
          ? "RETURNED"
          : queue === "received"
            ? "NEW,IN_PROGRESS"
            : "",
      created_from: "",
      created_to: "",
    }));
  }

  const updateFilter = (key: string, value: string) => {
    setPage(0);
    if (value && key !== "my_teams_only")
      setVisibleFilterKeys((current) =>
        current.includes(key) ? current : [...current, key],
      );
    setFilters((current) => ({
      ...current,
      [key]: value,
      ...(key === "assigned_team" ? { my_teams_only: "" } : {}),
      ...(key === "product_id" ? { product_module_id: "" } : {}),
      ...(key === "client_id" ? { branch_id: "" } : {}),
      ...(key === "category_id" ? { subcategory_id: "" } : {}),
    }));
  };
  const applyFastAction = (overrides: Filters) => {
    setPage(0);
    setActiveSavedViewId(null);
    setVisibleFilterKeys(
      defaultFilterKeys.filter(
        (key) => key !== "assigned_user_id" || canUseAssignmentFilters,
      ),
    );
    setDateType("created");
    setDatePreset(
      overrides.created_from === today() && overrides.created_to === today()
        ? "today"
        : "all",
    );
    setSortBy("updated_at");
    setSortDirection("desc");
    setFilters({
      ...Object.fromEntries(filterKeys.map((key) => [key, ""])),
      ...overrides,
    });
  };
  const removeFilter = (key: string) => {
    updateFilter(key, "");
    setVisibleFilterKeys((current) => current.filter((item) => item !== key));
  };
  const removeActiveFilter = (key: string) => {
    const nextFilters = { ...filters, [key]: "" };
    const hasRemainingFilter = Object.values(nextFilters).some(Boolean);
    if (!hasRemainingFilter) {
      const currentDay = today();
      nextFilters.created_from = currentDay;
      nextFilters.created_to = currentDay;
      setDateType("created");
      setDatePreset("today");
    }
    setFilters(nextFilters);
    setPage(0);
  };
  const activeFilters = {
    ...Object.fromEntries(
      Object.entries(filters).filter(
        ([key, value]) => value && key !== "entitlement_status",
      ),
    ),
    ...(approvalTab
      ? { entitlement_status: "PENDING_APPROVAL" }
      : filters.entitlement_status
        ? { entitlement_status: filters.entitlement_status }
        : {}),
    ...(handoverTab ? { shift_handover_only: "true" } : {}),
  };
  const tickets = useQuery({
    queryKey: [
      "tickets",
      trashTab ? "trash" : "active",
      activeFilters,
      page,
      pageSize,
      sortBy,
      sortDirection,
    ],
    queryFn: async () => {
      const response = await api.get<Ticket[]>(
        trashTab ? "/tickets/trash" : "/tickets",
        {
          params: trashTab
            ? { limit: pageSize, offset: page * pageSize }
            : {
                ...activeFilters,
                ...(!filters.ticket_type_id
                  ? { exclude_ticket_type_code: "CHANGE_REQUEST" }
                  : {}),
                timezone_offset_minutes: -new Date().getTimezoneOffset(),
                limit: pageSize,
                offset: page * pageSize,
                sort_by: sortBy,
                sort_direction: sortDirection,
              },
        },
      );
      return {
        items: response.data,
        total: Number(
          response.headers["x-total-count"] ?? response.data.length,
        ),
      };
    },
    // Without URL filters, the default saved view is restored asynchronously.
    // Wait for it so the provisional Today range never flashes incorrect rows.
    enabled: ticketQueryReady && !preTicketsTab && !reportsTab,
    refetchInterval: effectiveViewMode === "CARDS" ? 15_000 : false,
  });
  const statuses = useQuery({
    queryKey: ["ticket-statuses"],
    queryFn: async () => (await api.get<Catalog[]>("/ticket-statuses")).data,
  });
  const types = useQuery({
    queryKey: ["ticket-types"],
    queryFn: async () => (await api.get<Catalog[]>("/ticket-types")).data,
  });
  const clients = useQuery({
    queryKey: ["clients"],
    queryFn: async () =>
      (await api.get<Client[]>("/clients", { params: { limit: 200 } })).data,
  });
  const products = useQuery({
    queryKey: ["products"],
    queryFn: async () => (await api.get<Catalog[]>("/products")).data,
  });
  const branches = useQuery({
    queryKey: ["ticket-filter-branches", filters.client_id],
    queryFn: async () =>
      uniqueCatalog(
        await Promise.all(
          splitFilter(filters.client_id).map(
            async (id) =>
              (await api.get<Catalog[]>(`/clients/${id}/branches`)).data,
          ),
        ),
      ),
    enabled: Boolean(filters.client_id),
  });
  const environments = useQuery({
    queryKey: ["environments"],
    queryFn: async () => (await api.get<Catalog[]>("/environments")).data,
  });
  const services = useQuery({
    queryKey: ["services"],
    queryFn: async () => (await api.get<Catalog[]>("/services")).data,
  });
  const categories = useQuery({
    queryKey: ["ticket-categories"],
    queryFn: async () => (await api.get<Catalog[]>("/ticket-categories")).data,
  });
  const rootCauses = useQuery({
    queryKey: ["root-causes"],
    queryFn: async () => (await api.get<RootCause[]>("/root-causes")).data,
  });
  const resolutionOutcomes = useQuery({
    queryKey: ["resolution-outcomes"],
    queryFn: async () =>
      (await api.get<Catalog[]>("/resolution-outcomes")).data,
  });
  const subcategories = useQuery({
    queryKey: ["ticket-filter-subcategories", filters.category_id],
    queryFn: async () =>
      uniqueCatalog(
        await Promise.all(
          splitFilter(filters.category_id).map(
            async (id) =>
              (
                await api.get<Catalog[]>(
                  `/ticket-categories/${id}/subcategories`,
                )
              ).data,
          ),
        ),
      ),
    enabled: Boolean(filters.category_id),
  });
  const modules = useQuery({
    queryKey: ["product-modules", filters.product_id],
    queryFn: async () =>
      uniqueCatalog(
        await Promise.all(
          splitFilter(filters.product_id).map(
            async (id) =>
              (await api.get<Catalog[]>(`/products/${id}/modules`)).data,
          ),
        ),
      ),
    enabled: Boolean(filters.product_id),
  });
  const assignees = useQuery({
    queryKey: ["ticket-assignees"],
    queryFn: async () => (await api.get<Assignee[]>("/ticket-assignees")).data,
    enabled:
      hasPermission("ticket.assign.team") ||
      hasPermission("ticket.view.team") ||
      hasPermission("configuration.manage"),
  });
  const ticketFilterOptions = useQuery({
    queryKey: ["ticket-filter-options"],
    queryFn: async () =>
      (await api.get<TicketFilterOptions>("/tickets/filter-options")).data,
  });
  const supportTeams = useQuery({
    queryKey: ["support-teams"],
    queryFn: async () => (await api.get<SupportTeam[]>("/support-teams")).data,
    enabled:
      hasPermission("ticket.assign.team") ||
      hasPermission("ticket.view.team") ||
      hasPermission("configuration.manage"),
  });
  const savedViews = useQuery({
    queryKey: ["saved-views"],
    queryFn: async () => (await api.get<SavedView[]>("/saved-views")).data,
  });
  const cardTransitionDetails = useQuery({
    queryKey: ["ticket-card-transition", cardTransitionTicket?.id],
    queryFn: async () =>
      (
        await api.get<
          Ticket & {
            resolution_service_ids: number[];
            root_cause_ids: number[];
            resolution_outcome_id?: number;
            permanent_fix_status?: string;
            permanent_fix_summary?: string;
          }
        >(`/tickets/${cardTransitionTicket!.id}`)
      ).data,
    enabled: Boolean(
      cardTransitionTicket && ["RESOLVED", "CLOSED"].includes(bulkStatus),
    ),
  });
  const cardResolutionServices = useQuery({
    queryKey: [
      "ticket-card-resolution-services",
      cardTransitionTicket?.client_id,
    ],
    queryFn: async () =>
      (
        await api.get<{ services: Catalog[] }>("/ticket-contract-catalog", {
          params: { client_id: cardTransitionTicket!.client_id },
        })
      ).data.services,
    enabled: Boolean(
      cardTransitionTicket && ["RESOLVED", "CLOSED"].includes(bulkStatus),
    ),
  });
  const cardKnowledgeArticles = useQuery({
    queryKey: ["ticket-card-knowledge-search", cardKnowledgeSearch],
    queryFn: async () =>
      (
        await api.get<KnowledgeArticle[]>("/knowledge", {
          params: {
            search: cardKnowledgeSearch.trim(),
            published_only: true,
            limit: 8,
          },
        })
      ).data,
    enabled:
      hasPermission("knowledge.view") &&
      Boolean(cardTransitionTicket) &&
      ticketCardAllowsResolutionAttachments(bulkStatus) &&
      cardKnowledgeSearch.trim().length >= 2,
  });
  const applyCardKnowledgeResolution = useMutation({
    mutationFn: async (articleId: number) =>
      (
        await api.post<ResolutionApplication>(
          `/knowledge/tickets/${cardTransitionTicket!.id}/articles/${articleId}/apply-resolution`,
        )
      ).data,
    onSuccess: (result) => {
      setBulkReason(result.resolution_summary);
      setCardRootCauseIds(result.root_cause_ids);
      setCardResolutionServiceIds(result.resolution_service_ids);
      setCardResolutionOutcomeId(
        result.resolution_outcome_id
          ? String(result.resolution_outcome_id)
          : "",
      );
      setCardPermanentFixSummary(result.permanent_fix_summary ?? "");
      setCardPermanentFixStatus(result.permanent_fix_status ?? "PLANNED");
      setCardKnowledgeError("");
    },
    onError: (cause) =>
      setCardKnowledgeError(
        apiErrorMessage(
          cause,
          "The knowledge resolution could not be applied.",
        ),
      ),
  });
  useEffect(() => {
    if (!cardTransitionTicket || !["RESOLVED", "CLOSED"].includes(bulkStatus))
      return;
    const existing =
      bulkStatus === "CLOSED"
        ? (cardTransitionDetails.data?.resolution_service_ids ?? [])
        : [];
    if (existing.length) {
      setCardResolutionServiceIds(existing);
      return;
    }
    const defaultService = cardResolutionServices.data?.find(
      (service) => service.is_default_resolution_service,
    );
    if (defaultService) setCardResolutionServiceIds([defaultService.id]);
  }, [
    bulkStatus,
    cardResolutionServices.data,
    cardTransitionDetails.data,
    cardTransitionTicket,
  ]);
  const selectedCardRootCauses = (rootCauses.data ?? []).filter((cause) =>
    cardRootCauseIds.includes(cause.id),
  );
  const cardResolutionOutcomeRequired = selectedCardRootCauses.some(
    (cause) => cause.requires_resolution_outcome,
  );
  const cardPermanentFixRequired = selectedCardRootCauses.some(
    (cause) => cause.requires_permanent_fix,
  );
  const cardCurrentStatus = cardTransitionTicket
    ? (statuses.data?.find(
        (status) => status.id === cardTransitionTicket.status_id,
      )?.code ?? "")
    : "";
  const cardRequiresResolution = Boolean(
    cardTransitionTicket &&
    ticketCardRequiresResolution(
      bulkStatus,
      cardCurrentStatus,
      resolutionDetailsRequiredOnClose,
    ),
  );
  useEffect(() => {
    if (
      !cardTransitionTicket ||
      !cardRequiresResolution ||
      !cardTransitionDetails.data
    )
      return;
    const details = cardTransitionDetails.data;
    setBulkReason(details.resolution_summary ?? "");
    setCardRootCauseIds(details.root_cause_ids ?? []);
    setCardResolutionOutcomeId(
      details.resolution_outcome_id
        ? String(details.resolution_outcome_id)
        : "",
    );
    setCardPermanentFixStatus(details.permanent_fix_status ?? "PLANNED");
    setCardPermanentFixSummary(details.permanent_fix_summary ?? "");
  }, [
    cardRequiresResolution,
    cardTransitionDetails.data,
    cardTransitionTicket,
  ]);
  const gridPreference = useQuery({
    queryKey: ["ticket-grid-preference", user?.id],
    queryFn: async () =>
      (await api.get<GridPreference>("/ticket-grid-preference")).data,
  });
  const saveGridPreference = useMutation({
    mutationFn: async (preference: GridPreference) =>
      api.put("/ticket-grid-preference", preference),
    onSuccess: (response) => {
      queryClient.setQueryData(
        ["ticket-grid-preference", user?.id],
        response.data,
      );
      setLayoutDirty(false);
    },
  });
  const approvals = useQuery({
    queryKey: ["entitlement-approvals", "PENDING"],
    queryFn: async () =>
      (
        await api.get<ApprovalRequest[]>("/entitlement-approvals", {
          params: { status: "PENDING" },
        })
      ).data,
    enabled: hasPermission("entitlement_approval.view"),
  });
  const deletionRequests = useQuery({
    queryKey: ["ticket-deletion-requests", "PENDING"],
    queryFn: async () =>
      (
        await api.get<DeletionRequest[]>("/tickets/deletion-requests", {
          params: { status: "PENDING" },
        })
      ).data,
    enabled: hasPermission("ticket.delete.approve"),
  });
  const preTicketActionCount = useQuery({
    queryKey: ["pre-ticket-action-count"],
    queryFn: async () => {
      if (!hasPermission("ticket.pre_ticket.queue.view")) {
        const response = await api.get("/pre-tickets/mine", {
          params: { unconverted_only: true, limit: 1 },
        });
        return Number(
          response.headers["x-total-count"] ?? response.data.length,
        );
      }
      const responses = await Promise.all(
        ["SUBMITTED", "CLAIMED"].map((status) =>
          api.get("/pre-tickets/queue", {
            params: { status, unconverted_only: true, limit: 1 },
          }),
        ),
      );
      return responses.reduce(
        (total, response) =>
          total +
          Number(response.headers["x-total-count"] ?? response.data.length),
        0,
      );
    },
    enabled: canViewPreTickets,
    refetchInterval: 30_000,
  });
  useEffect(() => {
    if (layoutApplied) return;
    if (gridPreference.isError) {
      setLayoutApplied(true);
      return;
    }
    if (!gridPreference.data) return;
    const preference = gridPreference.data;
    if (preference.columns.length)
      setVisibleColumns(
        preference.columns.filter((column) =>
          (columnKeys as readonly string[]).includes(column),
        ),
      );
    setDensity(preference.density);
    setPageSize(preference.page_size);
    setSortBy(preference.sort_by);
    setSortDirection(preference.sort_direction);
    setGroupBy(preference.group_by);
    setColumnWidths(preference.column_widths ?? {});
    setViewMode(preference.default_view_mode ?? "GRID");
    setSelectedGroupValues(preference.selected_group_values ?? []);
    setBoardSettings({
      ...defaultBoardSettings,
      ...(preference.board_settings ?? {}),
    });
    setLayoutApplied(true);
  }, [gridPreference.data, gridPreference.isError, layoutApplied]);

  const persistGridLayout = (defaultViewMode?: TicketViewMode) =>
    saveGridPreference.mutate({
      columns: visibleColumns,
      column_widths: Object.fromEntries(
        Object.entries(columnWidths).map(([column, width]) => [
          column,
          Math.round(width),
        ]),
      ),
      density,
      page_size: pageSize as 25 | 50 | 100,
      sort_by: sortBy as GridPreference["sort_by"],
      sort_direction: sortDirection,
      group_by: groupBy,
      default_view_mode:
        defaultViewMode ?? gridPreference.data?.default_view_mode ?? "GRID",
      selected_group_values: selectedGroupValues,
      board_settings: boardSettings,
    });

  const persistCurrentLayout = async () => {
    const activeView = savedViews.data?.find(
      (view) => view.id === activeSavedViewId,
    );
    if (!activeView || activeView.owner_user_id !== user?.id) {
      persistGridLayout();
      return;
    }
    await api.put(`/saved-views/${activeView.id}`, {
      name: activeView.name,
      scope: activeView.scope,
      team_id: activeView.team_id ?? null,
      department_id: activeView.department_id ?? null,
      filters: JSON.parse(activeView.filter_json || "{}"),
      columns: visibleColumns,
      sort: [
        { field: sortBy, direction: sortDirection },
        ...(groupBy ? [{ field: "__group_by", direction: groupBy }] : []),
        { field: "__view_mode", direction: viewMode },
        ...(selectedGroupValues.length
          ? [
              {
                field: "__group_values",
                direction: JSON.stringify(selectedGroupValues),
              },
            ]
          : []),
        { field: "__board_settings", direction: JSON.stringify(boardSettings) },
      ],
      has_layout: true,
      is_default: activeView.id === user?.default_saved_view_id,
    });
    await queryClient.invalidateQueries({ queryKey: ["saved-views"] });
    setLayoutDirty(false);
  };

  useEffect(() => {
    const key = `ticket-grid-scroll:${user?.id ?? "anonymous"}`;
    const saved = Number(sessionStorage.getItem(key) ?? 0);
    const frame = window.requestAnimationFrame(() =>
      window.scrollTo({ top: saved }),
    );
    const remember = () => sessionStorage.setItem(key, String(window.scrollY));
    window.addEventListener("beforeunload", remember);
    return () => {
      window.cancelAnimationFrame(frame);
      remember();
      window.removeEventListener("beforeunload", remember);
    };
  }, [user?.id]);

  useEffect(() => {
    const grid = ticketGridScrollRef.current;
    if (!grid || effectiveViewMode !== "GRID") {
      setFloatingGridScroll((current) => ({ ...current, visible: false }));
      return;
    }
    const updateFloatingScroll = () => {
      const rect = grid.getBoundingClientRect();
      const left = Math.max(0, rect.left);
      const right = Math.min(window.innerWidth, rect.right);
      setFloatingGridScroll({
        visible:
          grid.scrollWidth > grid.clientWidth + 1 &&
          rect.top < window.innerHeight &&
          rect.bottom > 0,
        left,
        width: Math.max(0, right - left),
        contentWidth: grid.scrollWidth,
      });
      if (floatingGridScrollRef.current)
        floatingGridScrollRef.current.scrollLeft = grid.scrollLeft;
    };
    const observer = new ResizeObserver(updateFloatingScroll);
    observer.observe(grid);
    if (grid.firstElementChild) observer.observe(grid.firstElementChild);
    window.addEventListener("resize", updateFloatingScroll);
    document.addEventListener("scroll", updateFloatingScroll, true);
    updateFloatingScroll();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateFloatingScroll);
      document.removeEventListener("scroll", updateFloatingScroll, true);
    };
  }, [columnWidths, effectiveViewMode, tickets.data?.items.length, visibleColumns]);

  useEffect(() => {
    if (defaultApplied) return;
    if (!layoutApplied) return;
    if (savedViews.isError) {
      setDefaultApplied(true);
      return;
    }
    if (!savedViews.data) return;
    const defaultView = savedViews.data.find(
      (view) => view.id === user?.default_saved_view_id,
    );
    if (defaultView) {
      const savedDateView = resolveSavedViewDates(
        JSON.parse(defaultView.filter_json) as Filters,
        today(),
      );
      const savedFilters = savedDateView.filters;
      setDateType(savedDateView.dateType);
      setDatePreset(savedDateView.datePreset);
      setFilters((current) => ({ ...current, ...savedFilters }));
      setVisibleFilterKeys(
        Array.from(
          new Set([
            ...defaultFilterKeys.filter(
              (key) => key !== "assigned_user_id" || canUseAssignmentFilters,
            ),
            ...Object.keys(savedFilters).filter(
              (key) => key !== "my_teams_only" && filterKeys.includes(key),
            ),
          ]),
        ),
      );
      if (defaultView.has_layout && defaultView.sort_json) {
        const savedSorts = JSON.parse(defaultView.sort_json) as Array<{
          field: string;
          direction: string;
        }>;
        const savedSort = savedSorts[0];
        if (savedSort) {
          setSortBy(savedSort.field);
          setSortDirection(savedSort.direction as "asc" | "desc");
        }
        setGroupBy(
          savedSorts.find((item) => item.field === "__group_by")?.direction ??
            "",
        );
        setViewMode(
          savedSorts.find((item) => item.field === "__view_mode")?.direction ===
            "CARDS"
            ? "CARDS"
            : "GRID",
        );
        const savedGroups = savedSorts.find(
          (item) => item.field === "__group_values",
        )?.direction;
        setSelectedGroupValues(
          savedGroups ? (JSON.parse(savedGroups) as string[]) : [],
        );
        setBoardSettings(
          parseBoardSettings(
            savedSorts.find((item) => item.field === "__board_settings")
              ?.direction,
          ),
        );
      }
      if (defaultView.has_layout && defaultView.columns_json) {
        const savedColumns = JSON.parse(defaultView.columns_json) as string[];
        if (savedColumns.length)
          setVisibleColumns(
            savedColumns.filter((column) =>
              (columnKeys as readonly string[]).includes(column),
            ),
          );
      }
      setActiveSavedViewId(defaultView.id);
    }
    setDefaultApplied(true);
  }, [
    canUseAssignmentFilters,
    defaultApplied,
    layoutApplied,
    savedViews.data,
    savedViews.isError,
    user?.default_saved_view_id,
  ]);

  useEffect(() => {
    if (!defaultApplied || !layoutApplied) return;
    // Let URL synchronization and the default saved-view effect finish in the
    // current render cycle before the first ticket request. Otherwise an
    // unfiltered request can briefly render all tickets before the effective
    // date preset (normally Today) is applied.
    const frame = window.requestAnimationFrame(() => setTicketQueryReady(true));
    return () => window.cancelAnimationFrame(frame);
  }, [defaultApplied, layoutApplied]);
  const saveView = useMutation({
    mutationFn: async () => {
      const payload = {
        name: viewName.trim(),
        scope: viewScope,
        team_id: viewScope === "TEAM" ? Number(viewTeamId) : null,
        department_id: viewScope === "DEPARTMENT" ? user?.department_id : null,
        filters: {
          ...activeFilters,
          [savedDateTypeKey]: dateType,
          [savedDatePresetKey]: datePreset,
        },
        columns: visibleColumns,
        sort: [
          { field: sortBy, direction: sortDirection },
          ...(groupBy ? [{ field: "__group_by", direction: groupBy }] : []),
          { field: "__view_mode", direction: viewMode },
          ...(selectedGroupValues.length
            ? [
                {
                  field: "__group_values",
                  direction: JSON.stringify(selectedGroupValues),
                },
              ]
            : []),
          {
            field: "__board_settings",
            direction: JSON.stringify(boardSettings),
          },
        ],
        has_layout: saveViewLayout,
        is_default: makeDefault,
      };
      return editingViewId
        ? api.put(`/saved-views/${editingViewId}`, payload)
        : api.post("/saved-views", payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-views"] });
      await refreshPermissions();
      setSaveOpen(false);
      setViewName("");
      setMakeDefault(false);
      setViewScope("PRIVATE");
      setViewTeamId("");
      setEditingViewId(null);
      setSaveViewLayout(false);
    },
  });
  const deleteSavedView = useMutation({
    mutationFn: async (id: number) => api.delete(`/saved-views/${id}`),
    onSuccess: async (_, id) => {
      if (activeSavedViewId === id) setActiveSavedViewId(null);
      await queryClient.invalidateQueries({ queryKey: ["saved-views"] });
      await refreshPermissions();
    },
  });
  const makeDefaultView = useMutation({
    mutationFn: async (id: number) => api.patch(`/saved-views/${id}/default`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-views"] });
      await refreshPermissions();
    },
  });
  const applySavedView = useCallback((view: SavedView) => {
    const savedDateView = resolveSavedViewDates(
      JSON.parse(view.filter_json) as Filters,
      today(),
    );
    const savedFilters = savedDateView.filters;
    setDateType(savedDateView.dateType);
    setDatePreset(savedDateView.datePreset);
    setFilters({
      ...Object.fromEntries(filterKeys.map((key) => [key, ""])),
      ...savedFilters,
    });
    // Date range is represented by the compact Date type + Period controls.
    // Do not duplicate every historical *_from/*_to field in the expanded panel.
    setVisibleFilterKeys(
      Object.keys(savedFilters).filter(
        (key) =>
          filterKeys.includes(key) &&
          !dateTypes.some(
            (type) => key === `${type}_from` || key === `${type}_to`,
          ),
      ),
    );
    if (view.has_layout) {
      const savedSorts = JSON.parse(view.sort_json || "[]") as Array<{
        field: string;
        direction: string;
      }>;
      const savedSort = savedSorts.find((item) => item.field !== "__group_by");
      if (savedSort) {
        setSortBy(savedSort.field);
        setSortDirection(savedSort.direction as "asc" | "desc");
      }
      setGroupBy(
        savedSorts.find((item) => item.field === "__group_by")?.direction ?? "",
      );
      setViewMode(
        savedSorts.find((item) => item.field === "__view_mode")?.direction ===
          "CARDS"
          ? "CARDS"
          : "GRID",
      );
      const savedGroups = savedSorts.find(
        (item) => item.field === "__group_values",
      )?.direction;
      setSelectedGroupValues(
        savedGroups ? (JSON.parse(savedGroups) as string[]) : [],
      );
      setBoardSettings(
        parseBoardSettings(
          savedSorts.find((item) => item.field === "__board_settings")
            ?.direction,
        ),
      );
      if (view.columns_json) {
        const savedColumns = JSON.parse(view.columns_json) as string[];
        if (savedColumns.length)
          setVisibleColumns(
            savedColumns.filter((column) =>
              (columnKeys as readonly string[]).includes(column),
            ),
          );
      }
    } else if (gridPreference.data) {
      const preference = gridPreference.data;
      if (preference.columns.length)
        setVisibleColumns(
          preference.columns.filter((column) =>
            (columnKeys as readonly string[]).includes(column),
          ),
        );
      setColumnWidths(preference.column_widths ?? {});
      setDensity(preference.density);
      setPageSize(preference.page_size);
      setSortBy(preference.sort_by);
      setSortDirection(preference.sort_direction);
      setGroupBy(preference.group_by);
      setViewMode(preference.default_view_mode);
      setSelectedGroupValues(preference.selected_group_values ?? []);
      setBoardSettings({
        ...defaultBoardSettings,
        ...(preference.board_settings ?? {}),
      });
    }
    setActiveSavedViewId(view.id);
    setPage(0);
  }, [gridPreference.data]);
  useEffect(() => {
    const requestedId =
      Number(searchParams.get("saved_view_id") || 0) ||
      requestedSavedViewIdRef.current;
    if (!requestedId || appliedRequestedViewRef.current === requestedId || !savedViews.data)
      return;
    const requested = savedViews.data.find((view) => view.id === requestedId);
    if (!requested) return;
    appliedRequestedViewRef.current = requestedId;
    applySavedView(requested);
  }, [applySavedView, savedViews.data, searchParams]);
  const applyDatePreset = (preset: DatePreset, type: DateType = dateType) => {
    setDatePreset(preset);
    const { from, to } = dateRangeForPreset(preset, today());
    setFilters((current) => ({
      ...current,
      ...Object.fromEntries(
        dateTypes.flatMap((key) => [
          [`${key}_from`, ""],
          [`${key}_to`, ""],
        ]),
      ),
      ...(preset === "custom"
        ? {}
        : { [`${type}_from`]: from, [`${type}_to`]: to }),
    }));
    setPage(0);
  };
  const editSavedView = (view: SavedView) => {
    setEditingViewId(view.id);
    setViewName(view.name);
    setViewScope(view.scope as "PRIVATE" | "TEAM" | "DEPARTMENT" | "GLOBAL");
    setViewTeamId(view.team_id ? String(view.team_id) : "");
    setMakeDefault(view.id === user?.default_saved_view_id);
    setSaveViewLayout(view.has_layout);
    setSaveOpen(true);
  };
  const selectedItems = () =>
    selectedIds.map((ticket_id) => {
      const ticket = tickets.data?.items.find((item) => item.id === ticket_id);
      return { ticket_id, expected_version: ticket?.version ?? 0 };
    });
  const bulkAssign = useMutation({
    mutationFn: async () =>
      api.post("/tickets/bulk-assignment", {
        items: selectedItems(),
        assigned_team: bulkTeam || null,
        assigned_user_id: bulkUser ? Number(bulkUser) : null,
        reason: bulkReason.trim() || null,
      }),
    onSuccess: async () => {
      setSelectedIds([]);
      setBulkOpen(false);
      setBulkTeam("");
      setBulkUser("");
      setBulkReason("");
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });
  const bulkStatusChange = useMutation({
    mutationFn: async () => {
      if (cardTransitionTicket) {
        const requestStatus = ticketCardRequestStatus(
          bulkStatus,
          cardCurrentStatus,
        );
        let transitionVersion = cardTransitionTicket.version;
        for (const file of cardResolutionAttachments) {
          const body = new FormData();
          body.append("file", file);
          await api.post(
            `/tickets/${cardTransitionTicket.id}/attachments`,
            body,
          );
          transitionVersion += 1;
        }
        return api.post(`/tickets/${cardTransitionTicket.id}/transition`, {
          to_status_code: requestStatus,
          reason: bulkReason.trim() || null,
          version: transitionVersion,
          resolution_service_ids: ["RESOLVED", "CLOSED"].includes(bulkStatus)
            ? cardResolutionServiceIds
            : [],
          resolution_summary: cardRequiresResolution ? bulkReason.trim() : null,
          root_cause_ids: cardRequiresResolution ? cardRootCauseIds : [],
          resolution_outcome_id:
            cardRequiresResolution && cardResolutionOutcomeId
              ? Number(cardResolutionOutcomeId)
              : null,
          permanent_fix_status:
            cardRequiresResolution && cardPermanentFixSummary
              ? cardPermanentFixStatus
              : null,
          permanent_fix_summary: cardRequiresResolution
            ? cardPermanentFixSummary.trim() || null
            : null,
          create_knowledge_article:
            cardRequiresResolution && cardCreateKnowledge,
          close_after_resolve:
            cardRequiresResolution &&
            (bulkStatus === "CLOSED" || cardCloseAfterResolve),
          pending_owner_user_id: bulkStatus.startsWith("PENDING_")
            ? Number(bulkPendingOwner || user?.id)
            : null,
          pending_follow_up_at:
            bulkStatus.startsWith("PENDING_") && bulkPendingFollowUp
              ? new Date(bulkPendingFollowUp).toISOString()
              : null,
          pending_responsible_party: bulkStatus.startsWith("PENDING_")
            ? bulkPendingParty
            : null,
        });
      }
      return api.post("/tickets/bulk-status", {
        items: selectedItems(),
        to_status_code: bulkStatus,
        reason: bulkReason.trim() || null,
        resolution_summary:
          bulkStatus === "RESOLVED" && bulkReason.trim()
            ? bulkReason.trim()
            : null,
        root_cause_summary:
          bulkStatus === "RESOLVED" && bulkReason.trim()
            ? bulkReason.trim()
            : null,
        pending_owner_user_id: bulkStatus.startsWith("PENDING_")
          ? Number(bulkPendingOwner || user?.id)
          : null,
        pending_follow_up_at:
          bulkStatus.startsWith("PENDING_") && bulkPendingFollowUp
            ? new Date(bulkPendingFollowUp).toISOString()
            : null,
        pending_responsible_party: bulkStatus.startsWith("PENDING_")
          ? bulkPendingParty
          : null,
      });
    },
    onSuccess: async () => {
      setSelectedIds([]);
      setStatusOpen(false);
      setChoosePendingStatus(false);
      setBulkStatus("");
      setBulkReason("");
      setBulkPendingOwner("");
      setBulkPendingFollowUp("");
      setBulkPendingParty("CUSTOMER");
      setCardTransitionTicket(null);
      setCardResolutionServiceIds([]);
      setCardResolutionAttachments([]);
      setCardKnowledgeSearch("");
      setCardKnowledgeError("");
      setCardRootCauseIds([]);
      setCardResolutionOutcomeId("");
      setCardPermanentFixSummary("");
      setCardCreateKnowledge(false);
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });
  const moveTicketToStatus = useMutation({
    mutationFn: async ({
      ticket,
      statusCode,
    }: {
      ticket: Ticket;
      statusCode: string;
    }) =>
      api.post(`/tickets/${ticket.id}/transition`, {
        to_status_code: statusCode,
        reason:
          statusCode === "RESOLVED" ? null : "Moved from ticket card board",
        version: ticket.version,
      }),
    onMutate: async ({ ticket, statusCode }) => {
      await queryClient.cancelQueries({ queryKey: ["tickets"] });
      const snapshots = queryClient.getQueriesData<{
        items: Ticket[];
        total: number;
      }>({ queryKey: ["tickets"] });
      const target = statuses.data?.find(
        (status) => status.code === statusCode,
      );
      if (target)
        queryClient.setQueriesData<{ items: Ticket[]; total: number }>(
          { queryKey: ["tickets"] },
          (current) =>
            current
              ? {
                  ...current,
                  items: current.items.map((item) =>
                    item.id === ticket.id
                      ? { ...item, status_id: target.id }
                      : item,
                  ),
                }
              : current,
        );
      return { snapshots };
    },
    onError: (_error, _variables, context) =>
      context?.snapshots.forEach(([key, data]) =>
        queryClient.setQueryData(key, data),
      ),
    onSettled: async () =>
      queryClient.invalidateQueries({ queryKey: ["tickets"] }),
  });
  const bulkDelete = useMutation({
    mutationFn: async () =>
      api.post("/tickets/bulk-delete", {
        ticket_ids: selectedIds,
        reason: bulkReason.trim(),
      }),
    onSuccess: async () => {
      setSelectedIds([]);
      setDeleteOpen(false);
      setBulkReason("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tickets"] }),
        queryClient.invalidateQueries({
          queryKey: ["ticket-deletion-requests"],
        }),
      ]);
    },
  });
  const decideDeletion = useMutation({
    mutationFn: async ({
      id,
      decision,
      comment,
    }: {
      id: number;
      decision: "APPROVED" | "REJECTED";
      comment: string;
    }) =>
      api.post(`/tickets/deletion-requests/${id}/decision`, {
        decision,
        comment,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tickets"] }),
        queryClient.invalidateQueries({
          queryKey: ["ticket-deletion-requests"],
        }),
      ]);
    },
  });
  const restoreTicket = useMutation({
    mutationFn: async (ticket: Ticket) =>
      api.post(`/tickets/${ticket.id}/restore`, {
        version: ticket.version,
        reason: "Restored from the ticket Trash page.",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });
  const selfAssignTicketFromBoard = useMutation({
    mutationFn: async (ticket: Ticket) =>
      api.post<Ticket>(`/tickets/${ticket.id}/claim`, {
        version: ticket.version,
      }),
    onSuccess: async (response) => {
      setBoardMessage("");
      queryClient.setQueriesData<{ items: Ticket[]; total: number }>(
        { queryKey: ["tickets"] },
        (current) =>
          current
            ? {
                ...current,
                items: current.items.map((item) =>
                  item.id === response.data.id
                    ? { ...item, ...response.data }
                    : item,
                ),
              }
            : current,
      );
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
    onError: (cause) => {
      setBoardMessage(
        apiErrorMessage(
          cause,
          "The ticket could not be assigned to you. Refresh and try again.",
        ),
      );
    },
  });
  const remindApproval = useMutation({
    mutationFn: async (approvalId: number) =>
      api.post(`/entitlement-approvals/${approvalId}/reminder`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["entitlement-approvals"],
      });
      setPendingTicket(null);
    },
  });
  const decideApproval = useMutation({
    mutationFn: async ({
      approvalId,
      decision,
      comment,
    }: {
      approvalId: number;
      decision: "APPROVED" | "REJECTED";
      comment: string;
    }) =>
      api.post(`/entitlement-approvals/${approvalId}/decision`, {
        decision,
        comment,
      }),
    onSuccess: async () => {
      setPendingTicket(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tickets"] }),
        queryClient.invalidateQueries({ queryKey: ["entitlement-approvals"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
      ]);
    },
  });
  const selectedHasPendingApproval =
    tickets.data?.items.some(
      (ticket) =>
        selectedIds.includes(ticket.id) &&
        ticket.entitlement_status === "PENDING_APPROVAL",
    ) ?? false;
  const selectedApproval = pendingTicket
    ? approvals.data?.find((item) => item.ticket_id === pendingTicket.id)
    : undefined;
  const shareableTeams =
    supportTeams.data?.filter(
      (team) =>
        team.is_active &&
        (hasPermission("configuration.manage") ||
          team.leader_user_id === user?.id ||
          team.member_user_ids?.includes(user?.id ?? -1)),
    ) ?? [];
  async function exportTickets() {
    const response = await api.get("/reports/tickets.csv", {
      params: { ...activeFilters, columns: listColumns.join(",") },
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tickets-${serverDateInput()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const selectableFilterKeys = filterKeys.filter(
    (key) =>
      !hiddenFilterKeys.includes(key) &&
      !visibleFilterKeys.includes(key) &&
      ((key !== "assigned_user_id" && key !== "assigned_team") ||
        canUseAssignmentFilters),
  );
  const multiSelect = (
    key: string,
    label: string,
    options: Array<{ value: string; label: string }>,
    disabled = false,
  ) => {
    const selected = splitFilter(filters[key]);
    const labels = new Map(options.map((item) => [item.value, item.label]));
    return (
      <TextField
        size="small"
        fullWidth
        select
        label={label}
        value={selected}
        disabled={disabled}
        onChange={(event) =>
          updateFilter(
            key,
            (event.target.value as unknown as string[]).join(","),
          )
        }
        slotProps={{ inputLabel: { shrink: true } }}
        SelectProps={{
          multiple: true,
          displayEmpty: true,
          renderValue: (value) => {
            const values = value as string[];
            return values.length ? (
              values.map((item) => labels.get(item) ?? item).join(", ")
            ) : (
              <span style={{ color: "rgba(0, 0, 0, 0.6)" }}>
                {t("ticketsList.all")}
              </span>
            );
          },
        }}
      >
        {options.map((item) => (
          <MenuItem key={item.value} value={item.value}>
            <Checkbox size="small" checked={selected.includes(item.value)} />
            {item.label}
          </MenuItem>
        ))}
      </TextField>
    );
  };
  const renderFilter = (key: string) => {
    const common = { size: "small" as const, fullWidth: true };
    switch (key) {
      case "ticket_number":
        return (
          <TextField
            {...common}
            label={filterLabel(key)}
            value={filters.ticket_number}
            onChange={(e) => updateFilter("ticket_number", e.target.value)}
            helperText={t("ticketsList.ticketNumberHint")}
          />
        );
      case "search":
        return (
          <TextField
            {...common}
            label={filterLabel(key)}
            value={filters.search}
            onChange={(e) => updateFilter("search", e.target.value)}
            slotProps={{
              input: { startAdornment: <Search sx={{ marginInlineEnd: 1 }} /> },
            }}
          />
        );
      case "status_code":
        return multiSelect(
          key,
          filterLabel(key),
          statuses.data?.map((item) => ({
            value: item.code,
            label: getLocalizedName(item, language),
          })) ?? [],
        );
      case "priority":
        return multiSelect(
          key,
          filterLabel(key),
          ["P1", "P2", "P3", "P4"].map((item) => ({
            value: item,
            label: t(`priority.${item}`, { defaultValue: item }),
          })),
        );
      case "impact":
        return multiSelect(
          key,
          filterLabel(key),
          ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => ({
            value: item,
            label: t(`createTicket.${item.toLowerCase()}`),
          })),
        );
      case "urgency":
        return multiSelect(
          key,
          filterLabel(key),
          ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => ({
            value: item,
            label: t(`createTicket.${item.toLowerCase()}`),
          })),
        );
      case "patient_safety_flag":
      case "security_incident_flag":
        return (
          <TextField
            {...common}
            select
            label={filterLabel(key)}
            value={filters[key]}
            onChange={(event) => updateFilter(key, event.target.value)}
          >
            <MenuItem value="">{t("ticketsList.all")}</MenuItem>
            <MenuItem value="true">{t("ticketsList.yes")}</MenuItem>
            <MenuItem value="false">{t("ticketsList.no")}</MenuItem>
          </TextField>
        );
      case "client_id":
        return multiSelect(
          key,
          filterLabel(key),
          clients.data?.map((item) => ({
            value: String(item.id),
            label: item.name,
          })) ?? [],
        );
      case "branch_id":
        return multiSelect(
          key,
          filterLabel(key),
          branches.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
          !filters.client_id,
        );
      case "ticket_type_id":
        return multiSelect(
          key,
          filterLabel(key),
          types.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
        );
      case "product_id":
        return multiSelect(
          key,
          filterLabel(key),
          products.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
        );
      case "product_module_id":
        return multiSelect(
          key,
          filterLabel(key),
          modules.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
          !filters.product_id,
        );
      case "environment_id":
        return multiSelect(
          key,
          filterLabel(key),
          environments.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
        );
      case "service_id":
        return multiSelect(
          key,
          filterLabel(key),
          services.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
        );
      case "category_id":
        return multiSelect(
          key,
          filterLabel(key),
          categories.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
        );
      case "subcategory_id":
        return multiSelect(
          key,
          filterLabel(key),
          subcategories.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
          !filters.category_id,
        );
      case "root_cause_id":
        return multiSelect(
          key,
          filterLabel(key),
          rootCauses.data?.map((item) => ({
            value: String(item.id),
            label: getLocalizedName(item, language),
          })) ?? [],
        );
      case "entitlement_status":
        return multiSelect(
          key,
          filterLabel(key),
          [
            "PENDING_APPROVAL",
            "COVERED",
            "NO_CONTRACT",
            "NOT_COVERED",
            "EXCLUDED",
            "LIMIT_EXCEEDED",
            "OVERRIDDEN",
          ].map((item) => ({
            value: item,
            label: t(`ticketDetail.entitlement.${item}`, {
              defaultValue: item.replaceAll("_", " "),
            }),
          })),
        );
      case "source_channel":
        return multiSelect(
          key,
          filterLabel(key),
          [
            ["CLIENT_PORTAL", t("ticketsList.clientPortal")],
            ["NON_PORTAL", t("ticketsList.nonPortal")],
            ["WEB", t("ticketsList.originWeb")],
            ["PHONE", t("ticketsList.phoneCall")],
            ["EMAIL", t("ticketsList.email")],
            ["WALK_IN", t("ticketsList.walkIn")],
            ["MONITORING", t("ticketsList.monitoringAlert")],
            ["OTHER", t("ticketsList.other")],
          ].map(([value, label]) => ({ value, label })),
        );
      case "sla_state":
        return multiSelect(
          key,
          filterLabel(key),
          ["RUNNING", "PAUSED", "BREACHED", "COMPLETED"].map((item) => ({
            value: item,
            label: t(`ticketDetail.slaStates.${item}`, { defaultValue: item }),
          })),
        );
      case "routing_status":
        return multiSelect(
          key,
          filterLabel(key),
          ["NEW", "IN_PROGRESS", "RETURNED"].map((item) => ({
            value: item,
            label: t(`ticketDetail.routing.${item}`, {
              defaultValue: item.replaceAll("_", " "),
            }),
          })),
        );
      case "assigned_user_id":
        return multiSelect(
          key,
          filterLabel(key),
          assignees.data?.map((item) => ({
            value: String(item.id),
            label: item.full_name,
          })) ?? [],
        );
      case "created_by_user_id":
        return multiSelect(
          key,
          filterLabel(key),
          ticketFilterOptions.data?.creators.map((item) => ({
            value: String(item.id),
            label: item.name,
          })) ?? [],
        );
      case "department_id":
        return multiSelect(
          key,
          filterLabel(key),
          ticketFilterOptions.data?.departments.map((item) => ({
            value: String(item.id),
            label: item.name,
          })) ?? [],
        );
      case "parent_department_id":
        return multiSelect(
          key,
          filterLabel(key),
          ticketFilterOptions.data?.departments
            .filter((item) =>
              ticketFilterOptions.data?.departments.some(
                (child) => child.parent_department_id === item.id,
              ),
            )
            .map((item) => ({ value: String(item.id), label: item.name })) ??
            [],
        );
      case "assigned_team":
        return multiSelect(
          key,
          t("ticketsList.supportTeam"),
          supportTeams.data
            ?.filter((item) => item.is_active)
            .map((item) => ({ value: item.name, label: item.name })) ?? [],
        );
      default: {
        const isDateTimeFilter = key.endsWith("_from") || key.endsWith("_to");
        return (
          <TextField
            {...common}
            type={isDateTimeFilter ? "datetime-local" : "text"}
            label={filterLabel(key)}
            value={
              isDateTimeFilter
                ? dateTimeInputValue(
                    filters[key],
                    key.endsWith("_from") ? "from" : "to",
                  )
                : filters[key]
            }
            onChange={(e) => updateFilter(key, e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
        );
      }
    }
  };

  const catalogName = (
    items: Array<{ id: number; name: string; name_ar?: string }> | undefined,
    id?: number,
  ) => {
    const item = id ? items?.find((row) => row.id === id) : undefined;
    return item ? getLocalizedName(item, language) : id ? `#${id}` : "—";
  };
  const ticketRowStyle = (ticket: Ticket) => {
    if (ticket.entitlement_status === "PENDING_APPROVAL")
      return {
        bgcolor: "warning.light",
        borderInlineStart: "3px solid",
        borderColor: "warning.main",
      };
    if (
      ticket.sla_resolution_state === "BREACHED" ||
      (ticket.sla_overrun_minutes ?? 0) > 0
    )
      return { borderInlineStart: "3px solid", borderColor: "error.main" };
    if (ticket.priority === "P1")
      return { borderInlineStart: "3px solid", borderColor: "error.main" };
    const status = statuses.data?.find((item) => item.id === ticket.status_id);
    if (status?.color) {
      return {
        borderInlineStart: "3px solid",
        borderColor: status.color,
      };
    }
    return undefined;
  };
  const displayDate = (value?: string) =>
    value
      ? new Date(value).toLocaleString(language === "ar" ? "ar-EG" : "en-GB")
      : "—";
  const ticketValue = (ticket: Ticket, column: string) => {
    switch (column) {
      case "ticket_number":
        return (
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            flexWrap="nowrap"
          >
            <SemanticLink
              to={`/tickets/${ticket.id}`}
              state={ticketLinkState}
              fontWeight={800}
              sx={{
                whiteSpace: "nowrap",
                wordBreak: "normal",
                overflowWrap: "normal",
              }}
            >
              {ticket.ticket_number}
            </SemanticLink>
            {ticket.source_channel === "CLIENT_PORTAL" && (
              <Chip
                size="small"
                color="info"
                label={t("ticketsList.clientPortal")}
                sx={{ flexShrink: 0 }}
              />
            )}
            {ticket.is_uat_defect && (
              <Chip size="small" color="secondary" label="UAT Defect" sx={{ flexShrink: 0 }} />
            )}
          </Stack>
        );
      case "created_by":
        return ticket.created_by_name ?? `#${ticket.created_by_user_id}`;
      case "department":
        return ticket.department_name ?? "—";
      case "parent_department":
        return ticket.parent_department_name ?? "—";
      case "ticket_type":
        return catalogName(types.data, ticket.ticket_type_id);
      case "client":
        return (
          <Button
            size="small"
            variant="text"
            startIcon={<Business fontSize="small" />}
            onClick={(event) => {
              event.stopPropagation();
              setClientMenu({ anchor: event.currentTarget, ticket });
            }}
            sx={{
              justifyContent: "flex-start",
              textTransform: "none",
              fontWeight: 750,
              maxWidth: "100%",
            }}
          >
            {ticket.client_name ?? catalogName(clients.data, ticket.client_id)}
          </Button>
        );
      case "branch":
        return catalogName(branches.data, ticket.branch_id);
      case "requester":
      case "contact":
        return ticket.requester_contact_id ? (
          <Button
            size="small"
            variant="text"
            startIcon={<ContactPage fontSize="small" />}
            onClick={(event) => {
              event.stopPropagation();
              setContactMenu({ anchor: event.currentTarget, ticket });
            }}
            sx={{
              justifyContent: "flex-start",
              textTransform: "none",
              fontWeight: 750,
              maxWidth: "100%",
            }}
          >
            {ticket.requester_name ?? `Contact #${ticket.requester_contact_id}`}
          </Button>
        ) : (
          "—"
        );
      case "status": {
        const status = statuses.data?.find(
          (item) => item.id === ticket.status_id,
        );
        return (
          <Chip
            size="small"
            label={status ? getLocalizedName(status, language) : "—"}
            sx={{ bgcolor: status?.color ?? "#607D8B", color: "#fff" }}
          />
        );
      }
      case "flags":
        return ticket.active_flags?.length ? (
          <Stack direction="row" gap={0.5} flexWrap="wrap">
            {ticket.active_flags.map((flag) => (
              <Chip
                key={flag.id}
                size="small"
                icon={<Flag sx={{ color: "inherit !important" }} />}
                label={`${flag.name}${flag.pauses_sla ? " · SLA paused" : ""}`}
                sx={{ bgcolor: flag.color, color: "#fff", fontWeight: 750 }}
              />
            ))}
          </Stack>
        ) : (
          "—"
        );
      case "contract":
        return ticket.contract_id ? `#${ticket.contract_id}` : "—";
      case "assigned_engineer":
        return (
          assignees.data?.find((item) => item.id === ticket.assigned_user_id)
            ?.full_name ?? "—"
        );
      case "escalation_engineer":
        return (
          assignees.data?.find(
            (item) => item.id === ticket.escalation_assignee_user_id,
          )?.full_name ?? "—"
        );
      case "product":
        return catalogName(products.data, ticket.product_id);
      case "module":
        return catalogName(modules.data, ticket.product_module_id);
      case "environment":
        return catalogName(environments.data, ticket.environment_id);
      case "service":
        return catalogName(services.data, ticket.service_id);
      case "category":
        return (
          catalogName(categories.data, ticket.category_id) ||
          ticket.category ||
          "—"
        );
      case "subcategory":
        return catalogName(subcategories.data, ticket.subcategory_id);
      case "priority":
        return (
          <Chip
            size="small"
            color={priorityColor[ticket.priority as keyof typeof priorityColor]}
            label={t(`priority.${ticket.priority}`, {
              defaultValue: ticket.priority,
            })}
          />
        );
      case "shift_handover_status":
        return ticket.shift_handover_status ? (
          <Chip
            size="small"
            color={
              ticket.shift_handover_status === "PENDING" ? "warning" : "success"
            }
            label={ticket.shift_handover_status.replaceAll("_", " ")}
          />
        ) : (
          "—"
        );
      case "patient_safety_flag":
        return ticket.patient_safety_flag
          ? t("ticketsList.yes")
          : t("ticketsList.no");
      case "security_incident_flag":
        return ticket.security_incident_flag
          ? t("ticketsList.yes")
          : t("ticketsList.no");
      case "sla_resolution_target":
        return slaDuration(ticket.sla_resolution_target_minutes);
      case "sla_actual_business_time":
        return slaDuration(ticket.sla_actual_business_minutes);
      case "sla_time_balance":
        return !["RESOLVED", "CLOSED"].includes(
          statuses.data?.find((item) => item.id === ticket.status_id)?.code ??
            "",
        ) || ticket.sla_saved_minutes == null
          ? "—"
          : ticket.sla_saved_minutes >= 0
            ? t("ticketsList.saved", {
                duration: slaDuration(ticket.sla_saved_minutes),
              })
            : t("ticketsList.overrun", {
                duration: slaDuration(Math.abs(ticket.sla_saved_minutes)),
              });
      case "first_occurred_at":
      case "created_at":
      case "updated_at":
      case "resolved_at":
      case "closed_at":
      case "archived_at":
        return displayDate(
          ticket[column as keyof Ticket] as string | undefined,
        );
      default:
        return String(ticket[column as keyof Ticket] ?? "—");
    }
  };
  const groupLabel = (ticket: Ticket) => {
    switch (groupBy) {
      case "status": {
        const status = statuses.data?.find(
          (item) => item.id === ticket.status_id,
        );
        return status
          ? getLocalizedName(status, language)
          : t("ticketsList.unspecified");
      }
      case "priority":
        return ticket.priority
          ? t(`priority.${ticket.priority}`, { defaultValue: ticket.priority })
          : t("ticketsList.unspecified");
      case "assigned_engineer":
        return ticket.is_shared_assignment
          ? t("ticketsList.unassigned")
          : (assignees.data?.find((item) => item.id === ticket.assigned_user_id)
              ?.full_name ?? t("ticketsList.unassigned"));
      case "assigned_team":
        return ticket.assigned_team || t("ticketsList.unassigned");
      case "department":
        return ticket.department_name || t("ticketsList.noDepartment");
      case "client":
        return (
          ticket.client_name ??
          clients.data?.find((item) => item.id === ticket.client_id)?.name ??
          t("ticketsList.unknownClient")
        );
      case "source_channel":
        return ticket.source_channel
          ? t(`ticketsList.source.${ticket.source_channel}`, {
              defaultValue: ticket.source_channel.replaceAll("_", " "),
            })
          : t("ticketsList.unspecified");
      case "entitlement_status":
        return ticket.entitlement_status
          ? t(`ticketDetail.entitlement.${ticket.entitlement_status}`, {
              defaultValue: ticket.entitlement_status.replaceAll("_", " "),
            })
          : t("ticketsList.unspecified");
      default:
        return "";
    }
  };
  const groupValue = (ticket: Ticket) => {
    switch (groupBy) {
      case "status": {
        const effectiveStatusId = ticketStatusLaneId(
          ticket,
          statuses.data ?? [],
        );
        if (effectiveStatusId !== ticket.status_id)
          return String(effectiveStatusId);
        if (ticket.is_shared_assignment) {
          const status = statuses.data?.find(
            (item) => item.id === ticket.status_id,
          );
          const newStatus = statuses.data?.find((item) => item.code === "NEW");
          if (status?.code === "ASSIGNED" && newStatus)
            return String(newStatus.id);
        }
        return String(ticket.status_id);
      }
      case "priority":
        return ticket.priority || "__unspecified";
      case "assigned_engineer":
        return String(
          ticket.is_shared_assignment
            ? "__unassigned"
            : (ticket.assigned_user_id ?? "__unassigned"),
        );
      case "assigned_team":
        return ticket.assigned_team || "__unassigned";
      case "department":
        return String(ticket.department_id ?? "__none");
      case "client":
        return String(ticket.client_id ?? "__unknown");
      case "source_channel":
        return ticket.source_channel || "__unspecified";
      case "entitlement_status":
        return ticket.entitlement_status || "__unspecified";
      default:
        return "__all";
    }
  };
  const displayedTickets = effectiveGroupBy
    ? [...(tickets.data?.items ?? [])].sort((left, right) =>
        groupLabel(left).localeCompare(groupLabel(right)),
      )
    : (tickets.data?.items ?? []);
  const allCardGroups = (() => {
    if (groupBy === "status") {
      const catalog = statuses.data ?? [];
      const pendingStatuses = catalog.filter((status) =>
        isPendingStatusCode(status.code),
      );
      const groups = catalog
        .filter((status) => !isPendingStatusCode(status.code))
        .map((status) => ({
          key: String(status.id),
          label: getLocalizedName(status, language),
          statusCode: status.code,
          color: status.color,
          tickets: displayedTickets.filter(
            (ticket) => groupValue(ticket) === String(status.id),
          ),
        }));
      if (!pendingStatuses.length) return groups;
      const pendingGroup = {
        key: PENDING_BOARD_LANE_KEY,
        label: t("ticketsList.pendingLane", {
          defaultValue: "Waiting / Pending",
        }),
        statusCode: "PENDING",
        color: pendingStatuses[0]?.color,
        tickets: displayedTickets.filter(
          (ticket) => groupValue(ticket) === PENDING_BOARD_LANE_KEY,
        ),
      };
      const firstPendingIndex = catalog.findIndex((status) =>
        isPendingStatusCode(status.code),
      );
      const insertionIndex = catalog
        .slice(0, firstPendingIndex)
        .filter((status) => !isPendingStatusCode(status.code)).length;
      groups.splice(insertionIndex, 0, pendingGroup);
      return groups;
    }
    const groups = new Map<string, { label: string; tickets: Ticket[] }>();
    displayedTickets.forEach((ticket) => {
      const key = groupValue(ticket);
      const label = groupBy
        ? groupLabel(ticket)
        : t("ticketsList.allTickets", { defaultValue: "All tickets" });
      groups.set(key, {
        label,
        tickets: [...(groups.get(key)?.tickets ?? []), ticket],
      });
    });
    return Array.from(groups, ([key, group]) => ({
      key,
      label: group.label,
      tickets: group.tickets,
    }));
  })();
  const visibleCardGroups = selectedGroupValues.length
    ? allCardGroups.filter((group) =>
        selectedGroupValues.includes(String(group.key)),
      )
    : allCardGroups;
  const cardGroups = [...visibleCardGroups].sort((left, right) => {
    const leftIndex = boardSettings.laneOrder.indexOf(String(left.key));
    const rightIndex = boardSettings.laneOrder.indexOf(String(right.key));
    if (leftIndex < 0 && rightIndex < 0 && groupBy === "status") {
      const defaultOrder =
        defaultStatusLaneRank(
          "statusCode" in left ? String(left.statusCode) : undefined,
        ) -
        defaultStatusLaneRank(
          "statusCode" in right ? String(right.statusCode) : undefined,
        );
      if (defaultOrder !== 0) return defaultOrder;
    }
    return (
      (leftIndex < 0 ? 9999 : leftIndex) - (rightIndex < 0 ? 9999 : rightIndex)
    );
  });
  const orderedTickets = (items: Ticket[]) =>
    [...items].sort((left, right) => {
      const leftIndex = boardSettings.cardOrder.indexOf(left.id);
      const rightIndex = boardSettings.cardOrder.indexOf(right.id);
      return (
        (leftIndex < 0 ? 999999 : leftIndex) -
        (rightIndex < 0 ? 999999 : rightIndex)
      );
    });
  const pendingGroupLabel = (ticket: Ticket) => {
    const status = statuses.data?.find((item) => item.id === ticket.status_id);
    return status ? getLocalizedName(status, language) : "";
  };
  const orderedLaneTickets = (group: (typeof cardGroups)[number]) => {
    const ordered = orderedTickets(group.tickets);
    if (!("statusCode" in group) || group.statusCode !== "PENDING")
      return ordered;
    return [...ordered].sort((left, right) => {
      const leftCode =
        statuses.data?.find((item) => item.id === left.status_id)?.code ?? "";
      const rightCode =
        statuses.data?.find((item) => item.id === right.status_id)?.code ?? "";
      return leftCode.localeCompare(rightCode);
    });
  };
  const swimlaneLabel = (ticket: Ticket) => {
    if (boardSettings.swimlane === "priority")
      return t(`priority.${ticket.priority}`, {
        defaultValue: ticket.priority,
      });
    if (boardSettings.swimlane === "assigned_engineer")
      return (
        (!ticket.is_shared_assignment &&
          assignees.data?.find((item) => item.id === ticket.assigned_user_id)
            ?.full_name) ||
        t("ticketsList.unassigned")
      );
    if (boardSettings.swimlane === "client")
      return ticket.client_name ?? catalogName(clients.data, ticket.client_id);
    return "";
  };
  const openTicketAction = (
    action:
      | "status"
      | "history"
      | "assign"
      | "escalate"
      | "task"
      | "worklog"
      | "checklist"
      | "link"
      | "knowledge"
      | "template"
      | "mention"
      | "comment-public"
      | "comment-internal"
      | "handover"
      | "resolve",
  ) => {
    if (!rowMenu) return;
    openTicket(rowMenu.ticket.id, action);
    setRowMenu(null);
  };
  const prepareTicketReport = async (reportType: "TICKET" | "INCIDENT") => {
    if (!rowMenu) return;
    const selected = rowMenu.ticket;
    setRowMenu(null);
    try {
      const response = await api.post<{ id: number }>(
        `/ticket-reports/tickets/${selected.id}`,
        {
          report_type: reportType,
          title:
            reportType === "INCIDENT"
              ? `Incident Report ${selected.ticket_number}`
              : `Ticket Report ${selected.ticket_number}`,
          data: {},
        },
      );
      await queryClient.invalidateQueries({ queryKey: ["ticket-reports"] });
      setQueueTab("reports");
      setSearchParams({ tab: "reports", report_id: String(response.data.id) });
    } catch (cause) {
      window.alert(apiErrorMessage(cause, "The report could not be prepared."));
    }
  };
  const openTicketWhatsApp = async () => {
    if (!rowMenu) return;
    const popup = window.open("about:blank", "_blank");
    const ticketId = rowMenu.ticket.id;
    setRowMenu(null);
    try {
      const result = (
        await api.get<{ url: string }>(`/tickets/${ticketId}/whatsapp-contact`)
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
  const openContactWhatsApp = async (ticket: Ticket) => {
    setContactMenu(null);
    const popup = window.open("about:blank", "_blank");
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
  const copyContactInfo = async (ticket: Ticket) => {
    const lines = [
      ticket.requester_name,
      ticket.requester_job_title,
      ticket.requester_phone_number,
      ticket.requester_email,
    ].filter(Boolean);
    await navigator.clipboard.writeText(lines.join("\n"));
    setContactMenu(null);
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 0,
        minWidth: 0,
        overflow: "hidden",
        bgcolor: "transparent",
      }}
    >
      <Paper variant="outlined" sx={{ mb: 1.5, overflow: "hidden" }}>
        <Tabs
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          value={queueTab}
          onChange={(
            _,
            value:
              | "all"
              | "pre-tickets"
              | "escalations"
              | "handovers"
              | "approvals"
              | "reports"
              | "trash",
          ) => {
            setQueueTab(value);
            setSelectedIds([]);
            setPage(0);
            if (value === "escalations") selectEscalationQueue("received");
            else
              setFilters((current) => ({
                ...current,
                my_department_requests: "",
                department_requests_only: "",
                escalations_sent_only: "",
                routing_status: "",
                entitlement_status: "",
                ...(value === "all"
                  ? { created_from: today(), created_to: today() }
                  : { created_from: "", created_to: "" }),
              }));
          }}
          sx={{
            px: { xs: 0.5, sm: 1 },
            minHeight: 44,
            bgcolor: "background.paper",
            "& .MuiTab-root": {
              minHeight: 44,
              py: 0.75,
              textTransform: "none",
              fontWeight: 750,
            },
          }}
        >
          <Tab value="all" label={t("ticketsList.todayTickets")} />
          {canViewPreTickets && (
            <Tab
              value="pre-tickets"
              label={t("ticketsList.preTicketsCount", {
                count: preTicketActionCount.data ?? 0,
              })}
            />
          )}
          {hasPermission("ticket.view.department") && (
            <Tab value="escalations" label={t("ticketsList.escalations")} />
          )}
          <Tab value="handovers" label={t("ticketsList.shiftHandover")} />
          {(hasPermission("entitlement_approval.view") ||
            hasPermission("ticket.delete.approve")) && (
            <Tab
              value="approvals"
              label={t("ticketsList.approvalsCount", {
                count:
                  (approvals.data?.length ?? 0) +
                  (deletionRequests.data?.length ?? 0),
              })}
            />
          )}
          {hasPermission("report.export") && (
            <Tab value="reports" label="Reports" />
          )}
          {hasPermission("ticket.trash.view") && (
            <Tab
              value="trash"
              label={
                trashTab
                  ? t("ticketsList.trashCount", {
                      count: tickets.data?.total ?? 0,
                    })
                  : t("ticketsList.trash")
              }
            />
          )}
        </Tabs>
      </Paper>
      {preTicketsTab && <PreTicketsPage />}
      {reportsTab && <TicketReportsTab />}
      {!preTicketsTab && !reportsTab && (
        <>
          {approvalTab &&
            hasPermission("ticket.delete.approve") &&
            !!deletionRequests.data?.length && (
              <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" fontWeight={800}>
                  {t("ticketsList.pendingDeletionApprovals", {
                    count: deletionRequests.data.length,
                  })}
                </Typography>
                {deletionRequests.data.map((item) => (
                  <Stack
                    key={item.id}
                    direction={{ xs: "column", md: "row" }}
                    gap={1}
                    alignItems={{ md: "center" }}
                    py={1}
                  >
                    <Box flex={1}>
                      <Typography fontWeight={700}>
                        {item.ticket_number ??
                          t("ticketsList.ticketId", { id: item.ticket_id })}
                      </Typography>
                      {item.ticket_subject && (
                        <Typography>{item.ticket_subject}</Typography>
                      )}
                      <Typography variant="body2" color="text.secondary">
                        {item.reason} ·{" "}
                        {item.requested_by_name ??
                          t("ticketsList.unknownRequester")}
                      </Typography>
                    </Box>
                    <Button
                      color="error"
                      disabled={
                        decideDeletion.isPending ||
                        item.requested_by_user_id === user?.id
                      }
                      onClick={() =>
                        decideDeletion.mutate({
                          id: item.id,
                          decision: "REJECTED",
                          comment: t("ticketsList.deletionRejectedComment"),
                        })
                      }
                    >
                      {t("ticketsList.reject")}
                    </Button>
                    <Button
                      color="success"
                      variant="contained"
                      disabled={
                        decideDeletion.isPending ||
                        item.requested_by_user_id === user?.id
                      }
                      onClick={() =>
                        decideDeletion.mutate({
                          id: item.id,
                          decision: "APPROVED",
                          comment: t("ticketsList.deletionApprovedComment"),
                        })
                      }
                    >
                      {t("ticketsList.approveDeletion")}
                    </Button>
                  </Stack>
                ))}
              </Paper>
            )}
          {queueTab === "escalations" && (
            <Tabs
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
              value={escalationQueue}
              onChange={(_, value: "received" | "sent" | "returned") =>
                selectEscalationQueue(value)
              }
              sx={{ mb: 2 }}
            >
              <Tab value="received" label={t("ticketsList.received")} />
              <Tab value="sent" label={t("ticketsList.sent")} />
              <Tab value="returned" label={t("ticketsList.returned")} />
            </Tabs>
          )}
          <Box
            sx={{
              display: { xs: "block", xl: "grid" },
              gridTemplateColumns: {
                xl: "minmax(0, 1fr)",
              },
              gap: { xl: 1 },
              alignItems: "stretch",
            }}
          >
          {showLegacyFastActionPanel && (
            <Paper
              variant="outlined"
              sx={{
                px: 1.25,
                py: 1,
                mb: 1,
                borderRadius: 2,
                overflowX: { xs: "auto", md: "visible" },
                bgcolor: "action.hover",
              }}
            >
              <Stack
                direction="row"
                gap={0.75}
                alignItems="center"
                flexWrap={{ xs: "nowrap", md: "wrap" }}
                sx={{
                  width: { xs: "max-content", md: "auto" },
                  "& .MuiButton-root": {
                    minHeight: 32,
                    py: 0.4,
                    px: 1,
                    fontSize: "0.75rem",
                    lineHeight: 1.25,
                    whiteSpace: "nowrap",
                    borderRadius: 1.5,
                  },
                }}
              >
                <Typography
                  variant="body2"
                  fontWeight={850}
                  color="text.secondary"
                  sx={{ marginInlineEnd: 0.5, whiteSpace: "nowrap" }}
                >
                  {t("ticketsList.fastActions")}
                </Typography>
                <Button
                  variant={
                    filters.created_from === today() &&
                    filters.created_to === today() &&
                    !filters.open_only &&
                    !filters.assigned_user_id
                      ? "contained"
                      : "outlined"
                  }
                  onClick={() =>
                    applyFastAction({
                      created_from: today(),
                      created_to: today(),
                    })
                  }
                >
                  {t("ticketsList.todayTickets")}
                </Button>
                {hasPermission("ticket.assign.team") && (
                  <Button
                    color="warning"
                    variant={
                      filters.unassigned_only === "true"
                        ? "contained"
                        : "outlined"
                    }
                    onClick={() =>
                      applyFastAction({
                        created_from: today(),
                        created_to: today(),
                        unassigned_only: "true",
                      })
                    }
                  >
                    {t("ticketsList.todayUnassigned")}
                  </Button>
                )}
                {hasPermission("ticket.assign.self") && (
                  <Button
                    variant={
                      filters.assigned_user_id === String(user?.id) &&
                      filters.open_only === "true"
                        ? "contained"
                        : "outlined"
                    }
                    onClick={() => {
                      if (user)
                        applyFastAction({
                          assigned_user_id: String(user.id),
                          open_only: "true",
                        });
                    }}
                  >
                    {t("ticketsList.myQueue")}
                  </Button>
                )}
                {hasPermission("dashboard.online_engineers.view") && (
                  <Button variant="outlined" onClick={() => navigate("/")}>
                    {t("ticketsList.engineerQueues")}
                  </Button>
                )}
                <Button
                  variant={
                    filters.my_teams_only === "true" ? "contained" : "outlined"
                  }
                  onClick={() =>
                    applyFastAction({
                      my_teams_only:
                        filters.my_teams_only === "true" ? "" : "true",
                    })
                  }
                >
                  {t("ticketsList.myTeamTickets")}
                </Button>
                {hasPermission("ticket.view.department") && (
                  <Button
                    variant={
                      filters.my_department_requests === "true"
                        ? "contained"
                        : "outlined"
                    }
                    onClick={() =>
                      applyFastAction(
                        filters.my_department_requests === "true"
                          ? {}
                          : {
                              my_department_requests: "true",
                              department_requests_only: "true",
                            },
                      )
                    }
                  >
                    {t("ticketsList.myDepartmentRequests")}
                  </Button>
                )}
                {hasPermission("ticket.view.team") && (
                  <Button
                    color="warning"
                    variant={
                      filters.due_soon === "true" ? "contained" : "outlined"
                    }
                    onClick={() => applyFastAction({ due_soon: "true" })}
                  >
                    {t("ticketsList.dueSoon")}
                  </Button>
                )}
                {hasPermission("ticket.view.team") && (
                  <Button
                    color="error"
                    variant={
                      filters.breached_only === "true"
                        ? "contained"
                        : "outlined"
                    }
                    onClick={() => applyFastAction({ breached_only: "true" })}
                  >
                    {t("ticketsList.slaBreached")}
                  </Button>
                )}
                <Button
                  color="success"
                  variant={
                    filters.status_code === "RESOLVED" &&
                    filters.assigned_user_id === String(user?.id ?? "")
                      ? "contained"
                      : "outlined"
                  }
                  onClick={() => {
                    if (!user) return;
                    applyFastAction({
                      status_code: "RESOLVED",
                      assigned_user_id: String(user.id),
                      incomplete_resolution_only: "true",
                    });
                    setSortBy("resolved_at");
                    setSortDirection("asc");
                  }}
                >
                  {t("ticketsList.resolvedAwaitingClosure")}
                </Button>
                {hasPermission("report.export") && (
                  <Button startIcon={<Download />} onClick={exportTickets}>
                    {t("ticketsList.exportCsv")}
                  </Button>
                )}
              </Stack>
            </Paper>
          )}
          </Box>
          {!trashTab && (
            <Paper
              variant="outlined"
              sx={{
                p: { xs: 0.75, md: 1 },
                mb: 1,
                borderRadius: 1.5,
                bgcolor: "background.paper",
                display: { xs: "block", lg: "flex" },
                alignItems: { lg: "center" },
                gap: { lg: 0.5 },
                overflowX: { lg: "auto" },
                "& .MuiInputBase-root": {
                  minHeight: 36,
                  fontSize: "0.8125rem",
                },
                "& .MuiInputLabel-root": {
                  fontSize: "0.8125rem",
                },
                "& .MuiFormHelperText-root": {
                  mt: 0.25,
                  mx: 0.5,
                  fontSize: "0.6875rem",
                  lineHeight: 1.2,
                },
                "& .MuiButton-root": {
                  minHeight: 32,
                  px: 1,
                  fontSize: "0.75rem",
                },
                "& .MuiChip-root": {
                  height: 26,
                  fontSize: "0.75rem",
                },
              }}
            >
              <Stack
                direction={{ xs: "column", md: "row" }}
                spacing={0.5}
                mb={{ xs: 0.5, lg: 0 }}
                alignItems={{ md: "center" }}
                sx={{ flexShrink: 0 }}
              >
                <TextField
                  size="small"
                  placeholder={t("ticketsList.search", {
                    defaultValue: "Search tickets",
                  })}
                  value={filters.search}
                  onChange={(event) => {
                    setFilters((current) => ({
                      ...current,
                      search: event.target.value,
                    }));
                    setPage(0);
                  }}
                  slotProps={{
                    input: {
                      startAdornment: (
                        <Search
                          fontSize="small"
                          sx={{ mr: 0.75, color: "text.secondary" }}
                        />
                      ),
                    },
                  }}
                  sx={{ minWidth: { xs: "100%", md: 220 } }}
                />
                <TextField
                  select
                  size="small"
                  label={t("ticketsList.dateType")}
                  value={dateType}
                  onChange={(event) => {
                    const value = event.target.value as DateType;
                    setDateType(value);
                    applyDatePreset(datePreset, value);
                  }}
                  sx={{ minWidth: 120 }}
                >
                  <MenuItem value="created">
                    {t("ticketsList.dateCreated")}
                  </MenuItem>
                  <MenuItem value="updated">
                    {t("ticketsList.dateUpdated")}
                  </MenuItem>
                  <MenuItem value="assigned">
                    {t("ticketsList.dateAssigned")}
                  </MenuItem>
                  <MenuItem value="resolved">
                    {t("ticketsList.dateResolved")}
                  </MenuItem>
                  <MenuItem value="closed">
                    {t("ticketsList.dateClosed")}
                  </MenuItem>
                </TextField>
                <TextField
                  select
                  size="small"
                  label={t("ticketsList.period")}
                  value={datePreset}
                  onChange={(event) =>
                    applyDatePreset(event.target.value as DatePreset)
                  }
                  sx={{ minWidth: 120 }}
                >
                  <MenuItem value="today">Today</MenuItem>
                  <MenuItem value="yesterday">
                    {t("ticketsList.yesterday")}
                  </MenuItem>
                  <MenuItem value="this_week">
                    {t("ticketsList.thisWeek")}
                  </MenuItem>
                  <MenuItem value="last_week">
                    {t("ticketsList.lastWeek")}
                  </MenuItem>
                  <MenuItem value="this_month">
                    {t("ticketsList.thisMonth")}
                  </MenuItem>
                  <MenuItem value="last_month">
                    {t("ticketsList.lastMonth")}
                  </MenuItem>
                  <MenuItem value="custom">
                    {t("ticketsList.customDate")}
                  </MenuItem>
                  <MenuItem value="all">{t("ticketsList.allTime")}</MenuItem>
                </TextField>
                {datePreset === "custom" && (
                  <>
                    <TextField
                      size="small"
                      type="datetime-local"
                      label={t("ticketsList.from")}
                      value={dateTimeInputValue(
                        filters[`${dateType}_from`] ?? "",
                        "from",
                      )}
                      onChange={(event) =>
                        updateFilter(`${dateType}_from`, event.target.value)
                      }
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                    <TextField
                      size="small"
                      type="datetime-local"
                      label={t("ticketsList.to")}
                      value={dateTimeInputValue(
                        filters[`${dateType}_to`] ?? "",
                        "to",
                      )}
                      onChange={(event) =>
                        updateFilter(`${dateType}_to`, event.target.value)
                      }
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                  </>
                )}
              </Stack>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={0.5}
                alignItems={{ sm: "center" }}
                sx={{ flexGrow: 1, minWidth: 0 }}
              >
                <Button
                  variant={filtersOpen ? "contained" : "outlined"}
                  color="primary"
                  startIcon={<FilterAlt />}
                  endIcon={filtersOpen ? <ExpandLess /> : <ExpandMore />}
                  aria-expanded={filtersOpen}
                  aria-controls="ticket-filters-panel"
                  sx={{
                    flexGrow: 1,
                    justifyContent: "flex-start",
                    minHeight: 34,
                    textTransform: "none",
                    fontWeight: 800,
                  }}
                  onClick={() => {
                    setPreviewTicket(null);
                    setFiltersOpen((value) => !value);
                  }}
                >
                  {filtersOpen
                    ? t("ticketsList.hideFilters", {
                        defaultValue: "Hide filters",
                      })
                    : t("ticketsList.showFilters", {
                        defaultValue: "Show and add filters",
                      })}
                  {Object.keys(activeFilters).length > 0 && (
                    <Chip
                      size="small"
                      color={filtersOpen ? "default" : "primary"}
                      label={t("ticketsList.activeCount", {
                        count: Object.keys(activeFilters).length,
                      })}
                      sx={{ marginInlineStart: 1 }}
                    />
                  )}
                </Button>
                <Button
                  size="small"
                  startIcon={<ViewColumn />}
                  onClick={() => setColumnsOpen(true)}
                  sx={{ display: dedicatedListTab ? "none" : undefined }}
                >
                  {t("ticketsList.columns")}
                </Button>
                <Button
                  size="small"
                  startIcon={<Save />}
                  onClick={() => {
                    setEditingViewId(null);
                    setViewName("");
                    setViewScope("PRIVATE");
                    setViewTeamId("");
                    setMakeDefault(false);
                    setSaveViewLayout(false);
                    setSaveOpen(true);
                  }}
                >
                  {t("ticketsList.saveView")}
                </Button>
                {Object.keys(activeFilters).length > 0 && (
                  <Button
                    size="small"
                    onClick={() => {
                      setDateType("created");
                      setDatePreset("today");
                      setFilters({
                        ...Object.fromEntries(
                          filterKeys.map((key) => [key, ""]),
                        ),
                        created_from: today(),
                        created_to: today(),
                      });
                      setVisibleFilterKeys(
                        defaultFilterKeys.filter(
                          (key) =>
                            key !== "assigned_user_id" ||
                            canUseAssignmentFilters,
                        ),
                      );
                      setPage(0);
                    }}
                  >
                    {t("ticketsList.resetFilters")}
                  </Button>
                )}
                {hasPermission("ticket.pre_ticket.create") && (
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<Add />}
                    onClick={() => navigate("/tickets/pre-tickets")}
                    sx={{ whiteSpace: "nowrap" }}
                  >
                    {t("preTickets.new")}
                  </Button>
                )}
                {hasPermission("ticket.create") && (
                  <Button
                    size="small"
                    variant="contained"
                    startIcon={<Add />}
                    onClick={() => navigate("/tickets/create")}
                    sx={{
                      whiteSpace: "nowrap",
                      boxShadow: 1,
                      position: { xs: "fixed", sm: "static" },
                      insetInlineEnd: { xs: 16, sm: "auto" },
                      bottom: { xs: 16, sm: "auto" },
                      zIndex: { xs: 8, sm: "auto" },
                      borderRadius: { xs: 99, sm: 1 },
                    }}
                  >
                    {t("ticketsList.createTicket")}
                  </Button>
                )}
              </Stack>
              <Drawer
                anchor="right"
                open={filtersOpen}
                onClose={() => setFiltersOpen(false)}
                slotProps={{
                  paper: {
                    sx: {
                      top: { xs: 56, sm: 64 },
                      height: {
                        xs: "calc(100% - 56px)",
                        sm: "calc(100% - 64px)",
                      },
                    },
                  },
                }}
              >
                <Box
                  id="ticket-filters-panel"
                  sx={{
                    width: { xs: "92vw", sm: 420 },
                    p: 1.5,
                    "& .MuiInputBase-root": {
                      minHeight: 36,
                      fontSize: "0.8125rem",
                    },
                    "& .MuiInputLabel-root": { fontSize: "0.8125rem" },
                    "& .MuiFormHelperText-root": {
                      mt: 0.25,
                      mx: 0.5,
                      fontSize: "0.6875rem",
                      lineHeight: 1.2,
                    },
                    "& .MuiButton-root": {
                      minHeight: 32,
                      px: 1,
                      fontSize: "0.75rem",
                    },
                    "& .MuiChip-root": {
                      height: 26,
                      fontSize: "0.75rem",
                    },
                  }}
                >
                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    mb={0.5}
                  >
                    <Box>
                      <Typography variant="h6" fontWeight={900}>
                        {t("ticketsList.filters", { defaultValue: "Filters" })}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {t("ticketsList.activeCount", {
                          count: Object.keys(activeFilters).length,
                        })}
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      aria-label={t("ticketsList.hideFilters", {
                        defaultValue: "Close filters",
                      })}
                      onClick={() => setFiltersOpen(false)}
                    >
                      <Close />
                    </IconButton>
                  </Stack>
                  <Divider />
                <Stack
                  direction="column"
                  spacing={0.5}
                  mt={1}
                  alignItems={{ sm: "center" }}
                >
                  <Button
                    variant={
                      filters.uat_defect_only === "true" &&
                      filters.open_only === "true"
                        ? "contained"
                        : "outlined"
                    }
                    color="secondary"
                    onClick={() =>
                      filters.uat_defect_only === "true" &&
                      filters.open_only === "true"
                        ? applyFastAction({
                            uat_defect_only: "",
                            open_only: "",
                          })
                        : applyFastAction({
                            uat_defect_only: "true",
                            open_only: "true",
                          })
                    }
                  >
                    Open UAT Defects
                  </Button>
                  <TextField
                    size="small"
                    label="UAT cycle"
                    value={filters.uat_cycle_code}
                    onChange={(event) =>
                      updateFilter("uat_cycle_code", event.target.value)
                    }
                    sx={{ minWidth: 145 }}
                  />
                  <TextField
                    size="small"
                    label="UAT release"
                    value={filters.uat_release_version}
                    onChange={(event) =>
                      updateFilter("uat_release_version", event.target.value)
                    }
                    sx={{ minWidth: 145 }}
                  />
                </Stack>
                <Stack
                  direction="row"
                  spacing={0.5}
                  mt={0.75}
                >
                  <TextField
                    select
                    size="small"
                    label={t("ticketsList.addFilter")}
                    value={filterToAdd}
                    onChange={(event) => setFilterToAdd(event.target.value)}
                    sx={{ minWidth: 175 }}
                  >
                    <MenuItem value="">
                      {t("ticketsList.chooseFilter")}
                    </MenuItem>
                    {selectableFilterKeys.map((key) => (
                      <MenuItem key={key} value={key}>
                        {filterLabel(key)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Button
                    variant="outlined"
                    startIcon={<Add />}
                    disabled={!filterToAdd}
                    onClick={() => {
                      setVisibleFilterKeys((current) => [
                        ...current,
                        filterToAdd,
                      ]);
                      setFilterToAdd("");
                    }}
                  >
                    {t("ticketsList.add")}
                  </Button>
                </Stack>
                {visibleFilterKeys.length === 0 && !filters.my_teams_only && (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    {t("ticketsList.noFilters")}
                  </Typography>
                )}
                {(visibleFilterKeys.length > 0 ||
                  Object.keys(activeFilters).length > 0) && (
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "minmax(0, 1fr)",
                      gap: 0.75,
                      mt: 1,
                    }}
                  >
                    {visibleFilterKeys.map((key) => (
                      <Paper
                        key={key}
                        variant="outlined"
                        sx={{
                          p: 0.5,
                          borderRadius: 1.25,
                          bgcolor: "background.paper",
                        }}
                      >
                        <Stack
                          direction="row"
                          spacing={0.375}
                          alignItems="center"
                        >
                          {renderFilter(key)}
                          <Button
                            size="small"
                            color="inherit"
                            onClick={() => removeFilter(key)}
                            sx={{ minWidth: "auto", px: 0.75 }}
                          >
                            {t("ticketsList.remove")}
                          </Button>
                        </Stack>
                      </Paper>
                    ))}
                    {filters.my_teams_only === "true" && (
                      <Chip
                        label={t("ticketsList.myTeamTickets")}
                        color="primary"
                        onDelete={() => updateFilter("my_teams_only", "")}
                        sx={{ justifySelf: "start" }}
                      />
                    )}
                    {filters.my_department_requests === "true" && (
                      <Chip
                        label={t("ticketsList.myDepartmentRequests")}
                        color="info"
                        onDelete={() => {
                          updateFilter("my_department_requests", "");
                          updateFilter("department_requests_only", "");
                        }}
                        sx={{ justifySelf: "start" }}
                      />
                    )}
                    {filters.open_only === "true" && (
                      <Chip
                        label={t("ticketsList.openTickets")}
                        color="primary"
                        sx={{ justifySelf: "start" }}
                      />
                    )}
                    {(filters.unassigned_only === "true" ||
                      filters.strictly_unassigned_only === "true") && (
                      <Chip
                        label={t("ticketsList.unassignedTickets")}
                        color="primary"
                        onDelete={() => {
                          updateFilter("unassigned_only", "");
                          updateFilter("strictly_unassigned_only", "");
                        }}
                        sx={{ justifySelf: "start" }}
                      />
                    )}
                    {filters.due_soon === "true" && (
                      <Chip
                        label={t("ticketsList.dueWithin")}
                        color="warning"
                        sx={{ justifySelf: "start" }}
                      />
                    )}
                    {filters.breached_only === "true" && (
                      <Chip
                        label={t("ticketsList.slaOverdue")}
                        color="error"
                        sx={{ justifySelf: "start" }}
                      />
                    )}
                  </Box>
                )}
                </Box>
              </Drawer>
            </Paper>
          )}
          {!trashTab && Object.keys(activeFilters).length > 0 && (
            <Stack
              direction="row"
              gap={0.5}
              mb={1}
              flexWrap="wrap"
              aria-label={t("ticketsList.activeFilters", {
                defaultValue: "Active filters",
              })}
            >
              {Object.entries(activeFilters)
                .filter(
                  ([key]) =>
                    !key.endsWith("_from") &&
                    !key.endsWith("_to") &&
                    key !== "entitlement_status",
                )
                .slice(0, 6)
                .map(([key, value]) => (
                  <Chip
                    key={key}
                    size="small"
                    label={`${filterLabel(key)}: ${String(value).replaceAll("_", " ")}`}
                    onDelete={() => removeActiveFilter(key)}
                  />
                ))}
              {Object.keys(activeFilters).length > 6 && (
                <Chip
                  size="small"
                  variant="outlined"
                  label={`+${Object.keys(activeFilters).length - 6}`}
                  onClick={() => setFiltersOpen(true)}
                />
              )}
            </Stack>
          )}
          {!preTicketsTab && !!savedViews.data?.length && (
            <Tabs
              value={activeSavedViewId ?? false}
              variant="scrollable"
              scrollButtons="auto"
              aria-label="Saved ticket views"
              sx={{
                minHeight: 34,
                mb: 1,
                borderBottom: 1,
                borderColor: "divider",
                "& .MuiTab-root": {
                  minHeight: 34,
                  py: 0.25,
                  px: 1.25,
                  textTransform: "none",
                },
              }}
            >
              {savedViews.data.map((view) => (
                <Tab
                  key={view.id}
                  value={view.id}
                  onClick={() => applySavedView(view)}
                  label={
                    <Stack direction="row" alignItems="center" gap={0.5}>
                      <span>
                        {view.name}
                        {view.id === user?.default_saved_view_id ? " ★" : ""}
                      </span>
                      {view.owner_user_id === user?.id && (
                        <Edit
                          fontSize="inherit"
                          onClick={(event) => {
                            event.stopPropagation();
                            editSavedView(view);
                          }}
                        />
                      )}
                    </Stack>
                  }
                />
              ))}
            </Tabs>
          )}
          {tickets.isLoading && <CircularProgress />}
          {tickets.isError && (
            <Alert severity="error">{t("ticketsList.loadFailed")}</Alert>
          )}
          {tickets.data?.items.length === 0 && (
            <Alert
              severity="info"
              variant="outlined"
              sx={{ py: 0.25, mb: 1, alignItems: "center" }}
              action={
                Object.keys(activeFilters).length ? (
                  <Button
                    size="small"
                    onClick={() => {
                      setDateType("created");
                      setDatePreset("today");
                      setFilters({
                        ...Object.fromEntries(
                          filterKeys.map((key) => [key, ""]),
                        ),
                        created_from: today(),
                        created_to: today(),
                      });
                      setPage(0);
                    }}
                  >
                    {t("ticketsList.resetFilters")}
                  </Button>
                ) : undefined
              }
            >
              {Object.keys(activeFilters).length
                ? t("ticketsList.noMatchingCompact", {
                    defaultValue:
                      "No matching tickets. Clear or adjust the current filters.",
                  })
                : t("ticketsList.noTicketsCompact", {
                    defaultValue: "There are no tickets in this view.",
                  })}
            </Alert>
          )}
          {tickets.data && (
            <>
              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={1}
                alignItems={{ xs: "stretch", lg: "center" }}
                mb={1}
              >
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ flexGrow: 1 }}
                >
                  {t("ticketsList.summary", {
                    total: tickets.data.total,
                    selected: selectedIds.length,
                  })}
                </Typography>
                {selectedIds.length > 0 &&
                  hasPermission("ticket.assign.team") && (
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={selectedHasPendingApproval}
                      title={
                        selectedHasPendingApproval
                          ? t("ticketsList.approvalBeforeAssignment")
                          : undefined
                      }
                      onClick={() => setBulkOpen(true)}
                    >
                      {t("ticketsList.bulkAssign")}
                    </Button>
                  )}
                {selectedIds.length > 0 &&
                  hasPermission("ticket.bulk.status") && (
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={selectedHasPendingApproval}
                      onClick={() => {
                        setBulkReason("");
                        setChoosePendingStatus(false);
                        setStatusOpen(true);
                      }}
                    >
                      {t("ticketsList.changeStatusCount", {
                        count: selectedIds.length,
                      })}
                    </Button>
                  )}
                {selectedIds.length > 0 &&
                  !trashTab &&
                  hasPermission("ticket.delete.request") && (
                    <Button
                      size="small"
                      color="error"
                      startIcon={<Delete />}
                      onClick={() => {
                        setBulkReason("");
                        setDeleteOpen(true);
                      }}
                    >
                      {t("ticketsList.deleteCount", {
                        count: selectedIds.length,
                      })}
                    </Button>
                  )}
                <TextField
                  select
                  size="small"
                  label={t("ticketsList.sort")}
                  value={sortBy}
                  onChange={(event) => {
                    setSortBy(event.target.value);
                    setLayoutDirty(true);
                    setPage(0);
                  }}
                >
                  <MenuItem value="updated_at">
                    {t("ticketsList.updated")}
                  </MenuItem>
                  <MenuItem value="created_at">
                    {t("ticketsList.created")}
                  </MenuItem>
                  <MenuItem value="priority">
                    {t("ticketsList.fields.priority")}
                  </MenuItem>
                  <MenuItem value="ticket_number">
                    {t("ticketsList.fields.ticket_number")}
                  </MenuItem>
                </TextField>
                <TextField
                  select
                  size="small"
                  label={t("ticketsList.direction")}
                  value={sortDirection}
                  onChange={(event) => {
                    setSortDirection(event.target.value as "asc" | "desc");
                    setLayoutDirty(true);
                    setPage(0);
                  }}
                >
                  <MenuItem value="desc">
                    {t("ticketsList.descending")}
                  </MenuItem>
                  <MenuItem value="asc">{t("ticketsList.ascending")}</MenuItem>
                </TextField>
                <TextField
                  select
                  size="small"
                  label={t("ticketsList.groupBy")}
                  value={groupBy}
                  onChange={(event) => {
                    setGroupBy(event.target.value);
                    setSelectedGroupValues([]);
                    setLayoutDirty(true);
                  }}
                  sx={{
                    minWidth: 170,
                    display: dedicatedListTab ? "none" : undefined,
                  }}
                >
                  <MenuItem value="">{t("ticketsList.noGrouping")}</MenuItem>
                  {[
                    "status",
                    "priority",
                    "assigned_engineer",
                    "assigned_team",
                    "department",
                    "client",
                    "source_channel",
                    "entitlement_status",
                  ].map((value) => (
                    <MenuItem key={value} value={value}>
                      {columnLabel(value, value)}
                    </MenuItem>
                  ))}
                </TextField>
                {!dedicatedListTab && viewMode === "CARDS" && groupBy && (
                  <Button
                    variant="outlined"
                    onClick={() => setGroupPickerOpen(true)}
                  >
                    {selectedGroupValues.length
                      ? t("ticketsList.selectedLanes", {
                          count: selectedGroupValues.length,
                          defaultValue: `${selectedGroupValues.length} lanes`,
                        })
                      : t("ticketsList.allLanes", {
                          defaultValue: "All lanes",
                        })}
                  </Button>
                )}
                {!dedicatedListTab && viewMode === "CARDS" && (
                  <IconButton
                    onClick={() => setBoardSettingsOpen(true)}
                    aria-label={t("ticketsList.boardSettings", {
                      defaultValue: "Board settings",
                    })}
                  >
                    <Settings />
                  </IconButton>
                )}
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  value={viewMode}
                  onChange={(_, value: TicketViewMode | null) => {
                    if (!value) return;
                    setViewMode(value);
                    setLayoutDirty(true);
                    if (value === "CARDS" && !groupBy) {
                      setGroupBy("status");
                      setSelectedGroupValues([]);
                    }
                  }}
                  aria-label={t("ticketsList.viewMode", {
                    defaultValue: "Ticket view",
                  })}
                  sx={{ display: dedicatedListTab ? "none" : undefined }}
                >
                  <ToggleButton
                    value="GRID"
                    aria-label={t("ticketsList.gridView", {
                      defaultValue: "Grid view",
                    })}
                  >
                    <TableRows fontSize="small" />
                  </ToggleButton>
                  <ToggleButton
                    value="CARDS"
                    aria-label={t("ticketsList.cardView", {
                      defaultValue: "Card view",
                    })}
                  >
                    <ViewKanban fontSize="small" />
                  </ToggleButton>
                </ToggleButtonGroup>
                <Button
                  startIcon={<Save />}
                  variant={layoutDirty ? "contained" : "outlined"}
                  disabled={saveGridPreference.isPending}
                  onClick={() => void persistCurrentLayout()}
                  sx={{ display: dedicatedListTab ? "none" : undefined }}
                >
                  {t("ticketsList.saveLayout", { defaultValue: "Save layout" })}
                </Button>
                <Button
                  variant="outlined"
                  disabled={saveGridPreference.isPending}
                  onClick={() => persistGridLayout(viewMode)}
                  sx={{ display: dedicatedListTab ? "none" : undefined }}
                >
                  {t("ticketsList.setDefaultLayout", {
                    defaultValue: "Set as default layout",
                  })}
                </Button>
              </Stack>
              {effectiveViewMode === "CARDS" && (
                <>
                  {moveTicketToStatus.isError && (
                    <Alert severity="error" sx={{ mb: 1 }}>
                      {t("ticketsList.statusChangeFailed", {
                        defaultValue:
                          "The ticket could not be moved. Refresh and try again.",
                      })}
                    </Alert>
                  )}
                  {groupBy === "status" &&
                    !hasPermission("ticket.change.status") &&
                    !hasPermission("ticket.start.progress") &&
                    !hasPermission("ticket.assign.self") && (
                      <Alert severity="info" sx={{ mb: 1 }}>
                        {t("ticketsList.dragPermissionRequired", {
                          defaultValue:
                            "Cards are read-only because workflow permission is required to move them between lanes.",
                        })}
                      </Alert>
                    )}
                  {boardMessage && (
                    <Alert
                      severity="warning"
                      onClose={() => setBoardMessage("")}
                      sx={{ mb: 1 }}
                    >
                      {boardMessage}
                    </Alert>
                  )}
                  <Stack direction="row" gap={0.75} mb={1} flexWrap="wrap">
                    <Chip
                      clickable
                      size="small"
                      label="P1"
                      color={filters.priority === "P1" ? "error" : "default"}
                      onClick={() =>
                        updateFilter(
                          "priority",
                          filters.priority === "P1" ? "" : "P1",
                        )
                      }
                    />
                    <Chip
                      clickable
                      size="small"
                      label={t("ticketsList.todayTickets")}
                      color={
                        filters.created_from === today() &&
                        filters.created_to === today() &&
                        !filters.open_only &&
                        !filters.assigned_user_id
                          ? "primary"
                          : "default"
                      }
                      onClick={() =>
                        applyFastAction({
                          created_from: today(),
                          created_to: today(),
                        })
                      }
                    />
                    {hasPermission("ticket.assign.team") && (
                      <Chip
                        clickable
                        size="small"
                        label={t("ticketsList.todayUnassigned")}
                        color={
                          filters.unassigned_only === "true"
                            ? "warning"
                            : "default"
                        }
                        onClick={() =>
                          applyFastAction({
                            created_from: today(),
                            created_to: today(),
                            unassigned_only: "true",
                          })
                        }
                      />
                    )}
                    {hasPermission("ticket.assign.self") && (
                      <Chip
                        clickable
                        size="small"
                        label={t("ticketsList.myQueue")}
                        color={
                          filters.assigned_user_id === String(user?.id) &&
                          filters.open_only === "true"
                            ? "primary"
                            : "default"
                        }
                        onClick={() =>
                          user &&
                          applyFastAction({
                            assigned_user_id: String(user.id),
                            open_only: "true",
                          })
                        }
                      />
                    )}
                    {hasPermission("dashboard.online_engineers.view") && (
                      <Chip
                        clickable
                        size="small"
                        label={t("ticketsList.engineerQueues")}
                        onClick={() => navigate("/")}
                      />
                    )}
                    <Chip
                      clickable
                      size="small"
                      label={t("ticketsList.myTeamTickets")}
                      color={filters.my_teams_only === "true" ? "primary" : "default"}
                      onClick={() => applyFastAction({ my_teams_only: "true" })}
                    />
                    {hasPermission("ticket.view.department") && (
                      <Chip
                        clickable
                        size="small"
                        label={t("ticketsList.myDepartmentRequests")}
                        color={
                          filters.my_department_requests === "true"
                            ? "primary"
                            : "default"
                        }
                        onClick={() =>
                          applyFastAction({
                            my_department_requests: "true",
                            department_requests_only: "true",
                          })
                        }
                      />
                    )}
                    {hasPermission("ticket.view.team") && (
                      <Chip
                        clickable
                        size="small"
                        label={t("ticketsList.dueSoon")}
                        color={filters.due_soon === "true" ? "warning" : "default"}
                        onClick={() => applyFastAction({ due_soon: "true" })}
                      />
                    )}
                    {hasPermission("ticket.view.team") && (
                      <Chip
                        clickable
                        size="small"
                        label={t("ticketsList.slaBreached")}
                        color={filters.breached_only === "true" ? "error" : "default"}
                        onClick={() => applyFastAction({ breached_only: "true" })}
                      />
                    )}
                    <Chip
                      clickable
                      size="small"
                      label={t("ticketsList.resolvedAwaitingClosure")}
                      color={
                        filters.status_code === "RESOLVED" &&
                        filters.assigned_user_id === String(user?.id ?? "")
                          ? "success"
                          : "default"
                      }
                      onClick={() => {
                        if (!user) return;
                        applyFastAction({
                          status_code: "RESOLVED",
                          assigned_user_id: String(user.id),
                          incomplete_resolution_only: "true",
                        });
                        setSortBy("resolved_at");
                        setSortDirection("asc");
                      }}
                    />
                    {hasPermission("report.export") && (
                      <Chip
                        clickable
                        size="small"
                        icon={<Download />}
                        label={t("ticketsList.exportCsv")}
                        onClick={exportTickets}
                      />
                    )}
                  </Stack>
                  <Box
                    sx={{
                      display: "grid",
                      gridAutoFlow: "column",
                      gridAutoColumns: {
                        xs: "calc(100vw - 48px)",
                        sm: 320,
                        lg: 340,
                      },
                      gap: { xs: 1, sm: 1.25 },
                      overflowX: "auto",
                      overscrollBehaviorInline: "contain",
                      scrollSnapType: { xs: "x mandatory", md: "none" },
                      pb: 1.5,
                      alignItems: "start",
                      WebkitOverflowScrolling: "touch",
                    }}
                  >
                    {cardGroups.map((group) => (
                      <Paper
                        key={group.key}
                        variant="outlined"
                        title={
                          groupBy === "status" &&
                          "statusCode" in group &&
                          group.statusCode === "NEW" &&
                          hasPermission("ticket.create")
                            ? t("ticketsList.newLaneCreateHint", {
                                defaultValue: "Double-click to create a ticket",
                              })
                            : undefined
                        }
                        onDoubleClick={(event) => {
                          if (
                            (event.target as HTMLElement).closest(
                              "[data-ticket-card]",
                            )
                          )
                            return;
                          if (
                            groupBy === "status" &&
                            "statusCode" in group &&
                            group.statusCode === "NEW" &&
                            hasPermission("ticket.create")
                          )
                            navigate("/tickets/create");
                        }}
                        onDragOver={(event) => {
                          if (groupBy === "status" || draggedLaneKey)
                            event.preventDefault();
                        }}
                        onDrop={(event) => {
                          event.preventDefault();
                          if (draggedLaneKey) {
                            const target = String(group.key);
                            setBoardSettings((current) => {
                              const existing = current.laneOrder.length
                                ? current.laneOrder
                                : cardGroups.map((item) => String(item.key));
                              const next = existing.filter(
                                (key) => key !== draggedLaneKey,
                              );
                              next.splice(
                                Math.max(0, next.indexOf(target)),
                                0,
                                draggedLaneKey,
                              );
                              return { ...current, laneOrder: next };
                            });
                            setDraggedLaneKey(null);
                            return;
                          }
                          const droppedId =
                            Number(event.dataTransfer.getData("text/plain")) ||
                            draggedTicketId;
                          if (
                            groupBy !== "status" ||
                            !droppedId ||
                            !("statusCode" in group)
                          )
                            return;
                          const ticket = displayedTickets.find(
                            (item) => item.id === droppedId,
                          );
                          const isUnifiedPendingLane =
                            String(group.statusCode) === "PENDING";
                          const currentStatusCode = statuses.data?.find(
                            (item) => item.id === ticket?.status_id,
                          )?.code;
                          const pendingDefaultStatus = statuses.data?.find(
                            (item) => item.code === "PENDING_CLIENT",
                          );
                          const statusCode = isUnifiedPendingLane
                            ? (pendingDefaultStatus?.code ?? "PENDING_CLIENT")
                            : String(group.statusCode);
                          const targetStatusId = isUnifiedPendingLane
                            ? (pendingDefaultStatus?.id ?? ticket?.status_id ?? 0)
                            : Number(group.key);
                          if (ticket && ticketNeedsApprovalAttention(ticket)) {
                            setPendingTicket(ticket);
                            setDraggedTicketId(null);
                            return;
                          }
                          if (
                            ticket &&
                            !(
                              isUnifiedPendingLane &&
                              isPendingStatusCode(currentStatusCode)
                            ) &&
                            ticketCardNeedsStatusMove(
                              statusCode,
                              targetStatusId,
                              ticket,
                            )
                          ) {
                            const canMoveToLane =
                              statusCode === "IN_PROGRESS"
                                ? hasPermission("ticket.start.progress")
                                : statusCode === "ASSIGNED" &&
                                    (ticket?.is_shared_assignment ||
                                      !ticket?.assigned_user_id)
                                  ? hasPermission("ticket.assign.self")
                                  : hasPermission("ticket.change.status");
                            if (!canMoveToLane) {
                              setBoardMessage(
                                t("ticketsList.statusChangeFailed", {
                                  defaultValue:
                                    "You do not have permission to move this ticket to that lane.",
                                }),
                              );
                              setDraggedTicketId(null);
                              return;
                            }
                            const limit =
                              boardSettings.laneLimits[String(group.key)] || 0;
                            if (limit > 0 && group.tickets.length >= limit) {
                              setBoardMessage(
                                t("ticketsList.laneLimitReached", {
                                  name: group.label,
                                  count: limit,
                                  defaultValue: `${group.label} has reached its limit of ${limit}.`,
                                }),
                              );
                              setDraggedTicketId(null);
                              return;
                            }
                            const transitionMode = ticketCardDropMode(
                              statusCode,
                              ticket,
                              resolutionDetailsRequiredOnClose,
                            );
                            if (transitionMode === "self-assignment") {
                              selfAssignTicketFromBoard.mutate(ticket);
                              setDraggedTicketId(null);
                              return;
                            }
                            if (transitionMode === "status-dialog") {
                              setCardTransitionTicket(ticket);
                              setBulkStatus(statusCode);
                              setChoosePendingStatus(isUnifiedPendingLane);
                              setBulkReason("");
                              setBulkPendingOwner(String(user?.id ?? ""));
                              setBulkPendingFollowUp(
                                statusCode.startsWith("PENDING_")
                                  ? new Date(Date.now() + 24 * 60 * 60_000)
                                      .toISOString()
                                      .slice(0, 16)
                                  : "",
                              );
                              setBulkPendingParty(
                                statusCode === "PENDING_CLIENT"
                                  ? "CUSTOMER"
                                  : "MILLENSYS",
                              );
                              setCardResolutionServiceIds([]);
                              setCardResolutionAttachments([]);
                              setCardKnowledgeSearch(ticket.subject);
                              setCardKnowledgeError("");
                              setCardRootCauseIds([]);
                              setCardResolutionOutcomeId("");
                              setCardPermanentFixStatus("PLANNED");
                              setCardPermanentFixSummary("");
                              setCardCreateKnowledge(false);
                              setCardCloseAfterResolve(
                                Boolean(user?.auto_close_on_resolve),
                              );
                              setStatusOpen(true);
                            } else
                              moveTicketToStatus.mutate({ ticket, statusCode });
                          }
                          setDraggedTicketId(null);
                        }}
                        sx={{
                          bgcolor: "action.hover",
                          minHeight: 180,
                          p: { xs: 0.75, sm: 1 },
                          minWidth: 0,
                          overflow: "hidden",
                          scrollSnapAlign: { xs: "start", md: "none" },
                          cursor:
                            groupBy === "status" &&
                            "statusCode" in group &&
                            group.statusCode === "NEW" &&
                            hasPermission("ticket.create")
                              ? "copy"
                              : "default",
                        }}
                      >
                        <Stack
                          direction="row"
                          alignItems="center"
                          mb={1}
                          gap={{ xs: 0.5, sm: 1 }}
                          draggable
                          onDragStart={(event) => {
                            event.stopPropagation();
                            setDraggedLaneKey(String(group.key));
                            event.dataTransfer.setData(
                              "application/x-ticket-lane",
                              String(group.key),
                            );
                          }}
                          onDragEnd={() => setDraggedLaneKey(null)}
                          sx={{ cursor: "grab", minHeight: 40, minWidth: 0 }}
                        >
                          {"color" in group && (
                            <Box
                              sx={{
                                width: 8,
                                height: 8,
                                borderRadius: "50%",
                                bgcolor: group.color ?? "text.disabled",
                              }}
                            />
                          )}
                          <Typography
                            fontWeight={900}
                            noWrap
                            title={group.label}
                            sx={{ minWidth: 0, flex: 1 }}
                          >
                            {group.label}
                          </Typography>
                          <Chip
                            size="small"
                            color={
                              boardSettings.laneLimits[String(group.key)] > 0 &&
                              group.tickets.length >
                                boardSettings.laneLimits[String(group.key)]
                                ? "error"
                                : "default"
                            }
                            label={`${group.tickets.length}${boardSettings.laneLimits[String(group.key)] ? ` / ${boardSettings.laneLimits[String(group.key)]}` : ""}`}
                          />
                          <Chip
                            size="small"
                            color="error"
                            variant="outlined"
                            label={
                              group.tickets.filter(
                                (ticket) =>
                                  ticket.priority === "P1" ||
                                  ticket.sla_resolution_state === "BREACHED",
                              ).length
                            }
                            title={t("ticketsList.riskTickets", {
                              defaultValue: "SLA risk / P1",
                            })}
                            sx={{ display: { xs: "none", sm: "flex" } }}
                          />
                          <IconButton
                            size="small"
                            onClick={() =>
                              setBoardSettings((current) => ({
                                ...current,
                                collapsed: current.collapsed.includes(
                                  String(group.key),
                                )
                                  ? current.collapsed.filter(
                                      (key) => key !== String(group.key),
                                    )
                                  : [...current.collapsed, String(group.key)],
                              }))
                            }
                          >
                            {boardSettings.collapsed.includes(
                              String(group.key),
                            ) ? (
                              <ExpandMore />
                            ) : (
                              <ExpandLess />
                            )}
                          </IconButton>
                        </Stack>
                        {groupBy === "status" &&
                          "statusCode" in group &&
                          group.statusCode === "PENDING" && (
                            <Stack
                              direction="row"
                              gap={0.5}
                              mb={1}
                              flexWrap="wrap"
                            >
                              {(statuses.data ?? [])
                                .filter((status) =>
                                  isPendingStatusCode(status.code),
                                )
                                .map((status) => (
                                  <Chip
                                    key={status.id}
                                    size="small"
                                    variant="outlined"
                                    label={`${getLocalizedName(status, language)} · ${group.tickets.filter((ticket) => ticket.status_id === status.id).length}`}
                                    sx={{
                                      borderColor: status.color,
                                      maxWidth: "100%",
                                    }}
                                  />
                                ))}
                            </Stack>
                          )}
                        {groupBy === "status" &&
                          "statusCode" in group &&
                          group.statusCode === "NEW" &&
                          hasPermission("ticket.create") && (
                            <Typography
                              variant="caption"
                              color="primary"
                              display="block"
                              textAlign="center"
                              sx={{ mb: 1, fontWeight: 700 }}
                            >
                              {t("ticketsList.newLaneCreateHint", {
                                defaultValue: "Double-click to create a ticket",
                              })}
                            </Typography>
                          )}
                        {!boardSettings.collapsed.includes(
                          String(group.key),
                        ) && (
                          <Stack spacing={1}>
                            {orderedLaneTickets(group).map(
                              (ticket, cardIndex, laneTickets) => (
                                <Box key={ticket.id} sx={{ minWidth: 0 }}>
                                  {groupBy === "status" &&
                                    "statusCode" in group &&
                                    group.statusCode === "PENDING" &&
                                    (cardIndex === 0 ||
                                      laneTickets[cardIndex - 1].status_id !==
                                        ticket.status_id) && (
                                      <Divider
                                        textAlign="left"
                                        sx={{ my: 0.75 }}
                                      >
                                        <Typography
                                          variant="caption"
                                          fontWeight={900}
                                        >
                                          {pendingGroupLabel(ticket)}
                                        </Typography>
                                      </Divider>
                                    )}
                                  {boardSettings.swimlane &&
                                    (cardIndex === 0 ||
                                      swimlaneLabel(
                                        laneTickets[cardIndex - 1],
                                      ) !== swimlaneLabel(ticket)) && (
                                      <Divider
                                        textAlign="left"
                                        sx={{ my: 0.75 }}
                                      >
                                        <Typography
                                          variant="caption"
                                          fontWeight={900}
                                        >
                                          {swimlaneLabel(ticket)}
                                        </Typography>
                                      </Divider>
                                    )}
                                  <Paper
                                    data-ticket-card
                                    draggable={
                                      groupBy === "status" &&
                                      (hasPermission("ticket.change.status") ||
                                        hasPermission(
                                          "ticket.start.progress",
                                        ) ||
                                        hasPermission("ticket.assign.self"))
                                    }
                                    onDragStart={(event) => {
                                      setDraggedTicketId(ticket.id);
                                      event.dataTransfer.effectAllowed = "move";
                                      event.dataTransfer.setData(
                                        "text/plain",
                                        String(ticket.id),
                                      );
                                    }}
                                    onDragEnd={() => setDraggedTicketId(null)}
                                    onDragOver={(event) => {
                                      event.preventDefault();
                                    }}
                                    onDrop={(event) => {
                                      const sourceId =
                                        Number(
                                          event.dataTransfer.getData(
                                            "text/plain",
                                          ),
                                        ) || draggedTicketId;
                                      const source = displayedTickets.find(
                                        (item) => item.id === sourceId,
                                      );
                                      if (
                                        !source ||
                                        groupValue(source) !==
                                          String(group.key) ||
                                        source.id === ticket.id
                                      )
                                        return;
                                      event.preventDefault();
                                      event.stopPropagation();
                                      setBoardSettings((current) => {
                                        const base = current.cardOrder.length
                                          ? current.cardOrder
                                          : displayedTickets.map(
                                              (item) => item.id,
                                            );
                                        const next = base.filter(
                                          (id) => id !== source.id,
                                        );
                                        next.splice(
                                          Math.max(0, next.indexOf(ticket.id)),
                                          0,
                                          source.id,
                                        );
                                        return { ...current, cardOrder: next };
                                      });
                                    }}
                                    onContextMenu={(event) => {
                                      event.preventDefault();
                                      setRowMenu({
                                        ticket,
                                        mouseX: event.clientX + 2,
                                        mouseY: event.clientY - 6,
                                      });
                                    }}
                                    onDoubleClick={(event) => {
                                      event.stopPropagation();
                                      openTicket(ticket.id);
                                    }}
                                    onClick={(event) => {
                                      if (
                                        !(event.target as HTMLElement).closest(
                                          "a,button,input",
                                        )
                                      ) {
                                        if (
                                          ticketNeedsApprovalAttention(ticket)
                                        )
                                          setPendingTicket(ticket);
                                        else setPreviewTicket(ticket);
                                      }
                                    }}
                                    variant="outlined"
                                    sx={{
                                      ...ticketRowStyle(ticket),
                                      p:
                                        boardSettings.density === "COMPACT"
                                          ? 0.75
                                          : boardSettings.density === "DETAILED"
                                            ? 1.75
                                            : 1.25,
                                      position: "relative",
                                      cursor:
                                        groupBy === "status" &&
                                        (hasPermission(
                                          "ticket.change.status",
                                        ) ||
                                          hasPermission(
                                            "ticket.start.progress",
                                          ))
                                          ? "grab"
                                          : "pointer",
                                      bgcolor: "background.paper",
                                      transition:
                                        "transform .18s ease, box-shadow .18s ease, opacity .18s ease",
                                      opacity:
                                        draggedTicketId === ticket.id
                                          ? 0.55
                                          : 1,
                                      "&:hover": {
                                        transform: "translateY(-2px)",
                                        boxShadow: 4,
                                      },
                                      ...(ticket.sla_resolution_state ===
                                        "BREACHED" ||
                                      (ticket.sla_overrun_minutes ?? 0) > 0 ||
                                      ticket.priority === "P1"
                                        ? {
                                            animation:
                                              "ticketBoardAlert 1.5s ease-in-out infinite",
                                            "@keyframes ticketBoardAlert": {
                                              "0%,100%": {
                                                boxShadow:
                                                  "0 0 0 0 rgba(239,68,68,0)",
                                              },
                                              "50%": {
                                                boxShadow:
                                                  "0 0 0 4px rgba(239,68,68,.22), 0 8px 22px rgba(239,68,68,.18)",
                                              },
                                            },
                                            "@media (prefers-reduced-motion: reduce)":
                                              { animation: "none" },
                                          }
                                        : {}),
                                    }}
                                  >
                                    <Stack
                                      direction="row"
                                      gap={{ xs: 0.5, sm: 1 }}
                                      alignItems="flex-start"
                                      minWidth={0}
                                    >
                                      <Box minWidth={0} flex={1}>
                                        <SemanticLink
                                          to={`/tickets/${ticket.id}`}
                                          state={ticketLinkState}
                                          onClick={(event) => {
                                            if (
                                              ticketNeedsApprovalAttention(
                                                ticket,
                                              )
                                            ) {
                                              event.preventDefault();
                                              event.stopPropagation();
                                              setPendingTicket(ticket);
                                            }
                                          }}
                                          fontWeight={900}
                                          underline="hover"
                                          dir="ltr"
                                        >
                                          {ticket.ticket_number}
                                        </SemanticLink>
                                        {ticket.is_uat_defect && (
                                          <Chip size="small" color="secondary" label="UAT Defect" sx={{ mt: 0.5 }} />
                                        )}
                                        <Typography
                                          fontWeight={700}
                                          sx={{
                                            mt: 0.35,
                                            overflowWrap: "anywhere",
                                            lineHeight: 1.35,
                                            display: "-webkit-box",
                                            WebkitLineClamp:
                                              boardSettings.density ===
                                              "DETAILED"
                                                ? 3
                                                : 2,
                                            WebkitBoxOrient: "vertical",
                                            overflow: "hidden",
                                          }}
                                        >
                                          {ticket.subject}
                                        </Typography>
                                      </Box>
                                      <Checkbox
                                        size="small"
                                        sx={{ p: 0.75 }}
                                        checked={selectedIds.includes(
                                          ticket.id,
                                        )}
                                        onChange={(event) =>
                                          setSelectedIds((current) =>
                                            event.target.checked
                                              ? [
                                                  ...new Set([
                                                    ...current,
                                                    ticket.id,
                                                  ]),
                                                ]
                                              : current.filter(
                                                  (id) => id !== ticket.id,
                                                ),
                                          )
                                        }
                                      />
                                      <IconButton
                                        size="small"
                                        sx={{ p: 0.75 }}
                                        aria-label={t(
                                          "ticketsList.fastActionsFor",
                                          { number: ticket.ticket_number },
                                        )}
                                        onClick={(event) => {
                                          const box =
                                            event.currentTarget.getBoundingClientRect();
                                          setRowMenu({
                                            ticket,
                                            mouseX: box.left,
                                            mouseY: box.bottom,
                                          });
                                        }}
                                      >
                                        <MoreVert fontSize="small" />
                                      </IconButton>
                                    </Stack>
                                    {boardSettings.fields.includes(
                                      "client",
                                    ) && (
                                      <SemanticLink
                                        to={`/clients/${ticket.client_id}/profile`}
                                        variant="body2"
                                        color="text.secondary"
                                        underline="hover"
                                        noWrap
                                        sx={{ mt: 0.75, display: "block" }}
                                      >
                                        {ticket.client_name ??
                                          catalogName(
                                            clients.data,
                                            ticket.client_id,
                                          )}
                                      </SemanticLink>
                                    )}
                                    {boardSettings.fields.includes(
                                      "assigned_engineer",
                                    ) && (
                                      <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        noWrap
                                      >
                                        {String(
                                          ticketValue(
                                            ticket,
                                            "assigned_engineer",
                                          ),
                                        )}
                                      </Typography>
                                    )}
                                    <Stack
                                      direction="row"
                                      gap={0.5}
                                      mt={1}
                                      alignItems="center"
                                    >
                                      {boardSettings.fields.includes(
                                        "priority",
                                      ) && ticketValue(ticket, "priority")}
                                      {boardSettings.fields.includes(
                                        "status",
                                      ) && ticketValue(ticket, "status")}
                                      {boardSettings.fields.includes(
                                        "updated_at",
                                      ) && (
                                        <Typography
                                          variant="caption"
                                          color="text.secondary"
                                          ml="auto"
                                        >
                                          {displayDate(ticket.updated_at)}
                                        </Typography>
                                      )}
                                    </Stack>
                                    {boardSettings.density === "DETAILED" &&
                                      boardSettings.fields.includes(
                                        "description",
                                      ) && (
                                        <Typography
                                          variant="body2"
                                          color="text.secondary"
                                          sx={{ mt: 1 }}
                                          noWrap
                                        >
                                          {ticket.description || "—"}
                                        </Typography>
                                      )}
                                    {statuses.data
                                      ?.find(
                                        (item) => item.id === ticket.status_id,
                                      )
                                      ?.code?.startsWith("PENDING_") && (
                                      <Stack
                                        direction="row"
                                        gap={0.5}
                                        mt={1}
                                        flexWrap="wrap"
                                      >
                                        {hasPermission(
                                          "ticket.start.progress",
                                        ) && (
                                          <Button
                                            size="small"
                                            onClick={() =>
                                              openTicket(ticket.id, "start")
                                            }
                                          >
                                            {t("ticketsList.returnInProgress", {
                                              defaultValue:
                                                "Return to progress",
                                            })}
                                          </Button>
                                        )}
                                        {hasPermission(
                                          "ticket.change.status",
                                        ) &&
                                          statuses.data?.find(
                                            (item) =>
                                              item.id === ticket.status_id,
                                          )?.code === "PENDING_CLIENT" && (
                                            <Button
                                              size="small"
                                              color="success"
                                              onClick={() =>
                                                openTicket(ticket.id, "resolve")
                                              }
                                            >
                                              {t("ticketsList.resolve", {
                                                defaultValue: "Resolve",
                                              })}
                                            </Button>
                                          )}
                                        {(hasPermission("ticket.escalate") ||
                                          hasPermission(
                                            "ticket.help.request",
                                          )) && (
                                          <Button
                                            size="small"
                                            onClick={() =>
                                              openTicket(ticket.id, "escalate")
                                            }
                                          >
                                            {t("ticketsList.escalateHelp")}
                                          </Button>
                                        )}
                                        {hasPermission(
                                          "ticket.assign.team",
                                        ) && (
                                          <Button
                                            size="small"
                                            onClick={() =>
                                              openTicket(ticket.id, "handover")
                                            }
                                          >
                                            {t("ticketsList.handover", {
                                              defaultValue: "Hand over",
                                            })}
                                          </Button>
                                        )}
                                      </Stack>
                                    )}
                                  </Paper>
                                </Box>
                              ),
                            )}
                            {!group.tickets.length && (
                              <Typography
                                variant="body2"
                                color="text.secondary"
                                textAlign="center"
                                py={3}
                              >
                                {t("ticketsList.noTickets", {
                                  defaultValue: "No tickets",
                                })}
                              </Typography>
                            )}
                          </Stack>
                        )}
                      </Paper>
                    ))}
                  </Box>
                </>
              )}
              <Stack
                spacing={0.75}
                sx={{
                  display: {
                    xs: effectiveViewMode === "GRID" ? "flex" : "none",
                    md: "none",
                  },
                  pb: { xs: 8, sm: 0 },
                }}
              >
                {displayedTickets.map((ticket) => (
                  <Paper
                    key={`mobile-${ticket.id}`}
                    variant="outlined"
                    onClick={(event) => {
                      if (!(event.target as HTMLElement).closest("a,button,input"))
                        openTicket(ticket.id);
                    }}
                    sx={{
                      ...ticketRowStyle(ticket),
                      p: 1.25,
                      minHeight: 96,
                      cursor: "pointer",
                      "&:active": { bgcolor: "action.selected" },
                    }}
                  >
                    <Stack direction="row" alignItems="flex-start" gap={1}>
                      <Checkbox
                        size="small"
                        checked={selectedIds.includes(ticket.id)}
                        disabled={
                          ticket.entitlement_status === "PENDING_APPROVAL"
                        }
                        onChange={(event) =>
                          setSelectedIds((current) =>
                            event.target.checked
                              ? [...new Set([...current, ticket.id])]
                              : current.filter((id) => id !== ticket.id),
                          )
                        }
                      />
                      <Box minWidth={0} flex={1}>
                        <SemanticLink
                          to={`/tickets/${ticket.id}`}
                          state={ticketLinkState}
                          underline="hover"
                          fontWeight={800}
                          dir="ltr"
                        >
                          {ticket.ticket_number}
                        </SemanticLink>
                        {ticket.is_uat_defect && (
                          <Chip size="small" color="secondary" label="UAT Defect" sx={{ ml: 0.75 }} />
                        )}
                        <Typography
                          variant="body2"
                          fontWeight={700}
                          noWrap
                          title={ticket.subject}
                        >
                          {ticket.subject}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          noWrap
                          display="block"
                        >
                          {ticket.client_name ??
                            catalogName(clients.data, ticket.client_id)}{" "}
                          · {String(ticketValue(ticket, "assigned_engineer"))}
                        </Typography>
                        <Stack
                          direction="row"
                          gap={0.5}
                          mt={0.5}
                          alignItems="center"
                        >
                          {ticketValue(ticket, "status")}
                          {ticketValue(ticket, "priority")}
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            ml="auto"
                          >
                            {displayDate(ticket.updated_at)}
                          </Typography>
                        </Stack>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(event) => {
                          const box =
                            event.currentTarget.getBoundingClientRect();
                          setRowMenu({
                            ticket,
                            mouseX: box.left,
                            mouseY: box.bottom,
                          });
                        }}
                      >
                        <MoreVert fontSize="small" />
                      </IconButton>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
              <Box
                ref={ticketGridScrollRef}
                onScroll={(event) => {
                  if (floatingGridScrollRef.current)
                    floatingGridScrollRef.current.scrollLeft =
                      event.currentTarget.scrollLeft;
                }}
                sx={{
                  overflow: "auto",
                  display: {
                    xs: "none",
                    md: effectiveViewMode === "GRID" ? "block" : "none",
                  },
                  maxWidth: "100%",
                  maxHeight: {
                    xs: "calc(100dvh - 190px)",
                    md: "calc(100dvh - 220px)",
                  },
                  minHeight: 280,
                  overscrollBehavior: "contain",
                  scrollbarGutter: "stable",
                  WebkitOverflowScrolling: "touch",
                }}
              >
                <Table
                  stickyHeader
                  size="small"
                  sx={{
                    display: "table",
                    maxWidth: "none",
                    overflowX: "visible",
                    minWidth: { xs: 920, md: "100%" },
                    "& .MuiTableCell-root": {
                      py: listDensity === "COMPACT" ? 0.45 : 0.9,
                      px: listDensity === "COMPACT" ? 0.75 : 1.25,
                    },
                    "& tbody .MuiTableRow-root": {
                      height: listDensity === "COMPACT" ? 38 : 48,
                    },
                  }}
                >
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={tickets.data.items.every((item) =>
                            selectedIds.includes(item.id),
                          )}
                          indeterminate={
                            tickets.data.items.some((item) =>
                              selectedIds.includes(item.id),
                            ) &&
                            !tickets.data.items.every((item) =>
                              selectedIds.includes(item.id),
                            )
                          }
                          onChange={(event) =>
                            setSelectedIds(
                              event.target.checked
                                ? tickets
                                    .data!.items.filter(
                                      (item) =>
                                        item.entitlement_status !==
                                        "PENDING_APPROVAL",
                                    )
                                    .map((item) => item.id)
                                : [],
                            )
                          }
                        />
                      </TableCell>
                      {listColumns.map((column) => {
                        const sortable = [
                          "updated_at",
                          "created_at",
                          "priority",
                          "ticket_number",
                        ].includes(column);
                        return (
                          <TableCell
                            key={column}
                            draggable={!dedicatedListTab}
                            onDragStart={() => setDraggedColumn(column)}
                            onDragOver={(event) => event.preventDefault()}
                            onDrop={() => {
                              if (
                                dedicatedListTab ||
                                !draggedColumn ||
                                draggedColumn === column
                              )
                                return;
                              setVisibleColumns((current) => {
                                const next = current.filter(
                                  (item) => item !== draggedColumn,
                                );
                                next.splice(
                                  next.indexOf(column),
                                  0,
                                  draggedColumn,
                                );
                                return next;
                              });
                              setLayoutDirty(true);
                              setDraggedColumn(null);
                            }}
                            onClick={() => {
                              if (!sortable) return;
                              if (sortBy === column)
                                setSortDirection((current) =>
                                  current === "asc" ? "desc" : "asc",
                                );
                              else {
                                setSortBy(column);
                                setSortDirection("asc");
                              }
                              setPage(0);
                            }}
                            sx={{
                              whiteSpace: "nowrap",
                              cursor: dedicatedListTab
                                ? sortable
                                  ? "pointer"
                                  : "default"
                                : "grab",
                              fontWeight: 800,
                              position: "relative",
                              width: dedicatedListTab
                                ? undefined
                                : columnWidths[column],
                              minWidth: dedicatedListTab
                                ? 110
                                : (columnWidths[column] ?? 90),
                              maxWidth: dedicatedListTab
                                ? column === "subject" ||
                                  column === "shift_handover_reason" ||
                                  column === "archive_reason"
                                  ? 360
                                  : 240
                                : columnWidths[column],
                            }}
                          >
                            {columnLabel(
                              column,
                              availableColumns.find(
                                ([key]) => key === column,
                              )?.[1] ?? column,
                            )}
                            {sortBy === column
                              ? sortDirection === "asc"
                                ? " ↑"
                                : " ↓"
                              : ""}
                            {!dedicatedListTab && <Box
                              role="separator"
                              aria-orientation="vertical"
                              onClick={(event) => event.stopPropagation()}
                              onPointerDown={(event) => {
                                event.preventDefault();
                                event.stopPropagation();
                                const startX = event.clientX;
                                const startWidth =
                                  event.currentTarget.parentElement?.getBoundingClientRect()
                                    .width ??
                                  columnWidths[column] ??
                                  120;
                                const move = (moveEvent: PointerEvent) =>
                                  setColumnWidths((current) => ({
                                    ...current,
                                    [column]: Math.round(
                                      Math.max(
                                        80,
                                        Math.min(
                                          520,
                                          startWidth +
                                            moveEvent.clientX -
                                            startX,
                                        ),
                                      ),
                                    ),
                                  }));
                                const up = () => {
                                  setLayoutDirty(true);
                                  window.removeEventListener(
                                    "pointermove",
                                    move,
                                  );
                                  window.removeEventListener("pointerup", up);
                                };
                                window.addEventListener("pointermove", move);
                                window.addEventListener("pointerup", up);
                              }}
                              sx={{
                                position: "absolute",
                                insetInlineEnd: -4,
                                top: 0,
                                bottom: 0,
                                width: 9,
                                cursor: "col-resize",
                                zIndex: 2,
                                "&:hover": { bgcolor: "primary.main" },
                              }}
                            />}
                          </TableCell>
                        );
                      })}
                      <TableCell>{t("ticketsList.actions")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {displayedTickets.map((ticket, index) => (
                      <>
                        {effectiveGroupBy &&
                          (index === 0 ||
                            groupLabel(displayedTickets[index - 1]) !==
                              groupLabel(ticket)) && (
                            <TableRow key={`group-${groupLabel(ticket)}`}>
                              <TableCell
                                colSpan={listColumns.length + 2}
                                sx={{
                                  bgcolor: "action.selected",
                                  fontWeight: 900,
                                }}
                              >
                                {groupLabel(ticket)}
                              </TableCell>
                            </TableRow>
                          )}
                        <TableRow
                          hover
                          key={ticket.id}
                          sx={ticketRowStyle(ticket)}
                          onAuxClick={(event) => {
                            if (
                              event.button === 1 &&
                              !(event.target as HTMLElement).closest(
                                "button,input,a",
                              )
                            ) {
                              event.preventDefault();
                              window.open(
                                `/tickets/${ticket.id}`,
                                "_blank",
                                "noopener,noreferrer",
                              );
                            }
                          }}
                          onContextMenu={(event) => {
                            if (
                              (event.target as HTMLElement).closest(
                                "a,input,button",
                              )
                            )
                              return;
                            event.preventDefault();
                            setRowMenu({
                              ticket,
                              mouseX: event.clientX + 2,
                              mouseY: event.clientY - 6,
                            });
                          }}
                        >
                          {
                            <TableCell padding="checkbox">
                              <Checkbox
                                disabled={
                                  ticket.entitlement_status ===
                                  "PENDING_APPROVAL"
                                }
                                title={
                                  ticket.entitlement_status ===
                                  "PENDING_APPROVAL"
                                    ? t("ticketsList.approvalBeforeBulk")
                                    : undefined
                                }
                                checked={selectedIds.includes(ticket.id)}
                                onClick={(event) => event.stopPropagation()}
                                onChange={(event) =>
                                  setSelectedIds((current) =>
                                    event.target.checked
                                      ? [...new Set([...current, ticket.id])]
                                      : current.filter(
                                          (id) => id !== ticket.id,
                                        ),
                                  )
                                }
                              />
                            </TableCell>
                          }
                          {listColumns.map((column) => (
                            <TableCell
                              key={column}
                              onClick={() =>
                                ticket.entitlement_status === "PENDING_APPROVAL"
                                  ? setPendingTicket(ticket)
                                  : openTicket(ticket.id)
                              }
                              title={
                                typeof ticketValue(ticket, column) === "string"
                                  ? String(ticketValue(ticket, column))
                                  : undefined
                              }
                              sx={{
                                cursor: "pointer",
                                width: dedicatedListTab
                                  ? undefined
                                  : columnWidths[column],
                                minWidth: dedicatedListTab
                                  ? 110
                                  : columnWidths[column],
                                maxWidth: dedicatedListTab
                                  ? column === "subject" ||
                                    column === "shift_handover_reason" ||
                                    column === "archive_reason"
                                    ? 360
                                    : 240
                                  : (columnWidths[column] ?? 360),
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {ticketValue(ticket, column)}
                            </TableCell>
                          ))}
                          <TableCell>
                            {trashTab &&
                            hasPermission("ticket.trash.restore") ? (
                              <Button
                                size="small"
                                disabled={restoreTicket.isPending}
                                onClick={() => restoreTicket.mutate(ticket)}
                              >
                                Restore
                              </Button>
                            ) : (
                              <IconButton
                                size="small"
                                aria-label={t("ticketsList.fastActionsFor", {
                                  number: ticket.ticket_number,
                                })}
                                onClick={(event) => {
                                  const box =
                                    event.currentTarget.getBoundingClientRect();
                                  setRowMenu({
                                    ticket,
                                    mouseX: box.left,
                                    mouseY: box.bottom,
                                  });
                                }}
                              >
                                <MoreVert />
                              </IconButton>
                            )}
                          </TableCell>
                        </TableRow>
                      </>
                    ))}
                  </TableBody>
                </Table>
              </Box>
              {floatingGridScroll.visible &&
                createPortal(
                  <Box
                    ref={floatingGridScrollRef}
                    role="scrollbar"
                    aria-label={t("ticketsList.horizontalScroll", {
                      defaultValue: "Scroll ticket columns horizontally",
                    })}
                    onScroll={(event) => {
                      if (ticketGridScrollRef.current)
                        ticketGridScrollRef.current.scrollLeft =
                          event.currentTarget.scrollLeft;
                    }}
                    sx={{
                      position: "fixed",
                      left: floatingGridScroll.left,
                      bottom: 0,
                      width: floatingGridScroll.width,
                      height: 18,
                      overflowX: "scroll",
                      overflowY: "hidden",
                      bgcolor: "background.paper",
                      border: 1,
                      borderColor: "divider",
                      boxShadow: "0 -3px 10px rgba(15, 23, 42, .16)",
                      zIndex: 1600,
                    }}
                  >
                    <Box
                      sx={{
                        width: floatingGridScroll.contentWidth,
                        height: 1,
                      }}
                    />
                  </Box>,
                  document.body,
                )}
              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                justifyContent="flex-end"
                mt={2}
              >
                <TextField
                  select
                  size="small"
                  label={t("ticketsList.rows")}
                  value={pageSize}
                  slotProps={{
                    select: {
                      MenuProps: {
                        anchorOrigin: { vertical: "top", horizontal: "left" },
                        transformOrigin: {
                          vertical: "bottom",
                          horizontal: "left",
                        },
                        marginThreshold: 8,
                      },
                    },
                  }}
                  onChange={(event) => {
                    setPageSize(Number(event.target.value));
                    setLayoutDirty(true);
                    setPage(0);
                  }}
                >
                  <MenuItem value={25}>25</MenuItem>
                  <MenuItem value={50}>50</MenuItem>
                  <MenuItem value={100}>100</MenuItem>
                </TextField>
                <Button
                  disabled={page === 0}
                  onClick={() => setPage((value) => value - 1)}
                >
                  {t("ticketsList.previous")}
                </Button>
                <Typography variant="body2">
                  {t("ticketsList.pageOf", {
                    page: page + 1,
                    pages: Math.max(
                      1,
                      Math.ceil(tickets.data.total / pageSize),
                    ),
                  })}
                </Typography>
                <Button
                  disabled={(page + 1) * pageSize >= tickets.data.total}
                  onClick={() => setPage((value) => value + 1)}
                >
                  {t("ticketsList.next")}
                </Button>
              </Stack>
            </>
          )}
        </>
      )}
      <Menu
        open={Boolean(rowMenu)}
        onClose={() => {
          setOtherActionsAnchor(null);
          setRowMenu(null);
        }}
        anchorReference="anchorPosition"
        anchorPosition={
          rowMenu ? { left: rowMenu.mouseX, top: rowMenu.mouseY } : undefined
        }
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
          disabled={saveAssistantPreferences.isPending}
          onClick={() => {
            if (rowMenu) toggleTicketPin(rowMenu.ticket.id);
            setRowMenu(null);
          }}
        >
          {rowMenu && pinnedTicketIds.includes(rowMenu.ticket.id)
            ? "Unpin"
            : "Pin"}
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
              const ticketId = rowMenu?.ticket.id;
              setRowMenu(null);
              if (ticketId)
                navigate(`/tickets/create?copy_from=${ticketId}`, {
                  state: { returnTo: "/tickets" },
                });
            }}
          >
            Copy to new ticket
          </MenuItem>
        )}
        {hasPermission("ticket.mention") && (
          <MenuItem onClick={() => openTicketAction("mention")}>
            @ Mention users
          </MenuItem>
        )}
        <MenuItem onClick={() => void openTicketWhatsApp()}>
          Open WhatsApp
        </MenuItem>
        <MenuItem
          onClick={() => {
            const id = rowMenu?.ticket.id;
            setRowMenu(null);
            if (id) openTicket(id);
          }}
        >
          Open ticket
        </MenuItem>
        {hasPermission("report.export") &&
          (types.data?.find(
            (item) => item.id === rowMenu?.ticket.ticket_type_id,
          )?.code === "INCIDENT" ? (
            <MenuItem onClick={() => void prepareTicketReport("INCIDENT")}>
              Prepare Standard Incident Report
            </MenuItem>
          ) : (
            <MenuItem onClick={() => void prepareTicketReport("TICKET")}>
              Prepare Ticket Service Report
            </MenuItem>
          ))}
        {hasPermission("ticket.assign.team") && (
          <MenuItem
            disabled={rowMenu?.ticket.entitlement_status === "PENDING_APPROVAL"}
            onClick={() => openTicketAction("assign")}
          >
            Reassign ticket
          </MenuItem>
        )}
        {hasPermission("ticket.flag.apply") && (
          <MenuItem
            onClick={() => {
              const ticket = rowMenu?.ticket;
              setRowMenu(null);
              if (ticket) setFlagDialogTicket(ticket);
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
              General
            </ListSubheader>
            {hasPermission("ticket.copy") && (
              <MenuItem
                onClick={() => {
                  const ticketId = rowMenu?.ticket.id;
                  setRowMenu(null);
                  if (ticketId)
                    navigate(`/tickets/create?copy_from=${ticketId}`, {
                      state: { returnTo: "/tickets" },
                    });
                }}
              >
                {t("ticketsList.copyToNewTicket", {
                  defaultValue: "Copy to new ticket",
                })}
              </MenuItem>
            )}
            <MenuItem onClick={() => openTicketAction("history")}>
              {t("ticketsList.viewHistory")}
            </MenuItem>
            {hasPermission("ticket.flag.apply") && (
              <MenuItem
                onClick={() => {
                  const ticket = rowMenu?.ticket;
                  setRowMenu(null);
                  if (ticket) setFlagDialogTicket(ticket);
                }}
              >
                Add ticket flag
              </MenuItem>
            )}
            {[
              "ticket.live_update.send",
              "ticket.satisfaction.send",
              "complaint.tracking.send",
            ].some(hasPermission) && (
              <MenuItem
                onClick={() => {
                  const selected = rowMenu?.ticket.id;
                  setRowMenu(null);
                  if (selected) setSendTicketId(selected);
                }}
              >
                {t("ticketsList.sendActions")}
              </MenuItem>
            )}
            {hasPermission("complaint.create") && (
              <MenuItem
                onClick={() => {
                  const ticket = rowMenu?.ticket;
                  setRowMenu(null);
                  if (ticket)
                    navigate(
                      `/complaints?register=1&ticket_id=${ticket.id}&client_id=${ticket.client_id}&caller_id=${ticket.requester_contact_id ?? ""}`,
                    );
                }}
              >
                {t("ticketsList.registerComplaint")}
              </MenuItem>
            )}
            {hasPermission("ticket.change.status") && (
              <MenuItem
                disabled={
                  rowMenu?.ticket.entitlement_status === "PENDING_APPROVAL"
                }
                onClick={() => openTicketAction("status")}
              >
                {t("ticketsList.changeStatus")}
              </MenuItem>
            )}
            {hasPermission("ticket.assign.team") && (
              <MenuItem
                disabled={
                  rowMenu?.ticket.entitlement_status === "PENDING_APPROVAL"
                }
                onClick={() => openTicketAction("assign")}
              >
                {t("ticketsList.reassignTicket")}
              </MenuItem>
            )}
            {(hasPermission("ticket.escalate") ||
              hasPermission("ticket.help.request")) && (
              <MenuItem
                disabled={
                  rowMenu?.ticket.entitlement_status === "PENDING_APPROVAL"
                }
                onClick={() => openTicketAction("escalate")}
              >
                {t("ticketsList.escalateHelp")}
              </MenuItem>
            )}
            <ListSubheader
              disableSticky
              sx={{ lineHeight: "30px", fontWeight: 800 }}
            >
              Workflow
            </ListSubheader>
            <Divider />
            <ListSubheader
              disableSticky
              sx={{ lineHeight: "30px", fontWeight: 800 }}
            >
              Work &amp; collaboration
            </ListSubheader>
            {hasPermission("ticket.change.status") && (
              <MenuItem onClick={() => openTicketAction("task")}>
                {t("ticketDetail.addTask")}
              </MenuItem>
            )}
            {hasPermission("ticket.comment.public") && (
              <MenuItem onClick={() => openTicketAction("comment-public")}>
                Public comment
              </MenuItem>
            )}
            {hasPermission("ticket.comment.internal") && (
              <MenuItem onClick={() => openTicketAction("comment-internal")}>
                Internal comment
              </MenuItem>
            )}
            {hasPermission("ticket.assign.team") && (
              <MenuItem onClick={() => openTicketAction("handover")}>
                Hand over
              </MenuItem>
            )}
            {hasPermission("ticket.resolve") && (
              <MenuItem onClick={() => openTicketAction("resolve")}>
                Resolve ticket
              </MenuItem>
            )}
            {user?.user_type === "EMPLOYEE" && (
              <MenuItem onClick={() => openTicketAction("worklog")}>
                {t("ticketDetail.logWork")}
              </MenuItem>
            )}
            {hasPermission("ticket.change.status") && (
              <MenuItem onClick={() => openTicketAction("checklist")}>
                {t("ticketDetail.addChecklistItem")}
              </MenuItem>
            )}
            {hasPermission("ticket.relate") && (
              <MenuItem onClick={() => openTicketAction("link")}>
                {t("ticketDetail.linkRelated")}
              </MenuItem>
            )}
            {hasPermission("knowledge.view") && (
              <MenuItem onClick={() => openTicketAction("knowledge")}>
                {t("ticketDetail.linkKnowledge")}
              </MenuItem>
            )}
            {hasPermission("ticket.template.create") && (
              <MenuItem onClick={() => openTicketAction("template")}>
                {t("ticketDetail.createAsTemplate", {
                  defaultValue: "Create as ticket template",
                })}
              </MenuItem>
            )}
            {hasPermission("ticket.mention") && (
              <MenuItem onClick={() => openTicketAction("mention")}>
                @ Mention users
              </MenuItem>
            )}
            <Divider />
            <ListSubheader
              disableSticky
              sx={{ lineHeight: "30px", fontWeight: 800 }}
            >
              Contact
            </ListSubheader>
            <MenuItem onClick={() => void openTicketWhatsApp()}>
              Open WhatsApp
            </MenuItem>
          </>
        )}
      </Menu>
      <Menu
        anchorEl={otherActionsAnchor}
        open={Boolean(rowMenu && otherActionsAnchor)}
        onClose={() => setOtherActionsAnchor(null)}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
        MenuListProps={{ onMouseLeave: () => setOtherActionsAnchor(null) }}
      >
        <MenuItem onClick={() => openTicketAction("history")}>
          View status history
        </MenuItem>
        {hasPermission("ticket.change.status") && (
          <MenuItem
            disabled={rowMenu?.ticket.entitlement_status === "PENDING_APPROVAL"}
            onClick={() => openTicketAction("status")}
          >
            Change status
          </MenuItem>
        )}
        {hasPermission("ticket.comment.public") && (
          <MenuItem onClick={() => openTicketAction("comment-public")}>
            Public comment
          </MenuItem>
        )}
        {hasPermission("ticket.comment.internal") && (
          <MenuItem onClick={() => openTicketAction("comment-internal")}>
            Internal comment
          </MenuItem>
        )}
        {hasPermission("ticket.change.status") && (
          <MenuItem onClick={() => openTicketAction("task")}>Add task</MenuItem>
        )}
        {user?.user_type === "EMPLOYEE" && (
          <MenuItem onClick={() => openTicketAction("worklog")}>
            Log work
          </MenuItem>
        )}
        {hasPermission("ticket.assign.team") && (
          <MenuItem onClick={() => openTicketAction("handover")}>
            Hand over
          </MenuItem>
        )}
        {(hasPermission("ticket.escalate") ||
          hasPermission("ticket.help.request")) && (
          <MenuItem onClick={() => openTicketAction("escalate")}>
            Escalate / request help
          </MenuItem>
        )}
        {hasPermission("ticket.relate") && (
          <MenuItem onClick={() => openTicketAction("link")}>
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
              const selected = rowMenu?.ticket.id;
              setRowMenu(null);
              if (selected) setSendTicketId(selected);
            }}
          >
            {t("ticketsList.sendActions")}
          </MenuItem>
        )}
      </Menu>
      <TicketSendActionsDialog
        ticketId={sendTicketId}
        open={sendTicketId !== null}
        onClose={() => setSendTicketId(null)}
      />
      <Menu
        anchorEl={clientMenu?.anchor ?? null}
        open={clientMenu !== null}
        onClose={() => setClientMenu(null)}
      >
        <MenuItem
          onClick={() => {
            const id = clientMenu?.ticket.client_id;
            setClientMenu(null);
            if (id)
              setClientAccessDialog({
                clientId: id,
                editMode: hasPermission("client_access.manage"),
              });
          }}
          disabled={!hasPermission("client_access.view")}
        >
          <Visibility fontSize="small" sx={{ mr: 1 }} />
          Show access
        </MenuItem>
        <MenuItem
          onClick={() => {
            const id = clientMenu?.ticket.client_id;
            setClientMenu(null);
            if (id) navigate(`/clients/${id}/profile`);
          }}
          disabled={!hasPermission("client.profile.view")}
        >
          <Business fontSize="small" sx={{ mr: 1 }} />
          Show client profile
        </MenuItem>
        <MenuItem
          onClick={() => {
            const id = clientMenu?.ticket.client_id;
            setClientMenu(null);
            if (id) navigate(`/clients/${id}/edit#client-info`);
          }}
        >
          <Edit fontSize="small" sx={{ mr: 1 }} />
          Show client info
        </MenuItem>
        <MenuItem
          onClick={() => {
            const id = clientMenu?.ticket.client_id;
            setClientMenu(null);
            if (id) navigate(`/tickets?client_id=${id}`);
          }}
        >
          <Visibility fontSize="small" sx={{ mr: 1 }} />
          Show client tickets
        </MenuItem>
        <MenuItem
          onClick={() => {
            const selected = clientMenu?.ticket;
            setClientMenu(null);
            if (selected)
              setClientContactsDialog({
                clientId: selected.client_id,
                ticketId: selected.id,
              });
          }}
        >
          <ContactPage fontSize="small" sx={{ mr: 1 }} />
          Show client contacts
        </MenuItem>
      </Menu>
      <ClientAccessManagerDialog
        clientId={clientAccessDialog?.clientId ?? null}
        editMode={clientAccessDialog?.editMode ?? false}
        open={clientAccessDialog !== null}
        onClose={() => setClientAccessDialog(null)}
      />
      <ClientContactsDialog
        clientId={clientContactsDialog?.clientId ?? null}
        ticketId={clientContactsDialog?.ticketId ?? null}
        open={clientContactsDialog !== null}
        onClose={() => setClientContactsDialog(null)}
      />
      <Menu
        anchorEl={contactMenu?.anchor ?? null}
        open={contactMenu !== null}
        onClose={() => setContactMenu(null)}
      >
        <MenuItem
          onClick={() =>
            contactMenu && void openContactWhatsApp(contactMenu.ticket)
          }
          disabled={!contactMenu?.ticket.requester_phone_number}
        >
          <WhatsApp fontSize="small" sx={{ mr: 1 }} />
          Open WhatsApp
        </MenuItem>
        <MenuItem
          onClick={() => {
            const id = contactMenu?.ticket.id;
            setContactMenu(null);
            if (id) setSendTicketId(id);
          }}
          disabled={!hasPermission("ticket.live_update.send")}
        >
          <Send fontSize="small" sx={{ mr: 1 }} />
          Send live tracking
        </MenuItem>
        <MenuItem
          onClick={() => {
            const id = contactMenu?.ticket.requester_contact_id;
            setContactMenu(null);
            if (id) navigate(`/tickets?requester_contact_id=${id}`);
          }}
        >
          <Visibility fontSize="small" sx={{ mr: 1 }} />
          Show contact tickets
        </MenuItem>
        <MenuItem
          onClick={() =>
            contactMenu && void copyContactInfo(contactMenu.ticket)
          }
        >
          <ContentCopy fontSize="small" sx={{ mr: 1 }} />
          Copy contact info
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            const ticket = contactMenu?.ticket;
            setContactMenu(null);
            if (ticket) loadContact.mutate(ticket);
          }}
        >
          <ContactPage fontSize="small" sx={{ mr: 1 }} />
          Open contact info
        </MenuItem>
      </Menu>
      <Dialog
        open={flagDialogTicket !== null}
        onClose={() => setFlagDialogTicket(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Add ticket flag</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary" mb={1}>
            {flagDialogTicket?.ticket_number} · {flagDialogTicket?.subject}
          </Typography>
          <FormControl fullWidth margin="normal">
            <InputLabel>Flag</InputLabel>
            <Select
              value={selectedFlagId}
              label="Flag"
              onChange={(event) =>
                setSelectedFlagId(String(event.target.value))
              }
            >
              {(ticketFlagOptions.data ?? [])
                .filter(
                  (option) =>
                    !flagDialogTicket?.active_flags?.some(
                      (active) => active.flag_id === option.id,
                    ),
                )
                .map((option) => (
                  <MenuItem key={option.id} value={option.id}>
                    <Flag
                      fontSize="small"
                      sx={{ color: option.color, mr: 1 }}
                    />
                    {option.name}
                    {option.pauses_sla ? " — pauses SLA" : ""}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            required
            margin="normal"
            label="Reason"
            value={flagReason}
            onChange={(event) => setFlagReason(event.target.value)}
            helperText="Enter at least 3 characters."
          />
          {applyTicketFlag.isError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {apiErrorMessage(applyTicketFlag.error)}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFlagDialogTicket(null)}>Cancel</Button>
          <Button
            variant="contained"
            startIcon={<Flag />}
            disabled={
              !selectedFlagId ||
              flagReason.trim().length < 3 ||
              applyTicketFlag.isPending
            }
            onClick={() => applyTicketFlag.mutate()}
          >
            Add flag
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={contactDialog !== null}
        onClose={() => setContactDialog(null)}
        fullWidth
        maxWidth="sm"
      >
        <Stack
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            saveContact.mutate({
              full_name: String(values.full_name).trim(),
              phone_number: String(values.phone_number).trim() || null,
              email: String(values.email).trim() || null,
              job_title: String(values.job_title).trim() || null,
              contact_role: String(values.contact_role).trim() || null,
              is_active: values.is_active === "true",
            });
          }}
        >
          <DialogTitle>Contact information</DialogTitle>
          <DialogContent>
            {contactMessage && (
              <Alert severity="success" sx={{ mt: 1 }}>
                {contactMessage}
              </Alert>
            )}
            {saveContact.isError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                The contact information could not be updated.
              </Alert>
            )}
            <TextField
              required
              name="full_name"
              label="Full name"
              defaultValue={contactDialog?.full_name ?? ""}
              fullWidth
              margin="normal"
              disabled={!hasPermission("contact.manage")}
            />
            <TextField
              name="phone_number"
              label="Phone / WhatsApp"
              defaultValue={contactDialog?.phone_number ?? ""}
              fullWidth
              margin="normal"
              disabled={!hasPermission("contact.manage")}
            />
            <TextField
              name="email"
              type="email"
              label="Email"
              defaultValue={contactDialog?.email ?? ""}
              fullWidth
              margin="normal"
              disabled={!hasPermission("contact.manage")}
            />
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                name="job_title"
                label="Job title"
                defaultValue={contactDialog?.job_title ?? ""}
                fullWidth
                margin="normal"
                disabled={!hasPermission("contact.manage")}
              />
              <TextField
                name="contact_role"
                label="Contact role"
                defaultValue={contactDialog?.contact_role ?? ""}
                fullWidth
                margin="normal"
                disabled={!hasPermission("contact.manage")}
              />
            </Stack>
            <TextField
              select
              name="is_active"
              label="Status"
              defaultValue={String(contactDialog?.is_active ?? true)}
              fullWidth
              margin="normal"
              disabled={!hasPermission("contact.manage")}
            >
              <MenuItem value="true">Active</MenuItem>
              <MenuItem value="false">Inactive</MenuItem>
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setContactDialog(null)}>Close</Button>
            {hasPermission("contact.manage") && (
              <Button
                type="submit"
                variant="contained"
                disabled={saveContact.isPending}
              >
                Save changes
              </Button>
            )}
          </DialogActions>
        </Stack>
      </Dialog>
      <Dialog
        open={boardSettingsOpen}
        onClose={() => setBoardSettingsOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {t("ticketsList.boardSettings", { defaultValue: "Board settings" })}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <TextField
              select
              label={t("ticketsList.cardDensity", {
                defaultValue: "Card density",
              })}
              value={boardSettings.density}
              onChange={(event) =>
                setBoardSettings((current) => ({
                  ...current,
                  density: event.target.value as BoardSettings["density"],
                }))
              }
            >
              <MenuItem value="COMPACT">{t("ticketsList.compact")}</MenuItem>
              <MenuItem value="STANDARD">{t("ticketsList.standard")}</MenuItem>
              <MenuItem value="DETAILED">
                {t("ticketsList.detailed", { defaultValue: "Detailed" })}
              </MenuItem>
            </TextField>
            <TextField
              select
              label={t("ticketsList.swimlane", { defaultValue: "Swimlane" })}
              value={boardSettings.swimlane}
              onChange={(event) =>
                setBoardSettings((current) => ({
                  ...current,
                  swimlane: event.target.value as BoardSettings["swimlane"],
                }))
              }
            >
              <MenuItem value="">
                {t("ticketsList.noSwimlane", { defaultValue: "No swimlane" })}
              </MenuItem>
              <MenuItem value="priority">
                {columnLabel("priority", "Priority")}
              </MenuItem>
              <MenuItem value="assigned_engineer">
                {columnLabel("assigned_engineer", "Assigned engineer")}
              </MenuItem>
              <MenuItem value="client">
                {columnLabel("client", "Client")}
              </MenuItem>
            </TextField>
            <Box>
              <Typography fontWeight={900}>
                {t("ticketsList.cardFields", { defaultValue: "Card fields" })}
              </Typography>
              {[
                "client",
                "assigned_engineer",
                "priority",
                "status",
                "updated_at",
                "description",
              ].map((field) => (
                <FormControlLabel
                  key={field}
                  control={
                    <Checkbox
                      checked={boardSettings.fields.includes(field)}
                      onChange={(event) =>
                        setBoardSettings((current) => ({
                          ...current,
                          fields: event.target.checked
                            ? [...current.fields, field]
                            : current.fields.filter((item) => item !== field),
                        }))
                      }
                    />
                  }
                  label={columnLabel(field, field.replaceAll("_", " "))}
                />
              ))}
            </Box>
            <Box>
              <Typography fontWeight={900} mb={1}>
                {t("ticketsList.laneLimits", { defaultValue: "Lane limits" })}
              </Typography>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                  gap: 1,
                }}
              >
                {allCardGroups.map((group) => (
                  <TextField
                    key={group.key}
                    size="small"
                    type="number"
                    label={group.label}
                    value={boardSettings.laneLimits[String(group.key)] || ""}
                    slotProps={{ htmlInput: { min: 0 } }}
                    onChange={(event) =>
                      setBoardSettings((current) => ({
                        ...current,
                        laneLimits: {
                          ...current.laneLimits,
                          [String(group.key)]: Math.max(
                            0,
                            Number(event.target.value),
                          ),
                        },
                      }))
                    }
                  />
                ))}
              </Box>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBoardSettings(defaultBoardSettings)}>
            {t("ticketsList.default")}
          </Button>
          <Button
            variant="contained"
            onClick={() => setBoardSettingsOpen(false)}
          >
            {t("ticketsList.apply")}
          </Button>
        </DialogActions>
      </Dialog>
      <Drawer
        anchor="right"
        open={Boolean(previewTicket)}
        onClose={() => setPreviewTicket(null)}
        slotProps={{
          paper: {
            sx: {
              top: { xs: 56, sm: 64 },
              height: { xs: "calc(100% - 56px)", sm: "calc(100% - 64px)" },
            },
          },
        }}
      >
        {previewTicket && (
          <Box sx={{ width: { xs: "88vw", sm: 420 }, p: 2 }}>
            <Stack direction="row" alignItems="center" gap={1}>
              <Box flex={1}>
                <Typography variant="overline">
                  {previewTicket.ticket_number}
                </Typography>
                <Typography variant="h6" fontWeight={900}>
                  {previewTicket.subject}
                </Typography>
              </Box>
              <IconButton
                onClick={(event) => {
                  const box = event.currentTarget.getBoundingClientRect();
                  setRowMenu({
                    ticket: previewTicket,
                    mouseX: box.left,
                    mouseY: box.bottom,
                  });
                }}
              >
                <MoreVert />
              </IconButton>
            </Stack>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={1.5}>
              <Box>
                {ticketValue(previewTicket, "status")}{" "}
                {ticketValue(previewTicket, "priority")}
              </Box>
              <Typography>
                <b>{columnLabel("client", "Client")}:</b>{" "}
                {previewTicket.client_name ??
                  catalogName(clients.data, previewTicket.client_id)}
              </Typography>
              <Typography>
                <b>{columnLabel("assigned_engineer", "Assigned engineer")}:</b>{" "}
                {String(ticketValue(previewTicket, "assigned_engineer"))}
              </Typography>
              <Typography>
                <b>{columnLabel("updated_at", "Updated")}:</b>{" "}
                {displayDate(previewTicket.updated_at)}
              </Typography>
              <Divider />
              <Typography fontWeight={900}>{t("ticketDetail.sla")}</Typography>
              <Typography>
                <b>
                  {columnLabel(
                    "sla_resolution_target",
                    "Resolution SLA target",
                  )}
                  :
                </b>{" "}
                {slaDuration(previewTicket.sla_resolution_target_minutes)}
              </Typography>
              <Typography>
                <b>
                  {columnLabel("sla_actual_business_time", "Actual SLA time")}:
                </b>{" "}
                {slaDuration(previewTicket.sla_actual_business_minutes)}
              </Typography>
              {["RESOLVED", "CLOSED"].includes(
                statuses.data?.find(
                  (item) => item.id === previewTicket.status_id,
                )?.code ?? "",
              ) && (
                <Typography>
                  <b>
                    {columnLabel(
                      "sla_time_balance",
                      "SLA time saved / overrun",
                    )}
                    :
                  </b>{" "}
                  {previewTicket.sla_overrun_minutes
                    ? t("ticketsList.overrun", {
                        duration: slaDuration(
                          previewTicket.sla_overrun_minutes,
                        ),
                      })
                    : t("ticketsList.saved", {
                        duration: slaDuration(previewTicket.sla_saved_minutes),
                      })}
                </Typography>
              )}
              <Typography>
                <b>
                  {columnLabel("sla_resolution_state", "Resolution SLA state")}:
                </b>{" "}
                {previewTicket.sla_resolution_state || "—"}
              </Typography>
              {previewTicket.sla_match_reason && (
                <Typography variant="body2" color="text.secondary">
                  {previewTicket.sla_match_reason}
                </Typography>
              )}
              <Divider />
              <Typography sx={{ whiteSpace: "pre-wrap" }}>
                {previewTicket.description || "—"}
              </Typography>
            </Stack>
            <Button
              fullWidth
              variant="contained"
              sx={{ mt: 3 }}
              onClick={() => openTicket(previewTicket.id)}
            >
              {t("ticketsList.openTicket")}
            </Button>
          </Box>
        )}
      </Drawer>
      <Dialog
        open={groupPickerOpen}
        onClose={() => setGroupPickerOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>
          {t("ticketsList.chooseVisibleGroups", {
            defaultValue: "Choose visible groups",
          })}
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" mb={1}>
            {t("ticketsList.visibleGroupsHint", {
              defaultValue:
                "Leave every option unselected to show all groups. Save this ticket view to keep the selection.",
            })}
          </Typography>
          <Stack>
            {allCardGroups.map((group) => (
              <FormControlLabel
                key={group.key}
                control={
                  <Checkbox
                    checked={selectedGroupValues.includes(String(group.key))}
                    onChange={(event) =>
                      setSelectedGroupValues((current) =>
                        event.target.checked
                          ? [...current, String(group.key)]
                          : current.filter(
                              (value) => value !== String(group.key),
                            ),
                      )
                    }
                  />
                }
                label={`${group.label} (${group.tickets.length})`}
              />
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedGroupValues([])}>
            {t("ticketsList.showAll", { defaultValue: "Show all" })}
          </Button>
          <Button variant="contained" onClick={() => setGroupPickerOpen(false)}>
            {t("ticketsList.apply", { defaultValue: "Apply" })}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(pendingTicket)}
        onClose={() => setPendingTicket(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{t("ticketsList.approvalTitle")}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t("ticketsList.approvalLocked")}
          </Alert>
          {pendingTicket && (
            <>
              <Typography variant="h6">
                {pendingTicket.ticket_number} — {pendingTicket.subject}
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1 }}>
                {selectedApproval?.justification ??
                  t("ticketsList.approvalPending")}
              </Typography>
              {selectedApproval?.approval_deadline && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  {t("ticketsList.decisionDue", {
                    date: new Date(
                      selectedApproval.approval_deadline,
                    ).toLocaleString(),
                  })}
                </Typography>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingTicket(null)}>
            {t("ticketsList.informed")}
          </Button>
          {selectedApproval && (
            <Button
              color="warning"
              disabled={remindApproval.isPending}
              onClick={() => remindApproval.mutate(selectedApproval.id)}
            >
              {remindApproval.isPending
                ? t("ticketsList.sending")
                : t("ticketsList.sendReminder")}
            </Button>
          )}
          {selectedApproval && hasPermission("entitlement_approval.decide") && (
            <Button
              color="error"
              disabled={decideApproval.isPending}
              onClick={() => {
                const comment = window.prompt(t("ticketsList.rejectionReason"));
                if (comment && comment.trim().length >= 3)
                  decideApproval.mutate({
                    approvalId: selectedApproval.id,
                    decision: "REJECTED",
                    comment: comment.trim(),
                  });
              }}
            >
              {t("ticketsList.reject")}
            </Button>
          )}
          {selectedApproval && hasPermission("entitlement_approval.decide") && (
            <Button
              color="success"
              variant="contained"
              disabled={decideApproval.isPending}
              onClick={() => {
                const comment = window.prompt(
                  t("ticketsList.approvalComment"),
                  t("ticketsList.approvalCommentDefault"),
                );
                if (comment && comment.trim().length >= 3)
                  decideApproval.mutate({
                    approvalId: selectedApproval.id,
                    decision: "APPROVED",
                    comment: comment.trim(),
                  });
              }}
            >
              {t("ticketsList.approve")}
            </Button>
          )}
          <Button
            variant="outlined"
            onClick={() =>
              pendingTicket && openTicket(pendingTicket.id)
            }
          >
            {t("ticketsList.openTicket")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={columnsOpen}
        onClose={() => setColumnsOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{t("ticketsList.columnTitle")}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" mb={1}>
            {t("ticketsList.columnDragHint")}
          </Typography>
          <Stack gap={0.5}>
            {visibleColumns.map((column) => {
              const label =
                availableColumns.find(([key]) => key === column)?.[1] ?? column;
              return (
                <Paper
                  key={column}
                  draggable
                  variant="outlined"
                  onDragStart={() => setDraggedColumn(column)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => {
                    if (!draggedColumn || draggedColumn === column) return;
                    setVisibleColumns((current) => {
                      const next = current.filter(
                        (item) => item !== draggedColumn,
                      );
                      next.splice(next.indexOf(column), 0, draggedColumn);
                      return next;
                    });
                    setLayoutDirty(true);
                    setDraggedColumn(null);
                  }}
                  sx={{ px: 1, py: 0.25, cursor: "grab" }}
                >
                  <Stack direction="row" alignItems="center">
                    <DragIndicator color="action" fontSize="small" />
                    <Checkbox
                      size="small"
                      checked
                      onChange={() => {
                        setVisibleColumns((current) =>
                          current.filter((item) => item !== column),
                        );
                        setLayoutDirty(true);
                      }}
                    />
                    <Typography variant="body2">
                      {columnLabel(column, label)}
                    </Typography>
                  </Stack>
                </Paper>
              );
            })}
          </Stack>
          <Typography variant="subtitle2" mt={2}>
            {t("ticketsList.availableColumns")}
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)" }}>
            {availableColumns
              .filter(([column]) => !visibleColumns.includes(column))
              .map(([column, label]) => (
                <FormControlLabel
                  key={column}
                  control={
                    <Checkbox
                      size="small"
                      checked={false}
                      onChange={() => {
                        setVisibleColumns((current) => [...current, column]);
                        setLayoutDirty(true);
                      }}
                    />
                  }
                  label={columnLabel(column, label)}
                />
              ))}
          </Box>
          <TextField
            select
            size="small"
            fullWidth
            margin="normal"
            label={t("ticketsList.rowDensity")}
            value={density}
            onChange={(event) => {
              setDensity(event.target.value as "COMPACT" | "STANDARD");
              setLayoutDirty(true);
            }}
          >
            <MenuItem value="COMPACT">{t("ticketsList.compact")}</MenuItem>
            <MenuItem value="STANDARD">{t("ticketsList.standard")}</MenuItem>
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setVisibleColumns(columnKeys);
              setLayoutDirty(true);
            }}
          >
            {t("ticketsList.showAll")}
          </Button>
          <Button
            onClick={() => {
              setVisibleColumns(defaultColumns);
              setLayoutDirty(true);
            }}
          >
            {t("ticketsList.default")}
          </Button>
          <Button
            variant="contained"
            disabled={!visibleColumns.length}
            onClick={() => setColumnsOpen(false)}
          >
            {t("ticketsList.apply")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={bulkOpen}
        onClose={() => setBulkOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{t("ticketsList.bulkTitle")}</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            {t("ticketsList.bulkHint")}
          </Typography>
          <TextField
            select
            SelectProps={{ multiple: true }}
            label={t("ticketsList.title")}
            value={selectedIds.map(String)}
            onChange={(event) =>
              setSelectedIds(
                (typeof event.target.value === "string"
                  ? event.target.value.split(",")
                  : event.target.value
                ).map(Number),
              )
            }
            fullWidth
            margin="normal"
          >
            {tickets.data?.items.map((ticket) => (
              <MenuItem key={ticket.id} value={String(ticket.id)}>
                {ticket.ticket_number} — {ticket.subject}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label={t("ticketsList.supportTeam")}
            value={bulkTeam}
            onChange={(event) => setBulkTeam(event.target.value)}
            fullWidth
            margin="normal"
          >
            <MenuItem value="">{t("ticketsList.noTeam")}</MenuItem>
            {supportTeams.data
              ?.filter((team) => team.is_active)
              .map((team) => (
                <MenuItem key={team.id} value={team.name}>
                  {team.name}
                </MenuItem>
              ))}
          </TextField>
          <TextField
            select
            label={t("ticketsList.engineer")}
            value={bulkUser}
            onChange={(event) => setBulkUser(event.target.value)}
            fullWidth
            margin="normal"
          >
            <MenuItem value="">{t("ticketsList.noEngineer")}</MenuItem>
            {assignees.data?.map((engineer) => (
              <MenuItem key={engineer.id} value={engineer.id}>
                {engineer.full_name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label={t("ticketsList.assignmentReason")}
            value={bulkReason}
            onChange={(event) => setBulkReason(event.target.value)}
            fullWidth
            multiline
            rows={2}
            margin="normal"
            inputProps={{ maxLength: 500 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkOpen(false)}>
            {t("ticketsList.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={
              !selectedIds.length ||
              (!bulkTeam && !bulkUser) ||
              bulkAssign.isPending
            }
            onClick={() => bulkAssign.mutate()}
          >
            {t("ticketsList.assignCount", { count: selectedIds.length })}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={statusOpen}
        onClose={() => {
          setStatusOpen(false);
          setChoosePendingStatus(false);
          setCardTransitionTicket(null);
          setCardResolutionAttachments([]);
          setCardKnowledgeSearch("");
          setCardKnowledgeError("");
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {cardTransitionTicket
            ? `${t("ticketsList.changeStatus")} · ${cardTransitionTicket.ticket_number}`
            : bulkStatus === "RESOLVED"
              ? t("ticketsList.resolveTicket", {
                  defaultValue: "Resolve ticket",
                })
              : t("ticketsList.statusTitle", { count: selectedIds.length })}
        </DialogTitle>
        <DialogContent>
          {!cardTransitionTicket && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {t("ticketsList.statusAtomic")}
            </Alert>
          )}
          {bulkStatusChange.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {t("ticketsList.statusChangeFailed", {
                defaultValue:
                  "The ticket status could not be changed. Review the required fields and try again.",
              })}
            </Alert>
          )}
          {choosePendingStatus && (
            <Alert severity="info" sx={{ mb: 2 }}>
              {t("ticketsList.pendingLaneChooseReason", {
                defaultValue:
                  "Choose who the ticket is waiting for. The original pending status and workflow rules are preserved.",
              })}
            </Alert>
          )}
          <TextField
            select
            required
            fullWidth
            label={t("ticketsList.newStatus")}
            value={bulkStatus}
            disabled={Boolean(cardTransitionTicket) && !choosePendingStatus}
            onChange={(event) => {
              const nextStatus = event.target.value;
              setBulkStatus(nextStatus);
              if (choosePendingStatus)
                setBulkPendingParty(
                  nextStatus === "PENDING_CLIENT" ? "CUSTOMER" : "MILLENSYS",
                );
            }}
          >
            {statuses.data
              ?.filter(
                (status) =>
                  !choosePendingStatus || isPendingStatusCode(status.code),
              )
              .map((status) => (
                <MenuItem key={status.id} value={status.code}>
                  {getLocalizedName(status, language)}
                </MenuItem>
              ))}
          </TextField>
          <TextField
            required={
              bulkStatus.startsWith("PENDING_") ||
              bulkStatus === "CANCELLED" ||
              bulkStatus === "REOPENED" ||
              (Boolean(cardTransitionTicket) && cardRequiresResolution)
            }
            fullWidth
            multiline
            rows={3}
            margin="normal"
            label={
              (
                cardTransitionTicket
                  ? cardRequiresResolution
                  : bulkStatus === "RESOLVED"
              )
                ? t("ticketsList.resolutionCause")
                : t("ticketsList.changeReason")
            }
            value={bulkReason}
            onChange={(event) => setBulkReason(event.target.value)}
          />
          {bulkStatus.startsWith("PENDING_") && (
            <>
              <TextField
                select
                required
                fullWidth
                margin="normal"
                label={t("ticketDetail.waitingResponsibility")}
                value={bulkPendingParty}
                onChange={(event) =>
                  setBulkPendingParty(
                    event.target.value as "CUSTOMER" | "MILLENSYS",
                  )
                }
                helperText={t("ticketDetail.waitingSlaHelp")}
              >
                <MenuItem value="CUSTOMER">
                  {t("ticketDetail.customerClient")}
                </MenuItem>
                <MenuItem value="MILLENSYS">Millensys</MenuItem>
              </TextField>
              <TextField
                select
                required
                fullWidth
                margin="normal"
                label={t("ticketsList.followUpOwner")}
                value={bulkPendingOwner}
                onChange={(event) => setBulkPendingOwner(event.target.value)}
              >
                <MenuItem value={user?.id ?? ""}>
                  {t("ticketsList.me")}
                </MenuItem>
                {assignees.data
                  ?.filter((engineer) => engineer.id !== user?.id)
                  .map((engineer) => (
                    <MenuItem key={engineer.id} value={engineer.id}>
                      {engineer.full_name}
                    </MenuItem>
                  ))}
              </TextField>
              <TextField
                type="datetime-local"
                required
                fullWidth
                margin="normal"
                label={t("ticketsList.followUpDeadline")}
                value={bulkPendingFollowUp}
                onChange={(event) => setBulkPendingFollowUp(event.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </>
          )}
          {cardTransitionTicket && cardRequiresResolution && (
            <TextField
              select
              required
              fullWidth
              margin="normal"
              label={t("ticketDetail.serviceProvided")}
              value={cardResolutionServiceIds}
              onChange={(event) =>
                setCardResolutionServiceIds(
                  (event.target.value as unknown as number[]).map(Number),
                )
              }
              SelectProps={{
                multiple: true,
                renderValue: (value) =>
                  (value as number[])
                    .map((id) =>
                      getLocalizedName(
                        cardResolutionServices.data?.find(
                          (service) => service.id === id,
                        ) ?? { id, code: String(id), name: `#${id}` },
                        language,
                      ),
                    )
                    .join(", "),
              }}
              helperText={t("ticketDetail.serviceProvidedHelp")}
            >
              {cardResolutionServices.data?.map((service) => (
                <MenuItem key={service.id} value={service.id}>
                  <Checkbox
                    checked={cardResolutionServiceIds.includes(service.id)}
                  />
                  {getLocalizedName(service, language)}
                </MenuItem>
              ))}
            </TextField>
          )}
          {cardTransitionTicket &&
            ticketCardAllowsKnowledgeResolution(
              bulkStatus,
              hasPermission("knowledge.view"),
            ) && (
              <Paper variant="outlined" sx={{ mt: 1.5, p: 1.5 }}>
                <Typography fontWeight={700}>
                  {t("ticketDetail.searchKnowledge")}
                </Typography>
                <TextField
                  size="small"
                  fullWidth
                  sx={{ mt: 1 }}
                  value={cardKnowledgeSearch}
                  onChange={(event) =>
                    setCardKnowledgeSearch(event.target.value)
                  }
                  placeholder={t("ticketDetail.searchKnowledge")}
                />
                {cardKnowledgeError && (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {cardKnowledgeError}
                  </Alert>
                )}
                {cardKnowledgeArticles.isFetching && (
                  <Typography variant="body2" color="text.secondary" mt={1}>
                    {t("ticketDetail.loadingArticles")}
                  </Typography>
                )}
                {!cardKnowledgeArticles.isFetching &&
                  cardKnowledgeSearch.trim().length >= 2 &&
                  cardKnowledgeArticles.data?.length === 0 && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      {t("ticketDetail.noArticleMatches")}
                    </Alert>
                  )}
                <Stack spacing={0.5} mt={1}>
                  {cardKnowledgeArticles.data?.map((article) => (
                    <Stack
                      key={article.id}
                      direction={{ xs: "column", sm: "row" }}
                      alignItems={{ sm: "center" }}
                      gap={0.5}
                    >
                      <Box flex={1}>
                        <Typography variant="body2" fontWeight={700}>
                          {article.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {article.summary}
                        </Typography>
                      </Box>
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={applyCardKnowledgeResolution.isPending}
                        onClick={() =>
                          applyCardKnowledgeResolution.mutate(article.id)
                        }
                      >
                        {t("ticketDetail.applyResolution")}
                      </Button>
                    </Stack>
                  ))}
                </Stack>
              </Paper>
            )}
          {cardTransitionTicket &&
            ticketCardAllowsResolutionAttachments(bulkStatus) && (
              <Stack
                spacing={1}
                sx={{ mt: 1.5, pt: 1.5, borderTop: 1, borderColor: "divider" }}
              >
                <Stack direction="row" alignItems="center" gap={1}>
                  <Typography fontWeight={700} flex={1}>
                    {t("ticketDetail.resolutionAttachments")}
                  </Typography>
                  <Button component="label" variant="outlined" size="small">
                    {t("ticketDetail.selectFiles")}
                    <input
                      hidden
                      multiple
                      type="file"
                      accept=".pdf,.png,.jpg,.jpeg,.txt,.log,.csv,.docx,.xlsx"
                      onChange={(event) => {
                        setCardResolutionAttachments((current) => [
                          ...current,
                          ...Array.from(event.target.files ?? []),
                        ]);
                        event.target.value = "";
                      }}
                    />
                  </Button>
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {t("ticketDetail.resolutionAttachmentsHelp")}
                </Typography>
                {cardResolutionAttachments.map((file, index) => (
                  <Stack
                    key={`${file.name}-${file.size}-${index}`}
                    direction="row"
                    alignItems="center"
                    gap={1}
                  >
                    <Typography variant="body2" flex={1} noWrap>
                      {file.name} ({Math.ceil(file.size / 1024)} KB)
                    </Typography>
                    <Button
                      size="small"
                      color="error"
                      onClick={() =>
                        setCardResolutionAttachments((files) =>
                          files.filter((_, itemIndex) => itemIndex !== index),
                        )
                      }
                    >
                      {t("common.actions.delete")}
                    </Button>
                  </Stack>
                ))}
              </Stack>
            )}
          {cardTransitionTicket && cardRequiresResolution && (
            <>
              <TextField
                select
                required
                fullWidth
                margin="normal"
                label={t("ticketDetail.rootCauses")}
                value={cardRootCauseIds}
                onChange={(event) =>
                  setCardRootCauseIds(
                    (event.target.value as unknown as number[]).map(Number),
                  )
                }
                SelectProps={{
                  multiple: true,
                  renderValue: (value) =>
                    (value as number[])
                      .map((id) =>
                        getLocalizedName(
                          rootCauses.data?.find((cause) => cause.id === id) ?? {
                            id,
                            code: String(id),
                            name: `#${id}`,
                            requires_resolution_outcome: false,
                            requires_permanent_fix: false,
                          },
                          language,
                        ),
                      )
                      .join(", "),
                }}
                helperText={t("ticketDetail.rootCauseHelp")}
              >
                {rootCauses.data?.map((cause) => (
                  <MenuItem key={cause.id} value={cause.id}>
                    <Checkbox checked={cardRootCauseIds.includes(cause.id)} />
                    {getLocalizedName(cause, language)}
                  </MenuItem>
                ))}
              </TextField>
              {cardResolutionOutcomeRequired && (
                <TextField
                  select
                  required
                  fullWidth
                  margin="normal"
                  label={t("ticketDetail.resolutionOutcome")}
                  value={cardResolutionOutcomeId}
                  onChange={(event) =>
                    setCardResolutionOutcomeId(event.target.value)
                  }
                >
                  <MenuItem value="" disabled>
                    {t("ticketDetail.selectOutcome")}
                  </MenuItem>
                  {resolutionOutcomes.data?.map((outcome) => (
                    <MenuItem key={outcome.id} value={outcome.id}>
                      {getLocalizedName(outcome, language)}
                    </MenuItem>
                  ))}
                </TextField>
              )}
              {cardPermanentFixRequired && (
                <>
                  <TextField
                    select
                    required
                    fullWidth
                    margin="normal"
                    label={t("ticketDetail.permanentFixStatus")}
                    value={cardPermanentFixStatus}
                    onChange={(event) =>
                      setCardPermanentFixStatus(event.target.value)
                    }
                  >
                    {["PLANNED", "IMPLEMENTED", "VERIFIED"].map((status) => (
                      <MenuItem key={status} value={status}>
                        {t(`ticketDetail.${status.toLowerCase()}`)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    required
                    fullWidth
                    multiline
                    rows={2}
                    margin="normal"
                    label={t("ticketDetail.permanentFixEvidence")}
                    value={cardPermanentFixSummary}
                    onChange={(event) =>
                      setCardPermanentFixSummary(event.target.value)
                    }
                    inputProps={{ minLength: 5 }}
                  />
                </>
              )}
              <FormControlLabel
                control={
                  <Checkbox
                    checked={cardCreateKnowledge}
                    onChange={(event) =>
                      setCardCreateKnowledge(event.target.checked)
                    }
                  />
                }
                label={t("ticketDetail.createKnowledgeFromResolution")}
              />
              {bulkStatus === "RESOLVED" && hasPermission("ticket.close") && (
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={cardCloseAfterResolve}
                      onChange={(event) =>
                        setCardCloseAfterResolve(event.target.checked)
                      }
                    />
                  }
                  label={t("ticketDetail.closeAfterResolve")}
                />
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setStatusOpen(false);
              setChoosePendingStatus(false);
              setCardTransitionTicket(null);
              setCardResolutionAttachments([]);
              setCardKnowledgeSearch("");
              setCardKnowledgeError("");
            }}
          >
            {t("ticketsList.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={
              !bulkStatus ||
              ((bulkStatus.startsWith("PENDING_") ||
                bulkStatus === "CANCELLED" ||
                bulkStatus === "REOPENED" ||
                (Boolean(cardTransitionTicket) && cardRequiresResolution)) &&
                bulkReason.trim().length < 5) ||
              (bulkStatus.startsWith("PENDING_") &&
                (!bulkPendingOwner || !bulkPendingFollowUp)) ||
              (Boolean(cardTransitionTicket) &&
                ["RESOLVED", "CLOSED"].includes(bulkStatus) &&
                !cardResolutionServiceIds.length) ||
              (Boolean(cardTransitionTicket) &&
                cardRequiresResolution &&
                (!cardResolutionServiceIds.length ||
                  !cardRootCauseIds.length ||
                  (cardResolutionOutcomeRequired && !cardResolutionOutcomeId) ||
                  (cardPermanentFixRequired &&
                    cardPermanentFixSummary.trim().length < 5))) ||
              bulkStatusChange.isPending
            }
            onClick={() => bulkStatusChange.mutate()}
          >
            {bulkStatus === "RESOLVED"
              ? t("ticketsList.resolve", { defaultValue: "Resolve" })
              : t("ticketsList.changeStatus")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {t("ticketsList.deleteTitle", { count: selectedIds.length })}
        </DialogTitle>
        <DialogContent>
          <Alert severity="error">{t("ticketsList.deleteWarning")}</Alert>
          <TextField
            required
            fullWidth
            multiline
            rows={3}
            margin="normal"
            label={t("ticketsList.deletionReason")}
            value={bulkReason}
            onChange={(event) => setBulkReason(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteOpen(false)}>
            {t("ticketsList.cancel")}
          </Button>
          <Button
            color="error"
            variant="contained"
            startIcon={<Delete />}
            disabled={bulkReason.trim().length < 5 || bulkDelete.isPending}
            onClick={() => bulkDelete.mutate()}
          >
            {t("ticketsList.deletePermanently")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={saveOpen}
        onClose={() => {
          setSaveOpen(false);
          setEditingViewId(null);
        }}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>{t("ticketsList.saveTitle")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label={t("ticketsList.viewName")}
            value={viewName}
            onChange={(e) => setViewName(e.target.value)}
            error={saveView.isError}
            helperText={
              saveView.isError
                ? t("ticketsList.saveFailed")
                : t("ticketsList.saveHint")
            }
          />
          <TextField
            select
            fullWidth
            margin="normal"
            label={t("ticketsList.sharing")}
            value={viewScope}
            onChange={(event) => {
              setViewScope(
                event.target.value as
                  "PRIVATE" | "TEAM" | "DEPARTMENT" | "GLOBAL",
              );
              setViewTeamId("");
            }}
          >
            <MenuItem value="PRIVATE">{t("ticketsList.privateOnly")}</MenuItem>
            {shareableTeams.length > 0 && (
              <MenuItem value="TEAM">{t("ticketsList.team")}</MenuItem>
            )}
            {hasPermission("ticket.view.department") && user?.department_id && (
              <MenuItem value="DEPARTMENT">
                {t("ticketsList.department")}
              </MenuItem>
            )}
            {hasPermission("configuration.manage") && (
              <MenuItem value="GLOBAL">{t("ticketsList.global")}</MenuItem>
            )}
          </TextField>
          {viewScope === "TEAM" && (
            <TextField
              select
              required
              fullWidth
              margin="normal"
              label={t("ticketsList.supportTeam")}
              value={viewTeamId}
              onChange={(event) => setViewTeamId(event.target.value)}
            >
              {shareableTeams.map((team) => (
                <MenuItem key={team.id} value={team.id}>
                  {team.name}
                </MenuItem>
              ))}
            </TextField>
          )}
          <Stack direction="row" alignItems="center">
            <Checkbox
              checked={saveViewLayout}
              onChange={(event) => setSaveViewLayout(event.target.checked)}
            />
            <Typography>
              {t("ticketsList.saveLayoutWithView", {
                defaultValue: "Save current layout with this view",
              })}
            </Typography>
          </Stack>
          <Stack direction="row" alignItems="center">
            <Checkbox
              checked={makeDefault}
              onChange={(event) => setMakeDefault(event.target.checked)}
            />
            <Typography>{t("ticketsList.openDefault")}</Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          {editingViewId && (
            <Button
              color="error"
              startIcon={<Delete />}
              disabled={deleteSavedView.isPending}
              onClick={() => {
                deleteSavedView.mutate(editingViewId);
                setSaveOpen(false);
                setEditingViewId(null);
              }}
            >
              Delete
            </Button>
          )}
          {editingViewId && !makeDefault && (
            <Button
              disabled={makeDefaultView.isPending}
              onClick={() => {
                makeDefaultView.mutate(editingViewId);
                setMakeDefault(true);
              }}
            >
              {t("ticketsList.setDefault")}
            </Button>
          )}
          <Button
            onClick={() => {
              setSaveOpen(false);
              setEditingViewId(null);
            }}
          >
            {t("ticketsList.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={
              viewName.trim().length < 2 ||
              (viewScope === "TEAM" && !viewTeamId) ||
              (viewScope === "DEPARTMENT" && !user?.department_id) ||
              saveView.isPending
            }
            onClick={() => saveView.mutate()}
          >
            {editingViewId
              ? t("ticketsList.updateView")
              : t("ticketsList.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
