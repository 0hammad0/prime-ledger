#!/usr/bin/env bash
# Clone a Frappe site (MariaDB + files) onto a new site slug.
# Usage: bash clone-site.sh <SOURCE_SITE> <TARGET_SITE> <TARGET_HOST>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"

SOURCE_SITE="${1:?SOURCE_SITE required}"
TARGET_SITE="${2:?TARGET_SITE required}"
TARGET_HOST="${3:?TARGET_HOST required}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

DB_PASSWORD="${DB_PASSWORD:?DB_PASSWORD required in .env}"

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

dbexec() {
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T -e MYSQL_PWD="$DB_PASSWORD" db "$@"
}

pause_queues() {
  echo "==> Pause scheduler + queues"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" stop scheduler queue-short queue-long || true
}

start_queues() {
  echo "==> Start scheduler + queues"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" start scheduler queue-short queue-long || true
}

if backend bash -lc "test -d /home/frappe/frappe-bench/sites/${SOURCE_SITE}"; then
  :
else
  echo "SOURCE_SITE missing: ${SOURCE_SITE}" >&2
  exit 1
fi

if backend bash -lc "test -d /home/frappe/frappe-bench/sites/${TARGET_SITE}"; then
  echo "TARGET_SITE already exists: ${TARGET_SITE}" >&2
  exit 2
fi

echo "==> Clone ${SOURCE_SITE} -> ${TARGET_SITE} host=${TARGET_HOST}"
pause_queues
trap 'start_queues' EXIT

META=$(backend bash -lc "python3 - <<'PY'
import json
from pathlib import Path
src = Path('/home/frappe/frappe-bench/sites/${SOURCE_SITE}/site_config.json')
cfg = json.loads(src.read_text())
db_name = cfg.get('db_name')
db_user = cfg.get('db_user') or db_name
print(json.dumps({'db_name': db_name, 'db_user': db_user}))
PY")
META=$(printf '%s\n' "$META" | tr -d '\r' | awk 'END{print}')
echo "==> Source DB meta: ${META}"

SRC_DB=$(META="$META" python3 -c 'import json,os; print(json.loads(os.environ["META"])["db_name"])')
SRC_USER=$(META="$META" python3 -c 'import json,os; print(json.loads(os.environ["META"])["db_user"])')
NEW_DB="_${TARGET_SITE}"
NEW_DB=$(printf '%s' "$NEW_DB" | tr -c 'A-Za-z0-9_' '_' | cut -c1-64)

if [[ -z "$SRC_DB" || -z "$SRC_USER" ]]; then
  echo "Could not read source db_name/db_user" >&2
  exit 1
fi

EXISTS=$(dbexec mariadb -uroot -N -e "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='${NEW_DB}'" | tr -d '\r')
if [[ -n "${EXISTS}" ]]; then
  echo "Target database already exists: ${NEW_DB}" >&2
  exit 3
fi

echo "==> CREATE DATABASE ${NEW_DB}"
dbexec mariadb -uroot -e "CREATE DATABASE \`${NEW_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "==> GRANT source db_user onto ${NEW_DB}"
dbexec mariadb -uroot -e "GRANT ALL PRIVILEGES ON \`${NEW_DB}\`.* TO '${SRC_USER}'@'%'; FLUSH PRIVILEGES;"

echo "==> Dump/import source DB -> ${NEW_DB}"
set +e
dbexec bash -c "mariadb-dump -uroot --single-transaction --quick --routines --triggers --skip-comments '${SRC_DB}' | mariadb -uroot '${NEW_DB}'"
DUMP_RC=$?
set -e
if [[ "$DUMP_RC" -ne 0 ]]; then
  echo "clone dump/import failed rc=${DUMP_RC}" >&2
  exit "$DUMP_RC"
fi

echo "==> Copy site files ${SOURCE_SITE} -> ${TARGET_SITE}"
backend bash -lc "cp -a '/home/frappe/frappe-bench/sites/${SOURCE_SITE}' '/home/frappe/frappe-bench/sites/${TARGET_SITE}'"
backend bash -lc "rm -rf '/home/frappe/frappe-bench/sites/${TARGET_SITE}/locks'/* 2>/dev/null || true"

echo "==> Rewrite site_config db_name (keep encryption_key/db_password)"
backend bash -lc "python3 - <<'PY'
import json
from pathlib import Path
p = Path('/home/frappe/frappe-bench/sites/${TARGET_SITE}/site_config.json')
cfg = json.loads(p.read_text())
cfg['db_name'] = '${NEW_DB}'
# Frappe uses db_name as the MariaDB user when db_user is absent.
# Keep the granted source user so the clone can connect after db_name rewrite.
if not cfg.get('db_user'):
    cfg['db_user'] = '${SRC_USER}'
p.write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + '\n')
print('site_config_db_name_ok')
PY"

echo "==> Register ${TARGET_SITE} in sites.txt + host symlink"
backend bash -lc "cd /home/frappe/frappe-bench/sites && (grep -qx '${TARGET_SITE}' sites.txt 2>/dev/null || echo '${TARGET_SITE}' >> sites.txt) && ln -sfn '${TARGET_SITE}' '${TARGET_HOST}' && chown -R frappe:frappe '${TARGET_SITE}' '${TARGET_HOST}' 2>/dev/null || true"

set +e
backend bench --site "$TARGET_SITE" migrate
MIG_RC=$?
set -e
if [[ "$MIG_RC" -ne 0 ]]; then
  echo "WARN: migrate rc=${MIG_RC} (schema already cloned; continuing)" >&2
fi

set +e
backend bench setup add-domain --site "$TARGET_SITE" "$TARGET_HOST"
ADD_RC=$?
set -e
if [[ "$ADD_RC" -ne 0 ]]; then
  echo "WARN: add-domain rc=${ADD_RC} (symlink already ensured)" >&2
fi
backend bash -lc "ln -sfn '${TARGET_SITE}' '/home/frappe/frappe-bench/sites/${TARGET_HOST}'"
backend bench config dns_multitenant on || true

echo "clone_ok ${SOURCE_SITE}->${TARGET_SITE} host=${TARGET_HOST}"
