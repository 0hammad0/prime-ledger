import { Link, useSearchParams } from "react-router";
import { callMethod } from "@/lib/api";
import { money, whenLabel } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import { useHome } from "@/lib/home";
import { MODULE_CARDS, QUICK_LINKS, REPORT_PILLS, THEME } from "@/nexiscloud/MASTER";

export function DashboardPage() {
  const { boot } = useAuth();
  const { home, loading, error, reload } = useHome();
  const [params] = useSearchParams();
  const name = (boot?.user.full_name || "there").split(" ")[0];
  const currency = home?.currency || boot?.companies[0]?.default_currency || "PKR";
  const empty =
    home &&
    !home.receivables.amount &&
    !home.payables.amount &&
    !home.cash.amount &&
    !home.recent.length;
  const showInactive = localStorage.getItem("pl-show-inactive") === "1";
  const lockedParam = params.get("locked");

  const seed = async () => {
    if (
      !window.confirm(
        `Add the known sample customer, supplier, item, two sales invoices, and two purchase invoices to ${home?.company || "this company"}? This writes real documents.`,
      )
    ) {
      return;
    }
    try {
      const result = (await callMethod("erpnext.portal_control.demo.seed_demo_workspace", {
        company: home?.company,
      })) as { message?: string };
      window.alert(result.message || "Sample data loaded");
      await reload();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Could not load sample data");
    }
  };

  const cards = MODULE_CARDS.filter((c) => {
    if (showInactive) return true;
    if (c.locked) return false;
    const key = mapModule(c.id);
    const row = boot?.all_modules.find((m) => m.module_key === key || m.module_key === c.id);
    if (row) return Boolean(row.enabled);
    return true;
  }).map((c) => {
    const key = mapModule(c.id);
    const row = boot?.all_modules.find((m) => m.module_key === key || m.module_key === c.id);
    return { ...c, locked: Boolean(c.locked || (row && !row.enabled)) };
  });

  return (
    <div className="xl:flex xl:gap-6">
      <div className="min-w-0 flex-1">
        {lockedParam ? (
          <p className="mb-4 rounded-lg border border-[var(--pl-line)] bg-[var(--pl-surface)] px-3 py-2 text-sm">
            That module is locked until a Super Admin enables it.
          </p>
        ) : null}
        <p className="text-sm font-medium text-[var(--pl-accent)]">Dashboard</p>
        <h1 className="mt-1 text-2xl font-semibold">Welcome, {name}</h1>
        <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">
          {home?.company || boot?.companies[0]?.name || "Your organization"}
        </p>

        {error ? (
          <div className="mt-4 rounded-xl border border-[var(--pl-danger)]/40 bg-[var(--pl-surface)] p-4 text-sm">
            {error}{" "}
            <button type="button" className="underline" onClick={() => void reload()}>
              Retry
            </button>
          </div>
        ) : null}

        <section className="mt-6 grid gap-3 sm:grid-cols-3">
          <Kpi
            label="Total Receivables"
            amount={home?.receivables.amount}
            overdue={home?.receivables.overdue}
            currency={currency}
            loading={loading}
            href="/sales/invoices"
          />
          <Kpi
            label="Total Payables"
            amount={home?.payables.amount}
            overdue={home?.payables.overdue}
            currency={currency}
            loading={loading}
            href="/purchases/bills"
          />
          <Kpi label="Cash in Hand" amount={home?.cash.amount} currency={currency} loading={loading} href="/banking/accounts" />
        </section>

        {empty && !loading ? (
          <div className="mt-4 rounded-xl border border-dashed border-[var(--pl-accent)]/50 bg-[var(--pl-surface)] p-4 text-sm">
            No invoices in this company yet. Numbers above are live zeros, not placeholders.
            <button type="button" className="ml-2 font-medium text-[var(--pl-accent)] underline" onClick={() => void seed()}>
              Load known sample data
            </button>
          </div>
        ) : null}

        <section className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Quick Links</h2>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
            {QUICK_LINKS.map((l) => (
              <Link
                key={l.id}
                to={l.href}
                className="tap rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] px-3 py-3 text-sm hover:border-[var(--pl-accent)]"
              >
                {l.label}
              </Link>
            ))}
          </div>
        </section>

        <section className="mt-8">
          <h2 className="font-semibold">Modules</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {cards.map((card) => {
              const tint = THEME.moduleTint[card.id as keyof typeof THEME.moduleTint] || {
                bg: "#EEF2FF",
                fg: "#4338CA",
              };
              return (
                <div key={card.id} className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
                  <div className="flex items-center justify-between">
                    <span
                      className="rounded-lg px-2 py-1 text-xs font-semibold"
                      style={{ background: tint.bg, color: tint.fg }}
                    >
                      {card.title}
                    </span>
                    {card.locked ? <span className="text-xs text-[var(--pl-ink-soft)]">Locked</span> : null}
                  </div>
                  <ul className="mt-3 space-y-1 text-sm">
                    {card.links.map((link) => (
                      <li key={link.href}>
                        {card.locked ? (
                          <span className="text-[var(--pl-ink-soft)]">{link.label}</span>
                        ) : (
                          <Link className="text-[var(--pl-accent)] underline" to={link.href}>
                            {link.label}
                          </Link>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </section>

        <section className="mt-8">
          <h2 className="font-semibold">Reports</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {REPORT_PILLS.map((p) => (
              <Link
                key={p.id}
                to={p.href}
                className="rounded-full border border-[var(--pl-line)] bg-[var(--pl-surface)] px-4 py-2 text-sm"
              >
                {p.label}
              </Link>
            ))}
          </div>
        </section>
      </div>

      <aside className="mt-8 w-full shrink-0 space-y-4 xl:mt-0 xl:w-[300px]">
        <div className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
          <h2 className="font-semibold">Recently Opened</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(home?.recent || []).map((r) => (
              <li key={`${r.doctype}-${r.name}`}>
                <Link to={r.href || "/"} className="block hover:text-[var(--pl-accent)]">
                  <div className="font-medium">{r.title}</div>
                  <div className="text-xs text-[var(--pl-ink-soft)]">
                    {r.doctype} · {whenLabel(r.when)}
                  </div>
                </Link>
              </li>
            ))}
            {!loading && !home?.recent?.length ? (
              <li className="text-[var(--pl-ink-soft)]">Open an invoice or customer and it will show here.</li>
            ) : null}
          </ul>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
          <h2 className="font-semibold">Alerts & Notifications</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(home?.alerts || []).map((a) => (
              <li key={a.id}>
                <Link to={a.href || "/"} className="hover:underline">
                  {a.text}
                </Link>
              </li>
            ))}
            {!loading && !home?.alerts?.length ? (
              <li className="text-[var(--pl-ink-soft)]">Nothing overdue and no unread notifications.</li>
            ) : null}
          </ul>
        </div>
        <div className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
          <h2 className="font-semibold">Bank Accounts</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(home?.banks || []).map((b) => (
              <li key={b.name} className="flex justify-between gap-2">
                <span>{b.label || b.name}</span>
                <span className="font-medium">{money(b.balance, b.currency || currency)}</span>
              </li>
            ))}
            {!loading && !home?.banks?.length ? (
              <li className="text-[var(--pl-ink-soft)]">
                No cash or bank accounts yet.{" "}
                <Link className="underline" to="/finance/accounts">
                  Chart of Accounts
                </Link>
              </li>
            ) : null}
          </ul>
        </div>
      </aside>
    </div>
  );
}

function mapModule(id: string) {
  if (id === "purchase") return "purchases";
  if (id === "inventory") return "inventory";
  if (id === "accounts") return "finance";
  return id;
}

function Kpi({
  label,
  amount,
  overdue,
  currency,
  loading,
  href,
}: {
  label: string;
  amount?: number;
  overdue?: number;
  currency: string;
  loading: boolean;
  href: string;
}) {
  return (
    <Link to={href} className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4 shadow-[var(--pl-shadow)]">
      <div className="text-sm text-[var(--pl-ink-soft)]">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{loading ? "…" : money(amount || 0, currency)}</div>
      {overdue ? (
        <div className="mt-1 text-xs text-[var(--pl-danger)]">Overdue {money(overdue, currency)}</div>
      ) : (
        <div className="mt-1 text-xs text-[var(--pl-ink-soft)]">Overdue {money(0, currency)}</div>
      )}
    </Link>
  );
}
