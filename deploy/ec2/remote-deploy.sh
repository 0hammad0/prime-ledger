#!/usr/bin/env bash
# Runs ON the EC2 host. Safe for CI: never overwrites .env / passwords.
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-$HOME/deploy-ec2}"
FRAPPE_DOCKER_DIR="${FRAPPE_DOCKER_DIR:-$HOME/frappe_docker}"
ENV_FILE="${ENV_FILE:-$DEPLOY_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
GITOPS_FILE="${GITOPS_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
SITE_NAME="${SITE_NAME:-frontend}"

echo "==> Prime Ledger remote deploy $(date -u +%Y-%m-%dT%H:%M:%SZ) (cd)"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE on server"; exit 1; }
[[ -d "$FRAPPE_DOCKER_DIR" ]] || { echo "Missing $FRAPPE_DOCKER_DIR"; exit 1; }

chmod +x "$DEPLOY_DIR"/*.sh 2>/dev/null || true
chmod 600 "$ENV_FILE"
mkdir -p "$(dirname "$GITOPS_FILE")" "$HOME/backups/prime-ledger" "$DEPLOY_DIR/logs"

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

# Non-interactive CI shells often lack docker group — use sudo docker
DC=(sudo docker compose)

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

# Optional white-label image (CUSTOM_IMAGE in .env)
if [[ -n "${CUSTOM_IMAGE:-}" && -f "$DEPLOY_DIR/compose.brand-image.yaml" ]]; then
  echo "==> Using CUSTOM_IMAGE=${CUSTOM_IMAGE}"
  COMPOSE_ARGS+=(-f "$DEPLOY_DIR/compose.brand-image.yaml")
fi

"${DC[@]}" "${COMPOSE_ARGS[@]}" config | sudo tee "$GITOPS_FILE" >/dev/null
sudo chown ubuntu:ubuntu "$GITOPS_FILE" 2>/dev/null || true

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" pull || true
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" up -d --remove-orphans

echo "==> Waiting for backend"
for i in $(seq 1 40); do
  if "${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend true 2>/dev/null; then
    break
  fi
  sleep 3
done

echo "==> Migrating site: $SITE_NAME"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend \
  bench --site "$SITE_NAME" migrate

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

echo "==> Applying Prime Ledger white-label"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$DEPLOY_DIR/brand.sh"

echo "==> Applying setup-wizard hot patches"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$DEPLOY_DIR/patch-setup-wizard.sh" || true

echo "==> Health check"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  bash "$DEPLOY_DIR/healthcheck.sh"

echo "==> Deploy OK → https://${PUBLIC_HOST}/"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" ps
