import { usePortal } from "@/lib/portal";

export function TenantHome() {
  const { boot } = usePortal();
  if (!boot) return null;

  const tiles = boot.modules.filter((m) => m.category !== "Super Admin" && m.module_key !== "dashboard");

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Tenant Dashboard</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--pl-ink-soft)]">
          Your curated Prime Ledger workspace. Open a module to work in the portal or jump to the
          matching operational screen.
        </p>
      </header>

      <section className="mb-8 rounded-xl border border-[var(--pl-line)] bg-white p-5">
        <h2 className="text-sm font-semibold tracking-wide text-[var(--pl-ink-soft)] uppercase">
          Companies on this site
        </h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {boot.companies.map((c) => (
            <span
              key={c.name}
              className="rounded-full border border-[var(--pl-line)] px-3 py-1 text-sm"
            >
              {c.name}
              {c.abbr ? ` (${c.abbr})` : ""}
            </span>
          ))}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tiles.map((m) => (
          <a
            key={m.module_key}
            href={
              m.portal_route?.startsWith("/tenant") || m.portal_route?.startsWith("/admin")
                ? `/portal${m.portal_route}`
                : m.desk_route || "#"
            }
            className="rounded-xl border border-[var(--pl-line)] bg-white p-5 transition hover:border-[var(--pl-ink)]"
          >
            <div className="text-base font-semibold">{m.label}</div>
            <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">{m.description}</p>
            {m.desk_route ? (
              <div className="mt-4 text-xs text-[var(--pl-brass)]">
                Engine: {m.desk_route.replace("/app/", "")}
              </div>
            ) : null}
          </a>
        ))}
      </section>
    </div>
  );
}
