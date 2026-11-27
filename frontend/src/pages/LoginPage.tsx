import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowForwardRounded,
  LockOutlined,
  PersonOutlineRounded,
  VerifiedUserOutlined,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Divider,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { keyframes } from "@mui/material/styles";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { preferredWorkspace } from "../auth/projectWorkspaceAccess";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { z } from "zod";
import { useAuth } from "../auth/AuthContext";
import { consumeReturnPath, consumeSessionEndReason } from "../api/client";

type Form = { login: string; password: string };

type LoginNavigationState = {
  manualLogout?: boolean;
  from?: { pathname?: string; search?: string; hash?: string };
};

const orbitCounterClockwise = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(-360deg); }
`;

const orbitClockwise = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

const backgroundDrift = keyframes`
  0% { background-position: 0 0, 0 0, 0 0, 0 0, 0 0; }
  50% { background-position: 26px 18px, -20px 26px, 34px -20px, -30px 24px, 0 0; }
  100% { background-position: 52px 52px, -52px 52px, 0 0, 0 0, 0 0; }
`;

const ambientFloat = keyframes`
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); opacity: .72; }
  50% { transform: translate3d(42px, -34px, 0) scale(1.12); opacity: 1; }
`;

const ambientPulse = keyframes`
  0%, 100% { transform: translate3d(0, 0, 0) scale(.94); opacity: .48; }
  50% { transform: translate3d(-38px, 28px, 0) scale(1.1); opacity: .82; }
`;

export function loginDestination(
  user: { require_password_change: boolean; default_page: string; user_type?: "EMPLOYEE" | "CLIENT_PORTAL" },
  state: LoginNavigationState | null,
  savedReturnPath: string | null,
  preferredPath?: string,
) {
  if (user.require_password_change) return "/change-password";
  if (user.user_type === "CLIENT_PORTAL") return "/portal";
  const landingPages: Record<string, string> = {
    home: "/home",
    "my-workspace": "/my-workspace",
    dashboard: "/dashboard",
    "top-management": "/management-dashboards",
    "ticket-create": "/tickets/create",
    tickets: "/tickets",
    "saved-views": "/saved-views",
    clients: "/clients",
    knowledge: "/knowledge",
    "internal-operations": "/internal-operations",
    portal: "/portal",
  };
  if (state?.manualLogout) return preferredPath ?? landingPages[user.default_page] ?? "/home";
  const requested = state?.from;
  const returnTo =
    requested?.pathname?.startsWith("/") && !requested.pathname.startsWith("//")
      ? `${requested.pathname}${requested.search ?? ""}${requested.hash ?? ""}`
      : null;
  const safeSaved =
    savedReturnPath?.startsWith("/") && !savedReturnPath.startsWith("//")
      ? savedReturnPath
      : null;
  return returnTo ?? safeSaved ?? preferredPath ?? landingPages[user.default_page] ?? "/home";
}

export function LoginPage() {
  const { login } = useAuth();
  const { t, i18n } = useTranslation();
  const isRtl = i18n.dir() === "rtl";
  const schema = z.object({
    login: z.string().min(1, t("auth.loginRequired")),
    password: z.string().min(8, t("auth.passwordLength")),
  });
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");
  const [sessionNotice] = useState(() => {
    const reason = consumeSessionEndReason();
    const messages: Record<string, string> = {
      expired: "Your session expired. Sign in again to continue.",
      account_inactive: "Your account was disabled. Contact an administrator.",
      session_revoked: "Your session was revoked for security. Sign in again.",
      refresh_rejected: "Your saved session is no longer valid. Sign in again.",
      signed_out_elsewhere: "You signed out in another browser tab.",
      storage_loss:
        "Your browser session data was cleared. Sign in again to continue.",
    };
    return reason ? (messages[reason] ?? "Please sign in again.") : "";
  });
  const [savedReturnPath] = useState(() => consumeReturnPath());
  const {
    register,
    handleSubmit,
    resetField,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) });
  const submit = async (values: Form) => {
    try {
      const user = await login(values.login, values.password);
      resetField("password");
      navigate(
        loginDestination(
          user,
          location.state as LoginNavigationState | null,
          savedReturnPath,
          user.user_type === "EMPLOYEE"
            ? preferredWorkspace(user.id, (permission) => user.permissions.includes(permission))?.path
            : undefined,
        ),
        { replace: true },
      );
    } catch {
      resetField("password");
      setError(t("auth.failed"));
    }
  };
  return (
    <Box
      data-login-background="grid-drift ambient-glow"
      sx={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        minHeight: "100dvh",
        height: { md: "100dvh" },
        display: { xs: "flex", md: "grid" },
        flexDirection: "column",
        justifyContent: { xs: "center", md: "normal" },
        gridTemplateColumns: {
          xs: "1fr",
          md: "minmax(400px, .78fr) minmax(0, 1.22fr)",
        },
        alignItems: "center",
        gap: { md: 7, lg: 11 },
        px: {
          xs: "max(16px, env(safe-area-inset-left))",
          sm: 5,
          md: 7,
          lg: 10,
        },
        py: {
          xs: "max(16px, env(safe-area-inset-top))",
          md: 3,
        },
        pb: {
          xs: "max(16px, env(safe-area-inset-bottom))",
          md: 3,
        },
        overflowX: "hidden",
        overflowY: { xs: "auto", md: "hidden" },
        WebkitOverflowScrolling: "touch",
        direction: isRtl ? "rtl" : "ltr",
        bgcolor: "#06142f",
        background:
          "linear-gradient(rgba(56,189,248,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(56,189,248,.035) 1px, transparent 1px), radial-gradient(circle at 12% 12%, rgba(45,212,191,.16), transparent 31%), radial-gradient(circle at 86% 88%, rgba(56,189,248,.14), transparent 32%), linear-gradient(145deg, #06142f 0%, #081d3f 52%, #071832 100%)",
        backgroundSize: "52px 52px, 52px 52px, auto, auto, auto",
        animation: `${backgroundDrift} 24s linear infinite`,
        "&::before": {
          content: '""',
          position: "absolute",
          width: { xs: 280, md: 520 },
          height: { xs: 280, md: 520 },
          borderRadius: "50%",
          left: { xs: "-150px", md: "-240px" },
          bottom: { xs: "-170px", md: "-300px" },
          background: "rgba(13,148,136,.09)",
          filter: "blur(2px)",
          pointerEvents: "none",
          animation: `${ambientFloat} 13s ease-in-out infinite`,
        },
        "&::after": {
          content: '""',
          position: "absolute",
          width: { xs: 260, md: 460 },
          height: { xs: 260, md: 460 },
          borderRadius: "50%",
          right: { xs: "-150px", md: "-180px" },
          top: { xs: "-130px", md: "-210px" },
          background:
            "radial-gradient(circle, rgba(56,189,248,.18), rgba(56,189,248,.025) 58%, transparent 72%)",
          filter: "blur(4px)",
          pointerEvents: "none",
          animation: `${ambientPulse} 16s ease-in-out infinite`,
        },
        "@media (prefers-reduced-motion: reduce)": {
          animation: "none",
          "&::before, &::after": { animation: "none" },
        },
      }}
    >
      <Box
        component="section"
        sx={{
          position: "relative",
          zIndex: 1,
          color: "white",
          minWidth: 0,
          display: { xs: "none", md: "block" },
          order: 2,
          textAlign: "center",
          maxWidth: 880,
          width: "100%",
          justifySelf: "center",
          alignSelf: "stretch",
          pb: { md: 2, lg: 3 },
        }}
      >
        <Stack
          direction="row"
          justifyContent="center"
          alignItems="center"
          spacing={1.5}
          sx={{
            position: "fixed",
            zIndex: 3,
            top: { md: 28, lg: 36 },
            left: { md: 56, lg: 80 },
          }}
        >
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: 3.5,
              display: "grid",
              placeItems: "center",
              bgcolor: "white",
              color: "#0a1f46",
              fontSize: 24,
              fontWeight: 950,
              boxShadow: "0 16px 38px rgba(45,212,191,.17)",
            }}
          >
            M
          </Box>
          <Box>
            <Typography fontWeight={900} letterSpacing={0.8} lineHeight={1.05}>
              MILLENSYS
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: "#9fb3ce", letterSpacing: 2.3 }}
            >
              SUPPORT HUB
            </Typography>
          </Box>
        </Stack>

        <Box
          sx={{
            position: "fixed",
            zIndex: 2,
            left: "50%",
            bottom: { md: 10, lg: 14 },
            transform: "translateX(-50%)",
            width: "min(860px, calc(100vw - 48px))",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
            direction: isRtl ? "rtl" : "ltr",
          }}
        >
        <Typography
          variant="overline"
          sx={{
            display: "inline-flex",
            color: "#8cf0e2",
            fontWeight: 900,
            fontSize: 9,
            lineHeight: 1.2,
            letterSpacing: 1.2,
            whiteSpace: "nowrap",
          }}
        >
          {t("auth.heroEyebrow")}
        </Typography>
        <Typography
          component="h1"
          sx={{
            mt: 0.35,
            mb: 0.25,
            width: "100%",
            fontSize: { md: 17, lg: 19 },
            lineHeight: 1.05,
            letterSpacing: "-.035em",
            fontWeight: 950,
            fontFamily: isRtl
              ? '"Dubai", "Noto Kufi Arabic", "Segoe UI", Tahoma, sans-serif'
              : '"Bahnschrift", "Aptos Display", "Segoe UI Variable Display", "Segoe UI", sans-serif',
          }}
        >
          {t("auth.heroTitleStart")} <Box component="span" sx={{ color: "#2dd4bf" }}>{t("auth.heroTitleAccent")}</Box>
        </Typography>
        <Typography
          sx={{
            m: 0,
            width: "100%",
            maxWidth: 860,
            color: "#b9c8de",
            fontSize: { md: 9.5, lg: 10.5 },
            lineHeight: 1.35,
            whiteSpace: "normal",
            overflowWrap: "break-word",
            wordBreak: "keep-all",
          }}
        >
          {t("auth.heroDescription")}
        </Typography>
        </Box>
        <Box
          aria-hidden="true"
          data-login-orbits="true"
          sx={{
            position: "absolute",
            // Keep the decoration inside the hero stacking context. A negative
            // z-index can put it behind the full-page background in browsers.
            zIndex: 1,
            width: { md: 220, lg: 280 },
            aspectRatio: "1",
            right: "auto",
            left: "50%",
            top: "47%",
            translate: "-50% -50%",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(45,212,191,.10), transparent 58%)",
            boxShadow:
              "0 0 0 38px rgba(56,189,248,.035), 0 0 70px rgba(45,212,191,.08)",
            "&::after": {
              content: '""',
              position: "absolute",
              inset: "-14%",
              borderRadius: "50%",
              border: "1px solid rgba(56,189,248,.09)",
            },
          }}
        >
          <Box
            data-orbit-ring="outer"
            sx={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              border: "1px solid rgba(45,212,191,.2)",
              transformOrigin: "center",
              animation: `${orbitClockwise} 18s linear infinite`,
              willChange: "transform",
              "&::before": {
                content: '""',
                position: "absolute",
                width: 14,
                height: 14,
                top: "8%",
                left: "18%",
                borderRadius: "50%",
                bgcolor: "#2dd4bf",
                boxShadow: "0 0 22px #2dd4bf",
              },
            }}
          />
          <Box
            data-orbit-ring="inner"
            sx={{
              position: "absolute",
              inset: "21%",
              borderRadius: "50%",
              border: "1px solid rgba(56,189,248,.21)",
              transformOrigin: "center",
              animation: `${orbitCounterClockwise} 12s linear infinite`,
              willChange: "transform",
              "&::after": {
                content: '""',
                position: "absolute",
                width: 11,
                height: 11,
                right: "4%",
                bottom: "18%",
                borderRadius: "50%",
                bgcolor: "#38bdf8",
                boxShadow: "0 0 20px #38bdf8",
              },
            }}
          />
          <Box
            data-login-logo="true"
            sx={{
              position: "absolute",
              zIndex: 2,
              width: "36%",
              aspectRatio: "1",
              left: "32%",
              top: "32%",
              display: "grid",
              placeItems: "center",
              borderRadius: "28%",
              bgcolor: "rgba(255,255,255,.96)",
              color: "#0a1f46",
              fontSize: { md: 29, lg: 37 },
              fontWeight: 950,
              letterSpacing: "-.035em",
              whiteSpace: "nowrap",
              boxShadow:
                "0 24px 65px rgba(0,5,28,.42), inset 0 0 0 1px rgba(255,255,255,.8)",
            }}
          >
            SH
          </Box>
        </Box>
      </Box>

      <Paper
        component="form"
        onSubmit={handleSubmit(submit)}
        elevation={20}
        sx={{
          position: "relative",
          zIndex: 1,
          order: 1,
          flexShrink: 0,
          mx: { xs: "auto", md: 0 },
          justifySelf: { md: "start" },
          p: { xs: 2.25, sm: 3.5, lg: 4 },
          width: "100%",
          maxWidth: 440,
          borderRadius: { xs: 4, sm: 5 },
          border: "1px solid rgba(255,255,255,.22)",
          bgcolor: "rgba(255,255,255,.97)",
          backdropFilter: "blur(22px)",
          boxShadow:
            "0 32px 90px rgba(0, 5, 28, .52), 0 0 0 1px rgba(45,212,191,.05)",
          overflow: "hidden",
          "@media (max-height: 700px) and (max-width: 899.95px)": {
            p: 2,
            borderRadius: 3,
          },
          "&::before": {
            content: '""',
            position: "absolute",
            inset: "0 0 auto",
            height: 5,
            background: "linear-gradient(90deg, #0d9488, #2dd4bf, #38bdf8)",
          },
          "&::after": {
            content: '""',
            position: "absolute",
            width: 150,
            height: 150,
            borderRadius: "50%",
            right: -85,
            top: -85,
            background: "rgba(45,212,191,.08)",
          },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          spacing={1.25}
          mb={3}
          sx={{
            display: { md: "none" },
            "@media (max-height: 700px)": { mb: 1.5 },
          }}
        >
          <Box sx={{ width: 40, height: 40, borderRadius: 2.5, display: "grid", placeItems: "center", bgcolor: "#0a1f46", color: "white", fontWeight: 950 }}>
            M
          </Box>
          <Box>
            <Typography color="#0a1f46" fontWeight={900} lineHeight={1}>MILLENSYS</Typography>
            <Typography variant="caption" color="text.secondary" letterSpacing={1.6}>SUPPORT HUB</Typography>
          </Box>
        </Stack>
        <Typography
          variant="overline"
          sx={{
            display: "inline-flex",
            px: 1.25,
            py: 0.35,
            borderRadius: 99,
            color: "#0d9488",
            bgcolor: "rgba(13,148,136,.08)",
            fontWeight: 900,
            letterSpacing: 1.6,
          }}
        >
          {t("auth.secureWorkspace")}
        </Typography>
        <Typography variant="h4" fontWeight={900} color="#0a1f46" gutterBottom>
          {t("auth.welcomeBack")}
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ mb: 3, "@media (max-height: 700px)": { mb: 1 } }}
        >
          {t("auth.workspacePrompt")}
        </Typography>
        {sessionNotice && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {sessionNotice}
          </Alert>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          fullWidth
          label={t("auth.username")}
          autoComplete="username"
          margin="normal"
          sx={{
            "& .MuiOutlinedInput-root": {
              borderRadius: 2.5,
              bgcolor: "rgba(6,20,47,.025)",
              transition: "box-shadow 160ms ease, background 160ms ease",
              "&.Mui-focused": {
                bgcolor: "white",
                boxShadow: "0 0 0 4px rgba(13,148,136,.09)",
              },
            },
          }}
          slotProps={{
            htmlInput: { dir: "ltr" },
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <PersonOutlineRounded sx={{ color: "#0d9488" }} />
                </InputAdornment>
              ),
            },
          }}
          {...register("login")}
          error={!!errors.login}
          helperText={errors.login?.message}
        />
        <TextField
          fullWidth
          label={t("auth.password")}
          type="password"
          autoComplete="current-password"
          margin="normal"
          sx={{
            "& .MuiOutlinedInput-root": {
              borderRadius: 2.5,
              bgcolor: "rgba(6,20,47,.025)",
              transition: "box-shadow 160ms ease, background 160ms ease",
              "&.Mui-focused": {
                bgcolor: "white",
                boxShadow: "0 0 0 4px rgba(13,148,136,.09)",
              },
            },
          }}
          slotProps={{
            htmlInput: { dir: "ltr" },
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <LockOutlined sx={{ color: "#0d9488" }} />
                </InputAdornment>
              ),
            },
          }}
          {...register("password")}
          error={!!errors.password}
          helperText={errors.password?.message}
        />
        <Button
          fullWidth
          variant="contained"
          type="submit"
          endIcon={<ArrowForwardRounded />}
          disabled={isSubmitting}
          size="large"
          sx={{
            mt: 2,
            minHeight: 50,
            borderRadius: 2.5,
            bgcolor: "#0d9488",
            fontWeight: 900,
            boxShadow: "0 12px 28px rgba(13,148,136,.25)",
            letterSpacing: ".02em",
            transition: "transform 160ms ease, box-shadow 160ms ease",
            "&:hover": {
              bgcolor: "#08776e",
              transform: "translateY(-1px)",
              boxShadow: "0 16px 34px rgba(13,148,136,.32)",
            },
            "@media (max-height: 700px)": { mt: 1 },
          }}
        >
          {isSubmitting ? t("auth.signingIn") : t("auth.signIn")}
        </Button>
        <Button fullWidth component={Link} to="/forgot-password" sx={{ mt: 1, color: "#0a1f46" }}>
          {t("auth.forgotPassword")}
        </Button>
        <Divider sx={{ my: 2.25, "@media (max-height: 700px)": { my: 1 } }} />
        <Stack direction="row" alignItems="center" justifyContent="center" gap={1}>
          <VerifiedUserOutlined sx={{ color: "#0d9488", fontSize: 18 }} />
          <Typography variant="caption" color="text.secondary" fontWeight={650}>
            {t("auth.secureWorkspace")}
          </Typography>
        </Stack>
      </Paper>

      <Box
        component="footer"
        sx={{
          position: "relative",
          zIndex: 1,
          display: { xs: "block", md: "none" },
          order: 3,
          flexShrink: 0,
          mt: { xs: 2.5, sm: 3 },
          px: { xs: 1, sm: 3 },
          textAlign: "center",
          color: "white",
          "@media (max-height: 700px)": {
            mt: 1.5,
          },
        }}
      >
        <Typography
          component="p"
          sx={{
            m: 0,
            fontSize: { xs: 21, sm: 26 },
            lineHeight: 1.15,
            letterSpacing: "-.025em",
            fontWeight: 900,
            fontFamily: isRtl
              ? '"Dubai", "Noto Kufi Arabic", "Segoe UI", Tahoma, sans-serif'
              : '"Bahnschrift", "Aptos Display", "Segoe UI Variable Display", "Segoe UI", sans-serif',
            "@media (max-height: 620px)": { fontSize: 17 },
          }}
        >
          {t("auth.heroTitleStart")} <Box component="span" sx={{ color: "#2dd4bf" }}>{t("auth.heroTitleAccent")}</Box>
        </Typography>
        <Typography
          sx={{
            mt: 1,
            mx: "auto",
            maxWidth: 580,
            color: "#b9c8de",
            fontSize: { xs: 12, sm: 14 },
            lineHeight: 1.55,
            "@media (max-height: 700px)": { display: "none" },
          }}
        >
          {t("auth.heroDescription")}
        </Typography>
      </Box>
    </Box>
  );
}
