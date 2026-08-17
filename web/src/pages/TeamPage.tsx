import { useEffect, useState, type FormEvent } from "react";
import { callMethod, getList, insertDoc } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type UserRow = { name: string; full_name?: string; email?: string; enabled?: number; user_type?: string };

export function TeamPage() {
  const { boot } = useAuth();
  const [rows, setRows] = useState<UserRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const company = boot?.companies[0]?.name;

  const load = async () => {
    setError(null);
    try {
      const list = (await getList("User", ["name", "full_name", "email", "enabled", "user_type"], {
        filters: { enabled: 1 },
        limit: 80,
        orderBy: "full_name asc",
      })) as UserRow[];
      setRows(
        (Array.isArray(list) ? list : []).filter(
          (u) => u.name !== "Guest" && u.name !== "Administrator" && u.user_type !== "Website User",
        ),
      );
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : "Could not load users");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const invite = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const parts = fullName.trim().split(/\s+/);
      await insertDoc({
        doctype: "User",
        email: email.trim(),
        first_name: parts[0] || email.trim(),
        last_name: parts.slice(1).join(" ") || undefined,
        send_welcome_email: 0,
        new_password: password,
        role_profile_name: "Prime Ledger User",
      });
      if (company) {
        if (boot?.is_super_admin) {
          await callMethod("erpnext.portal_control.tenancy.bind_user_company", {
            user: email.trim(),
            company,
          });
        } else {
          await insertDoc({
            doctype: "User Permission",
            user: email.trim(),
            allow: "Company",
            for_value: company,
            apply_to_all_doctypes: 1,
          });
        }
      }
      setEmail("");
      setFullName("");
      setPassword("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add user");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold">Team</h1>
      <p className="mt-1 text-sm text-[var(--pl-ink-soft)]">
        People in this organization. They sign in here — they are not added to a shared pool.
        {company ? (
          <>
            {" "}
            New users are limited to <strong>{company}</strong>.
          </>
        ) : null}
      </p>
      {error ? <p className="mt-3 text-sm text-red-800">{error}</p> : null}

      <form onSubmit={invite} className="mt-5 grid gap-3 rounded-xl border border-[var(--pl-line)] bg-white p-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Full name</span>
          <input
            className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Email</span>
          <input
            className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm sm:col-span-2">
          <span className="text-[var(--pl-ink-soft)]">Temporary password</span>
          <input
            className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded-xl bg-[var(--pl-accent)] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Adding…" : "Add team member"}
          </button>
        </div>
      </form>

      <div className="mt-6 overflow-hidden rounded-xl border border-[var(--pl-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--pl-line)] bg-[var(--pl-paper)] text-[var(--pl-ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Email</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((u) => (
                <tr key={u.name} className="border-b border-[var(--pl-line)] last:border-0">
                  <td className="px-4 py-3 font-medium">{u.full_name || u.name}</td>
                  <td className="px-4 py-3">{u.email || u.name}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-6 text-[var(--pl-ink-soft)]" colSpan={2}>
                  No team members listed.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
