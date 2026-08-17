import { useEffect, useState } from "react";
import { callMethod } from "@/lib/api";
import type { LinkOption } from "@/lib/types";

export function LinkField({
  doctype,
  value,
  onChange,
  placeholder,
}: {
  doctype: string;
  value: string;
  onChange: (name: string) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState(value);
  const [open, setOpen] = useState(false);
  const [opts, setOpts] = useState<LinkOption[]>([]);

  useEffect(() => {
    setQ(value);
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => {
      void callMethod("erpnext.portal_control.workspace.link_options", { doctype, q, limit: 12 })
        .then((rows) => setOpts(Array.isArray(rows) ? (rows as LinkOption[]) : []))
        .catch(() => setOpts([]));
    }, 180);
    return () => window.clearTimeout(t);
  }, [doctype, q, open]);

  return (
    <div className="relative">
      <input
        className="mt-1 w-full rounded-lg border border-[var(--pl-line)] bg-[var(--pl-surface)] px-3 py-2"
        value={q}
        placeholder={placeholder || `Search ${doctype}`}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQ(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 180)}
      />
      {open && opts.length ? (
        <ul className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-[var(--pl-line)] bg-[var(--pl-surface)] shadow-[var(--pl-shadow)]">
          {opts.map((o) => (
            <li key={o.name}>
              <button
                type="button"
                className="flex w-full flex-col px-3 py-2 text-left text-sm hover:bg-[var(--pl-mist)]"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange(o.name);
                  setQ(o.name);
                  setOpen(false);
                }}
              >
                <span className="font-medium">{o.label}</span>
                {o.label !== o.name ? <span className="text-xs text-[var(--pl-ink-soft)]">{o.name}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
