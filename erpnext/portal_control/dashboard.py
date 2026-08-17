# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Tenant home payload: KPIs, banks, alerts, recent docs. Company-scoped."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate

from erpnext.portal_control.tenancy import get_user_companies, is_super_admin

RECENT_CACHE_PREFIX = "pl_recent|"


def resolve_company(requested: str | None = None) -> str | None:
	allowed = get_user_companies() if not is_super_admin() else frappe.get_all("Company", pluck="name")
	requested = (requested or "").strip()
	if requested and requested in allowed:
		return requested
	default = frappe.defaults.get_user_default("company")
	if default and default in allowed:
		return default
	return allowed[0] if allowed else None


def company_currency(company: str | None) -> str:
	if not company:
		return "PKR"
	return frappe.db.get_value("Company", company, "default_currency") or "PKR"


def _has_field(doctype: str, fieldname: str) -> bool:
	try:
		return bool(frappe.get_meta(doctype).has_field(fieldname))
	except Exception:
		return False


def _invoice_totals(doctype: str, company: str) -> tuple[float, float]:
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return 0.0, 0.0
	today = nowdate()
	row = frappe.db.sql(
		"""
		select
			ifnull(sum(outstanding_amount), 0) as total,
			ifnull(sum(case when due_date is not null and due_date < %s then outstanding_amount else 0 end), 0) as overdue
		from `tab{doctype}`
		where docstatus = 1 and company = %s and outstanding_amount > 0
		""".format(doctype=doctype),
		(today, company),
	)
	if not row:
		return 0.0, 0.0
	return flt(row[0][0]), flt(row[0][1])


def _cash_and_banks(company: str) -> tuple[float, list[dict]]:
	banks: list[dict] = []
	cash = 0.0
	if not frappe.db.exists("DocType", "Account") or not frappe.has_permission("Account", "read"):
		return cash, banks
	try:
		from erpnext.accounts.utils import get_balance_on
	except Exception:
		return cash, banks

	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ("in", ("Cash", "Bank"))},
		fields=["name", "account_name", "account_type", "account_currency"],
		limit=40,
	)
	today = nowdate()
	for acc in accounts:
		try:
			bal = flt(get_balance_on(acc.name, date=today, company=company, in_account_currency=False))
		except Exception:
			bal = 0.0
		if acc.account_type == "Cash":
			cash += bal
		banks.append(
			{
				"name": acc.name,
				"label": acc.account_name or acc.name,
				"kind": acc.account_type,
				"currency": acc.account_currency or company_currency(company),
				"balance": bal,
			}
		)
	return cash, banks


def _recent_from_docs(company: str) -> list[dict]:
	out: list[dict] = []
	pairs = (
		("Sales Invoice", "customer"),
		("Purchase Invoice", "supplier"),
		("Sales Order", "customer"),
		("Purchase Order", "supplier"),
		("Payment Entry", "party"),
		("Quotation", "party_name"),
	)
	for dt, party_field in pairs:
		if not frappe.db.exists("DocType", dt) or not frappe.has_permission(dt, "read"):
			continue
		fields = ["name", "modified"]
		if _has_field(dt, party_field):
			fields.append(party_field)
		if _has_field(dt, "grand_total"):
			fields.append("grand_total")
		filters = {"company": company} if _has_field(dt, "company") else {}
		try:
			rows = frappe.get_all(dt, filters=filters, fields=fields, order_by="modified desc", limit=4)
		except Exception:
			continue
		for r in rows:
			out.append(
				{
					"doctype": dt,
					"name": r.name,
					"title": r.get(party_field) or r.name,
					"when": str(r.modified),
					"amount": flt(r.get("grand_total")),
					"href": _href_for(dt, r.name),
				}
			)
	out.sort(key=lambda x: x["when"], reverse=True)
	return out[:8]


def _recent_from_cache() -> list[dict]:
	raw = frappe.cache().get_value(f"{RECENT_CACHE_PREFIX}{frappe.session.user}") or []
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except Exception:
			raw = []
	if not isinstance(raw, list):
		return []
	out = []
	for item in raw[:8]:
		if not isinstance(item, dict) or not item.get("name"):
			continue
		out.append(
			{
				"doctype": item.get("doctype") or "",
				"name": item.get("name"),
				"title": item.get("title") or item.get("name"),
				"when": item.get("when") or "",
				"amount": flt(item.get("amount")),
				"href": item.get("href") or _href_for(item.get("doctype") or "", item.get("name")),
			}
		)
	return out


def _href_for(doctype: str, name: str) -> str:
	mapping = {
		"Sales Invoice": "/sales/invoices",
		"Sales Order": "/sales/orders",
		"Quotation": "/sales/quotations",
		"Delivery Note": "/sales/delivery",
		"Purchase Invoice": "/purchases/bills",
		"Purchase Order": "/purchases/orders",
		"Purchase Receipt": "/purchases/receipts",
		"Supplier Quotation": "/purchases/rfq",
		"Payment Entry": "/finance/payments",
		"Journal Entry": "/finance/journal",
		"Item": "/products",
		"Customer": "/customers",
		"Lead": "/crm/leads",
		"Opportunity": "/crm/opportunities",
		"Bank Account": "/banking/accounts",
		"Employee": "/hr/employees",
		"ToDo": "/epad",
	}
	base = mapping.get(doctype, "/")
	if base == "/":
		return base
	return f"{base}/{name}"


def _alerts(company: str) -> list[dict]:
	alerts: list[dict] = []
	today = nowdate()
	if frappe.has_permission("Sales Invoice", "read"):
		try:
			n = frappe.db.count(
				"Sales Invoice",
				{
					"docstatus": 1,
					"company": company,
					"outstanding_amount": (">", 0),
					"due_date": ("<", today),
				},
			)
		except Exception:
			n = 0
		if n:
			alerts.append(
				{
					"id": "ar-overdue",
					"tone": "danger",
					"text": _("{0} sales invoice(s) overdue").format(n),
					"href": "/sales/invoices",
				}
			)
	if frappe.has_permission("Purchase Invoice", "read"):
		try:
			n = frappe.db.count(
				"Purchase Invoice",
				{
					"docstatus": 1,
					"company": company,
					"outstanding_amount": (">", 0),
					"due_date": ("<", today),
				},
			)
		except Exception:
			n = 0
		if n:
			alerts.append(
				{
					"id": "ap-overdue",
					"tone": "warning",
					"text": _("{0} purchase bill(s) overdue").format(n),
					"href": "/purchases/bills",
				}
			)
	if frappe.db.exists("DocType", "Notification Log") and frappe.has_permission("Notification Log", "read"):
		try:
			notes = frappe.get_all(
				"Notification Log",
				filters={"for_user": frappe.session.user, "read": 0},
				fields=["name", "subject"],
				order_by="creation desc",
				limit=5,
			)
		except Exception:
			notes = []
		for n in notes:
			alerts.append({"id": n.name, "tone": "info", "text": n.subject or n.name, "href": "/"})
	return alerts[:8]


@frappe.whitelist()
def get_home(company: str | None = None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	company = resolve_company(company)
	currency = company_currency(company)
	receivable = payable = cash = 0.0
	overdue_ar = overdue_ap = 0.0
	banks: list[dict] = []
	recent: list[dict] = []
	alerts: list[dict] = []
	if company:
		try:
			receivable, overdue_ar = _invoice_totals("Sales Invoice", company)
		except Exception:
			frappe.log_error(title="pl_home_ar")
		try:
			payable, overdue_ap = _invoice_totals("Purchase Invoice", company)
		except Exception:
			frappe.log_error(title="pl_home_ap")
		try:
			cash, banks = _cash_and_banks(company)
		except Exception:
			frappe.log_error(title="pl_home_cash")
		try:
			cached = _recent_from_cache()
			docs = _recent_from_docs(company)
			seen = {(r["doctype"], r["name"]) for r in cached}
			recent = cached + [r for r in docs if (r["doctype"], r["name"]) not in seen]
			recent = recent[:8]
		except Exception:
			frappe.log_error(title="pl_home_recent")
		try:
			alerts = _alerts(company)
		except Exception:
			frappe.log_error(title="pl_home_alerts")
	unread = sum(1 for a in alerts if a.get("tone") == "info")
	return {
		"company": company,
		"currency": currency,
		"receivables": {
			"label": "Total Receivables",
			"amount": receivable,
			"overdue": overdue_ar,
			"currency": currency,
		},
		"payables": {
			"label": "Total Payables",
			"amount": payable,
			"overdue": overdue_ap,
			"currency": currency,
		},
		"cash": {"label": "Cash in Hand", "amount": cash, "currency": currency},
		"banks": banks,
		"recent": recent,
		"alerts": alerts,
		"unread_notifications": unread,
	}


@frappe.whitelist()
def set_company(company: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	company = (company or "").strip()
	allowed = get_user_companies() if not is_super_admin() else frappe.get_all("Company", pluck="name")
	if company not in allowed:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.defaults.set_user_default("company", company)
	try:
		if frappe.db.has_column("User", "default_company"):
			frappe.db.set_value("User", frappe.session.user, "default_company", company, update_modified=False)
	except Exception:
		pass
	frappe.clear_cache(user=frappe.session.user)
	return {"company": company}


@frappe.whitelist()
def search(q: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	q = (q or "").strip()
	if len(q) < 2:
		return []
	doctypes = [
		("Customer", "customer_name", "/customers"),
		("Supplier", "supplier_name", "/purchases"),
		("Item", "item_name", "/products"),
		("Sales Invoice", "customer", "/sales/invoices"),
		("Purchase Invoice", "supplier", "/purchases/bills"),
		("Sales Order", "customer", "/sales/orders"),
		("Purchase Order", "supplier", "/purchases/orders"),
		("Lead", "lead_name", "/crm/leads"),
		("Employee", "employee_name", "/hr/employees"),
	]
	hits: list[dict] = []
	for dt, title, href in doctypes:
		if not frappe.db.exists("DocType", dt) or not frappe.has_permission(dt, "read"):
			continue
		or_filters = [["name", "like", f"%{q}%"]]
		if _has_field(dt, title) and title != "name":
			or_filters.append([title, "like", f"%{q}%"])
		try:
			fields = ["name", title] if title != "name" and _has_field(dt, title) else ["name"]
			rows = frappe.get_all(dt, or_filters=or_filters, fields=fields, limit=5)
		except Exception:
			continue
		for r in rows:
			hits.append(
				{
					"doctype": dt,
					"name": r.name,
					"title": r.get(title) or r.name,
					"href": f"{href}/{r.name}",
				}
			)
		if len(hits) >= 20:
			break
	return hits[:20]


@frappe.whitelist()
def record_open(doctype: str, name: str, title: str | None = None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	doctype = (doctype or "").strip()
	name = (name or "").strip()
	if not doctype or not name:
		return {"ok": False}
	item = {
		"doctype": doctype,
		"name": name,
		"title": (title or name).strip(),
		"when": str(now_datetime()),
		"href": _href_for(doctype, name),
	}
	key = f"{RECENT_CACHE_PREFIX}{frappe.session.user}"
	raw = frappe.cache().get_value(key) or []
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except Exception:
			raw = []
	if not isinstance(raw, list):
		raw = []
	raw = [x for x in raw if not (isinstance(x, dict) and x.get("doctype") == doctype and x.get("name") == name)]
	raw.insert(0, item)
	frappe.cache().set_value(key, raw[:12])
	return {"ok": True}


@frappe.whitelist()
def mark_notification_read(name: str | None = None):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	if not frappe.db.exists("DocType", "Notification Log"):
		return {"ok": True}
	filters = {"for_user": frappe.session.user}
	if name:
		filters["name"] = name
	try:
		rows = frappe.get_all("Notification Log", filters=filters, pluck="name", limit=50)
		for row in rows:
			frappe.db.set_value("Notification Log", row, "read", 1, update_modified=False)
	except Exception:
		frappe.log_error(title="pl_mark_notification")
	return {"ok": True}


@frappe.whitelist()
def tax_templates(company: str | None = None):
	"""Live tax templates for the duty/landed-cost calculator."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	company = resolve_company(company)
	if not company or not frappe.db.exists("DocType", "Sales Taxes and Charges Template"):
		return []
	if not frappe.has_permission("Sales Taxes and Charges Template", "read"):
		return []
	rows = frappe.get_all(
		"Sales Taxes and Charges Template",
		filters={"company": company},
		fields=["name", "title"],
		limit=30,
	)
	out = []
	for r in rows:
		try:
			doc = frappe.get_doc("Sales Taxes and Charges Template", r.name)
			taxes = [
				{"charge_type": t.charge_type, "account_head": t.account_head, "rate": flt(t.rate)}
				for t in (doc.taxes or [])
			]
			out.append({"name": r.name, "title": r.title or r.name, "taxes": taxes})
		except Exception:
			continue
	return out
