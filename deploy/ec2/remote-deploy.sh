#!/usr/bin/env bash
# Runs ON the EC2 host. Safe for CI: never overwrites .env / passwords.
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-$HOME/deploy-ec2}"
FRAPPE_DOCKER_DIR="${FRAPPE_DOCKER_DIR:-$HOME/frappe_docker}"
ENV_FILE="${ENV_FILE:-$DEPLOY_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
GITOPS_FILE="${GITOPS_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
SITE_NAME="${SITE_NAME:-frontend}"

echo "==> Prime Ledger remote deploy $(date -u +%Y-%m-%dT%H:%M:%SZ)"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE on server"; exit 1; }
[[ -d "$FRAPPE_DOCKER_DIR" ]] || { echo "Missing $FRAPPE_DOCKER_DIR"; exit 1; }

chmod +x "$DEPLOY_DIR"/*.sh 2>/dev/null || true
chmod 600 "$ENV_FILE"
mkdir -p "$(dirname "$GITOPS_FILE")" "$HOME/backups/prime-ledger" "$DEPLOY_DIR/logs"

# Optional: refresh frappe_docker definitions (compose overrides)
if [[ "${UPDATE_FRAPPE_DOCKER:-1}" == "1" ]]; then
  echo "==> Updating frappe_docker repo"
  git -C "$FRAPPE_DOCKER_DIR" fetch --depth 1 origin main || true
  git -C "$FRAPPE_DOCKER_DIR" checkout main || true
  git -C "$FRAPPE_DOCKER_DIR" pull --ff-only origin main || true
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a
SITE_NAME="${SITE_NAME:-frontend}"

echo "==> Rendering compose + restarting stack"
cd "$FRAPPE_DOCKER_DIR"
COMPOSE_ARGS=(
  --env-file "$ENV_FILE"
  -f compose.yaml
  -f overrides/compose.mariadb.yaml
  -f overrides/compose.redis.yaml
  -f overrides/compose.backup-cron.yaml
  -f "$DEPLOY_DIR/compose.https-public.yaml"
  -f "$DEPLOY_DIR/compose.resources.yaml"
)

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
else
  DOCKER=(sudo docker)
fi

"${DOCKER[@]}" compose "${COMPOSE_ARGS[@]}" config > "$GITOPS_FILE"
"${DOCKER[@]}" compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" pull || true
"${DOCKER[@]}" compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" up -d --remove-orphans

echo "==> Waiting for backend"
for i in $(seq 1 30); do
  if "${DOCKER[@]}" compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend true 2>/dev/null; then
    break
  fi
  sleep 2
done

echo "==> Migrating site: $SITE_NAME"
"${DOCKER[@]}" compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend \
  bench --site "$SITE_NAME" migrate

"${DOCKER[@]}" compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

echo "==> Health check"
ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  bash "$DEPLOY_DIR/healthcheck.sh"

echo "==> Deploy OK → https://${PUBLIC_HOST}/"
"${DOCKER[@]}" compose --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" ps
