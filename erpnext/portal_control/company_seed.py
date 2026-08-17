# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe


def ensure_org_company(
	org_name: str | None = None,
	country: str | None = None,
	currency: str | None = None,
	abbr: str | None = None,
	chart_of_accounts: str | None = None,
):
	org_name = (org_name or "My Company").strip()
	if frappe.db.count("Company"):
		existing = frappe.get_all("Company", pluck="name", limit=1)[0]
		_mark_setup_complete(existing)
		return {"ok": True, "existing": existing}

	country = (
		country
		or frappe.db.get_single_value("System Settings", "country")
		or "Pakistan"
	).strip()
	currency = (
		currency
		or frappe.db.get_single_value("Global Defaults", "default_currency")
		or "PKR"
	).strip()
	abbr = (abbr or _company_abbr(org_name)).strip()
	n = 0
	base = abbr
	while frappe.db.exists("Company", {"abbr": abbr}):
		n += 1
		abbr = f"{base}{n}"
	if not chart_of_accounts:
		chart_of_accounts = "Standard"

	_ensure_fixtures(country)

	payload = {
		"doctype": "Company",
		"company_name": org_name,
		"abbr": abbr,
		"country": country,
		"default_currency": currency,
		"create_chart_of_accounts_based_on": "Standard Template",
		"chart_of_accounts": chart_of_accounts,
		"enable_perpetual_inventory": 1,
	}

	doc = _try_insert(payload)
	if doc is None:
		existing_chart = None
		try:
			rows = frappe.get_all("Company", fields=["chart_of_accounts"], limit=1)
			if rows and rows[0].get("chart_of_accounts"):
				existing_chart = rows[0]["chart_of_accounts"]
		except Exception:
			existing_chart = None
		if existing_chart:
			payload["chart_of_accounts"] = existing_chart
			doc = _try_insert(payload)

	if doc is None:
		charts = ["Standard"]
		try:
			from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import (
				get_charts_for_country,
			)

			found = get_charts_for_country(country) or []
			if found:
				charts = found
		except Exception:
			pass
		payload["create_chart_of_accounts_based_on"] = "Standard Template"
		payload["chart_of_accounts"] = charts[0]
		doc = frappe.get_doc(payload)
		doc.insert(ignore_permissions=True)

	_mark_setup_complete(doc.name)
	_ensure_fiscal_year(doc.name)
	_ensure_price_lists()
	frappe.db.commit()
	return {"ok": True, "created": doc.name, "abbr": abbr}


def _ensure_fixtures(country: str) -> None:
	"""Install ERPNext setup fixtures so Company.insert can create warehouses."""
	try:
		from erpnext.setup.setup_wizard.operations.install_fixtures import install as install_fixtures

		install_fixtures(country)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
	if not frappe.db.exists("Warehouse Type", "Transit"):
		try:
			wt = frappe.new_doc("Warehouse Type")
			if wt.meta.get_field("warehouse_type"):
				wt.warehouse_type = "Transit"
			wt.name = "Transit"
			wt.insert(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()


def _try_insert(payload: dict):
	try:
		doc = frappe.get_doc(payload)
		doc.insert(ignore_permissions=True)
		return doc
	except Exception:
		frappe.db.rollback()
		return None


def _company_abbr(org_name: str) -> str:
	parts = [p for p in (org_name or "").split() if p]
	letters = "".join(p[0] for p in parts[:4]).upper()
	return letters[:5] or "CO"


def _mark_setup_complete(company: str) -> None:
	try:
		frappe.db.set_single_value("System Settings", "setup_complete", 1)
	except Exception:
		pass
	try:
		frappe.db.set_single_value("Global Defaults", "default_company", company)
	except Exception:
		pass
	try:
		frappe.defaults.set_global_default("company", company)
	except Exception:
		pass
	_ensure_fiscal_year(company)
	_ensure_price_lists()


def _ensure_fiscal_year(company: str) -> None:
	"""Every new company must be on a Fiscal Year that covers today, or invoices cannot post."""
	from frappe.utils import getdate

	today = getdate()
	rows = frappe.get_all(
		"Fiscal Year",
		fields=["name", "year_start_date", "year_end_date", "disabled"],
	)
	covering = [
		r
		for r in rows
		if not int(r.disabled or 0)
		and r.year_start_date
		and r.year_end_date
		and getdate(r.year_start_date) <= today <= getdate(r.year_end_date)
	]
	if not covering:
		year = str(today.year)
		if not frappe.db.exists("Fiscal Year", year):
			doc = frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": year,
					"year_start_date": f"{today.year}-01-01",
					"year_end_date": f"{today.year}-12-31",
				}
			)
			doc.append("companies", {"company": company})
			doc.insert(ignore_permissions=True)
			return
		covering = [{"name": year}]
	for r in covering:
		doc = frappe.get_doc("Fiscal Year", r["name"])
		have = {c.company for c in (doc.companies or [])}
		if company not in have:
			doc.append("companies", {"company": company})
			doc.save(ignore_permissions=True)


def _ensure_price_lists() -> None:
	for name, selling, buying in (("Standard Selling", 1, 0), ("Standard Buying", 0, 1)):
		if frappe.db.exists("Price List", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": name,
				"selling": selling,
				"buying": buying,
				"enabled": 1,
				"currency": frappe.db.get_single_value("Global Defaults", "default_currency") or "PKR",
			}
		).insert(ignore_permissions=True)
	try:
		if not frappe.db.get_single_value("Selling Settings", "selling_price_list"):
			frappe.db.set_single_value("Selling Settings", "selling_price_list", "Standard Selling")
		if not frappe.db.get_single_value("Buying Settings", "buying_price_list"):
			frappe.db.set_single_value("Buying Settings", "buying_price_list", "Standard Buying")
	except Exception:
		pass
