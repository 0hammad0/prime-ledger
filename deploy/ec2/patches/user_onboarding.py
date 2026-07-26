"""Assign sensible Role Profiles / roles for new System Users (Frappe v16+).

Important: on insert, Frappe often flips user_type to "Website User" when the
user has no desk roles yet. We must still attach a desk Role Profile, then
force user_type back to System User.
"""

from __future__ import annotations

import frappe

ADMIN_PROFILE = "Prime Ledger Admin"
USER_PROFILE = "Prime Ledger User"
PORTAL_ROLES = {"Customer", "Supplier", "Partner", "Student", "Instructor", "Guardian"}


def _profile_roles(profile: str) -> list[str]:
	return frappe.get_all(
		"Has Role",
		filters={"parent": profile, "parenttype": "Role Profile"},
		pluck="role",
	)


def _user_has_profile(user_name: str, profile: str | None = None) -> bool:
	filters: dict = {"parent": user_name}
	if profile:
		filters["role_profile"] = profile
	return bool(frappe.db.exists("User Role Profile", filters))


def apply_role_profile(user_name: str, profile: str) -> bool:
	"""Attach a Role Profile + sync roles (no recursive User.save)."""
	if not user_name or user_name in ("Administrator", "Guest"):
		return False
	if not frappe.db.exists("Role Profile", profile):
		return False
	if _user_has_profile(user_name, profile):
		# Still ensure System User for desk profiles
		frappe.db.set_value("User", user_name, "user_type", "System User", update_modified=False)
		return True

	frappe.get_doc(
		{
			"doctype": "User Role Profile",
			"parent": user_name,
			"parenttype": "User",
			"parentfield": "role_profiles",
			"role_profile": profile,
		}
	).insert(ignore_permissions=True)

	existing = set(frappe.get_roles(user_name))
	for role in _profile_roles(profile):
		if not role or role in existing:
			continue
		if frappe.db.exists("Has Role", {"parent": user_name, "role": role}):
			continue
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": user_name,
				"parenttype": "User",
				"parentfield": "roles",
				"role": role,
			}
		).insert(ignore_permissions=True)

	# Desk access requires System User
	frappe.db.set_value("User", user_name, "user_type", "System User", update_modified=False)
	frappe.clear_cache(user=user_name)
	return True


def on_user_after_insert(doc, method=None):
	try:
		name = getattr(doc, "name", None)
		if not name or name in ("Administrator", "Guest"):
			return
		if _user_has_profile(name):
			return

		role_names = {getattr(r, "role", None) for r in (doc.get("roles") or [])}
		role_names.discard(None)

		# Skip real portal / website contacts
		if role_names & PORTAL_ROLES and "System Manager" not in role_names:
			return

		profile = ADMIN_PROFILE if "System Manager" in role_names else USER_PROFILE
		apply_role_profile(name, profile)
	except Exception:
		frappe.log_error(title="prime_ledger_user_onboarding", message=frappe.get_traceback())


def ensure_admin_roles(email: str | None = None):
	try:
		from erpnext.setup.ensure_users import ensure_admin_roles as _ensure

		return _ensure(email)
	except Exception:
		return None
