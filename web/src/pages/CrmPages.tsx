import { ResourcePage } from "@/components/ResourcePage";
import { RESOURCES } from "@/lib/catalog";

function page(id: string) {
  const resource = RESOURCES.find((r) => r.id === id);
  if (!resource) return <p>Unknown list</p>;
  return <ResourcePage resource={resource} />;
}

export function ProductsPage() {
  return page("items");
}
export function CustomersPage() {
  return page("customers");
}
export function LeadsPage() {
  return page("leads");
}
export function SalesPage() {
  return page("sales-invoices");
}
export function PurchasesPage() {
  return page("purchase-invoices");
}
export function StockPage() {
  return page("bins");
}
export function BatchesPage() {
  return page("batches");
}
export function QualityPage() {
  return page("quality");
}
export function FinancePage() {
  return page("payments");
}
export function SettingsPage() {
  return page("companies");
}
