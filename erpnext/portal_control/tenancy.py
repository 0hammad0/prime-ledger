# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Company / organization isolation helpers (Phase 1 single-site locks)."""

from __future__ import annotations

import frappe
from frappe import _

SUPER_ADMIN_ROLES = frozenset({"Administrator", "System Manager", "Prime Ledger Super Admin"})


def is_super_admin(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	roles = set(frappe.get_roles(user))
	if "Prime Ledger Super Admin" in roles:
		return True
	site = str(frappe.local.site or "")
	on_control = bool(frappe.conf.get("pl_is_control_plane")) or site == "frontend"
	if on_control and (user == "Administrator" or "System Manager" in roles):
		return True
	return False


def get_user_companies(user: str | None = None) -> list[str]:
	"""Companies the user may access via User Permission (allow=Company)."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return []
	if is_super_admin(user):
		return frappe.get_all("Company", pluck="name", order_by="name asc")
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Company"},
		pluck="for_value",
	)
	# Preserve order, drop empties/dupes
	seen: set[str] = set()
	out: list[str] = []
	for name in rows:
		if name and name not in seen and frappe.db.exists("Company", name):
			seen.add(name)
			out.append(name)
	return out


def bind_user_to_company(user: str, company: str, *, set_default: bool = True) -> dict:
	"""Ensure User Permission(Company) + optional default company for a user."""
	if not user or user in ("Guest", "Administrator"):
		frappe.throw(_("Cannot bind this user to a company"))
	if is_super_admin(user):
		return {"user": user, "skipped": "super_admin"}
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Unknown company: {0}").format(company))

	exists = frappe.db.exists(
		"User Permission",
		{"user": user, "allow": "Company", "for_value": company},
	)
	if not exists:
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": company,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)

	if set_default:
		frappe.defaults.set_user_default("company", company, user)
		try:
			if frappe.db.has_column("User", "default_company"):
				frappe.db.set_value("User", user, "default_company", company, update_modified=False)
		except Exception:
			pass

	frappe.clear_cache(user=user)
	return {"user": user, "company": company, "ok": True}


def _resolve_bind_company(user: str) -> str | None:
	"""Pick a company for auto-bind: user default → global default → sole company."""
	company = frappe.defaults.get_user_default("company", user)
	if company and frappe.db.exists("Company", company):
		return company
	try:
		if frappe.db.has_column("User", "default_company"):
			company = frappe.db.get_value("User", user, "default_company")
			if company and frappe.db.exists("Company", company):
				return company
	except Exception:
		pass
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company and frappe.db.exists("Company", company):
		return company
	companies = frappe.get_all("Company", pluck="name", limit_page_length=2)
	if len(companies) == 1:
		return companies[0]
	return None


def apply_company_bindings(force_company: str | None = None) -> list[dict]:
	"""Bind all non–super-admin System Users to a company (idempotent)."""
	results: list[dict] = []
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		pluck="name",
	)
	for user in users:
		if user in ("Administrator", "Guest"):
			continue
		if is_super_admin(user):
			results.append({"user": user, "skipped": "super_admin"})
			continue
		existing = get_user_companies(user)
		if existing and not force_company:
			results.append({"user": user, "company": existing[0], "skipped": "already_bound"})
			continue
		company = force_company or _resolve_bind_company(user)
		if not company:
			results.append({"user": user, "skipped": "no_company"})
			continue
		results.append(bind_user_to_company(user, company))
	frappe.db.commit()
	return results


def assert_can_customize(doc, method=None):
	"""Block Custom Field / Property Setter changes for non–super-admins."""
	user = frappe.session.user
	if user in ("Administrator",):
		return
	if is_super_admin(user):
		return
	roles = set(frappe.get_roles(user))
	if roles & SUPER_ADMIN_ROLES or "System Manager" in roles:
		return
	frappe.throw(
		_("Only site admins can change forms and custom fields. Ask your administrator."),
		frappe.PermissionError,
	)


@frappe.whitelist()
def bind_user_company(user: str, company: str):
	"""Super Admin API: lock a user to one organization (company)."""
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return bind_user_to_company(user, company)


@frappe.whitelist()
def list_company_bindings():
	"""Super Admin: overview of user→company locks."""
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "role_profile_name"],
		order_by="name",
	)
	out = []
	for u in users:
		if u.name in ("Guest",):
			continue
		out.append(
			{
				"user": u.name,
				"full_name": u.full_name,
				"role_profile": u.role_profile_name,
				"companies": get_user_companies(u.name),
				"is_super_admin": is_super_admin(u.name),
			}
		)
	return out
