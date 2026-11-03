import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Send } from "@mui/icons-material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useTranslation } from "react-i18next";
import { copyText } from "../utils/clipboard";

type Channel = "COPY" | "WHATSAPP" | "EMAIL";
type ComplaintOption = {
  id: number;
  number: string;
  status: string;
  channels: Record<Channel, boolean>;
};
type Action = {
  code: "LIVE_TRACKING" | "SATISFACTION" | "COMPLAINT_TRACKING";
  label: string;
  eligible: boolean;
  reason?: string;
  channels?: Partial<Record<Channel, boolean>>;
  whatsapp_recipient?: string;
  complaints?: ComplaintOption[];
};
type Manifest = { ticket_id: number; ticket_number: string; actions: Action[] };
type Delivery = {
  channel?: Channel;
  recipient?: string;
  message: string;
  delivery_status?: string;
  copied?: boolean;
};

const whatsapp = (phone: string, message: string) => {
  let digits = phone.replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (!digits.startsWith("20"))
    digits = digits.startsWith("0") ? `20${digits.slice(1)}` : `20${digits}`;
  window.open(
    `https://wa.me/${digits}?text=${encodeURIComponent(message)}`,
    "_blank",
    "noopener,noreferrer",
  );
};

export function TicketSendActionsButton({
  ticketId,
  size = "small",
}: {
  ticketId: number;
  size?: "small" | "medium";
}) {
  const { t } = useTranslation(),
    { hasPermission } = useAuth(),
    [open, setOpen] = useState(false);
  if (
    ![
      "ticket.live_update.send",
      "ticket.satisfaction.send",
      "complaint.tracking.send",
    ].some(hasPermission)
  )
    return null;
  return (
    <>
      <Button
        size={size}
        variant="outlined"
        startIcon={<Send />}
        onClick={() => setOpen(true)}
      >
        {t("sendActions.button")}
      </Button>
      <TicketSendActionsDialog
        ticketId={ticketId}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}

export function TicketSendActionsDialog({
  ticketId,
  open,
  onClose,
  contactId,
}: {
  ticketId: number | null;
  open: boolean;
  onClose: () => void;
  contactId?: number | null;
}) {
  const { t } = useTranslation(),
    [actionCode, setActionCode] = useState(""),
    [complaintId, setComplaintId] = useState(""),
    [message, setMessage] = useState(""),
    [preparedMessage, setPreparedMessage] = useState(""),
    [error, setError] = useState("");
  const manifest = useQuery({
    queryKey: ["ticket-send-actions", ticketId, contactId],
    queryFn: async () =>
      (
        await api.get<Manifest>(`/tickets/${ticketId}/send-actions`, {
          params: { contact_id: contactId || undefined },
        })
      ).data,
    enabled: open && ticketId !== null,
  });
  const action = manifest.data?.actions.find((x) => x.code === actionCode),
    complaint = action?.complaints?.find((x) => x.id === Number(complaintId));
  const channels = useMemo(
    () =>
      Object.entries(complaint?.channels ?? action?.channels ?? {})
        .filter(([, enabled]) => enabled)
        .map(([channel]) => channel as Channel),
    [action, complaint],
  );
  useEffect(() => {
    if (!open) {
      setActionCode("");
      setComplaintId("");
      setMessage("");
      setPreparedMessage("");
      setError("");
    }
  }, [open]);
  const send = useMutation({
    mutationFn: async (channel: Channel) => {
      if (!ticketId || !action) return;
      if (action.code === "LIVE_TRACKING") {
        const result = (
          await api.post<Delivery>(`/tickets/${ticketId}/live-update-link`, {
            channel,
            contact_id: contactId || null,
          })
        ).data;
        if (channel === "COPY") result.copied = await copyText(result.message);
        else if (channel === "WHATSAPP" && result.recipient)
          whatsapp(result.recipient, result.message);
        return result;
      }
      if (action.code === "SATISFACTION") {
        const result = (
          await api.post<Delivery>(
            `/tickets/${ticketId}/satisfaction-delivery`,
            { channel, contact_id: contactId || null },
          )
        ).data;
        if (channel === "COPY") result.copied = await copyText(result.message);
        else if (channel === "WHATSAPP" && result.recipient)
          whatsapp(result.recipient, result.message);
        return result;
      }
      const result = (
        await api.post<Delivery>(
          `/complaints/${complaintId}/tracking-delivery`,
          { channel },
        )
      ).data;
      if (channel === "WHATSAPP" && result.recipient)
        whatsapp(result.recipient, result.message);
      return result;
    },
    onSuccess: (result, channel) => {
      if (!result) return;
      setError("");
      setPreparedMessage(channel === "COPY" ? result.message : "");
      setMessage(
        channel === "COPY"
          ? result.copied
            ? t("sendActions.copied")
            : t("sendActions.copyManually")
          : result.delivery_status === "QUEUED" || channel === "EMAIL"
            ? t("sendActions.emailQueued")
            : t("sendActions.whatsappReady"),
      );
    },
    onError: (e) => {
      setMessage("");
      setError(apiErrorMessage(e, t("sendActions.failed")));
    },
  });
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>
        {t("sendActions.title")}
        {manifest.data ? ` · ${manifest.data.ticket_number}` : ""}
      </DialogTitle>
      <DialogContent>
        {manifest.isError && (
          <Alert severity="error">{t("sendActions.eligibilityFailed")}</Alert>
        )}
        <Stack gap={1.5} mt={1}>
          {manifest.data?.actions.map((item) => (
            <Button
              key={item.code}
              variant={actionCode === item.code ? "contained" : "outlined"}
              disabled={!item.eligible}
              onClick={() => {
                setActionCode(item.code);
                setComplaintId(
                  item.complaints?.[0] ? String(item.complaints[0].id) : "",
                );
                setMessage("");
                setPreparedMessage("");
                setError("");
              }}
              sx={{ justifyContent: "flex-start" }}
            >
              {item.label}
              {!item.eligible && item.reason ? ` — ${item.reason}` : ""}
            </Button>
          ))}
        </Stack>
        {manifest.data && !manifest.data.actions.length && (
          <Alert severity="info">{t("sendActions.noPermission")}</Alert>
        )}
        {action?.complaints && action.complaints.length > 1 && (
          <TextField
            select
            fullWidth
            margin="normal"
            label={t("sendActions.linkedComplaint")}
            value={complaintId}
            onChange={(e) => setComplaintId(e.target.value)}
          >
            {action.complaints.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.number} — {item.status.replaceAll("_", " ")}
              </MenuItem>
            ))}
          </TextField>
        )}
        {action && action.eligible && !channels.length && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            {t("sendActions.noChannel")}
          </Alert>
        )}
        {action && channels.length > 0 && (
          <>
            <Typography fontWeight={700} mt={2}>
              {t("sendActions.deliveryChannel")}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1} mt={1}>
              {channels.map((channel) => (
                <Button
                  key={channel}
                  variant="contained"
                  disabled={send.isPending}
                  onClick={() => send.mutate(channel)}
                >
                  {channel === "COPY"
                    ? t("sendActions.copy")
                    : channel === "WHATSAPP"
                      ? "WhatsApp"
                      : "Email"}
                </Button>
              ))}
            </Stack>
          </>
        )}
        {message && (
          <Alert severity="success" sx={{ mt: 2 }}>
            {message}
          </Alert>
        )}
        {preparedMessage && (
          <TextField
            fullWidth
            multiline
            minRows={5}
            margin="normal"
            label={t("sendActions.preparedMessage")}
            value={preparedMessage}
            slotProps={{ input: { readOnly: true } }}
          />
        )}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("sendActions.close")}</Button>
      </DialogActions>
    </Dialog>
  );
}
