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
		"module_key": "banking",
		"label": "Banking",
		"category": "Tenant",
		"sort_order": 85,
		"icon": "building-2",
		"portal_route": "/tenant/banking",
		"desk_route": "/app/bank-account",
		"description": "Bank accounts, deposits, and reconciliation",
	},
	{
		"module_key": "hr",
		"label": "HR",
		"category": "Tenant",
		"sort_order": 86,
		"icon": "users",
		"portal_route": "/tenant/hr",
		"desk_route": "/app/employee",
		"description": "People, attendance, leave, and payroll",
	},
	{
		"module_key": "crm",
		"label": "CRM",
		"category": "Tenant",
		"sort_order": 55,
		"icon": "contact",
		"portal_route": "/tenant/crm",
		"desk_route": "/app/lead",
		"description": "Leads, opportunities, and customers",
	},
	{
		"module_key": "epad",
		"label": "ePad",
		"category": "Tenant",
		"sort_order": 95,
		"icon": "tablet",
		"portal_route": "/tenant/epad",
		"desk_route": "/app/todo",
		"description": "Notes and follow-ups for your team",
	},
	{
		"module_key": "import_custom",
		"label": "Import & Custom",
		"category": "Tenant",
		"sort_order": 96,
		"icon": "upload",
		"portal_route": "/tenant/import",
		"desk_route": "/app/data-import",
		"description": "Data import and duty / tax calculator",
	},
	{
		"module_key": "manufacturing",
		"label": "Manufacturing",
		"category": "Tenant",
		"sort_order": 200,
		"icon": "factory",
		"portal_route": "/tenant/manufacturing",
		"desk_route": "/app/work-order",
		"description": "BOM and work orders (locked until enabled)",
		"enabled": 0,
	},
	{
		"module_key": "projects",
		"label": "Projects",
		"category": "Tenant",
		"sort_order": 210,
		"icon": "folder-kanban",
		"portal_route": "/tenant/projects",
		"desk_route": "/app/project",
		"description": "Projects (locked until enabled)",
		"enabled": 0,
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
		"label": "Organizations",
		"category": "Super Admin",
		"sort_order": 20,
		"icon": "building-2",
		"portal_route": "/admin/tenants",
		"desk_route": "/app/pl-tenant",
		"is_super_admin_only": 1,
		"description": "Tenant organizations (one site per org)",
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
	# Write Singles directly — get_single() can show DocType defaults (1) while
	# tabSingles still has 0/empty, which disabled portal redirect after login.
	desired = {
		"portal_title": "Prime Ledger",
		"default_tenant_landing": "/portal/tenant",
		"default_super_admin_landing": "/portal/admin",
		"enable_portal_home": 1,
		"hide_desk_chrome_hint": 1,
	}
	for field, value in desired.items():
		current = frappe.db.get_single_value("PL Portal Settings", field)
		if field == "enable_portal_home":
			if int(current or 0) != 1:
				frappe.db.set_single_value("PL Portal Settings", field, value)
		elif not (current or "").strip() if isinstance(value, str) else current != value:
			frappe.db.set_single_value("PL Portal Settings", field, value)
	frappe.clear_cache()


def seed_modules(replace: bool = False) -> None:
	if not frappe.db.exists("DocType", "Portal Module"):
		return
	for row in DEFAULT_MODULES:
		name = row["module_key"]
		if frappe.db.exists("Portal Module", name):
			doc = frappe.get_doc("Portal Module", name)
			# Always refresh plain-language labels/descriptions + routes for easy UX
			for key in ("label", "description", "portal_route", "desk_route", "category", "sort_order", "icon"):
				if key in row and (replace or key in ("label", "description", "portal_route", "desk_route")):
					doc.set(key, row[key])
			if replace:
				doc.update(row)
			doc.enabled = 1 if doc.enabled is None else doc.enabled
			doc.save(ignore_permissions=True)
		else:
			payload = dict(row)
			enabled = payload.pop("enabled", 1)
			doc = frappe.get_doc({"doctype": "Portal Module", "enabled": enabled, **payload})
			doc.insert(ignore_permissions=True)


def ensure_customize_guardrails() -> None:
	"""Prefer System Manager for customization DocTypes (best-effort)."""
	for dt in ("Custom Field", "Property Setter", "Client Script"):
		if not frappe.db.exists("DocType", dt):
			continue
		try:
			# Ensure System Manager keeps full access; strip write from common desk roles if present
			for role in ("All", "Desk User", "Sales User", "Purchase User", "Stock User"):
				name = frappe.db.get_value(
					"Custom DocPerm",
					{"parent": dt, "role": role},
					"name",
				)
				if name:
					frappe.db.set_value("Custom DocPerm", name, "write", 0, update_modified=False)
					frappe.db.set_value("Custom DocPerm", name, "create", 0, update_modified=False)
					frappe.db.set_value("Custom DocPerm", name, "delete", 0, update_modified=False)
		except Exception:
			pass


def ensure_signup_policy() -> None:
	"""Stock signup is disabled; organizations register via /start."""
	try:
		frappe.db.set_single_value("Website Settings", "disable_signup", 1)
		frappe.db.set_single_value("Website Settings", "hide_footer_signup", 1)
	except Exception:
		pass


def run() -> None:
	ensure_roles()
	ensure_settings()
	ensure_signup_policy()
	seed_modules(replace=False)
	ensure_customize_guardrails()
	# Grant Super Admin role to Administrator
	if frappe.db.exists("User", "Administrator"):
		user = frappe.get_doc("User", "Administrator")
		roles = {r.role for r in user.roles}
		if "Prime Ledger Super Admin" not in roles:
			user.append("roles", {"role": "Prime Ledger Super Admin"})
			user.save(ignore_permissions=True)
	# Phase 1: bind existing tenant users to their default company
	try:
		from erpnext.portal_control.tenancy import apply_company_bindings

		apply_company_bindings()
	except Exception:
		frappe.log_error(title="prime_ledger_apply_company_bindings")
	frappe.db.commit()
