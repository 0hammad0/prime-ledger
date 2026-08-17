# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Known sample workspace — only when the signed-in company has no sales invoices.

Does not run on its own. Super Admin / System Manager / Tenant Admin must call it.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from erpnext.portal_control.dashboard import resolve_company
from erpnext.portal_control.tenancy import is_super_admin
from erpnext.portal_control.workspace import leaf_defaults, quick_create

DEMO_ITEM = "NEXIS-DEMO-SVC"
DEMO_CUSTOMER = "Nexis Demo Customer"
DEMO_SUPPLIER = "Nexis Demo Supplier"


def _can_seed() -> bool:
	if is_super_admin():
		return True
	return bool(set(frappe.get_roles()) & {"System Manager", "Prime Ledger Tenant Admin", "Accounts Manager"})


@frappe.whitelist()
def seed_demo_workspace(company: str | None = None, force: int | str = 0):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	if not _can_seed():
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	# Inserts below run as the signed-in tenant admin after roles are granted.

	company = resolve_company(company)
	if not company:
		frappe.throw(_("No company on this site"))

	existing = frappe.db.count("Sales Invoice", {"company": company})
	if existing and int(force or 0) != 1:
		return {
			"ok": True,
			"seeded": False,
			"company": company,
			"message": _("This company already has {0} sales invoice(s). Sample data was not added.").format(existing),
		}

	from erpnext.portal_control.company_seed import _ensure_fiscal_year

	_ensure_fiscal_year(company)

	masters = leaf_defaults()

	if not frappe.db.exists("Item", DEMO_ITEM):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": DEMO_ITEM,
				"item_name": "Nexis Demo Service",
				"item_group": masters.get("item_group") or "Products",
				"stock_uom": masters.get("stock_uom") or "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_purchase_item": 1,
			}
		).insert()

	if not frappe.db.exists("Customer", DEMO_CUSTOMER):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": DEMO_CUSTOMER,
				"customer_type": "Company",
				"customer_group": masters.get("customer_group"),
				"territory": masters.get("territory"),
			}
		).insert()

	if not frappe.db.exists("Supplier", DEMO_SUPPLIER):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": DEMO_SUPPLIER,
				"supplier_group": masters.get("supplier_group"),
			}
		).insert()

	today = nowdate()
	created = []

	si_open = quick_create(
		"Sales Invoice",
		party=DEMO_CUSTOMER,
		items=[{"item_code": DEMO_ITEM, "qty": 100, "rate": 1500}],
		company=company,
		extra={"due_date": add_days(today, 15), "posting_date": today},
		submit=1,
	)
	created.append(si_open.get("name"))

	si_overdue = quick_create(
		"Sales Invoice",
		party=DEMO_CUSTOMER,
		items=[{"item_code": DEMO_ITEM, "qty": 10, "rate": 2500}],
		company=company,
		extra={"due_date": add_days(today, -20), "posting_date": add_days(today, -25), "set_posting_time": 1},
		submit=1,
	)
	created.append(si_overdue.get("name"))

	pi_open = quick_create(
		"Purchase Invoice",
		party=DEMO_SUPPLIER,
		items=[{"item_code": DEMO_ITEM, "qty": 40, "rate": 2000}],
		company=company,
		extra={"due_date": add_days(today, 10), "posting_date": today, "bill_no": "NEXIS-DEMO-BILL"},
		submit=1,
	)
	created.append(pi_open.get("name"))

	pi_overdue = quick_create(
		"Purchase Invoice",
		party=DEMO_SUPPLIER,
		items=[{"item_code": DEMO_ITEM, "qty": 8, "rate": 1500}],
		company=company,
		extra={"due_date": add_days(today, -12), "posting_date": add_days(today, -18), "bill_no": "NEXIS-DEMO-OVERDUE", "set_posting_time": 1},
		submit=1,
	)
	created.append(pi_overdue.get("name"))

	if not frappe.db.exists("Lead", {"lead_name": "Nexis Demo Lead"}):
		frappe.get_doc(
			{"doctype": "Lead", "lead_name": "Nexis Demo Lead", "status": "Open", "email_id": "demo.lead@example.com"}
		).insert()

	if frappe.has_permission("ToDo", "create"):
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Follow up Nexis Demo Customer overdue invoice",
				"date": today,
				"status": "Open",
				"allocated_to": frappe.session.user,
			}
		).insert()

	frappe.db.commit()
	return {
		"ok": True,
		"seeded": True,
		"company": company,
		"documents": created,
		"message": _("Sample customer, supplier, item, two sales invoices, and two purchase invoices are in {0}.").format(
			company
		),
	}
