# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt


def execute():
	"""Ensure PL Tenant DocType is synced after hot-patch (migrate imports this)."""
	import frappe

	# Reloading Setup module DocTypes picks up pl_tenant from apps path
	try:
		from frappe.modules.utils import sync_customizations

		frappe.reload_doc("setup", "doctype", "pl_tenant", force=True)
	except Exception:
		pass
