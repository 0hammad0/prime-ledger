#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

SITE_NAME="${SITE_NAME:-frontend}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" console <<PY
import frappe
from frappe.utils.password import update_password

frappe.db.set_single_value("System Settings", "app_name", "Prime Ledger")
frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")
frappe.db.set_single_value("System Settings", "enable_password_policy", 1)
frappe.db.set_single_value("System Settings", "minimum_password_score", 2)
frappe.db.set_single_value("System Settings", "allow_login_using_user_name", 1)
update_password("Administrator", "${ADMIN_PASSWORD}")

email = "admin@primeledger.local"
if frappe.db.exists("User", email):
    user = frappe.get_doc("User", email)
else:
    user = frappe.new_doc("User")
    user.email = email
    user.first_name = "Admin"
    user.enabled = 1
    user.user_type = "System User"
    user.send_welcome_email = 0
    user.append("roles", {"role": "System Manager"})
    user.insert(ignore_permissions=True)

user.username = "admin"
user.enabled = 1
user.save(ignore_permissions=True)
update_password(user.name, "${ADMIN_PASSWORD}")
frappe.db.commit()
frappe.clear_cache()
print("branding_ok")
PY

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc 'sed -i "s/Starting Frappe \\.\\.\\./Starting Prime Ledger .../g" /home/frappe/frappe-bench/apps/frappe/frappe/desk/page/setup_wizard/setup_wizard.js || true'

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache

echo "Branded as Prime Ledger."
