import { usePortal } from "@/lib/portal";

export function AdminHome() {
  const { boot } = usePortal();
  if (!boot) return null;

  if (!boot.is_super_admin) {
    return (
      <div className="rounded-xl border border-[var(--pl-line)] bg-white p-6">
        <h1 className="text-xl font-semibold">Access restricted</h1>
        <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
          Super Admin role is required for the platform console.
        </p>
        <a className="mt-4 inline-block underline" href="/portal/tenant">
          Go to Tenant portal
        </a>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Super Admin</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--pl-ink-soft)]">
          Platform controls for this Prime Ledger site. Near-term tenancy is multi-company under one
          site; master controls decide what tenants see in their portal.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">{boot.companies.length}</div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Companies</div>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">
            {boot.all_modules.filter((m) => m.enabled).length}
          </div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Enabled modules</div>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">
            {boot.all_modules.filter((m) => !m.enabled).length}
          </div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Hidden modules</div>
        </div>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        <a
          href="/portal/admin/modules"
          className="rounded-xl border border-[var(--pl-line)] bg-white p-5 hover:border-[var(--pl-ink)]"
        >
          <div className="font-semibold">Master Controls</div>
          <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
            Choose which portal modules tenants can see.
          </p>
        </a>
        <a
          href="/portal/admin/tenants"
          className="rounded-xl border border-[var(--pl-line)] bg-white p-5 hover:border-[var(--pl-ink)]"
        >
          <div className="font-semibold">Companies / Tenants</div>
          <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
            Review companies configured under this site.
          </p>
        </a>
      </section>
    </div>
  );
}
