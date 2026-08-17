import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useSearchParams } from "react-router";
import { callControlMethod, callMethod, refreshControlCsrf, refreshGuestCsrf } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isTenantHost } from "@/lib/host";

type ResolveResult = {
  found?: boolean;
  ready?: boolean;
  host?: string;
  login_url?: string;
  message?: string;
};

export function LoginPage() {
  const { boot, loading, signIn } = useAuth();
  const [params] = useSearchParams();
  const [usr, setUsr] = useState(params.get("email") || "");
  const [pwd, setPwd] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ticketBusy, setTicketBusy] = useState(Boolean(params.get("ticket")));

  useEffect(() => {
    const ticket = params.get("ticket");
    if (!ticket) return;
    let cancelled = false;
    void (async () => {
      try {
        await refreshGuestCsrf();
        const result = (await callMethod("erpnext.portal_control.tenants.login_with_ticket", {
          ticket,
        })) as { redirect_to?: string };
        if (!cancelled) {
          window.location.href = result.redirect_to || "/";
        }
      } catch (err) {
        if (!cancelled) {
          setTicketBusy(false);
          setError(err instanceof Error ? err.message : "Sign-in link expired. Use your email and password.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params]);

  if (!loading && boot) return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const email = usr.trim();
      if (!isTenantHost()) {
        try {
          await refreshControlCsrf();
          const resolved = (await callControlMethod("erpnext.portal_control.tenants.resolve_workspace", {
            email,
          })) as ResolveResult;
          if (resolved?.found) {
            if (resolved.ready && resolved.host && resolved.host !== window.location.hostname) {
              window.location.href = `https://${resolved.host}/login?email=${encodeURIComponent(email)}`;
              return;
            }
            if (!resolved.ready) {
              setInfo(resolved.message || "Your workspace is still being prepared.");
              return;
            }
          }
        } catch {
          // Apex lookup failed — try signing in on this host.
        }
      }
      await signIn(email, pwd);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  };

  if (ticketBusy) {
    return (
      <AuthFrame title="Signing you in" subtitle="Taking you into your private workspace.">
        <p className="mt-6 text-sm text-[var(--pl-ink-soft)]">One moment…</p>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame
      title="Sign in"
      subtitle={
        isTenantHost()
          ? "This URL is only for your organization."
          : "Enter the email you signed up with. We'll send you to your organization's private URL."
      }
    >
      <form onSubmit={submit} className="mt-6 rounded-2xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-5">
        <label className="block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Email</span>
          <input
            className="tap mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            type="email"
            autoComplete="username"
            value={usr}
            onChange={(e) => setUsr(e.target.value)}
            required
          />
        </label>
        <label className="mt-3 block text-sm">
          <span className="text-[var(--pl-ink-soft)]">Password</span>
          <input
            className="tap mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
            type="password"
            autoComplete="current-password"
            value={pwd}
            onChange={(e) => setPwd(e.target.value)}
            required
          />
        </label>
        {error ? <p className="mt-3 text-sm text-[var(--pl-danger)]">{error}</p> : null}
        {info ? <p className="mt-3 text-sm text-[var(--pl-accent)]">{info}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="tap mt-5 w-full rounded-xl bg-[var(--pl-accent)] py-2.5 font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-4 flex justify-between text-sm text-[var(--pl-ink-soft)]">
        <Link className="text-[var(--pl-accent)] underline" to="/forgot">
          Forgot password
        </Link>
        <Link className="text-[var(--pl-accent)] underline" to="/signup">
          Create organization
        </Link>
      </p>
    </AuthFrame>
  );
}

export function AuthFrame({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center px-4 py-10">
      <p className="text-xs tracking-[0.16em] text-[var(--pl-accent)] uppercase">Prime Ledger</p>
      <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">{subtitle}</p>
      {children}
    </div>
  );
}
