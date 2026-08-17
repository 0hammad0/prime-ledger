import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { callMethod } from "@/lib/api";
import { money } from "@/lib/format";
import { useHome } from "@/lib/home";

type Tax = { charge_type?: string; account_head?: string; rate: number };
type Template = { name: string; title: string; taxes: Tax[] };

export function DutyPage() {
  const { home } = useHome();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [chosen, setChosen] = useState("");
  const [base, setBase] = useState("100000");

  useEffect(() => {
    void callMethod("erpnext.portal_control.dashboard.tax_templates", home?.company ? { company: home.company } : {}, false)
      .then((rows) => {
        const list = Array.isArray(rows) ? (rows as Template[]) : [];
        setTemplates(list);
        if (list[0]) setChosen(list[0].name);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load tax templates"));
  }, [home?.company]);

  const template = templates.find((t) => t.name === chosen);
  const amount = Number(base || 0);
  const lines = useMemo(() => {
    let running = amount;
    return (template?.taxes || []).map((t) => {
      const add = (running * Number(t.rate || 0)) / 100;
      running += add;
      return { ...t, add, running };
    });
  }, [template, amount]);
  const total = lines.length ? lines[lines.length - 1].running : amount;
  const currency = home?.currency || "PKR";

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold">Duty & tax calculator</h1>
      <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">
        Rates come from Sales Taxes and Charges Template on this company. They are not invented in the browser.
      </p>
      {error ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{error}</p> : null}
      <div className="mt-5 space-y-3 rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
        <label className="block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Assessable value</span>
          <input
            className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            type="number"
            min="0"
            value={base}
            onChange={(e) => setBase(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Tax template</span>
          <select
            className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            value={chosen}
            onChange={(e) => setChosen(e.target.value)}
          >
            {templates.map((t) => (
              <option key={t.name} value={t.name}>
                {t.title}
              </option>
            ))}
            {!templates.length ? <option value="">No templates on this company</option> : null}
          </select>
        </label>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-[var(--pl-ink-soft)]">
              <th className="py-2 font-medium">Charge</th>
              <th className="py-2 font-medium">Rate</th>
              <th className="py-2 font-medium">Amount</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={i} className="border-t border-[var(--pl-line)]">
                <td className="py-2">{l.account_head || l.charge_type || "Tax"}</td>
                <td className="py-2">{l.rate}%</td>
                <td className="py-2">{money(l.add, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-lg font-semibold">Landed {money(total, currency)}</div>
      </div>
      <p className="mt-4 text-sm">
        <Link className="text-[var(--pl-accent)] underline" to="/import/data">
          Data import
        </Link>
      </p>
    </div>
  );
}

export function ImportHubPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Import & Custom</h1>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Link to="/import/data" className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
          Data Import
        </Link>
        <Link to="/import/duty" className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
          Duty & tax calculator
        </Link>
      </div>
    </div>
  );
}
