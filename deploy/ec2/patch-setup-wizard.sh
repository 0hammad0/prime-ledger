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

echo "==> Patching setup wizard Python + JS (+ frappe locale fix)"
copy_file "$PATCH_DIR/setup_wizard.py" "$APP_ROOT/setup/setup_wizard/setup_wizard.py"
copy_file "$PATCH_DIR/install_fixtures.py" "$APP_ROOT/setup/setup_wizard/operations/install_fixtures.py"
copy_file "$PATCH_DIR/setup_wizard.js" "$APP_ROOT/public/js/setup_wizard.js"
copy_file "$PATCH_DIR/setup_wizard.js" "$ASSETS_JS/setup_wizard.js"
if [[ -f "$FRAPPE_LOCALE_PATCH" ]]; then
  copy_file "$FRAPPE_LOCALE_PATCH" "$FRAPPE_ROOT/locale.py"
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
  "${DOCKER[@]}" exec -u root "$cid" bash -lc \
    "find '$APP_ROOT/setup/setup_wizard' '$FRAPPE_ROOT' -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true" || true
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

echo "==> Clearing cache"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

echo "Setup wizard patch applied + workers restarted. Hard-refresh and retry."
