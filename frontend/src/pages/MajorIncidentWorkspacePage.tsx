import { ArrowBack, Edit } from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
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
} from "@mui/material";
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { TechnicalText } from "../components/TechnicalText";

type Incident = {
  id: number;
  major_incident_number: string;
  primary_ticket_id: number;
  severity: string;
  status: string;
  incident_commander_user_id: number;
  technical_owner_user_id?: number | null;
  communication_owner_user_id?: number | null;
  detected_at?: string | null;
  service_restored_at?: string | null;
  monitoring_started_at?: string | null;
  closed_at?: string | null;
  business_impact: string;
  affected_users?: string | null;
  current_status_summary: string;
  next_update_at?: string | null;
  resolution_summary?: string | null;
  post_incident_review?: string | null;
  problem_follow_up_owner_user_id?: number | null;
  problem_follow_up_due_at?: string | null;
  version: number;
  declared_at: string;
};
type Update = {
  id: number;
  update_type: string;
  internal_message?: string | null;
  client_message?: string | null;
  published_by_name: string;
  published_at: string;
};
type TicketLink = {
  id: number;
  ticket_id: number;
  ticket_number?: string | null;
  subject: string;
  link_type: string;
};
type ProblemLink = {
  id: number;
  problem_number: string;
  title: string;
  status: string;
};
type Scope = {
  client_ids: number[];
  product_ids: number[];
  product_module_ids: number[];
  service_ids: number[];
  environment_ids: number[];
};
type Option = {
  id: number;
  ticket_number?: string | null;
  subject?: string;
  problem_number?: string;
  title?: string;
  version?: number;
};
type CatalogOption = { id: number; name: string; code?: string };
type Assignee = { id: number; full_name: string; username: string };
const transitions: Record<string, string[]> = {
  DECLARED: ["RESPONSE_ACTIVE", "CANCELLED"],
  RESPONSE_ACTIVE: ["SERVICE_RESTORED", "CANCELLED"],
  SERVICE_RESTORED: ["MONITORING"],
  MONITORING: ["POST_INCIDENT_REVIEW", "RESPONSE_ACTIVE"],
  POST_INCIDENT_REVIEW: ["CLOSED", "RESPONSE_ACTIVE"],
  CLOSED: [],
  CANCELLED: [],
};
const label = (value?: string | null) =>
  value ? value.replaceAll("_", " ") : "—";
const optional = (value: FormDataEntryValue | null) =>
  String(value ?? "").trim() || null;
const dateInput = (value?: string | null) => (value ? value.slice(0, 16) : "");
const ids = (value: FormDataEntryValue | null) =>
  String(value ?? "")
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0);
function Detail({ title, value }: { title: string; value?: string | null }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {title}
      </Typography>
      <Typography sx={{ whiteSpace: "pre-wrap" }}>{value || "—"}</Typography>
    </Box>
  );
}

export function MajorIncidentWorkspacePage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const incidentId = Number(id);
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState("");
  const [linkOpen, setLinkOpen] = useState(false);
  const [problemOpen, setProblemOpen] = useState(false);
  const [scopeOpen, setScopeOpen] = useState(false);
  const [selectedScopeProductIds, setSelectedScopeProductIds] = useState<
    number[]
  >([]);
  const [selectedScopeModuleIds, setSelectedScopeModuleIds] = useState<
    number[]
  >([]);
  const [error, setError] = useState("");
  const incident = useQuery({
    queryKey: ["major-incident", incidentId],
    queryFn: async () =>
      (await api.get<Incident>(`/major-incidents/${incidentId}`)).data,
    enabled: Number.isFinite(incidentId),
  });
  const updates = useQuery({
    queryKey: ["major-incident-updates", incidentId],
    queryFn: async () =>
      (await api.get<Update[]>(`/major-incidents/${incidentId}/updates`)).data,
    enabled: !!incident.data,
  });
  const tickets = useQuery({
    queryKey: ["major-incident-tickets", incidentId],
    queryFn: async () =>
      (await api.get<TicketLink[]>(`/major-incidents/${incidentId}/tickets`))
        .data,
    enabled: !!incident.data,
  });
  const problems = useQuery({
    queryKey: ["major-incident-problems", incidentId],
    queryFn: async () =>
      (await api.get<ProblemLink[]>(`/major-incidents/${incidentId}/problems`))
        .data,
    enabled: !!incident.data,
  });
  const scopes = useQuery({
    queryKey: ["major-incident-scopes", incidentId],
    queryFn: async () =>
      (await api.get<Scope>(`/major-incidents/${incidentId}/scopes`)).data,
    enabled: !!incident.data,
  });
  const ticketOptions = useQuery({
    queryKey: ["major-incident-ticket-options"],
    queryFn: async () =>
      (
        await api.get<Option[]>("/tickets", {
          params: { limit: 200, open_only: true },
        })
      ).data,
    enabled: linkOpen,
  });
  const problemOptions = useQuery({
    queryKey: ["major-incident-problem-options"],
    queryFn: async () => (await api.get<Option[]>("/problems")).data,
    enabled: problemOpen,
  });
  const assignees = useQuery({
    queryKey: ["major-incident-assignees"],
    queryFn: async () => (await api.get<Assignee[]>("/ticket-assignees")).data,
    enabled: !!incident.data,
  });
  const clients = useQuery({
    queryKey: ["major-incident-scope-clients"],
    queryFn: async () =>
      (await api.get<CatalogOption[]>("/clients/ticket-options")).data,
    enabled: scopeOpen,
  });
  const products = useQuery({
    queryKey: ["major-incident-scope-products"],
    queryFn: async () => (await api.get<CatalogOption[]>("/products")).data,
    enabled: scopeOpen,
  });
  const services = useQuery({
    queryKey: ["major-incident-scope-services"],
    queryFn: async () => (await api.get<CatalogOption[]>("/services")).data,
    enabled: scopeOpen,
  });
  const environments = useQuery({
    queryKey: ["major-incident-scope-environments"],
    queryFn: async () => (await api.get<CatalogOption[]>("/environments")).data,
    enabled: scopeOpen,
  });
  const moduleQueries = useQueries({
    queries: selectedScopeProductIds.map((productId) => ({
      queryKey: ["major-incident-scope-modules", productId],
      queryFn: async () =>
        (await api.get<CatalogOption[]>(`/products/${productId}/modules`)).data,
      enabled: scopeOpen,
    })),
  });
  const moduleOptions = moduleQueries.flatMap((query) => query.data ?? []);
  const refresh = () =>
    queryClient.invalidateQueries({
      predicate: (query) =>
        String(query.queryKey[0]).startsWith("major-incident"),
    });
  const useIncidentMutation = (
    method: "patch" | "post" | "put",
    path: string,
    close?: () => void,
  ) =>
    useMutation({
      mutationFn: (payload: Record<string, unknown>) =>
        api[method](path, payload),
      onSuccess: async () => {
        close?.();
        setError("");
        await refresh();
      },
      onError: (reason) => setError(apiErrorMessage(reason)),
    });
  const edit = useIncidentMutation("patch", `/major-incidents/${incidentId}`, () =>
    setEditOpen(false),
  );
  const move = useIncidentMutation(
    "post",
    `/major-incidents/${incidentId}/transition`,
    () => setMoveOpen(false),
  );
  const publish = useIncidentMutation("post", `/major-incidents/${incidentId}/updates`);
  const linkTicket = useIncidentMutation(
    "post",
    `/major-incidents/${incidentId}/tickets`,
    () => setLinkOpen(false),
  );
  const linkProblem = useIncidentMutation(
    "post",
    `/major-incidents/${incidentId}/problem`,
    () => setProblemOpen(false),
  );
  const commitment = useIncidentMutation(
    "post",
    `/major-incidents/${incidentId}/problem-commitment`,
  );
  const replaceScopes = useIncidentMutation(
    "put",
    `/major-incidents/${incidentId}/scopes`,
    () => setScopeOpen(false),
  );
  if (incident.isLoading) return <CircularProgress />;
  if (incident.isError || !incident.data)
    return (
      <Alert severity="error">
        {t("serviceManagement.majorIncidents.workspace.loadFailed")}
      </Alert>
    );
  const row = incident.data;
  return (
    <Stack gap={2}>
      <Paper
        sx={{
          p: 3,
          borderLeft: 5,
          borderLeftColor:
            row.severity === "SEV1" ? "error.main" : "warning.main",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={1}
          alignItems={{ md: "center" }}
        >
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate("/major-incidents")}
          >
            {t("serviceManagement.majorIncidents.title")}
          </Button>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="overline">
              {t("serviceManagement.majorIncidents.workspace.title")}
            </Typography>
            <Typography variant="h4">
              <TechnicalText>{row.major_incident_number}</TechnicalText>
            </Typography>
          </Box>
          <Chip
            color={row.severity === "SEV1" ? "error" : "warning"}
            label={row.severity}
          />
          <Chip variant="outlined" label={label(row.status)} />
          {hasPermission("major_incident.command") && (
            <>
              <Button startIcon={<Edit />} onClick={() => setEditOpen(true)}>
                {t("serviceManagement.actions.edit")}
              </Button>
              {(transitions[row.status] ?? []).map((status) => (
                <Button
                  key={status}
                  variant="contained"
                  onClick={() => {
                    setTargetStatus(status);
                    setMoveOpen(true);
                  }}
                >
                  {label(status)}
                </Button>
              ))}
            </>
          )}
        </Stack>
      </Paper>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6">
          {t("serviceManagement.majorIncidents.workspace.currentSituation")}
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2,1fr)" },
            gap: 2,
            mt: 2,
          }}
        >
          <Detail
            title={t("serviceManagement.fields.businessImpact")}
            value={row.business_impact}
          />
          <Detail
            title={t("serviceManagement.fields.affectedUsers")}
            value={row.affected_users}
          />
          <Detail
            title={t("serviceManagement.fields.currentStatus")}
            value={row.current_status_summary}
          />
          <Detail
            title={t("serviceManagement.fields.nextUpdate")}
            value={
              row.next_update_at
                ? new Date(row.next_update_at).toLocaleString(i18n.language)
                : null
            }
          />
          <Detail
            title={t("serviceManagement.fields.resolutionSummary")}
            value={row.resolution_summary}
          />
          <Detail
            title={t("serviceManagement.fields.postIncidentReview")}
            value={row.post_incident_review}
          />
        </Box>
      </Paper>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "repeat(2,1fr)" },
          gap: 2,
        }}
      >
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6">
            {t("serviceManagement.majorIncidents.workspace.incidentUpdates")}
          </Typography>
          {updates.data?.map((item) => (
            <Box
              key={item.id}
              sx={{ py: 1, borderBottom: 1, borderColor: "divider" }}
            >
              <Chip size="small" label={label(item.update_type)} />
              <Typography sx={{ whiteSpace: "pre-wrap", mt: 0.5 }}>
                {item.client_message || item.internal_message}
              </Typography>
              <Typography variant="caption">
                {item.published_by_name} ·{" "}
                {new Date(item.published_at).toLocaleString()}
              </Typography>
            </Box>
          ))}
          {hasPermission("major_incident.publish_update") && (
            <Box
              component="form"
              sx={{ mt: 2 }}
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                const form = event.currentTarget;
                const data = new FormData(form);
                const type = String(data.get("update_type"));
                const message = String(data.get("message"));
                publish.mutate({
                  update_type: type,
                  internal_message: type === "CLIENT" ? null : message,
                  client_message: type === "CLIENT" ? message : null,
                });
                form.reset();
              }}
            >
              <Stack gap={1}>
                <TextField
                  select
                  name="update_type"
                  label={t(
                    "serviceManagement.majorIncidents.workspace.updateType",
                  )}
                  defaultValue="INTERNAL"
                >
                  <MenuItem value="INTERNAL">
                    {t("serviceManagement.majorIncidents.workspace.internal")}
                  </MenuItem>
                  <MenuItem value="CLIENT">
                    {t("serviceManagement.majorIncidents.workspace.clientSafe")}
                  </MenuItem>
                  <MenuItem value="RESTORATION">
                    {t(
                      "serviceManagement.majorIncidents.workspace.restoration",
                    )}
                  </MenuItem>
                </TextField>
                <TextField
                  name="message"
                  label={t(
                    "serviceManagement.majorIncidents.workspace.updateMessage",
                  )}
                  required
                  multiline
                  minRows={2}
                />
                <Button type="submit">
                  {t("serviceManagement.actions.publishUpdate")}
                </Button>
              </Stack>
            </Box>
          )}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row">
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("serviceManagement.majorIncidents.workspace.affectedTickets")}
            </Typography>
            {hasPermission("major_incident.link_ticket") && (
              <Button onClick={() => setLinkOpen(true)}>
                {t("serviceManagement.actions.linkTicket")}
              </Button>
            )}
          </Stack>
          {tickets.data?.map((item) => (
            <Button
              key={item.id}
              sx={{ display: "flex" }}
              onClick={() => navigate(`/tickets/${item.ticket_id}`)}
            >
              <TechnicalText>{item.ticket_number}</TechnicalText>&nbsp;·{" "}
              {item.subject} ({label(item.link_type)})
            </Button>
          ))}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row">
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("serviceManagement.majorIncidents.workspace.problemFollowUp")}
            </Typography>
            {hasPermission("major_incident.command") && (
              <Button onClick={() => setProblemOpen(true)}>
                {t("serviceManagement.actions.linkProblem")}
              </Button>
            )}
          </Stack>
          {problems.data?.map((item) => (
            <Button
              key={item.id}
              onClick={() => navigate(`/problems/${item.id}`)}
            >
              <TechnicalText>{item.problem_number}</TechnicalText>&nbsp;·{" "}
              {item.title}
            </Button>
          ))}
          {!problems.data?.length && (
            <Typography color="text.secondary">
              {t("serviceManagement.majorIncidents.workspace.noLinkedProblem")}
            </Typography>
          )}
          {hasPermission("major_incident.command") &&
            !problems.data?.length && (
              <Box
                component="form"
                sx={{ mt: 2 }}
                onSubmit={(event: FormEvent<HTMLFormElement>) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  commitment.mutate({
                    owner_user_id: Number(data.get("owner_user_id")),
                    due_at: String(data.get("due_at")),
                    version: row.version,
                  });
                }}
              >
                <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                  <TextField
                    name="owner_user_id"
                    label={t(
                      "serviceManagement.majorIncidents.workspace.problemOwner",
                    )}
                    select
                    required
                    defaultValue={row.problem_follow_up_owner_user_id ?? ""}
                    sx={{ minWidth: 220 }}
                  >
                    {assignees.data?.map((person) => (
                      <MenuItem key={person.id} value={person.id}>
                        {person.full_name} ({person.username})
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    name="due_at"
                    label={t(
                      "serviceManagement.majorIncidents.workspace.followUpDue",
                    )}
                    type="datetime-local"
                    required
                    defaultValue={dateInput(row.problem_follow_up_due_at)}
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <Button type="submit">
                    {t("serviceManagement.actions.commit")}
                  </Button>
                </Stack>
              </Box>
            )}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row">
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {t("serviceManagement.majorIncidents.workspace.affectedScope")}
            </Typography>
            {hasPermission("major_incident.command") && (
              <Button
                onClick={() => {
                  setSelectedScopeProductIds(scopes.data?.product_ids ?? []);
                  setSelectedScopeModuleIds(
                    scopes.data?.product_module_ids ?? [],
                  );
                  setScopeOpen(true);
                }}
              >
                {t("serviceManagement.actions.editScope")}
              </Button>
            )}
          </Stack>
          {scopes.data && (
            <Stack gap={0.5} sx={{ mt: 1 }}>
              <Typography>
                {t("serviceManagement.scope.clients")}:{" "}
                {scopes.data.client_ids.join(", ") || "—"}
              </Typography>
              <Typography>
                {t("serviceManagement.scope.products")}:{" "}
                {scopes.data.product_ids.join(", ") || "—"}
              </Typography>
              <Typography>
                {t("serviceManagement.scope.modules")}:{" "}
                {scopes.data.product_module_ids.join(", ") || "—"}
              </Typography>
              <Typography>
                {t("serviceManagement.scope.services")}:{" "}
                {scopes.data.service_ids.join(", ") || "—"}
              </Typography>
              <Typography>
                {t("serviceManagement.scope.environments")}:{" "}
                {scopes.data.environment_ids.join(", ") || "—"}
              </Typography>
            </Stack>
          )}
        </Paper>
      </Box>
      <Dialog
        open={editOpen}
        onClose={() => setEditOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            edit.mutate({
              severity: String(data.get("severity")),
              business_impact: String(data.get("business_impact")),
              affected_users: optional(data.get("affected_users")),
              current_status_summary: String(
                data.get("current_status_summary"),
              ),
              next_update_at: optional(data.get("next_update_at")),
              resolution_summary: optional(data.get("resolution_summary")),
              post_incident_review: optional(data.get("post_incident_review")),
              version: row.version,
            });
          }}
        >
          <DialogTitle>
            {t("serviceManagement.majorIncidents.workspace.editMajorIncident")}
          </DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              <TextField
                autoFocus
                select
                name="severity"
                label={t("serviceManagement.severity")}
                defaultValue={row.severity}
              >
                {["SEV1", "SEV2", "SEV3", "SEV4"].map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                name="business_impact"
                label={t("serviceManagement.fields.businessImpact")}
                defaultValue={row.business_impact}
                required
                multiline
              />
              <TextField
                name="affected_users"
                label={t("serviceManagement.fields.affectedUsers")}
                defaultValue={row.affected_users ?? ""}
              />
              <TextField
                name="current_status_summary"
                label={t("serviceManagement.fields.currentStatus")}
                defaultValue={row.current_status_summary}
                required
                multiline
              />
              <TextField
                name="next_update_at"
                label={t("serviceManagement.fields.nextUpdate")}
                type="datetime-local"
                defaultValue={dateInput(row.next_update_at)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                name="resolution_summary"
                label={t("serviceManagement.fields.resolutionSummary")}
                defaultValue={row.resolution_summary ?? ""}
                multiline
              />
              <TextField
                name="post_incident_review"
                label={t("serviceManagement.fields.postIncidentReview")}
                defaultValue={row.post_incident_review ?? ""}
                multiline
                minRows={3}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("serviceManagement.actions.save")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            move.mutate({
              status: targetStatus,
              reason: optional(new FormData(event.currentTarget).get("reason")),
              version: row.version,
            });
          }}
        >
          <DialogTitle>
            {t("serviceManagement.actions.moveTo", {
              status: label(targetStatus),
            })}
          </DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              name="reason"
              label={t("serviceManagement.fields.reason")}
              fullWidth
              multiline
              minRows={3}
              sx={{ mt: 1 }}
              required={targetStatus === "CANCELLED"}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setMoveOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("serviceManagement.actions.confirm")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={linkOpen}
        onClose={() => setLinkOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            linkTicket.mutate({
              ticket_id: Number(data.get("ticket_id")),
              link_type: String(data.get("link_type")),
              version: row.version,
            });
          }}
        >
          <DialogTitle>
            {t("serviceManagement.majorIncidents.workspace.linkAffectedTicket")}
          </DialogTitle>
          <DialogContent>
            <Stack gap={2} sx={{ pt: 1 }}>
              <TextField
                autoFocus
                select
                name="ticket_id"
                label={t(
                  "serviceManagement.majorIncidents.workspace.visibleOpenTicket",
                )}
                required
                defaultValue=""
              >
                {ticketOptions.data
                  ?.filter(
                    (item) =>
                      item.id !== row.primary_ticket_id &&
                      !tickets.data?.some(
                        (linked) => linked.ticket_id === item.id,
                      ),
                  )
                  .map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.ticket_number} · {item.subject}
                    </MenuItem>
                  ))}
              </TextField>
              <TextField
                select
                name="link_type"
                label={t("serviceManagement.relationships.relationship")}
                defaultValue="AFFECTED"
              >
                <MenuItem value="AFFECTED">
                  {t("serviceManagement.relationships.affected")}
                </MenuItem>
                <MenuItem value="DUPLICATE">
                  {t("serviceManagement.relationships.duplicate")}
                </MenuItem>
              </TextField>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setLinkOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("serviceManagement.actions.link")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={problemOpen}
        onClose={() => setProblemOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            linkProblem.mutate({
              problem_id: Number(
                new FormData(event.currentTarget).get("problem_id"),
              ),
              version: row.version,
            });
          }}
        >
          <DialogTitle>
            {t("serviceManagement.actions.linkProblem")}
          </DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              select
              name="problem_id"
              label={t(
                "serviceManagement.majorIncidents.workspace.visibleProblem",
              )}
              required
              defaultValue=""
              fullWidth
              sx={{ mt: 1 }}
            >
              {problemOptions.data
                ?.filter(
                  (item) =>
                    !problems.data?.some((linked) => linked.id === item.id),
                )
                .map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.problem_number} · {item.title}
                  </MenuItem>
                ))}
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setProblemOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("serviceManagement.actions.link")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
      <Dialog
        open={scopeOpen}
        onClose={() => setScopeOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            replaceScopes.mutate({
              client_ids: ids(data.get("client_ids")),
              product_ids: selectedScopeProductIds,
              product_module_ids: selectedScopeModuleIds.filter((moduleId) =>
                moduleOptions.some((module) => module.id === moduleId),
              ),
              service_ids: ids(data.get("service_ids")),
              environment_ids: ids(data.get("environment_ids")),
              version: row.version,
            });
          }}
        >
          <DialogTitle>
            {t("serviceManagement.majorIncidents.workspace.editAffectedScope")}
          </DialogTitle>
          <DialogContent>
            <Alert severity="info" sx={{ my: 1 }}>
              {t("serviceManagement.majorIncidents.workspace.scopeHelp")}
            </Alert>
            <Stack gap={2}>
              <TextField
                autoFocus
                select
                name="client_ids"
                label={t("serviceManagement.scope.clients")}
                defaultValue={scopes.data?.client_ids ?? []}
                slotProps={{ select: { multiple: true } }}
              >
                {clients.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>
              <Autocomplete
                multiple
                options={products.data ?? []}
                value={(products.data ?? []).filter((item) =>
                  selectedScopeProductIds.includes(item.id),
                )}
                getOptionLabel={(item) => item.name}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                onChange={(_, values) =>
                  setSelectedScopeProductIds(values.map((item) => item.id))
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label={t("serviceManagement.scope.products")}
                  />
                )}
              />
              <Autocomplete
                multiple
                options={moduleOptions}
                value={moduleOptions.filter((item) =>
                  selectedScopeModuleIds.includes(item.id),
                )}
                getOptionLabel={(item) => item.name}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                onChange={(_, values) =>
                  setSelectedScopeModuleIds(values.map((item) => item.id))
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label={t("serviceManagement.scope.productModules")}
                    helperText={
                      selectedScopeProductIds.length
                        ? "Modules from the selected products"
                        : "Select products first"
                    }
                  />
                )}
              />
              <TextField
                select
                name="service_ids"
                label={t("serviceManagement.scope.services")}
                defaultValue={scopes.data?.service_ids ?? []}
                slotProps={{ select: { multiple: true } }}
              >
                {services.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                name="environment_ids"
                label={t("serviceManagement.scope.environments")}
                defaultValue={scopes.data?.environment_ids ?? []}
                slotProps={{ select: { multiple: true } }}
              >
                {environments.data?.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.name}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setScopeOpen(false)}>
              {t("serviceManagement.actions.cancel")}
            </Button>
            <Button type="submit" variant="contained">
              {t("serviceManagement.majorIncidents.workspace.replaceScope")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
