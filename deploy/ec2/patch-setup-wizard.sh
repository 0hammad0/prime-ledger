#!/usr/bin/env bash
# Hot-patch setup-wizard fixes into a running Hub/custom stack.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="${PATCH_DIR:-$SCRIPT_DIR/patches/setup-wizard}"
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

[[ -f "$PATCH_DIR/setup_wizard.py" ]] || { echo "Missing $PATCH_DIR/setup_wizard.py"; exit 1; }
[[ -f "$PATCH_DIR/install_fixtures.py" ]] || { echo "Missing $PATCH_DIR/install_fixtures.py"; exit 1; }
[[ -f "$PATCH_DIR/setup_wizard.js" ]] || { echo "Missing $PATCH_DIR/setup_wizard.js"; exit 1; }
FRAPPE_LOCALE_PATCH="${FRAPPE_LOCALE_PATCH:-$SCRIPT_DIR/patches/frappe/locale.py}"
FRAPPE_SETUP_PATCH="${FRAPPE_SETUP_PATCH:-$SCRIPT_DIR/patches/frappe/setup_wizard.py}"

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

BACKEND_CID="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q backend | head -n1)"
[[ -n "$BACKEND_CID" ]] || { echo "backend not running"; exit 1; }

APP_ROOT="/home/frappe/frappe-bench/apps/erpnext/erpnext"
FRAPPE_ROOT="/home/frappe/frappe-bench/apps/frappe/frappe"
ASSETS_JS="/home/frappe/frappe-bench/sites/assets/erpnext/js"

copy_file() {
  local src="$1" dest="$2" cid="${3:-$BACKEND_CID}"
  "${DOCKER[@]}" exec -u root "$cid" mkdir -p "$(dirname "$dest")"
  "${DOCKER[@]}" cp "$src" "${cid}:${dest}"
  "${DOCKER[@]}" exec -u root "$cid" chown frappe:frappe "$dest" 2>/dev/null || true
}

echo "==> Patching setup wizard Python + JS (+ frappe locale/setup fixes)"
copy_file "$PATCH_DIR/setup_wizard.py" "$APP_ROOT/setup/setup_wizard/setup_wizard.py"
copy_file "$PATCH_DIR/install_fixtures.py" "$APP_ROOT/setup/setup_wizard/operations/install_fixtures.py"
copy_file "$PATCH_DIR/setup_wizard.js" "$APP_ROOT/public/js/setup_wizard.js"
copy_file "$PATCH_DIR/setup_wizard.js" "$ASSETS_JS/setup_wizard.js"
if [[ -f "$FRAPPE_LOCALE_PATCH" ]]; then
  copy_file "$FRAPPE_LOCALE_PATCH" "$FRAPPE_ROOT/locale.py"
fi
if [[ -f "$FRAPPE_SETUP_PATCH" ]]; then
  copy_file "$FRAPPE_SETUP_PATCH" "$FRAPPE_ROOT/desk/page/setup_wizard/setup_wizard.py"
fi

# Patch every app container (backend + queues keep code in memory)
for svc in backend queue-short queue-long scheduler websocket frontend; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
  [[ -n "${cid:-}" ]] || continue
  copy_file "$PATCH_DIR/setup_wizard.py" "$APP_ROOT/setup/setup_wizard/setup_wizard.py" "$cid" || true
  copy_file "$PATCH_DIR/install_fixtures.py" "$APP_ROOT/setup/setup_wizard/operations/install_fixtures.py" "$cid" || true
  copy_file "$PATCH_DIR/setup_wizard.js" "$APP_ROOT/public/js/setup_wizard.js" "$cid" || true
  copy_file "$PATCH_DIR/setup_wizard.js" "$ASSETS_JS/setup_wizard.js" "$cid" || true
  if [[ -f "$FRAPPE_LOCALE_PATCH" ]]; then
    copy_file "$FRAPPE_LOCALE_PATCH" "$FRAPPE_ROOT/locale.py" "$cid" || true
  fi
  if [[ -f "$FRAPPE_SETUP_PATCH" ]]; then
    copy_file "$FRAPPE_SETUP_PATCH" "$FRAPPE_ROOT/desk/page/setup_wizard/setup_wizard.py" "$cid" || true
  fi
  "${DOCKER[@]}" exec -u root "$cid" bash -lc \
    "find '$APP_ROOT/setup/setup_wizard' '$FRAPPE_ROOT/desk/page/setup_wizard' '$FRAPPE_ROOT' -maxdepth 2 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true" || true
done

echo "==> Restarting app containers so workers reload patched code"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" restart \
  backend queue-short queue-long scheduler websocket || true

echo "==> Waiting for backend"
for i in $(seq 1 40); do
  if "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend true 2>/dev/null; then
    break
  fi
  sleep 2
done

echo "==> Clearing cache + sealing completed setup"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" console <<'PY'
import frappe
from frappe.desk.page.setup_wizard.setup_wizard import enable_setup_wizard_complete

# If a company already exists, seal the wizard so Desk opens instead of Retry loops.
companies = frappe.get_all("Company", fields=["name", "country", "default_currency"], limit=1)
if not companies:
    print("no_company_yet")
else:
    company = companies[0]
    for app in ("frappe", "erpnext"):
        try:
            enable_setup_wizard_complete(app)
        except Exception as e:
            print("seal app", app, e)
    ss = frappe.get_doc("System Settings")
    if company.country and not ss.country:
        ss.country = company.country
    if company.default_currency and not ss.currency:
        ss.currency = company.default_currency
    if not ss.time_zone:
        ss.time_zone = "Asia/Karachi"
    if not ss.language:
        ss.language = "en"
    ss.flags.ignore_mandatory = True
    ss.save(ignore_permissions=True)
    frappe.db.set_default("company", company.name)
    frappe.db.set_default("country", company.country)
    frappe.db.set_default("currency", company.default_currency)
    frappe.db.set_default("desktop:home_page", "workspace")
    frappe.clear_cache()
    frappe.db.commit()
    print("sealed_setup", company.name, company.country, company.default_currency)
print("setup_complete", frappe.is_setup_complete())
print("apps", frappe.get_all("Installed Application", fields=["app_name", "is_setup_complete"]))
PY

echo "Setup wizard hardened + workers restarted. Hard-refresh and open /app."
