type IconName =
  | "layout-dashboard"
  | "trending-up"
  | "shopping-cart"
  | "warehouse"
  | "landmark"
  | "building-2"
  | "users"
  | "contact"
  | "bar-chart-3"
  | "tablet"
  | "upload"
  | "settings"
  | "search"
  | "bell"
  | "help"
  | "sun"
  | "moon"
  | "menu"
  | "x"
  | "lock"
  | "plus"
  | "chevron";

const PATHS: Record<IconName, string> = {
  "layout-dashboard":
    "M3 3h8v8H3V3zm10 0h8v5h-8V3zM3 13h8v8H3v-8zm10 7h8v-10h-8v10z",
  "trending-up": "M3 17l7-7 4 4 7-8M14 6h7v7",
  "shopping-cart": "M6 6h15l-1.5 9h-12L6 6zm0 0L4 3M9 20a1 1 0 100-2 1 1 0 000 2zm9 0a1 1 0 100-2 1 1 0 000 2z",
  warehouse: "M3 21V8l9-5 9 5v13M3 21h18M9 21v-6h6v6",
  landmark: "M3 21h18M5 21V10h14v11M12 3l9 7H3l9-7z",
  "building-2": "M6 22V3h8v19M14 8h6v14M9 8h2M9 12h2M9 16h2",
  users: "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M16 3.13a4 4 0 010 7.75M8 11a4 4 0 100-8 4 4 0 000 8z",
  contact: "M17 18a5 5 0 00-10 0M12 12a4 4 0 100-8 4 4 0 000 8zM4 4h16v16H4z",
  "bar-chart-3": "M4 20V10M12 20V4M20 20v-7",
  tablet: "M7 2h10a2 2 0 012 2v16a2 2 0 01-2 2H7a2 2 0 01-2-2V4a2 2 0 012-2zm5 18h.01",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16",
  settings:
    "M12 15a3 3 0 100-6 3 3 0 000 6zm7.4-3a7.4 7.4 0 00-.1-1l2-1.5-2-3.5-2.4 1a7 7 0 00-1.7-1L13 2h-2l-.2 2.5a7 7 0 00-1.7 1L6.7 4.5l-2 3.5 2 1.5a7.4 7.4 0 000 2l-2 1.5 2 3.5 2.4-1a7 7 0 001.7 1L11 22h2l.2-2.5a7 7 0 001.7-1l2.4 1 2-3.5-2-1.5c.1-.3.1-.7.1-1z",
  search: "M11 19a8 8 0 100-16 8 8 0 000 16zm10 2l-4.3-4.3",
  bell: "M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9zm-4.3 13a2 2 0 01-3.4 0",
  help: "M12 17h.01M9.1 9a3 3 0 015.8 1c0 2-3 2-3 4M12 22a10 10 0 100-20 10 10 0 000 20z",
  sun: "M12 4V2m0 20v-2m8-8h2M2 12h2m13.7 5.7l1.4 1.4M4.9 4.9l1.4 1.4m0 11.4l-1.4 1.4m14.2-14.2l-1.4 1.4M12 8a4 4 0 100 8 4 4 0 000-8z",
  moon: "M21 14.5A8.5 8.5 0 1110 3a7 7 0 0011 11.5z",
  menu: "M4 6h16M4 12h16M4 18h16",
  x: "M6 6l12 12M18 6L6 18",
  lock: "M7 11V8a5 5 0 0110 0v3M6 11h12v10H6V11z",
  plus: "M12 5v14M5 12h14",
  chevron: "M9 6l6 6-6 6",
};

export function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className || "h-5 w-5"}
      aria-hidden
    >
      <path d={PATHS[name] || PATHS["layout-dashboard"]} />
    </svg>
  );
}

export type { IconName };
