import { LockOutlined } from "@mui/icons-material";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ReactNode, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Capability = {
  permission: string;
  capability: string;
  module: string;
  resource: string;
};
type AccessRequest = {
  id: number;
  permission_code: string;
  status: string;
  resource: string;
};
type GrantImpact = {
  profile_id: number;
  profile_name: string;
  affected_user_count: number;
  capability: string;
  eligible: boolean;
  already_assigned: boolean;
};

export function AccessRequired({
  capability,
  children,
  compact = false,
  dialogOnly = false,
  openSignal = 0,
}: {
  capability: Capability;
  children?: ReactNode;
  compact?: boolean;
  dialogOnly?: boolean;
  openSignal?: number;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "ar" ? "ar-EG" : "en-US";
  const [open, setOpen] = useState(false);
  const [justification, setJustification] = useState("");
  const [message, setMessage] = useState("");
  const [approverLogin, setApproverLogin] = useState("");
  const [approverPassword, setApproverPassword] = useState("");
  const { refreshPermissions } = useAuth();
  const refreshed = useRef(false);
  const requestable = Boolean(
    capability.permission && capability.permission !== "unknown",
  );
  const requests = useQuery({
    queryKey: ["access-requests"],
    queryFn: async () =>
      (await api.get<AccessRequest[]>("/access-requests")).data,
    refetchInterval: 30_000,
  });
  const impact = useQuery({
    queryKey: ["access-grant-impact", capability.permission],
    queryFn: async () =>
      (
        await api.get<GrantImpact>("/access-requests/grant-impact", {
          params: { permission_code: capability.permission },
        })
      ).data,
    enabled: open && requestable,
  });
  const pending = requests.data?.find(
    (row) =>
      row.permission_code === capability.permission &&
      row.resource === capability.resource &&
      row.status === "PENDING",
  );
  const approved = requests.data?.some(
    (row) =>
      row.permission_code === capability.permission &&
      row.resource === capability.resource &&
      row.status === "APPROVED",
  );
  useEffect(() => {
    if (openSignal) setOpen(true);
  }, [openSignal]);
  useEffect(() => {
    if (approved && !refreshed.current) {
      refreshed.current = true;
      setMessage(t("accessRequired.approved"));
      void refreshPermissions();
    }
  }, [approved, refreshPermissions, t]);
  const submit = useMutation({
    mutationFn: async () =>
      (
        await api.post("/access-requests", {
          permission_code: capability.permission,
          resource: capability.resource,
          return_path: `${location.pathname}${location.search}${location.hash}`,
          justification: justification.trim(),
        })
      ).data,
    onSuccess: () => {
      setMessage(t("accessRequired.pendingReview"));
      void requests.refetch();
    },
    onError: (error) => setMessage(apiErrorMessage(error)),
  });
  const grant = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ profile_name: string; affected_user_count: number }>(
          "/access-requests/direct-profile-grant",
          {
            permission_code: capability.permission,
            resource: capability.resource,
            return_path: `${location.pathname}${location.search}${location.hash}`,
            reason: justification.trim(),
            approver_login: approverLogin.trim(),
            approver_password: approverPassword,
          },
        )
      ).data,
    onSuccess: async (result) => {
      setMessage(
        t("accessRequired.granted", {
          profile: result.profile_name,
          count: result.affected_user_count.toLocaleString(locale),
        }),
      );
      setApproverPassword("");
      await requests.refetch();
      await refreshPermissions();
    },
    onError: (error) => setMessage(apiErrorMessage(error)),
  });
  return (
    <>
      {!dialogOnly &&
        (compact ? (
          <IconButton
            aria-label={t("accessRequired.aria", {
              capability: capability.capability,
            })}
            onClick={() => setOpen(true)}
          >
            <LockOutlined />
          </IconButton>
        ) : (
          <Paper variant="outlined" sx={{ p: 4, textAlign: "center" }}>
            <Stack alignItems="center" gap={1.5}>
              <LockOutlined color="action" fontSize="large" />
              <Typography variant="h5">{t("accessRequired.title")}</Typography>
              <Typography color="text.secondary">
                {t("accessRequired.need", {
                  capability: capability.capability,
                })}
              </Typography>
              <Button
                variant="outlined"
                startIcon={<LockOutlined />}
                onClick={() => setOpen(true)}
              >
                {t("accessRequired.options")}
              </Button>
              {children}
            </Stack>
          </Paper>
        ))}
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="sm"
        aria-labelledby="access-required-title"
      >
        <DialogTitle id="access-required-title">
          {t("accessRequired.title")}
        </DialogTitle>
        <DialogContent>
          <Typography>
            <strong>{capability.capability}</strong>
          </Typography>
          <Typography color="text.secondary">{capability.module}</Typography>
          {!requestable ? (
            <Alert severity="warning" sx={{ mt: 2 }}>
              {t("accessRequired.unmapped")}
            </Alert>
          ) : (
            <>
              {pending && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  {t("accessRequired.alreadyPending")}
                </Alert>
              )}
              <TextField
                autoFocus
                required
                fullWidth
                multiline
                rows={3}
                margin="normal"
                label={t("accessRequired.justification")}
                value={justification}
                onChange={(event) => setJustification(event.target.value)}
                helperText={t("accessRequired.justificationHelp")}
              />
              {impact.data && (
                <Alert
                  severity={impact.data.eligible ? "warning" : "error"}
                  sx={{ mt: 2 }}
                >
                  {t("accessRequired.impact", {
                    profile: impact.data.profile_name,
                    count:
                      impact.data.affected_user_count.toLocaleString(locale),
                  })}
                  {!impact.data.eligible ? t("accessRequired.ineligible") : ""}
                </Alert>
              )}
              <Typography fontWeight={700} mt={2}>
                {t("accessRequired.immediate")}
              </Typography>
              <TextField
                required
                fullWidth
                margin="dense"
                label={t("accessRequired.approverLogin")}
                autoComplete="username"
                value={approverLogin}
                onChange={(event) => setApproverLogin(event.target.value)}
                inputProps={{ dir: "ltr" }}
              />
              <TextField
                required
                fullWidth
                margin="dense"
                label={t("accessRequired.approverPassword")}
                type="password"
                autoComplete="current-password"
                value={approverPassword}
                onChange={(event) => setApproverPassword(event.target.value)}
                helperText={t("accessRequired.credentialsHelp")}
                inputProps={{ dir: "ltr" }}
              />
              {message && (
                <Alert
                  severity={
                    submit.isError || grant.isError ? "error" : "success"
                  }
                  sx={{ mt: 2 }}
                >
                  {message}
                </Alert>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>
            {t("accessRequired.close")}
          </Button>
          {requestable && !pending && (
            <Button
              variant="outlined"
              disabled={
                justification.trim().length < 10 ||
                submit.isPending ||
                grant.isPending
              }
              onClick={() => submit.mutate()}
            >
              {t("accessRequired.send")}
            </Button>
          )}
          {requestable && (
            <Button
              variant="contained"
              disabled={
                justification.trim().length < 10 ||
                approverLogin.trim().length < 2 ||
                approverPassword.length < 8 ||
                grant.isPending ||
                submit.isPending ||
                impact.data?.eligible === false
              }
              onClick={() => grant.mutate()}
            >
              {t("accessRequired.grant")}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </>
  );
}
