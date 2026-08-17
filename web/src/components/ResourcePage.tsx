import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { getList, insertDoc } from "@/lib/api";
import type { Resource } from "@/lib/catalog";
import { useAuth } from "@/lib/auth";
import { LinkField } from "@/components/LinkField";

function applyMasters(extra: Record<string, unknown> | undefined, masters: Record<string, string> | undefined) {
  const doc = { ...(extra || {}) };
  const m = masters || {};
  if (doc.customer_group === "All Customer Groups" && m.customer_group) doc.customer_group = m.customer_group;
  if (doc.territory === "All Territories" && m.territory) doc.territory = m.territory;
  if (doc.item_group === "All Item Groups" && m.item_group) doc.item_group = m.item_group;
  if (doc.supplier_group === "All Supplier Groups" && m.supplier_group) doc.supplier_group = m.supplier_group;
  if (doc.stock_uom === "Nos" && m.stock_uom) doc.stock_uom = m.stock_uom;
  return doc;
}

export function ResourcePage({ resource }: { resource: Resource }) {
  const { boot } = useAuth();
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const navigate = useNavigate();
  const canCreate = Boolean(resource.createFields?.length || resource.hasItems);

  const load = async () => {
    setError(null);
    try {
      const fields = ["name", ...resource.columns.map((c) => c.key)].filter((v, i, a) => a.indexOf(v) === i);
      if (resource.submitable) fields.push("docstatus");
      const list = await getList(resource.doctype, fields, { limit: 50 });
      setRows(Array.isArray(list) ? list : []);
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : "Could not load");
    }
  };

  useEffect(() => {
    void load();
  }, [resource.doctype]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const doc: Record<string, unknown> = {
        doctype: resource.doctype,
        ...applyMasters(resource.extraDoc, boot?.masters),
      };
      for (const f of resource.createFields || []) {
        if (form[f.key]) doc[f.key] = f.type === "number" ? Number(form[f.key]) : form[f.key];
      }
      const saved = (await insertDoc(doc)) as { name?: string };
      setForm({});
      if (saved?.name) navigate(`${resource.path}/${saved.name}`);
      else await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{resource.title}</h1>
          {resource.hint ? <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">{resource.hint}</p> : null}
        </div>
        {canCreate ? (
          <Link
            to={`${resource.path}/new`}
            className="tap inline-flex items-center rounded-xl bg-[var(--pl-accent)] px-4 py-2 text-sm font-semibold text-white"
          >
            New {resource.title.replace(/s$/, "")}
          </Link>
        ) : null}
      </div>
      {error ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{error}</p> : null}

      {resource.createFields?.length && !resource.hasItems ? (
        <form onSubmit={create} className="mt-5 grid gap-3 rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4 sm:grid-cols-2">
          {resource.createFields.map((f) => (
            <label key={f.key} className="block text-sm">
              <span className="text-[var(--pl-ink-soft)]">{f.label}</span>
              {f.link ? (
                <LinkField
                  doctype={f.link}
                  value={form[f.key] || ""}
                  onChange={(v) => setForm((s) => ({ ...s, [f.key]: v }))}
                />
              ) : (
                <input
                  className="mt-1 w-full rounded-lg border border-[var(--pl-line)] bg-[var(--pl-surface)] px-3 py-2"
                  required={f.required}
                  type={f.type || "text"}
                  value={form[f.key] || ""}
                  onChange={(e) => setForm((s) => ({ ...s, [f.key]: e.target.value }))}
                />
              )}
            </label>
          ))}
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={busy}
              className="tap rounded-xl bg-[var(--pl-accent)] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      ) : null}

      <div className="mt-6 overflow-x-auto rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)]">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--pl-line)] bg-[var(--pl-paper)] text-[var(--pl-ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-medium">ID</th>
              {resource.columns.map((c) => (
                <th key={c.key} className="px-4 py-3 font-medium">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((r) => (
                <tr key={String(r.name)} className="border-b border-[var(--pl-line)] last:border-0">
                  <td className="px-4 py-3 font-medium">
                    <Link className="text-[var(--pl-accent)] underline" to={`${resource.path}/${String(r.name)}`}>
                      {String(r.name)}
                    </Link>
                  </td>
                  {resource.columns.map((c) => (
                    <td key={c.key} className="px-4 py-3">
                      {String(r[c.key] ?? "—")}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-6 text-[var(--pl-ink-soft)]" colSpan={resource.columns.length + 1}>
                  No records yet.
                  {canCreate ? (
                    <>
                      {" "}
                      <Link className="text-[var(--pl-accent)] underline" to={`${resource.path}/new`}>
                        Create one
                      </Link>
                    </>
                  ) : null}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
