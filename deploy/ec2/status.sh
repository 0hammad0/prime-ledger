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

echo "=== Prime Ledger status ==="
echo "Host: https://${PUBLIC_HOST:-unknown}/"
echo
docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps
echo
echo "=== TLS ==="
echo | openssl s_client -connect "${PUBLIC_HOST}:443" -servername "$PUBLIC_HOST" 2>/dev/null \
  | openssl x509 -noout -issuer -dates -subject 2>/dev/null || echo "cert check failed"
echo
echo "=== Health ==="
bash "$SCRIPT_DIR/healthcheck.sh" && echo HEALTHY || echo UNHEALTHY
echo
echo "=== Disk / Memory ==="
df -h / | tail -1
free -h
