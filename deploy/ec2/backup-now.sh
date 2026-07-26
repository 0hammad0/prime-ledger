#!/usr/bin/env bash
# Full enterprise backup: Frappe site (+files) + MariaDB logical dump.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups/prime-ledger}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

SITE_NAME="${SITE_NAME:-frontend}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_ROOT/$STAMP"
mkdir -p "$OUT"
chmod 700 "$BACKUP_ROOT" "$OUT"

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

echo "==> Bench backup (--with-files)"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" backup --with-files

echo "==> MariaDB dump"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T db \
  mariadb-dump -uroot -p"${DB_PASSWORD}" --all-databases --single-transaction --quick --routines --triggers \
  >"$OUT/mariadb-all.sql"
gzip -f "$OUT/mariadb-all.sql"

echo "==> Copy latest site backup files out of volume"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" cp \
  "backend:/home/frappe/frappe-bench/sites/${SITE_NAME}/private/backups/." \
  "$OUT/site-backups/" 2>/dev/null || \
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc "cd /home/frappe/frappe-bench/sites/${SITE_NAME}/private/backups && tar czf - ." >"$OUT/site-backups.tar.gz"

# Retain 14 local backup sets
ls -1dt "$BACKUP_ROOT"/20* 2>/dev/null | tail -n +15 | xargs -r rm -rf

# Optional offsite (set AWS_S3_BACKUP_URI=s3://bucket/prefix)
if [[ -n "${AWS_S3_BACKUP_URI:-}" ]] && command -v aws >/dev/null 2>&1; then
  echo "==> Upload to $AWS_S3_BACKUP_URI"
  aws s3 sync "$OUT" "${AWS_S3_BACKUP_URI%/}/$STAMP/" --storage-class STANDARD_IA
fi

echo "Backup complete: $OUT"
