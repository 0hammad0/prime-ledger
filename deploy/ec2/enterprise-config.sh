#!/usr/bin/env bash
# Apply enterprise Frappe/ERPNext site hardening (run after site exists).
# Uses bench execute (not console) so CI/SSH heredocs are not consumed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
MODULE_SRC="${SCRIPT_DIR}/patches/enterprise_site_config.py"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

SITE_NAME="${SITE_NAME:-frontend}"

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
[[ -f "$MODULE_SRC" ]] || { echo "Missing $MODULE_SRC"; exit 1; }

copy_py() {
  local src="$1" dest="$2"
  [[ -f "$src" ]] || return 0
  "${DOCKER[@]}" cp "$src" "${BACKEND_CID}:${dest}"
  "${DOCKER[@]}" exec -u root "$BACKEND_CID" chown frappe:frappe "$dest" 2>/dev/null || true
}

SETUP_ROOT="/home/frappe/frappe-bench/apps/erpnext/erpnext/setup"

copy_py "$MODULE_SRC" "$SETUP_ROOT/enterprise_site_config.py"
copy_py "${SCRIPT_DIR}/patches/ensure_users.py" "$SETUP_ROOT/ensure_users.py"
copy_py "${SCRIPT_DIR}/patches/grant_admin_roles.py" "$SETUP_ROOT/grant_admin_roles.py"
copy_py "${SCRIPT_DIR}/patches/user_onboarding.py" "$SETUP_ROOT/user_onboarding.py"

echo "==> Applying enterprise site config via bench execute"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" execute erpnext.setup.enterprise_site_config.apply

echo "==> Patch user hooks + ensure role profiles"
bash "$SCRIPT_DIR/patch-user-hooks.sh" || true
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" execute erpnext.setup.ensure_users.run || true

PUBLIC_HOST="${PUBLIC_HOST:-}"
if [[ -n "$PUBLIC_HOST" ]]; then
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$SITE_NAME" set-config host_name "https://${PUBLIC_HOST}"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$SITE_NAME" set-config hostname "https://${PUBLIC_HOST}"
fi

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

echo "Enterprise site configuration applied."
