#!/usr/bin/env bash
# Host watcher: Super Admin Approve → private tenant site, no SSH required.
# Cron every minute. flock skips ticks while a provision is already running.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:-$HOME/deploy-ec2/logs}"
LOCK_FILE="${LOCK_FILE:-/tmp/pl-auto-provision.lock}"
LOG="$LOG_DIR/auto-provision.log"
mkdir -p "$LOG_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) skip: provision already running" >>"$LOG"
  exit 0
fi

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) auto-provision tick" >>"$LOG"
set +e
bash "$SCRIPT_DIR/provision-approved.sh" >>"$LOG" 2>&1
rc=$?
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) done rc=$rc" >>"$LOG"
exit 0
