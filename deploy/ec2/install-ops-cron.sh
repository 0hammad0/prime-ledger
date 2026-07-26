#!/usr/bin/env bash
# Install host cron for health checks + nightly backups (production ops).
# Do NOT pass ENV_* via sudo — Ubuntu sudoers rejects that; scripts source .env themselves.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/deploy-ec2/logs"

# Scripts source $SCRIPT_DIR/.env and use sudo docker compose when needed.
HEALTH_LINE="*/5 * * * * AUTO_HEAL=1 $SCRIPT_DIR/healthcheck.sh >>$HOME/deploy-ec2/logs/healthcheck.log 2>&1"
BACKUP_LINE="15 2 * * * $SCRIPT_DIR/backup-now.sh >>$HOME/deploy-ec2/logs/backup.log 2>&1"

(crontab -l 2>/dev/null | grep -v 'deploy-ec2/healthcheck.sh' | grep -v 'deploy-ec2/backup-now.sh' || true
 echo "$HEALTH_LINE"
 echo "$BACKUP_LINE"
) | crontab -

echo "Installed crontab:"
crontab -l | grep deploy-ec2 || true
