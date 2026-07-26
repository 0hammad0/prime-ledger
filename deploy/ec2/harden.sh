#!/usr/bin/env bash
# Host hardening for Ubuntu EC2 running Prime Ledger Docker.
# Run once as ubuntu (uses sudo): ./harden.sh
set -euo pipefail

echo "==> Unattended security updates"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y unattended-upgrades ufw fail2ban
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> UFW firewall (SSH + HTTP + HTTPS only)"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# Close demo port if still open
sudo ufw delete allow 8080/tcp 2>/dev/null || true
echo "y" | sudo ufw enable
sudo ufw status

echo "==> fail2ban (SSH brute-force protection)"
sudo systemctl enable --now fail2ban

echo "==> Docker daemon log defaults"
sudo mkdir -p /etc/docker
if [[ ! -f /etc/docker/daemon.json ]]; then
  sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true
}
JSON
  sudo systemctl restart docker
fi

echo "==> Ensure swap exists (2G)"
if ! swapon --show | grep -q /swapfile; then
  if [[ ! -f /swapfile ]]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
  fi
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "==> Lock down deploy secrets"
chmod 700 "$HOME/deploy-ec2" 2>/dev/null || true
chmod 600 "$HOME/deploy-ec2/.env" "$HOME/deploy-ec2/.db_password" "$HOME/deploy-ec2/.admin_password" 2>/dev/null || true

echo "==> SSH: key-only, no root login"
sudo mkdir -p /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/99-prime-ledger-hardening.conf >/dev/null <<'SSH'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
SSH
sudo systemctl reload ssh || sudo systemctl reload sshd || true

echo "Host hardening done."
