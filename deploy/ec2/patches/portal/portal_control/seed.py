# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe

DEFAULT_MODULES = [
	{
		"module_key": "dashboard",
		"label": "Dashboard",
		"category": "Shared",
		"sort_order": 10,
		"icon": "layout-dashboard",
		"portal_route": "/tenant",
		"desk_route": "",
		"description": "Tenant home overview",
	},
	{
		"module_key": "products",
		"label": "Products",
		"category": "Tenant",
		"sort_order": 20,
		"icon": "package",
		"portal_route": "/tenant/products",
		"desk_route": "/app/item",
		"description": "Items, groups, brands, variants",
	},
	{
		"module_key": "inventory",
		"label": "Inventory",
		"category": "Tenant",
		"sort_order": 30,
		"icon": "warehouse",
		"portal_route": "/tenant/inventory",
		"desk_route": "/app/stock-balance",
		"description": "Warehouses, stock, transfers",
	},
	{
		"module_key": "batch_expiry",
		"label": "Batch & Expiry",
		"category": "Tenant",
		"sort_order": 40,
		"icon": "calendar-clock",
		"portal_route": "/tenant/batch-expiry",
		"desk_route": "/app/batch",
		"description": "Lots, manufacturing and expiry dates",
	},
	{
		"module_key": "purchases",
		"label": "Purchases",
		"category": "Tenant",
		"sort_order": 50,
		"icon": "shopping-cart",
		"portal_route": "/tenant/purchases",
		"desk_route": "/app/purchase-order",
		"description": "RFQ, PO, receipts, supplier invoices",
	},
	{
		"module_key": "sales",
		"label": "Sales",
		"category": "Tenant",
		"sort_order": 60,
		"icon": "badge-dollar-sign",
		"portal_route": "/tenant/sales",
		"desk_route": "/app/sales-order",
		"description": "Quotations, orders, delivery, invoices",
	},
	{
		"module_key": "quality",
		"label": "Quality & Compliance",
		"category": "Tenant",
		"sort_order": 70,
		"icon": "shield-check",
		"portal_route": "/tenant/quality",
		"desk_route": "/app/quality-inspection",
		"description": "Inspections, quarantine release",
	},
	{
		"module_key": "finance",
		"label": "Finance",
		"category": "Tenant",
		"sort_order": 80,
		"icon": "landmark",
		"portal_route": "/tenant/finance",
		"desk_route": "/app/account",
		"description": "Receivables, payables, payments",
	},
	{
		"module_key": "reports",
		"label": "Reports",
		"category": "Tenant",
		"sort_order": 90,
		"icon": "bar-chart-3",
		"portal_route": "/tenant/reports",
		"desk_route": "/app/query-report",
		"description": "Stock, sales, purchase and finance reports",
	},
	{
		"module_key": "settings",
		"label": "Settings",
		"category": "Tenant",
		"sort_order": 100,
		"icon": "settings",
		"portal_route": "/tenant/settings",
		"desk_route": "/app/company",
		"description": "Company and limited tenant settings",
	},
	{
		"module_key": "admin_home",
		"label": "Platform Home",
		"category": "Super Admin",
		"sort_order": 5,
		"icon": "gauge",
		"portal_route": "/admin",
		"desk_route": "",
		"is_super_admin_only": 1,
		"description": "Super Admin overview",
	},
	{
		"module_key": "master_controls",
		"label": "Master Controls",
		"category": "Super Admin",
		"sort_order": 15,
		"icon": "sliders-horizontal",
		"portal_route": "/admin/modules",
		"desk_route": "/app/portal-module",
		"is_super_admin_only": 1,
		"description": "Show or hide portal modules for tenants",
	},
	{
		"module_key": "tenants",
		"label": "Companies / Tenants",
		"category": "Super Admin",
		"sort_order": 20,
		"icon": "building-2",
		"portal_route": "/admin/tenants",
		"desk_route": "/app/company",
		"is_super_admin_only": 1,
		"description": "Companies under this site (near-term tenancy)",
	},
	{
		"module_key": "users",
		"label": "Users",
		"category": "Super Admin",
		"sort_order": 30,
		"icon": "users",
		"portal_route": "/admin/users",
		"desk_route": "/app/user",
		"is_super_admin_only": 1,
		"description": "Platform and tenant user access",
	},
]


def ensure_roles() -> None:
	for role in ("Prime Ledger Super Admin", "Prime Ledger Tenant Admin"):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def ensure_settings() -> None:
	if not frappe.db.exists("DocType", "PL Portal Settings"):
		return
	try:
		doc = frappe.get_single("PL Portal Settings")
	except Exception:
		doc = frappe.new_doc("PL Portal Settings")
	changed = False
	if not doc.portal_title:
		doc.portal_title = "Prime Ledger"
		changed = True
	if not doc.default_tenant_landing:
		doc.default_tenant_landing = "/portal/tenant"
		changed = True
	if not doc.default_super_admin_landing:
		doc.default_super_admin_landing = "/portal/admin"
		changed = True
	if doc.enable_portal_home is None:
		doc.enable_portal_home = 1
		changed = True
	if doc.is_new() or changed:
		doc.save(ignore_permissions=True)


def seed_modules(replace: bool = False) -> None:
	if not frappe.db.exists("DocType", "Portal Module"):
		return
	for row in DEFAULT_MODULES:
		name = row["module_key"]
		if frappe.db.exists("Portal Module", name):
			if not replace:
				continue
			doc = frappe.get_doc("Portal Module", name)
			doc.update(row)
			doc.enabled = 1 if doc.enabled is None else doc.enabled
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Portal Module", "enabled": 1, **row})
			doc.insert(ignore_permissions=True)


def run() -> None:
	ensure_roles()
	ensure_settings()
	seed_modules()
	# Grant Super Admin role to Administrator
	if frappe.db.exists("User", "Administrator"):
		user = frappe.get_doc("User", "Administrator")
		roles = {r.role for r in user.roles}
		if "Prime Ledger Super Admin" not in roles:
			user.append("roles", {"role": "Prime Ledger Super Admin"})
			user.save(ignore_permissions=True)
	frappe.db.commit()
