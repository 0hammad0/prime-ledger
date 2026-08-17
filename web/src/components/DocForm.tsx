import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { callMethod, getDoc } from "@/lib/api";
import type { Resource } from "@/lib/catalog";
import { todayIso } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import { LinkField } from "@/components/LinkField";

type ItemLine = { item_code: string; qty: string; rate: string };

const emptyLine = (): ItemLine => ({ item_code: "", qty: "1", rate: "0" });

export function DocForm({ resource }: { resource: Resource }) {
  const { name } = useParams();
  const isNew = !name || name === "new";
  const navigate = useNavigate();
  const { boot } = useAuth();
  const company = boot?.default_company || boot?.companies[0]?.name;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [doc, setDoc] = useState<Record<string, unknown> | null>(null);
  const [party, setParty] = useState("");
  const [paymentType, setPaymentType] = useState("Receive");
  const [amount, setAmount] = useState("");
  const [lines, setLines] = useState<ItemLine[]>([emptyLine()]);
  const [fields, setFields] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isNew) {
      setDoc(null);
      setParty("");
      setLines([emptyLine()]);
      setFields({});
      return;
    }
    void (async () => {
      setError(null);
      try {
        const next = (await getDoc(resource.doctype, name)) as Record<string, unknown>;
        setDoc(next);
        if (resource.partyField) setParty(String(next[resource.partyField] || ""));
        const items = (next.items as Array<Record<string, unknown>> | undefined) || [];
        if (items.length) {
          setLines(
            items.map((it) => ({
              item_code: String(it.item_code || ""),
              qty: String(it.qty ?? "1"),
              rate: String(it.rate ?? "0"),
            })),
          );
        }
        await callMethod("erpnext.portal_control.dashboard.record_open", {
          doctype: resource.doctype,
          name,
          title: String(next[resource.partyField || "name"] || name),
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load");
      }
    })();
  }, [resource.doctype, name, isNew]);

  const save = async (submit: boolean) => {
    setBusy(true);
    setError(null);
    try {
      if (!isNew && doc?.name) {
        if (submit) {
          await callMethod("erpnext.portal_control.workspace.submit_document", {
            doctype: resource.doctype,
            name: doc.name,
          });
        }
        const next = (await getDoc(resource.doctype, String(doc.name))) as Record<string, unknown>;
        setDoc(next);
        return;
      }

      if (resource.doctype === "Payment Entry") {
        const saved = (await callMethod("erpnext.portal_control.workspace.quick_create", {
          doctype: "Payment Entry",
          party,
          company,
          extra: {
            payment_type: paymentType,
            party_type: paymentType === "Receive" ? "Customer" : "Supplier",
            paid_amount: Number(amount || 0),
          },
          submit: submit ? 1 : 0,
        })) as { name: string };
        navigate(`${resource.path}/${saved.name}`, { replace: true });
        return;
      }

      if (resource.hasItems) {
        const items = lines
          .filter((l) => l.item_code)
          .map((l) => ({ item_code: l.item_code, qty: Number(l.qty || 1), rate: Number(l.rate || 0) }));
        if (!items.length) throw new Error("Add at least one item");
        const extra: Record<string, unknown> = { ...(resource.extraDoc || {}), company };
        const saved = (await callMethod("erpnext.portal_control.workspace.quick_create", {
          doctype: resource.doctype,
          party: party || undefined,
          items,
          company,
          extra,
          submit: submit ? 1 : 0,
        })) as { name: string };
        navigate(`${resource.path}/${saved.name}`, { replace: true });
        return;
      }

      const extra: Record<string, unknown> = { ...(resource.extraDoc || {}), ...fields, company };
      const saved = (await callMethod("erpnext.portal_control.workspace.quick_create", {
        doctype: resource.doctype,
        party: party || extra[resource.partyField || ""] || undefined,
        company,
        extra,
        submit: submit ? 1 : 0,
      })) as { name: string };
      navigate(`${resource.path}/${saved.name}`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void save(false);
  };

  const cancel = async () => {
    if (!doc?.name) return;
    if (!window.confirm("Cancel this document? This cannot be undone from here.")) return;
    setBusy(true);
    setError(null);
    try {
      await callMethod("erpnext.portal_control.workspace.cancel_document", {
        doctype: resource.doctype,
        name: doc.name,
      });
      const next = (await getDoc(resource.doctype, String(doc.name))) as Record<string, unknown>;
      setDoc(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not cancel");
    } finally {
      setBusy(false);
    }
  };

  const status = Number(doc?.docstatus ?? 0);

  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm">
        <Link className="text-[var(--pl-accent)] underline" to={resource.path}>
          ← {resource.title}
        </Link>
      </p>
      <h1 className="mt-2 text-2xl font-semibold">
        {isNew ? `New ${resource.title.replace(/s$/, "")}` : String(doc?.name || name)}
      </h1>
      {doc ? (
        <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">
          Status: {status === 1 ? "Submitted" : status === 2 ? "Cancelled" : "Draft"}
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{error}</p> : null}

      <form onSubmit={onSubmit} className="mt-5 space-y-4 rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-5">
        {resource.doctype === "Payment Entry" ? (
          <>
            <label className="block text-sm">
              <span className="text-[var(--pl-ink-soft)]">Type</span>
              <select
                className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
                value={paymentType}
                onChange={(e) => setPaymentType(e.target.value)}
                disabled={!isNew}
              >
                <option>Receive</option>
                <option>Pay</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-[var(--pl-ink-soft)]">{paymentType === "Receive" ? "Customer" : "Supplier"}</span>
              <LinkField
                doctype={paymentType === "Receive" ? "Customer" : "Supplier"}
                value={party}
                onChange={setParty}
              />
            </label>
            <label className="block text-sm">
              <span className="text-[var(--pl-ink-soft)]">Amount</span>
              <input
                className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
                type="number"
                min="0"
                step="0.01"
                value={isNew ? amount : String(doc?.paid_amount ?? "")}
                onChange={(e) => setAmount(e.target.value)}
                disabled={!isNew}
                required={isNew}
              />
            </label>
          </>
        ) : null}

        {resource.partyDoctype && resource.doctype !== "Payment Entry" ? (
          <label className="block text-sm">
            <span className="text-[var(--pl-ink-soft)]">{resource.partyDoctype}</span>
            <LinkField doctype={resource.partyDoctype} value={party} onChange={setParty} />
          </label>
        ) : null}

        {resource.hasItems ? (
          <div>
            <div className="mb-2 text-sm font-medium">Items</div>
            <div className="space-y-2">
              {lines.map((line, i) => (
                <div key={i} className="grid grid-cols-1 gap-2 sm:grid-cols-12">
                  <div className="sm:col-span-6">
                    <LinkField
                      doctype="Item"
                      value={line.item_code}
                      onChange={(v) =>
                        setLines((rows) => rows.map((r, idx) => (idx === i ? { ...r, item_code: v } : r)))
                      }
                    />
                  </div>
                  <input
                    className="rounded-lg border border-[var(--pl-line)] px-2 py-2 sm:col-span-2"
                    type="number"
                    min="0"
                    value={line.qty}
                    disabled={!isNew}
                    onChange={(e) =>
                      setLines((rows) => rows.map((r, idx) => (idx === i ? { ...r, qty: e.target.value } : r)))
                    }
                  />
                  <input
                    className="rounded-lg border border-[var(--pl-line)] px-2 py-2 sm:col-span-3"
                    type="number"
                    min="0"
                    step="0.01"
                    value={line.rate}
                    disabled={!isNew}
                    onChange={(e) =>
                      setLines((rows) => rows.map((r, idx) => (idx === i ? { ...r, rate: e.target.value } : r)))
                    }
                  />
                  {isNew ? (
                    <button
                      type="button"
                      className="tap col-span-1 text-sm text-[var(--pl-danger)] sm:col-span-1"
                      onClick={() => setLines((rows) => rows.filter((_, idx) => idx !== i))}
                    >
                      ×
                    </button>
                  ) : (
                    <span className="col-span-1" />
                  )}
                </div>
              ))}
            </div>
            {isNew ? (
              <button
                type="button"
                className="mt-2 text-sm font-medium text-[var(--pl-accent)] underline"
                onClick={() => setLines((rows) => [...rows, emptyLine()])}
              >
                Add row
              </button>
            ) : null}
          </div>
        ) : null}

        {!resource.hasItems && resource.doctype !== "Payment Entry"
          ? (resource.createFields || []).map((f) => (
              <label key={f.key} className="block text-sm">
                <span className="text-[var(--pl-ink-soft)]">{f.label}</span>
                {f.link ? (
                  <LinkField
                    doctype={f.link}
                    value={fields[f.key] || String(doc?.[f.key] ?? "")}
                    onChange={(v) => setFields((s) => ({ ...s, [f.key]: v }))}
                  />
                ) : (
                  <input
                    className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
                    type={f.type || "text"}
                    required={f.required && isNew}
                    value={fields[f.key] ?? (isNew && f.type === "date" ? todayIso() : String(doc?.[f.key] ?? fields[f.key] ?? ""))}
                    disabled={!isNew}
                    onChange={(e) => setFields((s) => ({ ...s, [f.key]: e.target.value }))}
                  />
                )}
              </label>
            ))
          : null}

        <div className="flex flex-wrap gap-2 pt-2">
          {isNew ? (
            <>
              <button
                type="submit"
                disabled={busy}
                className="tap rounded-xl border border-[var(--pl-line)] px-4 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {busy ? "Saving…" : "Save draft"}
              </button>
              {resource.submitable ? (
                <button
                  type="button"
                  disabled={busy}
                  className="tap rounded-xl bg-[var(--pl-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  onClick={() => void save(true)}
                >
                  Save and submit
                </button>
              ) : null}
            </>
          ) : (
            <>
              {resource.submitable && status === 0 ? (
                <button
                  type="button"
                  disabled={busy}
                  className="tap rounded-xl bg-[var(--pl-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  onClick={() => void save(true)}
                >
                  Submit
                </button>
              ) : null}
              {resource.submitable && status === 1 ? (
                <button
                  type="button"
                  disabled={busy}
                  className="tap rounded-xl border border-[var(--pl-danger)] px-4 py-2 text-sm font-semibold text-[var(--pl-danger)] disabled:opacity-50"
                  onClick={() => void cancel()}
                >
                  Cancel
                </button>
              ) : null}
            </>
          )}
        </div>
      </form>
    </div>
  );
}
