#!/usr/bin/env bash
# Apply enterprise Frappe/ERPNext site hardening (run after site exists).
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

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" console <<'PY'
import frappe

# Branding
frappe.db.set_single_value("System Settings", "app_name", "Prime Ledger")
frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")

# Auth / password policy
frappe.db.set_single_value("System Settings", "enable_password_policy", 1)
frappe.db.set_single_value("System Settings", "minimum_password_score", 3)
frappe.db.set_single_value("System Settings", "allow_login_using_user_name", 1)
frappe.db.set_single_value("System Settings", "login_with_email_link", 0)
frappe.db.set_single_value("System Settings", "disable_user_pass_login", 0)

# Session / idle (seconds) — 6 hours max session life feel for ERP desks
frappe.db.set_single_value("System Settings", "session_expiry", "06:00")
frappe.db.set_single_value("System Settings", "session_expiry_mobile", "06:00")

# Public website surface
frappe.db.set_single_value("Website Settings", "disable_signup", 1)
frappe.db.set_single_value("Website Settings", "hide_footer_signup", 1)
frappe.db.set_single_value("Website Settings", "show_footer_on_login", 0)

# Backups retained on site
frappe.db.set_single_value("System Settings", "backup_limit", 14)

# Scheduler must stay on in production
try:
    frappe.utils.scheduler.enable_scheduler()
except Exception as e:
    print("scheduler_enable:", e)

frappe.db.commit()
frappe.clear_cache()

# Persist host_name for emails / absolute links
public = frappe.conf.get("hostname") or None
print("enterprise_site_config_ok")
print("disable_signup=", frappe.db.get_single_value("Website Settings", "disable_signup"))
print("password_policy=", frappe.db.get_single_value("System Settings", "enable_password_policy"))
print("backup_limit=", frappe.db.get_single_value("System Settings", "backup_limit"))
PY

# Force HTTPS-aware site config + host_name for links
PUBLIC_HOST="${PUBLIC_HOST:-}"
if [[ -n "$PUBLIC_HOST" ]]; then
  docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$SITE_NAME" set-config host_name "https://${PUBLIC_HOST}"
  docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$SITE_NAME" set-config hostname "https://${PUBLIC_HOST}"
fi

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc 'sed -i "s/Starting Frappe \\.\\.\\./Starting Prime Ledger .../g" /home/frappe/frappe-bench/apps/frappe/frappe/desk/page/setup_wizard/setup_wizard.js || true'

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache

echo "Enterprise site configuration applied."
