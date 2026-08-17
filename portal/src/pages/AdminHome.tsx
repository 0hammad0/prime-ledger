import { usePortal } from "@/lib/portal";

export function AdminHome() {
  const { boot } = usePortal();
  if (!boot) return null;

  if (!boot.is_super_admin) {
    return (
      <div className="rounded-xl border border-[var(--pl-line)] bg-white p-6">
        <h1 className="text-xl font-semibold">This page is for the site owner</h1>
        <p className="mt-2 text-base text-[var(--pl-ink-soft)]">
          You can still use your business home for daily work.
        </p>
        <a
          className="mt-4 inline-flex min-h-11 items-center rounded-lg bg-[var(--pl-accent)] px-5 font-semibold text-white"
          href="/portal/tenant"
        >
          Go to business home
        </a>
      </div>
    );
  }

  const tenants = boot.tenants || [];
  const pending = tenants.filter((t) => t.status === "Pending").length;
  const waiting = tenants.filter((t) => t.status === "Approved" || t.status === "Provisioning").length;
  const live = tenants.filter((t) => t.status === "Active").length;
  const archived = tenants.filter((t) => t.status === "Archived").length;

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Platform owner</h1>
        <p className="mt-2 max-w-2xl text-base text-[var(--pl-ink-soft)]">
          This is the organization registry for Super Admin — not invoices, stock, or tenant books.
          Those live on each private site after provision.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">{pending}</div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Pending</div>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">{waiting}</div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Waiting on provision</div>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">{live}</div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Live</div>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">{archived}</div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Blocked / rejected</div>
        </div>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        <a
          href="/portal/admin/tenants"
          className="rounded-xl border-2 border-[var(--pl-accent)]/30 bg-white p-5 hover:border-[var(--pl-accent)]"
        >
          <div className="text-xs font-semibold tracking-wide text-[var(--pl-accent)] uppercase">
            Organizations
          </div>
          <div className="mt-1 font-semibold">Approve / reject / block</div>
          <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
            Signup requests and tenant sites. This panel does not open their books.
          </p>
        </a>
        <a
          href="/portal/admin/modules"
          className="rounded-xl border border-[var(--pl-line)] bg-white p-5 hover:border-[var(--pl-ink)]"
        >
          <div className="font-semibold">What teams can see</div>
          <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
            Turn menu items on or off for the control-site business home.
          </p>
        </a>
      </section>
    </div>
  );
}
