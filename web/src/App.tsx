import { Navigate, Outlet, Route, Routes } from "react-router";
import { useAuth } from "@/lib/auth";
import { RESOURCES } from "@/lib/catalog";
import { MODULE_CARDS } from "@/nexiscloud/MASTER";
import { Shell } from "@/components/Shell";
import { ResourcePage } from "@/components/ResourcePage";
import { DocForm } from "@/components/DocForm";
import { LoginPage } from "@/pages/LoginPage";
import { SignupPage } from "@/pages/SignupPage";
import { ForgotPage, ResetPage } from "@/pages/ForgotPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { AdminHomePage, ModulesPage, OrganizationsPage } from "@/pages/AdminPages";
import { TeamPage } from "@/pages/TeamPage";
import { EpadPage } from "@/pages/EpadPage";
import { DutyPage, ImportHubPage } from "@/pages/DutyPage";
import { BankingReconcilePage, ModuleHubPage, ReportsPage } from "@/pages/ReportsPage";

function ProtectedLayout() {
  const { boot, loading } = useAuth();
  if (loading) {
    return <div className="grid h-full place-items-center text-[var(--pl-ink-soft)]">Loading…</div>;
  }
  if (!boot) return <Navigate to="/login" replace />;
  return <Shell />;
}

function SuperOnly() {
  const { boot } = useAuth();
  if (!boot?.is_super_admin) {
    return (
      <div className="rounded-xl border border-[var(--pl-line)] bg-[var(--pl-surface)] p-6">
        <h1 className="text-xl font-semibold">This page is for the site owner</h1>
        <p className="mt-2 text-[var(--pl-ink-soft)]">Use Home for daily work in your organization.</p>
      </div>
    );
  }
  return <Outlet />;
}

function hub(id: string, title: string) {
  const card = MODULE_CARDS.find((c) => c.id === id);
  return <ModuleHubPage title={title} links={card?.links || []} />;
}

const RESOURCE_ROUTES = RESOURCES.flatMap((r) => {
  const base = r.path.replace(/^\//, "");
  return [
    <Route key={r.id} path={base} element={<ResourcePage resource={r} />} />,
    <Route key={`${r.id}-new`} path={`${base}/new`} element={<DocForm resource={r} />} />,
    <Route key={`${r.id}-one`} path={`${base}/:name`} element={<DocForm resource={r} />} />,
  ];
});

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/forgot" element={<ForgotPage />} />
      <Route path="/reset" element={<ResetPage />} />
      <Route element={<ProtectedLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="sales" element={hub("sales", "Sales")} />
        <Route path="purchases" element={hub("purchase", "Purchase")} />
        <Route path="stock" element={hub("inventory", "Inventory")} />
        <Route path="finance" element={hub("accounts", "Accounts")} />
        <Route path="crm" element={hub("crm", "CRM")} />
        <Route path="hr" element={hub("hr", "HR")} />
        <Route path="banking" element={hub("banking", "Banking")} />
        <Route path="banking/reconcile" element={<BankingReconcilePage />} />
        <Route path="import" element={<ImportHubPage />} />
        <Route path="import/duty" element={<DutyPage />} />
        <Route path="epad" element={<EpadPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="reports/:name" element={<ReportsPage />} />
        <Route path="team" element={<TeamPage />} />
        {RESOURCE_ROUTES}
        <Route path="admin" element={<SuperOnly />}>
          <Route index element={<AdminHomePage />} />
          <Route path="modules" element={<ModulesPage />} />
          <Route path="organizations" element={<OrganizationsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
