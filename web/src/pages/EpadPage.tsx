import { useEffect, useState, type FormEvent } from "react";
import { callMethod, getList } from "@/lib/api";
import { todayIso } from "@/lib/format";

type Todo = { name: string; description?: string; status?: string; date?: string };

export function EpadPage() {
  const [rows, setRows] = useState<Todo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(todayIso());

  const load = async () => {
    setError(null);
    try {
      const list = (await getList("ToDo", ["name", "description", "status", "date"], {
        filters: { allocated_to: undefined },
        limit: 50,
        orderBy: "modified desc",
      })) as Todo[];
      setRows(Array.isArray(list) ? list : []);
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : "Could not load notes");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await callMethod("erpnext.portal_control.workspace.save_todo", { description, date });
      setDescription("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };

  const close = async (name: string) => {
    try {
      await callMethod("erpnext.portal_control.workspace.save_todo", { name, description: "", status: "Closed" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not close");
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold">ePad</h1>
      <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">
        Team notes and follow-ups. These are live ToDo records — not a separate dummy pad.
      </p>
      {error ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{error}</p> : null}
      <form onSubmit={add} className="mt-5 rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
        <textarea
          className="w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
          required
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Write a follow-up…"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <input
            className="rounded-lg border border-[var(--pl-line)] px-3 py-2"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <button type="submit" disabled={busy} className="tap rounded-xl bg-[var(--pl-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {busy ? "Saving…" : "Add note"}
          </button>
        </div>
      </form>
      <ul className="mt-6 space-y-2">
        {rows.map((r) => (
          <li key={r.name} className="flex items-start justify-between gap-3 rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-4">
            <div>
              <div className="font-medium">{r.description}</div>
              <div className="text-xs text-[var(--pl-ink-soft)]">
                {r.status} · {r.date || ""} · {r.name}
              </div>
            </div>
            {r.status !== "Closed" ? (
              <button type="button" className="text-sm text-[var(--pl-accent)] underline" onClick={() => void close(r.name)}>
                Close
              </button>
            ) : null}
          </li>
        ))}
        {!rows.length ? <li className="text-sm text-[var(--pl-ink-soft)]">No notes yet.</li> : null}
      </ul>
    </div>
  );
}
