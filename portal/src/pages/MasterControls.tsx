import { useState } from "react";
import { setModuleEnabled, usePortal } from "@/lib/portal";

export function MasterControls() {
  const { boot, refresh } = usePortal();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (!boot) return null;

  if (!boot.is_super_admin) {
    return (
      <div className="rounded-xl border border-[var(--pl-line)] bg-white p-6">
        <h1 className="text-xl font-semibold">Access restricted</h1>
        <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">Only Super Admin can change master controls.</p>
      </div>
    );
  }

  const toggle = async (moduleKey: string, enabled: boolean) => {
    setBusy(moduleKey);
    setMessage(null);
    try {
      await setModuleEnabled(moduleKey, enabled);
      await refresh();
      setMessage(`Updated ${moduleKey}`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Master Controls</h1>
        <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
          Enable or disable portal modules. Disabled modules disappear from the Tenant sidebar.
          Super Admin modules stay available to platform operators.
        </p>
      </header>

      {message ? (
        <div className="mb-4 rounded-lg border border-[var(--pl-line)] bg-[var(--pl-mist)] px-3 py-2 text-sm">
          {message}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-[var(--pl-line)] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--pl-line)] bg-[var(--pl-paper)] text-[var(--pl-ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-medium">Module</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Visible</th>
            </tr>
          </thead>
          <tbody>
            {boot.all_modules.map((m) => (
              <tr key={m.module_key} className="border-b border-[var(--pl-line)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium">{m.label}</div>
                  <div className="text-xs text-[var(--pl-ink-soft)]">{m.description}</div>
                </td>
                <td className="px-4 py-3 text-[var(--pl-ink-soft)]">{m.category}</td>
                <td className="px-4 py-3">
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={!!m.enabled}
                      disabled={busy === m.module_key}
                      onChange={(e) => void toggle(m.module_key, e.target.checked)}
                    />
                    <span>{m.enabled ? "On" : "Off"}</span>
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
