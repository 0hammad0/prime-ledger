"""Full post-wizard audit + heal. Run via: bench --site <site> execute audit_onboarding.run"""

import frappe
from frappe.utils import cint, nowdate


def _set_company(company, values):
    values = {k: v for k, v in values.items() if v}
    if values:
        frappe.db.set_value("Company", company, values, update_modified=False)
    return values


def heal(company_name=None):
    companies = frappe.get_all(
        "Company",
        fields=["name", "abbr", "country", "default_currency"],
        limit=1,
    )
    if not companies:
        return {"status": "SKIP", "reason": "no company"}

    company = company_name or companies[0].name
    meta = frappe.get_meta("Company")
    c = frappe.get_doc("Company", company)
    currency = c.default_currency or "PKR"
    country = c.country or "Pakistan"
    abbr = c.abbr

    # Account currencies
    for acc in frappe.get_all(
        "Account",
        filters={"company": company, "account_currency": ("!=", currency)},
        pluck="name",
    ):
        if not frappe.db.exists("GL Entry", {"account": acc}):
            frappe.db.set_value("Account", acc, "account_currency", currency, update_modified=False)

    # Leaf bank
    bank_group = frappe.db.get_value(
        "Account", {"company": company, "account_type": "Bank", "is_group": 1}, "name"
    )
    bank = frappe.db.get_value(
        "Account", {"company": company, "account_type": "Bank", "is_group": 0}, "name"
    )
    if not bank and bank_group:
        bank = (
            frappe.get_doc(
                {
                    "doctype": "Account",
                    "account_name": "Bank Account",
                    "parent_account": bank_group,
                    "company": company,
                    "is_group": 0,
                    "account_type": "Bank",
                    "account_currency": currency,
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    cash = frappe.db.get_value(
        "Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name"
    )

    def acc(account_type=None, account_name=None, root_type=None, exclude_types=None):
        filters = {"company": company, "is_group": 0}
        if account_type:
            filters["account_type"] = account_type
        if account_name:
            filters["account_name"] = account_name
        if root_type:
            filters["root_type"] = root_type
        name = frappe.db.get_value("Account", filters, "name")
        if name or not exclude_types:
            return name
        rows = frappe.get_all(
            "Account",
            filters={"company": company, "is_group": 0, "root_type": root_type or "Expense"},
            fields=["name", "account_type"],
        )
        for r in rows:
            if r.account_type not in exclude_types:
                return r.name
        return rows[0].name if rows else None

    updates = {
        "default_bank_account": c.default_bank_account or bank,
        "default_cash_account": c.default_cash_account or cash,
        "default_receivable_account": c.default_receivable_account
        or acc(account_type="Receivable"),
        "default_payable_account": c.default_payable_account or acc(account_type="Payable"),
        "default_income_account": c.default_income_account
        or acc(account_name="Sales")
        or acc(root_type="Income"),
        "default_expense_account": c.default_expense_account
        or acc(account_name="Administrative Expenses")
        or acc(root_type="Expense", exclude_types=["Cost of Goods Sold", "Depreciation"]),
        "cost_center": c.cost_center
        or frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name"),
        "default_inventory_account": c.default_inventory_account or acc(account_type="Stock"),
        "stock_received_but_not_billed": c.stock_received_but_not_billed
        or acc(account_type="Stock Received But Not Billed"),
        "stock_adjustment_account": c.stock_adjustment_account
        or acc(account_type="Stock Adjustment"),
        "round_off_account": c.round_off_account or acc(account_type="Round Off"),
        "write_off_account": c.write_off_account
        or acc(account_name="Write Off")
        or acc(account_type="Expense Account")
        or acc(account_name="Administrative Expenses"),
        "exchange_gain_loss_account": c.exchange_gain_loss_account
        or acc(account_name="Exchange Gain/Loss"),
    }
    if meta.has_field("expenses_included_in_valuation"):
        updates["expenses_included_in_valuation"] = c.get("expenses_included_in_valuation") or acc(
            account_type="Expenses Included In Valuation"
        )
    if meta.has_field("default_discount_account") and not c.get("default_discount_account"):
        updates["default_discount_account"] = acc(account_name="Write Off") or updates[
            "write_off_account"
        ]

    # Terms
    if not frappe.db.exists("Terms and Conditions", "Standard Terms"):
        frappe.get_doc(
            {
                "doctype": "Terms and Conditions",
                "title": "Standard Terms",
                "selling": 1,
                "buying": 1,
                "terms": "<p>Payment is due as per the agreed payment terms.</p>",
            }
        ).insert(ignore_permissions=True)
    if frappe.db.exists("Terms and Conditions", "Standard Terms"):
        updates["default_selling_terms"] = c.default_selling_terms or "Standard Terms"
        updates["default_buying_terms"] = c.default_buying_terms or "Standard Terms"

    _set_company(company, updates)

    # Price lists
    for name, buying, selling in (("Standard Buying", 1, 0), ("Standard Selling", 0, 1)):
        if not frappe.db.exists("Price List", name):
            frappe.get_doc(
                {
                    "doctype": "Price List",
                    "price_list_name": name,
                    "enabled": 1,
                    "buying": buying,
                    "selling": selling,
                    "currency": currency,
                }
            ).insert(ignore_permissions=True)
        elif frappe.db.get_value("Price List", name, "currency") != currency:
            frappe.db.set_value("Price List", name, "currency", currency)

    # Address template
    if frappe.db.exists("Address Template", country):
        frappe.db.sql("update `tabAddress Template` set is_default=0")
        frappe.db.set_value("Address Template", country, "is_default", 1)

    # MoP
    bank = frappe.db.get_value("Company", company, "default_bank_account") or bank
    cash = frappe.db.get_value("Company", company, "default_cash_account") or cash
    for mop_name, account in {
        "Cash": cash,
        "Cheque": bank,
        "Check": bank,
        "Wire Transfer": bank,
        "Bank Draft": bank,
        "Credit Card": bank,
    }.items():
        if not account or not frappe.db.exists("Mode of Payment", mop_name):
            continue
        mop = frappe.get_doc("Mode of Payment", mop_name)
        rows = [r for r in mop.accounts if r.company == company]
        if rows:
            for row in rows:
                row.default_account = account
        else:
            mop.append("accounts", {"company": company, "default_account": account})
        mop.save(ignore_permissions=True)

    # Payment terms
    if not frappe.db.exists("Payment Term", "Net 30"):
        frappe.get_doc(
            {
                "doctype": "Payment Term",
                "payment_term_name": "Net 30",
                "due_date_based_on": "Day(s) after invoice date",
                "credit_days": 30,
                "description": "Payment due within 30 days",
            }
        ).insert(ignore_permissions=True)
    if not frappe.db.exists("Payment Terms Template", "Default Payment Terms"):
        frappe.get_doc(
            {
                "doctype": "Payment Terms Template",
                "template_name": "Default Payment Terms",
                "terms": [
                    {
                        "payment_term": "Net 30",
                        "description": "Net 30",
                        "invoice_portion": 100,
                        "due_date_based_on": "Day(s) after invoice date",
                        "credit_days": 30,
                    }
                ],
            }
        ).insert(ignore_permissions=True)

    # Warehouse default
    stores = frappe.db.get_value(
        "Warehouse", {"warehouse_name": "Stores", "company": company}, "name"
    ) or frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
    if stores:
        frappe.db.set_single_value("Stock Settings", "default_warehouse", stores)

    # Seal + defaults
    for app in ("frappe", "erpnext"):
        if frappe.db.exists("Installed Application", {"app_name": app}):
            frappe.db.set_value(
                "Installed Application", {"app_name": app}, "is_setup_complete", 1
            )

    ss = frappe.get_doc("System Settings")
    ss.country = ss.country or country
    ss.currency = ss.currency or currency
    ss.time_zone = ss.time_zone or "Asia/Karachi"
    ss.language = ss.language or "en"
    ss.app_name = ss.app_name or "Prime Ledger"
    if hasattr(ss, "setup_complete"):
        ss.setup_complete = 1
    ss.flags.ignore_mandatory = True
    ss.save(ignore_permissions=True)

    gd = frappe.get_doc("Global Defaults")
    gd.default_company = company
    gd.default_currency = currency
    gd.country = country
    gd.flags.ignore_mandatory = True
    gd.save(ignore_permissions=True)

    fy = frappe.db.get_value(
        "Fiscal Year",
        {
            "disabled": 0,
            "year_start_date": ("<=", nowdate()),
            "year_end_date": (">=", nowdate()),
        },
        "name",
    ) or frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")
    frappe.db.set_default("company", company)
    frappe.db.set_default("country", country)
    frappe.db.set_default("currency", currency)
    if fy:
        frappe.db.set_default("fiscal_year", fy)

    for code in ("PKR", "USD", "EUR", "GBP", "AED", "SAR", "INR"):
        if frappe.db.exists("Currency", code):
            frappe.db.set_value("Currency", code, "enabled", 1)

    frappe.clear_cache()
    frappe.db.commit()
    return {"status": "HEALED", "company": company, "currency": currency}


def audit():
    missing = []
    ok = []

    def check(label, condition, detail=""):
        line = f"{label}" + (f" | {detail}" if detail else "")
        (ok if condition else missing).append(line)

    if not frappe.get_all("Company", limit=1):
        return {"missing": ["company"], "ok": []}

    c = frappe.get_doc("Company", frappe.get_all("Company", pluck="name", limit=1)[0])
    company = c.name
    currency = c.default_currency
    country = c.country
    meta = frappe.get_meta("Company")

    check("setup_complete", frappe.is_setup_complete())
    for app in ("frappe", "erpnext"):
        sealed = cint(
            frappe.db.get_value("Installed Application", {"app_name": app}, "is_setup_complete")
        )
        check(f"app_sealed:{app}", sealed)

    required_fields = [
        "country",
        "default_currency",
        "abbr",
        "default_bank_account",
        "default_cash_account",
        "default_receivable_account",
        "default_payable_account",
        "default_income_account",
        "default_expense_account",
        "cost_center",
        "default_inventory_account",
        "stock_received_but_not_billed",
        "stock_adjustment_account",
        "round_off_account",
        "write_off_account",
        "exchange_gain_loss_account",
        "default_selling_terms",
        "default_buying_terms",
    ]
    if meta.has_field("expenses_included_in_valuation"):
        required_fields.append("expenses_included_in_valuation")

    for field in required_fields:
        check(f"company.{field}", bool(c.get(field)), str(c.get(field)))

    wrong = frappe.db.count(
        "Account", {"company": company, "account_currency": ("!=", currency)}
    )
    check("accounts_currency_match", wrong == 0, f"wrong={wrong}")

    for atype in (
        "Receivable",
        "Payable",
        "Cash",
        "Bank",
        "Stock",
        "Cost of Goods Sold",
        "Stock Received But Not Billed",
        "Stock Adjustment",
        "Round Off",
    ):
        n = frappe.db.count(
            "Account", {"company": company, "account_type": atype, "is_group": 0}
        )
        check(f"account_type:{atype}", n > 0, str(n))

    check(
        "income_leaves",
        frappe.db.count("Account", {"company": company, "root_type": "Income", "is_group": 0}) > 0,
    )
    check(
        "expense_leaves",
        frappe.db.count("Account", {"company": company, "root_type": "Expense", "is_group": 0}) > 0,
    )
    check(
        "cost_center_leaf",
        frappe.db.count("Cost Center", {"company": company, "is_group": 0}) > 0,
    )
    check(
        "warehouse_leaf",
        frappe.db.count("Warehouse", {"company": company, "is_group": 0}) > 0,
    )
    check(
        "stock_default_warehouse",
        bool(frappe.db.get_single_value("Stock Settings", "default_warehouse")),
        str(frappe.db.get_single_value("Stock Settings", "default_warehouse")),
    )

    fy = frappe.db.get_value(
        "Fiscal Year",
        {
            "disabled": 0,
            "year_start_date": ("<=", nowdate()),
            "year_end_date": (">=", nowdate()),
        },
        "name",
    )
    check("fiscal_year_current", bool(fy), str(fy))
    check("default.company", frappe.db.get_default("company") == company)
    check("default.currency", frappe.db.get_default("currency") == currency)
    check("default.fiscal_year", bool(frappe.db.get_default("fiscal_year")))

    ss = frappe.get_doc("System Settings")
    check("system.country", bool(ss.country), ss.country)
    check("system.currency", bool(ss.currency), ss.currency)
    check("system.time_zone", bool(ss.time_zone), ss.time_zone)
    check("currency_enabled:PKR", cint(frappe.db.get_value("Currency", "PKR", "enabled")))

    for dt, filters in [
        ("Item Group", None),
        ("Customer Group", None),
        ("Supplier Group", None),
        ("Territory", None),
        ("UOM", None),
        ("Sales Taxes and Charges Template", {"company": company}),
        ("Purchase Taxes and Charges Template", {"company": company}),
        ("Terms and Conditions", None),
        ("Payment Terms Template", None),
        ("Payment Term", None),
        ("Price List", None),
        ("Mode of Payment", None),
        ("Address Template", {"country": country}),
    ]:
        check(f"master:{dt}", frappe.db.count(dt, filters or None) > 0)

    for pl in frappe.get_all("Price List", fields=["name", "currency"]):
        check(f"price_list:{pl.name}", pl.currency == currency, pl.currency)

    check(
        "address_default",
        cint(frappe.db.get_value("Address Template", {"country": country}, "is_default")),
    )

    for mop in ("Cash", "Cheque", "Wire Transfer", "Credit Card", "Bank Draft"):
        if not frappe.db.exists("Mode of Payment", mop):
            missing.append(f"mop_exists:{mop}")
            continue
        rows = frappe.get_all(
            "Mode of Payment Account",
            filters={"parent": mop, "company": company},
            fields=["default_account"],
        )
        check(f"mop_linked:{mop}", bool(rows and rows[0].default_account), str(rows))

    broken = frappe.db.sql(
        """
        select count(*) from tabAccount
        where company=%s and (lft is null or rgt is null or lft=0 or rgt=0 or lft>=rgt)
        """,
        company,
    )[0][0]
    check("account_nestedset", broken == 0, f"broken={broken}")

    return {
        "company": company,
        "currency": currency,
        "country": country,
        "missing_count": len(missing),
        "ok_count": len(ok),
        "missing": missing,
        "ok": ok,
    }


def run():
    heal_result = heal()
    audit_result = audit()
    return {"heal": heal_result, "audit": audit_result}
