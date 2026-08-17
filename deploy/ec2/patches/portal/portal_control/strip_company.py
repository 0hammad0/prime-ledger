# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _

from erpnext.portal_control.tenancy import SUPER_ADMIN_ROLES, is_super_admin


def start_strip(keep_company: str):
	keep_company = (keep_company or "").strip()
	if not keep_company:
		frappe.throw(_("keep_company is required"))
	if not frappe.db.exists("Company", keep_company):
		frappe.throw(_("Unknown company: {0}").format(keep_company))

	stripped = []
	for company in frappe.get_all("Company", pluck="name"):
		if company == keep_company:
			continue
		disabled = _disable_other_company_users(keep_company, company)
		tdr_name = _enqueue_tdr(company)
		stripped.append({"company": company, "tdr": tdr_name, "disabled_users": disabled})

	_mark_keep_default(keep_company)
	frappe.db.commit()
	return {"ok": True, "keep_company": keep_company, "stripped": stripped}


def strip_status():
	rows = frappe.get_all(
		"Transaction Deletion Record",
		fields=["name", "company", "status", "docstatus"],
		order_by="creation desc",
	)
	return {"ok": True, "records": rows}


def finish_strip(keep_company: str):
	keep_company = (keep_company or "").strip()
	if not keep_company:
		frappe.throw(_("keep_company is required"))

	results = []
	for company in frappe.get_all("Company", pluck="name"):
		if company == keep_company:
			continue
		tdrs = frappe.get_all(
			"Transaction Deletion Record",
			filters={"company": company},
			fields=["name", "status", "docstatus"],
			order_by="creation desc",
			limit=1,
		)
		status = tdrs[0]["status"] if tdrs else None
		entry = {
			"company": company,
			"tdr": tdrs[0]["name"] if tdrs else None,
			"status": status,
			"deleted": False,
		}
		if status == "Completed":
			try:
				frappe.delete_doc("Company", company, ignore_permissions=True, force=1)
				entry["deleted"] = True
			except Exception as e:
				entry["error"] = str(e)
		results.append(entry)

	_mark_keep_default(keep_company)
	frappe.db.commit()
	return {"ok": True, "keep_company": keep_company, "results": results}


def _disable_other_company_users(keep_company: str, stripped_company: str) -> list[str]:
	users = frappe.get_all(
		"User Permission",
		filters={"allow": "Company", "for_value": stripped_company},
		pluck="user",
	)
	keep_users = set(
		frappe.get_all(
			"User Permission",
			filters={"allow": "Company", "for_value": keep_company},
			pluck="user",
		)
	)
	disabled = []
	seen: set[str] = set()
	for user in users:
		if not user or user in seen:
			continue
		seen.add(user)
		if user == "Administrator":
			continue
		if is_super_admin(user):
			continue
		if set(frappe.get_roles(user)) & SUPER_ADMIN_ROLES:
			continue
		if user in keep_users:
			continue
		frappe.db.set_value("User", user, "enabled", 0)
		disabled.append(user)
	return disabled


def _enqueue_tdr(company: str) -> str:
	existing = frappe.get_all(
		"Transaction Deletion Record",
		filters={"company": company, "docstatus": 1, "status": ("in", ["Queued", "Running"])},
		pluck="name",
		limit=1,
	)
	if existing:
		return existing[0]

	tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
	tdr.insert(ignore_permissions=True)
	tdr.generate_to_delete_list()
	tdr.reload()
	tdr.submit()
	return tdr.name


def _mark_keep_default(keep_company: str) -> None:
	try:
		frappe.db.set_single_value("Global Defaults", "default_company", keep_company)
	except Exception:
		pass
	try:
		frappe.defaults.set_global_default("company", keep_company)
	except Exception:
		pass
