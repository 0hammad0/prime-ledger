import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { callMethod, refreshGuestCsrf } from "@/lib/api";
import { AuthFrame } from "@/pages/LoginPage";

export function ForgotPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      await refreshGuestCsrf();
      const result = (await callMethod("erpnext.portal_control.auth.request_password_reset", {
        email: email.trim(),
      })) as { message?: string };
      setMsg(result.message || "If that account exists, we sent a reset link.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not send reset email");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFrame
      title="Forgot password"
      subtitle="We email a reset link to this organization's login host. The message is the same whether the account exists."
    >
      <form onSubmit={submit} className="mt-6 rounded-2xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-5">
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
        {err ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{err}</p> : null}
        {msg ? <p className="mt-3 text-sm text-[var(--pl-accent)]">{msg}</p> : null}
        <button type="submit" disabled={busy} className="tap mt-5 w-full rounded-xl bg-[var(--pl-accent)] py-2.5 font-semibold text-white disabled:opacity-50">
          {busy ? "Sending…" : "Send reset link"}
        </button>
      </form>
      <p className="mt-4 text-sm">
        <Link className="text-[var(--pl-accent)] underline" to="/login">
          Back to sign in
        </Link>
      </p>
    </AuthFrame>
  );
}

export function ResetPage() {
  const [params] = useSearchParams();
  const key = params.get("key") || "";
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      await refreshGuestCsrf();
      const result = (await callMethod("erpnext.portal_control.auth.complete_password_reset", {
        key,
        new_password: password,
      })) as { message?: string };
      setMsg(result.message || "Password updated.");
      setPassword("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not update password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFrame title="Set a new password" subtitle="Use the key from your reset email. After it succeeds, sign in with the new password.">
      <form onSubmit={submit} className="mt-6 rounded-2xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-5">
        {!key ? <p className="mb-3 text-sm text-[var(--pl-ink-soft)]">Missing reset key. Open the link from the email, or paste the key below.</p> : null}
        <label className="block text-sm">
          <span className="text-[var(--pl-ink-soft)]">New password</span>
          <input
            className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {err ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{err}</p> : null}
        {msg ? <p className="mt-3 text-sm text-[var(--pl-accent)]">{msg}</p> : null}
        <button type="submit" disabled={busy || !key} className="tap mt-5 w-full rounded-xl bg-[var(--pl-accent)] py-2.5 font-semibold text-white disabled:opacity-50">
          {busy ? "Updating…" : "Update password"}
        </button>
      </form>
      <p className="mt-4 text-sm">
        <Link className="text-[var(--pl-accent)] underline" to="/login">
          Sign in
        </Link>
      </p>
    </AuthFrame>
  );
}
