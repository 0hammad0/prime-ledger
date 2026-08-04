import { usePortal } from "@/lib/portal";

/** Simple module page — one clear action to open the work screen. */
export function ModuleBridge({ title, hint }: { title: string; hint?: string }) {
  const { boot } = usePortal();
  const mod =
    boot?.modules.find((m) => m.label === title) || boot?.all_modules.find((m) => m.label === title);

  return (
    <div className="mx-auto max-w-xl">
      <p className="text-sm font-medium text-[var(--pl-accent)]">Next step</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-3 text-base text-[var(--pl-ink-soft)]">
        {hint || mod?.description || `Use ${title} for your daily work.`}
      </p>
      {mod?.desk_route ? (
        <a
          href={mod.desk_route}
          className="mt-8 inline-flex min-h-12 items-center justify-center rounded-xl bg-[var(--pl-accent)] px-6 text-base font-semibold text-white shadow-sm"
        >
          Open {title}
        </a>
      ) : (
        <p className="mt-6 text-sm text-[var(--pl-ink-soft)]">This section is not ready yet.</p>
      )}
      <p className="mt-6 text-sm text-[var(--pl-ink-soft)]">
        Tip: if you get stuck, press the back button or open Home from the left menu.
      </p>
    </div>
  );
}
