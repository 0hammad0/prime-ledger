# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _

from erpnext.portal_control.tenancy import get_user_companies, is_super_admin


def _module_allowed(module: dict, user_roles: set[str], super_admin: bool) -> bool:
	if not module.get("enabled"):
		return False
	if module.get("is_super_admin_only") and not super_admin:
		return False
	allowed = module.get("roles") or []
	if not allowed:
		# Super-admin-only modules already gated; tenant modules open to system users
		return True
	return bool(user_roles & set(allowed))


@frappe.whitelist()
def get_portal_boot():
	"""Boot payload for the Prime Ledger portal SPA."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	if not frappe.db.exists("DocType", "Portal Module"):
		frappe.throw(_("Portal Module is not installed. Run migrate on this site."))

	from erpnext.portal_control.seed import ensure_settings, run

	ensure_settings()
	from erpnext.portal_control.seed import DEFAULT_MODULES, seed_modules

	if not frappe.db.count("Portal Module"):
		run()
	else:
		have = set(frappe.get_all("Portal Module", pluck="name"))
		needed = {m["module_key"] for m in DEFAULT_MODULES}
		if not needed.issubset(have):
			seed_modules(replace=False)

	super_admin = is_super_admin()
	user_roles = set(frappe.get_roles())

	settings = frappe.get_single("PL Portal Settings")
	modules = frappe.get_all(
		"Portal Module",
		fields=[
			"name",
			"module_key",
			"label",
			"enabled",
			"category",
			"sort_order",
			"icon",
			"portal_route",
			"desk_route",
			"is_super_admin_only",
			"description",
		],
		order_by="sort_order asc, label asc",
	)

	# Attach role lists
	for m in modules:
		m["roles"] = frappe.get_all(
			"Portal Module Role",
			filters={"parent": m["name"]},
			pluck="role",
		)

	visible = [m for m in modules if _module_allowed(m, user_roles, super_admin)]
	# Super Admin: all companies. Tenant users: only User Permission → Company.
	if super_admin:
		companies = frappe.get_all(
			"Company",
			fields=["name", "abbr", "default_currency", "country"],
			order_by="name asc",
		)
	else:
		allowed_names = get_user_companies()
		companies = (
			frappe.get_all(
				"Company",
				filters={"name": ("in", allowed_names)},
				fields=["name", "abbr", "default_currency", "country"],
				order_by="name asc",
			)
			if allowed_names
			else []
		)

	user = frappe.get_doc("User", frappe.session.user)

	# Tenant registry (Phase 2) — control-plane sites only
	tenants = []
	if super_admin and frappe.db.exists("DocType", "PL Tenant"):
		tenants = frappe.get_all(
			"PL Tenant",
			fields=[
				"name",
				"organization_name",
				"site_name",
				"host",
				"status",
				"company",
				"admin_email",
				"admin_full_name",
				"creation",
				"notes",
			],
			order_by="creation desc",
		)

	from erpnext.portal_control.workspace import leaf_defaults

	return {
		"app_name": settings.portal_title or "Prime Ledger",
		"user": {
			"name": user.name,
			"full_name": user.full_name,
			"email": user.email,
			"user_image": user.user_image,
		},
		"is_super_admin": super_admin,
		"roles": sorted(user_roles),
		"settings": {
			"enable_portal_home": int(settings.enable_portal_home or 0),
			"default_tenant_landing": settings.default_tenant_landing or "/portal/tenant",
			"default_super_admin_landing": settings.default_super_admin_landing or "/portal/admin",
			"support_email": settings.support_email,
		},
		"modules": visible,
		"all_modules": modules if super_admin else visible,
		"companies": companies,
		"default_company": frappe.defaults.get_user_default("company")
		or (companies[0]["name"] if companies else None),
		"masters": leaf_defaults(),
		"tenants": tenants,
	}


@frappe.whitelist()
def set_module_enabled(module_key: str, enabled: int | str):
	"""Super Admin master control — toggle module visibility."""
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.db.exists("Portal Module", module_key):
		frappe.throw(_("Unknown module: {0}").format(module_key))
	frappe.db.set_value("Portal Module", module_key, "enabled", 1 if int(enabled) else 0)
	return {"module_key": module_key, "enabled": int(enabled)}


@frappe.whitelist()
def save_portal_settings(enable_portal_home: int | str | None = None, portal_title: str | None = None):
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	doc = frappe.get_single("PL Portal Settings")
	if enable_portal_home is not None:
		doc.enable_portal_home = int(enable_portal_home)
	if portal_title is not None:
		doc.portal_title = portal_title
	doc.save(ignore_permissions=True)
	return {"ok": True}
