# Re-apply portal hot-patch + seed on ALL sites in the bench (control + tenants).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
SITE_NAME="${SITE_NAME:-frontend}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
SITE_NAME="${SITE_NAME:-frontend}"

bash "$SCRIPT_DIR/patch-portal.sh"

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

# Discover sites (exclude assets / apps / common configs)
mapfile -t SITES < <(
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bash -lc 'cd /home/frappe/frappe-bench/sites && for d in */; do
      n="${d%/}"
      case "$n" in assets|arch|*backup*) continue ;; esac
      [[ -f "$n/site_config.json" ]] && echo "$n"
    done' | tr -d '\r'
)

if [[ ${#SITES[@]} -eq 0 ]]; then
  SITES=("$SITE_NAME")
fi

for site in "${SITES[@]}"; do
  echo "==> Ensure portal on site: $site"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$site" migrate || true
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$site" execute erpnext.portal_control.seed.run \
    && echo "portal_seed_ok:$site" \
    || echo "portal_seed_skipped:$site"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
    bench --site "$site" clear-cache || true
done

echo "Portal ensure finished for sites: ${SITES[*]}"
echo "Open /portal on each tenant host"
