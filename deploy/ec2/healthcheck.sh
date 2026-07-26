#!/usr/bin/env bash
# Enterprise health probe — exit 0 healthy, 1 unhealthy. Suitable for cron + monitoring.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
LOG_FILE="${LOG_FILE:-$HOME/deploy-ec2/logs/healthcheck.log}"

mkdir -p "$(dirname "$LOG_FILE")"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

PUBLIC_HOST="${PUBLIC_HOST:?PUBLIC_HOST required}"
URL="https://${PUBLIC_HOST}/api/method/ping"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FAIL=0

code=$(curl -sS -o /tmp/pl-ping.json -w "%{http_code}" --max-time 20 "$URL" || echo 000)
body=$(cat /tmp/pl-ping.json 2>/dev/null || true)

if [[ "$code" != "200" ]] || ! echo "$body" | grep -q '"message"[[:space:]]*:[[:space:]]*"pong"'; then
  echo "$TS FAIL ping http=$code body=$body" | tee -a "$LOG_FILE"
  FAIL=1
else
  echo "$TS OK ping" >>"$LOG_FILE"
fi

DC=(docker compose)
docker compose version >/dev/null 2>&1 || DC=(sudo docker compose)

# Container presence
if ! "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps --status running --format '{{.Name}}' 2>/dev/null | grep -q backend; then
  echo "$TS FAIL backend_not_running" | tee -a "$LOG_FILE"
  FAIL=1
fi

# Disk pressure (>85%)
use=$(df -P / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
if [[ "${use:-0}" -ge 85 ]]; then
  echo "$TS WARN disk=${use}%" | tee -a "$LOG_FILE"
fi

# Memory pressure
avail_mb=$(free -m | awk '/Mem:/ {print $7}')
if [[ "${avail_mb:-9999}" -lt 100 ]]; then
  echo "$TS WARN low_mem_available_mb=$avail_mb" | tee -a "$LOG_FILE"
fi

exit "$FAIL"
