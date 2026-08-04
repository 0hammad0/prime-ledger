import { usePortal } from "@/lib/portal";

/** Generic module page — bridge to desk engine screens until full portal forms exist. */
export function ModuleBridge({ title, hint }: { title: string; hint?: string }) {
  const { boot } = usePortal();
  const mod = boot?.modules.find((m) => m.label === title) ||
    boot?.all_modules.find((m) => m.label === title);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm text-[var(--pl-ink-soft)]">
        {hint ||
          mod?.description ||
          "This module uses the Prime Ledger engine. Open the operational screen to continue."}
      </p>
      {mod?.desk_route ? (
        <a
          href={mod.desk_route}
          className="mt-6 inline-flex rounded-lg bg-[var(--pl-ink)] px-4 py-2 text-sm text-[var(--pl-paper)]"
        >
          Open {title}
        </a>
      ) : null}
      <p className="mt-6 text-xs text-[var(--pl-ink-soft)]">
        Next phases will embed printing, email, and user controls inside the portal. The backend
        documents stay the same.
      </p>
    </div>
  );
}
