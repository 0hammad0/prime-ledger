import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { callMethod } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { HomeProvider, useHome } from "@/lib/home";
import { NAV_ITEMS, THEME } from "@/nexiscloud/MASTER";
import type { IconName } from "@/components/Icon";
import { Icon } from "@/components/Icon";
import type { SearchHit } from "@/lib/types";

function applyTheme(theme: "light" | "dark") {
  document.documentElement.dataset.theme = theme === "dark" ? "dark" : "";
  localStorage.setItem("pl-theme", theme);
}

export function Shell() {
  return (
    <HomeProvider>
      <ShellFrame />
    </HomeProvider>
  );
}

function ShellFrame() {
  const { boot, signOut } = useAuth();
  const { home, setCompanyName, reload } = useHome();
  const navigate = useNavigate();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [showInactive, setShowInactive] = useState(() => localStorage.getItem("pl-show-inactive") === "1");
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    localStorage.getItem("pl-theme") === "dark" ? "dark" : "light",
  );
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
      if (e.key === "Escape") {
        setSearchOpen(false);
        setNotesOpen(false);
        setNavOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setNavOpen(false);
    setSearchOpen(false);
    setNotesOpen(false);
    setProfileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!searchOpen || q.trim().length < 2) {
      setHits([]);
      return;
    }
    const t = window.setTimeout(() => {
      void callMethod("erpnext.portal_control.dashboard.search", { q: q.trim() })
        .then((rows) => setHits(Array.isArray(rows) ? (rows as SearchHit[]) : []))
        .catch(() => setHits([]));
    }, 200);
    return () => window.clearTimeout(t);
  }, [q, searchOpen]);

  const enabledKeys = useMemo(() => {
    const src = showInactive ? boot?.all_modules || [] : boot?.modules || [];
    return new Set(src.filter((m) => (showInactive ? true : m.enabled)).map((m) => m.module_key));
  }, [boot, showInactive]);

  const nav = useMemo(() => {
    if (!boot) return [];
    return NAV_ITEMS.filter((item) => {
      if (item.superAdminOnly && !boot.is_super_admin) return false;
      const key = item.portalModuleKey || item.id;
      if (enabledKeys.has(key) || enabledKeys.has(item.id)) return true;
      if (!item.portalModuleKey && !boot.all_modules.some((m) => m.module_key === item.id)) return true;
      return showInactive;
    }).map((item) => {
      const key = item.portalModuleKey || item.id;
      const row = boot.all_modules.find((m) => m.module_key === key);
      const locked = Boolean(item.locked || (row && !row.enabled));
      return { ...item, locked };
    });
  }, [boot, enabledKeys, showInactive]);

  if (!boot) return null;

  const company = boot.default_company || boot.companies[0]?.name || "";
  const unread = home?.unread_notifications || 0;
  const support = boot.settings.support_email;

  return (
    <div className="flex min-h-full" style={{ fontFamily: THEME.font }}>
      {navOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          aria-label="Close menu"
          onClick={() => setNavOpen(false)}
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[232px] flex-col border-r border-[var(--pl-line)] bg-[var(--pl-sidebar)] transition-transform lg:static lg:translate-x-0 ${
          navOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="border-b border-[var(--pl-line)] px-4 py-5">
          <div className="text-[11px] font-semibold tracking-[0.16em] text-[var(--pl-accent)] uppercase">
            {boot.app_name}
          </div>
          <div className="mt-1 text-lg font-semibold">{company || "Your organization"}</div>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {nav.map((item) => (
            <NavLink
              key={item.id}
              to={item.locked ? `${item.href}?locked=1` : item.href}
              end={item.href === "/"}
              className={({ isActive }) =>
                `tap flex items-center gap-3 rounded-lg px-3 text-sm ${
                  isActive
                    ? "bg-[var(--pl-accent)] text-white"
                    : "text-[var(--pl-ink)] hover:bg-[var(--pl-mist)]"
                }`
              }
            >
              <Icon name={item.icon as IconName} className="h-4 w-4 shrink-0" />
              <span className="flex-1 truncate">{item.label}</span>
              {item.locked ? <Icon name="lock" className="h-3.5 w-3.5 opacity-70" /> : null}
            </NavLink>
          ))}
          {boot.is_super_admin ? (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `tap mt-3 flex items-center gap-3 rounded-lg px-3 text-sm ${
                  isActive ? "bg-[var(--pl-ink)] text-white" : "hover:bg-[var(--pl-mist)]"
                }`
              }
            >
              <Icon name="settings" className="h-4 w-4" />
              Owner console
            </NavLink>
          ) : null}
        </nav>
        <label className="flex items-center gap-2 border-t border-[var(--pl-line)] px-4 py-3 text-xs text-[var(--pl-ink-soft)]">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => {
              setShowInactive(e.target.checked);
              localStorage.setItem("pl-show-inactive", e.target.checked ? "1" : "0");
            }}
          />
          Show inactive
        </label>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex min-h-16 flex-wrap items-center gap-2 border-b border-[var(--pl-line)] bg-[var(--pl-header)] px-3 py-2 md:px-5">
          <button
            type="button"
            className="tap grid w-11 place-items-center rounded-lg hover:bg-[var(--pl-mist)] lg:hidden"
            onClick={() => setNavOpen(true)}
            aria-label="Open menu"
          >
            <Icon name="menu" />
          </button>
          <select
            className="tap max-w-[220px] rounded-lg border border-[var(--pl-line)] bg-[var(--pl-surface)] px-2 text-sm"
            value={company}
            onChange={(e) => void setCompanyName(e.target.value)}
            aria-label="Company"
          >
            {boot.companies.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
            {!boot.companies.length ? <option value="">No company</option> : null}
          </select>
          <button
            type="button"
            className="tap ml-auto hidden min-w-[220px] items-center gap-2 rounded-xl border border-[var(--pl-line)] bg-[var(--pl-paper)] px-3 text-left text-sm text-[var(--pl-ink-soft)] md:flex"
            onClick={() => setSearchOpen(true)}
          >
            <Icon name="search" className="h-4 w-4" />
            Search
            <kbd className="ml-auto rounded border border-[var(--pl-line)] px-1.5 text-[10px]">Ctrl K</kbd>
          </button>
          <button
            type="button"
            className="tap grid w-11 place-items-center rounded-lg hover:bg-[var(--pl-mist)] md:hidden"
            onClick={() => setSearchOpen(true)}
            aria-label="Search"
          >
            <Icon name="search" />
          </button>
          <button
            type="button"
            className="tap relative grid w-11 place-items-center rounded-lg hover:bg-[var(--pl-mist)]"
            onClick={() => setNotesOpen((v) => !v)}
            aria-label="Notifications"
          >
            <Icon name="bell" />
            {unread ? (
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[var(--pl-danger)]" />
            ) : null}
          </button>
          {support ? (
            <a
              className="tap grid w-11 place-items-center rounded-lg hover:bg-[var(--pl-mist)]"
              href={`mailto:${support}`}
              aria-label="Help"
            >
              <Icon name="help" />
            </a>
          ) : (
            <button
              type="button"
              className="tap grid w-11 place-items-center rounded-lg hover:bg-[var(--pl-mist)]"
              onClick={() => window.alert("Ask your site owner for support. No support email is set.")}
              aria-label="Help"
            >
              <Icon name="help" />
            </button>
          )}
          <button
            type="button"
            className="tap grid w-11 place-items-center rounded-lg hover:bg-[var(--pl-mist)]"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            aria-label="Toggle theme"
          >
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          <div className="relative">
            <button
              type="button"
              className="tap flex items-center gap-2 rounded-lg px-2 hover:bg-[var(--pl-mist)]"
              onClick={() => setProfileOpen((v) => !v)}
            >
              <span className="grid h-8 w-8 place-items-center rounded-full bg-[var(--pl-accent-soft)] text-xs font-semibold text-[var(--pl-accent)]">
                {(boot.user.full_name || boot.user.name).slice(0, 1).toUpperCase()}
              </span>
              <span className="hidden text-left text-sm leading-tight sm:block">
                <span className="block font-medium">{boot.user.full_name || boot.user.name}</span>
                <span className="block text-xs text-[var(--pl-ink-soft)]">
                  {boot.is_super_admin ? "Owner" : "User"}
                </span>
              </span>
            </button>
            {profileOpen ? (
              <div className="absolute right-0 mt-2 w-56 rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-2 shadow-[var(--pl-shadow)]">
                <div className="px-2 py-1 text-xs text-[var(--pl-ink-soft)]">{boot.user.email}</div>
                <button
                  type="button"
                  className="tap mt-1 w-full rounded-lg px-2 text-left text-sm hover:bg-[var(--pl-mist)]"
                  onClick={() => void signOut().then(() => navigate("/login"))}
                >
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-auto p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>

      {searchOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-start bg-black/40 p-4 pt-[12vh]" onClick={() => setSearchOpen(false)}>
          <div
            className="w-full max-w-xl rounded-2xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-3 shadow-[var(--pl-shadow)]"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              autoFocus
              className="w-full rounded-xl border border-[var(--pl-line)] px-3 py-3"
              placeholder="Search customers, invoices, items…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <ul className="mt-2 max-h-80 overflow-auto">
              {hits.map((h) => (
                <li key={`${h.doctype}-${h.name}`}>
                  <button
                    type="button"
                    className="flex w-full flex-col rounded-lg px-3 py-2 text-left hover:bg-[var(--pl-mist)]"
                    onClick={() => {
                      setSearchOpen(false);
                      navigate(h.href || "/");
                    }}
                  >
                    <span className="text-sm font-medium">{h.title}</span>
                    <span className="text-xs text-[var(--pl-ink-soft)]">
                      {h.doctype} · {h.name}
                    </span>
                  </button>
                </li>
              ))}
              {q.trim().length >= 2 && !hits.length ? (
                <li className="px-3 py-4 text-sm text-[var(--pl-ink-soft)]">No matches</li>
              ) : null}
            </ul>
          </div>
        </div>
      ) : null}

      {notesOpen ? (
        <div className="fixed inset-0 z-50" onClick={() => setNotesOpen(false)}>
          <aside
            className="absolute right-0 top-16 h-[calc(100%-4rem)] w-full max-w-sm overflow-auto border-l border-[var(--pl-line)] bg-[var(--pl-surface)] p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Alerts</h2>
              <button
                type="button"
                className="text-sm text-[var(--pl-accent)] underline"
                onClick={() =>
                  void callMethod("erpnext.portal_control.dashboard.mark_notification_read", {}).then(() => reload())
                }
              >
                Mark all read
              </button>
            </div>
            <ul className="mt-4 space-y-2">
              {(home?.alerts || []).map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    className="w-full rounded-lg border border-[var(--pl-line)] p-3 text-left text-sm"
                    onClick={() => {
                      setNotesOpen(false);
                      if (a.href) navigate(a.href);
                    }}
                  >
                    <span
                      className={
                        a.tone === "danger"
                          ? "text-[var(--pl-danger)]"
                          : a.tone === "warning"
                            ? "text-[var(--pl-warning)]"
                            : "text-[var(--pl-accent)]"
                      }
                    >
                      {a.text}
                    </span>
                  </button>
                </li>
              ))}
              {!home?.alerts?.length ? (
                <li className="text-sm text-[var(--pl-ink-soft)]">No alerts right now.</li>
              ) : null}
            </ul>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
