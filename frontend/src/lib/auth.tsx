"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { apiFetch, refreshAccessToken, setAccessToken } from "@/lib/api";
import type { TokenOut, UserOut } from "@/lib/types";

interface AuthState {
  user: UserOut | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<UserOut>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadUser() {
    try {
      setUser(await apiFetch<UserOut>("/me", { auth: true }));
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    (async () => {
      const token = await refreshAccessToken();
      if (token) await loadUser();
      setLoading(false);
    })();
  }, []);

  const value: AuthState = {
    user,
    loading,
    async login(email, password) {
      const t = await apiFetch<TokenOut>("/auth/login", {
        method: "POST",
        json: { email, password },
      });
      setAccessToken(t.access_token);
      await loadUser();
    },
    async signup(email, password, fullName) {
      return apiFetch<UserOut>("/auth/signup", {
        method: "POST",
        json: { email, password, full_name: fullName },
      });
    },
    async logout() {
      try {
        await apiFetch<void>("/auth/logout", { method: "POST" });
      } finally {
        setAccessToken(null);
        setUser(null);
      }
    },
    refreshUser: loadUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
