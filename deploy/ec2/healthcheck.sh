#!/usr/bin/env bash
# Production health probe + auto-heal. Exit 0 healthy, 1 unhealthy.
# Cron every 5m: recovers from stale nginx→backend IP after worker restarts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
LOG_FILE="${LOG_FILE:-$HOME/deploy-ec2/logs/healthcheck.log}"
AUTO_HEAL="${AUTO_HEAL:-1}"

mkdir -p "$(dirname "$LOG_FILE")"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

PUBLIC_HOST="${PUBLIC_HOST:?PUBLIC_HOST required}"
URL="https://${PUBLIC_HOST}/api/method/ping"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FAIL=0

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "$TS FAIL docker_unavailable" | tee -a "$LOG_FILE"
  exit 1
fi

ping_ok() {
  local code body tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/pl-ping.XXXXXX")"
  code=$(curl -skS -o "$tmp" -w "%{http_code}" --max-time 20 "$URL" || echo 000)
  body=$(cat "$tmp" 2>/dev/null || true)
  rm -f "$tmp"
  [[ "$code" == "200" ]] && echo "$body" | grep -q '"message"[[:space:]]*:[[:space:]]*"pong"'
}

repatch_after_recreate() {
  # Stock Hub images wipe docker cp overlays. Restore portal + login helpers.
  if [[ -x "$SCRIPT_DIR/patch-portal.sh" ]]; then
    echo "$TS HEAL re-applying patch-portal.sh" | tee -a "$LOG_FILE"
    bash "$SCRIPT_DIR/patch-portal.sh" >>"$LOG_FILE" 2>&1 || true
  fi
  if [[ -x "$SCRIPT_DIR/patch-user-hooks.sh" ]]; then
    bash "$SCRIPT_DIR/patch-user-hooks.sh" >>"$LOG_FILE" 2>&1 || true
  fi
}

heal_stack() {
  # Prefer frontend-only recreate: nginx caches the backend container IP.
  # Recreating backend wipes hot-patches and is a last resort.
  echo "$TS HEAL recreating frontend (stale upstream recovery)" | tee -a "$LOG_FILE"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --no-deps --force-recreate frontend || true
  sleep 8
  if ping_ok; then
    repatch_after_recreate
    return 0
  fi
  echo "$TS HEAL ping still down — recreating backend workers, then re-patching" | tee -a "$LOG_FILE"
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --no-deps --force-recreate \
    backend websocket queue-short queue-long scheduler || true
  sleep 8
  "${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --no-deps --force-recreate frontend || true
  sleep 5
  repatch_after_recreate
  sleep 15
}

if ! ping_ok; then
  echo "$TS FAIL ping" | tee -a "$LOG_FILE"
  FAIL=1
  if [[ "$AUTO_HEAL" == "1" ]]; then
    heal_stack
    if ping_ok; then
      echo "$TS OK ping_after_heal" | tee -a "$LOG_FILE"
      FAIL=0
    else
      echo "$TS FAIL ping_after_heal" | tee -a "$LOG_FILE"
      FAIL=1
    fi
  fi
else
  echo "$TS OK ping" >>"$LOG_FILE"
fi

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
if [[ "${avail_mb:-9999}" -lt 80 ]]; then
  echo "$TS WARN low_mem_available_mb=$avail_mb" | tee -a "$LOG_FILE"
fi

exit "$FAIL"
