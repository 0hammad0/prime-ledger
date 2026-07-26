#!/usr/bin/env bash
# Install host cron for health checks + nightly backups (enterprise ops).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/deploy-ec2/logs"

HEALTH_LINE="*/5 * * * * ENV_FILE=$SCRIPT_DIR/.env $SCRIPT_DIR/healthcheck.sh >>$HOME/deploy-ec2/logs/healthcheck.log 2>&1"
BACKUP_LINE="15 2 * * * ENV_FILE=$SCRIPT_DIR/.env $SCRIPT_DIR/backup-now.sh >>$HOME/deploy-ec2/logs/backup.log 2>&1"

(crontab -l 2>/dev/null | grep -v 'deploy-ec2/healthcheck.sh' | grep -v 'deploy-ec2/backup-now.sh' || true
 echo "$HEALTH_LINE"
 echo "$BACKUP_LINE"
) | crontab -

echo "Installed crontab:"
crontab -l | grep deploy-ec2 || true
