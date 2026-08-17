# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Public page: confirm signup email, then wait for the private workspace URL."""

import frappe

from erpnext.portal_control.tenants import _on_control_plane, _public_base_host

no_cache = 1


def get_context(context):
	if not _on_control_plane():
		frappe.local.flags.redirect_location = f"https://{_public_base_host()}/confirm"
		raise frappe.Redirect

	context.no_cache = 1
	context.app_name = (
		frappe.get_website_settings("app_name")
		or frappe.get_system_settings("app_name")
		or "Prime Ledger"
	)
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.confirm_token = (frappe.form_dict.get("token") or "").strip()
	frappe.db.commit()
