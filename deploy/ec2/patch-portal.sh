#!/usr/bin/env bash
# Hot-patch Prime Ledger portal onto a running Hub stack (before or after migrate).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
SITE_NAME="${SITE_NAME:-frontend}"
PATCH_ROOT="${PATCH_ROOT:-$SCRIPT_DIR/patches/portal}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
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

[[ -d "$PATCH_ROOT/portal_control" ]] || {
  echo "Missing $PATCH_ROOT — run sync-portal-patches.sh and redeploy" >&2
  exit 1
}

APP="/home/frappe/frappe-bench/apps/erpnext/erpnext"
SITE_ASSETS="/home/frappe/frappe-bench/sites/assets/erpnext"

patch_cid() {
  local cid="$1"
  [[ -n "$cid" ]] || return 0
  echo "  patching container ${cid:0:12}"
  "${DOCKER[@]}" exec -u root "$cid" mkdir -p \
    "$APP/portal_control" \
    "$APP/setup/doctype" \
    "$APP/www" \
    "$APP/public/portal" \
    "$APP/patches/v16_0" \
    "$SITE_ASSETS/portal" \
    /home/frappe/frappe-bench/sites/assets/erpnext/portal

  "${DOCKER[@]}" cp "$PATCH_ROOT/portal_control/." "${cid}:${APP}/portal_control/"
  # Remove mistaken Portal Settings overlay if present (conflicts with Frappe website DocType)
  "${DOCKER[@]}" exec -u root "$cid" rm -rf "$APP/setup/doctype/portal_settings" || true
  for dt in portal_module portal_module_role pl_portal_settings; do
    "${DOCKER[@]}" cp "$PATCH_ROOT/doctype/${dt}" "${cid}:${APP}/setup/doctype/"
  done
  "${DOCKER[@]}" cp "$PATCH_ROOT/www/portal.py" "${cid}:${APP}/www/portal.py"
  "${DOCKER[@]}" cp "$PATCH_ROOT/www/portal.html" "${cid}:${APP}/www/portal.html"
  "${DOCKER[@]}" cp "$PATCH_ROOT/public/." "${cid}:${APP}/public/portal/"
  "${DOCKER[@]}" cp "$PATCH_ROOT/public/." "${cid}:${SITE_ASSETS}/portal/" || true
  "${DOCKER[@]}" cp "$PATCH_ROOT/patches/seed_portal_control.py" \
    "${cid}:${APP}/patches/v16_0/seed_portal_control.py"
  if [[ -f "$PATCH_ROOT/patches/restore_frappe_portal_settings.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/patches/restore_frappe_portal_settings.py" \
      "${cid}:${APP}/patches/v16_0/restore_frappe_portal_settings.py"
  fi

  # Ensure website routes + patches.txt include portal
  "${DOCKER[@]}" exec -u root "$cid" python3 - <<'PY'
from pathlib import Path

hooks = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/hooks.py")
text = hooks.read_text()
needle = '{"from_route": "/portal", "to_route": "portal"}'
if needle not in text:
    old = '{"from_route": "/banking/<path:app_path>", "to_route": "banking"},'
    new = old + '\n\t{"from_route": "/portal", "to_route": "portal"},\n\t{"from_route": "/portal/<path:app_path>", "to_route": "portal"},'
    if old in text:
        hooks.write_text(text.replace(old, new, 1))
        print("hooks_portal_routes_ok")
    else:
        # append before closing of website_route_rules if possible
        marker = "website_route_rules = ["
        if marker in text and needle not in text:
            print("hooks_portal_routes_manual_needed")
        else:
            print("hooks_portal_routes_skip")
else:
    print("hooks_portal_routes_present")

patches = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/patches.txt")
pt = patches.read_text()
for line in (
    "erpnext.patches.v16_0.restore_frappe_portal_settings",
    "erpnext.patches.v16_0.seed_portal_control",
):
    if line not in pt:
        pt = pt.rstrip() + "\n" + line + "\n"
        print("patches_txt_added", line)
patches.write_text(pt)
print("patches_txt_ok")
PY

  "${DOCKER[@]}" exec -u root "$cid" chown -R frappe:frappe \
    "$APP/portal_control" \
    "$APP/setup/doctype/portal_module" \
    "$APP/setup/doctype/portal_module_role" \
    "$APP/setup/doctype/pl_portal_settings" \
    "$APP/www/portal.py" \
    "$APP/www/portal.html" \
    "$APP/public/portal" \
    "$APP/patches/v16_0/seed_portal_control.py" 2>/dev/null || true
}

echo "==> Hot-patching portal onto app containers"
for svc in backend frontend websocket queue-short queue-long scheduler; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
  patch_cid "${cid:-}"
done

echo "portal_patch_ok"
