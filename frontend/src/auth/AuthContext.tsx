import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  api,
  clearStoredTokens,
  consumeReturnPath,
  consumeSessionEndReason,
  expireSessionByPolicy,
  persistTokens,
  restoreAccessToken,
  storedRefreshToken,
  storedSessionExpiry,
} from "../api/client";
import { queryClient } from "../queryClient";

const accountScopedStorageKeys = [
  "support-hub-recent-pages-v1",
  "support-hub-opened-page-tabs-v2",
];

function clearAccountScopedClientState() {
  queryClient.clear();
  accountScopedStorageKeys.forEach((key) => window.sessionStorage.removeItem(key));
}

export type ThemePreset =
  | "CLASSIC"
  | "OCEAN"
  | "FOREST"
  | "SUNSET"
  | "PLUM"
  | "COBALT"
  | "MIDNIGHT"
  | "TERRACOTTA"
  | "GRAPHITE"
  | "NORDIC"
  | "AURORA"
  | "SAKURA"
  | "NEON"
  | "MOCHA"
  | "ARCTIC"
  | "OBSIDIAN_GOLD"
  | "MILLENSYS";

type User = {
  id: number;
  full_name: string;
  username: string;
  email: string;
  profile_picture_url?: string | null;
  user_type: "EMPLOYEE" | "CLIENT_PORTAL";
  department_id?: number | null;
  permissions: string[];
  require_password_change: boolean;
  default_page: string;
  auto_close_on_resolve: boolean;
  default_dashboard_scope: "GENERAL" | "MY";
  default_saved_view_id: number | null;
  theme_mode: "LIGHT" | "DARK" | "SYSTEM";
  theme_preset: ThemePreset;
  preferred_language: "en" | "ar";
};
type AuthValue = {
  user: User | null;
  permissions: string[];
  initializing: boolean;
  reconnecting: boolean;
  login: (login: string, password: string) => Promise<User>;
  changePassword: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  refreshPermissions: () => Promise<void>;
  updateProfilePreferences: (preferences: {
    default_page: string;
    default_dashboard_scope: "GENERAL" | "MY";
    default_saved_view_id: number | null;
    theme_mode: "LIGHT" | "DARK" | "SYSTEM";
    theme_preset: ThemePreset;
    profile_picture_url: string | null;
    preferred_language?: "en" | "ar";
  }) => Promise<void>;
  updateLanguage: (language: "en" | "ar") => Promise<void>;
  uploadProfilePicture: (file: File) => Promise<User>;
};

const AuthContext = createContext<AuthValue | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [initializing, setInitializing] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const restoreSession = async () => {
      if (!storedRefreshToken()) {
        setInitializing(false);
        return;
      }
      restoreAccessToken();
      while (!cancelled && storedRefreshToken()) {
        try {
          const response = await api.get<User>("/auth/me");
          if (cancelled) return;
          setUser(response.data);
          setPermissions(response.data.permissions);
          setReconnecting(false);
          setInitializing(false);
          return;
        } catch {
          if (!storedRefreshToken()) {
            setUser(null);
            setReconnecting(false);
            setInitializing(false);
            return;
          }
          setReconnecting(true);
          await new Promise((resolve) => window.setTimeout(resolve, 5000));
        }
      }
    };
    void restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let warned = false;
    const check = () => {
      const raw = storedSessionExpiry();
      if (!raw || !storedRefreshToken()) return;
      const remaining = new Date(raw).getTime() - Date.now();
      if (remaining <= 0) {
        expireSessionByPolicy();
        return;
      }
      if (remaining <= 5 * 60_000 && !warned) {
        warned = true;
        window.dispatchEvent(
          new CustomEvent("support-hub-session-expiry-warning", {
            detail: { minutes: Math.max(1, Math.ceil(remaining / 60_000)) },
          }),
        );
      }
    };
    check();
    const timer = window.setInterval(check, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const expireSession = () => {
      clearAccountScopedClientState();
      setUser(null);
      setPermissions([]);
      setInitializing(false);
    };
    window.addEventListener("support-hub-session-expired", expireSession);
    return () =>
      window.removeEventListener("support-hub-session-expired", expireSession);
  }, []);

  async function login(loginValue: string, password: string) {
    const { data } = await api.post("/auth/login", {
      login: loginValue,
      password,
    });
    persistTokens(data);
    const response = await api.get<User>("/auth/me");
    clearAccountScopedClientState();
    setUser(response.data);
    setPermissions(response.data.permissions);
    return response.data;
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    await api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    setUser((current) =>
      current ? { ...current, require_password_change: false } : current,
    );
  }

  function logout() {
    const refreshToken = storedRefreshToken();
    if (refreshToken)
      void api
        .post("/auth/logout", { refresh_token: refreshToken })
        .catch(() => undefined);
    clearStoredTokens();
    consumeReturnPath();
    consumeSessionEndReason();
    clearAccountScopedClientState();
    setUser(null);
    setPermissions([]);
  }

  async function updateProfilePreferences(profilePreferences: {
    default_page: string;
    default_dashboard_scope: "GENERAL" | "MY";
    default_saved_view_id: number | null;
    theme_mode: "LIGHT" | "DARK" | "SYSTEM";
    theme_preset: ThemePreset;
    profile_picture_url: string | null;
    preferred_language?: "en" | "ar";
  }) {
    const response = await api.put<User>(
      "/auth/me/profile-preferences",
      profilePreferences,
    );
    setUser(response.data);
    setPermissions(response.data.permissions);
  }

  async function updateLanguage(language: "en" | "ar") {
    const response = await api.put<User>("/auth/me/language", {
      preferred_language: language,
    });
    setUser(response.data);
    setPermissions(response.data.permissions);
  }

  async function uploadProfilePicture(file: File) {
    const form = new FormData();
    form.append("upload", file);
    const response = await api.post<User>("/auth/me/profile-picture", form);
    setUser(response.data);
    setPermissions(response.data.permissions);
    return response.data;
  }

  async function refreshPermissions() {
    const response = await api.get<User>("/auth/me");
    setUser(response.data);
    setPermissions(response.data.permissions);
  }

  const value = useMemo(
    () => ({
      user,
      permissions,
      initializing,
      reconnecting,
      login,
      changePassword,
      logout,
      updateProfilePreferences,
      updateLanguage,
      uploadProfilePicture,
      refreshPermissions,
      hasPermission: (code: string) => permissions.includes(code),
    }),
    [user, permissions, initializing, reconnecting],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
