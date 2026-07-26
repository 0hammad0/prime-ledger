#!/usr/bin/env bash
# Apply Prime Ledger white-label on a running Docker stack (Hub or custom image).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
BRAND_DIR="${BRAND_DIR:-$SCRIPT_DIR/branding}"
SITE_NAME="${SITE_NAME:-frontend}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

SITE_NAME="${SITE_NAME:-frontend}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

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
[[ -n "$BACKEND_CID" ]] || { echo "backend container not running"; exit 1; }

APP_IMG="/home/frappe/frappe-bench/apps/erpnext/erpnext/public/images"
APP_CSS="/home/frappe/frappe-bench/apps/erpnext/erpnext/public/css"
SITE_IMG="/home/frappe/frappe-bench/sites/assets/erpnext/images"
SITE_CSS="/home/frappe/frappe-bench/sites/assets/erpnext/css"
FOOTER_TMPL="/home/frappe/frappe-bench/apps/erpnext/erpnext/templates/includes/footer/footer_powered.html"

copy_into() {
  local src="$1" cid="$2" dest="$3"
  "${DOCKER[@]}" cp "$src" "${cid}:${dest}"
}

brand_container() {
  local cid="$1"
  [[ -n "$cid" ]] || return 0
  "${DOCKER[@]}" exec -u root "$cid" mkdir -p "$APP_IMG" "$APP_CSS" "$SITE_IMG" "$SITE_CSS" 2>/dev/null || true
  for img_dir in "$APP_IMG" "$SITE_IMG"; do
    copy_into "$BRAND_DIR/prime-ledger-logo.svg" "$cid" "$img_dir/prime-ledger-logo.svg" || true
    copy_into "$BRAND_DIR/prime-ledger-favicon.svg" "$cid" "$img_dir/prime-ledger-favicon.svg" || true
    copy_into "$BRAND_DIR/prime-ledger-logo.svg" "$cid" "$img_dir/erpnext-logo.svg" || true
    copy_into "$BRAND_DIR/prime-ledger-favicon.svg" "$cid" "$img_dir/erpnext-favicon.svg" || true
  done
  for css_dir in "$APP_CSS" "$SITE_CSS"; do
    copy_into "$BRAND_DIR/prime_ledger_brand.css" "$cid" "$css_dir/prime_ledger_brand.css" || true
  done
}

echo "==> Copying Prime Ledger brand assets"
brand_container "$BACKEND_CID"
for svc in frontend websocket; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
  brand_container "${cid:-}"
done

# Append theme into built Desk CSS bundles (Hub images ignore our hooks app_include_css)
append_theme() {
  local cid="$1"
  [[ -n "$cid" ]] || return 0
  "${DOCKER[@]}" exec -u root "$cid" bash -lc '
    CSS_SRC="/home/frappe/frappe-bench/apps/erpnext/erpnext/public/css/prime_ledger_brand.css"
    [ -f "$CSS_SRC" ] || CSS_SRC="/home/frappe/frappe-bench/sites/assets/erpnext/css/prime_ledger_brand.css"
    [ -f "$CSS_SRC" ] || exit 0
    shopt -s nullglob
    for f in \
      /home/frappe/frappe-bench/sites/assets/erpnext/dist/css/*.css \
      /home/frappe/frappe-bench/sites/assets/frappe/dist/css/desk*.css \
      /home/frappe/frappe-bench/sites/assets/css/erpnext.bundle.*.css
    do
      grep -q "Prime Ledger desk / login skin" "$f" 2>/dev/null && continue
      printf "\n" >> "$f"
      cat "$CSS_SRC" >> "$f"
    done
    mkdir -p /home/frappe/frappe-bench/sites/assets/css
    cp -f "$CSS_SRC" /home/frappe/frappe-bench/sites/assets/css/prime_ledger_brand.css 2>/dev/null || true
  ' || true
}
append_theme "$BACKEND_CID"
for svc in frontend websocket; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
  append_theme "${cid:-}"
done

"${DOCKER[@]}" exec -u root "$BACKEND_CID" bash -lc \
  "printf '%s\n' '{{ _(\"Powered by {0}\").format('\''<a href=\"https://github.com/0hammad0/prime-ledger\" target=\"_blank\" class=\"text-muted\">Prime Ledger</a>'\'') }}' > '$FOOTER_TMPL'" \
  || true

echo "==> Applying site branding settings"
"${DOCKER[@]}" cp "$BRAND_DIR/apply_brand.py" "${BACKEND_CID}:/tmp/apply_brand.py"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T \
  -e "ADMIN_PASSWORD=${ADMIN_PASSWORD}" backend \
  bench --site "$SITE_NAME" console <<'PY'
_code = open("/tmp/apply_brand.py", encoding="utf-8").read()
exec(_code, globals(), globals())
PY

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc 'sed -i "s/Starting Frappe \\.\\.\\./Starting Prime Ledger .../g" /home/frappe/frappe-bench/apps/frappe/frappe/desk/page/setup_wizard/setup_wizard.js 2>/dev/null || true'

echo "Branded as Prime Ledger (logos, theme CSS, navbar, site settings)."
