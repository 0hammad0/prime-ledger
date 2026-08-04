import { usePortal } from "@/lib/portal";

const START_HERE = ["products", "sales", "purchases", "finance"] as const;

export function TenantHome() {
  const { boot } = usePortal();
  if (!boot) return null;

  const tiles = boot.modules.filter((m) => m.category !== "Super Admin" && m.module_key !== "dashboard");
  const starters = START_HERE.map((key) => tiles.find((m) => m.module_key === key)).filter(Boolean);
  const more = tiles.filter((m) => !START_HERE.includes(m.module_key as (typeof START_HERE)[number]));
  const firstName = (boot.user.full_name || boot.user.name || "there").split(" ")[0];
  const company = boot.companies[0]?.name;

  const hrefFor = (m: (typeof tiles)[number]) =>
    m.portal_route?.startsWith("/tenant") || m.portal_route?.startsWith("/admin")
      ? `/portal${m.portal_route}`
      : m.desk_route || "#";

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-8">
        <p className="text-sm font-medium text-[var(--pl-accent)]">You are signed in</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Welcome, {firstName}</h1>
        <p className="mt-2 max-w-2xl text-base text-[var(--pl-ink-soft)]">
          This is your business home
          {company ? (
            <>
              {" "}
              for <span className="font-medium text-[var(--pl-ink)]">{company}</span>
            </>
          ) : null}
          . Pick one thing below to begin.
        </p>
      </header>

      <section className="mb-8 rounded-xl border border-[var(--pl-line)] bg-white p-5">
        <h2 className="text-base font-semibold">Start here</h2>
        <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">
          Follow these in order if you are new. Tap a big button — that is enough.
        </p>
        <ol className="mt-4 grid gap-3 sm:grid-cols-2">
          {starters.map((m, i) =>
            m ? (
              <li key={m.module_key}>
                <a
                  href={hrefFor(m)}
                  className="flex h-full flex-col rounded-xl border-2 border-[var(--pl-accent)]/30 bg-[var(--pl-paper)] p-4 transition hover:border-[var(--pl-accent)]"
                >
                  <span className="text-xs font-semibold tracking-wide text-[var(--pl-accent)] uppercase">
                    Step {i + 1}
                  </span>
                  <span className="mt-1 text-lg font-semibold">{m.label}</span>
                  <span className="mt-1 text-sm text-[var(--pl-ink-soft)]">{m.description}</span>
                  <span className="mt-3 text-sm font-semibold text-[var(--pl-accent)]">
                    Open {m.label} →
                  </span>
                </a>
              </li>
            ) : null
          )}
        </ol>
      </section>

      {more.length ? (
        <section>
          <h2 className="mb-3 text-base font-semibold">More tools</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {more.map((m) => (
              <a
                key={m.module_key}
                href={hrefFor(m)}
                className="rounded-xl border border-[var(--pl-line)] bg-white p-4 transition hover:border-[var(--pl-ink)]"
              >
                <div className="text-base font-semibold">{m.label}</div>
                <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">{m.description}</p>
              </a>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
