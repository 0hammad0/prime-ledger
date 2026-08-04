import { NavLink, Outlet } from "react-router";
import { usePortal } from "@/lib/portal";
import type { PortalModule } from "@/lib/types";

function ModuleLink({ mod, base }: { mod: PortalModule; base: "tenant" | "admin" }) {
  const path = (mod.portal_route || "").replace(/^\//, "");
  const to = path.startsWith("portal/")
    ? `/${path}`
    : path.startsWith("tenant/") || path.startsWith("admin/")
      ? `/portal/${path}`
      : `/portal/${base}`;

  // Normalize seeded routes which already include /tenant or /admin
  const href = mod.portal_route?.startsWith("/tenant") || mod.portal_route?.startsWith("/admin")
    ? `/portal${mod.portal_route}`
    : to;

  return (
    <NavLink
      to={href}
      className={({ isActive }) =>
        `block rounded-lg px-3 py-2 text-sm transition ${
          isActive ? "bg-[var(--pl-ink)] text-[var(--pl-paper)]" : "text-[var(--pl-ink)] hover:bg-[var(--pl-mist)]"
        }`
      }
    >
      {mod.label}
    </NavLink>
  );
}

export function PortalShell({ mode }: { mode: "tenant" | "admin" }) {
  const { boot, loading, error } = usePortal();

  if (loading) {
    return (
      <div className="grid h-full place-items-center text-[var(--pl-ink-soft)]">
        Loading Prime Ledger portal…
      </div>
    );
  }

  if (error || !boot) {
    return (
      <div className="grid h-full place-items-center p-8 text-center">
        <div>
          <h1 className="mb-2 text-xl font-semibold">Portal unavailable</h1>
          <p className="mb-4 text-sm text-[var(--pl-ink-soft)]">{error || "Unknown error"}</p>
          <a className="underline" href="/login?redirect-to=/portal">
            Sign in again
          </a>
        </div>
      </div>
    );
  }

  const navModules = boot.modules.filter((m) => {
    if (mode === "admin") {
      return m.category === "Super Admin" || m.module_key === "master_controls";
    }
    return m.category !== "Super Admin";
  });

  return (
    <div className="flex min-h-full">
      <aside className="flex w-64 shrink-0 flex-col border-r border-[var(--pl-line)] bg-white">
        <div className="border-b border-[var(--pl-line)] px-4 py-5">
          <div className="text-xs tracking-[0.14em] text-[var(--pl-accent)] uppercase">Prime Ledger</div>
          <div className="mt-1 text-lg font-semibold">{boot.app_name}</div>
          <div className="mt-1 text-xs text-[var(--pl-ink-soft)]">
            {mode === "admin" ? "Super Admin" : "Tenant"}
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {navModules.map((m) => (
            <ModuleLink key={m.module_key} mod={m} base={mode} />
          ))}
        </nav>
        <div className="border-t border-[var(--pl-line)] p-4 text-xs text-[var(--pl-ink-soft)]">
          <div className="font-medium text-[var(--pl-ink)]">{boot.user.full_name || boot.user.name}</div>
          <div className="mt-2 flex gap-3">
            {boot.is_super_admin && mode === "tenant" ? (
              <a className="underline" href="/portal/admin">
                Super Admin
              </a>
            ) : null}
            {mode === "admin" ? (
              <a className="underline" href="/portal/tenant">
                Tenant view
              </a>
            ) : null}
            <a className="underline" href="/app">
              Desk
            </a>
            <a className="underline" href="/logout">
              Logout
            </a>
          </div>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-auto p-6 md:p-8">
        <Outlet />
      </main>
    </div>
  );
}
