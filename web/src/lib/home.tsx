import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { callMethod } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { HomePayload } from "@/lib/types";

type HomeValue = {
  home: HomePayload | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setCompanyName: (name: string) => Promise<void>;
};

const HomeContext = createContext<HomeValue | null>(null);

export function HomeProvider({ children }: { children: ReactNode }) {
  const { boot, refresh } = useAuth();
  const [home, setHome] = useState<HomePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const company = boot?.default_company || boot?.companies[0]?.name || "";

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = (await callMethod(
        "erpnext.portal_control.dashboard.get_home",
        company ? { company } : {},
        false,
      )) as HomePayload;
      setHome(next);
    } catch (e) {
      setHome(null);
      setError(e instanceof Error ? e.message : "Could not load home");
    } finally {
      setLoading(false);
    }
  }, [company]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const setCompanyName = async (name: string) => {
    await callMethod("erpnext.portal_control.dashboard.set_company", { company: name });
    await refresh();
  };

  const value = useMemo(
    () => ({ home, loading, error, reload, setCompanyName }),
    [home, loading, error, reload],
  );

  return <HomeContext.Provider value={value}>{children}</HomeContext.Provider>;
}

export function useHome() {
  const ctx = useContext(HomeContext);
  if (!ctx) throw new Error("useHome requires HomeProvider");
  return ctx;
}
