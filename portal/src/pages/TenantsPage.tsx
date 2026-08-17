import { useState } from "react";
import { usePortal } from "@/lib/portal";
import type { PortalTenant } from "@/lib/types";

type ActionKind = "approve" | "reject" | "block";

function csrf() {
  return window.csrf_token || "";
}

async function postMethod(method: string, body: Record<string, string>) {
  const res = await fetch(`/api/method/${method}`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Frappe-CSRF-Token": csrf(),
    },
    body: new URLSearchParams(body),
  });
  const data = await res.json();
  if (data.exc_type || data.exception) {
    throw new Error(data._error_message || data.exception || "Request failed");
  }
  return data.message;
}

export function TenantsPage() {
  const { boot, refresh } = usePortal();
  const [orgName, setOrgName] = useState("");
  const [siteName, setSiteName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [acting, setActing] = useState<{ slug: string; kind: ActionKind } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  if (!boot) return null;

  if (!boot.is_super_admin) {
    return <div className="p-6">Access restricted</div>;
  }

  const tenants: PortalTenant[] = boot.tenants || [];
  const queue = tenants.filter((t) =>
    ["Pending", "Approved", "Provisioning", "Error"].includes(t.status),
  );
  const anyActing = acting != null;
  const slugOf = (t: PortalTenant) => t.site_name || t.name;
  const labelFor = (slug: string, kind: ActionKind, idle: string, busyLabel: string) =>
    acting?.slug === slug && acting.kind === kind ? busyLabel : idle;

  const register = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const result = await postMethod("erpnext.portal_control.tenants.register_tenant", {
        organization_name: orgName.trim(),
        ...(siteName.trim() ? { site_name: siteName.trim().toLowerCase() } : {}),
        ...(adminEmail.trim() ? { admin_email: adminEmail.trim() } : {}),
      });
      setMsg(`Registered ${result?.site_name}. It stays Pending until you Approve.`);
      setOrgName("");
      setSiteName("");
      setAdminEmail("");
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Register failed");
    } finally {
      setBusy(false);
    }
  };

  const approve = async (slug: string) => {
    setActing({ slug, kind: "approve" });
    setMsg(null);
    try {
      const result = await postMethod("erpnext.portal_control.tenants.approve_tenant", {
        site_name: slug,
      });
      const emailed = result?.email?.queued
        ? " Invite email queued."
        : " Invite email not queued (check Email Queue / SMTP).";
      setMsg(
        `Approved ${result?.site_name}. Login URL: ${result?.login_url}.${emailed} ` +
          "The server will create the private site automatically (usually a few minutes).",
      );
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setActing(null);
    }
  };

  const reject = async (slug: string) => {
    if (
      !window.confirm(
        "Reject this request? It will be archived. The reserved URL will not be provisioned.",
      )
    ) {
      return;
    }
    setActing({ slug, kind: "reject" });
    setMsg(null);
    try {
      const result = await postMethod("erpnext.portal_control.tenants.reject_tenant", {
        site_name: slug,
      });
      setMsg(`Rejected ${result?.site_name}. Status is Archived.`);
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Reject failed");
    } finally {
      setActing(null);
    }
  };

  const block = async (slug: string) => {
    if (
      !window.confirm(
        "Block this organization? It will be archived. The tenant database is not dropped. The URL may still work until routing is refreshed.",
      )
    ) {
      return;
    }
    setActing({ slug, kind: "block" });
    setMsg(null);
    try {
      const result = await postMethod("erpnext.portal_control.tenants.block_tenant", {
        site_name: slug,
      });
      setMsg(
        `Blocked ${result?.site_name}. Status is Archived. Then: ${result?.routing_hint || "bash deploy/ec2/refresh-tenant-routing.sh"}`,
      );
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Block failed");
    } finally {
      setActing(null);
    }
  };

  const actions = (t: PortalTenant, compact = false) => {
    const slug = slugOf(t);
    const canApproveReject = t.status === "Pending" || t.status === "Error";
    const canBlock = t.status === "Active" || t.status === "Approved" || t.status === "Provisioning";
    if (!canApproveReject && !canBlock) {
      return compact ? (
        <span className="text-sm text-[var(--pl-ink-soft)]">Waiting on provision</span>
      ) : null;
    }
    return (
      <div className="flex flex-wrap items-center gap-2">
        {canApproveReject ? (
          <>
            <button
              type="button"
              disabled={anyActing}
              onClick={() => void approve(slug)}
              className={
                compact
                  ? "inline-flex min-h-10 items-center rounded-xl bg-[var(--pl-accent)] px-4 text-sm font-semibold text-white disabled:opacity-50"
                  : "font-medium text-[var(--pl-accent)] underline disabled:opacity-50"
              }
            >
              {labelFor(slug, "approve", compact ? "Approve & send invite" : "Approve", "Approving…")}
            </button>
            <button
              type="button"
              disabled={anyActing}
              onClick={() => void reject(slug)}
              className={
                compact
                  ? "inline-flex min-h-10 items-center rounded-xl border border-[var(--pl-line)] bg-white px-4 text-sm font-semibold disabled:opacity-50"
                  : "font-medium underline disabled:opacity-50"
              }
            >
              {labelFor(slug, "reject", "Reject", "Rejecting…")}
            </button>
          </>
        ) : null}
        {canBlock ? (
          <>
            {compact && t.status !== "Active" ? (
              <span className="text-sm text-[var(--pl-ink-soft)]">Creating site automatically…</span>
            ) : null}
            <button
              type="button"
              disabled={anyActing}
              onClick={() => void block(slug)}
              className={
                compact
                  ? "inline-flex min-h-10 items-center rounded-xl border border-[var(--pl-line)] bg-white px-4 text-sm font-semibold disabled:opacity-50"
                  : "font-medium underline disabled:opacity-50"
              }
            >
              {labelFor(slug, "block", "Block", "Blocking…")}
            </button>
          </>
        ) : null}
      </div>
    );
  };

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Organizations</h1>
        <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
          Signup reserves a private URL. Approve emails that URL and the server creates the private
          site automatically (usually a few minutes). This owner panel does not show tenant books.
        </p>
      </header>

      {queue.length ? (
        <section className="mb-6 rounded-xl border border-[var(--pl-accent)]/40 bg-[var(--pl-paper)] p-4">
          <h2 className="text-sm font-semibold">Needs you ({queue.length})</h2>
          <ul className="mt-3 space-y-3">
            {queue.map((t) => (
              <li
                key={t.name}
                className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-[var(--pl-line)] bg-white p-3"
              >
                <div className="text-sm">
                  <div className="font-medium text-[var(--pl-ink)]">{t.organization_name}</div>
                  <div className="text-[var(--pl-ink-soft)]">
                    {t.admin_email || "no email"} · {t.status}
                  </div>
                  <div className="mt-1 text-[var(--pl-ink-soft)]">
                    {t.host ? `https://${t.host}/login` : "URL reserved at signup; emailed on approve"}
                  </div>
                </div>
                {actions(t, true)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mb-8 rounded-xl border border-[var(--pl-line)] bg-white p-5">
        <h2 className="text-base font-semibold">Register organization (admin)</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-[var(--pl-ink-soft)]">Organization name</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Sultan Group"
            />
          </label>
          <label className="block text-sm">
            <span className="text-[var(--pl-ink-soft)]">Site slug (optional)</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
              value={siteName}
              onChange={(e) => setSiteName(e.target.value)}
              placeholder="sultan"
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="text-[var(--pl-ink-soft)]">Org admin email (optional)</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--pl-line)] px-3 py-2"
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
              placeholder="owner@company.com"
            />
          </label>
        </div>
        <button
          type="button"
          disabled={busy || !orgName.trim()}
          onClick={() => void register()}
          className="mt-4 inline-flex min-h-11 items-center justify-center rounded-xl bg-[var(--pl-accent)] px-5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Saving…" : "Register as Pending"}
        </button>
        {msg ? <p className="mt-3 text-sm text-[var(--pl-ink-soft)]">{msg}</p> : null}
      </section>

      <div className="overflow-hidden rounded-xl border border-[var(--pl-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--pl-line)] bg-[var(--pl-paper)] text-[var(--pl-ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-medium">Organization</th>
              <th className="px-4 py-3 font-medium">Site</th>
              <th className="px-4 py-3 font-medium">Admin</th>
              <th className="px-4 py-3 font-medium">Host</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium"> </th>
            </tr>
          </thead>
          <tbody>
            {tenants.length ? (
              tenants.map((t) => (
                <tr key={t.name} className="border-b border-[var(--pl-line)] last:border-0">
                  <td className="px-4 py-3 font-medium">{t.organization_name}</td>
                  <td className="px-4 py-3">{t.site_name}</td>
                  <td className="px-4 py-3">{t.admin_email || "—"}</td>
                  <td className="px-4 py-3">
                    {t.host ? (
                      <a className="underline" href={`https://${t.host}/login`} target="_blank" rel="noreferrer">
                        {t.host}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3">{t.status}</td>
                  <td className="px-4 py-3">{actions(t)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-6 text-[var(--pl-ink-soft)]" colSpan={6}>
                  No tenant sites yet. Public requests appear after someone uses /start.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
