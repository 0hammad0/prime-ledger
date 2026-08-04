import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { PortalBoot } from "./types";

type PortalContextValue = {
  boot: PortalBoot | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const PortalContext = createContext<PortalContextValue>({
  boot: null,
  loading: true,
  error: null,
  refresh: async () => undefined,
});

async function fetchBoot(): Promise<PortalBoot> {
  const res = await fetch("/api/method/erpnext.portal_control.api.get_portal_boot", {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-Frappe-CSRF-Token": window.csrf_token || "",
    },
  });
  const data = await res.json();
  if (data.exc_type || data.exception) {
    throw new Error(data._error_message || data.exception || "Failed to load portal");
  }
  return data.message as PortalBoot;
}

export function PortalProvider({ children }: { children: ReactNode }) {
  const [boot, setBoot] = useState<PortalBoot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await fetchBoot();
      setBoot(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portal");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const value = useMemo(() => ({ boot, loading, error, refresh }), [boot, loading, error]);
  return <PortalContext.Provider value={value}>{children}</PortalContext.Provider>;
}

export function usePortal() {
  return useContext(PortalContext);
}

export async function setModuleEnabled(moduleKey: string, enabled: boolean) {
  const body = new URLSearchParams({
    module_key: moduleKey,
    enabled: enabled ? "1" : "0",
  });
  const res = await fetch("/api/method/erpnext.portal_control.api.set_module_enabled", {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Frappe-CSRF-Token": window.csrf_token || "",
    },
    body,
  });
  const data = await res.json();
  if (data.exc_type || data.exception) {
    throw new Error(data._error_message || data.exception || "Update failed");
  }
  return data.message;
}
