# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	from erpnext.portal_control.seed import run

	run()
