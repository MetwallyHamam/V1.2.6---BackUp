import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Rating,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useParams } from "react-router-dom";
import { api } from "../api/client";
import { TechnicalText } from "../components/TechnicalText";
import { getLocalizedName } from "../i18n/localizedMasterData";

type Ticket = {
  id: number;
  ticket_number: string;
  service_id?: number;
  entitlement_status?: string;
  subject: string;
  description: string;
  priority: string;
  version: number;
  resolution_summary?: string;
  sla_first_response_target_minutes?: number;
  sla_first_response_actual_minutes?: number;
  sla_resolution_target_minutes?: number;
  sla_actual_business_minutes?: number;
  sla_saved_minutes?: number;
};
type Attachment = {
  id: number;
  original_filename: string;
  size_bytes: number;
  created_at: string;
};
type TicketContext = {
  contract_id?: number;
  product_id?: number;
  product_module_id?: number;
};
type ContractEvidence = { id: number; contract_number: string; name: string };
type TimelineEvent = {
  id: string;
  title: string;
  description?: string;
  actor_name?: string;
  created_at: string;
};
type PortalCatalog = {
  products: Array<{ id: number; name: string; name_ar?: string | null }>;
  services: Array<{ id: number; name: string; name_ar?: string | null }>;
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
};
type Satisfaction = {
  state: "AVAILABLE" | "SUBMITTED" | "UNAVAILABLE";
  ticket_rating?: number;
  service_rating?: number;
  engineer_rating?: number;
  comments?: string | null;
  submitted_at?: string;
  source?: string;
};
type ServiceAdvisories = {
  major_incidents: Array<{
    id: number;
    major_incident_number: string;
    severity: string;
    status: string;
    updates: Array<{ id: number; message: string; published_at: string }>;
  }>;
  knowledge: Array<{
    problem_number: string;
    article_id: number;
    link_type: string;
    title: string;
    summary: string;
    body: string;
    updated_at: string;
  }>;
};
export function PortalTicketDetailPage() {
  const commentOperationKey = useRef<string | null>(null);
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "ar" ? "ar" : "en";
  const slaDuration = (minutes?: number) =>
    minutes == null
      ? t("portalTicketDetail.notAvailable")
      : minutes < 60
        ? t("time.minutes", { count: minutes })
        : t("time.hours", { count: Math.round(minutes / 6) / 10 });
  const { id } = useParams();
  const queryClient = useQueryClient();
  const location = useLocation();
  const [attachmentError, setAttachmentError] = useState(
    location.state?.attachmentUploadFailed
      ? t("portalTicketDetail.initialAttachmentError")
      : "",
  );
  const [ticketRating, setTicketRating] = useState(0),
    [serviceRating, setServiceRating] = useState(0),
    [engineerRating, setEngineerRating] = useState(0),
    [ratingComments, setRatingComments] = useState("");
  const ticket = useQuery({
    queryKey: ["portal-ticket", id],
    queryFn: async () =>
      (await api.get<Ticket & TicketContext>(`/portal/tickets/${id}`)).data,
  });
  const catalog = useQuery({
    queryKey: ["portal-contract-catalog"],
    queryFn: async () => (await api.get<PortalCatalog>("/portal/catalog")).data,
  });
  const timeline = useQuery({
    queryKey: ["portal-timeline", id],
    queryFn: async () =>
      (await api.get<TimelineEvent[]>(`/tickets/${id}/timeline`)).data,
  });
  const attachments = useQuery({
    queryKey: ["portal-attachments", id],
    queryFn: async () =>
      (await api.get<Attachment[]>(`/tickets/${id}/attachments`)).data,
  });
  const slaClocks = useQuery({
    queryKey: ["portal-ticket-sla", id],
    queryFn: async () => (await api.get<SlaClock[]>(`/tickets/${id}/sla`)).data,
  });
  const selectedContract = useQuery({
    queryKey: ["portal-ticket-contract", ticket.data?.contract_id],
    enabled: Boolean(ticket.data?.contract_id),
    queryFn: async () =>
      (
        await api.get<ContractEvidence>(
          `/portal/contracts/${ticket.data?.contract_id}`,
        )
      ).data,
  });
  const satisfaction = useQuery({
    queryKey: ["portal-ticket-satisfaction", id],
    enabled: Boolean(ticket.data),
    queryFn: async () =>
      (await api.get<Satisfaction>(`/portal/tickets/${id}/satisfaction`)).data,
  });
  const advisories = useQuery({
    queryKey: ["portal-ticket-service-advisories", id],
    enabled: Boolean(ticket.data),
    queryFn: async () =>
      (
        await api.get<ServiceAdvisories>(
          `/portal/tickets/${id}/service-advisories`,
        )
      ).data,
  });
  const submitRating = useMutation({
    mutationFn: async () =>
      api.post(`/portal/tickets/${id}/satisfaction`, {
        ticket_rating: ticketRating,
        service_rating: serviceRating,
        engineer_rating: engineerRating,
        comments: ratingComments.trim() || null,
      }),
    onSuccess: async () => {
      await satisfaction.refetch();
    },
  });
  async function uploadAttachment(file: File) {
    setAttachmentError("");
    const body = new FormData();
    body.append("file", file);
    try {
      await api.post(`/tickets/${id}/attachments`, body);
      await queryClient.invalidateQueries({
        queryKey: ["portal-attachments", id],
      });
      await queryClient.invalidateQueries({
        queryKey: ["portal-timeline", id],
      });
    } catch {
      setAttachmentError(t("portalTicketDetail.uploadFailed"));
    }
  }
  async function downloadAttachment(item: Attachment) {
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
      setAttachmentError(t("portalTicketDetail.downloadFailed"));
    }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = String(new FormData(form).get("body") ?? "");
    await api.post(`/portal/tickets/${id}/comments`, {
      body,
      is_internal: false,
      operation_key: (commentOperationKey.current ??= crypto.randomUUID()),
    });
    commentOperationKey.current = null;
    form.reset();
    await queryClient.invalidateQueries({ queryKey: ["portal-timeline", id] });
  }
  if (ticket.isLoading)
    return <CircularProgress aria-label={t("common.loading")} />;
  if (ticket.isError || !ticket.data)
    return <Alert severity="error">{t("portalTicketDetail.loadFailed")}</Alert>;
  const service = catalog.data?.services.find(
    (item) => item.id === ticket.data.service_id,
  );
  const serviceName = ticket.data.service_id
    ? service
      ? getLocalizedName(service, language)
      : t("portalTicketDetail.serviceNumber", { id: ticket.data.service_id })
    : t("portalTicketDetail.noService");
  const serviceHasContractSla =
    ticket.data.entitlement_status === "COVERED" &&
    (ticket.data.sla_first_response_target_minutes != null ||
      ticket.data.sla_resolution_target_minutes != null);
  const product = catalog.data?.products.find(
    (item) => item.id === ticket.data?.product_id,
  );
  const productName = ticket.data.product_id
    ? product
      ? getLocalizedName(product, language)
      : t("portalTicketDetail.productNumber", { id: ticket.data.product_id })
    : t("portalTicketDetail.noProduct");
  const agreementSnapshot = serviceHasContractSla
    ? slaClocks.data?.[0]
    : undefined;
  return (
    <Paper sx={{ p: 3, maxWidth: 900 }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Typography variant="h4">
          <TechnicalText>{ticket.data.ticket_number}</TechnicalText>
        </Typography>
        <Chip
          label={t(`priority.${ticket.data.priority}`, {
            defaultValue: ticket.data.priority,
          })}
        />
      </Stack>
      <Typography variant="h5" sx={{ my: 2 }}>
        {ticket.data.subject}
      </Typography>
      <Typography sx={{ whiteSpace: "pre-wrap" }}>
        {ticket.data.description}
      </Typography>
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          my: 2,
          borderColor: serviceHasContractSla ? "success.main" : "divider",
        }}
      >
        <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
          <Typography variant="h6">
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
              {ticket.data.sla_first_response_actual_minutes != null && (
                <>
                  {" "}
                  · {t("portalTicketDetail.actual")}:{" "}
                  <b>
                    {slaDuration(ticket.data.sla_first_response_actual_minutes)}
                  </b>
                </>
              )}
            </Typography>
            <Typography>
              {t("portalTicketDetail.resolutionTarget")}:{" "}
              <b>{slaDuration(ticket.data.sla_resolution_target_minutes)}</b>
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
                fontWeight={700}
              >
                {ticket.data.sla_saved_minutes >= 0
                  ? t("portalTickets.saved", {
                      value: slaDuration(ticket.data.sla_saved_minutes),
                    })
                  : t("portalTickets.overrun", {
                      value: slaDuration(
                        Math.abs(ticket.data.sla_saved_minutes),
                      ),
                    })}
              </Typography>
            )}
            <Typography variant="caption" color="text.secondary">
              {t("portalTicketDetail.slaNotice")}
            </Typography>
          </>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {t(
              ticket.data.service_id
                ? "portalTicketDetail.noSlaTarget"
                : "portalTicketDetail.noContractedService",
            )}
          </Typography>
        )}
      </Paper>
      {agreementSnapshot && (
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          sx={{ mb: 2 }}
        >
          {t("portalTicketDetail.agreementEvidence", {
            match: (
              agreementSnapshot.match_reason ?? "NO_MATCH_EVIDENCE"
            ).replaceAll("_", " "),
            contract:
              agreementSnapshot.contract_id ?? t("portalTicketDetail.default"),
            policy: agreementSnapshot.policy_id,
            version: agreementSnapshot.policy_version,
            target:
              agreementSnapshot.target_id ?? t("portalTicketDetail.legacy"),
            calendar:
              agreementSnapshot.calendar_id ?? t("portalTicketDetail.legacy"),
            calculation: agreementSnapshot.calculation_version,
          })}
        </Typography>
      )}
      <Alert severity="info" sx={{ mb: 2 }}>
        {t("portalTicketDetail.product")}: <b>{productName}</b> ·{" "}
        {t("portalTicketDetail.governingContract")}:{" "}
        <b>
          {selectedContract.data
            ? `${selectedContract.data.contract_number} — ${selectedContract.data.name}`
            : ticket.data.contract_id
              ? `#${ticket.data.contract_id}`
              : t("portalTicketDetail.noContract")}
        </b>
      </Alert>
      {ticket.data.resolution_summary && (
        <Alert severity="success" sx={{ my: 3 }}>
          {ticket.data.resolution_summary}
        </Alert>
      )}
      {!!advisories.data?.major_incidents.length && (
        <Paper
          variant="outlined"
          sx={{ p: 2, my: 3, borderColor: "error.main" }}
        >
          <Typography variant="h6">
            {t("serviceManagement.serviceIncidentUpdates")}
          </Typography>
          <Typography color="text.secondary" mb={1}>
            {t("serviceManagement.clientApprovedCommunications")}
          </Typography>
          {advisories.data.major_incidents.map((incident) => (
            <Box key={incident.id} sx={{ mt: 2 }}>
              <Stack direction="row" gap={1} alignItems="center">
                <TechnicalText>{incident.major_incident_number}</TechnicalText>
                <Chip
                  size="small"
                  color={incident.severity === "SEV1" ? "error" : "warning"}
                  label={incident.severity}
                />
                <Chip
                  size="small"
                  variant="outlined"
                  label={incident.status.replaceAll("_", " ")}
                />
              </Stack>
              {incident.updates.map((update) => (
                <Box
                  key={update.id}
                  sx={{ mt: 1, p: 1.5, bgcolor: "action.hover" }}
                >
                  <Typography sx={{ whiteSpace: "pre-wrap" }}>
                    {update.message}
                  </Typography>
                  <Typography variant="caption">
                    {new Date(update.published_at).toLocaleString(
                      i18n.language,
                    )}
                  </Typography>
                </Box>
              ))}
            </Box>
          ))}
        </Paper>
      )}
      {!!advisories.data?.knowledge.length && (
        <Paper
          variant="outlined"
          sx={{ p: 2, my: 3, borderColor: "success.main" }}
        >
          <Typography variant="h6">
            {t("serviceManagement.approvedGuidance")}
          </Typography>
          <Typography color="text.secondary" mb={1}>
            {t("serviceManagement.approvedGuidanceHelp")}
          </Typography>
          {advisories.data.knowledge.map((item) => (
            <Box
              key={`${item.problem_number}-${item.article_id}`}
              sx={{ py: 1.5, borderBottom: 1, borderColor: "divider" }}
            >
              <Stack direction="row" gap={1} alignItems="center">
                <Chip
                  size="small"
                  color="success"
                  variant="outlined"
                  label={item.link_type.replaceAll("_", " ")}
                />
                <Typography fontWeight={700}>{item.title}</Typography>
              </Stack>
              {item.summary && (
                <Typography color="text.secondary">{item.summary}</Typography>
              )}
              <Typography sx={{ whiteSpace: "pre-wrap", mt: 1 }}>
                {item.body}
              </Typography>
              <Typography variant="caption">
                <TechnicalText>{item.problem_number}</TechnicalText> ·{" "}
                {new Date(item.updated_at).toLocaleString(i18n.language)}
              </Typography>
            </Box>
          ))}
        </Paper>
      )}
      {satisfaction.data?.state === "AVAILABLE" && (
        <Paper variant="outlined" sx={{ p: 2, my: 3 }}>
          <Typography variant="h6">
            {t("portalTicketDetail.rateTitle")}
          </Typography>
          <Typography color="text.secondary" mb={2}>
            {t("portalTicketDetail.rateHelp")}
          </Typography>
          <Stack spacing={2}>
            <Box>
              <Typography fontWeight={700}>
                {t("portalTicketDetail.ticketRating")}
              </Typography>
              <Rating
                size="large"
                value={ticketRating}
                onChange={(_, value) => setTicketRating(value ?? 0)}
              />
            </Box>
            <Box>
              <Typography fontWeight={700}>
                {t("satisfaction.service")}
              </Typography>
              <Rating
                size="large"
                value={serviceRating}
                onChange={(_, value) => setServiceRating(value ?? 0)}
              />
            </Box>
            <Box>
              <Typography fontWeight={700}>
                {t("satisfaction.engineer")}
              </Typography>
              <Rating
                size="large"
                value={engineerRating}
                onChange={(_, value) => setEngineerRating(value ?? 0)}
              />
            </Box>
            <TextField
              label={t("satisfaction.comments")}
              multiline
              rows={3}
              value={ratingComments}
              onChange={(event) => setRatingComments(event.target.value)}
              inputProps={{ maxLength: 2000 }}
            />
            {submitRating.isError && (
              <Alert severity="error">{t("satisfaction.failed")}</Alert>
            )}
            <Button
              variant="contained"
              disabled={
                ticketRating < 1 ||
                serviceRating < 1 ||
                engineerRating < 1 ||
                submitRating.isPending
              }
              onClick={() => submitRating.mutate()}
            >
              {submitRating.isPending
                ? t("satisfaction.submitting")
                : t("satisfaction.submit")}
            </Button>
          </Stack>
        </Paper>
      )}
      {satisfaction.data?.state === "SUBMITTED" && (
        <Paper variant="outlined" sx={{ p: 2, my: 3 }}>
          <Alert severity="success" sx={{ mb: 2 }}>
            {t("portalTicketDetail.ratingSaved")}
          </Alert>
          <Stack direction={{ xs: "column", sm: "row" }} gap={3}>
            <Box>
              <Typography>{t("portalTicketDetail.ticketRating")}</Typography>
              <Rating readOnly value={satisfaction.data.ticket_rating ?? 0} />
            </Box>
            <Box>
              <Typography>{t("satisfaction.service")}</Typography>
              <Rating readOnly value={satisfaction.data.service_rating ?? 0} />
            </Box>
            <Box>
              <Typography>{t("satisfaction.engineer")}</Typography>
              <Rating readOnly value={satisfaction.data.engineer_rating ?? 0} />
            </Box>
          </Stack>
          {satisfaction.data.comments && (
            <Typography sx={{ mt: 2, whiteSpace: "pre-wrap" }}>
              {satisfaction.data.comments}
            </Typography>
          )}
        </Paper>
      )}
      <Typography variant="h6" sx={{ mt: 4 }}>
        {t("portalTicketDetail.attachments")}
      </Typography>
      {attachmentError && (
        <Alert severity="error" sx={{ my: 1 }}>
          {attachmentError}
        </Alert>
      )}
      {attachments.data?.map((item) => (
        <Stack
          key={item.id}
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{ py: 1 }}
        >
          <Typography sx={{ flexGrow: 1 }}>
            <TechnicalText>
              {item.original_filename} ({(item.size_bytes / 1024).toFixed(1)}{" "}
              KB)
            </TechnicalText>
          </Typography>
          <Button size="small" onClick={() => void downloadAttachment(item)}>
            {t("portalTicketDetail.download")}
          </Button>
        </Stack>
      ))}
      <Button component="label" variant="outlined" sx={{ mt: 1 }}>
        {t("portalTicketDetail.addAttachment")}
        <input
          hidden
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.txt,.log,.csv,.docx,.xlsx"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void uploadAttachment(file);
            event.target.value = "";
          }}
        />
      </Button>
      <Typography variant="h6" sx={{ mt: 4 }}>
        {t("portalTicketDetail.updates")}
      </Typography>
      {timeline.data?.map((event) => (
        <Box key={event.id} sx={{ bgcolor: "action.hover", p: 2, my: 1 }}>
          <Typography fontWeight={600}>{event.title}</Typography>
          {event.description && <Typography>{event.description}</Typography>}
          <Typography variant="caption">
            {event.actor_name ?? t("portalTicketDetail.system")} ·{" "}
            {new Date(event.created_at).toLocaleString(i18n.language)}
          </Typography>
        </Box>
      ))}
      <Box component="form" onSubmit={submit} sx={{ mt: 2 }}>
        <TextField
          name="body"
          label={t("portalTicketDetail.addReply")}
          required
          fullWidth
          multiline
          rows={3}
        />
        <Button type="submit" variant="contained" sx={{ mt: 1 }}>
          {t("portalTicketDetail.sendReply")}
        </Button>
      </Box>
    </Paper>
  );
}
