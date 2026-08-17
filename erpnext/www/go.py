# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""One-time sign-in from a signup ticket. Lands on this organization's host."""

import frappe

no_cache = 1


def get_context(context):
	ticket = (frappe.form_dict.get("ticket") or "").strip()
	if not ticket:
		frappe.local.flags.redirect_location = "/login"
		raise frappe.Redirect
	from erpnext.portal_control.tenants import login_with_ticket

	try:
		result = login_with_ticket(ticket)
		landing = (result or {}).get("redirect_to") or "/portal"
	except Exception:
		frappe.local.flags.redirect_location = "/login"
		raise frappe.Redirect
	frappe.local.flags.redirect_location = landing
	raise frappe.Redirect
