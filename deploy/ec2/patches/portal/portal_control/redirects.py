# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Post-login / home redirects into the Prime Ledger portal."""

from __future__ import annotations

import frappe

# Desk defaults that should become the portal home instead
_DESK_LANDINGS = frozenset(
	{
		"/",
		"/app",
		"/app/",
		"/app/home",
		"/desk",
		"/desk/",
		"/desk/home",
		"desk",
		"app",
	}
)


def _portal_enabled() -> bool:
	if not frappe.db.exists("DocType", "PL Portal Settings"):
		return True
	try:
		val = frappe.db.get_single_value("PL Portal Settings", "enable_portal_home")
		# Missing / unset Singles row → treat as enabled (portal is the product home)
		if val is None or val == "":
			return True
		return bool(int(val))
	except Exception:
		return True


def _default_landing(login_manager=None) -> str:
	if not frappe.db.exists("DocType", "PL Portal Settings"):
		return "/portal"
	try:
		from erpnext.portal_control.api import is_super_admin

		settings = frappe.get_single("PL Portal Settings")
		# During on_login, session roles may not be ready — use login_manager.user
		user = _resolve_user(login_manager)
		if is_super_admin(user):
			return settings.default_super_admin_landing or "/portal/admin"
		return settings.default_tenant_landing or "/portal/tenant"
	except Exception:
		return "/portal"


def _resolve_user(login_manager=None) -> str | None:
	user = None
	if login_manager is not None:
		user = getattr(login_manager, "user", None)
	user = user or getattr(frappe.session, "user", None)
	if not user or user == "Guest":
		return None
	return user


def _apply_redirect(landing: str, login_manager=None) -> None:
	"""Set login JSON fields and Frappe's redirect_after_login cache.

	LoginManager.set_user_info() runs *after* on_login and overwrites home_page to
	desk. It only preserves redirect_to when redirect_after_login is cached — so
	we must write that cache here for a reliable post-login portal landing.
	"""
	frappe.local.response["redirect_to"] = landing
	frappe.local.response["home_page"] = landing
	user = _resolve_user(login_manager)
	if user:
		frappe.cache.hset("redirect_after_login", user, landing)


def on_login(login_manager=None):
	"""Send System Users to the portal after login (unless a deep-link redirect-to is set)."""
	try:
		if not _resolve_user(login_manager):
			return
		if not _portal_enabled():
			return

		# Respect explicit redirect-to from the login form / query string
		redirect_to = None
		try:
			redirect_to = frappe.form_dict.get("redirect-to")
			if not redirect_to and getattr(frappe.local, "request", None):
				redirect_to = frappe.local.request.args.get("redirect-to")
		except Exception:
			redirect_to = None

		if redirect_to:
			redirect_to = str(redirect_to).strip()
			if redirect_to not in _DESK_LANDINGS:
				# Deep link (e.g. /app/sales-invoice/...) — keep it, but ensure response/cache
				_apply_redirect(redirect_to, login_manager)
				return

		_apply_redirect(_default_landing(login_manager), login_manager)
	except Exception:
		# Never block login if portal redirect wiring is missing/broken
		frappe.log_error(title="Prime Ledger on_login redirect skipped")


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
