# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Create / submit common ERPNext documents from the separate frontend."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from erpnext.portal_control.dashboard import resolve_company

def leaf_defaults() -> dict:
	"""Non-group masters so Customer/Item/Supplier inserts validate on this ERPNext."""
	out = {}
	pairs = (
		("customer_group", "Customer Group"),
		("territory", "Territory"),
		("item_group", "Item Group"),
		("supplier_group", "Supplier Group"),
	)
	for key, dt in pairs:
		if not frappe.db.exists("DocType", dt):
			continue
		name = None
		if frappe.get_meta(dt).has_field("is_group"):
			name = frappe.db.get_value(dt, {"is_group": 0}, "name")
		if not name:
			name = frappe.db.get_value(dt, {}, "name")
		if name:
			out[key] = name
	uom = frappe.db.get_value("UOM", {"name": "Nos"}, "name") or frappe.db.get_value("UOM", {}, "name")
	if uom:
		out["stock_uom"] = uom
	return out


PARTY_FIELD = {
	"Sales Invoice": "customer",
	"Sales Order": "customer",
	"Delivery Note": "customer",
	"Quotation": "party_name",
	"Purchase Invoice": "supplier",
	"Purchase Order": "supplier",
	"Purchase Receipt": "supplier",
	"Supplier Quotation": "supplier",
}

ALLOWED_CREATE = frozenset(
	{
		"Customer",
		"Supplier",
		"Item",
		"Lead",
		"Opportunity",
		"Sales Invoice",
		"Sales Order",
		"Quotation",
		"Delivery Note",
		"Purchase Invoice",
		"Purchase Order",
		"Purchase Receipt",
		"Supplier Quotation",
		"Payment Entry",
		"Journal Entry",
		"Stock Entry",
		"ToDo",
		"Employee",
		"Attendance",
		"Leave Application",
		"Bank Account",
		"Warehouse",
	}
)


def _parse(value):
	if isinstance(value, str):
		try:
			return frappe.parse_json(value)
		except Exception:
			return value
	return value


def _require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)


def _set_company(doc: dict, company: str | None):
	company = resolve_company(company)
	if company and frappe.get_meta(doc["doctype"]).has_field("company"):
		doc["company"] = company
	return company


@frappe.whitelist()
def quick_create(
	doctype: str,
	party: str | None = None,
	items: str | list | None = None,
	company: str | None = None,
	extra: str | dict | None = None,
	submit: int | str = 0,
):
	"""Create a document with optional items table. Used by New Invoice / New Bill / etc."""
	_require_login()
	doctype = (doctype or "").strip()
	if doctype not in ALLOWED_CREATE:
		frappe.throw(_("Cannot create {0} from this app").format(doctype))
	if not frappe.has_permission(doctype, "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	doc: dict = {"doctype": doctype}
	extra = _parse(extra) or {}
	if isinstance(extra, dict):
		doc.update(extra)
	masters = leaf_defaults()
	for field, fallback in (
		("customer_group", masters.get("customer_group")),
		("territory", masters.get("territory")),
		("item_group", masters.get("item_group")),
		("supplier_group", masters.get("supplier_group")),
		("stock_uom", masters.get("stock_uom")),
	):
		cur = doc.get(field)
		if fallback and (not cur or str(cur).startswith("All ")):
			doc[field] = fallback
	company = _set_company(doc, company or extra.get("company") if isinstance(extra, dict) else company)

	party_field = PARTY_FIELD.get(doctype)
	if party_field and party:
		doc[party_field] = party
		if doctype == "Quotation":
			doc.setdefault("quotation_to", "Customer")

	item_rows = _parse(items) or []
	if item_rows and frappe.get_meta(doctype).has_field("items"):
		doc["items"] = []
		for row in item_rows:
			if not isinstance(row, dict):
				continue
			line = {
				"item_code": row.get("item_code") or row.get("item"),
				"qty": flt(row.get("qty") or 1),
				"rate": flt(row.get("rate") or 0),
			}
			if row.get("warehouse"):
				line["warehouse"] = row["warehouse"]
			if line["item_code"]:
				doc["items"].append(line)

	if doctype == "Payment Entry":
		_fill_payment(doc, party, company, extra if isinstance(extra, dict) else {})
	elif doctype == "Stock Entry":
		doc.setdefault("stock_entry_type", extra.get("stock_entry_type") if isinstance(extra, dict) else None)
		doc.setdefault("stock_entry_type", "Material Receipt")
		doc.setdefault("purpose", "Material Receipt")
		if item_rows:
			warehouse = (extra.get("warehouse") if isinstance(extra, dict) else None) or _default_warehouse(company)
			doc["items"] = []
			for row in item_rows:
				if not isinstance(row, dict) or not (row.get("item_code") or row.get("item")):
					continue
				doc["items"].append(
					{
						"item_code": row.get("item_code") or row.get("item"),
						"qty": flt(row.get("qty") or 1),
						"t_warehouse": row.get("warehouse") or warehouse,
					}
				)
	elif doctype == "Journal Entry":
		accounts = extra.get("accounts") if isinstance(extra, dict) else None
		if accounts:
			doc["accounts"] = accounts
		doc.setdefault("posting_date", nowdate())
		doc.setdefault("voucher_type", "Journal Entry")

	if frappe.get_meta(doctype).has_field("posting_date") and not doc.get("posting_date"):
		doc["posting_date"] = nowdate()
	if frappe.get_meta(doctype).has_field("transaction_date") and not doc.get("transaction_date"):
		doc["transaction_date"] = nowdate()
	if (
		doc.get("posting_date")
		and str(doc.get("posting_date")) != str(nowdate())
		and frappe.get_meta(doctype).has_field("set_posting_time")
	):
		doc["set_posting_time"] = 1
	_apply_price_list_defaults(doc)

	created = frappe.get_doc(doc)
	created.insert()
	if int(submit or 0) == 1:
		created.submit()
	return created.as_dict()


def _apply_price_list_defaults(doc: dict) -> None:
	from erpnext.portal_control.company_seed import _ensure_price_lists

	_ensure_price_lists()
	company = doc.get("company")
	currency = None
	if company:
		currency = frappe.db.get_value("Company", company, "default_currency")
	if currency:
		doc.setdefault("currency", currency)
		doc.setdefault("price_list_currency", currency)
		doc.setdefault("plc_conversion_rate", 1)
		doc.setdefault("conversion_rate", 1)
	dt = doc.get("doctype")
	if dt in ("Sales Invoice", "Sales Order", "Quotation", "Delivery Note"):
		pl = frappe.db.get_single_value("Selling Settings", "selling_price_list") or frappe.db.get_value(
			"Price List", {"selling": 1, "enabled": 1}, "name"
		)
		if pl:
			doc.setdefault("selling_price_list", pl)
	if dt in ("Purchase Invoice", "Purchase Order", "Purchase Receipt", "Supplier Quotation"):
		pl = frappe.db.get_single_value("Buying Settings", "buying_price_list") or frappe.db.get_value(
			"Price List", {"buying": 1, "enabled": 1}, "name"
		)
		if pl:
			doc.setdefault("buying_price_list", pl)


def _fill_payment(doc: dict, party: str | None, company: str | None, extra: dict):
	payment_type = extra.get("payment_type") or "Receive"
	doc["payment_type"] = payment_type
	doc["posting_date"] = extra.get("posting_date") or nowdate()
	doc["paid_amount"] = flt(extra.get("paid_amount") or extra.get("amount") or 0)
	doc["received_amount"] = flt(extra.get("received_amount") or doc["paid_amount"])
	doc["party_type"] = extra.get("party_type") or ("Customer" if payment_type == "Receive" else "Supplier")
	if party:
		doc["party"] = party
	if not company:
		return
	company_doc = frappe.get_doc("Company", company)
	if payment_type == "Receive":
		doc["paid_from"] = extra.get("paid_from") or company_doc.default_receivable_account
		doc["paid_to"] = extra.get("paid_to") or company_doc.default_cash_account or company_doc.default_bank_account
	else:
		doc["paid_from"] = extra.get("paid_from") or company_doc.default_cash_account or company_doc.default_bank_account
		doc["paid_to"] = extra.get("paid_to") or company_doc.default_payable_account


def _default_warehouse(company: str | None) -> str | None:
	if not company:
		return None
	name = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
	return name


@frappe.whitelist()
def submit_document(doctype: str, name: str):
	_require_login()
	doc = frappe.get_doc(doctype, name)
	doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def cancel_document(doctype: str, name: str):
	_require_login()
	doc = frappe.get_doc(doctype, name)
	doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def delete_document(doctype: str, name: str):
	_require_login()
	frappe.delete_doc(doctype, name)
	return {"ok": True}


@frappe.whitelist()
def save_todo(description: str, date: str | None = None, name: str | None = None, status: str | None = None):
	"""ePad is backed by ToDo until a dedicated DocType exists."""
	_require_login()
	if name and frappe.db.exists("ToDo", name):
		doc = frappe.get_doc("ToDo", name)
		if description:
			doc.description = description
		if date:
			doc.date = date
		if status:
			doc.status = status
		doc.save()
		return doc.as_dict()
	doc = frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": description,
			"date": date or nowdate(),
			"status": status or "Open",
			"allocated_to": frappe.session.user,
		}
	)
	doc.insert()
	return doc.as_dict()


@frappe.whitelist()
def run_named_report(report_name: str, filters: str | dict | None = None):
	_require_login()
	if not frappe.db.exists("Report", report_name):
		frappe.throw(_("Unknown report: {0}").format(report_name))
	if not frappe.has_permission("Report", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	from frappe.desk.query_report import run

	filters = _parse(filters) or {}
	if not isinstance(filters, dict):
		filters = {}
	company = resolve_company(filters.get("company"))
	if company:
		filters["company"] = company
	filters.setdefault("from_date", frappe.defaults.get_user_default("year_start_date") or f"{nowdate()[:4]}-01-01")
	filters.setdefault("to_date", nowdate())
	try:
		return run(report_name, filters=filters)
	except Exception as exc:
		frappe.throw(_("{0}").format(str(exc).split("\n", 1)[0][:240]))


@frappe.whitelist()
def link_options(doctype: str, q: str | None = None, limit: int | str = 20):
	"""Typeahead for Customer / Item / Supplier / Account / Employee / Warehouse."""
	_require_login()
	doctype = (doctype or "").strip()
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return []
	q = (q or "").strip()
	title = {
		"Customer": "customer_name",
		"Supplier": "supplier_name",
		"Item": "item_name",
		"Employee": "employee_name",
		"Account": "account_name",
		"Warehouse": "warehouse_name",
		"Bank Account": "account_name",
		"Lead": "lead_name",
	}.get(doctype, "name")
	filters = {}
	company = resolve_company()
	if company and frappe.get_meta(doctype).has_field("company") and doctype != "Item":
		filters["company"] = company
	fields = ["name"]
	if title != "name" and frappe.get_meta(doctype).has_field(title):
		fields.append(title)
	kwargs = {
		"filters": filters,
		"fields": fields,
		"limit": int(limit or 20),
		"order_by": "modified desc",
	}
	if q:
		or_filters = [["name", "like", f"%{q}%"]]
		if title != "name" and frappe.get_meta(doctype).has_field(title):
			or_filters.append([title, "like", f"%{q}%"])
		kwargs["or_filters"] = or_filters
	rows = frappe.get_all(doctype, **kwargs)
	return [{"name": r.name, "label": r.get(title) or r.name} for r in rows]
