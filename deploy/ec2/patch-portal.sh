#!/usr/bin/env bash
# Hot-patch Prime Ledger portal onto a running Hub stack (before or after migrate).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
SITE_NAME="${SITE_NAME:-frontend}"
PATCH_ROOT="${PATCH_ROOT:-$SCRIPT_DIR/patches/portal}"
INJECT_PY="${SCRIPT_DIR/../docker/inject_portal_hooks.py}"
# Prefer inject next to deploy scripts if docker path missing on server
if [[ ! -f "$INJECT_PY" ]]; then
  INJECT_PY="$SCRIPT_DIR/inject_portal_hooks.py"
fi

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

# Ensure inject script exists on server (synced via deploy/ec2 or copied once)
if [[ ! -f "$INJECT_PY" ]]; then
  cat >"$SCRIPT_DIR/inject_portal_hooks.py" <<'PY'
from pathlib import Path

hooks = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/hooks.py")
text = hooks.read_text()
needle = '{"from_route": "/portal", "to_route": "portal"}'
if needle not in text:
	old = '{"from_route": "/banking/<path:app_path>", "to_route": "banking"},'
	if old in text:
		hooks.write_text(
			text.replace(
				old,
				old
				+ '\n\t{"from_route": "/portal", "to_route": "portal"},'
				+ '\n\t{"from_route": "/portal/<path:app_path>", "to_route": "portal"},',
				1,
			)
		)
		print("hooks_portal_routes_ok")
	else:
		print("hooks_portal_routes_banking_missing")
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
  INJECT_PY="$SCRIPT_DIR/inject_portal_hooks.py"
fi

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
    "$SITE_ASSETS/portal"

  "${DOCKER[@]}" cp "$PATCH_ROOT/portal_control/." "${cid}:${APP}/portal_control/"
  "${DOCKER[@]}" exec -u root "$cid" rm -rf "$APP/setup/doctype/portal_settings" || true
  for dt in portal_module portal_module_role pl_portal_settings pl_tenant; do
    if [[ -d "$PATCH_ROOT/doctype/${dt}" ]]; then
      "${DOCKER[@]}" cp "$PATCH_ROOT/doctype/${dt}" "${cid}:${APP}/setup/doctype/"
    fi
  done
  "${DOCKER[@]}" cp "$PATCH_ROOT/www/portal.py" "${cid}:${APP}/www/portal.py"
  "${DOCKER[@]}" cp "$PATCH_ROOT/www/portal.html" "${cid}:${APP}/www/portal.html"
	if [[ -f "$PATCH_ROOT/www/start.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/www/start.py" "${cid}:${APP}/www/start.py"
    "${DOCKER[@]}" cp "$PATCH_ROOT/www/start.html" "${cid}:${APP}/www/start.html"
  fi
  if [[ -f "$PATCH_ROOT/www/go.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/www/go.py" "${cid}:${APP}/www/go.py"
  fi
  if [[ -f "$PATCH_ROOT/www/go.html" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/www/go.html" "${cid}:${APP}/www/go.html"
  fi
  "${DOCKER[@]}" cp "$PATCH_ROOT/public/." "${cid}:${APP}/public/portal/"
  "${DOCKER[@]}" cp "$PATCH_ROOT/public/." "${cid}:${SITE_ASSETS}/portal/" || true
  "${DOCKER[@]}" cp "$PATCH_ROOT/patches/seed_portal_control.py" \
    "${cid}:${APP}/patches/v16_0/seed_portal_control.py"
  if [[ -f "$PATCH_ROOT/patches/restore_frappe_portal_settings.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/patches/restore_frappe_portal_settings.py" \
      "${cid}:${APP}/patches/v16_0/restore_frappe_portal_settings.py"
  fi
  if [[ -f "$PATCH_ROOT/patches/seed_pl_tenant.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/patches/seed_pl_tenant.py" \
      "${cid}:${APP}/patches/v16_0/seed_pl_tenant.py"
  fi
  # Login redirect + boot portal home (Hub overlay)
  if [[ -f "$PATCH_ROOT/portal_control/redirects.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/portal_control/redirects.py" "${cid}:${APP}/portal_control/redirects.py"
  fi
  if [[ -f "$PATCH_ROOT/boot.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/boot.py" "${cid}:${APP}/startup/boot.py"
  fi
  # Also copy user_onboarding for company bind on insert
  if [[ -f "$SCRIPT_DIR/patches/user_onboarding.py" ]]; then
    "${DOCKER[@]}" cp "$SCRIPT_DIR/patches/user_onboarding.py" \
      "${cid}:${APP}/setup/user_onboarding.py" || true
  elif [[ -f "$PATCH_ROOT/../user_onboarding.py" ]]; then
    "${DOCKER[@]}" cp "$PATCH_ROOT/../user_onboarding.py" \
      "${cid}:${APP}/setup/user_onboarding.py" || true
  fi
  "${DOCKER[@]}" exec -u root "$cid" mkdir -p "$APP/public/js" "$APP/public/images" "$APP/public/css" \
    "$SITE_ASSETS/js" "$SITE_ASSETS/images" "$SITE_ASSETS/css"
  if [[ -f "$SCRIPT_DIR/branding/login_simple.js" ]]; then
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/login_simple.js" "${cid}:${APP}/public/js/login_simple.js" || true
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/login_simple.js" "${cid}:${SITE_ASSETS}/js/login_simple.js" || true
  fi
  for img in prime-ledger-logo.svg prime-ledger-favicon.svg erpnext-logo.svg erpnext-favicon.svg; do
    if [[ -f "$SCRIPT_DIR/branding/$img" ]]; then
      "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/$img" "${cid}:${APP}/public/images/$img" || true
      "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/$img" "${cid}:${SITE_ASSETS}/images/$img" || true
    fi
  done
  if [[ -f "$SCRIPT_DIR/branding/prime-ledger-logo.svg" ]]; then
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/prime-ledger-logo.svg" "${cid}:${APP}/public/images/erpnext-logo.svg" || true
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/prime-ledger-logo.svg" "${cid}:${SITE_ASSETS}/images/erpnext-logo.svg" || true
  fi
  if [[ -f "$SCRIPT_DIR/branding/prime-ledger-favicon.svg" ]]; then
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/prime-ledger-favicon.svg" "${cid}:${APP}/public/images/erpnext-favicon.svg" || true
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/prime-ledger-favicon.svg" "${cid}:${SITE_ASSETS}/images/erpnext-favicon.svg" || true
  fi
  if [[ -f "$SCRIPT_DIR/branding/prime_ledger_brand.css" ]]; then
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/prime_ledger_brand.css" "${cid}:${APP}/public/css/prime_ledger_brand.css" || true
    "${DOCKER[@]}" cp "$SCRIPT_DIR/branding/prime_ledger_brand.css" "${cid}:${SITE_ASSETS}/css/prime_ledger_brand.css" || true
  fi
  if [[ -f "$SCRIPT_DIR/patches/setup-wizard/setup_wizard.js" ]]; then
    "${DOCKER[@]}" cp "$SCRIPT_DIR/patches/setup-wizard/setup_wizard.js" \
      "${cid}:${APP}/public/js/setup_wizard.js" || true
  fi

  "${DOCKER[@]}" cp "$INJECT_PY" "${cid}:/tmp/inject_portal_hooks.py"
  "${DOCKER[@]}" exec -u root "$cid" python3 /tmp/inject_portal_hooks.py

  "${DOCKER[@]}" exec -u root "$cid" chown -R frappe:frappe \
    "$APP/portal_control" \
    "$APP/setup/doctype/portal_module" \
    "$APP/setup/doctype/portal_module_role" \
    "$APP/setup/doctype/pl_portal_settings" \
    "$APP/setup/doctype/pl_tenant" \
    "$APP/www/portal.py" \
    "$APP/www/portal.html" \
    "$APP/public/portal" \
    "$APP/patches/v16_0/seed_portal_control.py" 2>/dev/null || true
}

echo "==> Hot-patching portal onto app containers"
for svc in backend frontend websocket queue-short queue-long scheduler; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q --status running "$svc" 2>/dev/null | head -n1 || true)"
  if [[ -z "${cid:-}" ]]; then
    echo "  skip $svc (not running)"
    continue
  fi
  patch_cid "${cid:-}"
done

echo "portal_patch_ok"
