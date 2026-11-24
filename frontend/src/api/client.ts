import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { randomUuid } from "../utils/randomUuid";

type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    details?: { required_permission?: string; required_permissions?: string[] };
  };
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
};

function requestArea(url = "") {
  if (url.includes("/auth/login")) return "Sign-in";
  if (url.includes("/home/")) return "Support Now";
  if (url.includes("/dashboards/")) return "Dashboard";
  if (url.includes("/pre-tickets")) return "Pre-Tickets";
  if (url.includes("/tickets")) return "Tickets";
  if (url.includes("/clients")) return "Clients";
  if (url.includes("/internal-operations")) return "Operations";
  if (url.includes("/shifts")) return "Shifts";
  return "This request";
}

function requestReference(error: AxiosError) {
  const responseReference = error.response?.headers?.["x-correlation-id"];
  const headers = error.config?.headers as
    | (InternalAxiosRequestConfig["headers"] & {
        get?: (name: string) => unknown;
      })
    | undefined;
  const requestReference =
    headers?.get?.("X-Correlation-ID") ?? headers?.["X-Correlation-ID"];
  const value = responseReference ?? requestReference;
  return typeof value === "string" && value ? ` Reference: ${value}.` : "";
}

export function apiErrorMessage(
  error: unknown,
  fallback = "The request could not be completed.",
) {
  if (!axios.isAxiosError<ApiErrorBody>(error)) return fallback;
  const area = requestArea(error.config?.url);
  if (error.code === "ECONNABORTED") {
    const readOnly = ["get", "head"].includes(
      error.config?.method?.toLowerCase() ?? "",
    );
    return readOnly
      ? `${area} is taking too long. Please try again.`
      : "No response from the server. Check whether the action completed before retrying.";
  }
  const body = error.response?.data;
  if (body?.error?.message) return body.error.message;
  if (typeof body?.detail === "string") return body.detail;
  if (Array.isArray(body?.detail) && body.detail.length) {
    return body.detail
      .map((item) => {
        const field = item.loc?.filter((value) => value !== "body").at(-1);
        return `${field ? `${String(field).replaceAll("_", " ")}: ` : ""}${item.msg ?? "Invalid value"}`;
      })
      .join(" · ");
  }
  if ([502, 503, 504].includes(error.response?.status ?? 0)) {
    return `${area} is temporarily unavailable. Please try again shortly.`;
  }
  if (!error.response)
    return "Connection lost. Check your network and try again.";
  return error.message || fallback;
}

function notifyApiError(error: AxiosError) {
  // Presence is best-effort background telemetry. A transient heartbeat
  // failure must never interrupt the user's current workflow with a toast.
  if (error.config?.url?.includes("/auth/presence")) return;
  const notificationSuppressed = (
    error.config as
      | (InternalAxiosRequestConfig & { suppressErrorNotification?: boolean })
      | undefined
  )?.suppressErrorNotification;
  if (notificationSuppressed) return;
  const accessAware = (
    error.config as
      | (InternalAxiosRequestConfig & { suppressAccessError?: boolean })
      | undefined
  )?.suppressAccessError;
  if (
    error.code === "ERR_CANCELED" ||
    error.response?.status === 401 ||
    (error.response?.status === 403 && accessAware)
  )
    return;
  const body = error.response?.data as ApiErrorBody | undefined;
  const required =
    body?.error?.details?.required_permission ??
    body?.error?.details?.required_permissions?.[0];
  if (
    error.response?.status === 403 &&
    body?.error?.code === "FORBIDDEN" &&
    required
  ) {
    window.dispatchEvent(
      new CustomEvent("support-hub-access-required", {
        detail: { permission: required },
      }),
    );
    return;
  }
  console.error("Support Hub API request failed", {
    message: error.message,
    code: error.code,
    status: error.response?.status,
    method: error.config?.method,
    url: error.config?.url,
    reference: requestReference(error).replace(/^ Reference: |\.$/g, ""),
    response: error.response?.data,
  });
  window.dispatchEvent(
    new CustomEvent("support-hub-api-error", {
      detail: {
        message: apiErrorMessage(error),
        status: error.response?.status,
      },
    }),
  );
}

export const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_URL ??
    `${import.meta.env.BASE_URL.replace(/\/$/, "")}/backend/api/v1`,
  timeout: 30_000,
});

api.interceptors.request.use((config) => {
  if (!config.headers.get("X-Correlation-ID"))
    config.headers.set("X-Correlation-ID", randomUuid());
  return config;
});

// Historical dashboards aggregate substantially more data than ordinary CRUD
// requests. Keep the normal 30-second safety bound while allowing these
// explicitly selected analytical calls enough time to finish on 30K+ histories.
export const DASHBOARD_ANALYSIS_TIMEOUT_MS = 120_000;

const refreshTokenKey = "support-hub-refresh-token";
const accessTokenKey = "support-hub-access-token";
const sessionEndReasonKey = "support-hub-session-end-reason";
const returnPathKey = "support-hub-return-path";
const sessionExpiryKey = "support-hub-session-expiry";
const diagnosticKey = "support-hub-session-diagnostics";
let refreshRequest: Promise<{
  access_token: string;
  refresh_token: string;
}> | null = null;

function tokenStorage(): Storage {
  return window.sessionStorage;
}
function refreshStorage(): Storage {
  try {
    const candidate = window.localStorage;
    return typeof candidate?.getItem === "function"
      ? candidate
      : tokenStorage();
  } catch {
    return tokenStorage();
  }
}

export function storedRefreshToken() {
  return (
    refreshStorage().getItem(refreshTokenKey) ??
    tokenStorage().getItem(refreshTokenKey)
  );
}

type Tokens = {
  access_token: string;
  refresh_token: string;
  session_expires_at?: string;
};
function diagnostic(code: string, status?: number) {
  try {
    const rows = JSON.parse(
      tokenStorage().getItem(diagnosticKey) ?? "[]",
    ) as unknown[];
    tokenStorage().setItem(
      diagnosticKey,
      JSON.stringify([
        ...rows.slice(-19),
        {
          code,
          status,
          online: navigator.onLine,
          at: new Date().toISOString(),
        },
      ]),
    );
  } catch {
    /* Diagnostics must never interrupt authentication. */
  }
}

export function persistTokens(tokens: Tokens) {
  tokenStorage().setItem(accessTokenKey, tokens.access_token);
  refreshStorage().setItem(refreshTokenKey, tokens.refresh_token);
  tokenStorage().removeItem(refreshTokenKey);
  if (tokens.session_expires_at)
    refreshStorage().setItem(sessionExpiryKey, tokens.session_expires_at);
  setAccessToken(tokens.access_token);
}

export function clearStoredTokens() {
  setAccessToken(null);
  tokenStorage().removeItem(accessTokenKey);
  tokenStorage().removeItem(refreshTokenKey);
  refreshStorage().removeItem(refreshTokenKey);
  refreshStorage().removeItem(sessionExpiryKey);
}

export function consumeSessionEndReason() {
  const value = tokenStorage().getItem(sessionEndReasonKey);
  tokenStorage().removeItem(sessionEndReasonKey);
  return value;
}
export function consumeReturnPath() {
  const value = tokenStorage().getItem(returnPathKey);
  tokenStorage().removeItem(returnPathKey);
  return value;
}
export function storedSessionExpiry() {
  return refreshStorage().getItem(sessionExpiryKey);
}
export function expireSessionByPolicy() {
  tokenStorage().setItem(sessionEndReasonKey, "expired");
  tokenStorage().setItem(
    returnPathKey,
    `${window.location.pathname}${window.location.search}${window.location.hash}`,
  );
  diagnostic("INACTIVITY_EXPIRY");
  clearStoredTokens();
  window.dispatchEvent(
    new CustomEvent("support-hub-session-expired", {
      detail: { reason: "expired" },
    }),
  );
}

export function authoritativeSessionEndReason(error: unknown) {
  if (
    !axios.isAxiosError<ApiErrorBody>(error) ||
    error.response?.status !== 401
  )
    return null;
  const code = error.response.data?.error?.code;
  if (code === "REFRESH_TOKEN_EXPIRED") return "expired";
  if (code === "ACCOUNT_INACTIVE") return "account_inactive";
  if (code === "REFRESH_TOKEN_REUSE") return "session_revoked";
  if (code === "INVALID_REFRESH_TOKEN") return "refresh_rejected";
  // A proxy, overloaded worker, or generic authentication middleware may
  // return 401 without one of the refresh endpoint's definitive error codes.
  // Preserve the local session and retry instead of turning that temporary
  // response into an accidental logout.
  return null;
}

function accessAppearsUnexpired() {
  try {
    const raw = tokenStorage().getItem(accessTokenKey);
    if (!raw) return false;
    const payload = JSON.parse(
      atob(raw.split(".")[1].replaceAll("-", "+").replaceAll("_", "/")),
    ) as { exp?: number };
    return (
      typeof payload.exp === "number" &&
      payload.exp * 1000 > Date.now() + 60_000
    );
  } catch {
    return false;
  }
}

const wait = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

export function announceSessionRestoredIfNeeded(hadTransientFailure: boolean) {
  if (!hadTransientFailure) return false;
  window.dispatchEvent(new CustomEvent("support-hub-session-restored"));
  return true;
}

export function restoreAccessToken() {
  const token = tokenStorage().getItem(accessTokenKey);
  if (token) setAccessToken(token);
  return token;
}

async function rotateToken(refreshToken: string) {
  let lastError: unknown;
  let hadTransientFailure = false;
  for (const delay of [0, 400, 1200]) {
    if (delay) await wait(delay);
    try {
      const current = storedRefreshToken() ?? refreshToken;
      const response = await axios.post<Tokens>(
        `${api.defaults.baseURL}/auth/refresh`,
        { refresh_token: current },
        { timeout: 30_000 },
      );
      persistTokens(response.data);
      diagnostic("REFRESH_SUCCEEDED");
      announceSessionRestoredIfNeeded(hadTransientFailure);
      return response.data;
    } catch (error) {
      lastError = error;
      const reason = authoritativeSessionEndReason(error);
      if (reason) {
        diagnostic(
          reason,
          axios.isAxiosError(error) ? error.response?.status : undefined,
        );
        throw error;
      }
      hadTransientFailure = true;
      diagnostic(
        "NETWORK_OR_SERVER",
        axios.isAxiosError(error) ? error.response?.status : undefined,
      );
      window.dispatchEvent(
        new CustomEvent("support-hub-session-reconnecting", {
          detail: { attempt: delay === 0 ? 1 : delay === 400 ? 2 : 3 },
        }),
      );
    }
  }
  throw lastError;
}

export async function refreshSession(refreshToken: string) {
  if (navigator.locks) {
    return navigator.locks.request("support-hub-token-refresh", () =>
      rotateToken(refreshToken),
    );
  }
  return rotateToken(refreshToken);
}

export function setAccessToken(token: string | null) {
  if (token) api.defaults.headers.common.Authorization = `Bearer ${token}`;
  else delete api.defaults.headers.common.Authorization;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as
      | (InternalAxiosRequestConfig & {
          _retriedAfterRefresh?: boolean;
          _databaseBusyRetries?: number;
          _transientGatewayRetries?: number;
        })
      | undefined;
    const requestUrl = request?.url ?? "";
    const responseBody = error.response?.data as ApiErrorBody | undefined;
    const databaseBusy =
      error.response?.status === 503 &&
      responseBody?.error?.code === "DATABASE_BUSY";
    if (
      databaseBusy &&
      request?.method?.toLowerCase() === "get" &&
      (request._databaseBusyRetries ?? 0) < 2
    ) {
      request._databaseBusyRetries = (request._databaseBusyRetries ?? 0) + 1;
      const retryAfterSeconds = Number(
        error.response?.headers?.["retry-after"] ?? 1,
      );
      await wait(Math.min(5, Math.max(1, retryAfterSeconds)) * 1000);
      return api(request);
    }
    const transientGatewayFailure = [502, 503, 504].includes(
      error.response?.status ?? 0,
    );
    if (
      transientGatewayFailure &&
      request?.method?.toLowerCase() === "get" &&
      (request._transientGatewayRetries ?? 0) < 2
    ) {
      request._transientGatewayRetries =
        (request._transientGatewayRetries ?? 0) + 1;
      await wait(request._transientGatewayRetries === 1 ? 400 : 1200);
      return api(request);
    }
    const canRefresh =
      error.response?.status === 401 &&
      request &&
      !request._retriedAfterRefresh &&
      !requestUrl.includes("/auth/login") &&
      !requestUrl.includes("/auth/refresh");
    if (canRefresh && accessAppearsUnexpired())
      diagnostic("CLOCK_SKEW_OR_SERVER_REJECTION", 401);
    const refreshToken = storedRefreshToken();
    if (!canRefresh || !refreshToken) {
      if (
        error.response?.status === 401 &&
        request &&
        !requestUrl.includes("/auth/login") &&
        !requestUrl.includes("/auth/refresh") &&
        !refreshToken
      ) {
        diagnostic("STORAGE_LOSS", 401);
        tokenStorage().setItem(sessionEndReasonKey, "storage_loss");
        tokenStorage().setItem(
          returnPathKey,
          `${window.location.pathname}${window.location.search}${window.location.hash}`,
        );
        clearStoredTokens();
        window.dispatchEvent(
          new CustomEvent("support-hub-session-expired", {
            detail: { reason: "storage_loss" },
          }),
        );
      }
      notifyApiError(error);
      return Promise.reject(error);
    }
    request._retriedAfterRefresh = true;
    try {
      refreshRequest ??= refreshSession(refreshToken).finally(() => {
        refreshRequest = null;
      });
      const tokens = await refreshRequest;
      persistTokens(tokens);
      request.headers.Authorization = `Bearer ${tokens.access_token}`;
      return api(request);
    } catch (refreshError) {
      const reason = authoritativeSessionEndReason(refreshError);
      if (reason) {
        tokenStorage().setItem(sessionEndReasonKey, reason);
        tokenStorage().setItem(
          returnPathKey,
          `${window.location.pathname}${window.location.search}${window.location.hash}`,
        );
        clearStoredTokens();
        window.dispatchEvent(
          new CustomEvent("support-hub-session-expired", {
            detail: { reason },
          }),
        );
      } else {
        window.dispatchEvent(
          new CustomEvent("support-hub-session-unavailable", {
            detail: { reason: "network_or_server" },
          }),
        );
      }
      return Promise.reject(refreshError);
    }
  },
);

window.addEventListener("storage", (event) => {
  if (event.key === refreshTokenKey && !event.newValue) {
    tokenStorage().setItem(sessionEndReasonKey, "signed_out_elsewhere");
    tokenStorage().setItem(
      returnPathKey,
      `${window.location.pathname}${window.location.search}${window.location.hash}`,
    );
    setAccessToken(null);
    diagnostic("SIGNED_OUT_ELSEWHERE");
    window.dispatchEvent(
      new CustomEvent("support-hub-session-expired", {
        detail: { reason: "signed_out_elsewhere" },
      }),
    );
  }
});
