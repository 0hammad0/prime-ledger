import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getCount } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const TILES = [
  { to: "/customers", label: "Customers", doctype: "Customer" },
  { to: "/products", label: "Products", doctype: "Item" },
  { to: "/sales", label: "Sales invoices", doctype: "Sales Invoice" },
  { to: "/purchases", label: "Purchase invoices", doctype: "Purchase Invoice" },
];

export function HomePage() {
  const { boot } = useAuth();
  const [counts, setCounts] = useState<Record<string, number>>({});
  const name = (boot?.user.full_name || "there").split(" ")[0];
  const company = boot?.companies[0]?.name;

  useEffect(() => {
    void Promise.all(
      TILES.map(async (t) => {
        try {
          const n = await getCount(t.doctype);
          return [t.doctype, Number(n) || 0] as const;
        } catch {
          return [t.doctype, 0] as const;
        }
      }),
    ).then((pairs) => setCounts(Object.fromEntries(pairs)));
  }, []);

  return (
    <div>
      <p className="text-sm font-medium text-[var(--pl-accent)]">You are signed in</p>
      <h1 className="mt-1 text-2xl font-semibold">Welcome, {name}</h1>
      <p className="mt-2 max-w-xl text-[var(--pl-ink-soft)]">
        This home is for {company ? <strong className="text-[var(--pl-ink)]">{company}</strong> : "your organization"}.
        Data stays in your company. Form customizations on a shared site still apply to everyone on that site.
      </p>
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {TILES.map((t) => (
          <Link
            key={t.doctype}
            to={t.to}
            className="rounded-xl border border-[var(--pl-line)] bg-white p-4 hover:border-[var(--pl-ink)]"
          >
            <div className="text-sm text-[var(--pl-ink-soft)]">{t.label}</div>
            <div className="mt-1 text-2xl font-semibold">{counts[t.doctype] ?? "…"}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
