# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Repair accidental overwrite of Frappe website Portal Settings by PL Portal Settings."""

from __future__ import annotations

import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.utils import get_bench_path


def execute():
	# If our mistaken DocType files still exist under erpnext, they are renamed in source.
	# Reload Frappe's website Portal Settings so sync_menu works again.
	bench = get_bench_path()
	path = f"{bench}/apps/frappe/frappe/website/doctype/portal_settings/portal_settings.json"
	try:
		import_file_by_path(path, force=True)
	except Exception:
		# Fallback: clear cached meta and reload from installed frappe app
		try:
			frappe.reload_doc("website", "doctype", "portal_settings", force=True)
		except Exception:
			frappe.log_error("restore_frappe_portal_settings_failed")

	# Drop orphan single values table rows that belong to wrong schema if needed — migrate will recreate.
	frappe.clear_cache()
