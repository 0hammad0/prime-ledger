export type PortalModule = {
  name: string;
  module_key: string;
  label: string;
  enabled: number;
  category: "Tenant" | "Super Admin" | "Shared";
  sort_order: number;
  icon?: string;
  portal_route?: string;
  desk_route?: string;
  is_super_admin_only?: number;
  description?: string;
  roles?: string[];
};

export type PortalBoot = {
  app_name: string;
  user: {
    name: string;
    full_name: string;
    email: string;
    user_image?: string;
  };
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
  companies: { name: string; abbr?: string; default_currency?: string; country?: string }[];
};
