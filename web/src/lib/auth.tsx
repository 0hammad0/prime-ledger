import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { callMethod, login as apiLogin, logout as apiLogout, refreshGuestCsrf } from "./api";
import type { Boot } from "./types";

type AuthValue = {
  boot: Boot | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  signIn: (usr: string, pwd: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [boot, setBoot] = useState<Boot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      await refreshGuestCsrf();
      const next = (await callMethod("erpnext.portal_control.api.get_portal_boot", {}, false)) as Boot;
      setBoot(next);
    } catch {
      setBoot(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const signIn = async (usr: string, pwd: string) => {
    setError(null);
    await apiLogin(usr, pwd);
    const next = (await callMethod("erpnext.portal_control.api.get_portal_boot", {}, false)) as Boot;
    setBoot(next);
  };

  const signOut = async () => {
    try {
      await apiLogout();
    } finally {
      setBoot(null);
    }
  };

  const value = useMemo(
    () => ({ boot, loading, error, refresh, signIn, signOut }),
    [boot, loading, error],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth requires AuthProvider");
  return ctx;
}
