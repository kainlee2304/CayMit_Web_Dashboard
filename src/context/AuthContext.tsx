"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { getTraceMe, loginTrace, registerTrace, TraceAuth, TraceRole, TraceUser } from "@/lib/api";

const TOKEN_KEY = "caymit_access_token";
const REFRESH_KEY = "caymit_refresh_token";

export type AuthState = "AUTH_LOADING" | "AUTHENTICATED" | "UNAUTHENTICATED";

export type RegisterData = {
  username: string;
  password: string;
  display_name: string;
  organization: string;
  role: Exclude<TraceRole, "admin" | "admin_hq">;
};

type AuthValue = {
  user: TraceUser | null;
  token: string;
  loading: boolean;
  authState: AuthState;
  login: (username: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<string>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<TraceUser | null>(null);
  const [token, setToken] = useState("");
  const [authState, setAuthState] = useState<AuthState>("AUTH_LOADING");

  const accept = (auth: TraceAuth) => {
    localStorage.setItem(TOKEN_KEY, auth.access_token);
    localStorage.setItem("trace_token", auth.access_token);
    if (auth.refresh_token) {
      localStorage.setItem(REFRESH_KEY, auth.refresh_token);
    }
    const orgIdCandidate = auth.user?.organization_id || auth.user?.organization;
    if (orgIdCandidate && /^[0-9a-fA-F-]{36}$/.test(String(orgIdCandidate))) {
      localStorage.setItem("tammy_organization_id", String(orgIdCandidate));
    } else {
      localStorage.removeItem("tammy_organization_id");
    }
    setToken(auth.access_token);
    setUser(auth.user);
    setAuthState("AUTHENTICATED");
  };

  useEffect(() => {
    let isMounted = true;

    async function bootstrapAuth() {
      const savedAccessToken = localStorage.getItem(TOKEN_KEY) || localStorage.getItem("trace_token");
      const savedRefreshToken = localStorage.getItem(REFRESH_KEY);

      if (!savedAccessToken && !savedRefreshToken) {
        if (isMounted) {
          setAuthState("UNAUTHENTICATED");
        }
        return;
      }

      // 1. Try restoring session with saved access token
      if (savedAccessToken) {
        try {
          const me = await getTraceMe(savedAccessToken);
          if (isMounted) {
            setToken(savedAccessToken);
            setUser(me);
            setAuthState("AUTHENTICATED");
          }
          return;
        } catch {
          // Token might be expired, proceed to refresh token below
        }
      }

      // 2. Try refreshing token if refresh token is present
      if (savedRefreshToken) {
        try {
          const baseURL = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
          const res = await axios.post(`${baseURL}/api/v1/auth/refresh`, {
            refresh_token: savedRefreshToken
          });
          const newAccess = res.data.access_token;
          const newRefresh = res.data.refresh_token;

          localStorage.setItem(TOKEN_KEY, newAccess);
          localStorage.setItem("trace_token", newAccess);
          if (newRefresh) {
            localStorage.setItem(REFRESH_KEY, newRefresh);
          }

          const me = await getTraceMe(newAccess);
          if (isMounted) {
            setToken(newAccess);
            setUser(me);
            setAuthState("AUTHENTICATED");
          }
          return;
        } catch {
          // Refresh failed
        }
      }

      // 3. Clear invalid session
      if (isMounted) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem("trace_token");
        setToken("");
        setUser(null);
        setAuthState("UNAUTHENTICATED");
      }
    }

    void bootstrapAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const logout = async () => {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    const accessToken = token || localStorage.getItem(TOKEN_KEY);

    if (refreshToken && accessToken) {
      try {
        const baseURL = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
        await axios.post(
          `${baseURL}/api/v1/auth/logout`,
          { refresh_token: refreshToken },
          { headers: { Authorization: `Bearer ${accessToken}` } }
        );
      } catch {
        // Continue clean logout regardless
      }
    }

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem("trace_token");
    localStorage.removeItem("tammy_organization_id");
    setToken("");
    setUser(null);
    setAuthState("UNAUTHENTICATED");
  };

  const value = useMemo<AuthValue>(
    () => ({
      user,
      token,
      loading: authState === "AUTH_LOADING",
      authState,
      login: async (username, password) => accept(await loginTrace({ username, password })),
      register: async (data) => (await registerTrace(data)).message,
      logout,
    }),
    [user, token, authState]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export const ROLE_LABELS: Record<TraceRole, string> = {
  admin_hq: "Quản trị viên HQ",
  farmer: "Nông hộ / Xã viên",
  technician: "Kỹ thuật viên Thẩm định",
  packhouse_lead: "Trưởng xưởng Đóng gói",
  qa_qc: "Chuyên viên Kiểm định QA/QC",
  logistics: "Quản lý Logistics & Xuất khẩu",
  admin: "Quản trị viên Hệ thống",
  producer: "Nông hộ sản xuất",
  processor: "Cơ sở sơ chế",
};
