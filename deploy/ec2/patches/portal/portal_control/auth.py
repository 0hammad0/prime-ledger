# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Guest-safe password reset. Same message whether the user exists."""

from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def request_password_reset(email: str | None = None):
	email = (email or "").strip().lower()
	msg = _("If that account exists, we sent a reset link.")
	if not email:
		frappe.throw(_("Enter your email"))
	if not frappe.db.exists("User", email):
		return {"ok": True, "message": msg}
	user = frappe.get_doc("User", email)
	if int(user.enabled or 0) != 1 or user.name in ("Guest", "Administrator"):
		return {"ok": True, "message": msg}
	try:
		user.reset_password(send_email=True)
	except Exception:
		frappe.log_error(title="pl_password_reset")
	return {"ok": True, "message": msg}


@frappe.whitelist(allow_guest=True)
def complete_password_reset(key: str | None = None, new_password: str | None = None):
	key = (key or "").strip()
	new_password = new_password or ""
	if not key or len(new_password) < 8:
		frappe.throw(_("Enter a valid reset key and a password of at least 8 characters"))
	from frappe.core.doctype.user.user import update_password

	update_password(new_password=new_password, key=key, logout_all_sessions=1)
	return {"ok": True, "message": _("Password updated. Sign in with your new password.")}
