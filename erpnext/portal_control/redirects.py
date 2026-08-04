# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Post-login / home redirects into the Prime Ledger portal."""

from __future__ import annotations

import frappe


def _portal_enabled() -> bool:
	if not frappe.db.exists("DocType", "PL Portal Settings"):
		return True
	try:
		return bool(frappe.db.get_single_value("PL Portal Settings", "enable_portal_home"))
	except Exception:
		return True


def _default_landing() -> str:
	if not frappe.db.exists("DocType", "PL Portal Settings"):
		return "/portal"
	try:
		from erpnext.portal_control.api import is_super_admin

		settings = frappe.get_single("PL Portal Settings")
		if is_super_admin():
			return settings.default_super_admin_landing or "/portal/admin"
		return settings.default_tenant_landing or "/portal/tenant"
	except Exception:
		return "/portal"


def on_login(login_manager=None):
	"""Send System Users to the portal after login (unless redirect-to is set)."""
	if frappe.session.user in ("Guest",):
		return
	if not _portal_enabled():
		return

	# Respect explicit redirect-to from the login form / query string
	redirect_to = frappe.form_dict.get("redirect-to") or frappe.local.request.args.get("redirect-to")
	if redirect_to and redirect_to not in ("/", "/app", "/desk", "/desk/home", "/app/home"):
		return

	landing = _default_landing()
	frappe.local.response["redirect_to"] = landing
	frappe.local.response["home_page"] = landing


def boot_session(bootinfo):
	"""Expose portal home so desk/app launcher prefers /portal."""
	if not _portal_enabled():
		return
	try:
		landing = _default_landing()
		bootinfo["app_home"] = landing
		bootinfo["sysdefaults"] = bootinfo.get("sysdefaults") or {}
		# Keep desk usable, but product home is portal
		bootinfo["prime_ledger_portal_home"] = landing
	except Exception:
		pass
