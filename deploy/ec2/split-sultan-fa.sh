#!/usr/bin/env bash
# Clone frontend onto sultan + fa, then strip the other company on each site.
# Do NOT use provision-tenant.sh here (that would create blank ERP sites).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
CONTROL_SITE="${CONTROL_SITE:-${SITE_NAME:-frontend}}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups/prime-ledger}"
POLL_TIMEOUT_SEC="${POLL_TIMEOUT_SEC:-2400}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

PUBLIC_HOST="${PUBLIC_HOST:?PUBLIC_HOST required in .env}"
SULTAN_HOST="${SULTAN_HOST:-sultan.${PUBLIC_HOST}}"
FA_HOST="${FA_HOST:-fa.${PUBLIC_HOST}}"

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

backend() {
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend "$@"
}

start_queues() {
  echo "==> Start scheduler + queues"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" start scheduler queue-short queue-long || true
}

clone_or_skip() {
  local src="$1" dest="$2" host="$3"
  if backend bash -lc "test -d /home/frappe/frappe-bench/sites/${dest}"; then
    echo "==> Site ${dest} already exists — skipping clone"
    return 0
  fi
  echo "==> Cloning ${src} -> ${dest} (${host})"
  set +e
  bash "$SCRIPT_DIR/clone-site.sh" "$src" "$dest" "$host"
  local rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    echo "BLOCKED: clone ${src}->${dest} failed rc=${rc} (possible OOM). Starting queues." >&2
    start_queues
    free -h || true
    return "$rc"
  fi
}

echo "==> split Sultan Group / FA Traders off ${CONTROL_SITE}"

need_backup=1
latest=$(ls -1dt "$BACKUP_ROOT"/20* 2>/dev/null | head -n1 || true)
if [[ -n "$latest" ]]; then
  age=$(( $(date +%s) - $(stat -c %Y "$latest" 2>/dev/null || stat -f %m "$latest") ))
  if [[ "$age" -lt 21600 ]]; then
    echo "==> Fresh backup (${age}s old) at $latest — skip backup-now.sh"
    need_backup=0
  fi
fi
if [[ "$need_backup" -eq 1 ]]; then
  echo "==> backup-now.sh (last backup older than ~6h)"
  set +e
  bash "$SCRIPT_DIR/backup-now.sh"
  BAK_RC=$?
  set -e
  if [[ "$BAK_RC" -ne 0 ]]; then
    echo "WARN: backup-now.sh rc=${BAK_RC} — continuing with clone (queues will be restored on clone failure)" >&2
  fi
fi

clone_or_skip "$CONTROL_SITE" sultan "$SULTAN_HOST"
clone_or_skip "$CONTROL_SITE" fa "$FA_HOST"

echo "==> Patch portal modules onto containers (no compose recreate)"
SITE_NAME="$CONTROL_SITE" bash "$SCRIPT_DIR/patch-portal.sh"

echo "==> start_strip sultan keep Sultan Group (disables other-company users)"
backend bench --site sultan execute erpnext.portal_control.strip_company.start_strip \
  --kwargs "$(python3 -c 'print(repr({"keep_company": "Sultan Group"}))')"

echo "==> start_strip fa keep FA Traders"
backend bench --site fa execute erpnext.portal_control.strip_company.start_strip \
  --kwargs "$(python3 -c 'print(repr({"keep_company": "FA Traders"}))')"

echo "==> Register PL Tenant Active rows"
KW_SULTAN=$(SULTAN_HOST="$SULTAN_HOST" python3 -c 'import json,os; print(json.dumps({"site_name":"sultan","host":os.environ["SULTAN_HOST"],"company":"Sultan Group"}))')
KW_FA=$(FA_HOST="$FA_HOST" python3 -c 'import json,os; print(json.dumps({"site_name":"fa","host":os.environ["FA_HOST"],"company":"FA Traders"}))')
backend bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.mark_tenant_active_from_host \
  --kwargs "$KW_SULTAN"
backend bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.mark_tenant_active_from_host \
  --kwargs "$KW_FA"

echo "==> Refresh Traefik last (strip already started; leftover hosts already archived)"
bash "$SCRIPT_DIR/refresh-tenant-routing.sh" "$SULTAN_HOST" "$FA_HOST"

echo "==> Poll TDR status (timeout ${POLL_TIMEOUT_SEC}s)"
deadline=$(( $(date +%s) + POLL_TIMEOUT_SEC ))
sultan_done=0
fa_done=0
while [[ $(date +%s) -lt "$deadline" ]]; do
  S_STAT=$(backend bench --site sultan execute erpnext.portal_control.strip_company.strip_status 2>/dev/null | tr -d '\r' || true)
  F_STAT=$(backend bench --site fa execute erpnext.portal_control.strip_company.strip_status 2>/dev/null | tr -d '\r' || true)
  echo "--- sultan strip_status ---"
  printf '%s\n' "$S_STAT" | tail -n 20
  echo "--- fa strip_status ---"
  printf '%s\n' "$F_STAT" | tail -n 20
  if printf '%s\n' "$S_STAT" | grep -Eq "Completed|Failed"; then sultan_done=1; fi
  if printf '%s\n' "$F_STAT" | grep -Eq "Completed|Failed"; then fa_done=1; fi
  if [[ "$sultan_done" -eq 1 && "$fa_done" -eq 1 ]]; then
    break
  fi
  sleep 30
done

echo "==> finish_strip"
set +e
backend bench --site sultan execute erpnext.portal_control.strip_company.finish_strip \
  --kwargs "$(python3 -c 'print(repr({"keep_company": "Sultan Group"}))')"
backend bench --site fa execute erpnext.portal_control.strip_company.finish_strip \
  --kwargs "$(python3 -c 'print(repr({"keep_company": "FA Traders"}))')"
set -e

echo "==> Evidence: Company list per site"
for site in "$CONTROL_SITE" sultan fa; do
  echo "--- Company ${site} ---"
  backend bash -lc "cd /home/frappe/frappe-bench/sites && ../env/bin/python - <<PY
import frappe
frappe.init(site='${site}')
frappe.connect()
print(frappe.get_all('Company', fields=['name','abbr'], order_by='name'))
PY"
done

echo "split_sultan_fa_done"
