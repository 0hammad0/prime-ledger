import { usePortal } from "@/lib/portal";

export function TenantsPage() {
  const { boot } = usePortal();
  if (!boot) return null;

  if (!boot.is_super_admin) {
    return <div className="p-6">Access restricted</div>;
  }

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Companies / Tenants</h1>
        <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
          Near-term model: companies under one Prime Ledger site. Full multi-site SaaS tenancy can
          layer on later without changing the ERP engine.
        </p>
      </header>
      <div className="overflow-hidden rounded-xl border border-[var(--pl-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--pl-line)] bg-[var(--pl-paper)] text-[var(--pl-ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-medium">Company</th>
              <th className="px-4 py-3 font-medium">Abbr</th>
              <th className="px-4 py-3 font-medium">Currency</th>
              <th className="px-4 py-3 font-medium">Country</th>
            </tr>
          </thead>
          <tbody>
            {boot.companies.map((c) => (
              <tr key={c.name} className="border-b border-[var(--pl-line)] last:border-0">
                <td className="px-4 py-3 font-medium">{c.name}</td>
                <td className="px-4 py-3">{c.abbr || "—"}</td>
                <td className="px-4 py-3">{c.default_currency || "—"}</td>
                <td className="px-4 py-3">{c.country || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <a className="mt-4 inline-block text-sm underline" href="/app/company">
        Manage companies in Desk
      </a>
    </div>
  );
}
