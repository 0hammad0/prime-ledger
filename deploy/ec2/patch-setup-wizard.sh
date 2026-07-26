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
ASSETS_JS="/home/frappe/frappe-bench/sites/assets/erpnext/js"

copy_file() {
  local src="$1" dest="$2" cid="${3:-$BACKEND_CID}"
  "${DOCKER[@]}" exec -u root "$cid" mkdir -p "$(dirname "$dest")"
  "${DOCKER[@]}" cp "$src" "${cid}:${dest}"
  "${DOCKER[@]}" exec -u root "$cid" chown frappe:frappe "$dest" 2>/dev/null || true
}

echo "==> Patching setup wizard Python + JS"
copy_file "$PATCH_DIR/setup_wizard.py" "$APP_ROOT/setup/setup_wizard/setup_wizard.py"
copy_file "$PATCH_DIR/install_fixtures.py" "$APP_ROOT/setup/setup_wizard/operations/install_fixtures.py"
copy_file "$PATCH_DIR/setup_wizard.js" "$APP_ROOT/public/js/setup_wizard.js"
copy_file "$PATCH_DIR/setup_wizard.js" "$ASSETS_JS/setup_wizard.js"

FRONT_CID="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q frontend 2>/dev/null | head -n1 || true)"
if [[ -n "${FRONT_CID:-}" ]]; then
  copy_file "$PATCH_DIR/setup_wizard.js" "$ASSETS_JS/setup_wizard.js" "$FRONT_CID" || true
  copy_file "$PATCH_DIR/setup_wizard.js" "$APP_ROOT/public/js/setup_wizard.js" "$FRONT_CID" || true
fi

echo "==> Clearing cache"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache

echo "Setup wizard patch applied. Hard-refresh (Cmd+Shift+R) and click Retry."
