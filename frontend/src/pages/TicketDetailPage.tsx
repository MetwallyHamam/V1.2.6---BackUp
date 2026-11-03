import { ArrowBack, InfoOutlined } from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
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
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TicketClientAccessDialog } from "./TicketClientAccessDialog";
import { TicketSendActionsButton } from "../components/TicketSendActions";
import { TicketFlagsPanel } from "../components/TicketFlagsPanel";
import { ChangeRequestPanel } from "../components/ChangeRequestPanel";
import { ProblemPanel } from "../components/ProblemPanel";
import { MajorIncidentPanel } from "../components/MajorIncidentPanel";
import { TechnicalText } from "../components/TechnicalText";
import { getLocalizedName } from "../i18n/localizedMasterData";
import { UatTicketEvidencePanel } from "./UatTicketEvidencePanel";

type Ticket = {
  id: number;
  ticket_number: string;
  ticket_type_id: number;
  client_id: number;
  client_name?: string;
  contract_id?: number;
  due_at?: string;
  branch_id?: number;
  requester_contact_id?: number;
  service_id?: number;
  resolution_service_ids: number[];
  category_id?: number;
  subcategory_id?: number;
  affected_users?: string;
  patient_safety_flag: boolean;
  security_incident_flag: boolean;
  subject: string;
  description: string;
  priority: string;
  impact: string;
  urgency: string;
  status_id: number;
  version: number;
  assigned_user_id?: number;
  assigned_team?: string;
  routed_department_id?: number;
  routed_team_id?: number;
  routing_status?: string;
  help_request_result?: string;
  returned_at?: string;
  escalation_parent_ticket_id?: number;
  escalation_assignee_user_id?: number;
  escalation_level?: string;
  escalation_reason?: string;
  escalated_at?: string;
  resolution_summary?: string;
  root_cause_summary?: string;
  root_cause_ids: number[];
  root_causes: string[];
  resolution_outcome_id?: number;
  permanent_fix_summary?: string;
  permanent_fix_status?: string;
  pending_reason?: string;
  pending_owner_user_id?: number;
  pending_follow_up_at?: string;
  shift_handover_status?: string;
  shift_handover_reason?: string;
  shift_handover_by_user_id?: number;
  shift_handover_to_user_id?: number;
  shift_handover_at?: string;
  shift_handover_completed_at?: string;
  sla_first_response_target_minutes?: number;
  sla_first_response_actual_minutes?: number;
  sla_resolution_target_minutes?: number;
  sla_actual_business_minutes?: number;
  sla_saved_minutes?: number;
  sla_overrun_minutes?: number;
  sla_resolution_state?: string;
};
type Catalog = {
  id: number;
  code?: string;
  name: string;
  name_ar?: string | null;
  is_default_resolution_service?: boolean;
};
type ContractOption = {
  id: number;
  contract_number: string;
  name: string;
  end_date: string;
};
type TicketContext = {
  product_id?: number;
  product_module_id?: number;
  environment_id?: number;
};
type Comment = {
  id: number;
  author_user_id: number;
  is_internal: boolean;
  body: string;
  created_at: string;
};
type Status = {
  id: number;
  code: string;
  name: string;
  name_ar?: string | null;
};
type SlaClock = {
  id: number;
  contract_id?: number;
  policy_id: number;
  target_id?: number;
  calendar_id?: number;
  policy_version: number;
  calculation_version: string;
  match_reason?: string;
  clock_type: string;
  started_at: string;
  due_at: string;
  state: string;
  target_minutes: number;
  warning_percent: number;
  breached_at?: string;
  completed_at?: string;
};
type SlaEditPreview = {
  version: number;
  changes_sla: boolean;
  changed_fields: string[];
  effective_at: string;
  old_contract_id?: number;
  old_policy_id?: number;
  old_target_id?: number;
  old_first_response_minutes?: number;
  old_resolution_minutes?: number;
  new_contract_id?: number;
  new_policy_id?: number;
  new_target_id?: number;
  new_first_response_minutes?: number;
  new_resolution_minutes?: number;
  match_reason?: string;
};
type Assignee = {
  id: number;
  full_name: string;
  username: string;
  department?: string;
  job_title?: string;
  last_assigned_at?: string;
};
type SupportTeam = {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  department_id?: number;
};
type Department = {
  id: number;
  name: string;
  name_ar?: string | null;
  is_active: boolean;
};
type Attachment = {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  scan_status: string;
  created_at: string;
};
type Relation = {
  id: number;
  relation_type: string;
  direction: string;
  related_ticket_id: number;
  related_ticket_number: string;
  related_subject: string;
  related_priority: string;
};
type TicketOption = { id: number; ticket_number: string; subject: string };
type KnowledgeLink = {
  id: number;
  article_id: number;
  title: string;
  summary: string;
  category?: string;
  status: string;
};
type ArticleOption = {
  id: number;
  title: string;
  summary: string;
  category?: string;
  status: string;
  match_score?: number;
  match_reasons?: string[];
};
type ResolutionApplication = {
  article_id: number;
  article_version: number;
  resolution_summary: string;
  root_cause_ids: number[];
  resolution_service_ids: number[];
  resolution_outcome_id?: number | null;
  permanent_fix_summary?: string | null;
  permanent_fix_status?: string | null;
  match_score: number;
  match_reasons: string[];
};

export const showsResolutionWorkspace = (
  targetStatus: string,
  requireResolutionOnClose: boolean,
) =>
  targetStatus === "CLOSED" ||
  (targetStatus === "RESOLVED" && !requireResolutionOnClose);
type ArticleDetail = ArticleOption & {
  body: string;
  tags?: string;
  client_visible: boolean;
  version: number;
};
type TimelineEvent = {
  id: string;
  event_type: string;
  title: string;
  description?: string;
  actor_name?: string;
  is_internal: boolean;
  created_at: string;
};
type Contact = {
  id: number;
  full_name: string;
  phone_number?: string;
  email?: string;
  job_title?: string;
  is_active: boolean;
};
type Follower = {
  user_id: number;
  full_name: string;
  username: string;
  created_at: string;
};
type MentionCandidate = {
  id: number;
  full_name: string;
  email: string;
  user_type: string;
};
type TicketTask = {
  id: number;
  title: string;
  description?: string;
  assigned_user_id?: number;
  status: string;
  due_at?: string;
  completed_at?: string;
};
type ChecklistItem = {
  id: number;
  label: string;
  sort_order: number;
  is_completed: boolean;
};
type ResolutionOutcome = Catalog & { requires_permanent_fix: boolean };
type RootCause = Catalog & {
  requires_resolution_outcome: boolean;
  requires_permanent_fix: boolean;
};
type ResolutionAiSuggestion = {
  professional_resolution: string;
  customer_resolution: string;
  suggested_root_cause: string;
  root_cause_id?: number;
  preventive_action: string;
  resolution_summary: string;
  suggest_knowledge_base_article: boolean;
  knowledge_base_title: string;
  evidence_used: string[];
  missing_closure_information: string[];
};
type Worklog = {
  id: number;
  task_id?: number;
  user_id: number;
  started_at: string;
  ended_at: string;
  duration_minutes: number;
  notes: string;
  status: string;
  approved_by_user_id?: number;
  rejection_reason?: string;
  version: number;
};

function whatsappUrl(phoneNumber?: string) {
  if (!phoneNumber) return null;
  let digits = phoneNumber.replace(/\D/g, "");
  if (!digits) return null;
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (!digits.startsWith("20"))
    digits = digits.startsWith("0") ? `20${digits.slice(1)}` : `20${digits}`;
  return `https://wa.me/${digits}`;
}

export function TicketDetailPage() {
  const commentOperationKey = useRef<string | null>(null);
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const localized = (
    item: { name: string; name_ar?: string | null } | undefined,
  ) => getLocalizedName(item, language);
  const slaDuration = (minutes?: number) =>
    minutes == null
      ? t("portalTicketDetail.notAvailable")
      : minutes < 60
        ? t("time.minutes", { count: minutes })
        : t("time.hours", { count: Math.round(minutes / 6) / 10 });
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = (location.state as { returnTo?: string } | null)?.returnTo;
  const [actionParams, setActionParams] = useSearchParams();
  const [statusHistoryOnly, setStatusHistoryOnly] = useState(false);
  const queryClient = useQueryClient();
  const { hasPermission, user } = useAuth();
  const [internal, setInternal] = useState(false);
  const [statusDialog, setStatusDialog] = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  const [resolutionServiceIds, setResolutionServiceIds] = useState<number[]>(
    [],
  );
  const [resolutionAttachments, setResolutionAttachments] = useState<File[]>(
    [],
  );
  const [transitionSubmitting, setTransitionSubmitting] = useState(false);
  const [closeAfterResolve, setCloseAfterResolve] = useState(
    Boolean(user?.auto_close_on_resolve),
  );
  const [createKnowledgeArticle, setCreateKnowledgeArticle] = useState(false);
  const [saveCloseDefault, setSaveCloseDefault] = useState(false);
  const [transitionError, setTransitionError] = useState("");
  const [resolutionRootCauseIds, setResolutionRootCauseIds] = useState<
    number[]
  >([]);
  const [assignmentDialog, setAssignmentDialog] = useState(false);
  const [assignmentError, setAssignmentError] = useState("");
  const [assignmentSearch, setAssignmentSearch] = useState("");
  const [handoverDialog, setHandoverDialog] = useState(false);
  const [handoverError, setHandoverError] = useState("");
  const [escalationDialog, setEscalationDialog] = useState(false);
  const [escalationChoiceDialog, setEscalationChoiceDialog] = useState(false);
  const [escalationError, setEscalationError] = useState("");
  const [escalationSearch, setEscalationSearch] = useState("");
  const [helpDialog, setHelpDialog] = useState(false);
  const [helpDepartmentId, setHelpDepartmentId] = useState("");
  const [helpError, setHelpError] = useState("");
  const [returnDialog, setReturnDialog] = useState(false);
  const [callerDialog, setCallerDialog] = useState(false);
  const [newCallerDialog, setNewCallerDialog] = useState(false);
  const [callerSelection, setCallerSelection] = useState("");
  const [callerError, setCallerError] = useState("");
  const [followersDialog, setFollowersDialog] = useState(false);
  const [followerIds, setFollowerIds] = useState<number[]>([]);
  const [followersError, setFollowersError] = useState("");
  const [taskDialog, setTaskDialog] = useState(false);
  const [checklistDialog, setChecklistDialog] = useState(false);
  const [worklogDialog, setWorklogDialog] = useState(false);
  const [ticketEventDialog, setTicketEventDialog] = useState(false);
  const [ticketEventTime, setTicketEventTime] = useState("");
  const [ticketEventText, setTicketEventText] = useState("");
  const [ticketEventOwner, setTicketEventOwner] = useState("");
  const [ticketEventError, setTicketEventError] = useState("");
  const [attachmentError, setAttachmentError] = useState("");
  const [relationDialog, setRelationDialog] = useState(false);
  const [relationSearch, setRelationSearch] = useState("");
  const [relationError, setRelationError] = useState("");
  const [relationTicketIds, setRelationTicketIds] = useState<number[]>([]);
  const [knowledgeDialog, setKnowledgeDialog] = useState(false);
  const [templateDialog, setTemplateDialog] = useState(false);
  const [mentionDialog, setMentionDialog] = useState(false);
  const [mentionRecipients, setMentionRecipients] = useState<
    MentionCandidate[]
  >([]);
  const [mentionMessage, setMentionMessage] = useState("");
  const [mentionInternal, setMentionInternal] = useState(false);
  const [mentionFollowers, setMentionFollowers] = useState(false);
  const [mentionError, setMentionError] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [knowledgeSearch, setKnowledgeSearch] = useState("");
  const [selectedKnowledgeArticleId, setSelectedKnowledgeArticleId] =
    useState("");
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [resolutionOutcomeId, setResolutionOutcomeId] = useState("");
  const [permanentFixSummary, setPermanentFixSummary] = useState("");
  const [permanentFixStatus, setPermanentFixStatus] = useState("PLANNED");
  const [resolutionAiSuggestion, setResolutionAiSuggestion] =
    useState<ResolutionAiSuggestion | null>(null);
  const [resolutionAiLoading, setResolutionAiLoading] = useState(false);
  const [resolutionAiError, setResolutionAiError] = useState("");
  const [knowledgeError, setKnowledgeError] = useState("");
  const [viewArticleId, setViewArticleId] = useState<number | null>(null);
  const [editDialog, setEditDialog] = useState(false);
  const [editError, setEditError] = useState("");
  const [editCategoryId, setEditCategoryId] = useState("");
  const [editClientId, setEditClientId] = useState("");
  const [editProductId, setEditProductId] = useState("");
  const [slaEditPreview, setSlaEditPreview] = useState<SlaEditPreview | null>(
    null,
  );
  const [pendingEditPayload, setPendingEditPayload] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [slaReevaluationReason, setSlaReevaluationReason] = useState("");
  const [slaPreviewError, setSlaPreviewError] = useState("");
  const ticket = useQuery({
    queryKey: ["ticket", id],
    queryFn: async () =>
      (await api.get<Ticket & TicketContext>(`/tickets/${id}`)).data,
  });
  const siteSettings = useQuery({
    queryKey: ["site-settings", "ticket-resolution-workflow"],
    queryFn: async () =>
      (
        await api.get<{ resolution_details_required_on_close?: boolean }>(
          "/system/site-settings",
        )
      ).data,
  });
  const requireResolutionOnClose =
    siteSettings.data?.resolution_details_required_on_close === true;
  // An explicit Close action must always expose the complete resolution
  // workspace. Besides enforcing close-time requirements, this lets an
  // engineer review or complete evidence that was missed during resolution.
  const resolutionDetailsTarget = showsResolutionWorkspace(
    targetStatus,
    requireResolutionOnClose,
  );
  const departmentRequests = useQuery({
    queryKey: ["ticket-department-requests", id],
    queryFn: async () =>
      (await api.get<Ticket[]>(`/tickets/${id}/department-requests`)).data,
    enabled: Boolean(ticket.data && !ticket.data.escalation_parent_ticket_id),
  });
  const allowedTransitions = useQuery({
    queryKey: ["ticket-allowed-transitions", id, ticket.data?.version],
    queryFn: async () =>
      (await api.get<Status[]>(`/tickets/${id}/allowed-transitions`)).data,
    enabled: Boolean(ticket.data),
  });
  const callerContacts = useQuery({
    queryKey: ["ticket-caller", ticket.data?.client_id],
    queryFn: async () =>
      (
        await api.get<Contact[]>("/contacts", {
          params: { client_id: ticket.data?.client_id },
        })
      ).data,
    enabled: Boolean(ticket.data?.client_id),
  });
  const followers = useQuery({
    queryKey: ["ticket-followers", id],
    queryFn: async () =>
      (await api.get<Follower[]>(`/tickets/${id}/followers`)).data,
  });
  const mentionCandidates = useQuery({
    queryKey: ["ticket-mention-candidates", id, mentionInternal],
    queryFn: async () =>
      (
        await api.get<MentionCandidate[]>(`/tickets/${id}/mention-candidates`, {
          params: { is_internal: mentionInternal },
        })
      ).data,
    enabled: mentionDialog && hasPermission("ticket.mention"),
  });
  const tasks = useQuery({
    queryKey: ["ticket-tasks", id],
    queryFn: async () =>
      (await api.get<TicketTask[]>(`/tickets/${id}/tasks`)).data,
  });
  const checklist = useQuery({
    queryKey: ["ticket-checklist", id],
    queryFn: async () =>
      (await api.get<ChecklistItem[]>(`/tickets/${id}/checklist`)).data,
  });
  const worklogs = useQuery({
    queryKey: ["ticket-worklogs", id],
    queryFn: async () =>
      (await api.get<Worklog[]>(`/tickets/${id}/worklogs`)).data,
  });
  const comments = useQuery({
    queryKey: ["ticket-comments", id],
    queryFn: async () =>
      (await api.get<Comment[]>(`/tickets/${id}/comments`)).data,
  });
  const timeline = useQuery({
    queryKey: ["ticket-timeline", id],
    queryFn: async () =>
      (await api.get<TimelineEvent[]>(`/tickets/${id}/timeline`)).data,
  });
  const statuses = useQuery({
    queryKey: ["ticket-statuses"],
    queryFn: async () => (await api.get<Status[]>("/ticket-statuses")).data,
  });
  const services = useQuery({
    queryKey: ["resolution-services", ticket.data?.client_id],
    queryFn: async () =>
      (
        await api.get<{ services: Catalog[] }>("/ticket-contract-catalog", {
          params: { client_id: ticket.data?.client_id },
        })
      ).data.services,
    enabled: Boolean(ticket.data?.client_id),
  });
  useEffect(() => {
    if (
      !["RESOLVED", "CLOSED"].includes(targetStatus) ||
      resolutionServiceIds.length > 0 ||
      !services.data
    )
      return;
    const defaultResolutionService = services.data.find(
      (item) => item.is_default_resolution_service,
    );
    setResolutionServiceIds(
      defaultResolutionService ? [defaultResolutionService.id] : [],
    );
  }, [
    resolutionServiceIds.length,
    services.data,
    targetStatus,
    ticket.data?.service_id,
  ]);
  useEffect(() => {
    if (!resolutionDetailsTarget || !ticket.data) return;
    setResolutionSummary(ticket.data.resolution_summary ?? "");
    setResolutionRootCauseIds(ticket.data.root_cause_ids ?? []);
    setResolutionServiceIds(ticket.data.resolution_service_ids ?? []);
    setResolutionOutcomeId(
      ticket.data.resolution_outcome_id
        ? String(ticket.data.resolution_outcome_id)
        : "",
    );
    setPermanentFixSummary(ticket.data.permanent_fix_summary ?? "");
    setPermanentFixStatus(ticket.data.permanent_fix_status ?? "PLANNED");
  }, [resolutionDetailsTarget, targetStatus, ticket.data]);
  const rootCauses = useQuery({
    queryKey: ["root-causes"],
    queryFn: async () => (await api.get<RootCause[]>("/root-causes")).data,
  });
  const selectedRootCauses = (rootCauses.data ?? []).filter((item) =>
    resolutionRootCauseIds.includes(item.id),
  );
  const resolutionOutcomeRequired = selectedRootCauses.some(
    (item) => item.requires_resolution_outcome,
  );
  const permanentFixRequired = selectedRootCauses.some(
    (item) => item.requires_permanent_fix,
  );
  const resolutionOutcomes = useQuery({
    queryKey: ["resolution-outcomes"],
    queryFn: async () =>
      (await api.get<ResolutionOutcome[]>("/resolution-outcomes")).data,
  });
  async function generateResolutionWithLocalAi() {
    if (!id) return;
    setResolutionAiLoading(true);
    setResolutionAiError("");
    try {
      const result = (
        await api.post<ResolutionAiSuggestion>(
          `/tickets/ai/${id}/resolution`,
          { draft_resolution: resolutionSummary },
          { timeout: 150_000 },
        )
      ).data;
      setResolutionAiSuggestion(result);
      if (result.resolution_summary || result.professional_resolution)
        setResolutionSummary(
          result.resolution_summary || result.professional_resolution,
        );
      if (result.root_cause_id)
        setResolutionRootCauseIds([result.root_cause_id]);
      setCreateKnowledgeArticle(result.suggest_knowledge_base_article);
    } catch (requestError) {
      setResolutionAiError(
        apiErrorMessage(
          requestError,
          "The local AI could not draft the resolution.",
        ),
      );
    } finally {
      setResolutionAiLoading(false);
    }
  }
  const products = useQuery({
    queryKey: ["products"],
    queryFn: async () => (await api.get<Catalog[]>("/products")).data,
  });
  const environments = useQuery({
    queryKey: ["environments"],
    queryFn: async () => (await api.get<Catalog[]>("/environments")).data,
  });
  const editModules = useQuery({
    queryKey: ["ticket-edit-modules", editProductId],
    queryFn: async () =>
      (await api.get<Catalog[]>(`/products/${editProductId}/modules`)).data,
    enabled: editDialog && Boolean(editProductId),
  });
  const selectedContract = useQuery({
    queryKey: ["ticket-selected-contract", ticket.data?.contract_id],
    enabled: Boolean(
      ticket.data?.contract_id && hasPermission("contract.view"),
    ),
    queryFn: async () =>
      (await api.get<ContractOption>(`/contracts/${ticket.data?.contract_id}`))
        .data,
  });
  const ticketTypes = useQuery({
    queryKey: ["ticket-types"],
    queryFn: async () => (await api.get<Catalog[]>("/ticket-types")).data,
  });
  const ticketCategories = useQuery({
    queryKey: ["ticket-categories"],
    queryFn: async () => (await api.get<Catalog[]>("/ticket-categories")).data,
    enabled: editDialog,
  });
  const ticketSubcategories = useQuery({
    queryKey: ["ticket-subcategories", editCategoryId],
    queryFn: async () =>
      (
        await api.get<Catalog[]>(
          `/ticket-categories/${editCategoryId}/subcategories`,
        )
      ).data,
    enabled: editDialog && Boolean(editCategoryId),
  });
  const ticketClients = useQuery({
    queryKey: ["ticket-edit-clients"],
    queryFn: async () =>
      (await api.get<Catalog[]>("/clients/ticket-options")).data,
    enabled: editDialog && hasPermission("ticket.change.client"),
  });
  const ticketContracts = useQuery({
    queryKey: ["ticket-edit-contracts", editClientId],
    queryFn: async () =>
      (
        await api.get<ContractOption[]>("/contracts", {
          params: { client_id: editClientId },
        })
      ).data,
    enabled:
      editDialog &&
      Boolean(editClientId) &&
      hasPermission("ticket.change.contract"),
  });
  const sla = useQuery({
    queryKey: ["ticket-sla", id],
    queryFn: async () => (await api.get<SlaClock[]>(`/tickets/${id}/sla`)).data,
    enabled: hasPermission("contract.view"),
  });
  const assignees = useQuery({
    queryKey: ["ticket-assignees", "display", ticket.data?.assigned_user_id],
    queryFn: async () =>
      (
        await api.get<Assignee[]>("/ticket-assignees", {
          params: { include_user_id: ticket.data?.assigned_user_id },
        })
      ).data,
    enabled: Boolean(ticket.data),
  });
  const assignmentAssignees = useQuery({
    queryKey: ["ticket-assignees", "assignment", assignmentSearch],
    queryFn: async () =>
      (
        await api.get<Assignee[]>("/ticket-assignees", {
          params: { q: assignmentSearch.trim() || undefined, limit: 100 },
        })
      ).data,
    enabled: assignmentDialog && hasPermission("ticket.assign.team"),
  });
  const supportTeams = useQuery({
    queryKey: ["support-teams"],
    queryFn: async () => (await api.get<SupportTeam[]>("/support-teams")).data,
    enabled:
      hasPermission("ticket.assign.team") ||
      hasPermission("ticket.help.request"),
  });
  const departments = useQuery({
    queryKey: ["departments", "ticket-help"],
    queryFn: async () => (await api.get<Department[]>("/departments")).data,
    enabled:
      helpDialog ||
      escalationDialog ||
      Boolean(ticket.data?.routed_department_id),
  });
  const attachments = useQuery({
    queryKey: ["ticket-attachments", id],
    queryFn: async () =>
      (await api.get<Attachment[]>(`/tickets/${id}/attachments`)).data,
  });
  const relations = useQuery({
    queryKey: ["ticket-relations", id],
    queryFn: async () =>
      (await api.get<Relation[]>(`/tickets/${id}/relations`)).data,
  });
  const relationCandidates = useQuery({
    queryKey: ["ticket-relation-search", relationSearch],
    queryFn: async () =>
      (
        await api.get<TicketOption[]>("/tickets", {
          params: { search: relationSearch, limit: 20 },
        })
      ).data,
    enabled: relationDialog && relationSearch.trim().length >= 2,
  });
  const knowledgeLinks = useQuery({
    queryKey: ["ticket-knowledge", id],
    queryFn: async () =>
      (await api.get<KnowledgeLink[]>(`/knowledge/tickets/${id}/links`)).data,
    enabled: hasPermission("knowledge.view"),
  });
  const knowledgeRecommendations = useQuery({
    queryKey: ["ticket-knowledge-recommendations", id],
    queryFn: async () =>
      (
        await api.get<ArticleOption[]>(
          `/knowledge/tickets/${id}/recommendations`,
        )
      ).data,
    enabled:
      hasPermission("knowledge.view") &&
      (knowledgeDialog ||
        (statusDialog && ["RESOLVED", "CLOSED"].includes(targetStatus))),
  });
  const articleCandidates = useQuery({
    queryKey: ["ticket-knowledge-search", knowledgeSearch],
    queryFn: async () =>
      (
        await api.get<ArticleOption[]>("/knowledge", {
          params: {
            search: knowledgeSearch.trim() || undefined,
            published_only: true,
            limit: 50,
          },
        })
      ).data,
    enabled:
      hasPermission("knowledge.view") &&
      (knowledgeDialog ||
        (statusDialog && ["RESOLVED", "CLOSED"].includes(targetStatus))),
  });
  useEffect(() => {
    if (
      statusDialog &&
      targetStatus === "RESOLVED" &&
      ticket.data &&
      !knowledgeSearch
    ) {
      setKnowledgeSearch(ticket.data.subject);
    }
  }, [knowledgeSearch, statusDialog, targetStatus, ticket.data]);
  const viewedArticle = useQuery({
    queryKey: ["knowledge-article", viewArticleId],
    queryFn: async () =>
      (await api.get<ArticleDetail>(`/knowledge/articles/${viewArticleId}`))
        .data,
    enabled: Boolean(viewArticleId),
  });
  const uploadAttachment = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api.post(`/tickets/${id}/attachments`, body);
    },
    onSuccess: async () => {
      setAttachmentError("");
      await queryClient.invalidateQueries({
        queryKey: ["ticket-attachments", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
    onError: () =>
      setAttachmentError(
        "The attachment could not be uploaded. Check its type and 8 MB size limit.",
      ),
  });
  const addComment = useMutation({
    mutationFn: async (body: string) =>
      api.post(`/tickets/${id}/comments`, {
        body,
        is_internal: internal,
        operation_key: (commentOperationKey.current ??= crypto.randomUUID()),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["ticket-comments", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
  });
  const addTicketEvent = useMutation({
    mutationFn: async () =>
      api.post(`/ticket-reports/tickets/${id}/events`, {
        occurred_at: new Date(ticketEventTime).toISOString(),
        event: ticketEventText.trim(),
        owner: ticketEventOwner.trim() || null,
      }),
    onSuccess: async () => {
      setTicketEventDialog(false);
      setTicketEventTime("");
      setTicketEventText("");
      setTicketEventOwner("");
      setTicketEventError("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
        queryClient.invalidateQueries({ queryKey: ["ticket-timeline", id] }),
      ]);
    },
    onError: (error) =>
      setTicketEventError(
        apiErrorMessage(error, "The ticket event could not be saved."),
      ),
  });
  const createMention = useMutation({
    mutationFn: async () =>
      api.post(`/tickets/${id}/mentions`, {
        recipient_user_ids: mentionRecipients.map((item) => item.id),
        message: mentionMessage.trim(),
        is_internal: mentionInternal,
        add_as_followers: mentionFollowers,
        operation_key: crypto.randomUUID(),
      }),
    onSuccess: async () => {
      setMentionDialog(false);
      setMentionRecipients([]);
      setMentionMessage("");
      setMentionFollowers(false);
      setMentionError("");
      setCommentBody("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ticket-comments", id] }),
        queryClient.invalidateQueries({ queryKey: ["ticket-followers", id] }),
        queryClient.invalidateQueries({ queryKey: ["ticket-timeline", id] }),
        queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
      ]);
    },
    onError: (error) =>
      setMentionError(apiErrorMessage(error, "The mention could not be sent.")),
  });
  const editTicket = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch(`/tickets/${id}`, payload),
    onSuccess: async () => {
      setEditDialog(false);
      setEditError("");
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
    onError: () =>
      setEditError(
        "The ticket could not be edited. Check your field permissions or refresh the ticket.",
      ),
  });
  const previewTicketSla = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post<SlaEditPreview>(`/tickets/${id}/sla-preview`, payload))
        .data,
    onSuccess: (preview, payload) => {
      const currentPayload = { ...payload, version: preview.version };
      if (!preview.changes_sla) {
        editTicket.mutate(currentPayload);
        return;
      }
      setSlaPreviewError("");
      setPendingEditPayload(currentPayload);
      setSlaEditPreview(preview);
    },
    onError: (error) =>
      setEditError(
        apiErrorMessage(
          error,
          "The SLA impact could not be calculated. Refresh the ticket and review the selected contract context.",
        ),
      ),
  });
  const changeStatus = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/transition`, payload),
    onSuccess: async () => {
      setStatusDialog(false);
      setTargetStatus("");
      setResolutionServiceIds([]);
      setResolutionAttachments([]);
      setCreateKnowledgeArticle(false);
      setTransitionError("");
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
    onError: () =>
      setTransitionError(
        "The status could not be changed. Check the workflow and required resolution fields.",
      ),
  });
  const assign = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/assignment`, payload),
    onSuccess: async () => {
      setAssignmentDialog(false);
      setAssignmentError("");
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
    onError: () =>
      setAssignmentError(
        "The engineer could not be assigned. Refresh the ticket and try again.",
      ),
  });
  const handover = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/shift-handover`, payload),
    onSuccess: async () => {
      setHandoverDialog(false);
      setHandoverError("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
        queryClient.invalidateQueries({ queryKey: ["ticket-timeline", id] }),
        queryClient.invalidateQueries({ queryKey: ["tickets"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
      ]);
    },
    onError: () =>
      setHandoverError(
        "The shift handover could not be saved. Refresh the ticket and verify the receiving engineer.",
      ),
  });
  const completeHandover = useMutation({
    mutationFn: async () =>
      api.post(`/tickets/${id}/shift-handover/complete`, {
        note: "Receiving shift accepted the ticket",
        version: ticket.data?.version,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
        queryClient.invalidateQueries({ queryKey: ["tickets"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
      ]);
    },
  });
  const claim = useMutation({
    mutationFn: async () =>
      api.post(`/tickets/${id}/claim`, { version: ticket.data?.version }),
    onSuccess: async () => {
      setAssignmentError("");
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
    onError: () =>
      setAssignmentError(
        "The ticket could not be assigned to you. Refresh it and try again.",
      ),
  });
  const escalate = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/escalation`, payload),
    onSuccess: async () => {
      setEscalationDialog(false);
      setEscalationError("");
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: () =>
      setEscalationError(
        "The escalation could not be saved. Refresh the ticket and verify the selected employee.",
      ),
  });
  const requestHelp = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/help-request`, payload),
    onSuccess: async (response) => {
      setHelpDialog(false);
      setHelpError("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
        queryClient.invalidateQueries({ queryKey: ["ticket-relations", id] }),
        queryClient.invalidateQueries({ queryKey: ["notifications"] }),
      ]);
      navigate(`/tickets/${response.data.id}`);
    },
    onError: () =>
      setHelpError(
        "The department request could not be created. Check the selected department, team, and engineer.",
      ),
  });
  const returnHelp = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/return-result`, payload),
    onSuccess: async () => {
      setReturnDialog(false);
      setHelpError("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ticket", id] }),
        queryClient.invalidateQueries({ queryKey: ["notifications"] }),
      ]);
    },
    onError: () =>
      setHelpError(
        "The result could not be returned. Refresh the request and try again.",
      ),
  });
  const updateCaller = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch(`/tickets/${id}/requester`, payload),
    onSuccess: async () => {
      setCallerDialog(false);
      setCallerError("");
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
    onError: () =>
      setCallerError(
        "The caller could not be changed. Refresh the ticket and verify the selected contact.",
      ),
  });
  const createCaller = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post<Contact>("/contacts", payload)).data,
    onSuccess: async (contact) => {
      setCallerSelection(String(contact.id));
      setNewCallerDialog(false);
      setCallerError("");
      await queryClient.invalidateQueries({
        queryKey: ["ticket-caller", ticket.data?.client_id],
      });
    },
    onError: () => setCallerError(t("ticketDetail.callerCreateFailed")),
  });
  const updateFollowers = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.put(`/tickets/${id}/followers`, payload),
    onSuccess: async () => {
      setFollowersDialog(false);
      setFollowersError("");
      await queryClient.invalidateQueries({
        queryKey: ["ticket-followers", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      await queryClient.invalidateQueries({
        queryKey: ["ticket-timeline", id],
      });
    },
    onError: () =>
      setFollowersError(
        "Followers could not be updated. Refresh the ticket and try again.",
      ),
  });
  const createTask = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/tasks`, payload),
    onSuccess: async () => {
      setTaskDialog(false);
      await queryClient.invalidateQueries({ queryKey: ["ticket-tasks", id] });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
    },
  });
  const updateTask = useMutation({
    mutationFn: async ({
      taskId,
      status,
    }: {
      taskId: number;
      status: string;
    }) => api.patch(`/tickets/${id}/tasks/${taskId}`, { status }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["ticket-tasks", id] });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
    },
  });
  const createChecklistItem = useMutation({
    mutationFn: async (label: string) =>
      api.post(`/tickets/${id}/checklist`, {
        label,
        sort_order: checklist.data?.length ?? 0,
      }),
    onSuccess: async () => {
      setChecklistDialog(false);
      await queryClient.invalidateQueries({
        queryKey: ["ticket-checklist", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
    },
  });
  const toggleChecklistItem = useMutation({
    mutationFn: async (item: ChecklistItem) =>
      api.patch(`/tickets/${id}/checklist/${item.id}`, {
        is_completed: !item.is_completed,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["ticket-checklist", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
    },
  });
  const createWorklog = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/tickets/${id}/worklogs`, payload),
    onSuccess: async () => {
      setWorklogDialog(false);
      await queryClient.invalidateQueries({
        queryKey: ["ticket-worklogs", id],
      });
    },
  });
  const submitWorklog = useMutation({
    mutationFn: async (worklogId: number) =>
      api.post(`/tickets/${id}/worklogs/${worklogId}/submit`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["ticket-worklogs", id] }),
  });
  const decideWorklog = useMutation({
    mutationFn: async ({
      item,
      approved,
    }: {
      item: Worklog;
      approved: boolean;
    }) =>
      api.post(`/tickets/${id}/worklogs/${item.id}/decision`, {
        approved,
        version: item.version,
        reason: approved ? null : "Returned for correction",
      }),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["ticket-worklogs", id] }),
  });
  const createRelation = useMutation({
    mutationFn: async (payloads: Array<Record<string, unknown>>) =>
      Promise.all(
        payloads.map((payload) =>
          api.post(`/tickets/${id}/relations`, payload),
        ),
      ),
    onSuccess: async () => {
      setRelationDialog(false);
      setRelationSearch("");
      setRelationTicketIds([]);
      setRelationError("");
      await queryClient.invalidateQueries({
        queryKey: ["ticket-relations", id],
      });
      await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
    },
    onError: () =>
      setRelationError(
        "The relationship could not be created. It may already exist or the ticket may not be visible.",
      ),
  });
  const removeRelation = useMutation({
    mutationFn: async (relationId: number) =>
      api.delete(`/tickets/${id}/relations/${relationId}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["ticket-relations", id] }),
  });
  const linkArticle = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(`/knowledge/tickets/${id}/links`, payload),
    onSuccess: async () => {
      setKnowledgeDialog(false);
      setKnowledgeSearch("");
      setSelectedKnowledgeArticleId("");
      setKnowledgeError("");
      await queryClient.invalidateQueries({
        queryKey: ["ticket-knowledge", id],
      });
    },
    onError: () =>
      setKnowledgeError(
        "The article could not be linked. It may already be linked.",
      ),
  });
  const unlinkArticle = useMutation({
    mutationFn: async (linkId: number) =>
      api.delete(`/knowledge/tickets/${id}/links/${linkId}`),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["ticket-knowledge", id] }),
  });
  const applyKnowledgeResolution = useMutation({
    mutationFn: async (articleId: number) =>
      (
        await api.post<ResolutionApplication>(
          `/knowledge/tickets/${id}/articles/${articleId}/apply-resolution`,
        )
      ).data,
    onSuccess: async (result) => {
      setResolutionSummary(result.resolution_summary);
      setResolutionRootCauseIds(result.root_cause_ids);
      setResolutionServiceIds(result.resolution_service_ids);
      setResolutionOutcomeId(
        result.resolution_outcome_id
          ? String(result.resolution_outcome_id)
          : "",
      );
      setPermanentFixSummary(result.permanent_fix_summary ?? "");
      setPermanentFixStatus(result.permanent_fix_status ?? "PLANNED");
      setKnowledgeError("");
      await queryClient.invalidateQueries({
        queryKey: ["ticket-knowledge", id],
      });
    },
    onError: (cause) =>
      setKnowledgeError(
        apiErrorMessage(
          cause,
          "The knowledge resolution could not be applied.",
        ),
      ),
  });
  const createTemplate = useMutation({
    mutationFn: async (payload: {
      name: string;
      keywords: string;
      scope: string;
      portal_visible: boolean;
    }) => api.post(`/tickets/${id}/template`, payload),
    onSuccess: () => setTemplateDialog(false),
  });
  async function submitTransition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ticket.data) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    setTransitionError("");
    setTransitionSubmitting(true);
    if (
      targetStatus === "RESOLVED" &&
      saveCloseDefault &&
      hasPermission("ticket.auto_close_on_resolve")
    ) {
      try {
        await api.put("/auth/me/resolve-preference", {
          auto_close_on_resolve: closeAfterResolve,
        });
      } catch {
        setTransitionError("Your default close preference could not be saved.");
        setTransitionSubmitting(false);
        return;
      }
    }
    try {
      let transitionVersion = ticket.data.version;
      for (const file of resolutionAttachments) {
        const body = new FormData();
        body.append("file", file);
        await api.post(`/tickets/${id}/attachments`, body);
        transitionVersion += 1;
      }
      await changeStatus.mutateAsync({
        to_status_code: targetStatus,
        resolution_service_ids: resolutionDetailsTarget && !isChangeRequest
          ? resolutionServiceIds
          : [],
        reason: String(values.reason).trim() || null,
        resolution_summary: resolutionDetailsTarget
          ? String(values.resolution_summary).trim()
          : null,
        root_cause_summary: null,
        root_cause_ids:
          resolutionDetailsTarget && !isChangeRequest
            ? resolutionRootCauseIds
            : [],
        resolution_outcome_id:
          resolutionDetailsTarget && resolutionOutcomeId
            ? Number(resolutionOutcomeId)
            : null,
        permanent_fix_summary:
          resolutionDetailsTarget && permanentFixSummary
            ? permanentFixSummary.trim() || null
            : null,
        permanent_fix_status:
          resolutionDetailsTarget && permanentFixStatus
            ? permanentFixStatus || null
            : null,
        version: transitionVersion,
        close_after_resolve:
          targetStatus === "RESOLVED" &&
          !requireResolutionOnClose &&
          closeAfterResolve,
        create_knowledge_article:
          resolutionDetailsTarget && createKnowledgeArticle,
        pending_owner_user_id:
          targetStatus.startsWith("PENDING_") && values.pending_owner_user_id
            ? Number(values.pending_owner_user_id)
            : null,
        pending_follow_up_at: targetStatus.startsWith("PENDING_")
          ? new Date(String(values.pending_follow_up_at)).toISOString()
          : null,
        pending_responsible_party: targetStatus.startsWith("PENDING_")
          ? String(values.pending_responsible_party)
          : null,
      });
      if (["RESOLVED", "CLOSED"].includes(targetStatus)) {
        setStatusDialog(false);
        if (returnTo) navigate(returnTo, { replace: true });
      }
      await queryClient.invalidateQueries({
        queryKey: ["ticket-attachments", id],
      });
    } catch (caught) {
      const serverMessage = axios.isAxiosError(caught)
        ? caught.response?.data?.error?.message
        : null;
      setTransitionError(
        serverMessage ||
          (resolutionAttachments.length
            ? "The attachment or status change failed. Any successfully uploaded files remain on the ticket; review the attachment list before retrying."
            : "The status could not be changed. Check the workflow and required fields."),
      );
    } finally {
      setTransitionSubmitting(false);
    }
  }
  function submitAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ticket.data) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const assignedUserId = Number(values.assigned_user_id);
    const engineer =
      assignmentAssignees.data?.find((item) => item.id === assignedUserId) ??
      assignees.data?.find((item) => item.id === assignedUserId);
    assign.mutate({
      assigned_user_id: assignedUserId,
      assigned_team:
        String(values.assigned_team).trim() || engineer?.department || null,
      reason: String(values.reason).trim() || null,
      version: ticket.data.version,
    });
  }
  function submitEscalation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ticket.data) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    escalate.mutate({
      escalation_assignee_user_id: values.escalation_assignee_user_id
        ? Number(values.escalation_assignee_user_id)
        : null,
      escalation_level: values.escalation_assignee_user_id
        ? String(values.escalation_level)
        : null,
      reason: String(values.reason).trim(),
      version: ticket.data.version,
    });
  }
  function submitCaller(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    updateCaller.mutate({
      requester_contact_id: values.requester_contact_id
        ? Number(values.requester_contact_id)
        : null,
      reason: String(values.reason).trim(),
      version: ticket.data?.version,
    });
  }
  function submitNewCaller(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ticket.data) return;
    const values = Object.fromEntries(new FormData(event.currentTarget));
    createCaller.mutate({
      client_id: ticket.data.client_id,
      full_name: String(values.full_name).trim(),
      email: values.email || null,
      phone_number: values.phone_number || null,
      job_title: values.job_title || null,
      is_active: true,
    });
  }
  function submitRelation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    createRelation.mutate(
      relationTicketIds.map((relatedTicketId) => ({
        related_ticket_id: relatedTicketId,
        relation_type: String(values.relation_type),
        reason: String(values.reason).trim() || null,
      })),
    );
  }
  function submitKnowledgeLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    linkArticle.mutate({
      article_id: Number(values.article_id),
      reason: String(values.reason).trim() || null,
    });
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = String(new FormData(form).get("body") ?? "");
    addComment.mutate(body, {
      onSuccess: () => {
        commentOperationKey.current = null;
        form.reset();
        setCommentBody("");
      },
    });
  }
  async function downloadAttachment(item: Attachment) {
    setAttachmentError("");
    try {
      const response = await api.get(
        `/tickets/${id}/attachments/${item.id}/download`,
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.original_filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setAttachmentError("The attachment could not be downloaded.");
    }
  }
  function startProgress() {
    if (!ticket.data) return;
    if (
      isSharedSupportAssignment &&
      ticket.data.assigned_user_id !== user?.id &&
      !window.confirm(
        "This ticket is currently assigned to the Support team. Starting progress will assign it to you. Do you want to continue?",
      )
    )
      return;
    changeStatus.mutate({
      to_status_code: "IN_PROGRESS",
      reason: "Work started from ticket action",
      version: ticket.data.version,
    });
  }
  useEffect(() => {
    const action = actionParams.get("action");
    if (!ticket.data || !action) return;
    if (action === "start" && hasPermission("ticket.start.progress")) {
      setTargetStatus("IN_PROGRESS");
      setStatusDialog(true);
    } else if (action === "status" && hasPermission("ticket.change.status"))
      setStatusDialog(true);
    else if (action === "resolve" && hasPermission("ticket.change.status")) {
      setTargetStatus("RESOLVED");
      setKnowledgeSearch(ticket.data.subject);
      setStatusDialog(true);
    } else if (action === "close" && hasPermission("ticket.change.status")) {
      setTargetStatus("CLOSED");
      setKnowledgeSearch(ticket.data.subject);
      setStatusDialog(true);
    } else if (action === "pending" && hasPermission("ticket.change.status")) {
      setTargetStatus("PENDING_INTERNAL");
      setStatusDialog(true);
    } else if (
      action === "comment-public" &&
      hasPermission("ticket.comment.public")
    ) {
      setInternal(false);
      requestAnimationFrame(() =>
        document
          .getElementById("ticket-comment-form")
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      );
    } else if (
      action === "comment-internal" &&
      hasPermission("ticket.comment.internal")
    ) {
      setInternal(true);
      requestAnimationFrame(() =>
        document
          .getElementById("ticket-comment-form")
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      );
    } else if (action === "handover" && hasPermission("ticket.assign.team"))
      setHandoverDialog(true);
    else if (action === "link" && hasPermission("ticket.relate"))
      setRelationDialog(true);
    else if (action === "task" && hasPermission("ticket.change.status"))
      setTaskDialog(true);
    else if (action === "checklist" && hasPermission("ticket.change.status"))
      setChecklistDialog(true);
    else if (action === "worklog" && user?.user_type === "EMPLOYEE")
      setWorklogDialog(true);
    else if (action === "knowledge" && hasPermission("knowledge.view"))
      setKnowledgeDialog(true);
    else if (action === "template" && hasPermission("ticket.template.create"))
      setTemplateDialog(true);
    else if (action === "mention" && hasPermission("ticket.mention")) {
      setMentionInternal(false);
      setMentionDialog(true);
    } else if (action === "contact")
      requestAnimationFrame(() =>
        document
          .getElementById("ticket-contact")
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      );
    else if (action === "assign" && hasPermission("ticket.assign.team")) {
      setAssignmentSearch("");
      setAssignmentDialog(true);
    } else if (
      action === "escalate" &&
      (hasPermission("ticket.escalate") || hasPermission("ticket.help.request"))
    )
      setEscalationChoiceDialog(true);
    else if (action === "history") {
      setStatusHistoryOnly(true);
      requestAnimationFrame(() =>
        document
          .getElementById("ticket-activity-history")
          ?.scrollIntoView({ behavior: "smooth", block: "start" }),
      );
    }
    setActionParams({}, { replace: true });
  }, [
    actionParams,
    hasPermission,
    setActionParams,
    ticket.data,
    user?.user_type,
  ]);
  if (ticket.isLoading) return <CircularProgress />;
  if (ticket.isError || !ticket.data)
    return <Alert severity="error">{t("ticketDetail.loadFailed")}</Alert>;
  const currentStatus = statuses.data?.find(
    (s) => s.id === ticket.data.status_id,
  );
  const isIncident =
    ticketTypes.data?.find((type) => type.id === ticket.data.ticket_type_id)
      ?.code === "INCIDENT";
  const isChangeRequest =
    ticketTypes.data?.find((type) => type.id === ticket.data.ticket_type_id)
      ?.code === "CHANGE_REQUEST";
  const approvalPending =
    (ticket.data as Ticket & { entitlement_status?: string })
      .entitlement_status === "PENDING_APPROVAL";
  const canPerformOwnedActions =
    ticket.data.assigned_user_id === user?.id && !approvalPending;
  const allowedStatuses = allowedTransitions.data ?? [];
  const assignedEngineer = assignees.data?.find(
    (item) => item.id === ticket.data.assigned_user_id,
  );
  const isSharedSupportAssignment =
    !ticket.data.assigned_user_id ||
    assignedEngineer?.username.toLowerCase() === "support";
  const canTakeTicket =
    ticket.data.assigned_user_id === user?.id || isSharedSupportAssignment;
  const escalationEngineer = assignees.data?.find(
    (item) => item.id === ticket.data.escalation_assignee_user_id,
  );
  const caller = callerContacts.data?.find(
    (item) => item.id === ticket.data.requester_contact_id,
  );
  const callerWhatsappUrl = whatsappUrl(caller?.phone_number);
  const selectedService = services.data?.find(
    (item) => item.id === ticket.data.service_id,
  );
  const serviceName = ticket.data.service_id
    ? selectedService
      ? localized(selectedService)
      : t("portalTicketDetail.serviceNumber", { id: ticket.data.service_id })
    : t("portalTicketDetail.noService");
  const serviceHasContractSla =
    (ticket.data as Ticket & { entitlement_status?: string })
      .entitlement_status === "COVERED" &&
    (ticket.data.sla_first_response_target_minutes != null ||
      ticket.data.sla_resolution_target_minutes != null);
  return (
    <>
      <Stack direction={{ xs: "column", lg: "row" }} spacing={3}>
        <Paper
          sx={{
            p: 3,
            flex: 2,
            borderLeft: 4,
            borderLeftColor: "primary.main",
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <Button
              startIcon={<ArrowBack />}
              onClick={() => (returnTo ? navigate(returnTo) : navigate(-1))}
            >
              {t("common.back")}
            </Button>
            <Typography variant="h4">
              <TechnicalText>{ticket.data.ticket_number}</TechnicalText>
            </Typography>
            <Chip
              label={t(`priority.${ticket.data.priority}`, {
                defaultValue: ticket.data.priority,
              })}
              color={ticket.data.priority === "P1" ? "error" : "default"}
            />
            <Chip
              label={
                currentStatus ? localized(currentStatus) : t("common.loading")
              }
            />
            {[
              "ticket.edit.own",
              "ticket.edit.assigned",
              "ticket.edit.team",
              "ticket.edit.all",
            ].some(hasPermission) && (
              <Button
                sx={{ marginInlineStart: "auto" }}
                onClick={() => {
                  setEditError("");
                  setEditCategoryId(
                    ticket.data.category_id
                      ? String(ticket.data.category_id)
                      : "",
                  );
                  setEditClientId(String(ticket.data.client_id));
                  setEditProductId(
                    ticket.data.product_id
                      ? String(ticket.data.product_id)
                      : "",
                  );
                  setEditDialog(true);
                }}
              >
                {t("ticketDetail.editTicket")}
              </Button>
            )}
          </Stack>
          <TicketFlagsPanel ticketId={ticket.data.id} />
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={0.5}
            alignItems={{ sm: "center" }}
            sx={{ mt: 1 }}
          >
            <Typography color="text.secondary">
              {t("tickets.client")}:
            </Typography>
            {hasPermission("client.view") ? (
              <Button
                size="small"
                onClick={() =>
                  navigate(`/clients/${ticket.data.client_id}/edit`)
                }
                sx={{ justifyContent: "flex-start", fontWeight: 700, px: 0.5 }}
              >
                {ticket.data.client_name ?? t("liveTicket.clientUnavailable")}
              </Button>
            ) : (
              <Typography fontWeight={700}>
                {ticket.data.client_name ?? t("liveTicket.clientUnavailable")}
              </Typography>
            )}
          </Stack>
          <Typography variant="h5" sx={{ mt: 2 }}>
            {ticket.data.subject}
          </Typography>
          <Typography sx={{ whiteSpace: "pre-wrap", my: 3 }}>
            {ticket.data.description}
          </Typography>
          {isChangeRequest && hasPermission("change_request.view") && (
            <ChangeRequestPanel ticketId={ticket.data.id} />
          )}
          {hasPermission("problem.view") && (
            <ProblemPanel ticketId={ticket.data.id} />
          )}
          {isIncident && hasPermission("major_incident.view") && (
            <MajorIncidentPanel ticketId={ticket.data.id} />
          )}
          <Divider />
          <Stack direction="row" alignItems="center" sx={{ mt: 2 }}>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("ticketDetail.tasks")}
            </Typography>
            {hasPermission("ticket.change.status") && (
              <Button onClick={() => setTaskDialog(true)}>
                {t("ticketDetail.addTask")}
              </Button>
            )}
          </Stack>
          {tasks.data?.length === 0 && (
            <Typography color="text.secondary">
              {t("ticketDetail.noTasks")}
            </Typography>
          )}
          {tasks.data?.map((task) => (
            <Paper variant="outlined" key={task.id} sx={{ p: 1.5, my: 1 }}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                alignItems={{ sm: "center" }}
                spacing={1}
              >
                <Box sx={{ flexGrow: 1 }}>
                  <Typography fontWeight={600}>{task.title}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {task.description || t("ticketDetail.noDescription")}
                    {task.due_at
                      ? ` · ${t("ticketDetail.dueAt", { date: new Date(task.due_at).toLocaleString(i18n.language) })}`
                      : ""}
                  </Typography>
                </Box>
                <Chip
                  size="small"
                  label={t(`ticketDetail.workStates.${task.status}`, {
                    defaultValue: task.status.replace("_", " "),
                  })}
                />
                {hasPermission("ticket.change.status") &&
                  task.status !== "COMPLETED" && (
                    <Button
                      size="small"
                      onClick={() =>
                        updateTask.mutate({
                          taskId: task.id,
                          status: "COMPLETED",
                        })
                      }
                    >
                      {t("ticketDetail.complete")}
                    </Button>
                  )}
              </Stack>
            </Paper>
          ))}
          <Stack direction="row" alignItems="center" sx={{ mt: 2 }}>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("ticketDetail.checklist")}
            </Typography>
            {hasPermission("ticket.change.status") && (
              <Button onClick={() => setChecklistDialog(true)}>
                {t("ticketDetail.addItem")}
              </Button>
            )}
          </Stack>
          {checklist.data?.length === 0 && (
            <Typography color="text.secondary">
              {t("ticketDetail.noChecklist")}
            </Typography>
          )}
          {checklist.data?.map((item) => (
            <FormControlLabel
              key={item.id}
              control={
                <Checkbox
                  checked={item.is_completed}
                  disabled={
                    !hasPermission("ticket.change.status") ||
                    toggleChecklistItem.isPending
                  }
                  onChange={() => toggleChecklistItem.mutate(item)}
                />
              }
              label={item.label}
              sx={{ display: "flex" }}
            />
          ))}
          <Stack direction="row" alignItems="center" sx={{ mt: 2 }}>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("ticketDetail.worklogs")}
            </Typography>
            {user?.user_type === "EMPLOYEE" && (
              <Button onClick={() => setWorklogDialog(true)}>
                {t("ticketDetail.logWork")}
              </Button>
            )}
          </Stack>
          {worklogs.data?.length === 0 && (
            <Typography color="text.secondary">
              {t("ticketDetail.noWorklogs")}
            </Typography>
          )}
          {worklogs.data?.map((item) => (
            <Paper variant="outlined" key={item.id} sx={{ p: 1.5, my: 1 }}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                gap={1}
                alignItems={{ sm: "center" }}
              >
                <Box flexGrow={1}>
                  <Typography fontWeight={600}>
                    {t("time.minutes", { count: item.duration_minutes })} ·{" "}
                    {new Date(item.started_at).toLocaleString(i18n.language)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {item.notes}
                    {item.task_id
                      ? ` · ${t("ticketDetail.taskNumber", { id: item.task_id })}`
                      : ""}
                  </Typography>
                </Box>
                <Chip
                  size="small"
                  label={t(`ticketDetail.workStates.${item.status}`, {
                    defaultValue: item.status,
                  })}
                />
                {item.user_id === user?.id && item.status === "DRAFT" && (
                  <Button
                    size="small"
                    onClick={() => submitWorklog.mutate(item.id)}
                  >
                    {t("ticketDetail.submit")}
                  </Button>
                )}
                {(hasPermission("ticket.resolve.any") ||
                  hasPermission("configuration.manage")) &&
                  item.status === "SUBMITTED" && (
                    <>
                      <Button
                        size="small"
                        color="success"
                        onClick={() =>
                          decideWorklog.mutate({ item, approved: true })
                        }
                      >
                        {t("ticketDetail.approve")}
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        onClick={() =>
                          decideWorklog.mutate({ item, approved: false })
                        }
                      >
                        {t("ticketDetail.reject")}
                      </Button>
                    </>
                  )}
              </Stack>
            </Paper>
          ))}
          <Divider sx={{ mt: 2 }} />
          {id && <UatTicketEvidencePanel ticketId={Number(id)} />}
          <Typography variant="h6" sx={{ mt: 3 }}>
            {t("portalTicketDetail.attachments")}
          </Typography>
          {attachmentError && (
            <Alert severity="error" sx={{ my: 1 }}>
              {attachmentError}
            </Alert>
          )}
          {attachments.data?.length === 0 && (
            <Typography color="text.secondary">
              {t("ticketDetail.noAttachments")}
            </Typography>
          )}
          <Stack spacing={1} sx={{ my: 1 }}>
            {attachments.data?.map((item) => (
              <Paper variant="outlined" key={item.id} sx={{ p: 1.5 }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1}
                  alignItems={{ sm: "center" }}
                >
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography dir="ltr" sx={{ unicodeBidi: "isolate" }}>
                      {item.original_filename}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {(item.size_bytes / 1024).toFixed(1)} KB ·{" "}
                      {new Date(item.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Button
                    size="small"
                    onClick={() => void downloadAttachment(item)}
                  >
                    {t("portalTicketDetail.download")}
                  </Button>
                </Stack>
              </Paper>
            ))}
          </Stack>
          {hasPermission("ticket.comment.public") && (
            <Button
              component="label"
              variant="outlined"
              disabled={uploadAttachment.isPending}
            >
              {uploadAttachment.isPending
                ? t("ticketDetail.uploading")
                : t("portalTicketDetail.addAttachment")}
              <input
                hidden
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.txt,.log,.csv,.docx,.xlsx"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) uploadAttachment.mutate(file);
                  event.target.value = "";
                }}
              />
            </Button>
          )}
          <Divider />
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ sm: "center" }}
            gap={1}
            sx={{ mt: 3 }}
          >
            <Typography
              id="ticket-activity-history"
              variant="h6"
              sx={{ scrollMarginTop: 80, flex: 1 }}
            >
              {statusHistoryOnly
                ? "Status change history"
                : t("ticketDetail.activity")}
            </Typography>
            {!statusHistoryOnly && hasPermission("ticket.comment.public") && (
              <Button
                variant="outlined"
                onClick={() => {
                  const now = new Date();
                  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
                  setTicketEventTime(now.toISOString().slice(0, 16));
                  setTicketEventDialog(true);
                }}
              >
                Add ticket event
              </Button>
            )}
          </Stack>
          <Stack spacing={1} sx={{ my: 1 }}>
            {statusHistoryOnly &&
              !timeline.isLoading &&
              !timeline.data?.some(
                (event) => event.event_type === "STATUS_CHANGED",
              ) && (
                <Alert severity="info">
                  No status changes have been recorded yet.
                </Alert>
              )}
            {timeline.data
              ?.filter(
                (event) =>
                  !statusHistoryOnly || event.event_type === "STATUS_CHANGED",
              )
              .map((event) => (
                <Box
                  key={event.id}
                  sx={{
                    p: 1.5,
                    bgcolor: event.is_internal
                      ? (theme) =>
                          theme.palette.mode === "dark"
                            ? "rgba(237, 108, 2, 0.14)"
                            : "#fff8e1"
                      : "action.hover",
                    borderInlineStart: 3,
                    borderColor: event.is_internal
                      ? "warning.main"
                      : "primary.main",
                    borderRadius: 1,
                  }}
                >
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    spacing={1}
                  >
                    <Typography fontWeight={600}>{event.title}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(event.created_at).toLocaleString()}
                    </Typography>
                  </Stack>
                  {event.description && (
                    <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                      {event.description}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {event.actor_name ?? "System"}
                    {event.is_internal ? " · Internal" : ""}
                  </Typography>
                </Box>
              ))}
          </Stack>
          <Divider />
          <Typography variant="h6" sx={{ mt: 3 }}>
            {t("ticketDetail.conversation")}
          </Typography>
          {comments.data?.map((comment) => (
            <Box
              key={comment.id}
              sx={{
                p: 2,
                my: 1,
                bgcolor: comment.is_internal
                  ? (theme) =>
                      theme.palette.mode === "dark"
                        ? "rgba(237, 108, 2, 0.14)"
                        : "#fff8e1"
                  : "action.hover",
                borderInlineStart: 4,
                borderColor: comment.is_internal
                  ? "warning.main"
                  : "primary.main",
                borderRadius: 1,
              }}
            >
              <Typography variant="caption">
                {comment.is_internal ? "Internal note" : "Public reply"} ·{" "}
                {new Date(comment.created_at).toLocaleString()}
              </Typography>
              <Typography>{comment.body}</Typography>
            </Box>
          ))}
          <Box
            id="ticket-comment-form"
            component="form"
            onSubmit={submit}
            sx={{ mt: 2, scrollMarginTop: 80 }}
          >
            <TextField
              name="body"
              label={t(
                internal
                  ? "ticketDetail.internalNote"
                  : "ticketDetail.publicReply",
              )}
              required
              fullWidth
              multiline
              rows={3}
              value={commentBody}
              onChange={(event) => {
                const value = event.target.value;
                setCommentBody(value);
                if (value.endsWith("@") && hasPermission("ticket.mention")) {
                  setMentionMessage(value.slice(0, -1).trim());
                  setMentionInternal(internal);
                  setMentionDialog(true);
                }
              }}
            />
            {hasPermission("ticket.comment.internal") && (
              <FormControlLabel
                control={
                  <Switch
                    checked={internal}
                    onChange={(_, checked) => setInternal(checked)}
                  />
                }
                label={t("ticketDetail.internalNote")}
              />
            )}
            <Button
              type="submit"
              variant="contained"
              disabled={addComment.isPending}
            >
              {t("ticketDetail.addComment")}
            </Button>
          </Box>
        </Paper>
        <Paper
          sx={{
            p: 3,
            flex: 1,
            alignSelf: "flex-start",
            borderLeft: 4,
            borderLeftColor: "secondary.main",
          }}
        >
          <Typography variant="h6">{t("ticketDetail.context")}</Typography>
          <Typography color="text.secondary">
            {t("ticketDetail.version", { version: ticket.data.version })}
          </Typography>
          <Typography
            id="ticket-contact"
            variant="subtitle2"
            sx={{ mt: 2, scrollMarginTop: 80 }}
          >
            {t("ticketDetail.caller")}
          </Typography>
          {ticket.data.requester_contact_id ? (
            <Paper variant="outlined" sx={{ p: 1.5, mt: 0.5 }}>
              <Typography fontWeight={600}>
                {caller?.full_name ??
                  t("ticketDetail.contactNumber", {
                    id: ticket.data.requester_contact_id,
                  })}
              </Typography>
              <Typography variant="body2">
                {t("ticketDetail.mobile")}:{" "}
                {caller?.phone_number ?? t("ticketDetail.notRecorded")}
              </Typography>
              <Typography variant="body2">
                {t("ticketDetail.email")}:{" "}
                {caller?.email ?? t("ticketDetail.notRecorded")}
              </Typography>
              <Typography variant="body2">
                {t("ticketDetail.role")}:{" "}
                {caller?.job_title ?? t("ticketDetail.notRecorded")}
              </Typography>
              {callerWhatsappUrl && (
                <Button
                  component="a"
                  href={callerWhatsappUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="small"
                  variant="contained"
                  sx={{
                    display: "flex",
                    width: "fit-content",
                    mt: 1,
                    bgcolor: "#25D366",
                    color: "#fff",
                    "&:hover": { bgcolor: "#1da851" },
                  }}
                >
                  {t("ticketDetail.openWhatsApp")}
                </Button>
              )}
              {caller && !caller.is_active && (
                <Chip
                  size="small"
                  color="warning"
                  label={t("ticketDetail.inactiveContact")}
                  sx={{ mt: 1 }}
                />
              )}
            </Paper>
          ) : (
            <Typography color="text.secondary">
              {t("ticketDetail.noCaller")}
            </Typography>
          )}
          <Stack sx={{ mt: 1 }} alignItems="flex-start">
            <TicketSendActionsButton ticketId={ticket.data.id} />
          </Stack>
          {hasPermission("ticket.change.status") && (
            <Button
              size="small"
              variant="outlined"
              sx={{ mt: 1 }}
              onClick={() => {
                setCallerSelection(
                  ticket.data.requester_contact_id
                    ? String(ticket.data.requester_contact_id)
                    : "",
                );
                setCallerDialog(true);
              }}
            >
              {t(
                ticket.data.requester_contact_id
                  ? "ticketDetail.changeCaller"
                  : "ticketDetail.selectCaller",
              )}
            </Button>
          )}
          <Typography variant="subtitle2" sx={{ mt: 2 }}>
            {t("ticketDetail.assignedEngineer")}
          </Typography>
          <Typography>
            {assignedEngineer?.full_name ??
              (ticket.data.assigned_user_id
                ? t("ticketDetail.userNumber", {
                    id: ticket.data.assigned_user_id,
                  })
                : t("ticketDetail.unassigned"))}
          </Typography>
          {ticket.data.assigned_team && (
            <Typography color="text.secondary">
              {t("ticketDetail.team")}: {ticket.data.assigned_team}
            </Typography>
          )}
          {assignmentError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {assignmentError}
            </Alert>
          )}
          <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1 }}>
            {hasPermission("ticket.assign.self") && (
              <Button
                variant="contained"
                disabled={
                  approvalPending ||
                  claim.isPending ||
                  ticket.data.assigned_user_id === user?.id ||
                  !canTakeTicket
                }
                onClick={() => claim.mutate()}
                title={
                  !canTakeTicket ? t("ticketDetail.assignedAnother") : undefined
                }
              >
                {ticket.data.assigned_user_id === user?.id
                  ? t("ticketDetail.assignedToMe")
                  : claim.isPending
                    ? t("ticketDetail.assigning")
                    : t("ticketDetail.assignToMe")}
              </Button>
            )}
            {hasPermission("ticket.assign.team") && (
              <Button
                variant="outlined"
                disabled={approvalPending}
                title={
                  approvalPending
                    ? t("ticketDetail.approvalBeforeAssignment")
                    : undefined
                }
                onClick={() => {
                  setAssignmentSearch("");
                  setAssignmentDialog(true);
                }}
              >
                {t(
                  ticket.data.assigned_user_id
                    ? "ticketDetail.reassignEngineer"
                    : "ticketDetail.assignEngineer",
                )}
              </Button>
            )}
            {(ticket.data.assigned_user_id === user?.id ||
              hasPermission("ticket.assign.team")) && (
              <Button
                color="warning"
                variant="contained"
                disabled={approvalPending}
                onClick={() => setHandoverDialog(true)}
              >
                {t("ticketDetail.handOver")}
              </Button>
            )}
          </Stack>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2">
            {t("ticketDetail.internalEscalation")}
          </Typography>
          {ticket.data.escalation_assignee_user_id ? (
            <Paper
              variant="outlined"
              sx={{
                p: 1.5,
                mt: 0.5,
                borderColor: "warning.main",
                bgcolor: (theme) =>
                  theme.palette.mode === "dark"
                    ? "rgba(237, 108, 2, 0.14)"
                    : "#fff8e1",
              }}
            >
              <Stack direction="row" alignItems="center" gap={1}>
                <Typography fontWeight={700}>
                  {escalationEngineer?.full_name ??
                    t("ticketDetail.userNumber", {
                      id: ticket.data.escalation_assignee_user_id,
                    })}
                </Typography>
                <Chip
                  size="small"
                  color="warning"
                  label={t(
                    `ticketDetail.states.${ticket.data.escalation_level ?? "ESCALATED"}`,
                    {
                      defaultValue: (
                        ticket.data.escalation_level ?? "ESCALATED"
                      ).replaceAll("_", " "),
                    },
                  )}
                />
              </Stack>
              {escalationEngineer?.department && (
                <Typography variant="body2">
                  {escalationEngineer.department}
                  {escalationEngineer.job_title
                    ? ` · ${escalationEngineer.job_title}`
                    : ""}
                </Typography>
              )}
              <Typography variant="body2" sx={{ mt: 1 }}>
                {ticket.data.escalation_reason}
              </Typography>
              {ticket.data.escalated_at && (
                <Typography variant="caption" color="text.secondary">
                  {t("ticketDetail.escalatedAt", {
                    date: new Date(ticket.data.escalated_at).toLocaleString(
                      i18n.language,
                    ),
                  })}
                </Typography>
              )}
            </Paper>
          ) : (
            <Typography color="text.secondary">
              {t("ticketDetail.notEscalated")}
            </Typography>
          )}
          {(hasPermission("ticket.escalate") ||
            hasPermission("ticket.help.request")) &&
            !ticket.data.escalation_parent_ticket_id && (
              <Button
                color="warning"
                variant="outlined"
                sx={{ mt: 1 }}
                disabled={!canPerformOwnedActions}
                title={
                  !canPerformOwnedActions
                    ? approvalPending
                      ? "Approval is required before escalation"
                      : "Assign the ticket to yourself before escalation"
                    : undefined
                }
                onClick={() => setEscalationChoiceDialog(true)}
              >
                {ticket.data.escalation_assignee_user_id
                  ? "Update escalation"
                  : "Escalate / Request Help"}
              </Button>
            )}
          {ticket.data.routed_department_id && (
            <Paper
              variant="outlined"
              sx={{ p: 1.5, mt: 1, borderColor: "info.main" }}
            >
              <Stack
                direction="row"
                gap={1}
                alignItems="center"
                flexWrap="wrap"
              >
                <Typography fontWeight={800}>
                  {t("ticketDetail.departmentHelpRequest")}
                </Typography>
                <Chip
                  size="small"
                  color={
                    ticket.data.routing_status === "RETURNED"
                      ? "success"
                      : "info"
                  }
                  label={t(
                    `ticketDetail.workStates.${ticket.data.routing_status ?? "NEW"}`,
                    {
                      defaultValue: (
                        ticket.data.routing_status ?? "NEW"
                      ).replaceAll("_", " "),
                    },
                  )}
                />
              </Stack>
              <Typography variant="body2">
                {t("ticketDetail.routedTo", {
                  department:
                    localized(
                      departments.data?.find(
                        (row) => row.id === ticket.data.routed_department_id,
                      ),
                    ) || `#${ticket.data.routed_department_id}`,
                })}
              </Typography>
              {ticket.data.help_request_result && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  {ticket.data.help_request_result}
                </Alert>
              )}
              {hasPermission("ticket.help.return") &&
                ticket.data.routing_status !== "RETURNED" && (
                  <Button
                    size="small"
                    variant="contained"
                    sx={{ mt: 1 }}
                    onClick={() => setReturnDialog(true)}
                  >
                    {t("ticketDetail.returnToSupport")}
                  </Button>
                )}
            </Paper>
          )}
          {!ticket.data.escalation_parent_ticket_id &&
            Boolean(departmentRequests.data?.length) && (
              <Stack spacing={1} mt={2}>
                <Typography variant="subtitle2">
                  {t("ticketDetail.departmentResponses")}
                </Typography>
                {departmentRequests.data?.map((request) => (
                  <Paper key={request.id} variant="outlined" sx={{ p: 1.5 }}>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      gap={1}
                      alignItems={{ sm: "center" }}
                    >
                      <Button
                        onClick={() => navigate(`/tickets/${request.id}`)}
                      >
                        {request.ticket_number}
                      </Button>
                      <Typography flexGrow={1}>
                        {localized(
                          departments.data?.find(
                            (row) => row.id === request.routed_department_id,
                          ),
                        ) || `#${request.routed_department_id}`}
                      </Typography>
                      <Chip
                        size="small"
                        color={
                          request.routing_status === "RETURNED"
                            ? "success"
                            : "info"
                        }
                        label={t(
                          `ticketDetail.workStates.${request.routing_status ?? "NEW"}`,
                          {
                            defaultValue: (
                              request.routing_status ?? "NEW"
                            ).replaceAll("_", " "),
                          },
                        )}
                      />
                    </Stack>
                    {request.help_request_result && (
                      <Alert severity="success" sx={{ mt: 1 }}>
                        {request.help_request_result}
                      </Alert>
                    )}
                  </Paper>
                ))}
              </Stack>
            )}
          <Typography variant="subtitle2" sx={{ mt: 2 }}>
            {t("ticketDetail.followers")}
          </Typography>
          <Typography variant="body2">
            {followers.data?.map((item) => item.full_name).join(", ") ||
              t("ticketDetail.noFollowers")}
          </Typography>
          {hasPermission("ticket.assign.team") && (
            <Button
              size="small"
              variant="outlined"
              sx={{ mt: 1 }}
              onClick={() => {
                setFollowerIds(
                  followers.data?.map((item) => item.user_id) ?? [],
                );
                setFollowersDialog(true);
              }}
            >
              {t("ticketDetail.manageFollowers")}
            </Button>
          )}
          {allowedStatuses.length > 0 && (
            <Button
              variant="outlined"
              disabled={approvalPending}
              title={
                approvalPending
                  ? t("ticketDetail.approvalBeforeStatus")
                  : undefined
              }
              sx={{ mt: 2 }}
              onClick={() => {
                setCloseAfterResolve(Boolean(user?.auto_close_on_resolve));
                setSaveCloseDefault(false);
                setStatusDialog(true);
              }}
            >
              {t("ticketDetail.changeStatus")}
            </Button>
          )}
          <Stack direction="row" spacing={1} mt={1} flexWrap="wrap">
            {allowedStatuses.some(
              (status) => status.code === "IN_PROGRESS",
            ) && (
              <Button
                variant="contained"
                disabled={
                  approvalPending ||
                  changeStatus.isPending ||
                  (!canTakeTicket &&
                    !hasPermission("ticket.start_progress_any"))
                }
                title={
                  !canTakeTicket
                    ? "Only the assigned engineer can start progress"
                    : undefined
                }
                onClick={startProgress}
              >
                {changeStatus.isPending
                  ? "Starting…"
                  : isSharedSupportAssignment &&
                      ticket.data.assigned_user_id !== user?.id
                    ? "Assign to me & start progress"
                    : "Start progress"}
              </Button>
            )}
            {allowedStatuses.some((status) => status.code === "RESOLVED") && (
              <Button
                color="success"
                variant="contained"
                disabled={!canPerformOwnedActions}
                title={
                  !canPerformOwnedActions
                    ? t("ticketDetail.onlyAssignedResolve")
                    : undefined
                }
                onClick={() => {
                  setTargetStatus("RESOLVED");
                  setStatusDialog(true);
                }}
              >
                {t("ticketDetail.resolve")}
              </Button>
            )}
            {allowedStatuses.some(
              (status) => status.code === "PENDING_INTERNAL",
            ) && (
              <Button
                color="warning"
                variant="outlined"
                disabled={approvalPending}
                onClick={() => {
                  setTargetStatus("PENDING_INTERNAL");
                  setStatusDialog(true);
                }}
              >
                {t("ticketDetail.pending")}
              </Button>
            )}
          </Stack>
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              mt: 2,
              borderColor: serviceHasContractSla ? "success.main" : "divider",
            }}
          >
            <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
              <Typography variant="subtitle2">
                {t("portalTicketDetail.contractSla")}
              </Typography>
              <Chip
                size="small"
                color={serviceHasContractSla ? "success" : "default"}
                label={t(
                  serviceHasContractSla
                    ? "portalTicketDetail.covered"
                    : "portalTicketDetail.notCovered",
                )}
              />
            </Stack>
            <Typography sx={{ mt: 1 }}>
              {t("portalTicketDetail.service")}: <b>{serviceName}</b>
            </Typography>
            <Typography>
              {t("portalTicketDetail.product")}:{" "}
              <b>
                {ticket.data.product_id
                  ? localized(
                      products.data?.find(
                        (item) => item.id === ticket.data?.product_id,
                      ),
                    ) || `#${ticket.data.product_id}`
                  : t("portalTicketDetail.noProduct")}
              </b>
            </Typography>
            <Typography>
              {t("portalTicketDetail.governingContract")}:{" "}
              <b>
                {selectedContract.data
                  ? `${selectedContract.data.contract_number} — ${selectedContract.data.name}`
                  : ticket.data.contract_id
                    ? `#${ticket.data.contract_id}`
                    : t("portalTicketDetail.noContract")}
              </b>
            </Typography>
            <Typography>
              {t("tickets.priority")}:{" "}
              <b>
                {t(`priority.${ticket.data.priority}`, {
                  defaultValue: ticket.data.priority,
                })}
              </b>
            </Typography>
            {serviceHasContractSla ? (
              <>
                <Typography>
                  {t("portalTicketDetail.firstResponse")}:{" "}
                  <b>
                    {slaDuration(ticket.data.sla_first_response_target_minutes)}
                  </b>
                </Typography>
                <Typography>
                  {t("portalTicketDetail.resolutionTarget")}:{" "}
                  <b>
                    {slaDuration(ticket.data.sla_resolution_target_minutes)}
                  </b>
                </Typography>
                <Typography>
                  {t("portalTicketDetail.accountableTime")}:{" "}
                  <b>{slaDuration(ticket.data.sla_actual_business_minutes)}</b>
                </Typography>
                {ticket.data.sla_saved_minutes != null && (
                  <Typography
                    color={
                      ticket.data.sla_saved_minutes >= 0
                        ? "success.main"
                        : "error.main"
                    }
                  >
                    {t("ticketDetail.result")}:{" "}
                    <b>
                      {ticket.data.sla_saved_minutes >= 0
                        ? t("portalTickets.saved", {
                            value: slaDuration(ticket.data.sla_saved_minutes),
                          })
                        : t("portalTickets.overrun", {
                            value: slaDuration(
                              Math.abs(ticket.data.sla_saved_minutes),
                            ),
                          })}
                    </b>
                  </Typography>
                )}
                <Typography variant="caption" color="text.secondary">
                  {t("ticketDetail.slaNotice")}
                </Typography>
              </>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {t(
                  ticket.data.service_id
                    ? "ticketDetail.noMatchingSla"
                    : "ticketDetail.selectContractedService",
                )}
              </Typography>
            )}
          </Paper>
          {serviceHasContractSla && sla.data?.[0] && (
            <Alert severity="info" sx={{ mt: 1 }}>
              SLA match:{" "}
              {(sla.data[0].match_reason ?? "NO_MATCH_EVIDENCE").replaceAll(
                "_",
                " ",
              )}{" "}
              · target #{sla.data[0].target_id ?? "legacy"} · policy v
              {sla.data[0].policy_version} · calendar #
              {sla.data[0].calendar_id ?? "legacy"}
            </Alert>
          )}
          {serviceHasContractSla &&
            sla.data?.map((clock) => {
              const effectiveState =
                clock.state === "RUNNING" &&
                new Date(clock.due_at).getTime() <= Date.now()
                  ? "OVERDUE"
                  : clock.state;
              const color =
                effectiveState === "COMPLETED"
                  ? "success"
                  : effectiveState === "BREACHED" ||
                      effectiveState === "OVERDUE"
                    ? "error"
                    : "info";
              return (
                <Box
                  key={clock.id}
                  sx={{
                    mt: 2,
                    p: 1.5,
                    bgcolor: "action.hover",
                    borderRadius: 1,
                    borderInlineStart: 4,
                    borderColor: `${color}.main`,
                  }}
                >
                  <Stack direction="row" alignItems="center" gap={1}>
                    <Typography variant="subtitle2" flex={1}>
                      {t(`ticketDetail.slaClock.${clock.clock_type}`, {
                        defaultValue: clock.clock_type.replace("_", " "),
                      })}
                    </Typography>
                    <Chip
                      size="small"
                      color={color}
                      label={t(`ticketDetail.workStates.${effectiveState}`, {
                        defaultValue: effectiveState,
                      })}
                    />
                  </Stack>
                  <Typography color="text.secondary">
                    {t("ticketDetail.slaTargetWarning", {
                      target: clock.target_minutes,
                      percent: clock.warning_percent,
                    })}
                  </Typography>
                  <Typography color="text.secondary">
                    {t("ticketDetail.slaDeadline", {
                      date: new Date(clock.due_at).toLocaleString(
                        i18n.language,
                      ),
                    })}
                  </Typography>
                  {clock.completed_at && (
                    <Typography variant="caption" display="block">
                      {t("ticketDetail.actualCompletion", {
                        date: new Date(clock.completed_at).toLocaleString(
                          i18n.language,
                        ),
                      })}
                    </Typography>
                  )}
                </Box>
              );
            })}
          {ticket.data.resolution_summary && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2">
                {t("ticketDetail.resolution")}
              </Typography>
              <Typography>{ticket.data.resolution_summary}</Typography>
              {ticket.data.resolution_service_ids.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ mt: 2 }}>
                    {t("ticketDetail.serviceProvided")}
                  </Typography>
                  <Stack direction="row" gap={1} flexWrap="wrap">
                    {ticket.data.resolution_service_ids.map((serviceId) => (
                      <Chip
                        key={serviceId}
                        label={
                          localized(
                            services.data?.find(
                              (item) => item.id === serviceId,
                            ),
                          ) || `#${serviceId}`
                        }
                      />
                    ))}
                  </Stack>
                </>
              )}
            </>
          )}
          {(ticket.data.root_causes.length > 0 ||
            ticket.data.root_cause_summary) && (
            <>
              <Typography variant="subtitle2" sx={{ mt: 2 }}>
                {t("ticketDetail.rootCauses")}
              </Typography>
              <Stack direction="row" gap={1} flexWrap="wrap">
                {ticket.data.root_causes.map((cause) => (
                  <Chip key={cause} label={cause} />
                ))}
                {ticket.data.root_causes.length === 0 && (
                  <Typography>{ticket.data.root_cause_summary}</Typography>
                )}
              </Stack>
            </>
          )}
          {ticket.data.pending_follow_up_at && (
            <Paper
              variant="outlined"
              sx={{ p: 1.5, mt: 2, borderColor: "warning.main" }}
            >
              <Typography variant="subtitle2">
                {t("ticketDetail.pendingFollowUp")}
              </Typography>
              <Typography>{ticket.data.pending_reason}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("ticketDetail.followUpOwnerDue", {
                  owner:
                    assignees.data?.find(
                      (item) => item.id === ticket.data.pending_owner_user_id,
                    )?.full_name ??
                    t("ticketDetail.userNumber", {
                      id: ticket.data.pending_owner_user_id,
                    }),
                  date: new Date(
                    ticket.data.pending_follow_up_at,
                  ).toLocaleString(i18n.language),
                })}
              </Typography>
            </Paper>
          )}
          {ticket.data.shift_handover_status && (
            <Paper
              variant="outlined"
              sx={{
                p: 1.5,
                mt: 2,
                borderColor:
                  ticket.data.shift_handover_status === "PENDING"
                    ? "warning.main"
                    : "success.main",
              }}
            >
              <Stack direction="row" alignItems="center">
                <Typography variant="subtitle2">
                  {t("ticketDetail.shiftHandover")}
                </Typography>
                <Chip
                  size="small"
                  sx={{ marginInlineStart: "auto" }}
                  color={
                    ticket.data.shift_handover_status === "PENDING"
                      ? "warning"
                      : "success"
                  }
                  label={t(
                    `ticketDetail.workStates.${ticket.data.shift_handover_status}`,
                    {
                      defaultValue:
                        ticket.data.shift_handover_status.replaceAll("_", " "),
                    },
                  )}
                />
              </Stack>
              <Typography>{ticket.data.shift_handover_reason}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("ticketDetail.handoverFromTo", {
                  from:
                    assignees.data?.find(
                      (item) =>
                        item.id === ticket.data.shift_handover_by_user_id,
                    )?.full_name ??
                    t("ticketDetail.userNumber", {
                      id: ticket.data.shift_handover_by_user_id,
                    }),
                  to:
                    assignees.data?.find(
                      (item) =>
                        item.id === ticket.data.shift_handover_to_user_id,
                    )?.full_name ?? t("ticketDetail.nextSupportShift"),
                })}
              </Typography>
              {ticket.data.shift_handover_status === "PENDING" &&
                (ticket.data.shift_handover_to_user_id === user?.id ||
                  ticket.data.assigned_user_id === user?.id ||
                  hasPermission("ticket.assign.team")) && (
                  <Button
                    size="small"
                    variant="contained"
                    color="success"
                    sx={{ mt: 1 }}
                    disabled={completeHandover.isPending}
                    onClick={() => completeHandover.mutate()}
                  >
                    {t("ticketDetail.markHandedOver")}
                  </Button>
                )}
            </Paper>
          )}
          <Divider sx={{ my: 2 }} />
          <Typography variant="h6">
            {t("ticketDetail.relatedTickets")}
          </Typography>
          {relations.data?.length === 0 && (
            <Typography color="text.secondary">
              {t("ticketDetail.noRelated")}
            </Typography>
          )}
          <Stack spacing={1} sx={{ mt: 1 }}>
            {relations.data?.map((relation) => (
              <Paper variant="outlined" key={relation.id} sx={{ p: 1 }}>
                <Chip
                  size="small"
                  label={relation.relation_type.replace("_", " ")}
                  sx={{ marginInlineEnd: 1 }}
                />
                <Button
                  size="small"
                  onClick={() =>
                    navigate(`/tickets/${relation.related_ticket_id}`)
                  }
                >
                  {relation.related_ticket_number}
                </Button>
                <Typography variant="body2">
                  {relation.related_subject}
                </Typography>
                {hasPermission("ticket.relate") && (
                  <Button
                    color="error"
                    size="small"
                    onClick={() => removeRelation.mutate(relation.id)}
                  >
                    {t("common.actions.delete")}
                  </Button>
                )}
              </Paper>
            ))}
          </Stack>
          {hasPermission("ticket.relate") && (
            <Button
              variant="outlined"
              sx={{ mt: 1 }}
              onClick={() => setRelationDialog(true)}
            >
              {t(
                isIncident
                  ? "ticketDetail.addIncidentIssues"
                  : "ticketDetail.linkTickets",
              )}
            </Button>
          )}
          {hasPermission("knowledge.view") && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6">
                {t("ticketDetail.knowledgeArticles")}
              </Typography>
              {knowledgeLinks.data?.length === 0 && (
                <Typography color="text.secondary">
                  {t("ticketDetail.noKnowledge")}
                </Typography>
              )}
              <Stack spacing={1} sx={{ mt: 1 }}>
                {knowledgeLinks.data?.map((link) => (
                  <Paper variant="outlined" key={link.id} sx={{ p: 1 }}>
                    <Typography fontWeight={600}>{link.title}</Typography>
                    <Typography variant="body2">{link.summary}</Typography>
                    <Chip
                      size="small"
                      label={link.category ?? t("ticketDetail.uncategorized")}
                      sx={{ mt: 1, mr: 1 }}
                    />
                    <Button
                      size="small"
                      onClick={() => setViewArticleId(link.article_id)}
                    >
                      {t("ticketDetail.viewArticle")}
                    </Button>
                    <Button
                      color="error"
                      size="small"
                      onClick={() => unlinkArticle.mutate(link.id)}
                    >
                      {t("ticketDetail.unlink")}
                    </Button>
                  </Paper>
                ))}
              </Stack>
              <Button
                variant="outlined"
                sx={{ mt: 1 }}
                onClick={() => setKnowledgeDialog(true)}
              >
                {t("ticketDetail.linkKnowledge")}
              </Button>
            </>
          )}
        </Paper>
      </Stack>
      <Box sx={{ mt: 3 }}>
        <TicketClientAccessDialog clientId={ticket.data.client_id} />
      </Box>
      <Dialog
        open={ticketEventDialog}
        onClose={() => setTicketEventDialog(false)}
        fullWidth
        maxWidth="sm"
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle>
          <Typography variant="h6" fontWeight={900}>
            Add ticket event
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This permanent event becomes part of the ticket history and can be
            included in future incident reports.
          </Typography>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} mt={1}>
            {ticketEventError && (
              <Alert severity="error">{ticketEventError}</Alert>
            )}
            <TextField
              required
              type="datetime-local"
              label="Date and time"
              value={ticketEventTime}
              onChange={(event) => setTicketEventTime(event.target.value)}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              required
              multiline
              minRows={4}
              label="Event description"
              value={ticketEventText}
              onChange={(event) => setTicketEventText(event.target.value)}
              helperText="Write a factual, client-safe operational event. Do not include credentials or private notes."
            />
            <TextField
              label="Owner or source"
              value={ticketEventOwner}
              onChange={(event) => setTicketEventOwner(event.target.value)}
              helperText="Leave empty to use your name."
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTicketEventDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={
              !ticketEventTime ||
              ticketEventText.trim().length < 3 ||
              addTicketEvent.isPending
            }
            onClick={() => addTicketEvent.mutate()}
          >
            Save ticket event
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={statusDialog}
        onClose={() => setStatusDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitTransition}>
          <DialogTitle>{t("ticketDetail.changeStatus")}</DialogTitle>
          <DialogContent>
            {transitionError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {transitionError}
              </Alert>
            )}
            <TextField
              select
              required
              label={t("ticketDetail.newStatus")}
              fullWidth
              margin="normal"
              value={targetStatus}
              onChange={(event) => {
                setTargetStatus(event.target.value);
                setCreateKnowledgeArticle(false);
                if (event.target.value === "RESOLVED")
                  setCloseAfterResolve(Boolean(user?.auto_close_on_resolve));
              }}
            >
              {allowedStatuses.map((status) => (
                <MenuItem key={status.code} value={status.code}>
                  {localized(status)}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              name="reason"
              label={t("ticketDetail.statusReason")}
              required={
                targetStatus.startsWith("PENDING_") ||
                targetStatus === "CANCELLED" ||
                targetStatus === "REOPENED"
              }
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            {targetStatus.startsWith("PENDING_") && (
              <>
                <TextField
                  select
                  required
                  name="pending_responsible_party"
                  label={t("ticketDetail.waitingResponsibility")}
                  defaultValue="CUSTOMER"
                  fullWidth
                  margin="normal"
                  helperText={t("ticketDetail.waitingSlaHelp")}
                >
                  <MenuItem value="CUSTOMER">
                    {t("ticketDetail.customerClient")}
                  </MenuItem>
                  <MenuItem value="MILLENSYS">Millensys</MenuItem>
                </TextField>
                {hasPermission("ticket.assign.team") ? (
                  <TextField
                    select
                    name="pending_owner_user_id"
                    label={t("ticketDetail.followUpOwner")}
                    defaultValue={
                      ticket.data.pending_owner_user_id ?? user?.id ?? ""
                    }
                    required
                    fullWidth
                    margin="normal"
                  >
                    {assignees.data?.map((employee) => (
                      <MenuItem key={employee.id} value={employee.id}>
                        {employee.full_name} —{" "}
                        {employee.job_title ?? employee.username}
                      </MenuItem>
                    ))}
                  </TextField>
                ) : (
                  <Alert severity="info" sx={{ mt: 1 }}>
                    {t("ticketDetail.ownFollowUp")}
                  </Alert>
                )}
                <TextField
                  type="datetime-local"
                  name="pending_follow_up_at"
                  label={t("ticketDetail.followUpDeadline")}
                  required
                  defaultValue={new Date(Date.now() + 24 * 60 * 60_000)
                    .toISOString()
                    .slice(0, 16)}
                  fullWidth
                  margin="normal"
                  slotProps={{ inputLabel: { shrink: true } }}
                />
              </>
            )}
            {resolutionDetailsTarget && !isChangeRequest && (
              <TextField
                select
                required
                label={t("ticketDetail.serviceProvided")}
                value={resolutionServiceIds}
                onChange={(event) =>
                  setResolutionServiceIds(
                    (event.target.value as unknown as number[]).map(Number),
                  )
                }
                SelectProps={{
                  multiple: true,
                  renderValue: (value) =>
                    (value as number[])
                      .map((serviceId) =>
                        localized(
                          services.data?.find((item) => item.id === serviceId),
                        ),
                      )
                      .join(", "),
                }}
                fullWidth
                margin="normal"
                helperText={t("ticketDetail.serviceProvidedHelp")}
              >
                {services.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    <Checkbox
                      checked={resolutionServiceIds.includes(item.id)}
                    />
                    {localized(item)}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {resolutionDetailsTarget && (
              <>
                <Button
                  variant="outlined"
                  onClick={generateResolutionWithLocalAi}
                  disabled={resolutionAiLoading}
                  sx={{ mt: 1 }}
                >
                  {resolutionAiLoading
                    ? "Drafting with local AI…"
                    : "Draft resolution with local AI"}
                </Button>
                {resolutionAiError && (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {resolutionAiError}
                  </Alert>
                )}
                {resolutionAiSuggestion && (
                  <Alert severity="info" sx={{ mt: 1 }}>
                    {resolutionAiSuggestion.customer_resolution && (
                      <Typography variant="body2">
                        <strong>Customer-facing wording:</strong>{" "}
                        {resolutionAiSuggestion.customer_resolution}
                      </Typography>
                    )}
                    {resolutionAiSuggestion.preventive_action && (
                      <Typography variant="body2">
                        <strong>Preventive action:</strong>{" "}
                        {resolutionAiSuggestion.preventive_action}
                      </Typography>
                    )}
                    {resolutionAiSuggestion.missing_closure_information.length >
                      0 && (
                      <Typography variant="body2">
                        <strong>Still needed:</strong>{" "}
                        {resolutionAiSuggestion.missing_closure_information.join(
                          " · ",
                        )}
                      </Typography>
                    )}
                  </Alert>
                )}
                <TextField
                  name="resolution_summary"
                  label={
                    isChangeRequest
                      ? "Change completion summary"
                      : t("ticketDetail.resolution")
                  }
                  required
                  fullWidth
                  multiline
                  rows={4}
                  margin="normal"
                  inputProps={{ minLength: 5 }}
                  value={resolutionSummary}
                  onChange={(event) => setResolutionSummary(event.target.value)}
                />
                {knowledgeError && (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {knowledgeError}
                  </Alert>
                )}
                {hasPermission("knowledge.view") && (
                  <Paper variant="outlined" sx={{ mt: 1.5, p: 1.5 }}>
                    <Typography fontWeight={700}>
                      {t("ticketDetail.searchKnowledge")}
                    </Typography>
                    <TextField
                      size="small"
                      fullWidth
                      sx={{ mt: 1 }}
                      value={knowledgeSearch}
                      onChange={(event) =>
                        setKnowledgeSearch(event.target.value)
                      }
                      placeholder={t("ticketDetail.searchKnowledge")}
                    />
                    {articleCandidates.isLoading && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 1 }}
                      >
                        {t("ticketDetail.loadingArticles")}
                      </Typography>
                    )}
                    {!articleCandidates.isLoading &&
                      articleCandidates.data?.length === 0 && (
                        <Alert severity="info" sx={{ mt: 1 }}>
                          {t("ticketDetail.noArticleMatches")}
                        </Alert>
                      )}
                    {!!articleCandidates.data?.length && (
                      <Stack spacing={0.5} sx={{ mt: 1 }}>
                        {articleCandidates.data.slice(0, 8).map((article) => (
                          <Stack
                            key={article.id}
                            direction={{ xs: "column", sm: "row" }}
                            alignItems={{ sm: "center" }}
                            gap={0.5}
                          >
                            <Typography variant="body2" sx={{ flex: 1 }}>
                              {article.title}
                              {article.category ? ` — ${article.category}` : ""}
                            </Typography>
                            <Button
                              size="small"
                              onClick={() => setViewArticleId(article.id)}
                            >
                              {t("ticketDetail.viewArticle")}
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              disabled={applyKnowledgeResolution.isPending}
                              onClick={() =>
                                applyKnowledgeResolution.mutate(article.id)
                              }
                            >
                              {t("ticketDetail.applyResolution")}
                            </Button>
                          </Stack>
                        ))}
                      </Stack>
                    )}
                  </Paper>
                )}
                {hasPermission("knowledge.view") &&
                  !!knowledgeRecommendations.data?.length && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      <Typography fontWeight={700}>
                        {t("ticketDetail.suggestedResolutions", {
                          defaultValue:
                            "Suggested resolutions from Knowledge Base",
                        })}
                      </Typography>
                      <Stack alignItems="flex-start">
                        {knowledgeRecommendations.data
                          .slice(0, 5)
                          .map((article) => (
                            <Button
                              key={article.id}
                              size="small"
                              disabled={applyKnowledgeResolution.isPending}
                              onClick={() =>
                                applyKnowledgeResolution.mutate(article.id)
                              }
                            >
                              {t("ticketDetail.applyKnowledgeResolution", {
                                title: article.title,
                                score: article.match_score,
                                reasons: (article.match_reasons ?? []).join(
                                  ", ",
                                ),
                                defaultValue:
                                  "Apply {{title}} · {{score}}% — {{reasons}}",
                              })}
                            </Button>
                          ))}
                      </Stack>
                    </Alert>
                  )}
                {!isChangeRequest && <TextField
                  select
                  label={t("ticketDetail.rootCauses")}
                  required
                  fullWidth
                  margin="normal"
                  value={resolutionRootCauseIds}
                  onChange={(event) =>
                    setResolutionRootCauseIds(
                      (event.target.value as unknown as number[]).map(Number),
                    )
                  }
                  SelectProps={{
                    multiple: true,
                    renderValue: (value) =>
                      (value as number[])
                        .map(
                          (rootCauseId) =>
                            localized(
                              rootCauses.data?.find(
                                (item) => item.id === rootCauseId,
                              ),
                            ) || `#${rootCauseId}`,
                        )
                        .join(", "),
                  }}
                  helperText={t("ticketDetail.rootCauseHelp")}
                >
                  {rootCauses.data?.map((cause) => (
                    <MenuItem key={cause.id} value={cause.id}>
                      <Checkbox
                        checked={resolutionRootCauseIds.includes(cause.id)}
                      />
                      {localized(cause)}
                    </MenuItem>
                  ))}
                </TextField>}
                {!isChangeRequest && resolutionOutcomeRequired && (
                  <TextField
                    select
                    required
                    name="resolution_outcome_id"
                    label={t("ticketDetail.resolutionOutcome")}
                    value={resolutionOutcomeId}
                    onChange={(event) =>
                      setResolutionOutcomeId(event.target.value)
                    }
                    fullWidth
                    margin="normal"
                  >
                    <MenuItem value="" disabled>
                      {t("ticketDetail.selectOutcome")}
                    </MenuItem>
                    {resolutionOutcomes.data?.map((outcome) => (
                      <MenuItem key={outcome.id} value={outcome.id}>
                        {localized(outcome)}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
                {!isChangeRequest && permanentFixRequired && (
                  <>
                    <TextField
                      select
                      required
                      name="permanent_fix_status"
                      label={t("ticketDetail.permanentFixStatus")}
                      value={permanentFixStatus}
                      onChange={(event) =>
                        setPermanentFixStatus(event.target.value)
                      }
                      fullWidth
                      margin="normal"
                    >
                      <MenuItem value="PLANNED">
                        {t("ticketDetail.planned")}
                      </MenuItem>
                      <MenuItem value="IMPLEMENTED">
                        {t("ticketDetail.implemented")}
                      </MenuItem>
                      <MenuItem value="VERIFIED">
                        {t("ticketDetail.verified")}
                      </MenuItem>
                    </TextField>
                    <TextField
                      required
                      name="permanent_fix_summary"
                      label={t("ticketDetail.permanentFixEvidence")}
                      fullWidth
                      multiline
                      rows={2}
                      margin="normal"
                      inputProps={{ minLength: 5 }}
                      value={permanentFixSummary}
                      onChange={(event) =>
                        setPermanentFixSummary(event.target.value)
                      }
                    />
                  </>
                )}
                {!isChangeRequest && <Stack
                  direction="row"
                  alignItems="center"
                  sx={{ mt: 1, py: 0.5, borderTop: 1, borderColor: "divider" }}
                >
                  <FormControlLabel
                    sx={{ m: 0, flex: 1 }}
                    control={
                      <Switch
                        size="small"
                        checked={createKnowledgeArticle}
                        onChange={(_, checked) =>
                          setCreateKnowledgeArticle(checked)
                        }
                      />
                    }
                    label={t("ticketDetail.createKnowledgeFromResolution")}
                  />
                  <Tooltip title={t("ticketDetail.createKnowledgeHelp")} arrow>
                    <InfoOutlined
                      color="action"
                      fontSize="small"
                      aria-label={t("ticketDetail.createKnowledgeHelp")}
                    />
                  </Tooltip>
                </Stack>}
                {targetStatus === "RESOLVED" &&
                  hasPermission("ticket.close") && (
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      alignItems={{ xs: "stretch", sm: "center" }}
                      gap={{ xs: 0, sm: 1 }}
                      sx={{ py: 0.5, borderTop: 1, borderColor: "divider" }}
                    >
                      <FormControlLabel
                        sx={{ m: 0 }}
                        control={
                          <Switch
                            size="small"
                            checked={closeAfterResolve}
                            onChange={(_, checked) =>
                              setCloseAfterResolve(checked)
                            }
                          />
                        }
                        label={t("ticketDetail.closeAfterResolve")}
                      />
                      <Tooltip
                        title={t("ticketDetail.closeAfterResolveHelp")}
                        arrow
                      >
                        <InfoOutlined
                          color="action"
                          fontSize="small"
                          aria-label={t("ticketDetail.closeAfterResolveHelp")}
                        />
                      </Tooltip>
                      {hasPermission("ticket.auto_close_on_resolve") && (
                        <FormControlLabel
                          sx={{
                            m: 0,
                            marginInlineStart: { sm: "auto" },
                            "& .MuiFormControlLabel-label": {
                              typography: "caption",
                            },
                          }}
                          control={
                            <Checkbox
                              size="small"
                              checked={saveCloseDefault}
                              onChange={(_, checked) =>
                                setSaveCloseDefault(checked)
                              }
                            />
                          }
                          label={t("ticketDetail.saveResolutionDefault")}
                        />
                      )}
                    </Stack>
                  )}
              </>
            )}
            {(targetStatus === "RESOLVED" || targetStatus === "CLOSED") &&
              (hasPermission("ticket.comment.public") ||
                hasPermission("ticket.change.status")) && (
                <Stack
                  spacing={0.5}
                  sx={{
                    py: 0.75,
                    mt: 0.5,
                    borderTop: 1,
                    borderColor: "divider",
                  }}
                >
                  <Stack direction="row" alignItems="center" gap={0.75}>
                    <Typography variant="body2" fontWeight={700} flex={1}>
                      {t("ticketDetail.resolutionAttachments")}
                    </Typography>
                    <Tooltip
                      title={t("ticketDetail.resolutionAttachmentsHelp")}
                      arrow
                    >
                      <InfoOutlined
                        color="action"
                        fontSize="small"
                        aria-label={t("ticketDetail.resolutionAttachmentsHelp")}
                      />
                    </Tooltip>
                    <Button
                      component="label"
                      variant="outlined"
                      size="small"
                      disabled={transitionSubmitting}
                    >
                      {t("ticketDetail.selectFiles")}
                      <input
                        hidden
                        multiple
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.txt,.log,.csv,.docx,.xlsx"
                        onChange={(event) => {
                          setResolutionAttachments(
                            Array.from(event.target.files ?? []),
                          );
                          event.target.value = "";
                        }}
                      />
                    </Button>
                  </Stack>
                  {resolutionAttachments.length > 0 && (
                    <Stack spacing={0.5} mt={1}>
                      {resolutionAttachments.map((file, index) => (
                        <Stack
                          key={`${file.name}-${index}`}
                          direction="row"
                          alignItems="center"
                          spacing={1}
                        >
                          <Typography variant="body2" flex={1}>
                            {file.name} ({Math.ceil(file.size / 1024)} KB)
                          </Typography>
                          <Button
                            size="small"
                            color="error"
                            onClick={() =>
                              setResolutionAttachments((files) =>
                                files.filter(
                                  (_, itemIndex) => itemIndex !== index,
                                ),
                              )
                            }
                          >
                            {t("common.actions.delete")}
                          </Button>
                        </Stack>
                      ))}
                    </Stack>
                  )}
                </Stack>
              )}
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                setStatusDialog(false);
                setResolutionAttachments([]);
                setCreateKnowledgeArticle(false);
              }}
              disabled={transitionSubmitting}
            >
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!targetStatus || transitionSubmitting}
            >
              {transitionSubmitting
                ? t("ticketDetail.uploadingSaving")
                : t("ticketDetail.changeStatus")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={worklogDialog}
        onClose={() => setWorklogDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            createWorklog.mutate({
              task_id: values.task_id ? Number(values.task_id) : null,
              started_at: new Date(String(values.started_at)).toISOString(),
              ended_at: new Date(String(values.ended_at)).toISOString(),
              notes: String(values.notes).trim(),
            });
          }}
        >
          <DialogTitle>{t("ticketDetail.recordWork")}</DialogTitle>
          <DialogContent>
            <TextField
              select
              name="task_id"
              label={t("ticketDetail.linkedTask")}
              defaultValue=""
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("ticketDetail.ticketLevelWork")}</MenuItem>
              {tasks.data?.map((task) => (
                <MenuItem key={task.id} value={task.id}>
                  {task.title}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              required
              type="datetime-local"
              name="started_at"
              label={t("ticketDetail.started")}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              required
              type="datetime-local"
              name="ended_at"
              label={t("ticketDetail.ended")}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              required
              name="notes"
              label={t("ticketDetail.workPerformed")}
              multiline
              rows={3}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 2 }}
            />
            {createWorklog.isError && (
              <Alert severity="error">{t("ticketDetail.worklogFailed")}</Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setWorklogDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createWorklog.isPending}
            >
              {t("ticketDetail.saveDraft")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={escalationChoiceDialog}
        onClose={() => setEscalationChoiceDialog(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>{t("ticketDetail.escalateHelp")}</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary">
            {t("ticketDetail.chooseWorkDestination")}
          </Typography>
          <Stack spacing={1} mt={2}>
            {hasPermission("ticket.escalate") && (
              <Button
                variant="outlined"
                color="warning"
                onClick={() => {
                  setEscalationChoiceDialog(false);
                  setEscalationDialog(true);
                }}
              >
                {t("ticketDetail.withinDepartment")}
              </Button>
            )}
            {hasPermission("ticket.help.request") && (
              <Button
                variant="contained"
                onClick={() => {
                  setEscalationChoiceDialog(false);
                  setHelpDialog(true);
                }}
              >
                {t("ticketDetail.anotherDepartment")}
              </Button>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEscalationChoiceDialog(false)}>
            {t("common.actions.cancel")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={escalationDialog}
        onClose={() => setEscalationDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitEscalation}>
          <DialogTitle>{t("ticketDetail.internalEscalation")}</DialogTitle>
          <DialogContent>
            {escalationError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {escalationError}
              </Alert>
            )}
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("ticketDetail.escalationNotice")}
            </Alert>
            <TextField
              label={t("ticketDetail.searchEngineer")}
              value={escalationSearch}
              onChange={(event) => setEscalationSearch(event.target.value)}
              fullWidth
              margin="normal"
              placeholder={t("ticketDetail.engineerSearchPlaceholder")}
            />
            <TextField
              select
              name="escalation_assignee_user_id"
              label={t("ticketDetail.escalateTo")}
              fullWidth
              margin="normal"
              defaultValue={ticket.data.escalation_assignee_user_id ?? ""}
              helperText={t("ticketDetail.escalateToHelp")}
            >
              <MenuItem value="">{t("ticketDetail.clearEscalation")}</MenuItem>
              {assignees.data
                ?.filter(
                  (employee) =>
                    (user?.department_id
                      ? employee.department ===
                        departments.data?.find(
                          (department) => department.id === user.department_id,
                        )?.name
                      : !employee.department) &&
                    `${employee.full_name} ${employee.username} ${employee.department ?? ""} ${employee.job_title ?? ""}`
                      .toLowerCase()
                      .includes(escalationSearch.toLowerCase()),
                )
                .map((employee) => (
                  <MenuItem key={employee.id} value={employee.id}>
                    {employee.full_name} —{" "}
                    {employee.job_title ??
                      employee.department ??
                      employee.username}
                    {employee.department ? ` (${employee.department})` : ""}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              select
              required
              name="escalation_level"
              label={t("ticketDetail.escalationType")}
              fullWidth
              margin="normal"
              defaultValue={ticket.data.escalation_level ?? "SENIOR_ENGINEER"}
            >
              <MenuItem value="SENIOR_ENGINEER">
                {t("ticketDetail.seniorEngineer")}
              </MenuItem>
              <MenuItem value="TEAM_LEADER">
                {t("ticketDetail.teamLeader")}
              </MenuItem>
            </TextField>
            <TextField
              required
              name="reason"
              label={t("ticketDetail.escalationReason")}
              fullWidth
              multiline
              rows={3}
              margin="normal"
              defaultValue={ticket.data.escalation_reason ?? ""}
              inputProps={{ minLength: 5 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEscalationDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              color="warning"
              variant="contained"
              disabled={escalate.isPending}
            >
              {escalate.isPending
                ? t("ticketDetail.saving")
                : t("ticketDetail.saveEscalation")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={helpDialog}
        onClose={() => setHelpDialog(false)}
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
            requestHelp.mutate({
              department_id: Number(values.department_id),
              team_id: values.team_id ? Number(values.team_id) : null,
              escalation_assignee_user_id: values.assignee_id
                ? Number(values.assignee_id)
                : null,
              escalation_level: "OTHER_DEPARTMENT",
              reason: String(values.reason),
              version: ticket.data.version,
            });
          }}
        >
          <DialogTitle>{t("ticketDetail.requestDepartment")}</DialogTitle>
          <DialogContent>
            {helpError && <Alert severity="error">{helpError}</Alert>}
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("ticketDetail.departmentHelpNotice")}
            </Alert>
            <TextField
              select
              required
              name="department_id"
              label={t("ticketDetail.department")}
              value={helpDepartmentId}
              onChange={(event) => setHelpDepartmentId(event.target.value)}
              fullWidth
              margin="normal"
            >
              {departments.data
                ?.filter((row) => row.is_active)
                .map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {localized(row)}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              select
              name="team_id"
              label={t("ticketDetail.optionalTeam")}
              defaultValue=""
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("ticketDetail.entireDepartment")}</MenuItem>
              {supportTeams.data
                ?.filter(
                  (row) =>
                    row.is_active &&
                    row.department_id === Number(helpDepartmentId),
                )
                .map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              select
              name="assignee_id"
              label={t("ticketDetail.optionalEngineer")}
              defaultValue=""
              fullWidth
              margin="normal"
            >
              <MenuItem value="">{t("ticketDetail.departmentQueue")}</MenuItem>
              {assignees.data
                ?.filter(
                  (row) =>
                    row.department ===
                    departments.data?.find(
                      (item) => item.id === Number(helpDepartmentId),
                    )?.name,
                )
                .map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.full_name} — {row.job_title ?? row.username}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              required
              name="reason"
              label={t("ticketDetail.helpRequired")}
              multiline
              rows={4}
              inputProps={{ minLength: 5 }}
              fullWidth
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setHelpDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={requestHelp.isPending}
            >
              {t("ticketDetail.createRequest")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={returnDialog}
        onClose={() => setReturnDialog(false)}
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
            returnHelp.mutate({
              result: String(values.result),
              version: ticket.data.version,
            });
          }}
        >
          <DialogTitle>{t("ticketDetail.returnToSupport")}</DialogTitle>
          <DialogContent>
            {helpError && <Alert severity="error">{helpError}</Alert>}
            <TextField
              required
              name="result"
              label={t("ticketDetail.completedResult")}
              multiline
              rows={6}
              inputProps={{ minLength: 5 }}
              fullWidth
              margin="normal"
              helperText={t("ticketDetail.returnResultHelp")}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setReturnDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              color="success"
              disabled={returnHelp.isPending}
            >
              {t("ticketDetail.returnResult")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={handoverDialog}
        onClose={() => setHandoverDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            handover.mutate({
              reason: String(values.reason).trim(),
              to_user_id: values.to_user_id ? Number(values.to_user_id) : null,
              follow_up_at: new Date(String(values.follow_up_at)).toISOString(),
              reassign: values.reassign === "on",
              version: ticket.data?.version,
            });
          }}
        >
          <DialogTitle>{t("ticketDetail.shiftHandover")}</DialogTitle>
          <DialogContent>
            <Alert severity="info" sx={{ mb: 1 }}>
              {t("ticketDetail.handoverNotice")}
            </Alert>
            {handoverError && <Alert severity="error">{handoverError}</Alert>}
            <TextField
              required
              select
              name="to_user_id"
              label={t("ticketDetail.receivingEngineer")}
              defaultValue=""
              fullWidth
              margin="normal"
            >
              <MenuItem value="">
                {t("ticketDetail.nextShiftUnassigned")}
              </MenuItem>
              {assignees.data
                ?.filter((item) => item.id !== user?.id)
                .map((engineer) => (
                  <MenuItem key={engineer.id} value={engineer.id}>
                    {engineer.full_name}
                    {engineer.job_title ? ` — ${engineer.job_title}` : ""}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              required
              name="follow_up_at"
              type="datetime-local"
              label={t("ticketDetail.receivingFollowUp")}
              defaultValue={new Date(Date.now() + 12 * 60 * 60_000)
                .toISOString()
                .slice(0, 16)}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              required
              name="reason"
              label={t("ticketDetail.handoverReason")}
              multiline
              rows={4}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 5, maxLength: 1000 }}
            />
            <FormControlLabel
              control={<Checkbox name="reassign" defaultChecked />}
              label={t("ticketDetail.reassignReceiving")}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setHandoverDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              color="warning"
              variant="contained"
              disabled={handover.isPending}
            >
              {t("ticketDetail.handOver")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={assignmentDialog}
        onClose={() => setAssignmentDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitAssignment}>
          <DialogTitle>{t("ticketDetail.assignEngineer")}</DialogTitle>
          <DialogContent>
            {assignmentError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {assignmentError}
              </Alert>
            )}
            <TextField
              label={t("ticketDetail.searchEngineer")}
              value={assignmentSearch}
              onChange={(event) => setAssignmentSearch(event.target.value)}
              fullWidth
              margin="normal"
              placeholder={t("ticketDetail.engineerSearchPlaceholder")}
            />
            <TextField
              select
              required
              name="assigned_user_id"
              label={t("ticketDetail.engineer")}
              fullWidth
              margin="normal"
              defaultValue={ticket.data.assigned_user_id ?? ""}
            >
              {assignmentAssignees.data?.map((engineer) => (
                <MenuItem key={engineer.id} value={engineer.id}>
                  {engineer.last_assigned_at ? "Recent · " : ""}
                  {engineer.full_name}
                  {engineer.job_title ? ` — ${engineer.job_title}` : ""}
                  {engineer.department ? ` (${engineer.department})` : ""}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              name="assigned_team"
              label={t("ticketDetail.supportTeam")}
              fullWidth
              margin="normal"
              defaultValue={ticket.data.assigned_team ?? ""}
            >
              <MenuItem value="">
                {t("ticketDetail.useEngineerDepartment")}
              </MenuItem>
              {supportTeams.data
                ?.filter((team) => team.is_active)
                .map((team) => (
                  <MenuItem key={team.id} value={team.name}>
                    {team.name}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              name="reason"
              label={t("ticketDetail.assignmentReason")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              inputProps={{ maxLength: 500 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAssignmentDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={assign.isPending}
            >
              {assign.isPending
                ? t("ticketDetail.assigning")
                : t("ticketDetail.assignEngineer")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={callerDialog}
        onClose={() => setCallerDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitCaller}>
          <DialogTitle>{t("ticketDetail.changeCaller")}</DialogTitle>
          <DialogContent>
            {callerError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {callerError}
              </Alert>
            )}
            <TextField
              select
              name="requester_contact_id"
              label={t("ticketDetail.caller")}
              fullWidth
              margin="normal"
              value={callerSelection}
              onChange={(event) =>
                setCallerSelection(String(event.target.value))
              }
              helperText={t("ticketDetail.activeCallersHelp")}
            >
              <MenuItem value="">{t("ticketDetail.noCaller")}</MenuItem>
              {callerContacts.data
                ?.filter((contact) => contact.is_active)
                .map((contact) => (
                  <MenuItem key={contact.id} value={contact.id}>
                    {contact.full_name} —{" "}
                    {contact.phone_number ??
                      contact.email ??
                      t("ticketDetail.noContactDetails")}
                  </MenuItem>
                ))}
            </TextField>
            {hasPermission("contact.manage") && (
              <Button
                type="button"
                size="small"
                onClick={() => setNewCallerDialog(true)}
              >
                {t("ticketDetail.addCaller")}
              </Button>
            )}
            <TextField
              required
              name="reason"
              label={t("ticketDetail.callerChangeReason")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              inputProps={{ minLength: 3 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCallerDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={updateCaller.isPending}
            >
              {updateCaller.isPending
                ? t("ticketDetail.saving")
                : t("ticketDetail.saveCaller")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={newCallerDialog}
        onClose={() => setNewCallerDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitNewCaller}>
          <DialogTitle>{t("ticketDetail.addCaller")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="full_name"
              label={t("ticketDetail.callerName")}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 2 }}
            />
            <TextField
              name="phone_number"
              label={t("ticketDetail.mobile")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="email"
              type="email"
              label={t("ticketDetail.email")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="job_title"
              label={t("ticketDetail.role")}
              fullWidth
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setNewCallerDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createCaller.isPending}
            >
              {t("ticketDetail.addAndSelectCaller")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={followersDialog}
        onClose={() => setFollowersDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{t("ticketDetail.manageFollowers")}</DialogTitle>
        <DialogContent>
          {followersError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {followersError}
            </Alert>
          )}
          <TextField
            select
            label={t("ticketDetail.followers")}
            value={followerIds}
            onChange={(event) =>
              setFollowerIds(event.target.value as unknown as number[])
            }
            SelectProps={{ multiple: true }}
            fullWidth
            margin="normal"
          >
            {assignees.data?.map((employee) => (
              <MenuItem key={employee.id} value={employee.id}>
                {employee.full_name} — {employee.job_title ?? employee.username}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            id="followers-reason"
            label={t("ticketDetail.reason")}
            required
            fullWidth
            multiline
            rows={2}
            margin="normal"
            inputProps={{ minLength: 3 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFollowersDialog(false)}>
            {t("common.actions.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={updateFollowers.isPending}
            onClick={() => {
              const reason =
                (
                  document.getElementById(
                    "followers-reason",
                  ) as HTMLInputElement | null
                )?.value.trim() ?? "";
              if (reason.length >= 3 && ticket.data)
                updateFollowers.mutate({
                  user_ids: followerIds,
                  reason,
                  version: ticket.data.version,
                });
            }}
          >
            {t("ticketDetail.saveFollowers")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={taskDialog}
        onClose={() => setTaskDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            createTask.mutate({
              title: String(values.title).trim(),
              description: String(values.description).trim() || null,
              assigned_user_id: values.assigned_user_id
                ? Number(values.assigned_user_id)
                : null,
              due_at: values.due_at || null,
            });
          }}
        >
          <DialogTitle>{t("ticketDetail.addTask")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="title"
              label={t("ticketDetail.task")}
              fullWidth
              margin="normal"
            />
            <TextField
              name="description"
              label={t("tickets.description")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <TextField
              select
              name="assigned_user_id"
              label={t("ticketDetail.assignedEmployee")}
              fullWidth
              margin="normal"
              defaultValue=""
            >
              <MenuItem value="">{t("ticketDetail.unassigned")}</MenuItem>
              {assignees.data?.map((employee) => (
                <MenuItem key={employee.id} value={employee.id}>
                  {employee.full_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              type="datetime-local"
              name="due_at"
              label={t("ticketDetail.dueDate")}
              fullWidth
              margin="normal"
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTaskDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createTask.isPending}
            >
              {t("ticketDetail.addTask")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={checklistDialog}
        onClose={() => setChecklistDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const label = String(
              new FormData(event.currentTarget).get("label") ?? "",
            ).trim();
            if (label.length >= 2) createChecklistItem.mutate(label);
          }}
        >
          <DialogTitle>{t("ticketDetail.addChecklistItem")}</DialogTitle>
          <DialogContent>
            <TextField
              required
              name="label"
              label={t("ticketDetail.checklistItem")}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 2 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setChecklistDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createChecklistItem.isPending}
            >
              {t("ticketDetail.addItem")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={relationDialog}
        onClose={() => setRelationDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitRelation}>
          <DialogTitle>
            {t(
              isIncident
                ? "ticketDetail.addIssuesToIncident"
                : "ticketDetail.linkRelated",
            )}
          </DialogTitle>
          <DialogContent>
            {relationError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {relationError}
              </Alert>
            )}
            <TextField
              label={t("ticketDetail.searchTicket")}
              fullWidth
              margin="normal"
              value={relationSearch}
              onChange={(event) => setRelationSearch(event.target.value)}
            />
            <TextField
              select
              required
              label={t(
                isIncident
                  ? "ticketDetail.incidentIssues"
                  : "ticketDetail.relatedTickets",
              )}
              fullWidth
              margin="normal"
              value={relationTicketIds}
              onChange={(event) =>
                setRelationTicketIds(
                  (event.target.value as unknown as number[]).map(Number),
                )
              }
              SelectProps={{
                multiple: true,
                renderValue: (value) =>
                  t("ticketDetail.ticketsSelected", {
                    count: (value as number[]).length,
                  }),
              }}
            >
              {relationCandidates.data
                ?.filter((item) => String(item.id) !== id)
                .map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    <Checkbox checked={relationTicketIds.includes(item.id)} />
                    {item.ticket_number} — {item.subject}
                  </MenuItem>
                ))}
            </TextField>
            <TextField
              select
              required
              name="relation_type"
              label={t("ticketDetail.relationship")}
              fullWidth
              margin="normal"
              defaultValue={isIncident ? "PARENT_CHILD" : "RELATED"}
            >
              <MenuItem value="RELATED">{t("ticketDetail.related")}</MenuItem>
              <MenuItem value="DUPLICATE">
                {t("ticketDetail.duplicate")}
              </MenuItem>
              <MenuItem value="PARENT_CHILD">
                {t("ticketDetail.parentRelation")}
              </MenuItem>
              <MenuItem value="CAUSED_BY">
                {t("ticketDetail.causedBy")}
              </MenuItem>
            </TextField>
            <TextField
              name="reason"
              label={t("ticketDetail.reason")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setRelationDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={
                createRelation.isPending || relationTicketIds.length === 0
              }
            >
              {t(
                isIncident
                  ? "ticketDetail.addIssues"
                  : "ticketDetail.linkTickets",
              )}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={knowledgeDialog}
        onClose={() => setKnowledgeDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submitKnowledgeLink}>
          <DialogTitle>{t("ticketDetail.linkKnowledge")}</DialogTitle>
          <DialogContent>
            {knowledgeError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {knowledgeError}
              </Alert>
            )}
            <TextField
              label={t("ticketDetail.searchKnowledge")}
              fullWidth
              margin="normal"
              value={knowledgeSearch}
              onChange={(event) => setKnowledgeSearch(event.target.value)}
            />
            {articleCandidates.isLoading && (
              <Typography color="text.secondary">
                {t("ticketDetail.loadingArticles")}
              </Typography>
            )}
            {articleCandidates.isError && (
              <Alert severity="error">{t("ticketDetail.articlesFailed")}</Alert>
            )}
            {!articleCandidates.isLoading &&
              articleCandidates.data?.length === 0 && (
                <Alert severity="info">
                  {t("ticketDetail.noArticleMatches")}
                </Alert>
              )}
            <TextField
              select
              required
              name="article_id"
              label={t("ticketDetail.publishedArticle")}
              fullWidth
              margin="normal"
              value={selectedKnowledgeArticleId}
              onChange={(event) =>
                setSelectedKnowledgeArticleId(event.target.value)
              }
            >
              {articleCandidates.data?.map((article) => (
                <MenuItem key={article.id} value={article.id}>
                  {article.title}
                  {article.category ? ` — ${article.category}` : ""}
                </MenuItem>
              ))}
            </TextField>
            <Button
              size="small"
              disabled={!selectedKnowledgeArticleId}
              onClick={() =>
                setViewArticleId(Number(selectedKnowledgeArticleId))
              }
            >
              {t("ticketDetail.viewArticle")}
            </Button>
            <TextField
              name="reason"
              label={t("ticketDetail.articleReason")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setKnowledgeDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={linkArticle.isPending || !selectedKnowledgeArticleId}
            >
              {t("ticketDetail.linkArticle")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(viewArticleId)}
        onClose={() => setViewArticleId(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {viewedArticle.data?.title ?? t("ticketDetail.knowledgeArticle")}
        </DialogTitle>
        <DialogContent>
          {viewedArticle.isLoading && <CircularProgress />}
          {viewedArticle.isError && (
            <Alert severity="error">{t("ticketDetail.articleFailed")}</Alert>
          )}
          {viewedArticle.data && (
            <>
              <Stack direction="row" spacing={1} mb={2}>
                <Chip size="small" label={viewedArticle.data.status} />
                <Chip
                  size="small"
                  label={
                    viewedArticle.data.category ??
                    t("ticketDetail.uncategorized")
                  }
                />
              </Stack>
              <Typography variant="subtitle1" fontWeight={600}>
                {t("ticketDetail.summary")}
              </Typography>
              <Typography color="text.secondary">
                {viewedArticle.data.summary}
              </Typography>
              <Typography variant="subtitle1" fontWeight={600} sx={{ mt: 2 }}>
                {t("ticketDetail.content")}
              </Typography>
              <Typography sx={{ whiteSpace: "pre-wrap" }}>
                {viewedArticle.data.body}
              </Typography>
              <Typography variant="subtitle1" fontWeight={600} sx={{ mt: 2 }}>
                {t("ticketDetail.tags")}
              </Typography>
              <Typography>
                {viewedArticle.data.tags || t("ticketDetail.noTags")}
              </Typography>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewArticleId(null)}>
            {t("common.actions.close")}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={editDialog}
        onClose={() => setEditDialog(false)}
        fullWidth
        maxWidth="md"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            const canClassify = hasPermission("ticket.edit.classification");
            setEditError("");
            previewTicketSla.mutate({
              ...(hasPermission("ticket.edit.subject")
                ? { subject: values.subject }
                : {}),
              ...(hasPermission("ticket.edit.description")
                ? { description: values.description }
                : {}),
              ...(hasPermission("ticket.change.priority")
                ? { priority: values.priority }
                : {}),
              ...(hasPermission("ticket.change.client")
                ? {
                    client_id: Number(
                      values.client_id || ticket.data?.client_id,
                    ),
                  }
                : {}),
              ...(hasPermission("ticket.change.contract")
                ? {
                    contract_id: values.contract_id
                      ? Number(values.contract_id)
                      : null,
                  }
                : {}),
              ...(hasPermission("ticket.edit.due_date")
                ? {
                    due_at: values.due_at
                      ? new Date(String(values.due_at)).toISOString()
                      : null,
                  }
                : {}),
              ...(canClassify
                ? {
                    impact: values.impact,
                    urgency: values.urgency,
                    ticket_type_id: Number(
                      values.ticket_type_id || ticket.data?.ticket_type_id,
                    ),
                    product_id: values.product_id
                      ? Number(values.product_id)
                      : null,
                    product_module_id: values.product_module_id
                      ? Number(values.product_module_id)
                      : null,
                    environment_id: values.environment_id
                      ? Number(values.environment_id)
                      : null,
                    service_id: values.service_id
                      ? Number(values.service_id)
                      : null,
                    category_id: values.category_id
                      ? Number(values.category_id)
                      : null,
                    subcategory_id: values.subcategory_id
                      ? Number(values.subcategory_id)
                      : null,
                    affected_users: values.affected_users || null,
                    patient_safety_flag: values.patient_safety_flag === "on",
                    security_incident_flag:
                      values.security_incident_flag === "on",
                  }
                : {}),
              reason: values.reason,
              version: ticket.data?.version,
            });
          }}
        >
          <DialogTitle>{t("ticketDetail.editTicket")}</DialogTitle>
          <DialogContent>
            {editError && <Alert severity="error">{editError}</Alert>}
            <TextField
              required
              name="subject"
              label={t("tickets.subject")}
              defaultValue={ticket.data.subject}
              disabled={!hasPermission("ticket.edit.subject")}
              fullWidth
              margin="normal"
              inputProps={{ minLength: 5 }}
            />
            <TextField
              required
              name="description"
              label={t("tickets.description")}
              defaultValue={ticket.data.description}
              disabled={!hasPermission("ticket.edit.description")}
              fullWidth
              multiline
              rows={5}
              margin="normal"
              inputProps={{ minLength: 10 }}
            />
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                select
                name="priority"
                label={t("tickets.priority")}
                defaultValue={ticket.data.priority}
                disabled={!hasPermission("ticket.change.priority")}
                fullWidth
                margin="normal"
              >
                {["P1", "P2", "P3", "P4"].map((value) => (
                  <MenuItem key={value} value={value}>
                    {t(`ticketDetail.classification.${value}`, {
                      defaultValue: value,
                    })}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="impact"
                label={t("ticketDetail.impact")}
                defaultValue={ticket.data.impact}
                disabled={!hasPermission("ticket.edit.classification")}
                fullWidth
                margin="normal"
              >
                {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
                  <MenuItem key={value} value={value}>
                    {t(`ticketDetail.classification.${value}`, {
                      defaultValue: value,
                    })}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="urgency"
                label={t("ticketDetail.urgency")}
                defaultValue={ticket.data.urgency}
                disabled={!hasPermission("ticket.edit.classification")}
                fullWidth
                margin="normal"
              >
                {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
                  <MenuItem key={value} value={value}>
                    {t(`ticketDetail.classification.${value}`, {
                      defaultValue: value,
                    })}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Divider sx={{ my: 2 }} />
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                select
                required
                name="client_id"
                label={t("ticketDetail.customer")}
                value={editClientId}
                onChange={(event) => setEditClientId(event.target.value)}
                disabled={
                  !hasPermission("ticket.change.client") ||
                  Boolean(
                    ticket.data.branch_id || ticket.data.requester_contact_id,
                  )
                }
                fullWidth
              >
                {!hasPermission("ticket.change.client") && (
                  <MenuItem value={String(ticket.data.client_id)}>
                    {t("ticketDetail.currentCustomer")}
                  </MenuItem>
                )}
                {ticketClients.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="contract_id"
                label={t("ticketDetail.relatedContract")}
                key={editClientId}
                defaultValue={
                  editClientId === String(ticket.data.client_id) &&
                  ticket.data.contract_id
                    ? String(ticket.data.contract_id)
                    : ""
                }
                disabled={!hasPermission("ticket.change.contract")}
                fullWidth
              >
                <MenuItem value="">{t("ticketDetail.automaticNone")}</MenuItem>
                {ticketContracts.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {value.contract_number} — {value.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                name="due_at"
                label={t("ticketDetail.dueDate")}
                type="datetime-local"
                defaultValue={
                  ticket.data.due_at ? ticket.data.due_at.slice(0, 16) : ""
                }
                disabled={!hasPermission("ticket.edit.due_date")}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
            </Stack>
            {Boolean(
              ticket.data.branch_id || ticket.data.requester_contact_id,
            ) &&
              hasPermission("ticket.change.client") && (
                <Alert severity="info" sx={{ mt: 1 }}>
                  {t("ticketDetail.customerChangeBlocked")}
                </Alert>
              )}
            <Divider sx={{ my: 2 }} />
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                select
                required
                name="ticket_type_id"
                label={t("portalCreate.requestType")}
                defaultValue={String(ticket.data.ticket_type_id)}
                disabled={!hasPermission("ticket.edit.classification")}
                fullWidth
              >
                {ticketTypes.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="category_id"
                label={t("ticketDetail.category")}
                value={editCategoryId}
                onChange={(event) => setEditCategoryId(event.target.value)}
                disabled={!hasPermission("ticket.edit.classification")}
                fullWidth
              >
                <MenuItem value="">{t("ticketDetail.none")}</MenuItem>
                {ticketCategories.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="subcategory_id"
                label={t("ticketDetail.subcategory")}
                key={editCategoryId}
                defaultValue={
                  String(ticket.data.category_id) === editCategoryId &&
                  ticket.data.subcategory_id
                    ? String(ticket.data.subcategory_id)
                    : ""
                }
                disabled={
                  !hasPermission("ticket.edit.classification") ||
                  !editCategoryId
                }
                fullWidth
              >
                <MenuItem value="">{t("ticketDetail.none")}</MenuItem>
                {ticketSubcategories.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t("ticketDetail.productServiceContext")}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                select
                name="product_id"
                label={t("portalCreate.product")}
                value={editProductId}
                onChange={(event) => setEditProductId(event.target.value)}
                disabled={!hasPermission("ticket.edit.classification")}
                fullWidth
              >
                <MenuItem value="">{t("ticketDetail.none")}</MenuItem>
                {products.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="product_module_id"
                label={t("portalCreate.module")}
                key={editProductId}
                defaultValue={
                  String(ticket.data.product_id) === editProductId &&
                  ticket.data.product_module_id
                    ? String(ticket.data.product_module_id)
                    : ""
                }
                disabled={
                  !hasPermission("ticket.edit.classification") || !editProductId
                }
                fullWidth
              >
                <MenuItem value="">{t("ticketDetail.noneAllModules")}</MenuItem>
                {editModules.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              sx={{ mt: 1 }}
            >
              <TextField
                select
                name="environment_id"
                label={t("ticketDetail.environment")}
                defaultValue={
                  ticket.data.environment_id
                    ? String(ticket.data.environment_id)
                    : ""
                }
                disabled={!hasPermission("ticket.edit.classification")}
                fullWidth
              >
                <MenuItem value="">{t("ticketDetail.none")}</MenuItem>
                {environments.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="service_id"
                label={t("portalCreate.service")}
                defaultValue={
                  ticket.data.service_id ? String(ticket.data.service_id) : ""
                }
                disabled={!hasPermission("ticket.edit.classification")}
                fullWidth
              >
                <MenuItem value="">{t("ticketDetail.none")}</MenuItem>
                {services.data?.map((value) => (
                  <MenuItem key={value.id} value={String(value.id)}>
                    {localized(value)}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("ticketDetail.revalidationNotice")}
            </Alert>
            <TextField
              name="affected_users"
              label={t("ticketDetail.affectedUsers")}
              defaultValue={ticket.data.affected_users ?? ""}
              disabled={!hasPermission("ticket.edit.classification")}
              fullWidth
              margin="normal"
            />
            <Stack direction={{ xs: "column", sm: "row" }}>
              <FormControlLabel
                control={
                  <Checkbox
                    name="patient_safety_flag"
                    defaultChecked={ticket.data.patient_safety_flag}
                    disabled={!hasPermission("ticket.edit.classification")}
                  />
                }
                label={t("ticketDetail.patientSafety")}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="security_incident_flag"
                    defaultChecked={ticket.data.security_incident_flag}
                    disabled={!hasPermission("ticket.edit.classification")}
                  />
                }
                label={t("ticketDetail.securityIncident")}
              />
            </Stack>
            <TextField
              required
              name="reason"
              label={t("ticketDetail.changeReason")}
              fullWidth
              multiline
              rows={2}
              margin="normal"
              inputProps={{ minLength: 5 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={editTicket.isPending}
            >
              {t("ticketDetail.saveAudited")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={Boolean(slaEditPreview && pendingEditPayload)}
        onClose={() => {
          setSlaEditPreview(null);
          setPendingEditPayload(null);
          setSlaPreviewError("");
          setSlaReevaluationReason("");
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>SLA impact confirmation</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This edit changes the contractual SLA. The active resolution clock
            will restart at the confirmed edit time; a completed first response
            remains historical.
          </Alert>
          {slaEditPreview && (
            <Stack spacing={1}>
              <Typography variant="body2">
                Changed: <b>{slaEditPreview.changed_fields.join(", ")}</b>
              </Typography>
              <Typography variant="body2">
                First response:{" "}
                <b>{slaDuration(slaEditPreview.old_first_response_minutes)}</b>{" "}
                →{" "}
                <b>{slaDuration(slaEditPreview.new_first_response_minutes)}</b>
              </Typography>
              <Typography variant="body2">
                Resolution:{" "}
                <b>{slaDuration(slaEditPreview.old_resolution_minutes)}</b> →{" "}
                <b>{slaDuration(slaEditPreview.new_resolution_minutes)}</b>
              </Typography>
              <Typography variant="body2">
                Target: <b>#{slaEditPreview.old_target_id ?? "—"}</b> →{" "}
                <b>#{slaEditPreview.new_target_id ?? "—"}</b>
              </Typography>
            </Stack>
          )}
          <TextField
            required
            autoFocus
            label="Reason for SLA re-evaluation"
            helperText="This reason is retained in the SLA audit history."
            value={slaReevaluationReason}
            onChange={(event) => setSlaReevaluationReason(event.target.value)}
            fullWidth
            multiline
            rows={2}
            margin="normal"
            inputProps={{ minLength: 5 }}
          />
          {slaPreviewError && <Alert severity="error">{slaPreviewError}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setSlaEditPreview(null);
              setPendingEditPayload(null);
              setSlaPreviewError("");
              setSlaReevaluationReason("");
            }}
          >
            {t("common.actions.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={editTicket.isPending}
            onClick={() => {
              if (
                !pendingEditPayload ||
                slaReevaluationReason.trim().length < 5
              ) {
                setSlaPreviewError(
                  "Enter at least five characters explaining the SLA change.",
                );
                return;
              }
              editTicket.mutate({
                ...pendingEditPayload,
                sla_reevaluation_reason: slaReevaluationReason.trim(),
              });
              setSlaEditPreview(null);
              setPendingEditPayload(null);
              setSlaPreviewError("");
              setSlaReevaluationReason("");
            }}
          >
            Confirm SLA change
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={templateDialog}
        onClose={() => setTemplateDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            createTemplate.mutate({
              name: String(values.get("name") ?? "").trim(),
              keywords: String(values.get("keywords") ?? "").trim(),
              scope: String(values.get("scope") ?? "GLOBAL"),
              portal_visible: values.get("portal_visible") === "on",
            });
          }}
        >
          <DialogTitle>
            {t("ticketDetail.createAsTemplate", {
              defaultValue: "Create as ticket template",
            })}
          </DialogTitle>
          <DialogContent>
            {createTemplate.isError && (
              <Alert severity="error">
                {t("ticketDetail.templateCreateFailed", {
                  defaultValue: "The ticket template could not be created.",
                })}
              </Alert>
            )}
            <TextField
              required
              name="name"
              label={t("ticketDetail.templateName", {
                defaultValue: "Template name",
              })}
              defaultValue={ticket.data?.subject}
              inputProps={{ minLength: 2, maxLength: 200 }}
              fullWidth
              margin="normal"
            />
            <TextField
              name="keywords"
              label={t("ticketDetail.templateKeywords", {
                defaultValue: "Keywords",
              })}
              helperText={t("ticketDetail.templateKeywordsHelp", {
                defaultValue: "Separate searchable phrases with commas.",
              })}
              defaultValue={ticket.data?.subject}
              fullWidth
              multiline
              rows={2}
              margin="normal"
            />
            <TextField
              select
              required
              name="scope"
              label={t("ticketDetail.templateScope", {
                defaultValue: "Template scope",
              })}
              defaultValue="GLOBAL"
              fullWidth
              margin="normal"
            >
              <MenuItem value="GLOBAL">
                {t("ticketDetail.scopeGlobal", { defaultValue: "Global" })}
              </MenuItem>
              <MenuItem value="CLIENT">
                {t("ticketDetail.scopeClient", { defaultValue: "This client" })}
              </MenuItem>
              <MenuItem value="PRODUCT">
                {t("ticketDetail.scopeProduct", {
                  defaultValue: "This product",
                })}
              </MenuItem>
              <MenuItem value="MODULE">
                {t("ticketDetail.scopeModule", { defaultValue: "This module" })}
              </MenuItem>
            </TextField>
            <FormControlLabel
              control={<Switch name="portal_visible" />}
              label={t("ticketDetail.portalVisibleTemplate", {
                defaultValue: "Available in Client Portal",
              })}
            />
            <Alert severity="info" sx={{ mt: 1 }}>
              {t("ticketDetail.templateSafeCopy", {
                defaultValue:
                  "Requester, SLA state, comments, worklogs, attachments, and audit history are not copied.",
              })}
            </Alert>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTemplateDialog(false)}>
              {t("common.actions.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createTemplate.isPending}
            >
              {t("ticketDetail.createTemplate", {
                defaultValue: "Create template",
              })}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={mentionDialog}
        onClose={() => !createMention.isPending && setMentionDialog(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Mention users</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {mentionError && <Alert severity="error">{mentionError}</Alert>}
            <Autocomplete
              multiple
              options={mentionCandidates.data ?? []}
              value={mentionRecipients}
              loading={mentionCandidates.isLoading}
              getOptionLabel={(option) =>
                `${option.full_name} (${option.email})`
              }
              isOptionEqualToValue={(option, value) => option.id === value.id}
              onChange={(_, value) => setMentionRecipients(value)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="@ Mention users"
                  placeholder="Type a name or email"
                />
              )}
            />
            <TextField
              label="Message"
              required
              multiline
              minRows={3}
              value={mentionMessage}
              onChange={(event) => setMentionMessage(event.target.value)}
            />
            {hasPermission("ticket.comment.internal") && (
              <FormControlLabel
                control={
                  <Switch
                    checked={mentionInternal}
                    onChange={(_, checked) => {
                      setMentionInternal(checked);
                      setMentionRecipients([]);
                    }}
                  />
                }
                label="Internal mention"
              />
            )}
            <FormControlLabel
              control={
                <Checkbox
                  checked={mentionFollowers}
                  onChange={(_, checked) => setMentionFollowers(checked)}
                />
              }
              label="Add mentioned users as ticket followers"
            />
            <Typography variant="caption" color="text.secondary">
              Only users who can access this ticket are listed. Client Portal
              users are available for public mentions.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setMentionDialog(false)}
            disabled={createMention.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => createMention.mutate()}
            disabled={
              createMention.isPending ||
              mentionRecipients.length === 0 ||
              !mentionMessage.trim()
            }
          >
            Mention & notify
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
