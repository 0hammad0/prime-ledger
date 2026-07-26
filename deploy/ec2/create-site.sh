#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

SITE_NAME="${SITE_NAME:-frontend}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?ADMIN_PASSWORD must be set in .env}"
DB_PASSWORD="${DB_PASSWORD:?DB_PASSWORD must be set in .env}"

echo "Waiting for db healthy + configurator..."
for i in $(seq 1 30); do
  if docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend true 2>/dev/null; then
    break
  fi
  sleep 2
done
sleep 10

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench new-site "$SITE_NAME" \
  --mariadb-user-host-login-scope='%' \
  --db-root-password "$DB_PASSWORD" \
  --admin-password "$ADMIN_PASSWORD" \
  --install-app erpnext \
  --set-default

echo "Site '$SITE_NAME' ready."
echo "Login: Administrator / (ADMIN_PASSWORD from .env)"
