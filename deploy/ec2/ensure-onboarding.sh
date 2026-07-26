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

    # Price lists
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

    # Stock settings warehouse
    stores = frappe.db.get_value(
        "Warehouse", {"warehouse_name": "Stores", "company": company.name}, "name"
    ) or frappe.db.get_value("Warehouse", {"company": company.name, "is_group": 0}, "name")
    if stores:
        frappe.db.set_single_value("Stock Settings", "default_warehouse", stores)
        print("default_warehouse", stores)

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

echo "Onboarding ensure complete."
