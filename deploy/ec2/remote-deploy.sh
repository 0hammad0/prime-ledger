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
# Local tip: before pushing, run deploy/ec2/sync-app-patches.sh so Hub
# hot-patches match erpnext/setup (ensure_users, user_onboarding, wizard).

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
PUBLIC_HOST="${PUBLIC_HOST:?PUBLIC_HOST required in .env}"

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

echo "==> Hot-patching Prime Ledger portal (SPA + DocTypes)"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$DEPLOY_DIR/patch-portal.sh" || true

echo "==> Reload backend so gunicorn picks up hot-patches"
BACKEND_CID="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" ps -q --status running backend | head -n1 || true)"
if [[ -n "${BACKEND_CID:-}" ]]; then
  sudo docker restart "$BACKEND_CID" || true
  for i in $(seq 1 30); do
    if sudo docker exec "$BACKEND_CID" true 2>/dev/null; then
      break
    fi
    sleep 2
  done
fi
FRONTEND_CID="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" ps -q --status running frontend | head -n1 || true)"
if [[ -n "${FRONTEND_CID:-}" ]]; then
  sudo docker restart "$FRONTEND_CID" || true
fi

echo "==> Migrating site: $SITE_NAME"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend \
  bench --site "$SITE_NAME" migrate

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

echo "==> Seeding portal modules / roles"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" exec -T backend \
  bench --site "$SITE_NAME" execute erpnext.portal_control.seed.run || true

echo "==> Applying Prime Ledger white-label"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$DEPLOY_DIR/brand.sh" || true

echo "==> Applying setup-wizard hot patches"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$DEPLOY_DIR/patch-setup-wizard.sh"

echo "==> Ensuring onboarding defaults"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$DEPLOY_DIR/ensure-onboarding.sh"

echo "==> Enterprise site config + user role profiles"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" PUBLIC_HOST="$PUBLIC_HOST" \
  bash "$DEPLOY_DIR/enterprise-config.sh" || true

echo "==> Re-apply user hooks after container recreate"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  SITE_NAME="$SITE_NAME" \
  bash "$DEPLOY_DIR/patch-user-hooks.sh" || true

echo "==> Ensure ops cron (health + nightly backup)"
bash "$DEPLOY_DIR/install-ops-cron.sh" || true

echo "==> Waiting for public HTTPS ping"
URL="https://${PUBLIC_HOST}/api/method/ping"
ok=0
for i in $(seq 1 36); do
  code=$(curl -skS -o /tmp/pl-deploy-ping.json -w "%{http_code}" --max-time 20 "$URL" || echo 000)
  body=$(cat /tmp/pl-deploy-ping.json 2>/dev/null || true)
  echo "  attempt $i → http=$code"
  if [[ "$code" == "200" ]] && echo "$body" | grep -q '"message"[[:space:]]*:[[:space:]]*"pong"'; then
    ok=1
    break
  fi
  # One auto-heal mid-wait if still failing after ~1 minute
  if [[ "$i" -eq 12 ]]; then
    echo "==> Mid-deploy heal (frontend/backend recreate)"
    AUTO_HEAL=1 sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
      bash "$DEPLOY_DIR/healthcheck.sh" || true
  fi
  sleep 5
done

if [[ "$ok" != "1" ]]; then
  echo "ERROR: public ping failed after deploy" >&2
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" ps || true
  exit 1
fi

echo "==> Final health check"
sudo ENV_FILE="$ENV_FILE" PROJECT_NAME="$PROJECT_NAME" COMPOSE_FILE="$GITOPS_FILE" \
  bash "$DEPLOY_DIR/healthcheck.sh"

echo "==> Deploy OK → https://${PUBLIC_HOST}/"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$GITOPS_FILE" ps
