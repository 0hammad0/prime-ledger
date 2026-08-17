/**
 * NexisCloud dashboard contract + live bindings.
 * Chrome uses boot.app_name (Prime Ledger on this site). Mock art said NexisCloud.
 */

/* -------------------------------------------------------------------------- */
/* 1. Theme (from the mock)                                                   */
/* -------------------------------------------------------------------------- */

export const THEME = {
  font:
    'Inter, "Segoe UI", "Helvetica Neue", system-ui, -apple-system, sans-serif',
  radius: { sm: 8, md: 12, lg: 16, pill: 999 },
  shadow: {
    card: "0 1px 2px rgba(15, 23, 42, 0.06)",
    pop: "0 8px 24px rgba(15, 23, 42, 0.12)",
  },
  color: {
    canvas: "#F4F6FB",
    surface: "#FFFFFF",
    line: "#E5E7EB",
    ink: "#0F172A",
    inkSoft: "#64748B",
    accent: "#6366F1",
    accentSoft: "#EEF2FF",
    success: "#10B981",
    danger: "#EF4444",
    warning: "#F59E0B",
    info: "#3B82F6",
  },
  moduleTint: {
    sales: { bg: "#ECFDF5", fg: "#047857" },
    purchase: { bg: "#EFF6FF", fg: "#1D4ED8" },
    inventory: { bg: "#F5F3FF", fg: "#6D28D9" },
    accounts: { bg: "#ECFEFF", fg: "#0F766E" },
    banking: { bg: "#EEF2FF", fg: "#4338CA" },
    hr: { bg: "#FFF7ED", fg: "#C2410C" },
    crm: { bg: "#FEF2F2", fg: "#B91C1C" },
    reports: { bg: "#EEF2FF", fg: "#4338CA" },
    epad: { bg: "#ECFEFF", fg: "#0F766E" },
    import_custom: { bg: "#F5F3FF", fg: "#6D28D9" },
    manufacturing: { bg: "#F8FAFC", fg: "#64748B" },
    projects: { bg: "#F8FAFC", fg: "#64748B" },
  },
} as const;

/** Replace current web teal tokens (--pl-accent #0f766e) with THEME.color.accent. */
export const CSS_VARS_TO_APPLY: Record<string, string> = {
  "--pl-ink": THEME.color.ink,
  "--pl-ink-soft": THEME.color.inkSoft,
  "--pl-accent": THEME.color.accent,
  "--pl-paper": THEME.color.canvas,
  "--pl-mist": THEME.color.accentSoft,
  "--pl-line": THEME.color.line,
  "--pl-surface": THEME.color.surface,
};

/* -------------------------------------------------------------------------- */
/* 2. Layout                                                                  */
/* -------------------------------------------------------------------------- */

export const LAYOUT = {
  sidebarWidth: 232,
  sidebarCollapsed: 72,
  headerHeight: 64,
  rightRailWidth: 300,
  contentMax: 1120,
  breakpoints: {
    /** one column, hamburger, widgets below */
    sm: 0,
    /** two columns for stats/quick links */
    md: 768,
    /** three-pane: nav + main (right rail under or beside) */
    lg: 1100,
    /** full mock: nav + main + right rail */
    xl: 1280,
  },
} as const;

export type ShellSlot =
  | "leftNav"
  | "topBar"
  | "main"
  | "rightRail"
  | "footer"
  | "mobileNavDrawer"
  | "commandPalette"
  | "notificationDrawer";

/**
 * Desktop (xl): left nav | header+main | right rail.
 * Tablet (md–lg): left nav collapsible | main; right rail stacks under main.
 * Mobile (<md): header with hamburger + search icon; drawer nav; stats stack;
 * quick links 2-col or horizontal snap; modules 1-col; right-rail widgets
 * become the last sections of the same scroll. Touch targets >= 44px.
 */
export const MOBILE_RULES = {
  minTapPx: 44,
  nav: "drawer-left",
  stats: "stack-1-col",
  quickLinks: "grid-2-or-h-scroll",
  modules: "stack-1-col",
  rightRail: "flow-below-main",
  search: "icon-then-fullscreen",
  companySwitch: "full-width-sheet",
} as const;

/* -------------------------------------------------------------------------- */
/* 3. Chrome — every control on the screenshot                                */
/* -------------------------------------------------------------------------- */

export type NavItem = {
  id: string;
  label: string;
  href: string;
  icon: string;
  portalModuleKey?: string;
  locked?: boolean;
  subtitle?: string;
  /** Super Admin only (apex control plane). Hidden on tenant sites. */
  superAdminOnly?: boolean;
};

export const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", href: "/", icon: "layout-dashboard", portalModuleKey: "dashboard" },
  { id: "sales", label: "Sales", href: "/sales", icon: "trending-up", portalModuleKey: "sales" },
  { id: "purchase", label: "Purchase", href: "/purchases", icon: "shopping-cart", portalModuleKey: "purchases" },
  { id: "inventory", label: "Inventory", href: "/stock", icon: "warehouse", portalModuleKey: "inventory" },
  { id: "accounts", label: "Accounts", href: "/finance", icon: "landmark", portalModuleKey: "finance" },
  { id: "banking", label: "Banking", href: "/banking", icon: "building-2" },
  { id: "hr", label: "HR", href: "/hr", icon: "users" },
  { id: "crm", label: "CRM", href: "/crm", icon: "contact", portalModuleKey: "leads" },
  { id: "reports", label: "Reports", href: "/reports", icon: "bar-chart-3", portalModuleKey: "reports" },
  { id: "epad", label: "ePad System", href: "/epad", icon: "tablet" },
  {
    id: "import_custom",
    label: "Import & Custom",
    href: "/import",
    icon: "upload",
    subtitle: "Duty & Tax Calculator",
  },
  { id: "settings", label: "Settings", href: "/settings", icon: "settings", portalModuleKey: "settings" },
];

export const TOP_BAR = {
  companySwitcher: true,
  globalSearch: { shortcut: "Ctrl+K" },
  notifications: { badge: true },
  help: true,
  themeToggle: true,
  profile: { name: true, role: true, avatar: true, signOut: true },
} as const;

export const QUICK_LINKS: { id: string; label: string; doctype?: string; href: string }[] = [
  { id: "create_invoice", label: "Create Invoice", doctype: "Sales Invoice", href: "/sales/invoices/new" },
  { id: "record_expense", label: "Record Expense", doctype: "Purchase Invoice", href: "/purchases/bills/new" },
  { id: "new_purchase", label: "New Purchase", doctype: "Purchase Order", href: "/purchases/orders/new" },
  { id: "receive_payment", label: "Receive Payment", doctype: "Payment Entry", href: "/finance/payments/new?type=Receive" },
  { id: "make_payment", label: "Make Payment", doctype: "Payment Entry", href: "/finance/payments/new?type=Pay" },
  { id: "new_item", label: "New Item", doctype: "Item", href: "/products/new" },
  { id: "stock_entry", label: "Stock Entry", doctype: "Stock Entry", href: "/stock/entries/new" },
  { id: "new_lead", label: "New Lead", doctype: "Lead", href: "/crm/leads/new" },
  { id: "journal", label: "Journal Entry", doctype: "Journal Entry", href: "/finance/journal/new" },
  { id: "reconcile", label: "Reconcile", doctype: "Bank Reconciliation Tool", href: "/banking/reconcile" },
];

export type ModuleCard = {
  id: string;
  title: string;
  links: { label: string; href: string; doctype?: string }[];
  locked?: boolean;
};

export const MODULE_CARDS: ModuleCard[] = [
  {
    id: "sales",
    title: "Sales",
    links: [
      { label: "Quotations", href: "/sales/quotations", doctype: "Quotation" },
      { label: "Sales Orders", href: "/sales/orders", doctype: "Sales Order" },
      { label: "Delivery Notes", href: "/sales/delivery", doctype: "Delivery Note" },
      { label: "Sales Invoices", href: "/sales/invoices", doctype: "Sales Invoice" },
    ],
  },
  {
    id: "purchase",
    title: "Purchase",
    links: [
      { label: "Supplier Quotations", href: "/purchases/rfq", doctype: "Supplier Quotation" },
      { label: "Purchase Orders", href: "/purchases/orders", doctype: "Purchase Order" },
      { label: "Purchase Receipts", href: "/purchases/receipts", doctype: "Purchase Receipt" },
      { label: "Purchase Invoices", href: "/purchases/bills", doctype: "Purchase Invoice" },
    ],
  },
  {
    id: "inventory",
    title: "Inventory",
    links: [
      { label: "Items", href: "/products", doctype: "Item" },
      { label: "Warehouses", href: "/stock/warehouses", doctype: "Warehouse" },
      { label: "Stock Entry", href: "/stock/entries", doctype: "Stock Entry" },
      { label: "Stock Balance", href: "/stock/balance", doctype: "Bin" },
    ],
  },
  {
    id: "accounts",
    title: "Accounts",
    links: [
      { label: "Chart of Accounts", href: "/finance/accounts", doctype: "Account" },
      { label: "Journal Entry", href: "/finance/journal", doctype: "Journal Entry" },
      { label: "Payment Entry", href: "/finance/payments", doctype: "Payment Entry" },
      { label: "General Ledger", href: "/reports/general-ledger" },
    ],
  },
  {
    id: "crm",
    title: "CRM",
    links: [
      { label: "Leads", href: "/crm/leads", doctype: "Lead" },
      { label: "Opportunities", href: "/crm/opportunities", doctype: "Opportunity" },
      { label: "Customers", href: "/customers", doctype: "Customer" },
    ],
  },
  {
    id: "hr",
    title: "HR",
    links: [
      { label: "Employee", href: "/hr/employees", doctype: "Employee" },
      { label: "Attendance", href: "/hr/attendance", doctype: "Attendance" },
      { label: "Leave", href: "/hr/leave", doctype: "Leave Application" },
      { label: "Payroll", href: "/hr/payroll", doctype: "Salary Slip" },
    ],
  },
  {
    id: "banking",
    title: "Banking",
    links: [
      { label: "Bank Account", href: "/banking/accounts", doctype: "Bank Account" },
      { label: "Bank Transaction", href: "/banking/transactions", doctype: "Bank Transaction" },
      { label: "Reconcile", href: "/banking/reconcile" },
    ],
  },
  {
    id: "reports",
    title: "Reports",
    links: [
      { label: "P&L", href: "/reports/profit-and-loss" },
      { label: "Balance Sheet", href: "/reports/balance-sheet" },
      { label: "Stock", href: "/reports/stock-balance" },
      { label: "AR / AP", href: "/reports/receivable" },
    ],
  },
  {
    id: "epad",
    title: "ePad System",
    links: [{ label: "Open ePad", href: "/epad" }],
  },
  {
    id: "import_custom",
    title: "Import & Custom",
    links: [
      { label: "Data Import", href: "/import/data", doctype: "Data Import" },
      { label: "Duty & Tax Calculator", href: "/import/duty" },
    ],
  },
  {
    id: "manufacturing",
    title: "Manufacturing",
    locked: true,
    links: [
      { label: "BOM", href: "/manufacturing/bom", doctype: "BOM" },
      { label: "Work Order", href: "/manufacturing/work-orders", doctype: "Work Order" },
    ],
  },
  {
    id: "projects",
    title: "Projects",
    locked: true,
    links: [{ label: "Project", href: "/projects", doctype: "Project" }],
  },
];

export const REPORT_PILLS = [
  { id: "sales", label: "Sales", href: "/reports?group=sales" },
  { id: "purchase", label: "Purchase", href: "/reports?group=purchase" },
  { id: "stock", label: "Stock", href: "/reports?group=stock" },
  { id: "accounts", label: "Accounts", href: "/reports?group=accounts" },
  { id: "tax", label: "Tax", href: "/reports?group=tax" },
] as const;

/* -------------------------------------------------------------------------- */
/* 4. Backend map — ready vs missing                                          */
/* -------------------------------------------------------------------------- */

export type BindingStatus = "ready" | "partial" | "missing";

export type ApiBinding = {
  ui: string;
  status: BindingStatus;
  method?: string;
  doctype?: string;
  note: string;
};

export const API_BINDINGS: ApiBinding[] = [
  {
    ui: "Session + shell boot",
    status: "ready",
    method: "erpnext.portal_control.api.get_portal_boot",
    note: "User, roles, companies, modules, app_name. Guest is 403.",
  },
  {
    ui: "Login / logout",
    status: "ready",
    method: "login / logout",
    note: "Cookie session on the tenant host only.",
  },
  {
    ui: "Company switcher",
    status: "ready",
    method: "erpnext.portal_control.dashboard.set_company",
    note: "Writes User default company, then boot refresh. One company per live tenant today.",
  },
  {
    ui: "Module on/off + locked cards",
    status: "ready",
    method: "erpnext.portal_control.api.set_module_enabled",
    note: "Super Admin only. enabled=0 => lock icon. Show inactive = all_modules.",
  },
  {
    ui: "CRUD lists (Item, Customer, SO, SI, PO, PI, Lead…)",
    status: "ready",
    method: "frappe.client.get_list / insert / get",
    note: "web/src/lib/api.ts already wraps these. ResourcePage exists.",
  },
  {
    ui: "Total Receivables + overdue",
    status: "ready",
    method: "erpnext.portal_control.dashboard.get_home",
    note: "Sums outstanding Sales Invoice for the selected company. Zero is a real empty books, not a mock.",
  },
  {
    ui: "Total Payables + overdue",
    status: "ready",
    method: "erpnext.portal_control.dashboard.get_home",
    note: "Sums outstanding Purchase Invoice for the selected company.",
  },
  {
    ui: "Cash in Hand",
    status: "ready",
    method: "erpnext.portal_control.dashboard.get_home",
    note: "Sum of Cash accounts via get_balance_on.",
  },
  {
    ui: "Bank Accounts rail",
    status: "ready",
    method: "erpnext.portal_control.dashboard.get_home",
    note: "Cash + Bank account balances for the company.",
  },
  {
    ui: "Recently Opened",
    status: "ready",
    method: "erpnext.portal_control.dashboard.record_open",
    note: "Per-user cache plus last-modified invoices/orders.",
  },
  {
    ui: "Alerts & Notifications",
    status: "ready",
    method: "erpnext.portal_control.dashboard.get_home",
    note: "Overdue SI/PI counts plus unread Notification Log.",
  },
  {
    ui: "Global search Ctrl+K",
    status: "ready",
    method: "erpnext.portal_control.dashboard.search",
    note: "Customer, Item, invoices, leads, employees the user can read.",
  },
  {
    ui: "Help",
    status: "ready",
    note: "boot.settings.support_email mailto. No extra API.",
  },
  {
    ui: "Theme toggle",
    status: "ready",
    note: "Client-only (localStorage). No backend.",
  },
  {
    ui: "Quick link Customize",
    status: "missing",
    note: "Needs User-level JSON in a Custom Field or localStorage v1.",
  },
  {
    ui: "ePad System",
    status: "ready",
    method: "erpnext.portal_control.workspace.save_todo",
    note: "ToDo records until a dedicated ePad DocType exists.",
  },
  {
    ui: "Duty & Tax Calculator",
    status: "ready",
    method: "erpnext.portal_control.dashboard.tax_templates",
    note: "Applies live Sales Taxes and Charges Template rates. No invented tariff table.",
  },
  {
    ui: "Manufacturing / Projects lock",
    status: "partial",
    note: "ERPNext DocTypes exist. Treat as locked until Portal Module rows exist and enabled.",
  },
  {
    ui: "Owner Organizations (not on this mock)",
    status: "ready",
    method: "erpnext.portal_control.tenants.*",
    note: "Approve / reject / block stay on Super Admin routes, not tenant home.",
  },
];

/* -------------------------------------------------------------------------- */
/* 5. UX states every widget must implement                                   */
/* -------------------------------------------------------------------------- */

export type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "ready"; data: T };

export const UX_RULES = {
  loading: "Skeleton that matches card shape. Never a blank white hole.",
  error: "Inline card error + Retry. Do not toast-bomb the whole shell.",
  empty: "One line of copy + primary action (e.g. Create Invoice).",
  permission: "If 403, hide the widget or show 'You cannot see this'. Never fake zeros as success.",
  stale: "Keep last good data, dim it, retry in background.",
  timeoutMs: 20000,
} as const;

/* -------------------------------------------------------------------------- */
/* 6. Empty fetchers — implement these next, in this order                    */
/* -------------------------------------------------------------------------- */

export type MoneyKpi = {
  label: string;
  amount: number;
  currency: string;
  overdue?: number;
};

export type DashboardPayload = {
  company: string;
  currency: string;
  receivables: MoneyKpi;
  payables: MoneyKpi;
  cash: MoneyKpi;
  quickLinks: typeof QUICK_LINKS;
  modules: ModuleCard[];
  recent: { doctype: string; name: string; title: string; when: string }[];
  alerts: { id: string; tone: "danger" | "warning" | "info"; text: string }[];
  banks: { name: string; currency: string; balance: number }[];
};

export const BUILD_STEPS = [
  "Tokens + Shell (nav, header, drawers) with boot user/company/modules",
  "Responsive breakpoints from MOBILE_RULES",
  "Dashboard skeletons",
  "Wire lists already in ResourcePage to new chrome",
  "KPI strip (after portal dashboard method or query_report wrapper)",
  "Right rail: Notification Log + Bank Account",
  "Ctrl+K search",
  "Locked modules + Show inactive",
  "Stubs: ePad, Duty calculator",
  "Dark theme tokens",
] as const;

export async function fetchDashboard(company: string): Promise<DashboardPayload> {
  const { callMethod } = await import("@/lib/api");
  const home = (await callMethod(
    "erpnext.portal_control.dashboard.get_home",
    company ? { company } : {},
    false,
  )) as DashboardPayload;
  return { ...home, quickLinks: QUICK_LINKS, modules: MODULE_CARDS };
}

export async function fetchSearch(q: string): Promise<{ doctype: string; name: string; title: string }[]> {
  const { callMethod } = await import("@/lib/api");
  const rows = await callMethod("erpnext.portal_control.dashboard.search", { q });
  return Array.isArray(rows) ? rows : [];
}

export async function fetchNotifications(): Promise<{ unread: number; items: DashboardPayload["alerts"] }> {
  const { callMethod } = await import("@/lib/api");
  const home = (await callMethod("erpnext.portal_control.dashboard.get_home", {}, false)) as {
    unread_notifications?: number;
    alerts?: DashboardPayload["alerts"];
  };
  return { unread: home.unread_notifications || 0, items: home.alerts || [] };
}

export async function setCompany(name: string): Promise<void> {
  const { callMethod } = await import("@/lib/api");
  await callMethod("erpnext.portal_control.dashboard.set_company", { company: name });
}

export async function toggleInactiveModules(show: boolean): Promise<ModuleCard[]> {
  localStorage.setItem("pl-show-inactive", show ? "1" : "0");
  return show ? [...MODULE_CARDS] : MODULE_CARDS.filter((c) => !c.locked);
}

/* -------------------------------------------------------------------------- */
/* 7. Honest leftovers (do not hide)                                          */
/* -------------------------------------------------------------------------- */

export const BACKEND_GAPS = [
  "Apex frontend site can still store leftover Company rows from before the tenant split. Tenant home must use the tenant host (VITE_API_TARGET), never apex, as the customer app.",
  "Forgot-password email still uses Frappe's /update-password link on the tenant host. The SPA /reset?key= path works if you open that key here.",
  "Sample workspace (Nexis Demo Customer / NEXIS-DEMO-SVC) is opt-in via seed_demo_workspace. It is not written unless someone clicks Load known sample data.",
  "Signup still lands as Pending on the control plane. Approve + host cron creates the private site; this SPA cannot docker-provision.",
] as const;
