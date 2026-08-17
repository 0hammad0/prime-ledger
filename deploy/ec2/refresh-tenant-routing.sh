#!/usr/bin/env bash
# Point Traefik at apex + tenant Host() names and let Frappe pick the site from Host.
# Let's Encrypt HTTP-01 cannot issue a wildcard for sslip.io, so every tenant host
# must be listed explicitly (refresh after each provision-tenant.sh).
#
# Usage: bash refresh-tenant-routing.sh [extra.host ...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
FRAPPE_DOCKER_DIR="${FRAPPE_DOCKER_DIR:-$HOME/frappe_docker}"
CONTROL_SITE="${CONTROL_SITE:-${SITE_NAME:-frontend}}"
DEPLOY_DIR="${DEPLOY_DIR:-$SCRIPT_DIR}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

PUBLIC_HOST="${PUBLIC_HOST:?PUBLIC_HOST required}"
CONTROL_SITE="${SITE_NAME:-frontend}"

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

echo "==> Binding apex ${PUBLIC_HOST} to control site ${CONTROL_SITE}"
set +e
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench setup add-domain --site "$CONTROL_SITE" "$PUBLIC_HOST"
ADD_DOMAIN_RC=$?
set -e
if [[ "$ADD_DOMAIN_RC" -ne 0 ]]; then
  echo "WARN: add-domain failed rc=${ADD_DOMAIN_RC} (will still ensure site symlink)" >&2
fi
echo "==> Ensure sites/${PUBLIC_HOST} -> ${CONTROL_SITE}"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc "ln -sfn '${CONTROL_SITE}' '/home/frappe/frappe-bench/sites/${PUBLIC_HOST}'"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench config dns_multitenant on || true

RAW="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.print_routing_hosts 2>/dev/null || true)"
JSON_LINE="$(printf '%s\n' "$RAW" | grep 'PL_ROUTING_HOSTS:' | tail -n1 || true)"
JSON_LINE="${JSON_LINE#PL_ROUTING_HOSTS:}"

python3 - "$ENV_FILE" "$PUBLIC_HOST" "$JSON_LINE" "$@" <<'PY'
import json, re, sys
from pathlib import Path

env_path = Path(sys.argv[1])
public = sys.argv[2].strip().lower()
raw = sys.argv[3].strip()
extras = [h.strip().lower() for h in sys.argv[4:] if h.strip()]
hosts = [public]
if raw:
    try:
        extra = json.loads(raw)
        if isinstance(extra, list):
            hosts.extend(str(x).strip().lower() for x in extra if x)
    except json.JSONDecodeError:
        pass
hosts.extend(extras)
# keep order: apex first, then unique others
seen = set()
ordered = []
for h in hosts:
    h = re.sub(r"^https?://", "", h).split("/")[0].split(":")[0]
    if not h or h in seen:
        continue
    seen.add(h)
    ordered.append(h)
rule = " || ".join("Host(`%s`)" % h for h in ordered)
text = env_path.read_text()
line = "SITES_RULE='%s'" % rule.replace("'", "")
if re.search(r"^SITES_RULE=", text, flags=re.M):
    text = re.sub(r"^SITES_RULE=.*$", line, text, count=1, flags=re.M)
else:
    text = text.rstrip() + "\n" + line + "\n"
text = re.sub(
    r"^FRAPPE_SITE_NAME_HEADER=.*$",
    r"# \g<0>  # Host header selects site (refresh-tenant-routing.sh)",
    text,
    flags=re.M,
)
env_path.write_text(text)
print("SITES_RULE=" + rule)
print("hosts=" + ",".join(ordered))
PY

# Re-export .env so compose interpolates the SITES_RULE just written
# (docker compose prefers already-exported vars over --env-file).
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo "==> Re-render compose without FRAPPE_SITE_NAME_HEADER"
cd "${FRAPPE_DOCKER_DIR}"
COMPOSE_ARGS=(
  --env-file "$ENV_FILE"
  -f compose.yaml
  -f overrides/compose.mariadb.yaml
  -f overrides/compose.redis.yaml
  -f overrides/compose.backup-cron.yaml
  -f "$DEPLOY_DIR/compose.https-public.yaml"
)
[[ -f "$DEPLOY_DIR/compose.resources.yaml" ]] && COMPOSE_ARGS+=(-f "$DEPLOY_DIR/compose.resources.yaml")
if [[ -n "${CUSTOM_IMAGE:-}" && -f "$DEPLOY_DIR/compose.brand-image.yaml" ]]; then
  COMPOSE_ARGS+=(-f "$DEPLOY_DIR/compose.brand-image.yaml")
fi

"${DC[@]}" "${COMPOSE_ARGS[@]}" config | sudo tee "$COMPOSE_FILE" >/dev/null
sudo python3 - "$COMPOSE_FILE" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
lines = [ln for ln in p.read_text().splitlines(True) if "FRAPPE_SITE_NAME_HEADER" not in ln]
p.write_text("".join(lines))
print("stripped FRAPPE_SITE_NAME_HEADER from compose")
PY
sudo chown ubuntu:ubuntu "$COMPOSE_FILE" 2>/dev/null || true

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --remove-orphans

echo "==> Wait for backend"
for i in $(seq 1 40); do
  if "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend true 2>/dev/null; then
    break
  fi
  sleep 3
done

SITE_NAME="$CONTROL_SITE" bash "$SCRIPT_DIR/patch-portal.sh"

echo "routing_ok host_list_updated"
