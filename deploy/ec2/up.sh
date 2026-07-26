#!/usr/bin/env bash
# Enterprise start: MariaDB + Redis + workers + Traefik HTTPS + backups + limits
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAPPE_DOCKER_DIR="${FRAPPE_DOCKER_DIR:-$HOME/frappe_docker}"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
GITOPS_FILE="${GITOPS_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
RESOURCES_FILE="${RESOURCES_FILE:-$SCRIPT_DIR/compose.resources.yaml}"
HTTPS_FILE="${HTTPS_FILE:-$SCRIPT_DIR/compose.https-public.yaml}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy .env.example → .env and set secrets"
  exit 1
fi
if [[ ! -d "$FRAPPE_DOCKER_DIR" ]]; then
  echo "Missing frappe_docker at $FRAPPE_DOCKER_DIR"
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

[[ -n "${DB_PASSWORD:-}" && "$DB_PASSWORD" != "CHANGE_ME_STRONG_PASSWORD" ]] || {
  echo "Strong DB_PASSWORD required in $ENV_FILE"; exit 1; }
[[ -n "${LETSENCRYPT_EMAIL:-}" && -n "${SITES_RULE:-}" && -n "${PUBLIC_HOST:-}" ]] || {
  echo "LETSENCRYPT_EMAIL, SITES_RULE, PUBLIC_HOST required for HTTPS"; exit 1; }

chmod 600 "$ENV_FILE" 2>/dev/null || true
mkdir -p "$(dirname "$GITOPS_FILE")" "$HOME/backups/prime-ledger" "$SCRIPT_DIR/logs"
cd "$FRAPPE_DOCKER_DIR"

COMPOSE_ARGS=(
  --env-file "$ENV_FILE"
  -f compose.yaml
  -f overrides/compose.mariadb.yaml
  -f overrides/compose.redis.yaml
  -f overrides/compose.backup-cron.yaml
  -f "$HTTPS_FILE"
)
[[ -f "$RESOURCES_FILE" ]] && COMPOSE_ARGS+=(-f "$RESOURCES_FILE")

docker compose "${COMPOSE_ARGS[@]}" config > "$GITOPS_FILE"
docker compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" up -d --remove-orphans

echo "Enterprise stack up."
echo "Public URL: https://${PUBLIC_HOST}/"
docker compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" ps
