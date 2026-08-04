# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe

DEFAULT_MODULES = [
	{
		"module_key": "dashboard",
		"label": "Home",
		"category": "Shared",
		"sort_order": 10,
		"icon": "layout-dashboard",
		"portal_route": "/tenant",
		"desk_route": "",
		"description": "Your business home",
	},
	{
		"module_key": "products",
		"label": "Products",
		"category": "Tenant",
		"sort_order": 20,
		"icon": "package",
		"portal_route": "/tenant/products",
		"desk_route": "/app/item",
		"description": "Things you buy and sell",
	},
	{
		"module_key": "inventory",
		"label": "Stock",
		"category": "Tenant",
		"sort_order": 30,
		"icon": "warehouse",
		"portal_route": "/tenant/inventory",
		"desk_route": "/app/stock-balance",
		"description": "How much you have in store",
	},
	{
		"module_key": "batch_expiry",
		"label": "Batch & Expiry",
		"category": "Tenant",
		"sort_order": 40,
		"icon": "calendar-clock",
		"portal_route": "/tenant/batch-expiry",
		"desk_route": "/app/batch",
		"description": "Track batches and expiry dates",
	},
	{
		"module_key": "purchases",
		"label": "Purchases",
		"category": "Tenant",
		"sort_order": 50,
		"icon": "shopping-cart",
		"portal_route": "/tenant/purchases",
		"desk_route": "/app/purchase-order",
		"description": "Buy from suppliers and get bills",
	},
	{
		"module_key": "sales",
		"label": "Sales",
		"category": "Tenant",
		"sort_order": 60,
		"icon": "badge-dollar-sign",
		"portal_route": "/tenant/sales",
		"desk_route": "/app/sales-order",
		"description": "Sell to customers and send invoices",
	},
	{
		"module_key": "quality",
		"label": "Quality checks",
		"category": "Tenant",
		"sort_order": 70,
		"icon": "shield-check",
		"portal_route": "/tenant/quality",
		"desk_route": "/app/quality-inspection",
		"description": "Check goods before you accept them",
	},
	{
		"module_key": "finance",
		"label": "Money",
		"category": "Tenant",
		"sort_order": 80,
		"icon": "landmark",
		"portal_route": "/tenant/finance",
		"desk_route": "/app/account",
		"description": "Money in, money out, and payments",
	},
	{
		"module_key": "reports",
		"label": "Reports",
		"category": "Tenant",
		"sort_order": 90,
		"icon": "bar-chart-3",
		"portal_route": "/tenant/reports",
		"desk_route": "/app/query-report",
		"description": "Simple numbers for sales, stock, and money",
	},
	{
		"module_key": "settings",
		"label": "Settings",
		"category": "Tenant",
		"sort_order": 100,
		"icon": "settings",
		"portal_route": "/tenant/settings",
		"desk_route": "/app/company",
		"description": "Your business name and basic options",
	},
	{
		"module_key": "admin_home",
		"label": "Site admin",
		"category": "Super Admin",
		"sort_order": 5,
		"icon": "gauge",
		"portal_route": "/admin",
		"desk_route": "",
		"is_super_admin_only": 1,
		"description": "Controls for the whole site",
	},
	{
		"module_key": "master_controls",
		"label": "What teams can see",
		"category": "Super Admin",
		"sort_order": 15,
		"icon": "sliders-horizontal",
		"portal_route": "/admin/modules",
		"desk_route": "/app/portal-module",
		"is_super_admin_only": 1,
		"description": "Show or hide menu items for teams",
	},
	{
		"module_key": "tenants",
		"label": "Businesses",
		"category": "Super Admin",
		"sort_order": 20,
		"icon": "building-2",
		"portal_route": "/admin/tenants",
		"desk_route": "/app/company",
		"is_super_admin_only": 1,
		"description": "Companies set up on this site",
	},
	{
		"module_key": "users",
		"label": "People",
		"category": "Super Admin",
		"sort_order": 30,
		"icon": "users",
		"portal_route": "/admin/users",
		"desk_route": "/app/user",
		"is_super_admin_only": 1,
		"description": "Who can sign in and what they can do",
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
			doc = frappe.get_doc("Portal Module", name)
			# Always refresh plain-language labels/descriptions for easy UX
			for key in ("label", "description", "portal_route", "desk_route", "category", "sort_order", "icon"):
				if key in row and (replace or key in ("label", "description")):
					doc.set(key, row[key])
			if replace:
				doc.update(row)
			doc.enabled = 1 if doc.enabled is None else doc.enabled
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Portal Module", "enabled": 1, **row})
			doc.insert(ignore_permissions=True)


def run() -> None:
	ensure_roles()
	ensure_settings()
	seed_modules(replace=False)
	# Grant Super Admin role to Administrator
	if frappe.db.exists("User", "Administrator"):
		user = frappe.get_doc("User", "Administrator")
		roles = {r.role for r in user.roles}
		if "Prime Ledger Super Admin" not in roles:
			user.append("roles", {"role": "Prime Ledger Super Admin"})
			user.save(ignore_permissions=True)
	frappe.db.commit()
