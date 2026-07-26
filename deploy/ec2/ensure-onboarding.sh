#!/usr/bin/env bash
# Heal post-setup onboarding gaps on a running site (safe to re-run).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
SITE_NAME="${SITE_NAME:-frontend}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi
SITE_NAME="${SITE_NAME:-frontend}"

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

echo "==> Ensuring onboarding defaults for site: $SITE_NAME"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" console <<'PY'
import frappe
from frappe.desk.page.setup_wizard.setup_wizard import enable_setup_wizard_complete
from frappe.utils.nestedset import rebuild_tree
from frappe.utils import nowdate

companies = frappe.get_all(
    "Company", fields=["name", "country", "default_currency", "abbr"], limit=1
)
if not companies:
    print("SKIP: no company — setup wizard still required")
else:
    company = companies[0]
    print("company", company.name, company.country, company.default_currency)

    # Mark apps complete so wizard does not reopen
    for app in ("frappe", "erpnext"):
        try:
            enable_setup_wizard_complete(app)
        except Exception as e:
            print("enable_setup", app, e)

    # System Settings
    ss = frappe.get_doc("System Settings")
    ss.country = ss.country or company.country or "Pakistan"
    ss.currency = ss.currency or company.default_currency or "PKR"
    ss.time_zone = ss.time_zone or "Asia/Karachi"
    ss.language = ss.language or "en"
    if hasattr(ss, "setup_complete"):
        ss.setup_complete = 1
    ss.enable_onboarding = 1
    ss.app_name = ss.app_name or "Prime Ledger"
    ss.flags.ignore_mandatory = True
    ss.save(ignore_permissions=True)

    # Global Defaults
    gd = frappe.get_doc("Global Defaults")
    gd.default_company = company.name
    gd.default_currency = company.default_currency or ss.currency
    gd.country = company.country or ss.country
    gd.flags.ignore_mandatory = True
    gd.save(ignore_permissions=True)

    # Defaults / home
    frappe.db.set_default("company", company.name)
    frappe.db.set_default("country", company.country or ss.country)
    frappe.db.set_default("currency", company.default_currency or ss.currency)
    frappe.db.set_default("desktop:home_page", "workspace")

    # Fiscal year default
    fy = frappe.db.get_value(
        "Fiscal Year",
        {"disabled": 0, "year_start_date": ("<=", nowdate()), "year_end_date": (">=", nowdate())},
        "name",
    ) or frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")
    if fy:
        frappe.db.set_default("fiscal_year", fy)
        print("fiscal_year", fy)

    # Ensure regional currencies are enabled (Pakistan → PKR must be selectable)
    for code, meta in {
        "PKR": {"symbol": "Rs", "fraction": "Paisa", "fraction_units": 100, "symbol_on_right": 1},
        "USD": {},
        "EUR": {},
        "GBP": {},
        "AED": {},
        "SAR": {},
        "INR": {},
    }.items():
        if frappe.db.exists("Currency", code):
            frappe.db.set_value("Currency", code, "enabled", 1)
            for k, v in meta.items():
                frappe.db.set_value("Currency", code, k, v)
        elif code == "PKR":
            frappe.get_doc(
                {
                    "doctype": "Currency",
                    "currency_name": "PKR",
                    "enabled": 1,
                    "symbol": "Rs",
                    "symbol_on_right": 1,
                    "fraction": "Paisa",
                    "fraction_units": 100,
                    "number_format": "#,###.##",
                }
            ).insert(ignore_permissions=True)
            print("created currency PKR")
    if (company.country or "").lower() == "pakistan":
        if company.default_currency != "PKR":
            frappe.db.set_value("Company", company.name, "default_currency", "PKR")
            company.default_currency = "PKR"
            print("forced company currency PKR")

    # Price lists (create or align currency to company)
    currency = company.default_currency or ss.currency or "PKR"
    for name, buying, selling in (
        ("Standard Buying", 1, 0),
        ("Standard Selling", 0, 1),
    ):
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
            print("created price list", name)
        elif frappe.db.get_value("Price List", name, "currency") != currency:
            frappe.db.set_value("Price List", name, "currency", currency)
            print("price_list_currency", name, currency)

    # Stock settings warehouse
    stores = frappe.db.get_value(
        "Warehouse", {"warehouse_name": "Stores", "company": company.name}, "name"
    ) or frappe.db.get_value("Warehouse", {"company": company.name, "is_group": 0}, "name")
    if stores:
        frappe.db.set_single_value("Stock Settings", "default_warehouse", stores)
        print("default_warehouse", stores)

    # Account currencies must match company (wizard can leave USD on a PKR company)
    wrong_ccy = frappe.get_all(
        "Account",
        filters={"company": company.name, "account_currency": ("!=", currency)},
        pluck="name",
    )
    fixed_ccy = 0
    for acc_name in wrong_ccy:
        if frappe.db.exists("GL Entry", {"account": acc_name}):
            print("skip_ccy_gl", acc_name)
            continue
        frappe.db.set_value("Account", acc_name, "account_currency", currency, update_modified=False)
        fixed_ccy += 1
    if fixed_ccy:
        print("fixed_account_currency", fixed_ccy)

    # Default address template for company country
    country = company.country or ss.country
    if country and frappe.db.exists("Address Template", country):
        frappe.db.sql("update `tabAddress Template` set is_default=0")
        frappe.db.set_value("Address Template", country, "is_default", 1)
        print("default_address_template", country)

    # Ensure a leaf bank account + company cash/bank defaults
    bank_group = frappe.db.get_value(
        "Account", {"company": company.name, "account_type": "Bank", "is_group": 1}, "name"
    )
    bank = frappe.db.get_value(
        "Account", {"company": company.name, "account_type": "Bank", "is_group": 0}, "name"
    )
    if not bank and bank_group:
        bank_doc = frappe.get_doc(
            {
                "doctype": "Account",
                "account_name": "Bank Account",
                "parent_account": bank_group,
                "company": company.name,
                "is_group": 0,
                "account_type": "Bank",
                "account_currency": currency,
            }
        )
        bank_doc.insert(ignore_permissions=True)
        bank = bank_doc.name
        print("created_bank", bank)

    cash = frappe.db.get_value(
        "Account", {"company": company.name, "account_type": "Cash", "is_group": 0}, "name"
    )
    company_updates = {}
    if bank and not frappe.db.get_value("Company", company.name, "default_bank_account"):
        company_updates["default_bank_account"] = bank
    if cash and not frappe.db.get_value("Company", company.name, "default_cash_account"):
        company_updates["default_cash_account"] = cash
    if company_updates:
        frappe.db.set_value("Company", company.name, company_updates, update_modified=False)
        print("company_defaults", company_updates)
    bank = bank or frappe.db.get_value("Company", company.name, "default_bank_account")
    cash = cash or frappe.db.get_value("Company", company.name, "default_cash_account")

    # Fill remaining company accounting defaults if empty
    def _acc(account_type=None, account_name=None, root_type=None):
        filters = {"company": company.name, "is_group": 0}
        if account_type:
            filters["account_type"] = account_type
        if account_name:
            filters["account_name"] = account_name
        if root_type:
            filters["root_type"] = root_type
        return frappe.db.get_value("Account", filters, "name")

    extra = {}
    field_sources = {
        "default_receivable_account": lambda: _acc(account_type="Receivable"),
        "default_payable_account": lambda: _acc(account_type="Payable"),
        "default_income_account": lambda: _acc(account_name="Sales") or _acc(root_type="Income"),
        "default_expense_account": lambda: _acc(account_name="Administrative Expenses")
        or _acc(root_type="Expense"),
        "cost_center": lambda: frappe.db.get_value(
            "Cost Center", {"company": company.name, "is_group": 0}, "name"
        ),
        "default_inventory_account": lambda: _acc(account_type="Stock"),
        "stock_received_but_not_billed": lambda: _acc(account_type="Stock Received But Not Billed"),
        "stock_adjustment_account": lambda: _acc(account_type="Stock Adjustment"),
        "round_off_account": lambda: _acc(account_type="Round Off"),
        "write_off_account": lambda: _acc(account_name="Write Off")
        or _acc(account_name="Administrative Expenses"),
        "exchange_gain_loss_account": lambda: _acc(account_name="Exchange Gain/Loss"),
    }
    for field, finder in field_sources.items():
        if not frappe.db.get_value("Company", company.name, field):
            value = finder()
            if value:
                extra[field] = value
    if extra:
        frappe.db.set_value("Company", company.name, extra, update_modified=False)
        print("company_account_defaults", extra)

    # Mode of Payment → company default accounts
    mop_map = {
        "Cash": cash,
        "Cheque": bank,
        "Check": bank,
        "Wire Transfer": bank,
        "Bank Draft": bank,
        "Credit Card": bank,
    }
    for mop_name, account in mop_map.items():
        if not account or not frappe.db.exists("Mode of Payment", mop_name):
            continue
        mop = frappe.get_doc("Mode of Payment", mop_name)
        rows = [r for r in mop.accounts if r.company == company.name]
        if rows:
            for row in rows:
                row.default_account = account
        else:
            mop.append("accounts", {"company": company.name, "default_account": account})
        mop.save(ignore_permissions=True)
        print("mop", mop_name, account)

    # Payment Term / Template
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
        print("created payment term Net 30")
    if not frappe.db.exists("Payment Terms Template", "Default Payment Terms"):
        frappe.get_doc(
            {
                "doctype": "Payment Terms Template",
                "template_name": "Default Payment Terms",
                "allocate_payment_based_on_payment_terms": 0,
                "terms": [
                    {
                        "doctype": "Payment Terms Template Detail",
                        "payment_term": "Net 30" if frappe.db.exists("Payment Term", "Net 30") else None,
                        "description": "Net 30",
                        "invoice_portion": 100,
                        "due_date_based_on": "Day(s) after invoice date",
                        "credit_days": 30,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        print("created payment terms template")

    # Standard buying/selling terms
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
        print("created terms")
    if frappe.db.exists("Terms and Conditions", "Standard Terms"):
        term_updates = {}
        if not frappe.db.get_value("Company", company.name, "default_selling_terms"):
            term_updates["default_selling_terms"] = "Standard Terms"
        if not frappe.db.get_value("Company", company.name, "default_buying_terms"):
            term_updates["default_buying_terms"] = "Standard Terms"
        if term_updates:
            frappe.db.set_value("Company", company.name, term_updates, update_modified=False)

    # Nested set heal
    for dt in ("Item Group", "Territory", "Customer Group", "Supplier Group", "Sales Person", "Warehouse", "Account", "Cost Center"):
        try:
            if frappe.db.count(dt):
                rebuild_tree(dt)
                print("rebuilt", dt)
        except Exception as e:
            print("rebuild_skip", dt, e)

    # Website branding
    try:
        frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")
    except Exception:
        pass

    frappe.clear_cache()
    frappe.db.commit()
    print("ONBOARDING_OK")

print("setup_complete", frappe.is_setup_complete())
print("apps", frappe.get_all("Installed Application", fields=["app_name", "is_setup_complete"]))
PY

# Users / roles (bench execute — safe for SSH/CI; no console stdin issues)
USERS_SRC="${SCRIPT_DIR}/patches/ensure_users.py"
if [[ -f "$USERS_SRC" ]]; then
  echo "==> Ensuring admin + new-user role profiles"
  if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
  else
    DOCKER=(sudo docker)
  fi
  BACKEND_CID="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q backend | head -n1 || true)"
  if [[ -n "${BACKEND_CID:-}" ]]; then
    "${DOCKER[@]}" cp "$USERS_SRC" \
      "${BACKEND_CID}:/home/frappe/frappe-bench/apps/erpnext/erpnext/setup/ensure_users.py"
    for f in grant_admin_roles.py user_onboarding.py; do
      [[ -f "${SCRIPT_DIR}/patches/$f" ]] || continue
      "${DOCKER[@]}" cp "${SCRIPT_DIR}/patches/$f" \
        "${BACKEND_CID}:/home/frappe/frappe-bench/apps/erpnext/erpnext/setup/$f"
    done
    "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
      bench --site "$SITE_NAME" set-config server_script_enabled 1 || true
    "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
      bench --site "$SITE_NAME" execute erpnext.setup.ensure_users.run || true
  fi
fi

echo "Onboarding ensure complete."
