# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	"""Rename Module Def so desk never shows 'ERPNext Integrations'."""
	old, new = "ERPNext Integrations", "Integrations"
	if frappe.db.exists("Module Def", old):
		try:
			frappe.rename_doc("Module Def", old, new, force=True, show_alert=False)
		except Exception:
			# Already renamed or conflicting — ensure DocTypes point at new name
			pass
	if frappe.db.exists("DocType", "Plaid Settings"):
		frappe.db.set_value("DocType", "Plaid Settings", "module", new, update_modified=False)
	frappe.db.commit()
