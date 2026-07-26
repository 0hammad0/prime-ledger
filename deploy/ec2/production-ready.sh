#!/usr/bin/env bash
# One-shot production readiness on an already-provisioned EC2 host.
# Re-renders compose, applies site hardening, installs ops cron, verifies HTTPS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
FRAPPE_DOCKER_DIR="${FRAPPE_DOCKER_DIR:-$HOME/frappe_docker}"
RUN_HARDEN="${RUN_HARDEN:-0}"
FULL_DEPLOY="${FULL_DEPLOY:-0}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

PUBLIC_HOST="${PUBLIC_HOST:?PUBLIC_HOST required}"
SITE_NAME="${SITE_NAME:-frontend}"

echo "==> Production ready $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ "$RUN_HARDEN" == "1" ]]; then
  bash "$SCRIPT_DIR/harden.sh"
fi

if [[ "$FULL_DEPLOY" == "1" ]]; then
  UPDATE_FRAPPE_DOCKER="${UPDATE_FRAPPE_DOCKER:-0}" bash "$SCRIPT_DIR/remote-deploy.sh"
  exit 0
fi

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

if [[ -d "$FRAPPE_DOCKER_DIR" ]]; then
  echo "==> Re-render compose overlays"
  cd "$FRAPPE_DOCKER_DIR"
  "${DC[@]}" --env-file "$ENV_FILE" \
    -f compose.yaml \
    -f overrides/compose.mariadb.yaml \
    -f overrides/compose.redis.yaml \
    -f overrides/compose.backup-cron.yaml \
    -f "$SCRIPT_DIR/compose.https-public.yaml" \
    -f "$SCRIPT_DIR/compose.resources.yaml" \
    config | sudo tee "$COMPOSE_FILE" >/dev/null
  sudo chown "$(id -un):$(id -gn)" "$COMPOSE_FILE" 2>/dev/null || true
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --remove-orphans
fi

bash "$SCRIPT_DIR/install-ops-cron.sh"

sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$COMPOSE_FILE" \
  SITE_NAME="$SITE_NAME" PUBLIC_HOST="$PUBLIC_HOST" \
  bash "$SCRIPT_DIR/enterprise-config.sh"

sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$COMPOSE_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$SCRIPT_DIR/ensure-onboarding.sh"

echo "==> Health check (auto-heal enabled)"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$COMPOSE_FILE" \
  AUTO_HEAL=1 bash "$SCRIPT_DIR/healthcheck.sh"

echo "==> Verify https://${PUBLIC_HOST}/api/method/ping"
for i in $(seq 1 18); do
  code=$(curl -skS -o /tmp/pl-ready.json -w "%{http_code}" --max-time 20 \
    "https://${PUBLIC_HOST}/api/method/ping" || echo 000)
  body=$(cat /tmp/pl-ready.json 2>/dev/null || true)
  echo "  attempt $i → $code"
  if [[ "$code" == "200" ]] && echo "$body" | grep -q '"message"[[:space:]]*:[[:space:]]*"pong"'; then
    echo "$body"
    echo "Production ready → https://${PUBLIC_HOST}/"
    exit 0
  fi
  sleep 5
done

echo "ERROR: public ping failed" >&2
exit 1
