# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.setup.install import _set_website_brand_assets, add_app_name, add_standard_navbar_items


def execute():
	"""Apply Prime Ledger white-label on migrate (custom images / forks)."""
	add_app_name()
	_set_website_brand_assets()
	add_standard_navbar_items()

	# Ensure brand CSS is linked for desk/website when assets are built from this fork
	css_link = '<link rel="stylesheet" href="/assets/erpnext/css/prime_ledger_brand.css">'
	try:
		head = frappe.db.get_single_value("Website Settings", "head_html") or ""
		if "prime_ledger_brand.css" not in head:
			# Also keep SCSS-bundled theme; head link covers Hub-style injects if CSS file exists
			frappe.db.set_single_value("Website Settings", "head_html", (css_link + "\n" + head).strip())
	except Exception:
		pass

	try:
		for name, label in frappe.get_all("Workspace", fields=["name", "label"], as_list=True):
			if label and "ERPNext" in label:
				frappe.db.set_value(
					"Workspace",
					name,
					"label",
					label.replace("ERPNext", "Prime Ledger"),
					update_modified=False,
				)
	except Exception:
		pass

	logo = "/assets/erpnext/images/prime-ledger-logo.svg"
	for row in frappe.get_all("Desktop Icon", fields=["name", "label"]):
		label = row.label or ""
		if "ERPNext" in label:
			frappe.db.set_value(
				"Desktop Icon",
				row.name,
				{"label": label.replace("ERPNext", "Prime Ledger"), "logo_url": logo},
				update_modified=False,
			)

	frappe.db.commit()
