import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { callMethod } from "@/lib/api";
import { useHome } from "@/lib/home";
import { REPORT_PILLS } from "@/nexiscloud/MASTER";

const GROUP_REPORTS: Record<string, { name: string; label: string }[]> = {
  sales: [
    { name: "Sales Register", label: "Sales Register" },
    { name: "Accounts Receivable Summary", label: "Receivables" },
  ],
  purchase: [
    { name: "Purchase Register", label: "Purchase Register" },
    { name: "Accounts Payable Summary", label: "Payables" },
  ],
  stock: [{ name: "Stock Balance", label: "Stock Balance" }],
  accounts: [
    { name: "Profit and Loss Statement", label: "Profit and Loss" },
    { name: "Balance Sheet", label: "Balance Sheet" },
    { name: "General Ledger", label: "General Ledger" },
  ],
  tax: [{ name: "Tax Detail", label: "Tax Detail" }],
};

export function ReportsPage() {
  const { home } = useHome();
  const [params, setParams] = useSearchParams();
  const group = params.get("group") || "accounts";
  const reports = GROUP_REPORTS[group] || GROUP_REPORTS.accounts;
  const [chosen, setChosen] = useState(reports[0]?.name || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ columns?: { label: string }[]; result?: unknown[] } | null>(null);

  const pills = useMemo(() => REPORT_PILLS, []);

  const run = async (reportName: string) => {
    setChosen(reportName);
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const data = (await callMethod("erpnext.portal_control.workspace.run_named_report", {
        report_name: reportName,
        filters: { company: home?.company },
      })) as { columns?: { label: string }[]; result?: unknown[] };
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not run report");
    } finally {
      setBusy(false);
    }
  };

  const columns = (result?.columns || []).map((c) => (typeof c === "string" ? c : c.label || JSON.stringify(c)));
  const rows = Array.isArray(result?.result) ? result.result : [];

  return (
    <div>
      <h1 className="text-2xl font-semibold">Reports</h1>
      <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">
        Runs named ERPNext reports for {home?.company || "this company"}. Empty means no posted data — not fake rows.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {pills.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`rounded-full border px-4 py-2 text-sm ${
              group === p.id ? "border-[var(--pl-accent)] bg-[var(--pl-accent-soft)]" : "border-[var(--pl-line)]"
            }`}
            onClick={() => {
              setParams({ group: p.id });
              const first = GROUP_REPORTS[p.id]?.[0]?.name;
              if (first) void run(first);
            }}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {reports.map((r) => (
          <button
            key={r.name}
            type="button"
            className={`rounded-xl border px-3 py-2 text-sm ${
              chosen === r.name ? "border-[var(--pl-accent)]" : "border-[var(--pl-line)]"
            }`}
            onClick={() => void run(r.name)}
          >
            {r.label}
          </button>
        ))}
      </div>
      {busy ? <p className="mt-4 text-sm text-[var(--pl-ink-soft)]">Running…</p> : null}
      {error ? <p className="mt-4 text-sm text-[var(--pl-danger)]">{error}</p> : null}
      {rows.length ? (
        <div className="mt-6 overflow-auto rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)]">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--pl-line)] text-[var(--pl-ink-soft)]">
                {columns.map((c) => (
                  <th key={c} className="px-3 py-2 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 80).map((row, i) => {
                const cells = Array.isArray(row) ? row : Object.values(row as object);
                return (
                  <tr key={i} className="border-b border-[var(--pl-line)] last:border-0">
                    {cells.map((cell, j) => (
                      <td key={j} className="px-3 py-2">
                        {cell == null ? "—" : String(cell)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : !busy && !error && chosen ? (
        <p className="mt-6 text-sm text-[var(--pl-ink-soft)]">No rows for this report yet.</p>
      ) : null}
    </div>
  );
}

export function ModuleHubPage({
  title,
  links,
}: {
  title: string;
  links: { label: string; href: string }[];
}) {
  return (
    <div>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {links.map((l) => (
          <Link
            key={l.href}
            to={l.href}
            className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4 hover:border-[var(--pl-accent)]"
          >
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

export function BankingReconcilePage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Reconcile</h1>
      <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
        Match bank transactions to payment entries. Open bank transactions, then mark them cleared from the transaction
        list when your bank feed is connected.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Link className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4" to="/banking/transactions">
          Bank transactions
        </Link>
        <Link className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4" to="/finance/payments">
          Payment entries
        </Link>
      </div>
    </div>
  );
}
