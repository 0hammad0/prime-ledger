export type PortalModule = {
  name: string;
  module_key: string;
  label: string;
  enabled: number;
  category: "Tenant" | "Super Admin" | "Shared";
  portal_route?: string;
  desk_route?: string;
  description?: string;
  is_super_admin_only?: number;
};

export type Company = {
  name: string;
  abbr?: string;
  default_currency?: string;
  country?: string;
};

export type Tenant = {
  name: string;
  organization_name: string;
  site_name: string;
  host?: string;
  status: string;
  company?: string;
  admin_email?: string;
  admin_full_name?: string;
};

export type Boot = {
  app_name: string;
  user: { name: string; full_name: string; email: string; user_image?: string };
  is_super_admin: boolean;
  roles: string[];
  settings: {
    enable_portal_home: number;
    default_tenant_landing: string;
    default_super_admin_landing: string;
    support_email?: string;
  };
  modules: PortalModule[];
  all_modules: PortalModule[];
  companies: Company[];
  default_company?: string | null;
  masters?: {
    customer_group?: string;
    territory?: string;
    item_group?: string;
    supplier_group?: string;
    stock_uom?: string;
  };
  tenants?: Tenant[];
};

export type MoneyKpi = {
  label: string;
  amount: number;
  currency: string;
  overdue?: number;
};

export type HomeAlert = {
  id: string;
  tone: "danger" | "warning" | "info";
  text: string;
  href?: string;
};

export type HomeRecent = {
  doctype: string;
  name: string;
  title: string;
  when: string;
  amount?: number;
  href?: string;
};

export type HomeBank = {
  name: string;
  label?: string;
  kind?: string;
  currency: string;
  balance: number;
};

export type HomePayload = {
  company: string | null;
  currency: string;
  receivables: MoneyKpi;
  payables: MoneyKpi;
  cash: MoneyKpi;
  banks: HomeBank[];
  recent: HomeRecent[];
  alerts: HomeAlert[];
  unread_notifications: number;
};

export type SearchHit = {
  doctype: string;
  name: string;
  title: string;
  href?: string;
};

export type LinkOption = { name: string; label: string };
