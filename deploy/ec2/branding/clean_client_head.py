# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Client-review polish: clean login head HTML. Does not change passwords."""

from __future__ import annotations

import frappe

HEAD = (
	'<link rel="stylesheet" href="/assets/erpnext/css/prime_ledger_brand.css">\n'
	'<script src="/assets/erpnext/js/login_simple.js?v=20260818" defer></script>'
)


def run():
	frappe.db.set_single_value("Website Settings", "head_html", HEAD)
	frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")
	frappe.db.set_single_value("Website Settings", "footer_powered", "Prime Ledger")
	frappe.db.set_single_value("Website Settings", "copyright", "Prime Ledger")
	frappe.db.set_single_value("Website Settings", "title_prefix", "Prime Ledger")
	try:
		frappe.db.set_single_value("Website Settings", "disable_signup", 1)
		frappe.db.set_single_value("Website Settings", "hide_footer_signup", 1)
	except Exception as e:
		print("skip signup flags", e)
	frappe.db.commit()
	frappe.clear_cache()
	print("client_head_ok", frappe.local.site)
