#!/usr/bin/env bash
# Provision a new organization as its own Frappe site (Phase 2 multi-tenancy).
# Usage:
#   bash provision-tenant.sh <site-slug> "Organization Name" [admin-email]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
CONTROL_SITE="${CONTROL_SITE:-${SITE_NAME:-frontend}}"

SITE_SLUG="${1:?site slug required (e.g. sultan)}"
ORG_NAME="${2:?organization name required}"
ADMIN_EMAIL="${3:-}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

PUBLIC_HOST="${PUBLIC_HOST:?PUBLIC_HOST required in .env}"
DB_PASSWORD="${DB_PASSWORD:?DB_PASSWORD required}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?ADMIN_PASSWORD required}"
TENANT_HOST="${TENANT_HOST:-${SITE_SLUG}.${PUBLIC_HOST}}"

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

echo "==> Provision tenant site=${SITE_SLUG} host=${TENANT_HOST} org=${ORG_NAME}"

# Mark provisioning on control site if row exists
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.set_tenant_status \
  --kwargs "{\"site_name\": \"${SITE_SLUG}\", \"status\": \"Provisioning\"}" 2>/dev/null || true

if ! "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc "test -d /home/frappe/frappe-bench/sites/${SITE_SLUG}"; then
  echo "==> Pause idle workers (t3.small RAM)"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" stop scheduler queue-short queue-long || true
  echo "==> bench new-site ${SITE_SLUG}"
set +e
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench new-site "$SITE_SLUG" \
    --mariadb-user-host-login-scope='%' \
    --db-root-password "$DB_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --install-app erpnext
  NEW_SITE_RC=$?
set -e
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" start scheduler queue-short queue-long || true
  if [[ "$NEW_SITE_RC" -ne 0 ]]; then
    echo "new-site failed rc=$NEW_SITE_RC" >&2
    "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
		  bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.set_tenant_status \
      --kwargs "{\"site_name\": \"${SITE_SLUG}\", \"status\": \"Error\"}" 2>/dev/null || true
    exit "$NEW_SITE_RC"
  fi
else
  echo "==> Site ${SITE_SLUG} already exists — skipping new-site"
fi

echo "==> Set host_name=${TENANT_HOST}"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_SLUG" set-config host_name "$TENANT_HOST"

set +e
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench setup add-domain --site "$SITE_SLUG" "$TENANT_HOST"
ADD_DOMAIN_RC=$?
set -e
if [[ "$ADD_DOMAIN_RC" -ne 0 ]]; then
  echo "WARN: add-domain failed rc=${ADD_DOMAIN_RC} site=${SITE_SLUG} host=${TENANT_HOST} (will still ensure site symlink)" >&2
fi
echo "==> Ensure sites/${TENANT_HOST} -> ${SITE_SLUG}"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc "ln -sfn '${SITE_SLUG}' '/home/frappe/frappe-bench/sites/${TENANT_HOST}'"

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench config dns_multitenant on || true

echo "==> Hot-patch portal onto containers"
SITE_NAME="$CONTROL_SITE" bash "$SCRIPT_DIR/patch-portal.sh"

echo "==> Migrate + seed portal on tenant site"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_SLUG" migrate
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_SLUG" execute erpnext.portal_control.seed.run || true
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_SLUG" execute erpnext.setup.ensure_users.run || true
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_SLUG" clear-cache || true

echo "==> Brand tenant site"
SITE_NAME="$SITE_SLUG" bash "$SCRIPT_DIR/brand.sh" </dev/null || true

echo "==> Seed Company so the org skips the setup wizard"
ORG_KW=$(ORG_NAME="$ORG_NAME" python3 - <<'PY'
import os
print(repr({"org_name": os.environ["ORG_NAME"]}))
PY
)
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_SLUG" execute erpnext.portal_control.tenants.ensure_org_company \
  --kwargs "$ORG_KW"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_SLUG" set-config setup_complete 1

# Resolve admin email / name from control PL Tenant if not passed
if [[ -z "$ADMIN_EMAIL" ]]; then
  ADMIN_EMAIL=$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bash -lc "cd /home/frappe/frappe-bench/sites && ../env/bin/python - <<'PY'
import frappe
frappe.init(site='${CONTROL_SITE}')
frappe.connect()
print(frappe.db.get_value('PL Tenant', '${SITE_SLUG}', 'admin_email') or '')
PY" | tr -d '\r')
fi
ADMIN_NAME=$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc "cd /home/frappe/frappe-bench/sites && ../env/bin/python - <<'PY'
import frappe
frappe.init(site='${CONTROL_SITE}')
frappe.connect()
print(frappe.db.get_value('PL Tenant', '${SITE_SLUG}', 'admin_full_name') or '')
PY" | tr -d '\r')

# Peek signup password from control-site cache (consume only after successful create).
# Pass site via docker env: a quoted <<'PY' heredoc does not expand ${SITE_SLUG}.
SIGNUP_PWD=$(
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T \
    -e PL_CONTROL="$CONTROL_SITE" -e PL_SLUG="$SITE_SLUG" -e PL_HOST="${PUBLIC_HOST}" backend \
    bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' <<'PY'
import os
import frappe
from erpnext.portal_control.tenants import peek_signup_password

pwd = ""
slug = os.environ.get("PL_SLUG") or ""
seen = set()
for site in (os.environ.get("PL_CONTROL") or "", os.environ.get("PL_HOST") or ""):
    site = (site or "").strip()
    if not site or site in seen:
        continue
    seen.add(site)
    try:
        frappe.destroy()
    except Exception:
        pass
    try:
        frappe.init(site=site)
        frappe.connect()
        found = peek_signup_password(slug) or ""
        if found:
            pwd = found
            break
    except Exception:
        continue
print("PL_PEEK:" + pwd)
PY
)
SIGNUP_PWD=$(printf '%s' "$SIGNUP_PWD" | tr -d '\r' | sed -n 's/^PL_PEEK://p' | tail -n1)

if [[ -n "${ADMIN_EMAIL}" ]]; then
  if [[ -z "${SIGNUP_PWD}" ]]; then
    echo "ERROR: signup password missing for site=${SITE_SLUG} (cache peek empty). Refusing to create admin without a password." >&2
    "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
      bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.set_tenant_status \
      --kwargs "{\"site_name\": \"${SITE_SLUG}\", \"status\": \"Error\"}" 2>/dev/null || true
    exit 1
  fi
  echo "==> Create org admin ${ADMIN_EMAIL} on tenant site"
  ADMIN_KW=$(ADMIN_EMAIL="$ADMIN_EMAIL" ADMIN_NAME="$ADMIN_NAME" SIGNUP_PWD="$SIGNUP_PWD" ORG_NAME="$ORG_NAME" python3 - <<'PY'
import os
d = {"email": os.environ["ADMIN_EMAIL"].strip()}
name = (os.environ.get("ADMIN_NAME") or "").strip()
pwd = (os.environ.get("SIGNUP_PWD") or "").strip()
company = (os.environ.get("ORG_NAME") or "").strip()
if name:
    d["full_name"] = name
if pwd:
    d["password"] = pwd
if company:
    d["company"] = company
print(repr(d))
PY
)
  set +e
  CREATE_ADMIN_OUT=$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$SITE_SLUG" execute erpnext.portal_control.tenants.create_tenant_admin_user \
    --kwargs "$ADMIN_KW" 2>&1)
  CREATE_ADMIN_RC=$?
  set -e
  printf '%s\n' "$CREATE_ADMIN_OUT"
  if [[ "$CREATE_ADMIN_RC" -ne 0 || "$CREATE_ADMIN_OUT" == *"signup_password_MISSING"* || "$CREATE_ADMIN_OUT" == *"'ok': False"* || "$CREATE_ADMIN_OUT" == *'"ok": False'* ]]; then
    echo "ERROR: create_tenant_admin_user failed rc=${CREATE_ADMIN_RC} (not marking Active)" >&2
    "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
      bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.set_tenant_status \
      --kwargs "{\"site_name\": \"${SITE_SLUG}\", \"status\": \"Error\"}" 2>/dev/null || true
    exit 1
  fi
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T \
    -e PL_CONTROL="$CONTROL_SITE" -e PL_SLUG="$SITE_SLUG" backend \
    bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' <<'PY'
import os
import frappe
from erpnext.portal_control.tenants import consume_signup_password

frappe.init(site=os.environ["PL_CONTROL"])
frappe.connect()
consume_signup_password(os.environ["PL_SLUG"])
PY
fi

echo "==> Register Active on control site ${CONTROL_SITE}"
KWARGS=$(ORG_NAME="$ORG_NAME" SITE_SLUG="$SITE_SLUG" TENANT_HOST="$TENANT_HOST" python3 - <<'PY'
import json, os
print(json.dumps({
  "site_name": os.environ["SITE_SLUG"],
  "host": os.environ["TENANT_HOST"],
  "company": os.environ["ORG_NAME"],
}))
PY
)
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.mark_tenant_active_from_host \
  --kwargs "$KWARGS"

echo "==> Refresh Traefik Host() list + Host-based site routing"
bash "$SCRIPT_DIR/refresh-tenant-routing.sh" "$TENANT_HOST"

echo ""
echo "Tenant ready:"
echo "  URL:  https://${TENANT_HOST}"
echo "  Site: ${SITE_SLUG}"
if [[ -n "${ADMIN_EMAIL}" ]]; then
  echo "  Org admin: ${ADMIN_EMAIL}"
else
  echo "  Login: Administrator / (ADMIN_PASSWORD from .env)"
fi
echo ""
echo "Routing: use wildcard SITES_RULE and unset FRAPPE_SITE_NAME_HEADER (see .env.example)."
