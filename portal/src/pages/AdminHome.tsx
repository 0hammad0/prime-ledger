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

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Site admin</h1>
        <p className="mt-2 max-w-2xl text-base text-[var(--pl-ink-soft)]">
          Control what teams can see. Most people only need the business home — use these tools when
          you want to change that.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">{boot.companies.length}</div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Businesses</div>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">
            {boot.all_modules.filter((m) => m.enabled).length}
          </div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Tools turned on</div>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-white p-5">
          <div className="text-3xl font-semibold">
            {boot.all_modules.filter((m) => !m.enabled).length}
          </div>
          <div className="mt-1 text-sm text-[var(--pl-ink-soft)]">Tools hidden</div>
        </div>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        <a
          href="/portal/admin/modules"
          className="rounded-xl border-2 border-[var(--pl-accent)]/30 bg-white p-5 hover:border-[var(--pl-accent)]"
        >
          <div className="text-xs font-semibold tracking-wide text-[var(--pl-accent)] uppercase">
            Step 1
          </div>
          <div className="mt-1 font-semibold">What teams can see</div>
          <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
            Turn menu items on or off for the business home.
          </p>
        </a>
        <a
          href="/portal/admin/tenants"
          className="rounded-xl border border-[var(--pl-line)] bg-white p-5 hover:border-[var(--pl-ink)]"
        >
          <div className="font-semibold">Businesses on this site</div>
          <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">See the companies set up here.</p>
        </a>
      </section>
    </div>
  );
}
