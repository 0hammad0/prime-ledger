import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { FrappeProvider } from "frappe-react-sdk";
import { PortalProvider } from "@/lib/portal";
import { PortalShell } from "@/components/PortalShell";
import { TenantHome } from "@/pages/TenantHome";
import { AdminHome } from "@/pages/AdminHome";
import { MasterControls } from "@/pages/MasterControls";
import { TenantsPage } from "@/pages/TenantsPage";
import { ModuleBridge } from "@/pages/ModuleBridge";
import { usePortal } from "@/lib/portal";

function HomeRedirect() {
  const { boot, loading } = usePortal();
  if (loading || !boot) {
    return <div className="grid h-full place-items-center">Loading…</div>;
  }
  const dest = boot.is_super_admin
    ? boot.settings.default_super_admin_landing || "/portal/admin"
    : boot.settings.default_tenant_landing || "/portal/tenant";
  return <Navigate to={dest} replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/portal" element={<HomeRedirect />} />
      <Route path="/portal/tenant" element={<PortalShell mode="tenant" />}>
        <Route index element={<TenantHome />} />
        <Route path="products" element={<ModuleBridge title="Products" />} />
        <Route path="inventory" element={<ModuleBridge title="Inventory" />} />
        <Route path="batch-expiry" element={<ModuleBridge title="Batch & Expiry" />} />
        <Route path="purchases" element={<ModuleBridge title="Purchases" />} />
        <Route path="sales" element={<ModuleBridge title="Sales" />} />
        <Route path="quality" element={<ModuleBridge title="Quality & Compliance" />} />
        <Route path="finance" element={<ModuleBridge title="Finance" />} />
        <Route path="reports" element={<ModuleBridge title="Reports" />} />
        <Route path="settings" element={<ModuleBridge title="Settings" />} />
      </Route>
      <Route path="/portal/admin" element={<PortalShell mode="admin" />}>
        <Route index element={<AdminHome />} />
        <Route path="modules" element={<MasterControls />} />
        <Route path="tenants" element={<TenantsPage />} />
        <Route path="users" element={<ModuleBridge title="Users" />} />
      </Route>
      <Route path="*" element={<Navigate to="/portal" replace />} />
    </Routes>
  );
}

export default function App() {
  const userId = document.cookie
    ?.split("; ")
    .find((row) => row.startsWith("user_id="))
    ?.split("=")[1]
    ?.trim();
  if (userId === "Guest" && !import.meta.env.DEV) {
    window.location.href = "/login?redirect-to=/portal";
  }

  return (
    <FrappeProvider
      url=""
      socketPort={import.meta.env.VITE_SOCKET_PORT}
      siteName={import.meta.env.VITE_SITE_NAME}
    >
      <PortalProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </PortalProvider>
    </FrappeProvider>
  );
}
