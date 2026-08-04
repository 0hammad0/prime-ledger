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
  APP_JS="/home/frappe/frappe-bench/apps/erpnext/erpnext/public/js"
  SITE_JS="/home/frappe/frappe-bench/sites/assets/erpnext/js"
  "${DOCKER[@]}" exec -u root "$cid" mkdir -p "$APP_JS" "$SITE_JS" 2>/dev/null || true
  if [[ -f "$BRAND_DIR/login_simple.js" ]]; then
    copy_into "$BRAND_DIR/login_simple.js" "$cid" "$APP_JS/login_simple.js" || true
    copy_into "$BRAND_DIR/login_simple.js" "$cid" "$SITE_JS/login_simple.js" || true
  fi
}

echo "==> Copying Prime Ledger brand assets"
brand_container "$BACKEND_CID"
for svc in frontend websocket; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
  brand_container "${cid:-}"
done

# Refresh theme into built CSS bundles
append_theme() {
  local cid="$1"
  [[ -n "$cid" ]] || return 0
  "${DOCKER[@]}" cp "$BRAND_DIR/inject_theme.py" "${cid}:/tmp/inject_theme.py"
  "${DOCKER[@]}" exec -u root "$cid" python3 /tmp/inject_theme.py || true
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

# Scrub remaining ERPNext / Frappe product strings from login, footer, wizard templates
scrub_frappe() {
  local cid="$1"
  [[ -n "$cid" ]] || return 0
  "${DOCKER[@]}" exec -u root "$cid" bash -lc '
    set +e
    for f in \
      /home/frappe/frappe-bench/apps/frappe/frappe/desk/page/setup_wizard/setup_wizard.js \
      /home/frappe/frappe-bench/apps/frappe/frappe/templates/includes/footer/footer.html \
      /home/frappe/frappe-bench/apps/frappe/frappe/www/login.html \
      /home/frappe/frappe-bench/apps/frappe/frappe/templates/includes/footer/footer_powered.html \
      /home/frappe/frappe-bench/apps/erpnext/erpnext/templates/includes/footer/footer_powered.html
    do
      [ -f "$f" ] || continue
      sed -i \
        -e "s/Starting Frappe \\.\\.\\./Starting Prime Ledger .../g" \
        -e "s/Welcome to Frappe/Welcome to Prime Ledger/g" \
        -e "s/ERPNext/Prime Ledger/g" \
        -e "s/Frappe Framework/Prime Ledger/g" \
        "$f"
    done
  ' || true
}
scrub_frappe "$BACKEND_CID"
for svc in frontend websocket; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
  scrub_frappe "${cid:-}"
done

# Hot-patch scrubbed help/error sources into the Hub erpnext app tree
if [[ -d "$BRAND_DIR/scrub" ]]; then
  while IFS= read -r -d '' src; do
    rel="${src#$BRAND_DIR/scrub/}"
    dest="/home/frappe/frappe-bench/apps/erpnext/erpnext/${rel}"
    dest_dir="$(dirname "$dest")"
    "${DOCKER[@]}" exec -u root "$BACKEND_CID" mkdir -p "$dest_dir" 2>/dev/null || true
    copy_into "$src" "$BACKEND_CID" "$dest" || true
    for svc in frontend websocket; do
      cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
      if [[ -n "${cid:-}" ]]; then
        "${DOCKER[@]}" exec -u root "$cid" mkdir -p "$dest_dir" 2>/dev/null || true
        copy_into "$src" "$cid" "$dest" || true
      fi
    done
  done < <(find "$BRAND_DIR/scrub" -type f -print0 2>/dev/null)
fi

echo "Branded as Prime Ledger (logos, theme CSS, navbar, site settings)."
