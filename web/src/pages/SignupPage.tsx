import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { callControlMethod, refreshControlCsrf } from "@/lib/api";
import { AuthFrame } from "@/pages/LoginPage";

type SignupResult = {
  host?: string;
  login_url?: string;
  message?: string;
  poll_token?: string;
  status?: string;
};

type StatusResult = {
  ready?: boolean;
  host?: string;
  message?: string;
};

export function SignupPage() {
  const [org, setOrg] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [waitHost, setWaitHost] = useState<string | null>(null);
  const [waitMsg, setWaitMsg] = useState<string | null>(null);

  const poll = async (pollToken: string) => {
    const st = (await callControlMethod("erpnext.portal_control.tenants.signup_status", {
      poll_token: pollToken,
    })) as StatusResult;
    if (st.host) setWaitHost(`https://${st.host}`);
    setWaitMsg(st.ready ? "Workspace ready. Signing you in…" : st.message || "Preparing your workspace…");
    if (!st.ready) {
      setTimeout(() => {
        void poll(pollToken).catch(() => {
          setTimeout(() => void poll(pollToken), 8000);
        });
      }, 5000);
      return;
    }
    const ticket = (await callControlMethod("erpnext.portal_control.tenants.issue_login_ticket", {
      poll_token: pollToken,
    })) as { login_url?: string };
    if (ticket.login_url) window.location.href = ticket.login_url;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await refreshControlCsrf();
      const result = (await callControlMethod("erpnext.portal_control.tenants.signup_organization", {
        organization_name: org.trim(),
        admin_full_name: name.trim(),
        admin_email: email.trim(),
        password,
      })) as SignupResult;
      setWaitHost(result.host ? `https://${result.host}` : result.login_url || null);
      setWaitMsg(result.message || "Check your email to confirm. After that we create your private URL.");
      if (result.poll_token) void poll(result.poll_token);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not create organization");
      setBusy(false);
    }
  };

  if (waitMsg) {
    return (
      <AuthFrame
        title="Check your email"
        subtitle="Open the confirmation link. After you confirm, we create your private URL and sign you in."
      >
        <div className="mt-6 rounded-2xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-5">
          <p className="text-sm text-[var(--pl-accent)]">{waitMsg}</p>
          {waitHost ? <p className="mt-3 break-all text-sm font-medium">{waitHost}</p> : null}
          <p className="mt-3 text-sm text-[var(--pl-ink-soft)]">After you confirm, keep that tab open — setup usually takes a few minutes.</p>
        </div>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame
      title="Create your organization"
      subtitle="You get a private workspace and your own login URL. We email a confirmation link first."
    >
      <form onSubmit={submit} className="mt-6 rounded-2xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-5">
        <label className="block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Organization name</span>
          <input className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2" required value={org} onChange={(e) => setOrg(e.target.value)} />
        </label>
        <label className="mt-3 block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Your full name</span>
          <input className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2" required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="mt-3 block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Work email</span>
          <input className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="mt-3 block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Password</span>
          <input className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {err ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{err}</p> : null}
        <button type="submit" disabled={busy} className="tap mt-5 w-full rounded-xl bg-[var(--pl-accent)] py-2.5 font-semibold text-white disabled:opacity-50">
          {busy ? "Submitting…" : "Create organization"}
        </button>
      </form>
      <p className="mt-4 text-sm">
        <Link className="text-[var(--pl-accent)] underline" to="/login">
          Already have an organization? Sign in
        </Link>
      </p>
    </AuthFrame>
  );
}
